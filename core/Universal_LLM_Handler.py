# core/Universal_LLM_Handler.py
# 统一的LLM处理器 - 支持Azure OpenAI和OpenRouter
import logging
import requests
from typing import Dict, Any, List, Optional
from openai.lib.azure import AzureOpenAI

class UniversalLLMHandler:
    """
    统一的LLM客户端 - 支持Azure OpenAI和OpenRouter
    """
    
    # 统一的续写提示词 - 确保Azure和OpenRouter行为一致
    CONTINUATION_PROMPT = "Continue exactly from where you left off. Do not restart, do not repeat any content, do not add any preamble or introduction. Continue the response seamlessly as if there was no interruption."
    
    def __init__(self, provider: str, config: Dict[str, Any], verbose_print: bool = False, overflow_truncate: bool = True):
        """
        初始化统一客户端
        
        Args:
            provider: "azure" 或 "openrouter"
            config: 提供商特定的配置
            verbose_print: 是否打印详细信息，False时只打印错误
            overflow_truncate: 是否允许自动处理输入溢出
                - False: 严格模式，超限直接报错（Manager/Memory必须用）
                - True: 自动处理模式，provider自动处理溢出（默认）
        """
        self.provider = provider.lower()
        self.config = config
        self.verbose_print = verbose_print
        self.overflow_truncate = overflow_truncate
        
        if self.provider == "azure":
            self._init_azure()
        elif self.provider == "openrouter":
            self._init_openrouter()
        else:
            raise ValueError(f"Unsupported provider: {provider}. Supported: azure, openrouter")
    
    def _init_azure(self):
        """直接初始化Azure客户端 - 使用配置参数"""
        # 检查必需的配置项
        required_keys = ['azure_api_key', 'azure_endpoint', 'azure_api_version', 'azure_deployment', 'max_output_tokens']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"[UniHandler] Missing required config key: {key}")
        
        # 从配置中获取Azure参数
        api_key = self.config['azure_api_key']
        endpoint = self.config['azure_endpoint']
        api_version = self.config['azure_api_version']
        deployment = self.config['azure_deployment']
        
        # 初始化Azure OpenAI客户端
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_deployment=deployment,
            api_version=api_version,
            api_key=api_key
        )
        
        self.azure_deployment = deployment
        
        # 内部维护的消息列表
        self.messages = []
        
        if self.verbose_print:
            print(f"[UniHandler] Initialized Azure client with deployment: {self.azure_deployment}")

    def _init_openrouter(self):
        """初始化OpenRouter配置"""
        # 检查必需的配置项
        required_keys = ['api_key', 'model', 'base_url', 'max_tokens']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"[UniHandler] Missing required config key: {key}")
        
        # 从配置中获取OpenRouter参数
        self.api_key = self.config['api_key']
        self.model = self.config['model']
        self.base_url = self.config['base_url']
        self.max_tokens = self.config['max_tokens']
        
        # 内部维护的消息列表
        self.messages = []
        
        if self.verbose_print:
            print(f"[UniHandler] Initialized OpenRouter client with model: {self.model}")
    
    def _print(self, message: str, force: bool = False):
        """控制打印输出"""
        if self.verbose_print or force:
            print(message)
    
    def set_system_prompt(self, system_prompt):
        """设置系统提示"""
        self.messages = [{"role": "system", "content": system_prompt}]
    
    def add_user_message(self, content):
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})
    
    def generate_response(self, max_iterations: int = 5, retry: int = 3):
        """生成回复并更新消息列表，带重试机制，直接返回LLM回复内容"""
        for attempt in range(retry):
            try:
                self._print(f"[UniHandler] Attempt {attempt + 1}/{retry}")
                
                # 根据provider路由到不同的续写方法
                if self.provider == "azure":
                    final_messages, info = self.auto_continue_response(self.messages, max_iterations)
                elif self.provider == "openrouter":
                    final_messages, info = self.auto_continue_openrouter(self.messages, max_iterations)
                else:
                    raise ValueError(f"Unsupported provider for generate_response: {self.provider}")
                
                self.messages = final_messages
                
                # 提取实际的LLM回复内容
                if final_messages and len(final_messages) > 0:
                    last_message = final_messages[-1]
                    if last_message['role'] == 'assistant':
                        return last_message['content']
                    else:
                        # 如果最后一条不是assistant消息，寻找最后一条assistant消息
                        for msg in reversed(final_messages):
                            if msg['role'] == 'assistant':
                                return msg['content']
                
                # 如果找不到assistant回复，返回空字符串而不是崩溃
                self._print("[UniHandler] Warning: No assistant response found", force=True)
                return ""
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                self._print(f"[UniHandler] Attempt {attempt + 1}/{retry} failed:", force=True)
                self._print(f"[UniHandler] Error Type: {error_type}", force=True)
                self._print(f"[UniHandler] Error Details: {error_msg}", force=True)
                
                # 如果有特定的错误属性，也打印出来
                if hasattr(e, 'status_code'):
                    self._print(f"[UniHandler] Status Code: {e.status_code}", force=True)
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    self._print(f"[UniHandler] Response Text (Length: {len(e.response.text)} chars): {e.response.text}", force=True)
                if attempt == retry - 1:  # 最后一次重试失败
                    self._print(f"[UniHandler] All {retry} attempts failed, giving up", force=True)
                    raise e
                else:
                    self._print(f"[UniHandler] Retrying in attempt {attempt + 2}...", force=True)
        
        # 这里永远不会到达，但为了类型检查
        raise Exception("Unexpected error in retry logic")
    
    def get_messages(self):
        """获取当前消息列表"""
        return self.messages.copy()
    
    def auto_continue_response(self, messages, max_iterations: int = 5):
        """
        自动处理 Responses API 输出截断并续写
        
        Args:
            messages: 原始消息列表 [{"role": "system/user", "content": "..."}]
            max_iterations: 最大续写次数
        
        Returns:
            tuple: (完整消息列表, 续写详情)
        """
        responses = []  # 存储所有响应对象
        full_output = ""  # 累积的完整输出
        previous_response_id = None
        iteration = 0
        
        self._print(f"[UniHandler] Processing started with {len(messages)} messages")
        
        while iteration < max_iterations:
            self._print(f"\n[UniHandler] === API call {iteration + 1} ===")
            
            # 构建请求参数
            request_params = {
                "model": self.azure_deployment,
                "max_output_tokens": self.config["max_output_tokens"],
                "store": True  # 必须存储以支持续写
            }
            
            # 根据overflow_truncate设置truncation值
            if self.overflow_truncate:
                request_params["truncation"] = "auto"  # 启用中段压缩
            else:
                request_params["truncation"] = "disabled"  # 默认值，显式禁用，超限报400
            
            # 添加reasoning支持（GPT-5/o-series专属）
            if "reasoning_effort" in self.config:
                request_params["reasoning"] = {
                    "effort": self.config["reasoning_effort"]
                }
                self._print(f"[UniHandler] Using reasoning effort: {self.config['reasoning_effort']}")
            
            if previous_response_id is None:
                # 首次调用：传入完整消息列表
                request_params["input"] = messages
                self._print(f"[UniHandler] Initial call with {len(messages)} messages")
            else:
                # 续写调用：使用 previous_response_id + continuation input (industry standard)
                request_params["previous_response_id"] = previous_response_id
                # Azure OpenAI requires input parameter even for continuations
                continuation_input = [{"role": "user", "content": self.CONTINUATION_PROMPT}]
                request_params["input"] = continuation_input
                self._print(f"[UniHandler] Continuation call with previous_response_id: {previous_response_id}")
            
            # 发送请求
            resp = self.client.responses.create(**request_params)
            responses.append(resp)
            
            # 累积输出
            current_output = resp.output_text
            full_output += current_output
            
            self._print(f"[UniHandler] Response status: {resp.status}")
            self._print(f"[UniHandler] Current output length: {len(current_output)} characters")
            self._print(f"[UniHandler] Total output length: {len(full_output)} characters")
            
            # 检查完成状态
            if resp.status == "completed":
                self._print("[UniHandler] Response completed, no continuation needed")
                break
                
            # 检查是否因 max_output_tokens 被截断
            if (resp.status == "incomplete" and 
                resp.incomplete_details and 
                resp.incomplete_details.reason == "max_output_tokens"):
                
                self._print("[UniHandler] Output truncated, preparing continuation...")
                previous_response_id = resp.id
                iteration += 1
            else:
                self._print(f"[UniHandler] Incomplete for other reason: {resp.incomplete_details}")
                break
        
        # 构建最终的消息列表
        final_messages = self.build_final_message_list(messages, full_output)
        
        # 返回结果
        continuation_info = {
            "total_iterations": iteration + 1,
            "was_continued": iteration > 0,
            "total_responses": len(responses),
            "final_length": len(full_output),
            "response_ids": [r.id for r in responses]
        }
        
        return final_messages, continuation_info

    def auto_continue_openrouter(self, messages, max_iterations: int = 5):
        """
        OpenRouter自动续写处理
        
        Args:
            messages: 原始消息列表
            max_iterations: 最大续写次数
            
        Returns:
            tuple: (完整消息列表, 续写详情)
        """
        full_output = ""
        current_messages = messages.copy()
        iteration = 0
        
        self._print(f"[UniHandler] OpenRouter processing started with {len(messages)} messages")
        
        while iteration < max_iterations:
            self._print(f"\n[UniHandler] === OpenRouter API call {iteration + 1} ===")
            
            # 构造请求参数
            request_body = {
                "model": self.model,
                "messages": current_messages,
                "max_tokens": self.max_tokens
            }
            
            # 根据overflow_truncate设置transforms
            if self.overflow_truncate:
                request_body["transforms"] = ["middle-out"]  # 自动处理模式
            else:
                request_body["transforms"] = []  # 严格模式，明确禁用
            
            try:
                # 发送请求
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_body,
                    timeout=180
                )
                
                self._print(f"[DEBUG] HTTP Status: {response.status_code}")
                if response.status_code != 200:
                    # 科研代码要求：完整错误记录，绝不截断
                    self._print(f"[DEBUG] HTTP Error Response (Full): {response.text}")
                response.raise_for_status()
                
                # 健壮解析OpenRouter响应
                data = response.json()
                
                # 1) 错误优先 - 严格检查不使用.get()
                if "error" in data:
                    err = data["error"]
                    self._print(f"[DEBUG] Full error response: {data}")
                    
                    # 严格验证错误结构，不允许默认值
                    if "message" not in err:
                        raise Exception(f"OpenRouter Error: Invalid error format - missing 'message' field")
                    
                    error_msg = err["message"]
                    error_type = err["type"] if "type" in err else "unknown_type"
                    error_code = err["code"] if "code" in err else "unknown_code"
                    
                    raise Exception(f"OpenRouter Error: {error_msg} | Type: {error_type} | Code: {error_code}")
                
                # 2) 标准主路径 - 严格验证不使用.get()
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    
                    # 严格验证message结构
                    if "message" not in choice:
                        raise Exception(f"OpenRouter Response Error: Missing 'message' in choice")
                    msg = choice["message"]
                    
                    # 严格验证content - 科研代码不允许任何妥协
                    if "content" not in msg:
                        raise Exception(f"OpenRouter Response Error: Missing 'content' in message")
                    content = msg["content"]
                    if content is None:
                        raise Exception(f"OpenRouter Response Error: 'content' is null")
                    if not isinstance(content, str):
                        raise Exception(f"OpenRouter Response Error: 'content' must be string, got {type(content)}")
                    
                    # 严格验证finish_reason
                    if "finish_reason" not in choice:
                        raise Exception(f"OpenRouter Response Error: Missing 'finish_reason' in choice")
                    finish_reason = choice["finish_reason"]
                    
                else:
                    raise Exception(f"OpenRouter Response Error: Missing or empty 'choices' field. Available keys: {list(data.keys())}")
                
                # 累积输出
                full_output += content
                
                self._print(f"[UniHandler] Response finish_reason: {finish_reason}")
                self._print(f"[UniHandler] Current output length: {len(content)} characters")
                self._print(f"[UniHandler] Total output length: {len(full_output)} characters")
                
                # 检查是否需要续写
                if finish_reason != "length":
                    self._print("[UniHandler] Response completed, no continuation needed")
                    break
                
                # 需要续写：构造新的消息列表（包含完整历史）
                self._print("[UniHandler] Output truncated by length, preparing continuation...")
                current_messages = messages + [
                    {"role": "assistant", "content": full_output},
                    {"role": "user", "content": self.CONTINUATION_PROMPT}
                ]
                iteration += 1
                
            except Exception as e:
                self._print(f"[UniHandler] OpenRouter API call failed: {e}", force=True)
                raise
        
        # 构建最终消息列表
        final_messages = messages + [{"role": "assistant", "content": full_output}]
        
        # 返回续写信息
        continuation_info = {
            "total_iterations": iteration + 1,
            "was_continued": iteration > 0,
            "final_length": len(full_output)
        }
        
        return final_messages, continuation_info

    def build_final_message_list(self, original_messages, full_assistant_output):
        """
        构建包含完整助手回复的消息列表
        
        Args:
            original_messages: 原始消息列表 (system + user messages)
            full_assistant_output: 拼接后的完整助手输出
        
        Returns:
            list: 完整的消息列表
        """
        final_messages = original_messages.copy()
        final_messages.append({
            "role": "assistant",
            "content": full_assistant_output
        })
        return final_messages