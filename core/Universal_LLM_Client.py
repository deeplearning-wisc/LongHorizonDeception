# core/Universal_LLM_Client.py
# 统一的LLM客户端 - 支持OpenAI和Azure的统一接口

import os
import time
import re
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
        self.model = self.config.get('model_name', self.config.get('model', 'unknown'))
        
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
        
        # 支持直接的api_key配置或环境变量引用
        if 'api_key' in self.config:
            # 直接从配置中获取API key
            api_key = self.config['api_key']
        elif 'api_key_env' in self.config:
            # 从环境变量获取API key（旧格式）
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
        else:
            raise ValueError("Neither 'api_key' nor 'api_key_env' found in OpenRouter config")
        
        if not api_key:
            if 'api_key_env' in self.config:
                raise ValueError(f"Environment variable {self.config['api_key_env']} not found in environment or .env file")
            else:
                raise ValueError("OpenRouter API key not found in configuration")
        
        # OpenRouter使用requests，不是OpenAI客户端
        self.api_key = api_key
        self.api_base = "https://openrouter.ai/api/v1"
        self.model = self.config.get('model_name', self.config.get('model', 'unknown'))
        
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
                     system_role: Optional[str] = None, require_complete_response: bool = False,
                     caller: str = "UNKNOWN") -> Dict[str, Any]:
        """
        统一的聊天补全接口
        返回格式与Unified_LLM_Handler保持一致
        """
        if self.provider == "openai":
            return self._openai_complete_chat(messages, model, max_tokens, temperature, system_role, require_complete_response, caller)
        elif self.provider == "azure":
            return self._azure_complete_chat(messages, model, max_tokens, temperature, system_role, require_complete_response, caller)
        elif self.provider == "openrouter":
            return self._openrouter_complete_chat(messages, model, max_tokens, temperature, system_role, require_complete_response, caller)
        else:
            return {'success': False, 'error': f'Unsupported provider: {self.provider}'}
    
    def _truncate_messages_by_task(self, messages: List[Dict[str, str]], attempt: int) -> List[Dict[str, str]]:
        """按task为单位删除messages，每次删除一个完整task的所有消息"""
        if len(messages) <= 2:  # 至少保留当前任务
            return messages
        
        truncated = messages.copy()
        original_count = len(messages)
        
        if attempt > 2:
            # 第3次还溢出就直接error
            raise RuntimeError(f"Context overflow persists after removing 2 tasks, cannot proceed")
        
        print(f"[UNIVERSAL_LLM] Attempt {attempt}: Removing 1 complete task from message history")
        
        # 查找最早的task开头并删除该task的所有消息
        task_removed = False
        removed_count = 0
        
        # 从头开始找task标记：如 "[TASK_01 Round 1]"
        i = 0
        while i < len(truncated) and len(truncated) > 2:
            msg_content = truncated[i]['content']
            
            # 找到task开头标记
            if '[TASK_' in msg_content and 'Round 1]' in msg_content:
                print(f"[UNIVERSAL_LLM] Found task start: {msg_content[:50]}...")
                
                # 删除从这个task开始的所有消息，直到下一个task开始或消息结束
                while i < len(truncated) and len(truncated) > 2:
                    current_msg = truncated[i]['content']
                    
                    # 如果遇到下一个task开头，停止删除
                    if i > 0 and '[TASK_' in current_msg and 'Round 1]' in current_msg:
                        break
                    
                    truncated.pop(i)
                    removed_count += 1
                    # i不需要+1，因为pop后下一个元素会移到当前位置
                
                task_removed = True
                break
            else:
                i += 1
        
        if not task_removed:
            # 如果没找到task标记，就简单删除前面一半的消息
            messages_to_remove = max(5, len(truncated) // 2)
            for _ in range(messages_to_remove):
                if len(truncated) > 2:
                    truncated.pop(0)
                    removed_count += 1
            print(f"[UNIVERSAL_LLM] No task markers found, removed {removed_count} messages from start")
        
        print(f"[UNIVERSAL_LLM] Removed {removed_count} messages, {len(truncated)} messages remaining")
        print(f"[UNIVERSAL_LLM] Original: {original_count} messages -> After truncation: {len(truncated)} messages")
        
        return truncated
    
    def _openai_complete_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                            max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                            system_role: Optional[str] = None, require_complete_response: bool = False,
                            caller: str = "UNKNOWN") -> Dict[str, Any]:
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
            
            print(f"[{caller}] Using: {call_params['model']}")
            
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
            error_str = str(e)
            print(f"[UNIVERSAL_LLM] OpenAI API call failed: {error_str}")
            
            # 检查是否是context length错误
            context_error_info = self.parse_context_length_error(error_str)
            
            return {
                'success': False,
                'content': '',
                'finish_reason': 'error',
                'is_complete': False,
                'is_truncated': False,
                'total_rounds': 0,
                'model_used': model or self.model,
                'tokens_used': 0,
                'error': error_str,
                'context_overflow': context_error_info  # 添加context溢出信息
            }
    
    def _azure_complete_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                           max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                           system_role: Optional[str] = None, require_complete_response: bool = False,
                           caller: str = "UNKNOWN") -> Dict[str, Any]:
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
            
            # 简化打印，只显示模型名字
            model_display = self.config.get('model_name', self.azure_deployment)
            print(f"[{caller}] Using: {model_display}")
            
            # API调用 - 强制使用正确的API版本
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
            error_str = str(e)
            print(f"[UNIVERSAL_LLM] Azure API call failed: {error_str}")
            
            # 检查是否是context length错误
            context_error_info = self.parse_context_length_error(error_str)
            
            return {
                'success': False,
                'content': '',
                'finish_reason': 'error',
                'is_complete': False,
                'is_truncated': False,
                'total_rounds': 0,
                'model_used': model or self.model,
                'tokens_used': 0,
                'error': error_str,
                'context_overflow': context_error_info  # 添加context溢出信息
            }
    
    def _openrouter_complete_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                                max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                                system_role: Optional[str] = None, require_complete_response: bool = False,
                                caller: str = "UNKNOWN") -> Dict[str, Any]:
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
            
            print(f"[{caller}] Using: {used_model}")
            
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
    
    def parse_context_length_error(self, error_msg: str) -> Optional[Dict[str, int]]:
        """
        解析context length超限错误，提取最大限制和实际请求的token数
        
        错误格式: 'This model's maximum context length is 128000 tokens. However, you requested 129947 tokens (113563 in the messages, 16384 in the completion)'
        
        Returns:
            Dict with:
            - 'max_context_length': 模型的最大context限制
            - 'requested_tokens': 实际请求的总token数
            - 'message_tokens': messages中的token数
            - 'completion_tokens': completion中的token数
            None if not a context length error
        """
        # 检查是否是context length错误
        if 'context_length_exceeded' not in error_msg and 'maximum context length' not in error_msg:
            return None
        
        result = {}
        
        # 提取最大context限制
        max_match = re.search(r'maximum context length is (\d+) tokens', error_msg)
        if max_match:
            result['max_context_length'] = int(max_match.group(1))
        else:
            # 如果没找到，使用默认值
            result['max_context_length'] = 128000
        
        # 提取请求的总token数 - 支持两种格式
        request_match = re.search(r'requested (\d+) tokens', error_msg)
        if not request_match:
            # 尝试另一种格式："messages resulted in 129835 tokens"
            request_match = re.search(r'messages resulted in (\d+) tokens', error_msg)
            if not request_match:
                return None
        
        result['requested_tokens'] = int(request_match.group(1))
        
        # 尝试提取messages和completion的详细信息
        detail_match = re.search(r'\((\d+) in the messages, (\d+) in the completion\)', error_msg)
        if detail_match:
            result['message_tokens'] = int(detail_match.group(1))
            result['completion_tokens'] = int(detail_match.group(2))
        else:
            # 如果没有详细信息，估算分配
            # 对于"messages resulted in X tokens"格式，假设completion需要16384
            result['message_tokens'] = result['requested_tokens'] - 16384
            result['completion_tokens'] = 16384
        
        # 计算超出了多少
        result['overflow_tokens'] = result['requested_tokens'] - result['max_context_length']
        
        return result