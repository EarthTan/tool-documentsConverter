#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
删除管理器模块
专门处理源文件的删除操作，支持多种删除策略和安全措施
"""

import os
import sys
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import subprocess


class DeleteManager:
    """删除管理器，负责安全地删除源文件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化删除管理器
        
        参数:
            config: 配置字典
        """
        self.config = config
        self.deleted_files: List[Path] = []
        self.failed_deletes: List[Tuple[Path, str]] = []
        
        # 辅助函数：从嵌套字典获取值
        def get_nested(config_dict: Dict[str, Any], key_path: str, default: Any = None) -> Any:
            """从嵌套字典中获取值，支持点分隔键路径"""
            keys = key_path.split('.')
            value = config_dict
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
        
        # 获取删除相关配置
        self.delete_source = get_nested(config, "file_handling.delete_source", False)
        self.delete_mode = get_nested(config, "file_handling.delete_mode", "after_conversion")
        self.ask_before_delete = get_nested(config, "file_handling.ask_before_delete", True)
        self.batch_confirmation = get_nested(config, "file_handling.batch_confirmation", "interactive")
        self.backup_enabled = get_nested(config, "file_handling.backup_enabled", False)
        backup_dir_str = get_nested(config, "file_handling.backup_dir", "./backup")
        self.backup_dir = Path(backup_dir_str)
        self.use_trash = get_nested(config, "file_handling.use_trash", True)
        self.verify_before_delete = get_nested(config, "file_handling.verify_before_delete", True)
        
        # 调试日志：显示配置（已禁用）
        # print(f"[DEBUG] DeleteManager配置:")
        # print(f"[DEBUG]   delete_source: {self.delete_source}")
        # print(f"[DEBUG]   delete_mode: {self.delete_mode}")
        # print(f"[DEBUG]   ask_before_delete: {self.ask_before_delete}")
        # print(f"[DEBUG]   batch_confirmation: {self.batch_confirmation}")
        # print(f"[DEBUG]   verify_before_delete: {self.verify_before_delete}")
        
        # 确保备份目录存在
        if self.backup_enabled:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def should_delete(self, doc_path: Path, md_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
        """
        判断是否应该删除源文件
        
        参数:
            doc_path: 源文档路径
            md_path: 生成的Markdown文件路径
            dry_run: 是否为dry-run模式
            
        返回:
            (should_delete, reason)
        """
        if not self.delete_source:
            return False, "删除功能未启用"
        
        # 检查删除模式
        if self.delete_mode == "before_conversion":
            # 转换前删除，需要确保目标文件不存在或可以覆盖
            return True, "转换前删除模式"
        elif self.delete_mode == "after_conversion":
            # 转换后删除，需要验证转换结果
            if not md_path.exists():
                return False, "目标Markdown文件不存在"
            
            if self.verify_before_delete:
                # 验证文件有效性
                if not self._verify_conversion(doc_path, md_path):
                    return False, "转换结果验证失败"
            
            return True, "转换后删除模式"
        else:
            return False, f"未知的删除模式: {self.delete_mode}"
    
    def _verify_conversion(self, doc_path: Path, md_path: Path) -> bool:
        """
        验证转换结果的有效性
        
        参数:
            doc_path: 源文档路径
            md_path: 生成的Markdown文件路径
            
        返回:
            bool: 转换是否有效
        """
        try:
            # 检查文件是否存在且不为空
            if not md_path.exists():
                return False
            
            # 检查文件大小
            if md_path.stat().st_size == 0:
                return False
            
            # 检查文件内容（简单验证）
            with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024)  # 读取前1KB
                if not content.strip():
                    return False
            
            return True
        except Exception:
            return False
    
    def ask_user_confirmation(self, doc_path: Path, is_batch: bool = False) -> bool:
        """
        询问用户是否删除文件
        
        参数:
            doc_path: 要删除的文件路径
            is_batch: 是否为批量确认模式
            
        返回:
            bool: 是否删除
        """
        if not self.ask_before_delete:
            return True
        
        if self.batch_confirmation == "yes_all":
            return True
        elif self.batch_confirmation == "no_all":
            return False
        
        # 交互式确认
        try:
            from .main import ask_yes_no
            return ask_yes_no(f"删除源文件? {doc_path}", default_no=True)
        except ImportError:
            # 如果无法导入，使用简单的输入
            try:
                response = input(f"删除源文件? {doc_path} [y/N]: ").strip().lower()
                return response in ['y', 'yes']
            except (EOFError, KeyboardInterrupt):
                return False
    
    def backup_file(self, doc_path: Path) -> Optional[Path]:
        """
        备份文件到备份目录
        
        参数:
            doc_path: 要备份的文件路径
            
        返回:
            Optional[Path]: 备份文件路径，如果备份失败则返回None
        """
        if not self.backup_enabled:
            return None
        
        try:
            # 创建唯一的备份文件名
            timestamp = int(time.time())
            backup_name = f"{doc_path.stem}_{timestamp}{doc_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # 复制文件
            shutil.copy2(doc_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"备份失败 {doc_path}: {e}")
            return None
    
    def move_to_trash(self, doc_path: Path) -> bool:
        """
        将文件移动到系统回收站（如果支持）
        
        参数:
            doc_path: 要删除的文件路径
            
        返回:
            bool: 是否成功
        """
        if not self.use_trash:
            return False
        
        try:
            # macOS: 使用osascript移动文件到回收站
            if sys.platform == 'darwin':
                script = f'''
                tell application "Finder"
                    set theFile to POSIX file "{doc_path}" as alias
                    delete theFile
                end tell
                '''
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            
            # Linux: 使用gio或trash-cli
            elif sys.platform.startswith('linux'):
                # 尝试使用gio
                if shutil.which('gio'):
                    result = subprocess.run(['gio', 'trash', str(doc_path)], 
                                          capture_output=True, text=True)
                    return result.returncode == 0
                # 尝试使用trash-cli
                elif shutil.which('trash'):
                    result = subprocess.run(['trash', str(doc_path)], 
                                          capture_output=True, text=True)
                    return result.returncode == 0
            
            # Windows: 使用Send2Trash库（需要安装）
            elif sys.platform == 'win32':
                try:
                    import send2trash
                    send2trash.send2trash(str(doc_path))
                    return True
                except ImportError:
                    pass
            
            return False
        except Exception as e:
            print(f"移动到回收站失败 {doc_path}: {e}")
            return False
    
    def delete_file(self, doc_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
        """
        安全地删除文件
        
        参数:
            doc_path: 要删除的文件路径
            dry_run: 是否为dry-run模式
            
        返回:
            (success, message)
        """
        if dry_run:
            return True, "DRY-RUN: 将删除源文件"
        
        try:
            # 1. 备份文件（如果启用）
            backup_path = None
            if self.backup_enabled:
                backup_path = self.backup_file(doc_path)
                if backup_path:
                    print(f"已备份到: {backup_path}")
            
            # 2. 尝试移动到回收站（如果启用）
            if self.use_trash and self.move_to_trash(doc_path):
                self.deleted_files.append(doc_path)
                return True, "已移动到回收站"
            
            # 3. 直接删除
            doc_path.unlink()
            self.deleted_files.append(doc_path)
            
            message = "已删除源文件"
            if backup_path:
                message += f"（已备份到: {backup_path}）"
            
            return True, message
            
        except Exception as e:
            error_msg = f"删除失败: {e}"
            self.failed_deletes.append((doc_path, error_msg))
            return False, error_msg
    
    def delete_source_file(self, doc_path: Path, md_path: Path, 
                          dry_run: bool = False, user_confirmed: bool = False) -> Tuple[bool, str]:
        """
        删除源文件的主要入口点
        
        参数:
            doc_path: 源文档路径
            md_path: 生成的Markdown文件路径
            dry_run: 是否为dry-run模式
            user_confirmed: 用户是否已确认删除
            
        返回:
            (success, message)
        """
        # 检查是否应该删除
        should_delete, reason = self.should_delete(doc_path, md_path, dry_run)
        if not should_delete:
            return False, reason
        
        # 获取用户确认
        if not user_confirmed and not self.ask_user_confirmation(doc_path):
            return False, "用户取消删除"
        
        # 执行删除
        return self.delete_file(doc_path, dry_run)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取删除操作摘要
        
        返回:
            删除统计信息
        """
        return {
            "total_deleted": len(self.deleted_files),
            "total_failed": len(self.failed_deletes),
            "deleted_files": [str(p) for p in self.deleted_files],
            "failed_deletes": [(str(p), msg) for p, msg in self.failed_deletes]
        }
    
    def print_summary(self) -> None:
        """打印删除摘要"""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("删除操作摘要")
        print("=" * 60)
        print(f"成功删除: {summary['total_deleted']} 个文件")
        print(f"删除失败: {summary['total_failed']} 个文件")
        
        if summary['failed_deletes']:
            print("\n删除失败的文件:")
            for file_path, error_msg in summary['failed_deletes']:
                print(f"  - {file_path}: {error_msg}")
        
        if summary['deleted_files']:
            print("\n已删除的文件:")
            for file_path in summary['deleted_files'][:10]:  # 只显示前10个
                print(f"  - {file_path}")
            if len(summary['deleted_files']) > 10:
                print(f"  ... 还有 {len(summary['deleted_files']) - 10} 个文件")


if __name__ == "__main__":
    # 测试代码
    test_config = {
        "file_handling": {
            "delete_source": True,
            "delete_mode": "after_conversion",
            "ask_before_delete": True,
            "batch_confirmation": "interactive",
            "backup_enabled": False,
            "backup_dir": "./backup",
            "use_trash": True,
            "verify_before_delete": True
        }
    }
    
    manager = DeleteManager(test_config)
    print("DeleteManager 测试完成")