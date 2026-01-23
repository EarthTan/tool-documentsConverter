#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件管理模块
用于读取和解析doc_to_md工具的配置文件
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse


class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置管理器
        
        参数:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 默认配置文件路径：与脚本同目录下的config.yaml
            self.config_path = Path(__file__).parent / "config.yaml"
        else:
            self.config_path = Path(config_path)
        
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            # 如果配置文件不存在，使用默认配置
            self.config = self.get_default_config()
            # 创建默认配置文件
            self.save_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
            
            # 确保配置有所有必要的部分
            default_config = self.get_default_config()
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
                elif isinstance(value, dict) and isinstance(self.config[key], dict):
                    # 递归合并字典
                    self._merge_dicts(self.config[key], value)
        
        except Exception as e:
            print(f"警告: 无法加载配置文件 {self.config_path}: {e}")
            print("使用默认配置")
            self.config = self.get_default_config()
    
    def _merge_dicts(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """递归合并字典"""
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._merge_dicts(target[key], value)
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "file_types": ["pdf", "docx"],
            "conversion": {
                "force": False,
                "include_hidden": False,
                "keep_outputs": False,
                "verbose_cmd": False
            },
            "performance": {
                "workers": 0,  # 0表示自动检测
                "timeout": 0   # 0表示不设超时
            },
            "file_handling": {
                "delete_source": False,
                "ask_before_delete": True,
                "exclude_dirs": [
                    ".git", "node_modules", ".venv", "venv",
                    "dist", "build", "__pycache__", "_marker_outputs"
                ]
            },
            "output": {
                "directory_mode": "same",
                "relative_path": "./converted",
                "absolute_path": ""
            },
            "tool_priority": {
                "pdf": ["marker", "pdftotext", "pdfminer"],
                "docx": ["pandoc", "python-docx", "antiword", "catdoc"],
                "doc": ["antiword", "catdoc", "pandoc"]
            },
            "logging": {
                "level": "info",
                "color": True,
                "file": "",
                "show_progress": True
            }
        }
    
    def save_default_config(self) -> None:
        """保存默认配置文件"""
        try:
            default_config = self.get_default_config()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True, indent=2)
            print(f"已创建默认配置文件: {self.config_path}")
        except Exception as e:
            print(f"警告: 无法创建默认配置文件: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分隔的键路径"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def update_from_args(self, args: argparse.Namespace) -> None:
        """使用命令行参数更新配置"""
        # 更新文件类型
        if hasattr(args, 'types') and args.types:
            if "all" in args.types:
                self.config["file_types"] = ["pdf", "docx", "doc"]
            else:
                self.config["file_types"] = args.types
        
        # 更新转换选项
        if hasattr(args, 'force'):
            self.config["conversion"]["force"] = args.force
        if hasattr(args, 'include_hidden'):
            self.config["conversion"]["include_hidden"] = args.include_hidden
        if hasattr(args, 'keep_outputs'):
            self.config["conversion"]["keep_outputs"] = args.keep_outputs
        if hasattr(args, 'verbose_cmd'):
            self.config["conversion"]["verbose_cmd"] = args.verbose_cmd
        
        # 更新性能设置
        if hasattr(args, 'workers') and args.workers:
            self.config["performance"]["workers"] = args.workers
        if hasattr(args, 'timeout'):
            self.config["performance"]["timeout"] = args.timeout
        
        # 更新文件处理选项
        if hasattr(args, 'delete_source'):
            self.config["file_handling"]["delete_source"] = args.delete_source
        if hasattr(args, 'ask_before_delete'):
            self.config["file_handling"]["ask_before_delete"] = args.ask_before_delete
        
        # 更新排除目录
        if hasattr(args, 'exclude') and args.exclude:
            self.config["file_handling"]["exclude_dirs"] = args.exclude
    
    def validate(self) -> List[str]:
        """验证配置，返回错误消息列表"""
        errors = []
        
        # 验证文件类型
        file_types = self.get("file_types", [])
        valid_types = ["pdf", "docx", "doc", "all"]
        for ft in file_types:
            if ft not in valid_types:
                errors.append(f"无效的文件类型: {ft}")
        
        # 验证输出目录模式
        directory_mode = self.get("output.directory_mode")
        if directory_mode not in ["same", "relative", "absolute"]:
            errors.append(f"无效的输出目录模式: {directory_mode}")
        
        # 验证日志级别
        log_level = self.get("logging.level")
        if log_level not in ["debug", "info", "warning", "error"]:
            errors.append(f"无效的日志级别: {log_level}")
        
        return errors
    
    def print_summary(self) -> None:
        """打印配置摘要"""
        print("配置摘要:")
        print(f"  文件类型: {', '.join(self.get('file_types', []))}")
        print(f"  强制转换: {self.get('conversion.force')}")
        print(f"  删除源文件: {self.get('file_handling.delete_source')}")
        print(f"  交互式删除: {self.get('file_handling.ask_before_delete')}")
        print(f"  工作线程: {self.get('performance.workers')}")
        print(f"  超时时间: {self.get('performance.timeout')}秒")


def create_arg_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="递归将目录下所有文档（PDF、DOCX、DOC）转为 Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                         # 使用配置文件转换文档
  %(prog)s --config custom.yaml    # 使用自定义配置文件
  %(prog)s --types pdf docx        # 转换PDF和DOCX文件
  %(prog)s --types all             # 转换所有支持的文件类型
  %(prog)s --force                 # 强制重新转换所有文件
  %(prog)s --delete-source         # 转换成功后删除源文件
  %(prog)s --dry-run               # 只显示计划，不执行
        """
    )
    
    # 配置文件相关参数
    parser.add_argument("--config", type=str, help="配置文件路径（默认：doc_to_md/config.yaml）")
    
    # 文件类型参数
    parser.add_argument("--types", nargs="+", 
                       choices=["pdf", "docx", "doc", "all"],
                       help="要处理的文件类型（覆盖配置文件设置）")
    
    # 转换选项
    parser.add_argument("--force", action="store_true", help="即使目标 .md 已存在也强制重跑")
    parser.add_argument("--include-hidden", action="store_true", help="包含隐藏目录/文件（以 . 开头）")
    parser.add_argument("--verbose-cmd", action="store_true", help="日志里输出完整命令")
    parser.add_argument("--keep-outputs", action="store_true", help="保留 _marker_outputs/ 下的原始输出（便于调试）")
    
    # 性能设置
    parser.add_argument("--workers", type=int, help="并发线程数（0=自动检测，覆盖配置文件设置）")
    parser.add_argument("--timeout", type=int, default=0, help="单个文件超时秒数（0=不设超时）")
    
    # 文件处理选项
    parser.add_argument("--delete-source", action="store_true", help="转换成功后删除源文件")
    parser.add_argument("--ask-before-delete", action="store_true", 
                       help="交互式询问是否删除源文件（默认启用）")
    parser.add_argument("--no-ask-delete", action="store_true", 
                       help="禁用交互式询问删除源文件")
    parser.add_argument("--exclude", nargs="*", help="要排除的目录名（覆盖配置文件设置）")
    
    # 其他选项
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不执行")
    parser.add_argument("--show-config", action="store_true", help="显示配置摘要后退出")
    
    return parser


if __name__ == "__main__":
    # 测试配置管理器
    parser = create_arg_parser()
    args = parser.parse_args()
    
    config_mgr = ConfigManager(args.config)
    config_mgr.update_from_args(args)
    
    errors = config_mgr.validate()
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    config_mgr.print_summary()