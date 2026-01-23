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
        # 首先获取默认配置
        default_config = self.get_default_config()
        
        if not self.config_path.exists():
            # 如果配置文件不存在，使用默认配置
            self.config = default_config
            # 创建默认配置文件
            self.save_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f) or {}
            
            # 深度合并配置：从默认配置开始，然后用加载的配置覆盖
            self.config = self._deep_merge(default_config, loaded_config)
        
        except Exception as e:
            print(f"警告: 无法加载配置文件 {self.config_path}: {e}")
            print("使用默认配置")
            self.config = default_config
    
    def _deep_merge(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典，override中的值覆盖default中的值"""
        result = default.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
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
                "delete_mode": "after_conversion",
                "ask_before_delete": True,
                "batch_confirmation": "interactive",
                "backup_enabled": False,
                "backup_dir": "./backup",
                "use_trash": True,
                "verify_before_delete": True,
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
        if hasattr(args, 'delete_mode') and args.delete_mode:
            self.config["file_handling"]["delete_mode"] = args.delete_mode
        # 对于布尔参数，只有当为True时才更新（避免将默认的True覆盖为False）
        if hasattr(args, 'ask_before_delete') and args.ask_before_delete:
            self.config["file_handling"]["ask_before_delete"] = True
        if hasattr(args, 'batch_confirm') and args.batch_confirm:
            self.config["file_handling"]["batch_confirmation"] = args.batch_confirm
        if hasattr(args, 'backup_dir') and args.backup_dir:
            self.config["file_handling"]["backup_dir"] = args.backup_dir
        if hasattr(args, 'backup_enabled') and args.backup_enabled:
            self.config["file_handling"]["backup_enabled"] = True
        if hasattr(args, 'use_trash') and args.use_trash:
            self.config["file_handling"]["use_trash"] = True
        if hasattr(args, 'no_trash'):
            self.config["file_handling"]["use_trash"] = False
        if hasattr(args, 'verify_before_delete') and args.verify_before_delete:
            self.config["file_handling"]["verify_before_delete"] = True
        if hasattr(args, 'no_verify_delete'):
            self.config["file_handling"]["verify_before_delete"] = False
        
        # 更新排除目录
        if hasattr(args, 'exclude') and args.exclude:
            self.config["file_handling"]["exclude_dirs"] = args.exclude
        
        # 处理互斥参数
        if hasattr(args, 'yes') and args.yes:
            self.config["file_handling"]["batch_confirmation"] = "yes_all"
            self.config["file_handling"]["ask_before_delete"] = False
        if hasattr(args, 'no') and args.no:
            self.config["file_handling"]["batch_confirmation"] = "no_all"
            self.config["file_handling"]["ask_before_delete"] = False
        if hasattr(args, 'no_ask_delete') and args.no_ask_delete:
            self.config["file_handling"]["ask_before_delete"] = False
    
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
        if directory_mode and directory_mode not in ["same", "relative", "absolute"]:
            errors.append(f"无效的输出目录模式: {directory_mode}")
        
        # 验证删除模式
        delete_mode = self.get("file_handling.delete_mode")
        if delete_mode and delete_mode not in ["before_conversion", "after_conversion"]:
            errors.append(f"无效的删除模式: {delete_mode}")
        
        # 验证批量确认模式
        batch_confirmation = self.get("file_handling.batch_confirmation")
        if batch_confirmation and batch_confirmation not in ["interactive", "yes_all", "no_all"]:
            errors.append(f"无效的批量确认模式: {batch_confirmation}")
        
        # 验证日志级别
        log_level = self.get("logging.level")
        if log_level and log_level not in ["debug", "info", "warning", "error"]:
            errors.append(f"无效的日志级别: {log_level}")
        
        return errors
    
    def print_summary(self) -> None:
        """打印配置摘要"""
        print("配置摘要:")
        print(f"  文件类型: {', '.join(self.get('file_types', []))}")
        print(f"  强制转换: {self.get('conversion.force', False)}")
        print(f"  删除源文件: {self.get('file_handling.delete_source', False)}")
        print(f"  删除模式: {self.get('file_handling.delete_mode', 'after_conversion')}")
        print(f"  交互式删除: {self.get('file_handling.ask_before_delete', True)}")
        print(f"  批量确认: {self.get('file_handling.batch_confirmation', 'interactive')}")
        print(f"  备份功能: {self.get('file_handling.backup_enabled', False)}")
        print(f"  使用回收站: {self.get('file_handling.use_trash', True)}")
        print(f"  删除前验证: {self.get('file_handling.verify_before_delete', True)}")
        print(f"  工作线程: {self.get('performance.workers', 0)}")
        print(f"  超时时间: {self.get('performance.timeout', 0)}秒")


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
  
删除选项示例:
  %(prog)s --delete-source --delete-mode before_conversion  # 转换前删除
  %(prog)s --delete-source --yes                           # 自动确认所有删除
  %(prog)s --delete-source --backup-dir ./backups          # 启用备份
  %(prog)s --delete-source --no-trash                      # 直接删除而不使用回收站
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
    
    # 文件处理选项 - 删除相关
    delete_group = parser.add_argument_group("删除选项")
    delete_group.add_argument("--delete-source", action="store_true", 
                            help="转换成功后删除源文件")
    delete_group.add_argument("--delete-mode", type=str, choices=["before_conversion", "after_conversion"],
                            help="删除模式：转换前删除（风险较高）或转换后删除（默认）")
    delete_group.add_argument("--ask-before-delete", action="store_true", 
                            help="交互式询问是否删除源文件（默认启用）")
    delete_group.add_argument("--no-ask-delete", action="store_true", 
                            help="禁用交互式询问删除源文件")
    delete_group.add_argument("--batch-confirm", type=str, choices=["interactive", "yes_all", "no_all"],
                            help="批量确认模式：interactive（交互式），yes_all（全部确认），no_all（全部拒绝）")
    delete_group.add_argument("--yes", action="store_true", 
                            help="自动确认所有删除操作（等同于 --batch-confirm yes_all）")
    delete_group.add_argument("--no", action="store_true", 
                            help="自动拒绝所有删除操作（等同于 --batch-confirm no_all）")
    
    # 文件处理选项 - 安全性
    safety_group = parser.add_argument_group("安全性选项")
    safety_group.add_argument("--backup-enabled", action="store_true", 
                            help="启用备份功能")
    safety_group.add_argument("--backup-dir", type=str, 
                            help="备份目录路径（默认：./backup）")
    safety_group.add_argument("--use-trash", action="store_true", 
                            help="使用系统回收站（如果可用）")
    safety_group.add_argument("--no-trash", action="store_true", 
                            help="直接删除而不使用回收站")
    safety_group.add_argument("--verify-before-delete", action="store_true", 
                            help="删除前验证转换结果（默认启用）")
    safety_group.add_argument("--no-verify-delete", action="store_true", 
                            help="禁用删除前验证")
    
    # 排除目录
    parser.add_argument("--exclude", nargs="*", help="要排除的目录名（覆盖配置文件设置）")
    
    # 其他选项
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不执行")
    parser.add_argument("--show-config", action="store_true", help="显示配置摘要后退出")
    parser.add_argument("--preview-delete", action="store_true", 
                       help="预览删除操作（显示将要删除的文件但不执行）")
    parser.add_argument("--delete-log", type=str, 
                       help="删除日志文件路径（记录所有删除操作）")
    
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