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
        
        # Recent K rounds - full detail (FIFO)
        self.recent_rounds: deque = deque(maxlen=k_window)
        
        # Summarized older memory
        self.summary_memory: List[str] = []
        
        # Hard-coded: Memory LLM must NOT truncate - needs complete context for summarization
        self.memory_llm = UniversalLLMHandler(
            provider=memory_llm_config['provider'],
            config=memory_llm_config,
            verbose_print=memory_llm_config.get('verbose_print', False),
            truncation="disabled"  # Hard-coded disable - fail if context overflows
        )
        self.memory_llm.set_system_prompt(memory_prompt)
    
    def add_interaction_round(self, round_data: Dict[str, Any]) -> None:
        """
        Add a new interaction round to memory
        When recent_rounds exceeds K, oldest gets summarized and moved to summary_memory
        
        Args:
            round_data: Complete interaction data for this round
        """
        # Check if we need to summarize the oldest round
        if len(self.recent_rounds) == self.k_window:
            # Get the oldest round that will be pushed out
            oldest_round = self.recent_rounds[0]
            
            # Summarize it and add to summary memory
            summary = self._generate_summary(oldest_round)
            self.summary_memory.append(summary)
        
        # Add new round (this will automatically remove oldest if at capacity)
        self.recent_rounds.append(round_data)
    
    def get_memory_context(self) -> str:
        """
        Get formatted memory context for Manager evaluation
        Returns JSON-embedded text format to distinguish from normal conversation
        """
        context_parts = []
        
        # Recent complete interactions (last K rounds)
        if self.recent_rounds:
            context_parts.append(f"Recent complete interactions (last {len(self.recent_rounds)} rounds):")
            for i, round_data in enumerate(self.recent_rounds, 1):
                # Format as embedded JSON for system-like appearance
                round_json = json.dumps(round_data, indent=2, ensure_ascii=False)
                context_parts.append(f"[ROUND_{i}] {round_json}")
        
        # Earlier summarized memory
        if self.summary_memory:
            context_parts.append("\nEarlier summarized memory:")
            for i, summary in enumerate(self.summary_memory, 1):
                context_parts.append(f"[SUMMARY_{i}] {summary}")
        
        if not context_parts:
            return "No previous interaction memory."
        
        return "\n".join(context_parts)
    
    def _generate_summary(self, round_data: Dict[str, Any]) -> str:
        """
        Generate human-like summary of an interaction round using LLM
        
        Args:
            round_data: Complete round data to summarize
            
        Returns:
            Human-like summary string
        """
        # Format round data for summarization
        round_json = json.dumps(round_data, indent=2, ensure_ascii=False)
        
        prompt = f"""Please summarize this interaction round in a human-like, thoughtful way:

{round_json}

Summarize as if you're a manager writing personal notes/comments about this interaction."""
        
        try:
            self.memory_llm.add_user_message(prompt)
            summary = self.memory_llm.generate_response()
            return summary.strip()
        except Exception as e:
            # Fallback to basic summary if LLM fails
            return f"[ERROR: Could not generate summary - {str(e)}] Round with {len(str(round_data))} characters"