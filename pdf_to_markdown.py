#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()

COLOR = supports_color()

def c(text: str, code: str) -> str:
    if not COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(s: str) -> str: return c(s, "32")
def yellow(s: str) -> str: return c(s, "33")
def red(s: str) -> str: return c(s, "31")
def blue(s: str) -> str: return c(s, "34")
def dim(s: str) -> str: return c(s, "2")
def bold(s: str) -> str: return c(s, "1")


@dataclass(frozen=True)
class TaskResult:
    pdf_path: Path
    md_path: Path
    status: str              # "ok" | "skipped" | "failed"
    seconds: float
    message: str = ""
    cmd: Optional[List[str]] = None


def ensure_converter_exists() -> None:
    """检查是否有可用的PDF转换工具"""
    # 首先检查是否有正确的marker工具（PDF转Markdown）
    marker_bin = "marker"
    if shutil.which(marker_bin) is not None:
        # 检查是否是PDF转Markdown工具（通过运行--help查看）
        try:
            result = subprocess.run([marker_bin, "--help"], capture_output=True, text=True, timeout=2)
            if "--output" in result.stdout or "--output" in result.stderr:
                return  # 看起来是正确的工具
        except:
            pass  # 不是正确的工具
    
    # 检查是否有其他工具
    if shutil.which("pdftotext") is not None:
        return
    
    # 检查Python库
    try:
        import pdfminer
        return
    except ImportError:
        pass
    
    raise RuntimeError("找不到可用的PDF转换工具。请安装以下之一：\n"
                       "1. 正确的marker工具（PDF转Markdown）\n"
                       "2. pdftotext（来自poppler）\n"
                       "3. Python库：pip install pdfminer.six")


def build_converter_cmd(pdf_path: Path, out_dir: Path) -> Tuple[str, List[str]]:
    """
    根据可用的工具构建转换命令
    返回：(tool_name, command_args)
    """
    marker_bin = "marker"
    if shutil.which(marker_bin) is not None:
        # 检查是否是PDF转Markdown工具
        try:
            result = subprocess.run([marker_bin, "--help"], capture_output=True, text=True, timeout=2)
            if "--output" in result.stdout or "--output" in result.stderr:
                return ("marker", [marker_bin, str(pdf_path), "--output", str(out_dir)])
        except:
            pass
    
    # 尝试使用pdftotext
    if shutil.which("pdftotext") is not None:
        output_file = out_dir / f"{pdf_path.stem}.txt"
        return ("pdftotext", ["pdftotext", str(pdf_path), str(output_file)])
    
    # 如果没有外部工具，使用Python库
    return ("python", ["python3", "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent}')
from pdf_converter import convert_pdf_to_markdown
convert_pdf_to_markdown('{pdf_path}', '{out_dir}')
"""])


def find_pdfs(root: Path, include_hidden: bool) -> List[Path]:
    pdfs: List[Path] = []
    for p in root.rglob("*.pdf"):
        if not include_hidden and any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        pdfs.append(p)
    return sorted(pdfs)


def compute_final_md_path(pdf_path: Path) -> Path:
    return pdf_path.with_suffix(".md")


def safe_stem(path: Path) -> str:
    # 生成一个文件系统友好的 stem 用于输出目录名
    s = path.stem
    # 允许中文，但把分隔符/奇怪符号稍微处理一下，避免目录问题
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, "_")
    s = s.strip() or "document"
    return s


def newest_md_in_dir(out_dir: Path) -> Optional[Path]:
    mds = list(out_dir.rglob("*.md"))
    if not mds:
        return None
    # 选修改时间最新的那个
    mds.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return mds[0]


def run_one(
    pdf_path: Path,
    root: Path,
    force: bool,
    dry_run: bool,
    timeout: Optional[int],
    verbose_cmd: bool,
    keep_outputs: bool,
) -> TaskResult:
    t0 = time.perf_counter()
    final_md = compute_final_md_path(pdf_path)

    if final_md.exists() and not force:
        return TaskResult(pdf_path, final_md, "skipped", time.perf_counter() - t0, "目标 Markdown 已存在，跳过（用 --force 覆盖）")

    # 为每个 PDF 创建专属输出目录，避免 marker 输出互相覆盖
    base_out = root / "_marker_outputs"
    doc_out = base_out / f"{safe_stem(pdf_path)}__{abs(hash(str(pdf_path))) % 10**8}"
    # 若 force，清理旧输出
    if doc_out.exists() and force and not dry_run:
        shutil.rmtree(doc_out, ignore_errors=True)

    tool_name, cmd = build_converter_cmd(pdf_path, doc_out)

    if dry_run:
        return TaskResult(pdf_path, final_md, "skipped", time.perf_counter() - t0, "dry-run：未执行", cmd=cmd)

    doc_out.mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "").strip()[-1200:]
            stdout_tail = (proc.stdout or "").strip()[-600:]
            msg = f"{tool_name} 失败，exit code={proc.returncode}"
            details = "\n".join([x for x in [stdout_tail, stderr_tail] if x])
            if details:
                msg += f"\n--- {tool_name} output tail ---\n{details}"
            if verbose_cmd:
                msg += f"\ncmd={shlex.join(cmd)}"
            return TaskResult(pdf_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)

        # 根据工具类型查找输出文件
        if tool_name == "pdftotext":
            produced_file = doc_out / f"{pdf_path.stem}.txt"
            if not produced_file.exists():
                produced_file = next(doc_out.rglob("*.txt"), None)
        else:
            produced_file = newest_md_in_dir(doc_out)
            
        if produced_file is None:
            stderr_tail = (proc.stderr or "").strip()[-1200:]
            stdout_tail = (proc.stdout or "").strip()[-1200:]
            msg = (
                f"{tool_name} 返回成功，但在输出目录里没有找到任何输出文件。\n"
                f"输出目录：{doc_out}\n"
                "请用 --verbose-cmd 查看实际输出了什么，或检查工具是否输出为其他格式。"
            )
            details = "\n".join([x for x in [stdout_tail, stderr_tail] if x])
            if details:
                msg += f"\n--- {tool_name} output tail ---\n{details}"
            if verbose_cmd:
                msg += f"\ncmd={shlex.join(cmd)}"
            return TaskResult(pdf_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)

        # 将产物复制成你想要的同目录同名 .md
        final_md.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(produced_file, final_md)

        # 如果不保留 marker 输出目录，则清理
        if not keep_outputs:
            shutil.rmtree(doc_out, ignore_errors=True)

        msg = f"转换完成 | produced={produced_file}"
        if verbose_cmd:
            msg += f" | cmd={shlex.join(cmd)}"
        return TaskResult(pdf_path, final_md, "ok", time.perf_counter() - t0, msg, cmd=cmd)

    except subprocess.TimeoutExpired:
        msg = f"{tool_name} 超时（>{timeout}s）"
        if verbose_cmd:
            msg += f" | cmd={shlex.join(cmd)}"
        return TaskResult(pdf_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)
    except Exception as e:
        msg = f"执行异常：{type(e).__name__}: {e}"
        if verbose_cmd:
            msg += f" | cmd={shlex.join(cmd)}"
        return TaskResult(pdf_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)


def fmt_path(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except Exception:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description="递归调用 marker 将脚本目录下所有 PDF 转为 Markdown（稳健定位输出）")
    ap.add_argument("--force", action="store_true", help="即使目标 .md 已存在也强制重跑")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1), help="并发线程数（默认 CPU核-1）")
    ap.add_argument("--timeout", type=int, default=0, help="单个文件超时秒数（0=不设超时）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不执行")
    ap.add_argument("--include-hidden", action="store_true", help="包含隐藏目录/文件（以 . 开头）")
    ap.add_argument("--verbose-cmd", action="store_true", help="日志里输出完整命令")
    ap.add_argument("--keep-outputs", action="store_true", help="保留 _marker_outputs/ 下的 marker 原始输出（便于调试）")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = script_dir

    try:
        ensure_converter_exists()
    except Exception as e:
        print(red(f"[FATAL] {e}"))
        return 2

    pdfs = find_pdfs(root, include_hidden=args.include_hidden)
    if not pdfs:
        print(yellow("未找到任何 PDF。"))
        return 0

    timeout = None if args.timeout <= 0 else args.timeout

    print(bold("marker batch PDF → Markdown"))
    print(f"Root: {blue(str(root))}")
    print(f"PDFs: {blue(str(len(pdfs)))} | workers={blue(str(args.workers))} | force={args.force} | dry_run={args.dry_run}")
    if timeout is not None:
        print(f"Timeout per file: {blue(str(timeout))}s")
    if args.keep_outputs:
        print(f"Keep outputs: {blue('true')} (will leave _marker_outputs/)")
    print("-" * 72)

    t_all = time.perf_counter()
    results: List[TaskResult] = []

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, pdf, root, args.force, args.dry_run, timeout, args.verbose_cmd, args.keep_outputs) for pdf in pdfs]
        total = len(futs)
        done = 0

        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1

            rel_pdf = fmt_path(r.pdf_path, root)
            rel_md = fmt_path(r.md_path, root)
            cost = f"{r.seconds:.2f}s"

            if r.status == "ok":
                print(f"[{done:>4}/{total}] {green('OK   ')} {rel_pdf}  →  {rel_md}  {dim(cost)}")
            elif r.status == "skipped":
                print(f"[{done:>4}/{total}] {yellow('SKIP ')} {rel_pdf}  {dim(r.message)}")
                if args.dry_run and r.cmd:
                    print(dim(f"           cmd: {shlex.join(r.cmd)}"))
            else:
                print(f"[{done:>4}/{total}] {red('FAIL ')} {rel_pdf}  {dim(cost)}")
                first_line = (r.message or "").strip().splitlines()[0] if r.message else ""
                if first_line:
                    print(dim(f"           {first_line}"))

    elapsed = time.perf_counter() - t_all

    ok = [x for x in results if x.status == "ok"]
    skipped = [x for x in results if x.status == "skipped"]
    failed = [x for x in results if x.status == "failed"]

    print("-" * 72)
    print(bold("Summary"))
    print(f"Total:   {len(results)}")
    print(f"OK:      {green(str(len(ok)))}")
    print(f"Skipped: {yellow(str(len(skipped)))}")
    print(f"Failed:  {red(str(len(failed)))}")
    print(f"Elapsed: {elapsed:.2f}s")

    if failed:
        print("\n" + bold("Failures (details)"))
        for r in sorted(failed, key=lambda x: str(x.pdf_path)):
            rel_pdf = fmt_path(r.pdf_path, root)
            print(red(f"\n- {rel_pdf}"))
            if r.cmd:
                print(dim(f"  cmd: {shlex.join(r.cmd)}"))
            msg = (r.message or "").rstrip()
            if msg:
                for line in msg.splitlines():
                    print(dim(f"  {line}"))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())