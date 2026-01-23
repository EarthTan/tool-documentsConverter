#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
md_batch_to_pdf.py
递归搜索目录下所有 Markdown (.md)，调用 md-to-pdf 转为 PDF。
可选：转换成功后删除原始 md（自动或交互式）。

用法示例：
  python md_batch_to_pdf.py
  python md_batch_to_pdf.py --root /path/to/dir
  python md_batch_to_pdf.py --delete-md
  python md_batch_to_pdf.py --ask-delete
  python md_batch_to_pdf.py --workers 4
  python md_batch_to_pdf.py --force
  python md_batch_to_pdf.py --dry-run
  python md_batch_to_pdf.py --exclude .git node_modules dist
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class JobResult:
    md_path: Path
    pdf_path: Path
    ok: bool
    elapsed_s: float
    message: str


def _human_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def _is_excluded(path: Path, exclude_names: set[str]) -> bool:
    # 任何一个父级目录名命中 exclude_names 则排除
    return any(part in exclude_names for part in path.parts)


def find_markdown_files(root: Path, exclude_names: set[str]) -> List[Path]:
    md_files: List[Path] = []
    for p in root.rglob("*.md"):
        if p.is_file() and not _is_excluded(p, exclude_names):
            md_files.append(p)
    # 稳定排序，便于日志可复现
    md_files.sort(key=lambda x: str(x).lower())
    return md_files


def build_cmd(md_path: Path, force: bool) -> List[str]:
    # md-to-pdf: 默认输出同目录同名 .pdf
    # force: 若 md-to-pdf 支持 --overwrite（不同版本参数可能不同）
    # 为兼容性：这里不强行加 overwrite 参数；force 主要用“跳过已存在PDF”的逻辑来控制。
    return ["md-to-pdf", str(md_path)]


def convert_one(md_path: Path, root: Path, force: bool, dry_run: bool) -> JobResult:
    t0 = time.time()
    pdf_path = md_path.with_suffix(".pdf")

    # 若已存在 PDF，且不 force，则跳过
    if pdf_path.exists() and not force:
        return JobResult(
            md_path=md_path,
            pdf_path=pdf_path,
            ok=True,
            elapsed_s=0.0,
            message="SKIP (pdf exists)",
        )

    cmd = build_cmd(md_path, force=force)

    if dry_run:
        return JobResult(
            md_path=md_path,
            pdf_path=pdf_path,
            ok=True,
            elapsed_s=0.0,
            message=f"DRY-RUN: {' '.join(cmd)}",
        )

    try:
        # capture_output=True 便于把失败原因写入日志
        proc = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=True,
        )
        elapsed = time.time() - t0

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            if not msg:
                msg = f"md-to-pdf exited with code {proc.returncode}"
            return JobResult(md_path, pdf_path, False, elapsed, msg)

        if not pdf_path.exists():
            # 有些工具可能输出到别处；这里按“同目录同名”作为默认规则
            msg = "md-to-pdf succeeded but expected PDF not found next to md"
            return JobResult(md_path, pdf_path, False, elapsed, msg)

        return JobResult(md_path, pdf_path, True, elapsed, "OK")

    except FileNotFoundError:
        elapsed = time.time() - t0
        return JobResult(
            md_path=md_path,
            pdf_path=pdf_path,
            ok=False,
            elapsed_s=elapsed,
            message="md-to-pdf not found in PATH. Install it (e.g., npm i -g md-to-pdf).",
        )
    except Exception as e:
        elapsed = time.time() - t0
        return JobResult(md_path, pdf_path, False, elapsed, f"Unexpected error: {e}")


def ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    suffix = " [y/N] " if default_no else " [Y/n] "
    while True:
        ans = input(prompt + suffix).strip().lower()
        if not ans:
            return not default_no
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please type y/yes or n/no.")


def maybe_delete_md(
    md_path: Path,
    mode_delete: bool,
    mode_ask: bool,
    dry_run: bool,
) -> Tuple[bool, str]:
    """
    返回 (deleted?, message)
    """
    if not (mode_delete or mode_ask):
        return False, "keep md"

    do_delete = mode_delete
    if mode_ask:
        do_delete = ask_yes_no(f"Delete source md? {md_path}", default_no=True)

    if not do_delete:
        return False, "keep md"

    if dry_run:
        return True, "DRY-RUN delete"

    try:
        md_path.unlink()
        return True, "deleted"
    except Exception as e:
        return False, f"delete failed: {e}"


def print_header(root: Path, total: int, workers: int, force: bool, dry_run: bool, delete_md: bool, ask_delete: bool):
    print("md-to-pdf batch: Markdown → PDF")
    print(f"Root: {root}")
    print(
        f"MD files: {total} | workers={workers} | force={force} | dry_run={dry_run} | "
        f"delete_md={delete_md} | ask_delete={ask_delete}"
    )
    print("-" * 72)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recursively convert all .md files to .pdf via md-to-pdf.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--root",
        type=str,
        default="..",  # 默认从父目录（项目根目录）开始搜索
        help="Root directory to scan (default: parent directory).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(2, (os.cpu_count() or 4) // 2),
        help="Number of concurrent conversions (thread pool).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-render even if target PDF already exists (otherwise skip).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done, without running conversions or deleting files.",
    )
    parser.add_argument(
        "--delete-md",
        action="store_true",
        help="Delete source .md automatically after successful PDF generation.",
    )
    parser.add_argument(
        "--ask-delete",
        action="store_true",
        help="Ask interactively whether to delete each source .md after success.",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"],
        help="Directory names to exclude anywhere in the path.",
    )
    args = parser.parse_args(argv)

    if args.delete_md and args.ask_delete:
        print("❌ You cannot use --delete-md and --ask-delete together.")
        return 2

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"❌ Root is not a directory: {root}")
        return 2

    # 提前检查 md-to-pdf（dry-run 时允许不安装）
    if not args.dry_run and shutil.which("md-to-pdf") is None:
        print("❌ md-to-pdf not found in PATH.")
        print("   Install: npm i -g md-to-pdf")
        return 2

    exclude_names = set(args.exclude or [])
    md_files = find_markdown_files(root, exclude_names)

    print_header(
        root=root,
        total=len(md_files),
        workers=args.workers,
        force=args.force,
        dry_run=args.dry_run,
        delete_md=args.delete_md,
        ask_delete=args.ask_delete,
    )

    if not md_files:
        print("No markdown files found.")
        return 0

    ok_count = 0
    fail_count = 0
    skip_count = 0
    del_count = 0

    # 并发转换（删除逻辑放在主线程按完成顺序处理，避免交互阻塞线程池）
    results: List[JobResult] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        future_map = {
            ex.submit(convert_one, md, root, args.force, args.dry_run): md for md in md_files
        }

        done_idx = 0
        total = len(future_map)

        for fut in as_completed(future_map):
            done_idx += 1
            res = fut.result()
            results.append(res)

            rel_md = _human_rel(res.md_path, root)
            rel_pdf = _human_rel(res.pdf_path, root)

            # 输出每个任务一行摘要 + 失败原因（若失败）
            if res.message.startswith("SKIP"):
                skip_count += 1
                print(f"[{done_idx:>4}/{total}] SKIP  {rel_md}  ->  {rel_pdf}")
                continue

            if res.ok:
                ok_count += 1
                print(f"[{done_idx:>4}/{total}] OK    {rel_md}  ->  {rel_pdf}  ({res.elapsed_s:.2f}s)")
                deleted, del_msg = maybe_delete_md(
                    res.md_path,
                    mode_delete=args.delete_md,
                    mode_ask=args.ask_delete,
                    dry_run=args.dry_run,
                )
                if deleted:
                    del_count += 1
                    print(f"              🧹 {del_msg}: {rel_md}")
            else:
                fail_count += 1
                print(f"[{done_idx:>4}/{total}] FAIL  {rel_md}  ({res.elapsed_s:.2f}s)")
                print(f"              Reason: {res.message}")

    print("-" * 72)
    print(
        f"Done. OK={ok_count} | FAIL={fail_count} | SKIP={skip_count} | "
        f"Deleted MD={del_count} | Total MD={len(md_files)}"
    )

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())