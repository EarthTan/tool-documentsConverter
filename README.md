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
- **配置文件支持**：使用YAML配置文件管理所有设置
- **灵活的配置优先级**：命令行参数 > 配置文件 > 默认值
- **高级删除功能**：支持多种删除模式和安全性选项
  - 两种删除模式：转换前删除（风险较高）或转换后删除（默认，更安全）
  - 批量确认模式：交互式、全部确认、全部拒绝
  - 备份功能：删除前自动备份源文件
  - 系统回收站：支持使用系统回收站（如果可用）
  - 删除前验证：验证转换结果后再删除源文件
- **输出目录配置**：支持多种输出目录模式（同目录、相对路径、绝对路径）

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

## Python依赖安装

项目使用requirements.txt管理Python依赖。安装所有依赖：

```bash
# 安装核心Python依赖
pip install -r requirements.txt
```

### requirements.txt内容说明

```txt
# 核心依赖（必须安装）
pdfminer.six>=20221105    # PDF转换库
python-docx>=1.1.0        # Word文档处理库
PyYAML>=6.0               # 配置文件解析库

# 可选依赖（增强功能）
# 这些工具通过系统包管理器安装，不是Python包
# - pandoc: 通用文档转换工具（推荐）
# - antiword: 针对.doc文件的工具
# - catdoc: 文本提取工具
# - marker: PDF转Markdown专用工具
# - pdftotext: 来自poppler工具集
```

### 依赖验证
安装后可以验证依赖是否齐全：
```bash
# 验证Python依赖
python -c "import pdfminer; import docx; import yaml; print('所有Python依赖已安装')"

# 验证外部工具
which pandoc || echo "pandoc未安装（可选）"
which antiword || echo "antiword未安装（可选）"
which catdoc || echo "catdoc未安装（可选）"
which marker || echo "marker未安装（可选）"
which pdftotext || echo "pdftotext未安装（可选）"
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

## 高级删除功能

doc_to_md工具提供了强大的删除功能，可以在转换成功后自动删除源文件，同时提供多种安全措施防止数据丢失。

### 删除模式
1. **转换后删除（默认）**：先转换文件，验证转换成功后再删除源文件。这是最安全的模式。
2. **转换前删除（风险较高）**：在转换前就删除源文件。仅当您有可靠备份时使用此模式。

### 批量确认模式
1. **交互式（默认）**：逐个文件询问是否删除
2. **全部确认**：自动确认所有删除操作
3. **全部拒绝**：自动拒绝所有删除操作

### 安全性功能
1. **备份功能**：删除前自动备份源文件到指定目录
2. **系统回收站**：使用系统回收站（如果可用），可以从回收站恢复文件
3. **删除前验证**：验证转换结果后再删除源文件，确保转换成功
4. **预览模式**：显示将要删除的文件但不实际执行删除操作
5. **删除日志**：记录所有删除操作到日志文件，便于审计

### 使用示例
```bash
# 基本删除功能
python doc_to_md/main.py --delete-source

# 使用转换前删除模式（风险较高）
python doc_to_md/main.py --delete-source --delete-mode before_conversion

# 自动确认所有删除
python doc_to_md/main.py --delete-source --yes

# 启用备份功能
python doc_to_md/main.py --delete-source --backup-enabled --backup-dir ./backups

# 使用系统回收站
python doc_to_md/main.py --delete-source --use-trash

# 预览删除操作（不实际执行）
python doc_to_md/main.py --delete-source --preview-delete

# 记录删除日志
python doc_to_md/main.py --delete-source --delete-log delete.log
```

### 安全建议
1. **首次使用**：先使用`--dry-run`和`--preview-delete`预览操作
2. **重要文件**：启用备份功能或使用系统回收站
3. **批量操作**：使用交互式模式或先测试少量文件
4. **定期检查**：检查删除日志确保操作符合预期

## 配置文件使用（文档转Markdown工具）

doc_to_md工具支持使用YAML配置文件来管理所有设置，使工具更加专业和用户友好。

### 配置文件位置
- 默认配置文件：`doc_to_md/config.yaml`
- 自定义配置文件：使用`--config`参数指定，如`--config custom.yaml`

### 配置优先级
配置按以下优先级应用（高优先级覆盖低优先级）：
1. **命令行参数**：最高优先级，直接覆盖其他配置
2. **配置文件**：中等优先级，覆盖默认值
3. **默认值**：最低优先级，当没有其他配置时使用

### 配置文件示例
```yaml
# doc_to_md 工具配置文件
# 配置文件优先级：命令行参数 > 配置文件 > 默认值

# 要处理的文件类型（支持：pdf, docx, doc）
# 可以使用 "all" 表示所有支持的类型
file_types:
  - pdf
  - docx

# 转换选项
conversion:
  # 是否强制重新转换已存在的文件
  force: false
  
  # 是否包含隐藏文件/目录
  include_hidden: false
  
  # 是否保留临时输出目录（用于调试）
  keep_outputs: false
  
  # 是否显示详细命令信息
  verbose_cmd: false

# 并发设置
performance:
  # 并发工作线程数（0表示自动检测）
  workers: 0
  
  # 单个文件超时时间（秒，0表示不设超时）
  timeout: 0

# 文件处理选项
file_handling:
  # 转换成功后是否删除源文件
  # 注意：此操作不可逆，请谨慎使用
  delete_source: false
  
  # 删除模式：
  # "before_conversion" - 转换前删除（风险较高）
  # "after_conversion" - 转换后删除（默认，更安全）
  delete_mode: "after_conversion"
  
  # 是否交互式询问删除源文件
  ask_before_delete: true
  
  # 批量确认模式：
  # "interactive" - 交互式逐个确认（默认）
  # "yes_all" - 自动确认所有删除
  # "no_all" - 自动拒绝所有删除
  batch_confirmation: "interactive"
  
  # 是否启用备份功能
  backup_enabled: false
  
  # 备份目录路径
  backup_dir: "./backup"
  
  # 是否使用系统回收站（如果可用）
  use_trash: true
  
  # 删除前是否验证转换结果
  verify_before_delete: true
  
  # 排除的目录名（任何位置）
  exclude_dirs:
    - .git
    - node_modules
    - .venv
    - venv
    - dist
    - build
    - __pycache__
    - _marker_outputs

# 输出设置
output:
  # 输出目录模式：
  # "same" - 与源文件同目录
  # "relative" - 相对于源文件的相对路径
  # "absolute" - 指定绝对路径
  directory_mode: "same"
  
  # 当 directory_mode 为 "relative" 时的相对路径
  relative_path: "./converted"
  
  # 当 directory_mode 为 "absolute" 时的绝对路径
  absolute_path: ""

# 工具优先级设置（按顺序尝试）
tool_priority:
  pdf:
    - marker
    - pdftotext
    - pdfminer
  
  docx:
    - pandoc
    - python-docx
    - antiword
    - catdoc
  
  doc:
    - antiword
    - catdoc
    - pandoc

# 日志设置
logging:
  # 日志级别：debug, info, warning, error
  level: "info"
  
  # 是否启用彩色输出
  color: true
  
  # 日志文件路径（空表示不保存到文件）
  file: ""
  
  # 是否在控制台显示进度
  show_progress: true
```

### 配置文件相关命令行参数
```bash
# 使用自定义配置文件
python doc_to_md/main.py --config custom.yaml

# 显示当前配置摘要后退出
python doc_to_md/main.py --show-config

# 删除源文件相关参数
python doc_to_md/main.py --delete-source          # 转换成功后删除源文件
python doc_to_md/main.py --delete-mode before_conversion  # 转换前删除（风险较高）
python doc_to_md/main.py --delete-mode after_conversion   # 转换后删除（默认，更安全）
python doc_to_md/main.py --ask-before-delete      # 交互式询问是否删除源文件
python doc_to_md/main.py --no-ask-delete          # 禁用交互式询问删除源文件
python doc_to_md/main.py --batch-confirm interactive  # 交互式逐个确认（默认）
python doc_to_md/main.py --batch-confirm yes_all  # 自动确认所有删除
python doc_to_md/main.py --batch-confirm no_all   # 自动拒绝所有删除
python doc_to_md/main.py --yes                    # 自动确认所有删除（等同于 --batch-confirm yes_all）
python doc_to_md/main.py --no                     # 自动拒绝所有删除（等同于 --batch-confirm no_all）

# 安全性参数
python doc_to_md/main.py --backup-enabled         # 启用备份功能
python doc_to_md/main.py --backup-dir ./backups   # 指定备份目录
python doc_to_md/main.py --use-trash              # 使用系统回收站（如果可用）
python doc_to_md/main.py --no-trash               # 直接删除而不使用回收站
python doc_to_md/main.py --verify-before-delete   # 删除前验证转换结果（默认启用）
python doc_to_md/main.py --no-verify-delete       # 禁用删除前验证

# 输出目录相关参数
python doc_to_md/main.py --exclude .git node_modules  # 排除特定目录

# 性能相关参数
python doc_to_md/main.py --workers 8              # 指定并发线程数
python doc_to_md/main.py --timeout 60             # 设置单文件超时时间

# 其他参数
python doc_to_md/main.py --preview-delete         # 预览删除操作（显示将要删除的文件但不执行）
python doc_to_md/main.py --delete-log delete.log  # 记录删除操作到日志文件
```

### 配置文件生成
首次运行工具时，如果配置文件不存在，会自动创建默认配置文件`doc_to_md/config.yaml`。您可以修改此文件来自定义工具行为。

### 配置验证
工具会自动验证配置文件的正确性，如果发现错误会显示明确的错误信息并退出。

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