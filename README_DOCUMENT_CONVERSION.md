# 文档批量转换工具

这是一个用于批量将PDF、DOCX和DOC文件转换为Markdown格式的Python脚本。

## 功能特性

- 支持多种文件格式：PDF、DOCX、DOC
- 递归搜索目录中的文档文件
- 并行处理提高转换速度
- 智能跳过已转换的文件
- 支持多种转换工具（自动选择最佳可用工具）
- 彩色输出和详细日志
- 支持dry-run模式预览转换计划

## 安装依赖

### 基本Python依赖
```bash
pip install pdfminer.six
```

### PDF转换工具（至少安装一个）
1. **marker**（推荐）：专门的PDF转Markdown工具
2. **pdftotext**：来自poppler工具集
3. **pdfminer.six**：Python库（已包含在基本依赖中）

### Word文档转换工具（至少安装一个）
1. **pandoc**（推荐）：通用文档转换工具
   ```bash
   # macOS
   brew install pandoc
   
   # Ubuntu/Debian
   sudo apt-get install pandoc
   ```
2. **python-docx**：Python库
   ```bash
   pip install python-docx
   ```
3. **antiword**：针对.doc文件的工具
   ```bash
   # macOS
   brew install antiword
   
   # Ubuntu/Debian
   sudo apt-get install antiword
   ```
4. **catdoc**：文本提取工具
   ```bash
   # macOS
   brew install catdoc
   
   # Ubuntu/Debian
   sudo apt-get install catdoc
   ```

## 使用方法

### 基本用法
```bash
# 转换所有PDF文件（默认）
python3 document_to_markdown.py

# 转换所有支持的文件类型
python3 document_to_markdown.py --types all

# 转换PDF和DOCX文件
python3 document_to_markdown.py --types pdf docx

# 强制重新转换所有文件（覆盖已存在的Markdown文件）
python3 document_to_markdown.py --force

# 只显示转换计划，不实际执行
python3 document_to_markdown.py --dry-run

# 指定并发工作线程数
python3 document_to_markdown.py --workers 4

# 设置单文件超时时间（秒）
python3 document_to_markdown.py --timeout 30

# 包含隐藏文件/目录
python3 document_to_markdown.py --include-hidden

# 显示详细命令信息
python3 document_to_markdown.py --verbose-cmd

# 保留临时输出目录（用于调试）
python3 document_to_markdown.py --keep-outputs
```

### 文件类型选项
- `--types pdf`：只处理PDF文件（默认）
- `--types docx`：只处理DOCX文件
- `--types doc`：只处理DOC文件
- `--types pdf docx`：处理PDF和DOCX文件
- `--types all`：处理所有支持的文件类型

## 工具优先级

### PDF转换优先级
1. marker（专门的PDF转Markdown工具）
2. pdftotext（poppler工具）
3. pdfminer.six（Python库）

### Word文档转换优先级
1. pandoc（通用文档转换工具）
2. python-docx（Python库）
3. antiword（针对.doc文件）
4. catdoc（文本提取工具）
5. 内置简单文本提取（最后手段）

## 输出说明

- 转换后的Markdown文件与原始文档在同一目录，扩展名改为`.md`
- 临时文件保存在`_marker_outputs/`目录（可使用`--keep-outputs`保留）
- 彩色输出显示转换状态：
  - 绿色：成功
  - 黄色：跳过（文件已存在）
  - 红色：失败

## 错误处理

- 如果缺少必要的转换工具，脚本会显示明确的错误信息和安装指南
- 转换失败的文件会显示详细错误信息
- 可以使用`--verbose-cmd`查看执行的命令以便调试

## 文件说明

- `document_to_markdown.py`：主脚本，支持PDF、DOCX、DOC转换
- `pdf_to_markdown.py`：原始PDF转换脚本（保持向后兼容）
- `docx_converter.py`：Word文档转换模块
- `pdf_converter.py`：PDF转换模块（后备方案）

## 向后兼容性

原始的`pdf_to_markdown.py`脚本仍然可用，功能不变。新的`document_to_markdown.py`脚本扩展了功能，支持更多文件类型。

## 注意事项

1. 对于中文文档，确保系统支持UTF-8编码
2. 复杂的Word文档格式可能无法完美转换为Markdown
3. 扫描的PDF文件需要OCR工具支持，本脚本可能无法处理
4. 大文件可能需要较长的转换时间，建议使用`--timeout`参数

## 许可证

本项目基于MIT许可证开源。