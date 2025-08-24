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
        """Build complete prompt from task and event"""
        prompt_parts = [task.base_prompt]
        
        # Add file contents if present
        if task.files:
            prompt_parts.append("\n=== RELEVANT FILES ===")
            for task_file in task.files:
                prompt_parts.append(f"\n--- {task_file.filename} ---")
                prompt_parts.append(task_file.content)
        
        # Add event content
        prompt_parts.append(f"\n=== CURRENT SITUATION ===\n{event_content}")
        
        return "\n".join(prompt_parts)