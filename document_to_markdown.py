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
    doc_path: Path
    md_path: Path
    status: str              # "ok" | "skipped" | "failed"
    seconds: float
    message: str = ""
    cmd: Optional[List[str]] = None


def ensure_converter_exists(file_types: List[str]) -> None:
    """
    检查是否有可用的转换工具
    
    参数:
        file_types: 要处理的文件类型列表，如 ['pdf', 'docx', 'doc']
    """
    errors = []
    
    # 检查PDF转换工具
    if 'pdf' in file_types:
        pdf_tools_available = False
        
        # 检查marker工具
        marker_bin = "marker"
        if shutil.which(marker_bin) is not None:
            try:
                result = subprocess.run([marker_bin, "--help"], capture_output=True, text=True, timeout=2)
                if "--output" in result.stdout or "--output" in result.stderr:
                    pdf_tools_available = True
            except:
                pass
        
        # 检查pdftotext
        if not pdf_tools_available and shutil.which("pdftotext") is not None:
            pdf_tools_available = True
        
        # 检查Python库
        if not pdf_tools_available:
            try:
                import pdfminer
                pdf_tools_available = True
            except ImportError:
                pass
        
        if not pdf_tools_available:
            errors.append("PDF转换工具：请安装以下之一：\n"
                         "  1. 正确的marker工具（PDF转Markdown）\n"
                         "  2. pdftotext（来自poppler）\n"
                         "  3. Python库：pip install pdfminer.six")
    
    # 检查Word文档转换工具
    word_types = [ft for ft in file_types if ft in ['docx', 'doc']]
    if word_types:
        word_tools_available = False
        
        # 检查pandoc
        if shutil.which("pandoc") is not None:
            word_tools_available = True
        
        # 检查python-docx
        if not word_tools_available:
            try:
                import docx
                word_tools_available = True
            except ImportError:
                pass
        
        # 检查antiword（针对.doc文件）
        if not word_tools_available and 'doc' in word_types and shutil.which("antiword") is not None:
            word_tools_available = True
        
        # 检查catdoc
        if not word_tools_available and shutil.which("catdoc") is not None:
            word_tools_available = True
        
        if not word_tools_available:
            errors.append("Word文档转换工具：请安装以下之一：\n"
                         "  1. pandoc（推荐）\n"
                         "  2. python-docx（Python库）\n"
                         "  3. antiword（针对.doc文件）\n"
                         "  4. catdoc（文本提取）")
    
    if errors:
        error_msg = "找不到可用的转换工具：\n\n" + "\n\n".join(errors)
        raise RuntimeError(error_msg)


def build_pdf_converter_cmd(pdf_path: Path, out_dir: Path) -> Tuple[str, List[str]]:
    """
    根据可用的工具构建PDF转换命令
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


def build_word_converter_cmd(doc_path: Path, out_dir: Path) -> Tuple[str, List[str]]:
    """
    根据可用的工具构建Word文档转换命令
    返回：(tool_name, command_args)
    """
    # 方法1: 尝试使用pandoc（首选）
    if shutil.which("pandoc") is not None:
        output_file = out_dir / f"{doc_path.stem}.md"
        return ("pandoc", ["pandoc", "-s", str(doc_path), "-t", "markdown", "-o", str(output_file)])
    
    # 方法2: 尝试使用python-docx
    try:
        import docx
        return ("python-docx", ["python3", "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent}')
from docx_converter import convert_docx_to_markdown
success, message, output_file = convert_docx_to_markdown('{doc_path}', '{out_dir}')
if not success:
    print(message, file=sys.stderr)
    sys.exit(1)
"""])
    except ImportError:
        pass
    
    # 方法3: 尝试使用antiword（针对.doc文件）
    if doc_path.suffix.lower() == '.doc' and shutil.which("antiword") is not None:
        output_file = out_dir / f"{doc_path.stem}.txt"
        return ("antiword", ["antiword", str(doc_path), ">", str(output_file)])
    
    # 方法4: 尝试使用catdoc
    if shutil.which("catdoc") is not None:
        output_file = out_dir / f"{doc_path.stem}.txt"
        return ("catdoc", ["catdoc", str(doc_path), ">", str(output_file)])
    
    # 如果没有工具，使用docx_converter模块
    return ("docx-converter", ["python3", "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent}')
from docx_converter import convert_docx_to_markdown
success, message, output_file = convert_docx_to_markdown('{doc_path}', '{out_dir}')
if not success:
    print(message, file=sys.stderr)
    sys.exit(1)
"""])


def build_converter_cmd(doc_path: Path, out_dir: Path) -> Tuple[str, List[str]]:
    """
    根据文件类型构建转换命令
    返回：(tool_name, command_args)
    """
    suffix = doc_path.suffix.lower()
    
    if suffix == '.pdf':
        return build_pdf_converter_cmd(doc_path, out_dir)
    elif suffix in ['.docx', '.doc']:
        return build_word_converter_cmd(doc_path, out_dir)
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")


def find_documents(root: Path, include_types: List[str], include_hidden: bool) -> List[Path]:
    """
    查找指定类型的文档文件
    
    参数:
        root: 根目录
        include_types: 要包含的文件类型列表，如 ['pdf', 'docx', 'doc']
        include_hidden: 是否包含隐藏文件
    
    返回:
        文档文件路径列表
    """
    documents: List[Path] = []
    
    # 构建扩展名模式
    patterns = []
    for file_type in include_types:
        if file_type == 'pdf':
            patterns.append('*.pdf')
        elif file_type == 'docx':
            patterns.append('*.docx')
        elif file_type == 'doc':
            patterns.append('*.doc')
    
    for pattern in patterns:
        for p in root.rglob(pattern):
            if not include_hidden and any(part.startswith(".") for part in p.relative_to(root).parts):
                continue
            documents.append(p)
    
    return sorted(documents)


def compute_final_md_path(doc_path: Path) -> Path:
    return doc_path.with_suffix(".md")


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
    doc_path: Path,
    root: Path,
    force: bool,
    dry_run: bool,
    timeout: Optional[int],
    verbose_cmd: bool,
    keep_outputs: bool,
) -> TaskResult:
    t0 = time.perf_counter()
    final_md = compute_final_md_path(doc_path)

    if final_md.exists() and not force:
        return TaskResult(doc_path, final_md, "skipped", time.perf_counter() - t0, "目标 Markdown 已存在，跳过（用 --force 覆盖）")

    # 为每个文档创建专属输出目录，避免输出互相覆盖
    base_out = root / "_marker_outputs"
    doc_out = base_out / f"{safe_stem(doc_path)}__{abs(hash(str(doc_path))) % 10**8}"
    # 若 force，清理旧输出
    if doc_out.exists() and force and not dry_run:
        shutil.rmtree(doc_out, ignore_errors=True)

    try:
        tool_name, cmd = build_converter_cmd(doc_path, doc_out)
    except ValueError as e:
        return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, str(e))

    if dry_run:
        return TaskResult(doc_path, final_md, "skipped", time.perf_counter() - t0, "dry-run：未执行", cmd=cmd)

    doc_out.mkdir(parents=True, exist_ok=True)

    try:
        # 处理包含shell操作符的命令
        if '>' in ' '.join(cmd):
            # 使用shell执行
            proc = subprocess.run(
                ' '.join(cmd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        else:
            # 不使用shell
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
                msg += f"\ncmd={shlex.join(cmd) if not '>' in ' '.join(cmd) else ' '.join(cmd)}"
            return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)

        # 根据工具类型查找输出文件
        suffix = doc_path.suffix.lower()
        if tool_name == "pdftotext":
            produced_file = doc_out / f"{doc_path.stem}.txt"
            if not produced_file.exists():
                produced_file = next(doc_out.rglob("*.txt"), None)
        elif tool_name in ["antiword", "catdoc"]:
            # 这些工具输出.txt文件
            produced_file = doc_out / f"{doc_path.stem}.txt"
            if not produced_file.exists():
                produced_file = next(doc_out.rglob("*.txt"), None)
            
            # 将.txt转换为.md
            if produced_file and produced_file.exists():
                md_file = doc_out / f"{doc_path.stem}.md"
                with open(produced_file, 'r', encoding='utf-8', errors='ignore') as f_in, \
                     open(md_file, 'w', encoding='utf-8') as f_out:
                    f_out.write(f"# {doc_path.stem}\n\n")
                    f_out.write("```text\n")
                    f_out.write(f_in.read())
                    f_out.write("\n```\n")
                produced_file = md_file
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
                msg += f"\ncmd={shlex.join(cmd) if not '>' in ' '.join(cmd) else ' '.join(cmd)}"
            return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)

        # 将产物复制成你想要的同目录同名 .md
        final_md.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(produced_file, final_md)

        # 如果不保留输出目录，则清理
        if not keep_outputs:
            shutil.rmtree(doc_out, ignore_errors=True)

        msg = f"转换完成 | produced={produced_file}"
        if verbose_cmd:
            msg += f" | cmd={shlex.join(cmd) if not '>' in ' '.join(cmd) else ' '.join(cmd)}"
        return TaskResult(doc_path, final_md, "ok", time.perf_counter() - t0, msg, cmd=cmd)

    except subprocess.TimeoutExpired:
        msg = f"{tool_name} 超时（>{timeout}s）"
        if verbose_cmd:
            msg += f" | cmd={shlex.join(cmd) if not '>' in ' '.join(cmd) else ' '.join(cmd)}"
        return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)
    except Exception as e:
        msg = f"执行异常：{type(e).__name__}: {e}"
        if verbose_cmd:
            msg += f" | cmd={shlex.join(cmd) if not '>' in ' '.join(cmd) else ' '.join(cmd)}"
        return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)


def fmt_path(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except Exception:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="递归将目录下所有文档（PDF、DOCX、DOC）转为 Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                         # 转换所有PDF文件
  %(prog)s --types pdf docx        # 转换PDF和DOCX文件
  %(prog)s --types all             # 转换所有支持的文件类型
  %(prog)s --force                 # 强制重新转换所有文件
  %(prog)s --dry-run               # 只显示计划，不执行
        """
    )
    ap.add_argument("--force", action="store_true", help="即使目标 .md 已存在也强制重跑")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1), help="并发线程数（默认 CPU核-1）")
    ap.add_argument("--timeout", type=int, default=0, help="单个文件超时秒数（0=不设超时）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不执行")
    ap.add_argument("--include-hidden", action="store_true", help="包含隐藏目录/文件（以 . 开头）")
    ap.add_argument("--verbose-cmd", action="store_true", help="日志里输出完整命令")
    ap.add_argument("--keep-outputs", action="store_true", help="保留 _marker_outputs/ 下的原始输出（便于调试）")
    ap.add_argument("--types", nargs="+", default=["pdf"], 
                   choices=["pdf", "docx", "doc", "all"],
                   help="要处理的文件类型（默认：pdf，'all' 表示所有类型）")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = script_dir

    # 处理文件类型
    if "all" in args.types:
        file_types = ["pdf", "docx", "doc"]
    else:
        file_types = args.types

    try:
        ensure_converter_exists(file_types)
    except Exception as e:
        print(red(f"[FATAL] {e}"))
        return 2

    documents = find_documents(root, file_types, include_hidden=args.include_hidden)
    if not documents:
        print(yellow(f"未找到任何 {', '.join(file_types)} 文件。"))
        return 0

    timeout = None if args.timeout <= 0 else args.timeout

    print(bold("文档批量转换 → Markdown"))
    print(f"根目录: {blue(str(root))}")
    print(f"文件类型: {blue(', '.join(file_types))}")
    print(f"文件数: {blue(str(len(documents)))} | workers={blue(str(args.workers))} | force={args.force} | dry_run={args.dry_run}")
    if timeout is not None:
        print(f"单文件超时: {blue(str(timeout))}s")
    if args.keep_outputs:
        print(f"保留输出: {blue('true')} (will leave _marker_outputs/)")
    print("-" * 72)

    t_all = time.perf_counter()
    results: List[TaskResult] = []

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, doc, root, args.force, args.dry_run, timeout, args.verbose_cmd, args.keep_outputs) for doc in documents]
        total = len(futs)
        done = 0

        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1

            rel_doc = fmt_path(r.doc_path, root)
            rel_md = fmt_path(r.md_path, root)
            cost = f"{r.seconds:.2f}s"

            if r.status == "ok":
                print(f"[{done:>4}/{total}] {green('OK   ')} {rel_doc}  →  {rel_md}  {dim(cost)}")
            elif r.status == "skipped":
                print(f"[{done:>4}/{total}] {yellow('SKIP ')} {rel_doc}  {dim(r.message)}")
                if args.dry_run and r.cmd:
                    print(dim(f"           cmd: {shlex.join(r.cmd) if not '>' in ' '.join(r.cmd) else ' '.join(r.cmd)}"))
            else:
                print(f"[{done:>4}/{total}] {red('FAIL ')} {rel_doc}  {dim(cost)}")
                first_line = (r.message or "").strip().splitlines()[0] if r.message else ""
                if first_line:
                    print(dim(f"           {first_line}"))

    elapsed = time.perf_counter() - t_all

    ok = [x for x in results if x.status == "ok"]
    skipped = [x for x in results if x.status == "skipped"]
    failed = [x for x in results if x.status == "failed"]

    print("-" * 72)
    print(bold("总结"))
    print(f"总计:   {len(results)}")
    print(f"成功:   {green(str(len(ok)))}")
    print(f"跳过:   {yellow(str(len(skipped)))}")
    print(f"失败:   {red(str(len(failed)))}")
    print(f"耗时:   {elapsed:.2f}s")

    if failed:
        print("\n" + bold("失败详情"))
        for r in sorted(failed, key=lambda x: str(x.doc_path)):
            rel_doc = fmt_path(r.doc_path, root)
            print(red(f"\n- {rel_doc}"))
            if r.cmd:
                print(dim(f"  cmd: {shlex.join(r.cmd) if not '>' in ' '.join(r.cmd) else ' '.join(r.cmd)}"))
            msg = (r.message or "").rstrip()
            if msg:
                for line in msg.splitlines():
                    print(dim(f"  {line}"))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
