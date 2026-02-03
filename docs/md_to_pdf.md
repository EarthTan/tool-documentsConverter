# md_to_pdf 详细说明

## 功能
- 递归搜索 Markdown 文件
- 调用 md-to-pdf 批量转换
- 支持并发、dry-run、跳过已存在
- 可选删除源文件

## 基本用法
- 默认转换：python md_to_pdf/main.py
- 指定搜索根目录：python md_to_pdf/main.py --root /path/to/dir
- 强制重建：python md_to_pdf/main.py --force
- 预览计划：python md_to_pdf/main.py --dry-run

## 常用参数
- --workers N
- --delete-md
- --ask-delete
- --exclude 目录名列表

## 依赖
- md-to-pdf（npm 全局安装）
