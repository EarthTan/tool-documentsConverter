# doc_to_md 详细说明

## 功能
- PDF/DOCX/DOC 批量转 Markdown
- 递归扫描目录
- 支持 dry-run、并发、跳过已存在
- 支持多工具自动选择
- 支持配置文件与高级删除策略

## 基本用法
- 转换所有 PDF（默认）：python doc_to_md/main.py
- 转换所有支持类型：python doc_to_md/main.py --types all
- 转换指定类型：python doc_to_md/main.py --types pdf docx
- 预览计划：python doc_to_md/main.py --dry-run

## 常用参数
- --root（默认从项目根目录开始搜索）
- --types pdf docx doc all
- --force
- --workers N
- --timeout 秒
- --include-hidden
- --verbose-cmd
- --keep-outputs

## 输出与目录
- 默认输出到源文件同目录
- 可通过配置文件调整输出模式

## 删除功能
- 转换后删除（默认更安全）或转换前删除（风险更高）
- 支持交互确认、批量确认、备份、回收站、删除日志

## 配置文件
- 默认：doc_to_md/config.yaml
- 优先级：命令行参数 > 配置文件 > 默认值
- 查看配置摘要：python doc_to_md/main.py --show-config

## 参考
- 配置字段示例见 doc_to_md/config.yaml
