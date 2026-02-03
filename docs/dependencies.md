# 依赖与安装说明

## Python 依赖

使用 requirements.txt 安装：
- pdfminer.six
- python-docx
- PyYAML
- openpyxl

## 额外工具（按需）

### PDF 转 Markdown（至少安装一个）
- marker（推荐）
- pdftotext（poppler）
- pdfminer.six（已包含在 Python 依赖中）

### Word 文档转换（至少安装一个）
- pandoc（推荐）
- python-docx（已包含在 Python 依赖中）
- antiword（针对 .doc）
- catdoc（文本提取）

### Markdown 转 PDF
- md-to-pdf（npm 全局安装）

## 依赖验证（可选）

- Python 依赖可通过 import 检查
- 外部工具可用 which 检查
