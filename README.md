# 文档批量转换工具集

这是一个文档批量转换工具集，包含两个独立的工具：
1. **文档转Markdown工具**：将PDF、DOCX、DOC文件批量转换为Markdown格式
2. **Markdown转PDF工具**：将Markdown文件批量转换为PDF格式

## 项目结构

```
tool/ (项目根目录)
├── doc_to_md/          # 文档转Markdown工具
│   ├── main.py         # 主脚本
│   ├── pdf_converter.py # PDF转换模块
│   └── docx_converter.py # Word文档转换模块
├── md_to_pdf/          # Markdown转PDF工具
│   └── main.py         # 主脚本
├── README.md           # 本说明文件
└── requirements.txt    # Python依赖
```

**重要**：两个工具都会从**项目根目录**开始递归搜索文件，而不是从工具所在目录。这样您可以将要处理的文件直接放在项目根目录下，工具放在子目录中。

## 功能特性

### 文档转Markdown工具 (doc_to_md/)
- 支持多种文件格式：PDF、DOCX、DOC
- 递归搜索项目根目录中的文档文件
- 并行处理提高转换速度
- 智能跳过已转换的文件
- 支持多种转换工具（自动选择最佳可用工具）
- 彩色输出和详细日志
- 支持dry-run模式预览转换计划

### Markdown转PDF工具 (md_to_pdf/)
- 递归搜索项目根目录中的Markdown文件
- 使用md-to-pdf工具进行转换
- 支持批量转换和并行处理
- 可选的源文件删除功能（自动或交互式）
- 排除特定目录（如.git、node_modules等）
- 彩色输出和进度显示

## 安装依赖

### 基本Python依赖
```bash
pip install pdfminer.six
```

### PDF转Markdown工具（至少安装一个）
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

### Markdown转PDF工具
```bash
# 需要安装md-to-pdf
npm install -g md-to-pdf
```

## 使用方法

### 文档转Markdown工具
```bash
# 进入项目根目录
cd /path/to/tool

# 转换所有PDF文件（默认）
python doc_to_md/main.py

# 转换所有支持的文件类型
python doc_to_md/main.py --types all

# 转换PDF和DOCX文件
python doc_to_md/main.py --types pdf docx

# 强制重新转换所有文件（覆盖已存在的Markdown文件）
python doc_to_md/main.py --force

# 只显示转换计划，不实际执行
python doc_to_md/main.py --dry-run

# 指定并发工作线程数
python doc_to_md/main.py --workers 4

# 设置单文件超时时间（秒）
python doc_to_md/main.py --timeout 30

# 包含隐藏文件/目录
python doc_to_md/main.py --include-hidden

# 显示详细命令信息
python doc_to_md/main.py --verbose-cmd

# 保留临时输出目录（用于调试）
python doc_to_md/main.py --keep-outputs
```

### Markdown转PDF工具
```bash
# 进入项目根目录
cd /path/to/tool

# 转换所有Markdown文件（默认从父目录开始搜索）
python md_to_pdf/main.py

# 指定搜索根目录
python md_to_pdf/main.py --root /path/to/dir

# 强制重新转换所有文件（覆盖已存在的PDF文件）
python md_to_pdf/main.py --force

# 转换成功后自动删除源Markdown文件
python md_to_pdf/main.py --delete-md

# 交互式询问是否删除源Markdown文件
python md_to_pdf/main.py --ask-delete

# 只显示转换计划，不实际执行
python md_to_pdf/main.py --dry-run

# 指定并发工作线程数
python md_to_pdf/main.py --workers 4

# 排除特定目录
python md_to_pdf/main.py --exclude .git node_modules dist
```

## 文件类型选项（文档转Markdown工具）
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

### 文档转Markdown工具
- 转换后的Markdown文件与原始文档在同一目录，扩展名改为`.md`
- 临时文件保存在`_marker_outputs/`目录（可使用`--keep-outputs`保留）
- 彩色输出显示转换状态：
  - 绿色：成功
  - 黄色：跳过（文件已存在）
  - 红色：失败

### Markdown转PDF工具
- 转换后的PDF文件与原始Markdown文件在同一目录，扩展名改为`.pdf`
- 彩色输出显示转换状态和进度

## 错误处理

- 如果缺少必要的转换工具，脚本会显示明确的错误信息和安装指南
- 转换失败的文件会显示详细错误信息
- 可以使用`--verbose-cmd`查看执行的命令以便调试

## 注意事项

1. 对于中文文档，确保系统支持UTF-8编码
2. 复杂的Word文档格式可能无法完美转换为Markdown
3. 扫描的PDF文件需要OCR工具支持，本脚本可能无法处理
4. 大文件可能需要较长的转换时间，建议使用`--timeout`参数
5. 两个工具都从项目根目录开始搜索文件，请将要处理的文件放在项目根目录下

## 向后兼容性

原始的`src/`目录中的脚本仍然可用，但建议使用新的目录结构。

## 许可证

本项目基于MIT许可证开源。