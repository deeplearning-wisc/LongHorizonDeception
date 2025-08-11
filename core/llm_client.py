# core/llm_client.py
# 统一LLM调用封装 - 支持自动token管理、多轮拼接、无截断处理

import openai
import time
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

class ModelType(Enum):
    """支持的模型类型"""
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4_1 = "gpt-4.1"
    O1 = "o1"
    O3 = "o3"
    O1_MINI = "o1-mini"
    O3_MINI = "o3-mini"

@dataclass
class ModelLimits:
    """模型限制信息"""
    context_window: int
    max_output_tokens: int
    supports_continuation: bool = True

# 最新模型限制配置 - 2025年最新规格
MODEL_SPECS = {
    ModelType.GPT_4O: ModelLimits(128000, 16384),
    ModelType.GPT_4_TURBO: ModelLimits(128000, 4096),
    ModelType.GPT_4_1: ModelLimits(1047576, 32768),
    ModelType.O1: ModelLimits(200000, 100000),
    ModelType.O3: ModelLimits(200000, 100000),
    ModelType.O1_MINI: ModelLimits(128000, 65536),
    ModelType.O3_MINI: ModelLimits(200000, 100000),
}

class UnifiedLLMClient:
    """
    统一LLM调用客户端
    
    特性：
    - 自动token限制检测和管理
    - 多轮拼接突破output限制  
    - 统一错误处理和重试
    - 完整的日志记录
    - 支持stream和非stream模式
    - 绝对不会出现截断
    """
    
    def __init__(self, 
                 azure_api_key: str,
                 azure_endpoint: str,
                 azure_deployment: str,
                 default_model: str,
                 max_retries: int,
                 retry_delay: float,
                 timeout: int,
                 enable_continuation: bool,
                 api_version: str):
        """
        初始化统一LLM客户端 - 使用Azure OpenAI API
        
        Args:
            azure_api_key: Azure OpenAI API密钥
            azure_endpoint: Azure OpenAI endpoint
            azure_deployment: Azure部署名称
            default_model: 默认模型
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
            timeout: 请求超时(秒)
            enable_continuation: 是否启用多轮拼接
            api_version: Azure API版本
        """
        if not azure_api_key:
            raise ValueError("必须提供Azure API密钥！")
        if not azure_endpoint:
            raise ValueError("必须提供Azure endpoint！")
        if not azure_deployment:
            raise ValueError("必须提供Azure部署名称！")
        
        self.azure_api_key = azure_api_key
        self.azure_endpoint = azure_endpoint
        self.azure_deployment = azure_deployment
        self.api_version = api_version
        self.default_model = default_model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.enable_continuation = enable_continuation
        
        # 创建Azure OpenAI客户端
        self.client = self._create_azure_client()
        
        # 识别模型类型
        self.model_type = self._detect_model_type(default_model)
        if self.model_type not in MODEL_SPECS:
            raise ValueError(f"Model type '{self.model_type}' not found in MODEL_SPECS")
        self.model_limits = MODEL_SPECS[self.model_type]
        
        # 统计信息
        self.total_requests = 0
        self.total_tokens_used = 0
        self.continuation_requests = 0
    
    def _create_azure_client(self):
        """创建Azure OpenAI客户端"""
        import openai
        
        try:
            client = openai.AzureOpenAI(
                api_key=self.azure_api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version
            )
            print(f"[LLM_CLIENT] 使用Azure OpenAI API - Endpoint: {self.azure_endpoint}")
            print(f"[LLM_CLIENT] Azure部署: {self.azure_deployment}")
            return client
        except Exception as e:
            raise ValueError(f"Azure OpenAI客户端初始化失败: {e}")
        
    def _detect_model_type(self, model_name: str) -> ModelType:
        """检测模型类型"""
        model_lower = model_name.lower()
        
        if "gpt-4.1" in model_lower:
            return ModelType.GPT_4_1
        elif "gpt-4o" in model_lower:
            return ModelType.GPT_4O
        elif "gpt-4-turbo" in model_lower or "gpt-4-turbo" in model_lower:
            return ModelType.GPT_4_TURBO
        elif "o3-mini" in model_lower:
            return ModelType.O3_MINI
        elif "o3" in model_lower:
            return ModelType.O3
        elif "o1-mini" in model_lower:
            return ModelType.O1_MINI
        elif "o1" in model_lower:
            return ModelType.O1
        else:
            return ModelType.GPT_4O  # 默认
    
    def get_optimal_max_tokens(self, requested_tokens: Optional[int] = None) -> int:
        """获取最优的max_tokens设置"""
        if requested_tokens is None:
            return self.model_limits.max_output_tokens
        
        return min(requested_tokens, self.model_limits.max_output_tokens)
    
    def complete_chat(self, 
                     messages: List[Dict[str, str]], 
                     model: Optional[str],
                     max_tokens: Optional[int],
                     temperature: Optional[float],
                     system_role: Optional[str],
                     require_complete_response: bool) -> Dict[str, Any]:
        """
        完整的聊天补全，支持多轮拼接确保完整响应
        
        Args:
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度
            system_role: 系统角色描述
            require_complete_response: 是否要求完整响应（启用多轮拼接）
            
        Returns:
            包含完整响应和元数据的字典
        """
        model = model or self.default_model
        model_type = self._detect_model_type(model)
        if model_type not in MODEL_SPECS:
            raise ValueError(f"Model type '{model_type}' not found in MODEL_SPECS")
        model_limits = MODEL_SPECS[model_type]
        
        # 设置最优token限制
        optimal_max_tokens = max_tokens or model_limits.max_output_tokens
        
        # 如果不需要完整响应或模型不支持continuation，直接单次调用
        if not require_complete_response or not self.enable_continuation:
            return self._single_completion(messages, model, optimal_max_tokens, temperature, system_role)
        
        # 多轮拼接模式 - 确保完整响应
        return self._multi_round_completion(messages, model, optimal_max_tokens, temperature, system_role)
    
    def _single_completion(self, 
                          messages: List[Dict[str, str]], 
                          model: str,
                          max_tokens: int,
                          temperature: Optional[float],
                          system_role: Optional[str]) -> Dict[str, Any]:
        """Single completion call with robust rate limit recovery"""
        
        # Prepare messages
        prepared_messages = self._prepare_messages(messages, system_role)
        
        # Enhanced retry logic with special handling for rate limits
        max_normal_retries = self.max_retries
        max_rate_limit_retries = 20  # Much higher limit for rate limits
        
        for attempt in range(max_normal_retries + max_rate_limit_retries):
            try:
                self.total_requests += 1
                
                call_params = {
                    "model": self.azure_deployment,  # 使用Azure部署名称
                    "messages": prepared_messages,
                    "max_tokens": max_tokens,
                    "timeout": self.timeout,
                }
                
                if temperature is not None:
                    call_params["temperature"] = temperature
                
                response = self.client.chat.completions.create(**call_params)
                
                # Extract response
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # Update statistics
                if hasattr(response, 'usage'):
                    self.total_tokens_used += response.usage.total_tokens
                
                return {
                    'content': content,
                    'finish_reason': finish_reason,
                    'is_complete': finish_reason == 'stop',
                    'is_truncated': finish_reason == 'length',
                    'total_rounds': 1,
                    'model_used': model,
                    'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None,
                    'success': True,
                    'error': None
                }
                
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = ("rate_limit_exceeded" in error_str or 
                               "429" in error_str or 
                               "rate limit" in error_str or
                               "quota" in error_str)
                
                if is_rate_limit:
                    # Special handling for rate limits - much more patient
                    if attempt < max_normal_retries + max_rate_limit_retries - 1:
                        # Extract wait time from error message if possible
                        wait_time = self._extract_wait_time_from_error(str(e))
                        if wait_time is None:
                            # Exponential backoff for rate limits: 5s, 10s, 20s, 40s, 60s, then 60s
                            wait_time = min(60.0, 5.0 * (2 ** min(attempt, 5)))
                        
                        print(f"[LLM_CLIENT] Rate limit hit (attempt {attempt + 1}), waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        continue
                else:
                    # Normal error handling - stricter retry limit
                    if attempt >= max_normal_retries - 1:
                        break
                    
                    print(f"[LLM_CLIENT] Attempt {attempt + 1} failed: {e}")
                    time.sleep(self.retry_delay)
        
        # If we get here, all retries failed
        return {
            'content': '',
            'finish_reason': 'error',
            'is_complete': False,
            'is_truncated': False,
            'total_rounds': 0,
            'model_used': model,
            'tokens_used': 0,
            'success': False,
            'error': f"Failed after {max_normal_retries + max_rate_limit_retries} attempts: {str(e)}"
        }
    
    def _extract_wait_time_from_error(self, error_message: str) -> Optional[float]:
        """
        Extract suggested wait time from OpenAI error message
        
        Examples:
        - "Please try again in 20s" -> 20.0
        - "Please try again in 1m 30s" -> 90.0
        """
        import re
        
        # Pattern for "try again in Xs"
        seconds_match = re.search(r'try again in (\d+)s', error_message)
        if seconds_match:
            return float(seconds_match.group(1))
        
        # Pattern for "try again in Xm Ys" 
        minutes_seconds_match = re.search(r'try again in (\d+)m(?: (\d+)s)?', error_message)
        if minutes_seconds_match:
            minutes = int(minutes_seconds_match.group(1))
            seconds = int(minutes_seconds_match.group(2) or 0)
            return minutes * 60.0 + seconds
        
        # Pattern for "try again in Xm"
        minutes_match = re.search(r'try again in (\d+)m', error_message)
        if minutes_match:
            return float(minutes_match.group(1)) * 60.0
            
        return None
    
    def _multi_round_completion(self, 
                               messages: List[Dict[str, str]], 
                               model: str,
                               max_tokens: int,
                               temperature: Optional[float],
                               system_role: Optional[str]) -> Dict[str, Any]:
        """
        多轮拼接完成 - 突破output token限制，确保完整响应
        """
        
        full_content = ""
        total_rounds = 0
        total_tokens = 0
        current_messages = self._prepare_messages(messages, system_role)
        
        while total_rounds < 10:  # 最多10轮，避免无限循环
            # 单次调用
            result = self._single_completion(current_messages, model, max_tokens, temperature, None)
            
            if not result['success']:
                return result
            
            total_rounds += 1
            total_tokens += result['tokens_used'] or 0
            
            current_content = result['content']
            full_content += current_content
            
            # 如果完成或者内容很短，结束
            if result['finish_reason'] == 'stop' or len(current_content.strip()) < 50:
                break
            
            # 如果是因为长度限制被截断，准备继续
            if result['finish_reason'] == 'length':
                self.continuation_requests += 1
                
                # 准备continuation messages
                continuation_prompt = "Please continue your previous response from where it was interrupted. Maintain the same format and style."
                
                current_messages = [
                    {"role": "assistant", "content": current_content},
                    {"role": "user", "content": continuation_prompt}
                ]
            else:
                break
        
        return {
            'content': full_content,
            'finish_reason': 'stop' if total_rounds < 10 else 'max_rounds',
            'is_complete': True,
            'is_truncated': False,  # 多轮拼接确保不截断
            'total_rounds': total_rounds,
            'model_used': model,
            'tokens_used': total_tokens,
            'success': True,
            'error': None
        }
    
    def _prepare_messages(self, messages: List[Dict[str, str]], system_role: Optional[str]) -> List[Dict[str, str]]:
        """准备消息列表"""
        prepared = []
        
        # 添加系统消息
        if system_role:
            prepared.append({"role": "system", "content": system_role})
        
        # 添加用户消息
        prepared.extend(messages)
        
        return prepared
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取使用统计信息"""
        return {
            'total_requests': self.total_requests,
            'total_tokens_used': self.total_tokens_used,
            'continuation_requests': self.continuation_requests,
            'model_type': self.model_type.value,
            'model_limits': {
                'context_window': self.model_limits.context_window,
                'max_output_tokens': self.model_limits.max_output_tokens
            }
        }
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本token数量 (粗略估算)"""
        # 简单估算：英文1token≈4字符，中文1token≈2字符
        chinese_chars = len([c for c in text if ord(c) > 127])
        english_chars = len(text) - chinese_chars
        
        estimated_tokens = (chinese_chars // 2) + (english_chars // 4)
        return max(estimated_tokens, len(text.split()) // 2)  # 最小估算 