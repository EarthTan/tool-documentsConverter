# xlsx_to_csv 详细说明

## 功能
- 递归搜索 XLSX 文件
- 每个工作表输出一个 CSV
- 可指定单个工作表
- 支持并发、dry-run、跳过已存在
- 可指定输出目录

## 基本用法
- 默认转换：python xlsx_to_csv/main.py
- 指定搜索根目录：python xlsx_to_csv/main.py --root /path/to/dir
- 指定输出目录：python xlsx_to_csv/main.py --output-dir ./converted
- 只导出指定工作表：python xlsx_to_csv/main.py --sheet "Sheet1"
- 强制重建：python xlsx_to_csv/main.py --force
- 预览计划：python xlsx_to_csv/main.py --dry-run

## 常用参数
- --workers N
- --include-hidden
- --exclude 目录名列表

## 输出规则
- 单个工作表：<stem>.csv
- 多个工作表：<stem>__<sheet>.csv

## 依赖
- openpyxl
