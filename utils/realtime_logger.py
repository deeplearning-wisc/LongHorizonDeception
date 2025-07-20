#!/usr/bin/env python3
"""
实时Logger系统 - 和printstream完全一样，但log文件中完全展开无截断
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import threading

class RealtimeLogger:
    """
    实时Logger - 同时输出到console和文件
    - Console: 可能有截断（保持原有的用户体验）
    - Log文件: 完全展开，无截断，实时写入
    """
    
    def __init__(self, log_file_path: str, console_enabled: bool = True):
        """
        初始化Logger
        
        Args:
            log_file_path: log文件路径
            console_enabled: 是否同时输出到console
        """
        self.log_file_path = Path(log_file_path)
        self.console_enabled = console_enabled
        self._lock = threading.Lock()
        
        # 确保log目录存在
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 打开log文件（实时写入模式）
        self.log_file = open(self.log_file_path, 'w', encoding='utf-8', buffering=1)  # 行缓冲
        
        # 写入开始标记
        self._write_log_header()
    
    def _write_log_header(self):
        """写入log文件头信息"""
        header = f"""
================================================================================
LDLE Pipeline Real-time Log
Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Log File: {self.log_file_path}
================================================================================

"""
        self.log_file.write(header)
        self.log_file.flush()
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime('%H:%M:%S.%f')[:-3]  # 精确到毫秒
    
    def print(self, *args, sep: str = ' ', end: str = '\n', **kwargs):
        """
        替代print函数 - 同时输出到console和log文件
        
        Args:
            *args: print参数
            sep: 分隔符
            end: 结束符
            **kwargs: 其他参数
        """
        with self._lock:
            # 构建完整消息
            message = sep.join(str(arg) for arg in args) + end
            
            # 输出到console（原有逻辑，可能有截断）
            if self.console_enabled:
                print(*args, sep=sep, end=end, **kwargs)
            
            # 写入log文件（完全展开，无截断）
            timestamp = self._get_timestamp()
            log_line = f"[{timestamp}] {message}"
            self.log_file.write(log_line)
            self.log_file.flush()  # 立即刷新到磁盘
    
    def print_full(self, label: str, content: str, max_console_chars: int = 500):
        """
        打印长内容 - console显示截断版本，log显示完整版本
        
        Args:
            label: 内容标签
            content: 完整内容
            max_console_chars: console最大显示字符数
        """
        with self._lock:
            # Console显示截断版本（保持用户体验）
            if self.console_enabled:
                if len(content) > max_console_chars:
                    console_content = content[:max_console_chars] + f'... ({len(content)} total chars)'
                    print(f"{label}:\n{console_content}")
                else:
                    print(f"{label}:\n{content}")
            
            # Log文件显示完整版本
            timestamp = self._get_timestamp()
            log_content = f"[{timestamp}] {label} (FULL {len(content)} chars):\n{content}\n"
            self.log_file.write(log_content)
            self.log_file.flush()
    
    def section(self, title: str, width: int = 70):
        """打印分割线"""
        separator = "=" * width
        section_text = f"\n{separator}\n{title.center(width)}\n{separator}\n"
        self.print(section_text, end='')
    
    def subsection(self, title: str, width: int = 60):
        """打印子分割线"""
        separator = "-" * width  
        subsection_text = f"\n{separator}\n{title}\n{separator}\n"
        self.print(subsection_text, end='')
    
    def close(self):
        """关闭logger"""
        if hasattr(self, 'log_file') and not self.log_file.closed:
            # 写入结束标记
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            footer = f"\n\n================================================================================\nLog Ended: {end_time}\n================================================================================\n"
            self.log_file.write(footer)
            self.log_file.close()
    
    def __del__(self):
        """析构函数 - 确保文件关闭"""
        self.close()

# 全局logger实例
_global_logger: Optional[RealtimeLogger] = None

def init_logger(log_file_path: str, console_enabled: bool = True) -> RealtimeLogger:
    """
    初始化全局logger
    
    Args:
        log_file_path: log文件路径
        console_enabled: 是否启用console输出
        
    Returns:
        Logger实例
    """
    global _global_logger
    if _global_logger:
        _global_logger.close()
    
    _global_logger = RealtimeLogger(log_file_path, console_enabled)
    return _global_logger

def get_logger() -> Optional[RealtimeLogger]:
    """获取全局logger"""
    return _global_logger

def log_print(*args, **kwargs):
    """全局log打印函数"""
    if _global_logger:
        _global_logger.print(*args, **kwargs)
    else:
        print(*args, **kwargs)

def log_full(label: str, content: str, max_console_chars: int = 300):
    """
    Log full content to file, but truncate console output
    """
    if _global_logger:
        _global_logger.print_full(label, content, max_console_chars)
    else:
        # Fallback when no logger is set
        truncated = content[:max_console_chars] + "..." if len(content) > max_console_chars else content
        print(f"{label}: {truncated}")

def log_collapsed(label: str, content: str, preview_chars: int = 100, show_length: bool = True):
    """
    Log content with collapsible format - short preview on console, full content in log file
    """
    if _global_logger:
        # Show preview on console
        preview = content[:preview_chars] + "..." if len(content) > preview_chars else content
        length_info = f" ({len(content)} chars)" if show_length and len(content) > preview_chars else ""
        _global_logger.print(f"{label}{length_info}: {preview}")
        # Write full content to log file
        _global_logger.log_file.write(f"\n{label} (FULL CONTENT):\n{content}\n")
        _global_logger.log_file.flush()
    else:
        # Fallback when no logger is set
        preview = content[:preview_chars] + "..." if len(content) > preview_chars else content
        length_info = f" ({len(content)} chars)" if show_length and len(content) > preview_chars else ""
        print(f"{label}{length_info}: {preview}")

def log_manager_feedback(feedback: str):
    """
    Special logging for Manager feedback - always collapsed due to length
    """
    log_collapsed("[MANAGER TO AGENT]", feedback, preview_chars=150, show_length=True)

def log_section(title: str, width: int = 70):
    """全局log分割线函数"""
    if _global_logger:
        _global_logger.section(title, width)
    else:
        separator = "=" * width
        print(f"\n{separator}\n{title.center(width)}\n{separator}")

def log_subsection(title: str, width: int = 60):
    """全局log子分割线函数"""
    if _global_logger:
        _global_logger.subsection(title, width)
    else:
        separator = "-" * width
        print(f"\n{separator}\n{title}\n{separator}")

def close_logger():
    """关闭全局logger"""
    global _global_logger
    if _global_logger:
        _global_logger.close()
        _global_logger = None 