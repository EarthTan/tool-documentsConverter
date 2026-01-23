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
from typing import Optional, List, Tuple, Any

# 导入配置管理器
try:
    from .config_manager import ConfigManager, create_arg_parser
    from .delete_manager import DeleteManager
except ImportError:
    # 当直接运行main.py时使用绝对导入
    from config_manager import ConfigManager, create_arg_parser
    from delete_manager import DeleteManager


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
    """
    errors = []
    
    if 'pdf' in file_types:
        pdf_tools_available = False
        
        marker_bin = "marker"
        if shutil.which(marker_bin) is not None:
            try:
                result = subprocess.run([marker_bin, "--help"], capture_output=True, text=True, timeout=2)
                if "--output" in result.stdout or "--output" in result.stderr:
                    pdf_tools_available = True
            except:
                pass
        
        if not pdf_tools_available and shutil.which("pdftotext") is not None:
            pdf_tools_available = True
        
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
    
    word_types = [ft for ft in file_types if ft in ['docx', 'doc']]
    if word_types:
        word_tools_available = False
        
        if shutil.which("pandoc") is not None:
            word_tools_available = True
        
        if not word_tools_available:
            try:
                import docx
                word_tools_available = True
            except ImportError:
                pass
        
        if not word_tools_available and 'doc' in word_types and shutil.which("antiword") is not None:
            word_tools_available = True
        
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
    marker_bin = "marker"
    if shutil.which(marker_bin) is not None:
        try:
            result = subprocess.run([marker_bin, "--help"], capture_output=True, text=True, timeout=2)
            if "--output" in result.stdout or "--output" in result.stderr:
                return ("marker", [marker_bin, str(pdf_path), "--output", str(out_dir)])
        except:
            pass
    
    if shutil.which("pdftotext") is not None:
        output_file = out_dir / f"{pdf_path.stem}.txt"
        return ("pdftotext", ["pdftotext", str(pdf_path), str(output_file)])
    
    return ("python", ["python3", "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent}')
from pdf_converter import convert_pdf_to_markdown
convert_pdf_to_markdown('{pdf_path}', '{out_dir}')
"""])


def build_word_converter_cmd(doc_path: Path, out_dir: Path) -> Tuple[str, List[str]]:
    if shutil.which("pandoc") is not None:
        output_file = out_dir / f"{doc_path.stem}.md"
        return ("pandoc", ["pandoc", "-s", str(doc_path), "-t", "markdown", "-o", str(output_file)])
    
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
    
    if doc_path.suffix.lower() == '.doc' and shutil.which("antiword") is not None:
        output_file = out_dir / f"{doc_path.stem}.txt"
        return ("antiword", ["antiword", str(doc_path), ">", str(output_file)])
    
    if shutil.which("catdoc") is not None:
        output_file = out_dir / f"{doc_path.stem}.txt"
        return ("catdoc", ["catdoc", str(doc_path), ">", str(output_file)])
    
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
    suffix = doc_path.suffix.lower()
    
    if suffix == '.pdf':
        return build_pdf_converter_cmd(doc_path, out_dir)
    elif suffix in ['.docx', '.doc']:
        return build_word_converter_cmd(doc_path, out_dir)
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")


def find_documents(root: Path, include_types: List[str], include_hidden: bool, exclude_dirs: List[str]) -> List[Path]:
    documents: List[Path] = []
    
    patterns = []
    for file_type in include_types:
        if file_type == 'pdf':
            patterns.append('*.pdf')
        elif file_type == 'docx':
            patterns.append('*.docx')
        elif file_type == 'doc':
            patterns.append('*.doc')
    
    exclude_set = set(exclude_dirs)
    
    for pattern in patterns:
        for p in root.rglob(pattern):
            if any(part in exclude_set for part in p.parts):
                continue
            
            if not include_hidden and any(part.startswith(".") for part in p.relative_to(root).parts):
                continue
            
            documents.append(p)
    
    return sorted(documents)


def compute_final_md_path(doc_path: Path, config) -> Path:
    directory_mode = config.get("output.directory_mode", "same")
    
    if directory_mode == "same":
        return doc_path.with_suffix(".md")
    elif directory_mode == "relative":
        relative_path = config.get("output.relative_path", "./converted")
        output_dir = doc_path.parent / relative_path
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{doc_path.stem}.md"
    elif directory_mode == "absolute":
        absolute_path = config.get("output.absolute_path", "")
        if absolute_path:
            output_dir = Path(absolute_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir / f"{doc_path.stem}.md"
        else:
            return doc_path.with_suffix(".md")
    else:
        return doc_path.with_suffix(".md")


def safe_stem(path: Path) -> str:
    s = path.stem
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, "_")
    s = s.strip() or "document"
    return s


def newest_md_in_dir(out_dir: Path) -> Optional[Path]:
    mds = list(out_dir.rglob("*.md"))
    if not mds:
        return None
    mds.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return mds[0]


def ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    suffix = " [y/N] " if default_no else " [Y/n] "
    while True:
        try:
            ans = input(prompt + suffix).strip().lower()
            if not ans:
                return not default_no
            if ans in {"y", "yes"}:
                return True
            if ans in {"n", "no"}:
                return False
            print("请输入 y/yes 或 n/no")
        except (EOFError, KeyboardInterrupt):
            print()
            return False


def run_one(
    doc_path: Path,
    root: Path,
    config,
    dry_run: bool,
    delete_manager: Optional[DeleteManager] = None,
) -> TaskResult:
    t0 = time.perf_counter()
    final_md = compute_final_md_path(doc_path, config)

    # 辅助函数：从嵌套字典获取值
    def get_nested(config_dict, key_path: str, default: Any = None) -> Any:
        """从嵌套字典中获取值，支持点分隔键路径"""
        keys = key_path.split('.')
        value = config_dict
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

    # 调试日志（已禁用）
    # print(f"[DEBUG] run_one开始:")
    # print(f"[DEBUG]   doc_path: {doc_path}")
    # print(f"[DEBUG]   final_md: {final_md}")
    # print(f"[DEBUG]   final_md.exists(): {final_md.exists()}")
    # print(f"[DEBUG]   delete_manager: {delete_manager}")
    # if delete_manager:
    #     print(f"[DEBUG]   delete_manager.delete_source: {delete_manager.delete_source}")
    #     print(f"[DEBUG]   delete_manager.delete_mode: {delete_manager.delete_mode}")

    force = get_nested(config, "conversion.force", False)
    # print(f"[DEBUG]   force: {force}")
    if final_md.exists() and not force:
        # print(f"[DEBUG]   文件已存在，跳过转换")
        return TaskResult(doc_path, final_md, "skipped", time.perf_counter() - t0, "目标 Markdown 已存在，跳过（用 --force 覆盖）")
    
    # 转换前删除（如果配置要求）
    delete_before_msg = ""
    if delete_manager and delete_manager.delete_source:
        delete_mode = delete_manager.delete_mode
        print(f"[DEBUG]   检查转换前删除，模式: {delete_mode}")
        if delete_mode == "before_conversion":
            # 转换前删除
            print(f"[DEBUG]   执行转换前删除")
            delete_success, delete_msg = delete_manager.delete_source_file(
                doc_path, final_md, dry_run, user_confirmed=False
            )
            if delete_success:
                delete_before_msg = f", 转换前删除: {delete_msg}"
                print(f"[DEBUG]   转换前删除成功: {delete_msg}")
            else:
                # 如果转换前删除失败，可以继续尝试转换
                delete_before_msg = f", 转换前删除失败: {delete_msg}"
                print(f"[DEBUG]   转换前删除失败: {delete_msg}")

    base_out = root / "_marker_outputs"
    doc_out = base_out / f"{safe_stem(doc_path)}__{abs(hash(str(doc_path))) % 10**8}"
    if doc_out.exists() and force and not dry_run:
        shutil.rmtree(doc_out, ignore_errors=True)

    try:
        tool_name, cmd = build_converter_cmd(doc_path, doc_out)
    except ValueError as e:
        return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, str(e))

    if dry_run:
        return TaskResult(doc_path, final_md, "skipped", time.perf_counter() - t0, "dry-run：未执行", cmd=cmd)

    doc_out.mkdir(parents=True, exist_ok=True)

    timeout = config.get("performance.timeout", 0)
    timeout = None if timeout <= 0 else timeout
    verbose_cmd = config.get("conversion.verbose_cmd", False)
    
    try:
        if '>' in ' '.join(cmd):
            proc = subprocess.run(
                ' '.join(cmd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        else:
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

        suffix = doc_path.suffix.lower()
        if tool_name == "pdftotext":
            produced_file = doc_out / f"{doc_path.stem}.txt"
            if not produced_file.exists():
                produced_file = next(doc_out.rglob("*.txt"), None)
        elif tool_name in ["antiword", "catdoc"]:
            produced_file = doc_out / f"{doc_path.stem}.txt"
            if not produced_file.exists():
                produced_file = next(doc_out.rglob("*.txt"), None)
            
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
            return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, msg, cmd=cmd)

        # 复制到最终位置
        if produced_file != final_md:
            shutil.copy2(produced_file, final_md)
        
        # 转换后删除（如果配置要求且不是转换前删除模式）
        delete_after_msg = ""
        if delete_manager and delete_manager.delete_source:
            delete_mode = delete_manager.delete_mode
            print(f"[DEBUG]   检查转换后删除，模式: {delete_mode}")
            if delete_mode == "after_conversion":
                # 转换后删除
                print(f"[DEBUG]   执行转换后删除")
                delete_success, delete_msg = delete_manager.delete_source_file(
                    doc_path, final_md, dry_run, user_confirmed=False
                )
                if delete_success:
                    delete_after_msg = f", 转换后删除: {delete_msg}"
                    print(f"[DEBUG]   转换后删除成功: {delete_msg}")
                else:
                    delete_after_msg = f", 转换后删除失败: {delete_msg}"
                    print(f"[DEBUG]   转换后删除失败: {delete_msg}")
        
        # 清理临时输出目录（如果配置要求）
        keep_outputs = config.get("conversion.keep_outputs", False)
        if not keep_outputs and doc_out.exists() and not dry_run:
            shutil.rmtree(doc_out, ignore_errors=True)
        
        delete_msg = delete_before_msg + delete_after_msg
        return TaskResult(doc_path, final_md, "ok", time.perf_counter() - t0, 
                         f"转换成功{delete_msg}", cmd=cmd)
        
    except subprocess.TimeoutExpired:
        return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, 
                         f"{tool_name} 超时（{timeout}秒）", cmd=cmd)
    except Exception as e:
        return TaskResult(doc_path, final_md, "failed", time.perf_counter() - t0, 
                         f"执行异常: {e}", cmd=cmd)




def main() -> None:
    # 使用配置管理器的参数解析器
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # 加载配置
    config_mgr = ConfigManager(args.config)
    config_mgr.update_from_args(args)
    
    # 处理互斥参数
    if hasattr(args, 'no_ask_delete') and args.no_ask_delete:
        config_mgr.config["file_handling"]["ask_before_delete"] = False
    
    # 验证配置
    errors = config_mgr.validate()
    if errors:
        print(red("配置错误:"))
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    # 显示配置摘要
    if args.show_config:
        config_mgr.print_summary()
        sys.exit(0)
    
    # 检查转换工具
    file_types = config_mgr.get("file_types", ["pdf", "docx"])
    try:
        ensure_converter_exists(file_types)
    except RuntimeError as e:
        print(red("[FATAL]"), str(e))
        sys.exit(1)
    
    # 获取配置
    config = config_mgr.config
    root = Path.cwd()
    
    # 创建DeleteManager实例
    delete_manager = None
    if config["file_handling"]["delete_source"]:
        delete_manager = DeleteManager(config)
        print(f"删除功能已启用 - 模式: {config['file_handling']['delete_mode']}")
        if config["file_handling"]["backup_enabled"]:
            print(f"备份功能已启用 - 目录: {config['file_handling']['backup_dir']}")
        if config["file_handling"]["use_trash"]:
            print("将使用系统回收站（如果可用）")
    
    # 查找文档
    include_types = config["file_types"]
    include_hidden = config["conversion"]["include_hidden"]
    exclude_dirs = config["file_handling"]["exclude_dirs"]
    
    documents = find_documents(root, include_types, include_hidden, exclude_dirs)
    
    if not documents:
        print(yellow("未找到任何"), ", ".join(include_types), yellow("文件。"))
        print("当前目录:", root)
        sys.exit(0)
    
    # 显示计划
    dry_run = args.dry_run
    workers = config["performance"]["workers"]
    if workers <= 0:
        workers = min(len(documents), os.cpu_count() or 4)
    
    print(bold("文档批量转换 → Markdown"))
    print(f"根目录: {root}")
    print(f"文件类型: {', '.join(include_types)}")
    print(f"文件数: {len(documents)} | workers={workers} | force={config['conversion']['force']} | dry_run={dry_run}")
    print("-" * 72)
    
    # 执行转换
    results: List[TaskResult] = []
    start_time = time.perf_counter()
    
    if workers == 1 or dry_run:
        # 单线程执行（用于dry-run或调试）
        for i, doc_path in enumerate(documents, 1):
            result = run_one(doc_path, root, config, dry_run, delete_manager)
            results.append(result)
            
            # 显示进度
            status_color = {
                "ok": green("OK"),
                "skipped": yellow("SKIP"),
                "failed": red("FAIL")
            }.get(result.status, result.status)
            
            print(f"[{i:4d}/{len(documents)}] {status_color:6} {doc_path.relative_to(root)}  {result.message}")
            if result.cmd and config["conversion"]["verbose_cmd"]:
                cmd_str = shlex.join(result.cmd) if not '>' in ' '.join(result.cmd) else ' '.join(result.cmd)
                print(f"           cmd: {cmd_str}")
    else:
        # 多线程执行
        with cf.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_doc = {
                executor.submit(run_one, doc_path, root, config, dry_run, delete_manager): doc_path
                for doc_path in documents
            }
            
            completed = 0
            for future in cf.as_completed(future_to_doc):
                completed += 1
                result = future.result()
                results.append(result)
                
                # 显示进度
                status_color = {
                    "ok": green("OK"),
                    "skipped": yellow("SKIP"),
                    "failed": red("FAIL")
                }.get(result.status, result.status)
                
                print(f"[{completed:4d}/{len(documents)}] {status_color:6} {result.doc_path.relative_to(root)}  {result.message}")
                if result.cmd and config["conversion"]["verbose_cmd"]:
                    cmd_str = shlex.join(result.cmd) if not '>' in ' '.join(result.cmd) else ' '.join(result.cmd)
                    print(f"           cmd: {cmd_str}")
    
    # 统计结果
    total_time = time.perf_counter() - start_time
    ok_count = sum(1 for r in results if r.status == "ok")
    skip_count = sum(1 for r in results if r.status == "skipped")
    fail_count = sum(1 for r in results if r.status == "failed")
    
    print("-" * 72)
    print(bold("总结"))
    print(f"总计:   {len(documents)}")
    print(f"成功:   {ok_count}")
    print(f"跳过:   {skip_count}")
    print(f"失败:   {fail_count}")
    print(f"耗时:   {total_time:.2f}s")
    
    # 清理临时目录（如果配置要求且不是dry-run）
    if not dry_run and not config["conversion"]["keep_outputs"]:
        base_out = root / "_marker_outputs"
        if base_out.exists():
            shutil.rmtree(base_out, ignore_errors=True)
    
    # 显示删除摘要
    if delete_manager:
        delete_manager.print_summary()
    
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
