from typing import Dict, Any
from tasks.task import Task
from core.Universal_LLM_Handler import UniversalLLMHandler

class Performer:
    """
    Simple LLM class - wraps Universal_LLM_Handler
    """
    
    def __init__(self, llm_config: Dict[str, Any], system_prompt: str):
        """Initialize LLM with config and system prompt"""
        self.config = llm_config
        self.system_prompt = system_prompt
        
        # Wrapper around Universal handler
        provider = llm_config['provider']
        verbose_print = llm_config['verbose_print'] if 'verbose_print' in llm_config else False
        
        self.handler = UniversalLLMHandler(
            provider=provider,
            config=llm_config,
            verbose_print=verbose_print
        )
        
        # Set system prompt
        self.handler.set_system_prompt(system_prompt)
    
    def process_task_with_event(self, task_event: Dict[str, Any]) -> str:
        """
        Process task with event content, return LLM response
        
        Args:
            task_event: Unified task_event object containing task, event, and task_sequence_num
        
        Returns:
            LLM response string
        """
        # Extract task and event from unified object
        task = task_event['task']
        event_content = task_event['event']['content']
        
        # Build prompt from task + event
        prompt = self._build_prompt(task, event_content)
        # print(f"LLM Prompt: {prompt}")
        # Add user message to handler
        self.handler.add_user_message(prompt)
        
        # Generate response
        response = self.handler.generate_response()
        
        # Debug print message list - RED for first round
        print(f"\033[91m[LLM-FIRST-ROUND] core/LLM.py:process_task_with_event - Message count: {len(self.handler.messages)}\033[0m")
        # # print(f"\033[91m[DEBUG] Message list in process_task_with_event:\033[0m")
        # for i, msg in enumerate(self.handler.messages):
        #     content_preview = msg['content'][:100] + ('...' if len(msg['content']) > 100 else '')
        #     print(f"\033[91m  [{i}] {msg['role']}: {content_preview}\033[0m")
        return response
    
    def add_manager_feedback_response(self, feedback_response: str) -> None:
        """Add manager feedback to message history"""
        # print(f"\033[93m[DEBUG] Adding manager feedback - before: {len(self.handler.messages)} messages\033[0m")
        self.handler.add_user_message(f"Manager feedback response: {feedback_response}")
        # print(f"\033[93m[DEBUG] Adding manager feedback - after: {len(self.handler.messages)} messages\033[0m")
        # print(f"\033[93m[DEBUG] Feedback content: {feedback_response[:100]}{'...' if len(feedback_response) > 100 else ''}\033[0m")
    
    def continue_conversation(self) -> str:
        """
        Continue conversation based on existing message history
        Used for rounds after the first one
        
        Returns:
            LLM response string
        """
        # Generate response based on current message history
        # (which already includes previous messages and manager feedback)
        response = self.handler.generate_response()
        
        # Debug print message list - GREEN for subsequent rounds
        print(f"\033[92m[LLM-CONTINUE] core/LLM.py:continue_conversation - Message count: {len(self.handler.messages)}\033[0m")
        # print(f"\033[92m[DEBUG] Message list in continue_conversation:\033[0m")
        # for i, msg in enumerate(self.handler.messages):
        #     content_preview = msg['content'][:100] + ('...' if len(msg['content']) > 100 else '')
        #     print(f"\033[92m  [{i}] {msg['role']}: {content_preview}\033[0m")
        
        return response
    
    def _build_prompt(self, task: Task, event_content: str) -> str:
        """Build complete prompt with smooth natural language flow"""
        
        # Start with natural task introduction
        prompt = f"Now we need to complete the following task:\n\n"
        
        # Add task header with clear separation
        prompt += "=" * 50 + "\n"
        prompt += f"TASK: {task.title}\n"
        prompt += "=" * 50 + "\n\n"
        
        # Add the main task prompt
        prompt += f"{task.base_prompt}\n"
        
        # Add files section if present
        if task.files:
            prompt += "\nRELEVANT FILES:\n"
            prompt += "-" * 30 + "\n"
            for task_file in task.files:
                prompt += f"\n📄 {task_file.filename}\n"
                prompt += f"{task_file.content}\n"
                prompt += "-" * 30 + "\n"
        
        # Add event context with smooth transition if present
        if event_content and event_content.strip():
            prompt += "\n" + "=" * 50 + "\n"
            prompt += "CURRENT EXTERNAL EVENTS\n"
            prompt += "=" * 50 + "\n"
            prompt += (
                "Please note that the following external events may influence the task context.\n"
                "Carefully consider them and, where relevant, address their impact with concrete actions, clarifications, or risk mitigations.\n\n"
            )
            prompt += f"{event_content}\n"
            prompt += "=" * 50 + "\n"
        
        # Add clear call to action
        prompt += "\nPlease proceed to complete the task now, taking into account all the information provided above."
        
        return prompt
