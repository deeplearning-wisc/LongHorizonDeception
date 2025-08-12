"""
统一的错误处理和重试系统
支持颜色输出、重试机制、严格的错误级别管理
"""

import time
import json
from typing import Callable, Any, Optional, Dict
from functools import wraps


class PipelineErrorHandler:
    """统一的Pipeline错误处理器"""
    
    @staticmethod
    def warning(msg: str, component: str = "SYSTEM") -> None:
        """黄色WARNING - 不终止pipeline"""
        print(f"\033[93m⚠️  [{component} WARNING] {msg}\033[0m")
    
    @staticmethod
    def error(msg: str, component: str = "SYSTEM") -> None:
        """红色ERROR - 立即终止pipeline"""
        print(f"\033[91m❌ [{component} ERROR] {msg}\033[0m")
        raise RuntimeError(f"Pipeline terminated: {msg}")
    
    @staticmethod
    def critical_error(msg: str, component: str = "SYSTEM") -> None:
        """红色CRITICAL ERROR - 系统级错误"""
        print(f"\033[91m💥 [{component} CRITICAL ERROR] {msg}\033[0m")
        raise RuntimeError(f"System failure: {msg}")
    
    @staticmethod
    def info(msg: str, component: str = "SYSTEM") -> None:
        """蓝色INFO - 信息提示"""
        print(f"\033[94m🔵 [{component} INFO] {msg}\033[0m")
    
    @staticmethod
    def success(msg: str, component: str = "SYSTEM") -> None:
        """绿色SUCCESS - 成功提示"""
        print(f"\033[92m✅ [{component} SUCCESS] {msg}\033[0m")


class RetryHandler:
    """重试处理器 - 专门处理LLM输出不稳定的问题"""
    
    def __init__(self, max_retries: int = 10, delay_between_retries: float = 1.0):
        self.max_retries = max_retries
        self.delay_between_retries = delay_between_retries
    
    def retry_with_warnings(self, func: Callable, component: str, 
                          operation_name: str, *args, **kwargs) -> Any:
        """
        重试机制 - 用于处理LLM输出格式问题
        
        Args:
            func: 要重试的函数
            component: 组件名称 (如 "JUDGE", "LLM")
            operation_name: 操作名称 (如 "JSON parsing", "response generation")
            
        Returns:
            函数执行结果
            
        Raises:
            RuntimeError: 超过最大重试次数后抛出
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # 检查结果是否有效
                if self._is_valid_result(result):
                    if attempt > 1:
                        PipelineErrorHandler.success(
                            f"{operation_name} succeeded on attempt {attempt}", 
                            component
                        )
                    return result
                else:
                    # 结果无效，当作一次失败
                    raise ValueError("Invalid result returned")
                    
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    PipelineErrorHandler.warning(
                        f"{operation_name} failed on attempt {attempt}/{self.max_retries}: {str(e)[:100]}...", 
                        component
                    )
                    time.sleep(self.delay_between_retries)
                else:
                    # 最后一次尝试失败
                    PipelineErrorHandler.error(
                        f"{operation_name} failed after {self.max_retries} attempts. Last error: {str(e)}", 
                        component
                    )
        
        # 不会到达这里，因为上面的error会抛异常
        
    def _is_valid_result(self, result: Any) -> bool:
        """检查结果是否有效"""
        if result is None:
            return False
        if isinstance(result, dict) and result.get('error'):
            return False
        return True


def retry_on_llm_failure(max_retries: int = 3, component: str = "LLM"):
    """
    装饰器：自动重试LLM相关的函数
    
    Args:
        max_retries: 最大重试次数
        component: 组件名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_retries=max_retries)
            return retry_handler.retry_with_warnings(
                func, component, func.__name__, *args, **kwargs
            )
        return wrapper
    return decorator


# 全局实例
error_handler = PipelineErrorHandler()
retry_handler = RetryHandler()