"""
基础API提供商接口
定义所有LLM提供商必须实现的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from collections import namedtuple

# 统一的模型限制信息
ModelLimits = namedtuple('ModelLimits', ['context_window', 'max_output_tokens'])

class BaseLLMProvider(ABC):
    """所有LLM提供商的基础接口"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'total_tokens_used': 0
        }
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """初始化提供商特定的客户端和配置"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass
    
    @property
    @abstractmethod
    def model_limits(self) -> ModelLimits:
        """模型限制信息"""
        pass
    
    @abstractmethod
    def supports_temperature(self) -> bool:
        """是否支持temperature参数"""
        pass
    
    @abstractmethod
    def complete_chat(self, messages: List[Dict[str, str]], 
                     model: Optional[str] = None,
                     max_tokens: Optional[int] = None, 
                     temperature: Optional[float] = None,
                     system_role: Optional[str] = None, 
                     require_complete_response: bool = False) -> Dict[str, Any]:
        """
        聊天补全接口
        
        Returns:
            Dict包含: {
                'success': bool,
                'content': str,
                'finish_reason': str,
                'tokens_used': int,
                'error': str (如果失败)
            }
        """
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def _update_stats(self, success: bool, tokens_used: int = 0):
        """更新统计信息"""
        self.stats['total_calls'] += 1
        if success:
            self.stats['successful_calls'] += 1
            self.stats['total_tokens_used'] += tokens_used