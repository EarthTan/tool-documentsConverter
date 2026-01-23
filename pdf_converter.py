#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单的PDF转换器模块
如果其他工具不可用，使用这个模块作为后备方案
"""

import os
import sys
from pathlib import Path
from typing import Optional

def convert_pdf_to_markdown(pdf_path: Path, out_dir: Path) -> None:
    """
    将PDF转换为Markdown的简单实现
    这是一个后备方案，实际应该使用专门的PDF转换工具
    """
    try:
        # 确保参数是Path对象
        pdf_path_obj = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        out_dir_obj = Path(out_dir) if isinstance(out_dir, str) else out_dir
        
        # 尝试使用pdfminer
        from pdfminer.high_level import extract_text
        
        text = extract_text(str(pdf_path_obj))
        
        # 创建Markdown文件
        md_file = out_dir_obj / f"{pdf_path_obj.stem}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {pdf_path_obj.stem}\n\n")
            f.write("```text\n")
            f.write(text)
            f.write("\n```\n")
            
        print(f"转换完成: {pdf_path_obj} -> {md_file}")
        
    except ImportError:
        # 如果pdfminer不可用，创建一个简单的文本文件
        print("警告: pdfminer 未安装，创建空文件")
        pdf_path_obj = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        out_dir_obj = Path(out_dir) if isinstance(out_dir, str) else out_dir
        md_file = out_dir_obj / f"{pdf_path_obj.stem}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {pdf_path_obj.stem}\n\n")
            f.write("PDF转换失败: 需要安装pdfminer.six库\n")
            f.write("请运行: pip install pdfminer.six\n")
    except Exception as e:
        print(f"PDF转换错误: {e}")
        # 创建错误文件
        pdf_path_obj = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        out_dir_obj = Path(out_dir) if isinstance(out_dir, str) else out_dir
        md_file = out_dir_obj / f"{pdf_path_obj.stem}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {pdf_path_obj.stem}\n\n")
            f.write(f"PDF转换错误: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python pdf_converter.py <pdf文件> <输出目录>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    
    if not pdf_path.exists():
        print(f"错误: PDF文件不存在: {pdf_path}")
        sys.exit(1)
    
    out_dir.mkdir(parents=True, exist_ok=True)
    convert_pdf_to_markdown(pdf_path, out_dir)