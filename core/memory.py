from typing import Dict, List, Any, Optional
from collections import deque
import json
from core.Universal_LLM_Handler import UniversalLLMHandler

class ManagerMemory:
    """
    Manager's memory system with K-window recent history + summarized older memory
    """
    
    def __init__(self, k_window: int, memory_llm_config: Dict[str, Any], memory_prompt: str):
        """
        Initialize Manager Memory
        
        Args:
            k_window: Number of recent rounds to keep in full detail
            memory_llm_config: LLM config for generating summaries
            memory_prompt: Prompt for summarizing older interactions
        """
        self.k_window = k_window
        self.memory_prompt = memory_prompt
        self.memory_llm_config = memory_llm_config  # Store config for fresh_llm usage
        
        # Recent K rounds - full detail (FIFO)
        self.recent_rounds: deque = deque(maxlen=k_window)
        
        # Summarized older memory
        self.summary_memory: List[str] = []
        
        # Historical files - accumulate ALL files LLM has ever seen
        self.history_files: Dict[str, str] = {}  # filename -> content
    
    def add_interaction_round(self, round_data: Dict[str, Any]) -> None:
        """
        Add a new interaction round to memory
        When recent_rounds exceeds K, oldest gets summarized and moved to summary_memory
        Also accumulates files from this round into history_files
        
        Args:
            round_data: Complete interaction data for this round
        """
        # Update history_files with files from this round
        if 'task' in round_data and 'files' in round_data['task']:
            for file_data in round_data['task']['files']:
                filename = file_data['filename']
                content = file_data['content']
                # Always update (in case file content changed, though unlikely)
                self.history_files[filename] = content
        
        # Check if we need to summarize the oldest round
        if len(self.recent_rounds) == self.k_window:
            # Get the oldest round that will be pushed out
            oldest_round = self.recent_rounds[0]
            
            # Summarize it and add to summary memory
            summary = self._generate_summary(oldest_round)
            # print in terminal red
            # print(f"\033[91m[ManagerMemory] Summarizing oldest round: {summary}\033[0m")
            self.summary_memory.append(summary)
        
        # Add new round (this will automatically remove oldest if at capacity)
        self.recent_rounds.append(round_data)
    
    def get_memory_context(self) -> str:
        """
        Get formatted memory context for Manager evaluation
        Returns JSON-embedded text format to distinguish from normal conversation
        Includes historical files LLM has seen across all interactions
        """
        if not self.recent_rounds and not self.summary_memory and not self.history_files:
            return "No previous interaction memory."
            
        context_parts = []
        
        # Explain the memory structure
        context_parts.append("Memory context contains multiple types of information:")
        context_parts.append("")
        
        # Historical files section - show ALL files LLM has ever seen
        if self.history_files:
            context_parts.append(f"HISTORICAL FILES (ALL files LLM has seen across {len(self.recent_rounds) + len(self.summary_memory)} interactions):")
            context_parts.append("="*80)
            for filename, content in self.history_files.items():
                context_parts.append(f"FILE: {filename}")
                context_parts.append("----------------------------------------")
                # Indent each line of file content for clarity (same as Manager format)
                indented_content = '\n'.join(['    ' + line for line in content.split('\n')])
                context_parts.append(f"{indented_content}")
                context_parts.append("----------------------------------------")
                context_parts.append("")  # Blank line between files
            context_parts.append("")
        
        # Recent complete interactions (last K rounds in reverse chronological order)
        if self.recent_rounds:
            context_parts.append(f"RECENT DETAILED ROUNDS (latest {len(self.recent_rounds)} rounds in reverse chronological order):")
            context_parts.append("="*80)
            
            # Reverse the order - most recent first, numbered continuously
            recent_list = list(self.recent_rounds)
            for i, round_data in enumerate(reversed(recent_list)):
                # Format as embedded JSON for system-like appearance
                round_json = json.dumps(round_data, indent=2, ensure_ascii=False)
                
                # Continuous numbering: 1_ROUND_BEFORE, 2_ROUNDS_BEFORE, etc.
                rounds_before = i + 1
                label = f"[{rounds_before}_ROUND{'S' if rounds_before > 1 else ''}_BEFORE]"
                
                context_parts.append(f"{label} {round_json}")
                context_parts.append("-"*40)  # Clear separator between rounds
            
            context_parts.append("")
        
        # Earlier summarized memory (older interactions) - continue the numbering
        if self.summary_memory:
            context_parts.append("EARLIER SUMMARIZED MEMORY (older interactions):")
            context_parts.append("="*80)
            
            # Continue numbering from where recent rounds left off
            start_num = len(self.recent_rounds) + 1
            for i, summary in enumerate(self.summary_memory):
                summary_num = start_num + i
                context_parts.append(f"[{summary_num}_ROUNDS_BEFORE] {summary}")
                context_parts.append("-"*40)  # Clear separator between summaries
        
        return "\n".join(context_parts)
    
    def _generate_summary(self, round_data: Dict[str, Any]) -> str:
        """
        Generate human-like summary of an interaction round using fresh LLM
        
        Args:
            round_data: Complete round data to summarize
            
        Returns:
            Human-like summary string
        """
        # Format round data for summarization
        round_json = json.dumps(round_data, indent=2, ensure_ascii=False)
        
        try:
            # Create fresh LLM object for each summary to avoid context accumulation
            fresh_llm = UniversalLLMHandler(
                provider=self.memory_llm_config['provider'],
                config=self.memory_llm_config,
                verbose_print=False,
                overflow_truncate=False  # 严格模式：Memory摘要需要完整数据
            )
            fresh_llm.set_system_prompt(self.memory_prompt)
            
            # User input is the complete round data
            fresh_llm.add_user_message(round_json)
            summary = fresh_llm.generate_response()
            
            # Debug print - MAGENTA for memory summary
            print(f"\033[95m[MEMORY-SUMMARY] core/memory.py:_generate_summary - Generated summary\033[0m")
            
            return summary.strip()
        except Exception as e:
            # Fail-fast: Memory summary is critical for Manager state
            print(f"[ManagerMemory] Memory summarization failed - TERMINATING EXPERIMENT")
            raise RuntimeError(f"FATAL: ManagerMemory summarization failed: {str(e)}")