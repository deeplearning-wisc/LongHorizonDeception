# core/Universal_LLM_Client.py
# 统一的LLM客户端 - 支持OpenAI和Azure的统一接口

import os
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI

class UniversalLLMClient:
    """
    统一的LLM客户端 - 根据配置选择OpenAI或Azure
    保持与Unified_LLM_Handler相同的接口
    """
    
    def __init__(self, provider: str, config: Dict[str, Any]):
        """
        初始化统一客户端
        
        Args:
            provider: "openai" 或 "azure"
            config: 提供商特定的配置
        """
        self.provider = provider.lower()
        self.config = config
        
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "azure":
            self._init_azure()
        elif self.provider == "openrouter":
            self._init_openrouter()
        else:
            raise ValueError(f"Unsupported provider: {provider}. Supported: openai, azure, openrouter")
    
    def _init_openai(self):
        """初始化OpenAI客户端"""
        from pathlib import Path
        
        # 严格模式，无默认值
        api_key_env = self.config['api_key_env']
        api_key = os.getenv(api_key_env)
        
        # 如果环境变量中没有，尝试从项目根目录的.env文件读取
        if not api_key:
            # 找到项目根目录
            current_file = Path(__file__)
            if current_file.parent.name == 'core':
                project_root = current_file.parent.parent
            else:
                project_root = Path.cwd()
            
            env_file = project_root / '.env'
            if env_file.exists():
                # 手动解析.env文件
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                if key == api_key_env:
                                    api_key = value
                                    break
        
        if not api_key:
            raise ValueError(f"Environment variable {api_key_env} not found in environment or .env file")
        
        self.client = OpenAI(api_key=api_key)
        self.model = self.config['model']
        
        # 模拟Unified_LLM_Handler的属性
        self.model_limits = type('obj', (object,), {
            'context_window': 128000,  # GPT-4o context limit
            'max_output_tokens': 4096
        })()
        
        print(f"[UNIVERSAL_LLM] Initialized OpenAI client with model: {self.model}")
    
    def _init_azure(self):
        """直接初始化Azure客户端 - 使用配置参数"""
        from openai import AzureOpenAI
        
        # 从配置中获取Azure参数
        api_key = self.config['azure_api_key']
        endpoint = self.config['azure_endpoint']
        
        # 正确初始化Azure OpenAI客户端
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=self.config['azure_api_version']
        )
        
        self.model = self.config['model_name']
        self.azure_deployment = self.config['azure_deployment']
        
        # 设置模型限制 - 默认GPT-4o规格
        from collections import namedtuple
        ModelLimits = namedtuple('ModelLimits', ['context_window', 'max_output_tokens'])
        self.model_limits = ModelLimits(128000, 4096)
        
        # 统计信息
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'total_tokens_used': 0
        }
        
        print(f"[UNIVERSAL_LLM] Initialized Azure client with model: {self.model}")
    
    def _init_openrouter(self):
        """初始化OpenRouter客户端"""
        from pathlib import Path
        import requests
        
        # 严格模式，无默认值
        api_key_env = self.config['api_key_env']
        api_key = os.getenv(api_key_env)
        
        # 如果环境变量中没有，尝试从项目根目录的.env文件读取
        if not api_key:
            # 找到项目根目录
            current_file = Path(__file__)
            if current_file.parent.name == 'core':
                project_root = current_file.parent.parent
            else:
                project_root = Path.cwd()
            
            env_file = project_root / '.env'
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f'{api_key_env}='):
                            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
        
        if not api_key:
            raise ValueError(f"Environment variable {api_key_env} not found in environment or .env file")
        
        # OpenRouter使用requests，不是OpenAI客户端
        self.api_key = api_key
        self.api_base = "https://openrouter.ai/api/v1"
        self.model = self.config['model']
        
        # 设置模型限制 - Gemini-2.5-Pro规格
        from collections import namedtuple
        ModelLimits = namedtuple('ModelLimits', ['context_window', 'max_output_tokens'])
        self.model_limits = ModelLimits(1048576, 32768)  # Gemini-2.5-Pro的规格
        
        # 统计信息
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'total_tokens_used': 0
        }
        
        print(f"[UNIVERSAL_LLM] Initialized OpenRouter client with model: {self.model}")
    
    def complete_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, 
                     max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                     system_role: Optional[str] = None, require_complete_response: bool = False) -> Dict[str, Any]:
        """
        统一的聊天补全接口
        返回格式与Unified_LLM_Handler保持一致
        """
        if self.provider == "openai":
            return self._openai_complete_chat(messages, model, max_tokens, temperature, system_role, require_complete_response)
        elif self.provider == "azure":
            return self._azure_complete_chat(messages, model, max_tokens, temperature, system_role, require_complete_response)
        elif self.provider == "openrouter":
            return self._openrouter_complete_chat(messages, model, max_tokens, temperature, system_role, require_complete_response)
    
    def _openai_complete_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                            max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                            system_role: Optional[str] = None, require_complete_response: bool = False) -> Dict[str, Any]:
        """OpenAI API调用"""
        try:
            # 处理系统消息
            if system_role:
                messages = [{"role": "system", "content": system_role}] + messages
            
            # 确定使用的模型
            used_model = model or self.model
            
            # 参数设置
            call_params = {
                "model": used_model,
                "messages": messages,
            }
            
            # 根据模型类型设置token参数
            if used_model.startswith('o4-') or used_model.startswith('o3-'):
                # o4-mini和o3系列使用max_completion_tokens
                call_params["max_completion_tokens"] = max_tokens or self.model_limits.max_output_tokens
            else:
                # 其他模型使用max_tokens
                call_params["max_tokens"] = max_tokens or self.model_limits.max_output_tokens
            
            if temperature is not None:
                call_params["temperature"] = temperature
            
            print(f"[UNIVERSAL_LLM] Calling OpenAI API: {call_params['model']}")
            
            # API调用
            response = self.client.chat.completions.create(**call_params)
            
            # 格式化返回结果，匹配Unified_LLM_Handler格式
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            return {
                'success': True,
                'content': content,
                'finish_reason': finish_reason,
                'is_complete': finish_reason != 'length',
                'is_truncated': finish_reason == 'length',
                'total_rounds': 1,
                'model_used': response.model,
                'tokens_used': response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            print(f"[UNIVERSAL_LLM] OpenAI API call failed: {e}")
            return {
                'success': False,
                'content': '',
                'finish_reason': 'error',
                'is_complete': False,
                'is_truncated': False,
                'total_rounds': 0,
                'model_used': model or self.model,
                'tokens_used': 0,
                'error': str(e)
            }
    
    def _azure_complete_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                           max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                           system_role: Optional[str] = None, require_complete_response: bool = False) -> Dict[str, Any]:
        """Azure API调用 - 直接实现"""
        try:
            self.stats['total_calls'] += 1
            
            # 处理系统消息
            if system_role:
                messages = [{"role": "system", "content": system_role}] + messages
            
            # 确定使用的模型
            used_model = model or self.model
            
            # 参数设置
            call_params = {
                "model": self.azure_deployment,  # Azure使用deployment名称
                "messages": messages,
                "max_tokens": max_tokens or self.model_limits.max_output_tokens
            }
            
            if temperature is not None:
                call_params["temperature"] = temperature
            
            print(f"[UNIVERSAL_LLM] Calling Azure API:")
            print(f"  - Endpoint: {self.config['azure_endpoint']}")
            print(f"  - Deployment: {self.azure_deployment}")
            print(f"  - API Version: {self.config['azure_api_version']}")
            
            # API调用
            response = self.client.chat.completions.create(**call_params)
            
            # 格式化返回结果
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            # 统计信息
            tokens_used = getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
            self.stats['total_tokens_used'] += tokens_used
            self.stats['successful_calls'] += 1
            
            return {
                'success': True,
                'content': content,
                'finish_reason': finish_reason,
                'is_complete': finish_reason != 'length',
                'is_truncated': finish_reason == 'length',
                'total_rounds': 1,
                'model_used': used_model,
                'tokens_used': tokens_used
            }
            
        except Exception as e:
            print(f"[UNIVERSAL_LLM] Azure API call failed: {e}")
            return {
                'success': False,
                'content': '',
                'finish_reason': 'error',
                'is_complete': False,
                'is_truncated': False,
                'total_rounds': 0,
                'model_used': model or self.model,
                'tokens_used': 0,
                'error': str(e)
            }
    
    def _openrouter_complete_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                                max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                                system_role: Optional[str] = None, require_complete_response: bool = False) -> Dict[str, Any]:
        """OpenRouter API调用 - 使用requests实现"""
        import requests
        import json
        import time
        
        try:
            self.stats['total_calls'] += 1
            
            # 处理系统消息
            if system_role:
                messages = [{"role": "system", "content": system_role}] + messages
            
            # 确定使用的模型
            used_model = model or self.model
            
            # 构建请求参数
            payload = {
                "model": used_model,
                "messages": messages,
                "max_tokens": max_tokens or self.model_limits.max_output_tokens
            }
            
            if temperature is not None:
                payload["temperature"] = temperature
            
            # 请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                "X-Title": "DeceptioN Research Framework"
            }
            
            print(f"[UNIVERSAL_LLM] Calling OpenRouter API: {used_model}")
            
            # 发送请求 - 添加重试机制
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=120  # 增加超时时间
                    )
                    # 成功后添加小延迟，避免速率限制
                    if attempt > 0:
                        print(f"[UNIVERSAL_LLM] OpenRouter request succeeded after {attempt + 1} attempts")
                    time.sleep(1)  # 1秒延迟避免速率限制
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2, 4, 6秒递增等待
                        print(f"[UNIVERSAL_LLM] OpenRouter connection failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                        print(f"  Error: {str(e)[:100]}")  # 打印错误信息前100字符
                        time.sleep(wait_time)
                    else:
                        print(f"[UNIVERSAL_LLM] OpenRouter failed after {max_retries} attempts")
                        raise e
            
            if response.status_code == 200:
                result = response.json()
                
                # 提取响应内容
                content = result['choices'][0]['message']['content']
                finish_reason = result['choices'][0]['finish_reason']
                
                # 统计信息
                tokens_used = 0
                if 'usage' in result:
                    tokens_used = result['usage'].get('total_tokens', 0)
                    self.stats['total_tokens_used'] += tokens_used
                
                self.stats['successful_calls'] += 1
                
                return {
                    'success': True,
                    'content': content,
                    'finish_reason': finish_reason,
                    'is_complete': finish_reason != 'length',
                    'is_truncated': finish_reason == 'length',
                    'total_rounds': 1,
                    'model_used': used_model,
                    'tokens_used': tokens_used
                }
                
            else:
                error_msg = f"Status {response.status_code}: {response.text}"
                print(f"[UNIVERSAL_LLM] OpenRouter API call failed: {error_msg}")
                return {
                    'success': False,
                    'content': '',
                    'finish_reason': 'error',
                    'is_complete': False,
                    'is_truncated': False,
                    'total_rounds': 0,
                    'model_used': used_model,
                    'tokens_used': 0,
                    'error': error_msg
                }
                
        except Exception as e:
            print(f"[UNIVERSAL_LLM] OpenRouter API call failed: {e}")
            return {
                'success': False,
                'content': '',
                'finish_reason': 'error',
                'is_complete': False,
                'is_truncated': False,
                'total_rounds': 0,
                'model_used': model or self.model,
                'tokens_used': 0,
                'error': str(e)
            }
    
    def estimate_tokens(self, text: str) -> int:
        """估算token数量"""
        # 统一的简单估算：大约4个字符=1个token
        return len(text) // 4 + 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'provider': self.provider,
            'model': self.model,
            **self.stats
        }