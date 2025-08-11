# core/agent.py
# LDLE Agent abstraction layer with unified LLM client

from typing import Dict, Any, Optional, List
from tasks.base import Task, TaskFile
from .llm_client import UnifiedLLMClient
from utils.error_handler import PipelineErrorHandler, RetryHandler

class LDLEAgent:
    """
    LDLE Agent that can process tasks with file attachments
    Uses unified LLM client for robust token handling
    """
    
    def __init__(self, azure_api_key: str, azure_endpoint: str, azure_deployment: str, model_name: str, system_prompt: str, max_tokens: int, api_version: str):
        """
        Initialize the LDLE Agent
        
        Args:
            azure_api_key: Azure OpenAI API key
            azure_endpoint: Azure OpenAI endpoint
            azure_deployment: Azure deployment name
            model_name: Model to use for task processing
            system_prompt: System prompt for the agent
            max_tokens: Maximum tokens for responses
            api_version: Azure API version
        """
        self.azure_api_key = azure_api_key
        self.azure_endpoint = azure_endpoint
        self.azure_deployment = azure_deployment
        self.model_name = model_name
        
        if system_prompt is None:
            raise ValueError("system_prompt is required and cannot be None")
        self.system_prompt = system_prompt
        
        self.max_tokens = max_tokens
        self.api_version = api_version
        
        # 🆕 添加重试处理器
        self.retry_handler = RetryHandler(max_retries=3)
        
        # Use unified LLM client - supports multi-round concatenation and complete responses
        self.llm_client = UnifiedLLMClient(
            azure_api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment,
            default_model=model_name,
            max_retries=3,
            retry_delay=2.0,
            timeout=300,
            api_version=api_version,
            enable_continuation=True  # Enable multi-round concatenation for complete responses
        )
        
        # 确定模型的context限制
        model_type = self.llm_client._detect_model_type(model_name)
        self.context_limit = self.llm_client.model_limits.context_window
        
        # Memory/context tracking
        self.conversation_history = []
        
        # 🆕 全局对话历史管理 (跨Task连续记忆)
        self.global_conversation_history = []
    
    def _estimate_context_size(self, base_prompt: str, event_content: str, files: List[TaskFile]) -> int:
        """估算当前context大小 (包含全局历史)"""
        # 粗略估算：4个字符≈1个token
        size = len(self.system_prompt) // 4  # 系统提示词
        size += len(base_prompt) // 4
        
        if event_content and event_content != 'Normal business conditions':
            size += len(event_content) // 4
        
        # 计算全局对话历史大小
        for interaction in self.global_conversation_history:
            size += len(interaction['agent_response']) // 4
            size += len(interaction['manager_feedback']) // 4
        
        # 计算文件内容大小
        if files:
            for file_obj in files:
                size += len(file_obj.content) // 4
        
        # 加上格式化字符的估算
        size += 1000  # 格式化字符和其他overhead
        
        return size
    
    def _truncate_global_history(self, max_history_tokens: int = 30000):
        """智能截断全局对话历史，保留最近的交互"""
        if not self.global_conversation_history:
            return
        
        # 计算当前历史大小
        total_tokens = 0
        for interaction in self.global_conversation_history:
            total_tokens += len(interaction['agent_response']) // 4
            total_tokens += len(interaction['manager_feedback']) // 4
        
        # 如果超过限制，从最早的开始删除
        while total_tokens > max_history_tokens and len(self.global_conversation_history) > 1:
            # 移除最早的交互
            removed = self.global_conversation_history.pop(0)
            total_tokens -= len(removed['agent_response']) // 4
            total_tokens -= len(removed['manager_feedback']) // 4
            print(f"⚠️  [AGENT] Truncated history: removed {removed['task_id']} Round {removed['round']}")
    
    def add_interaction_to_global_history(self, task_id: str, round_num: int, agent_response: str, manager_feedback: str, task_complete: bool):
        """添加交互到全局历史"""
        interaction_record = {
            'task_id': task_id,
            'round': round_num,
            'agent_response': agent_response,
            'manager_feedback': manager_feedback,
            'task_complete': task_complete
        }
        self.global_conversation_history.append(interaction_record)
    
    def _build_enhanced_prompt_with_history(self, task: Task, event_content: str) -> str:
        """构建包含全局历史的完整prompt"""
        # 1. 智能截断历史以避免context溢出
        estimated_size = self._estimate_context_size(task.base_prompt, event_content, task.files)
        print(f"📊 [AGENT] Estimated context size: ~{estimated_size} tokens")
        
        # 动态计算context limit阈值（保留20%余量）
        context_threshold = int(self.context_limit * 0.8)
        if estimated_size > context_threshold:
            print(f"⚠️  [AGENT] Context approaching limit ({estimated_size}/{context_threshold}), truncating history...")
            self._truncate_global_history(max_history_tokens=30000)
            estimated_size_after = self._estimate_context_size(task.base_prompt, event_content, task.files)
            print(f"✅ [AGENT] Context size after truncation: ~{estimated_size_after} tokens")
        
        # 2. 构建基础prompt
        if event_content and event_content != 'Normal business conditions':
            enhanced_prompt = f"""{task.base_prompt}

=== CURRENT SITUATION ===
{event_content}"""
        else:
            enhanced_prompt = task.base_prompt
        
        # 3. 添加全局对话历史 (如果有)
        if self.global_conversation_history:
            conversation_context = []
            for interaction in self.global_conversation_history:
                task_info = interaction.get('task_id', 'Unknown')
                round_info = interaction.get('round', 1)
                conversation_context.append(f"[{task_info} - Round {round_info}]")
                conversation_context.append(f"Assistant: {interaction['agent_response']}")
                conversation_context.append("")
                conversation_context.append(f"Manager: {interaction['manager_feedback']}")
                conversation_context.append("")
            
            enhanced_prompt += f"""

=== CONVERSATION HISTORY ===
{chr(10).join(conversation_context)}

[Current Task: {task.task_id}]
Please continue based on the conversation history above."""
        else:
            enhanced_prompt += f"""

[Current Task: {task.task_id}]
Please provide a comprehensive response to complete this task."""
        
        return enhanced_prompt

    def process_task_with_event(self, task: Task, event_content: str) -> Dict[str, Any]:
        """
        处理带有事件的任务 - 自动管理context和历史
        
        Args:
            task: Task object with prompt and files
            event_content: Event content (e.g., pressure situation)
            
        Returns:
            Dictionary containing agent response and metadata
        """
        try:
            # 构建包含全局历史的enhanced prompt
            enhanced_prompt = self._build_enhanced_prompt_with_history(task, event_content)
            
            # 使用enhanced prompt方法处理任务
            return self.process_task_with_enhanced_prompt(task, enhanced_prompt, manager_feedback_history=None)
            
        except Exception as e:
            print(f"❌ [AGENT] Error in task processing with event: {e}")
            raise

    def process_task(self, 
                    task: Task, 
                    manager_feedback_history: Optional[List[str]]) -> Dict[str, Any]:
        """
        Process a task with file attachments using unified LLM client with retry mechanism
        
        Args:
            task: Task object with prompt and files
            manager_feedback_history: Previous feedback from manager
            
        Returns:
            Dictionary containing agent response and metadata
        """
        
        try:
            # 🆕 使用重试机制进行任务处理
            result = self.retry_handler.retry_with_warnings(
                self._single_task_attempt,
                "AGENT",
                "task processing",
                task, manager_feedback_history
            )
            return result
                
        except Exception as e:
            error_msg = f"Agent processing failed after retries: {str(e)}"
            # 现在这是真正的失败，可以返回错误
            return {
                'response': f"I apologize, but I encountered an error processing this task: {error_msg}",
                'prompt_used': "",
                'files_processed': 0,
                'success': False,
                'error': error_msg,
                'llm_metadata': None
            }
    
    def _single_task_attempt(self, task: Task, manager_feedback_history: Optional[List[str]]) -> Dict[str, Any]:
        """单次任务处理尝试 - 被重试机制调用"""
        
        # 1. 获取任务prompt - 使用正确的Task结构
        base_prompt = task.base_prompt
        
        # 2. Build file context
        file_context = self._build_file_context(task.files)
        
        # 3. Build full prompt
        full_prompt = self._build_full_prompt(base_prompt, file_context)
        
        # 4. Add manager feedback context if available
        if manager_feedback_history:
            feedback_context = self._build_feedback_context(manager_feedback_history)
            full_prompt = feedback_context + "\n\n" + full_prompt
        
        # 5. Prepare messages for LLM client
        messages = [
            {"role": "user", "content": full_prompt}
        ]
        
        # 5.5. Check context size before LLM call
        estimated_tokens = self.llm_client.estimate_tokens(self.system_prompt + full_prompt)
        
        if estimated_tokens > self.context_limit:
            # Context溢出 - 记录警告但不抛出错误，Agent应该能处理长对话
            print(f"⚠️  [AGENT WARNING] Context approaching limit: {estimated_tokens}/{self.context_limit} tokens")
            print(f"⚠️  Full prompt length: {len(full_prompt)} chars")
            print(f"⚠️  Agent will proceed with current context, but may need history truncation in future rounds")
        
        # 6. Call unified LLM client with complete response requirement
        llm_result = self.llm_client.complete_chat(
            messages=messages,
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=None,  # 使用OpenAI默认值
            system_role=self.system_prompt,
            require_complete_response=True  # Enable multi-round concatenation for complete responses
        )
        
        if not llm_result['success']:
            # 抛出异常让重试机制处理
            raise RuntimeError(f"LLM call failed: {llm_result['error']}")
        
        agent_response = llm_result['content']
        
        # 7. Store conversation history - 完整保存，不截断
        self.conversation_history.append({
            'day': task.day,
            'task_id': task.task_id,
            'prompt_full': full_prompt,           # 完整prompt
            'response_full': agent_response,      # 完整回复
            'files_provided': len(task.files) if task.files else 0,
            'llm_rounds': llm_result['total_rounds'],
            'tokens_used': llm_result['tokens_used']
        })
        
        return {
            'response': agent_response,
            'prompt_used': full_prompt,
            'files_processed': len(task.files) if task.files else 0,
            'success': True,
            'error': None,
            'llm_metadata': {
                'is_complete': llm_result['is_complete'],
                'is_truncated': llm_result['is_truncated'],
                'total_rounds': llm_result['total_rounds'],
                'tokens_used': llm_result['tokens_used'],
                'finish_reason': llm_result['finish_reason']
            }
        }
    
    def process_task_with_enhanced_prompt(self,
                                        task: Task,
                                        enhanced_prompt: str,
                                        manager_feedback_history: Optional[List[str]]) -> Dict[str, Any]:
        """
        Process a task with a pre-enhanced prompt (using Event System)
        
        Args:
            task: Task object with files and metadata
            enhanced_prompt: Already enhanced prompt (base_prompt + event if applicable)
            manager_feedback_history: Previous feedback from manager
            
        Returns:
            Dictionary containing agent response and metadata
        """
        
        # 1. Build file context
        file_context = self._build_file_context(task.files)
        
        # 2. Build full prompt with file context
        full_prompt = self._build_full_prompt(enhanced_prompt, file_context)
        
        # 3. Add manager feedback context if available
        if manager_feedback_history:
            feedback_context = self._build_feedback_context(manager_feedback_history)
            full_prompt = feedback_context + "\n\n" + full_prompt
        
        # 4. Prepare messages for LLM client
        messages = [
            {"role": "user", "content": full_prompt}
        ]
        
        # 4.5. Check context size before LLM call
        estimated_tokens = self.llm_client.estimate_tokens(self.system_prompt + full_prompt)
        
        if estimated_tokens > self.context_limit:
            # Context溢出 - 记录警告但不抛出错误，Agent应该能处理长对话
            print(f"⚠️  [AGENT WARNING] Context approaching limit: {estimated_tokens}/{self.context_limit} tokens")
            print(f"⚠️  Enhanced prompt length: {len(full_prompt)} chars")
            print(f"⚠️  Agent will proceed with current context, but may need history truncation in future rounds")
        
        # 5. Call unified LLM client with complete response requirement
        llm_result = self.llm_client.complete_chat(
            messages=messages,
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=None,  # 使用OpenAI默认值
            system_role=self.system_prompt,
            require_complete_response=True
        )
            
        if not llm_result['success']:
            # 抛出异常让重试机制处理
            raise RuntimeError(f"LLM call failed: {llm_result['error']}")
        
        agent_response = llm_result['content']
        
        # 6. Store conversation history - 完整保存，不截断
        self.conversation_history.append({
            'day': task.day,
            'task_id': task.task_id,
            'prompt_full': full_prompt,           # 完整prompt
            'response_full': agent_response,      # 完整回复
            'files_provided': len(task.files) if task.files else 0,
            'llm_rounds': llm_result['total_rounds'],
            'tokens_used': llm_result['tokens_used']
        })
        
        return {
            'response': agent_response,
            'prompt_used': full_prompt,
            'files_processed': len(task.files) if task.files else 0,
            'success': True,
            'error': None,
            'llm_metadata': {
                'is_complete': llm_result['is_complete'],
                'is_truncated': llm_result['is_truncated'],
                'total_rounds': llm_result['total_rounds'],
                'tokens_used': llm_result['tokens_used'],
                'finish_reason': llm_result['finish_reason']
            }
        }
            

    
    def _build_file_context(self, files: Optional[List[TaskFile]]) -> str:
        """Build file context section for the prompt"""
        if not files:
            return ""
        
        file_context = "\n\n=== ATTACHED FILES FOR ANALYSIS ===\n"
        
        for file_obj in files:
            file_context += f"\n--- FILE: {file_obj.filename} ---\n"
            if file_obj.description:
                file_context += f"Description: {file_obj.description}\n"
            file_context += f"Type: {file_obj.file_type}\n"
            file_context += f"Content:\n{file_obj.content}\n"
        
        file_context += "\n=== END OF ATTACHED FILES ===\n"
        return file_context
    
    def _build_full_prompt(self, base_prompt: str, file_context: str) -> str:
        """Combine base prompt with file context"""
        if file_context:
            return f"{base_prompt}{file_context}\n\nPlease analyze the attached files and provide your complete response based on the task requirements above. Take your time to provide a thorough and comprehensive analysis."
        else:
            return base_prompt
    
    def _build_feedback_context(self, feedback_history: List[str]) -> str:
        """Build context from follow-up requests (legacy manager feedback removed)"""
        if not feedback_history:
            return ""
        
        context = "=== FOLLOW-UP REQUESTS ===\n"
        for i, followup in enumerate(feedback_history, 1):
            context += f"Request {i}: {followup}\n"
        context += "=== END REQUESTS ===\n"
        context += "Please address these follow-up requests in your current response."
        
        return context
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of agent's conversation history"""
        total_tokens = sum(h.get('tokens_used', 0) for h in self.conversation_history)
        total_rounds = sum(h.get('llm_rounds', 1) for h in self.conversation_history)
        
        return {
            'total_tasks_processed': len(self.conversation_history),
            'tasks_with_files': sum(1 for h in self.conversation_history if h['files_provided'] > 0),

            'llm_statistics': {
                'total_tokens_used': total_tokens,
                'total_llm_rounds': total_rounds,
                'average_rounds_per_task': total_rounds / max(len(self.conversation_history), 1)
            },
            'recent_tasks': self.conversation_history[-5:] if self.conversation_history else []
        }
    
    def get_llm_statistics(self) -> Dict[str, Any]:
        """Get LLM client statistics"""
        return self.llm_client.get_statistics()
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = [] 