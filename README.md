# 文档批量转换工具集

包含三个工具：
- 文档转Markdown（PDF/DOCX/DOC → MD）
- Markdown转PDF（MD → PDF）
- Excel转CSV（XLSX → CSV）

## 快速上手

1) 安装依赖
- Python 依赖：安装 [requirements.txt](requirements.txt)
- 额外工具：见详细文档

2) 运行（默认从项目根目录递归搜索文件）
- 文档转Markdown：python doc_to_md/main.py
- Markdown转PDF：python md_to_pdf/main.py
- Excel转CSV：python xlsx_to_csv/main.py

## 详细文档

- [doc_to_md 详细说明](docs/doc_to_md.md)
- [md_to_pdf 详细说明](docs/md_to_pdf.md)
- [xlsx_to_csv 详细说明](docs/xlsx_to_csv.md)
- [依赖与安装说明](docs/dependencies.md)
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