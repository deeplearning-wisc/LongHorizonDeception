# core/Universal_LLM_Client.py
# 统一的LLM客户端 - 支持Azure OpenAI和自动截断
from typing import Dict, Any, List, Optional
from openai.lib.azure import AzureOpenAI

class UniversalLLMClient:
    """
    统一的LLM客户端 - 支持Azure和自动截断
    """
    
    def __init__(self, provider: str, config: Dict[str, Any]):
        """
        初始化统一客户端
        
        Args:
            provider: "azure" 
            config: 提供商特定的配置
        """
        self.provider = provider.lower()
        self.config = config
        
        if self.provider == "azure":
            self._init_azure()
        elif self.provider == "openrouter":
            # OpenRouter placeholder - 暂时不支持
            raise NotImplementedError("OpenRouter support is planned but not yet implemented")
        else:
            raise ValueError(f"Unsupported provider: {provider}. Supported: azure")
    
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
        
        print(f"[UniHandler] Initialized Azure client with deployment: {self.azure_deployment}")
    
    def set_system_prompt(self, system_prompt):
        """设置系统提示"""
        self.messages = [{"role": "system", "content": system_prompt}]
    
    def add_user_message(self, content):
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})
    
    def generate_response(self, max_iterations=5, retry=3):
        """生成回复并更新消息列表，带重试机制"""
        for attempt in range(retry):
            try:
                print(f"[UniHandler] Attempt {attempt + 1}/{retry}")
                final_messages, info = self.auto_continue_response(self.messages, max_iterations)
                self.messages = final_messages
                return info
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"[UniHandler] Attempt {attempt + 1}/{retry} failed:")
                print(f"[UniHandler] Error Type: {error_type}")
                print(f"[UniHandler] Error Details: {error_msg}")
                
                # 如果有特定的错误属性，也打印出来
                if hasattr(e, 'status_code'):
                    print(f"[UniHandler] Status Code: {e.status_code}")
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    print(f"[UniHandler] Response Text: {e.response.text[:500]}")  # 只显示前500字符
                if attempt == retry - 1:  # 最后一次重试失败
                    print(f"[UniHandler] All {retry} attempts failed, giving up")
                    raise e
                else:
                    print(f"[UniHandler] Retrying in attempt {attempt + 2}...")
        
        # 这里永远不会到达，但为了类型检查
        raise Exception("Unexpected error in retry logic")
    
    def get_messages(self):
        """获取当前消息列表"""
        return self.messages.copy()
    
    def auto_continue_response(self, messages, max_iterations=5):
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
        
        print(f"[UniHandler] Processing started with {len(messages)} messages")
        
        while iteration < max_iterations:
            print(f"\n[UniHandler] === API call {iteration + 1} ===")
            
            # 构建请求参数
            request_params = {
                "model": self.azure_deployment,
                "truncation": "auto",
                "max_output_tokens": self.config["max_output_tokens"],
                "store": True  # 必须存储以支持续写
            }
            
            if previous_response_id is None:
                # 首次调用：传入完整消息列表
                request_params["input"] = messages
                print(f"[UniHandler] Initial call with {len(messages)} messages")
            else:
                # 续写调用：使用 previous_response_id
                request_params["previous_response_id"] = previous_response_id
                print(f"[UniHandler] Continuation call with previous_response_id: {previous_response_id}")
            
            # 发送请求
            resp = self.client.responses.create(**request_params)
            responses.append(resp)
            
            # 累积输出
            current_output = resp.output_text
            full_output += current_output
            
            print(f"[UniHandler] Response status: {resp.status}")
            print(f"[UniHandler] Current output length: {len(current_output)} characters")
            print(f"[UniHandler] Total output length: {len(full_output)} characters")
            
            # 检查完成状态
            if resp.status == "completed":
                print("[UniHandler] Response completed, no continuation needed")
                break
                
            # 检查是否因 max_output_tokens 被截断
            if (resp.status == "incomplete" and 
                resp.incomplete_details and 
                resp.incomplete_details.reason == "max_output_tokens"):
                
                print("[UniHandler] Output truncated, preparing continuation...")
                previous_response_id = resp.id
                iteration += 1
            else:
                print(f"[UniHandler] Incomplete for other reason: {resp.incomplete_details}")
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