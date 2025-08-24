"""
统一的错误输出系统
支持颜色输出、严格的错误级别管理

NOTE: 重试逻辑已移至Universal_LLM_Handler，这里只保留颜色输出功能
"""


class PipelineErrorHandler:
    """统一的Pipeline错误处理器 - 专注于颜色输出"""
    
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


# 保留这个类是因为LLM.py还在使用，但建议未来迁移到Universal_LLM_Handler
class RetryHandler:
    """
    DEPRECATED: 重试处理器 - 建议使用Universal_LLM_Handler的重试机制
    保留此类是为了向后兼容，但将来会被移除
    """
    
    def __init__(self, max_retries: int = 10, delay_between_retries: float = 1.0):
        self.max_retries = max_retries
        self.delay_between_retries = delay_between_retries
        PipelineErrorHandler.warning(
            "RetryHandler is deprecated, consider using Universal_LLM_Handler", 
            "DEPRECATION"
        )
    
    def retry_with_warnings(self, func, component: str, operation_name: str, *args, **kwargs):
        """
        DEPRECATED: 建议使用Universal_LLM_Handler的重试机制
        """
        import time
        
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
                        f"{operation_name} failed on attempt {attempt}/{self.max_retries} (Error length: {len(str(e))} chars): {str(e)}", 
                        component
                    )
                    time.sleep(self.delay_between_retries)
                else:
                    # 最后一次尝试失败
                    PipelineErrorHandler.error(
                        f"{operation_name} failed after {self.max_retries} attempts. Last error: {str(e)}", 
                        component
                    )
    
    def _is_valid_result(self, result) -> bool:
        """检查结果是否有效"""
        if result is None:
            return False
        if isinstance(result, dict) and 'error' in result and result['error']:
            return False
        return True


# 全局实例
error_handler = PipelineErrorHandler()