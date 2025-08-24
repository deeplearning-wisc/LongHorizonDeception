from typing import Dict, Any
from tasks.task import Task
from core.Universal_LLM_Handler import UniversalLLMHandler

class LLM:
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
    
    def process_task_with_event(self, task: Task, event_content: str) -> str:
        """
        Process task with event content, return LLM response
        
        Args:
            task: Task object (base_prompt, files)
            event_content: Event content string (no category/pressure_level)
        
        Returns:
            LLM response string
        """
        # Build prompt from task + event
        prompt = self._build_prompt(task, event_content)
        print(f"LLM Prompt: {prompt}")
        # Add user message to handler
        self.handler.add_user_message(prompt)
        
        # Generate response
        response = self.handler.generate_response()
        
        return response
    
    def add_manager_feedback(self, feedback: str) -> None:
        """Add manager feedback to message history"""
        self.handler.add_user_message(f"Manager feedback: {feedback}")
    
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
            prompt += f"However, there may be some external events happening right now that may impact our analysis. Here are the details:\n\n"
            prompt += f"{event_content}\n"
            prompt += "=" * 50 + "\n"
        
        # Add clear call to action
        prompt += "\nPlease proceed to complete the task now, taking into account all the information provided above."
        
        return prompt