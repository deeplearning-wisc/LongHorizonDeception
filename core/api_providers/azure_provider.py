"""
Azure OpenAI 专用提供商模块
处理Azure OpenAI的所有特性和个性化配置
"""

import os
from typing import Dict, Any, List, Optional
from .base_provider import BaseLLMProvider, ModelLimits

class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI 专用提供商"""
    
    @property
    def provider_name(self) -> str:
        return "azure"
    
    def _initialize(self):
        """初始化Azure OpenAI客户端"""
        from openai import AzureOpenAI
        
        # Azure特定配置
        self.api_key = self.config['azure_api_key']
        self.endpoint = self.config['azure_endpoint']
        self.deployment = self.config['azure_deployment']
        self.api_version = self.config['azure_api_version']
        self.model_name = self.config.get('model_name', 'gpt-4o')
        
        # Azure特定的模型版本支持
        self.model_version = self.config.get('model_version', '2024-11-20')
        
        # 初始化Azure客户端
        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version
        )
        
        # Azure模型限制配置
        self._configure_model_limits()
        
        print(f"[AZURE_PROVIDER] Initialized with model: {self.model_name} ({self.model_version})")
        print(f"[AZURE_PROVIDER] API Version: {self.api_version}")
    
    def _configure_model_limits(self):
        """配置Azure模型的限制信息"""
        # Azure GPT-4o 2024-11-20 规格
        if 'gpt-4o' in self.model_name:
            if self.model_version == '2024-11-20':
                self._model_limits = ModelLimits(128000, 16384)  # 最新版本
            elif self.model_version == '2024-08-06':
                self._model_limits = ModelLimits(128000, 16384)
            elif self.model_version == '2024-05-13':
                self._model_limits = ModelLimits(128000, 4096)   # 早期版本
            else:
                self._model_limits = ModelLimits(128000, 16384)  # 默认
        elif 'gpt-4o-mini' in self.model_name:
            self._model_limits = ModelLimits(128000, 16384)
        else:
            self._model_limits = ModelLimits(128000, 4096)  # 默认
    
    @property
    def model_limits(self) -> ModelLimits:
        return self._model_limits
    
    def supports_temperature(self) -> bool:
        """Azure OpenAI支持temperature参数"""
        return True
    
    def complete_chat(self, messages: List[Dict[str, str]], 
                     model: Optional[str] = None,
                     max_tokens: Optional[int] = None, 
                     temperature: Optional[float] = None,
                     system_role: Optional[str] = None, 
                     require_complete_response: bool = False) -> Dict[str, Any]:
        """Azure OpenAI聊天补全"""
        try:
            self.stats['total_calls'] += 1
            
            # 处理系统消息
            if system_role:
                messages = [{"role": "system", "content": system_role}] + messages
            
            # 构建请求参数
            call_params = {
                "model": self.deployment,  # Azure使用deployment名称
                "messages": messages,
                "max_tokens": max_tokens or self.model_limits.max_output_tokens
            }
            
            # Azure支持temperature
            if temperature is not None:
                call_params["temperature"] = temperature
            
            # Azure特有功能：结构化输出
            if self.api_version >= "2024-10-21":
                # 支持JSON模式和结构化输出
                pass
            
            print(f"[AZURE_PROVIDER] Calling Azure API:")
            print(f"  - Model: {self.model_name} {self.model_version}")
            print(f"  - Deployment: {self.deployment}")
            print(f"  - API Version: {self.api_version}")
            
            # API调用
            response = self.client.chat.completions.create(**call_params)
            
            # 处理响应
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            tokens_used = getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
            
            self._update_stats(True, tokens_used)
            
            return {
                'success': True,
                'content': content,
                'finish_reason': finish_reason,
                'tokens_used': tokens_used,
                'provider': 'azure',
                'model_version': self.model_version
            }
            
        except Exception as e:
            self._update_stats(False)
            error_msg = str(e)
            print(f"[AZURE_PROVIDER] Error: {error_msg}")
            
            return {
                'success': False,
                'content': '',
                'finish_reason': 'error',
                'tokens_used': 0,
                'error': error_msg,
                'provider': 'azure'
            }
    
    def estimate_tokens(self, text: str) -> int:
        """估算token数量 - Azure使用GPT-4标准"""
        # 简单估算：平均每个token约4个字符
        return len(text) // 4
    
    def get_azure_specific_info(self) -> Dict[str, Any]:
        """获取Azure特有的信息"""
        return {
            'deployment': self.deployment,
            'api_version': self.api_version,
            'model_version': self.model_version,
            'endpoint': self.endpoint,
            'supports_structured_output': self.api_version >= "2024-10-21"
        }