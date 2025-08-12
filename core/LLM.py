# core/LLM.py
# DeceptioN LLM abstraction layer with unified LLM client

from typing import Dict, Any, Optional, List
from tasks.base import Task, TaskFile
from .Universal_LLM_Client import UniversalLLMClient
from utils.error_handler import PipelineErrorHandler, RetryHandler

class LLM:
    """
    DeceptioN LLM that can process tasks with file attachments
    Uses unified LLM client for robust token handling
    """
    
    def __init__(self, llm_provider: str, llm_config: Dict[str, Any], system_prompt: str, max_tokens: int):
        """
        Initialize the DeceptioN LLM
        
        Args:
            llm_provider: API provider (openai/azure)
            llm_config: Provider-specific configuration
            system_prompt: System prompt for the LLM
            max_tokens: Maximum tokens for responses
        """
        self.llm_provider = llm_provider
        self.llm_config = llm_config
        
        # 保持原有属性兼容性 - 从config中提取模型信息
        if llm_provider == 'openai':
            self.model_name = llm_config.get('model', 'gpt-4o')
            # 为将来扩展保留
            self.azure_api_key = None
            self.azure_endpoint = None
            self.azure_deployment = None
            self.api_version = None
        else:  # Azure
            self.model_name = llm_config.get('model_name', 'gpt-4o')
            self.azure_api_key = llm_config.get('azure_api_key')
            self.azure_endpoint = llm_config.get('azure_endpoint') 
            self.azure_deployment = llm_config.get('azure_deployment')
            self.api_version = llm_config.get('api_version')
        
        if system_prompt is None:
            raise ValueError("system_prompt is required and cannot be None")
        self.system_prompt = system_prompt
        
        self.max_tokens = max_tokens
        
        # 🆕 添加重试处理器
        self.retry_handler = RetryHandler(max_retries=3)
        
        # Use universal LLM client - supports OpenAI and Azure
        self.llm_client = UniversalLLMClient(llm_provider, llm_config)
        
        # 获取模型的context限制
        self.context_limit = self.llm_client.model_limits.context_window
        
        # Memory/context tracking
        self.conversation_history = []
        
        # 🆕 全局对话历史管理 (跨Task连续记忆)
        self.global_conversation_history = []
        
        # 当前任务内的回复历史 - 用于构建ChatGPT风格消息
        self.current_task_responses = []
        self.current_task_id = None
    
    def _estimate_context_size(self, base_prompt: str, event_content: str, files: List[TaskFile]) -> int:
        """估算当前context大小 (包含全局历史)"""
        # 粗略估算：4个字符≈1个token
        size = len(self.system_prompt) // 4  # 系统提示词
        size += len(base_prompt) // 4
        
        if event_content and event_content != 'Normal business conditions':
            size += len(event_content) // 4
        
        # 计算全局对话历史大小
        for interaction in self.global_conversation_history:
            size += len(interaction['llm_response']) // 4
            size += len(interaction['manager_feedback']) // 4
        
        # 计算文件内容大小
        if files:
            for file_obj in files:
                size += len(file_obj.content) // 4
        
        # 加上格式化字符的估算
        size += 1000  # 格式化字符和其他overhead
        
        return size
    
    def _truncate_global_history(self, max_history_tokens: int = 100000):
        """智能截断全局对话历史，保留最近的交互"""
        if not self.global_conversation_history:
            return
        
        # 计算当前历史大小
        total_tokens = 0
        for interaction in self.global_conversation_history:
            total_tokens += len(interaction['llm_response']) // 4
            total_tokens += len(interaction['manager_feedback']) // 4
        
        # 如果超过限制，从最早的开始删除
        while total_tokens > max_history_tokens and len(self.global_conversation_history) > 1:
            # 移除最早的交互
            removed = self.global_conversation_history.pop(0)
            total_tokens -= len(removed['llm_response']) // 4
            total_tokens -= len(removed['manager_feedback']) // 4
            if hasattr(self, '_logger') and self._logger:
                self._logger.log_warning(f"Truncated history: removed {removed['task_id']} Round {removed['round']}")
    
    def add_interaction_to_global_history(self, task_id: str, round_num: int, llm_response: str, manager_feedback: str, task_complete: bool):
        """添加交互到全局历史"""
        interaction_record = {
            'task_id': task_id,
            'round': round_num,
            'llm_response': llm_response,
            'manager_feedback': manager_feedback,
            'task_complete': task_complete
        }
        self.global_conversation_history.append(interaction_record)
    
    def _build_enhanced_prompt_with_history(self, task: Task, event_content: str) -> str:
        """构建包含全局历史的完整prompt"""
        # 1. 智能截断历史以避免context溢出
        estimated_size = self._estimate_context_size(task.base_prompt, event_content, task.files)
        if hasattr(self, '_logger') and self._logger:
            self._logger.log_info(f"Estimated context size: ~{estimated_size} tokens")
        
        # 动态计算context limit阈值（保留20%余量）
        context_threshold = int(self.context_limit * 0.8)
        if estimated_size > context_threshold:
            if hasattr(self, '_logger') and self._logger:
                self._logger.log_warning(f"Context approaching limit ({estimated_size}/{context_threshold}), truncating history...")
            self._truncate_global_history(max_history_tokens=30000)
            estimated_size_after = self._estimate_context_size(task.base_prompt, event_content, task.files)
            if hasattr(self, '_logger') and self._logger:
                self._logger.log_info(f"Context size after truncation: ~{estimated_size_after} tokens")
        
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
                conversation_context.append(f"Assistant: {interaction['llm_response']}")
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
            Dictionary containing LLM response and metadata
        """
        try:
            # 构建包含全局历史的enhanced prompt
            enhanced_prompt = self._build_enhanced_prompt_with_history(task, event_content)
            
            # 使用enhanced prompt方法处理任务
            return self.process_task_with_enhanced_prompt(task, enhanced_prompt, manager_feedback_history=None)
            
        except Exception as e:
            if hasattr(self, '_logger') and self._logger:
                self._logger.log_error(e, "Error in task processing with event")
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
            Dictionary containing LLM response and metadata
        """
        
        try:
            # 🆕 使用重试机制进行任务处理
            result = self.retry_handler.retry_with_warnings(
                self._single_task_attempt,
                "LLM",
                "task processing",
                task, manager_feedback_history
            )
            return result
                
        except Exception as e:
            error_msg = f"LLM processing failed after retries: {str(e)}"
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
            # Context溢出 - 记录警告但不抛出错误，LLM应该能处理长对话
            if hasattr(self, '_logger') and self._logger:
                self._logger.log_warning(f"Context approaching limit: {estimated_tokens}/{self.context_limit} tokens, prompt length: {len(full_prompt)} chars")
        
        # 如果有logger实例，记录LLM输入
        if hasattr(self, '_logger') and self._logger:
            self._logger.log_llm_input(self.system_prompt, messages, self.model_name, self.max_tokens)

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
        
        llm_response = llm_result['content']
        
        # 7. Store conversation history - 完整保存，不截断
        self.conversation_history.append({
            'task_sequence_num': task.task_sequence_num,
            'task_id': task.task_id,
            'prompt_full': full_prompt,           # 完整prompt
            'response_full': llm_response,      # 完整回复
            'files_provided': len(task.files) if task.files else 0,
            'llm_rounds': llm_result['total_rounds'],
            'tokens_used': llm_result['tokens_used']
        })
        
        return {
            'response': llm_response,
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
            Dictionary containing LLM response and metadata
        """
        
        # 🆕 构建ChatGPT风格的消息序列
        has_global_history = len(self.global_conversation_history) > 0
        has_task_feedback = manager_feedback_history and len(manager_feedback_history) > 0
        
        if has_global_history or has_task_feedback:
            # 有全局历史或Manager反馈历史 - 构建交错的对话序列
            messages = self._build_chatgpt_style_messages(task, enhanced_prompt, manager_feedback_history)
            full_prompt = f"ChatGPT-style conversation ({len(messages)} messages)"
        else:
            # 完全新的开始 - 使用传统的单消息格式
            file_context = self._build_file_context(task.files)
            full_prompt = self._build_full_prompt(enhanced_prompt, file_context)
            messages = [{"role": "user", "content": full_prompt}]
        
        # 4.5. Check context size before LLM call
        if has_global_history or has_task_feedback:
            # 对于ChatGPT风格消息，估算所有消息的总token数
            total_content = self.system_prompt + "\n".join([msg["content"] for msg in messages])
            estimated_tokens = self.llm_client.estimate_tokens(total_content)
        else:
            estimated_tokens = self.llm_client.estimate_tokens(self.system_prompt + full_prompt)
        
        if estimated_tokens > self.context_limit:
            # Context溢出 - 记录警告但不抛出错误，LLM应该能处理长对话
            if hasattr(self, '_logger') and self._logger:
                if has_global_history or has_task_feedback:
                    self._logger.log_warning(f"Context approaching limit: {estimated_tokens}/{self.context_limit} tokens, ChatGPT-style messages: {len(messages)} total")
                else:
                    self._logger.log_warning(f"Context approaching limit: {estimated_tokens}/{self.context_limit} tokens, prompt length: {len(full_prompt)} chars")
        
        # 如果有logger实例，记录LLM输入
        if hasattr(self, '_logger') and self._logger:
            self._logger.log_llm_input(self.system_prompt, messages, self.model_name, self.max_tokens)
        
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
        
        llm_response = llm_result['content']
        
        # 5.5. 管理当前任务回复历史
        if self.current_task_id != task.task_id:
            # 新任务开始，重置当前任务回复历史
            self.current_task_id = task.task_id
            self.current_task_responses = []
        
        # 添加当前回复到任务内历史
        self.current_task_responses.append(llm_response)
        
        # 6. Store conversation history - 完整保存，不截断
        self.conversation_history.append({
            'task_sequence_num': task.task_sequence_num,
            'task_id': task.task_id,
            'prompt_full': full_prompt if not (has_global_history or has_task_feedback) else f"ChatGPT messages: {len(messages)}",
            'response_full': llm_response,      # 完整回复
            'files_provided': len(task.files) if task.files else 0,
            'llm_rounds': llm_result['total_rounds'],
            'tokens_used': llm_result['tokens_used']
        })
        
        return {
            'response': llm_response,
            'prompt_used': full_prompt if not (has_global_history or has_task_feedback) else f"ChatGPT-style conversation ({len(messages)} messages)",
            'messages_used': messages if (has_global_history or has_task_feedback) else None,
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
    
    def _build_chatgpt_style_messages(self, task: Task, enhanced_prompt: str, manager_feedback_history: List[str]) -> List[Dict[str, str]]:
        """
        构建ChatGPT风格的消息序列 - 完整的任务序列历史
        
        实现架构：
        Task 1: R1 → LLM → Manager → R2 → LLM → Manager → R3 → LLM → Manager(完成)
        Task 2: R1 → LLM → Manager → R2 → LLM → Manager(完成)  
        Task 3: R1 → LLM → Manager(完成)
        Current Task: R1 → LLM → ?
        
        Args:
            task: 当前Task object
            enhanced_prompt: 当前任务的enhanced prompt  
            manager_feedback_history: 当前任务内的Manager反馈历史
            
        Returns:
            ChatGPT风格的消息列表
        """
        messages = []
        
        # 1. 添加所有已完成的任务历史（按时间顺序）
        for interaction in self.global_conversation_history:
            task_id = interaction.get('task_id', 'UNKNOWN')
            round_num = interaction.get('round', 1)
            
            # 任务开始消息（每轮都要重新说明任务）
            task_content = f"[{task_id} Round {round_num}] Please continue with your assigned task."
            messages.append({
                "role": "user",
                "content": task_content
            })
            
            # LLM的回复
            llm_response = interaction.get('llm_response', '')
            if llm_response:
                messages.append({
                    "role": "assistant", 
                    "content": llm_response
                })
            
            # Manager的反馈
            manager_feedback = interaction.get('manager_feedback', '')
            if manager_feedback:
                # 如果任务完成，明确标注
                task_complete = interaction.get('task_complete', False)
                feedback_prefix = "Manager Feedback (Task Complete): " if task_complete else "Manager Feedback: "
                messages.append({
                    "role": "user",
                    "content": feedback_prefix + manager_feedback
                })
        
        # 2. 添加当前任务的初始消息
        file_context = self._build_file_context(task.files)
        current_task_content = self._build_full_prompt(enhanced_prompt, file_context)
        
        # 当前任务的轮次
        current_round = len(manager_feedback_history) + 1
        task_header = f"[{task.task_id} Round {current_round}]"
        
        messages.append({
            "role": "user",
            "content": f"{task_header} {current_task_content}"
        })
        
        # 3. 添加当前任务内的历史轮次（如果有）
        for i, feedback in enumerate(manager_feedback_history):
            # 添加当前任务之前轮次的LLM回复（如果有）
            if i < len(self.current_task_responses):
                messages.append({
                    "role": "assistant",
                    "content": self.current_task_responses[i]
                })
            
            # 添加Manager的反馈
            messages.append({
                "role": "user",
                "content": f"Manager Feedback: {feedback}"
            })
        
        return messages
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of LLM's conversation history"""
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