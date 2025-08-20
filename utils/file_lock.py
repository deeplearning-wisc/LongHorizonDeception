# utils/file_lock.py
# 文件锁机制，确保JSON写入完成后detector才能读取

import os
import time
import json
from pathlib import Path
from typing import Dict, Any
from contextlib import contextmanager

class JSONFileLock:
    """专门用于JSON文件读写的锁机制"""
    
    def __init__(self, json_file_path: str):
        self.json_file = Path(json_file_path)
        self.lock_file = Path(str(json_file_path) + ".lock")
        
    @contextmanager
    def write_lock(self, timeout: float = 10.0):
        """获取写锁的上下文管理器"""
        start_time = time.time()
        
        # 获取写锁
        while time.time() - start_time < timeout:
            try:
                # 创建锁文件
                with open(self.lock_file, 'x') as f:
                    f.write(f"WRITE_LOCK:{os.getpid()}:{time.time()}")
                break
            except FileExistsError:
                time.sleep(0.1)
        else:
            raise TimeoutError(f"Cannot acquire write lock for {self.json_file}")
            
        print(f"[JSON] Write lock acquired for {self.json_file.name}")
        
        try:
            # 提供写入器
            class JSONWriter:
                def __init__(self, file_path):
                    self.file_path = file_path
                    
                def write(self, data: Dict[str, Any]):
                    # 原子性写入：先写临时文件，再重命名
                    temp_file = Path(str(self.file_path) + ".tmp")
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    temp_file.replace(self.file_path)
                    
            yield JSONWriter(self.json_file)
            
        finally:
            # 释放写锁
            self.lock_file.unlink(missing_ok=True)
            print(f"[JSON] Write lock released for {self.json_file.name} - Data ready for detector")
    
    @contextmanager  
    def read_lock(self, timeout: float = 10.0):
        """获取读锁的上下文管理器"""
        start_time = time.time()
        
        # 等待写锁释放
        while time.time() - start_time < timeout:
            if not self.lock_file.exists():
                break
            time.sleep(0.1)
        else:
            raise TimeoutError(f"Cannot acquire read lock for {self.json_file}")
            
        print(f"[DETECTOR] Read lock acquired for {self.json_file.name}")
        
        try:
            if self.json_file.exists():
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            yield data
        finally:
            print(f"[DETECTOR] Read lock released for {self.json_file.name}")