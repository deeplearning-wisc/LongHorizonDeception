"""
Autoregressive Detector - Inherits from BidirectionalDetector but limits context visibility
Only difference: can only see rounds 1 through current round (no future context)
"""

from pathlib import Path
from typing import Dict, Any
from .bidirectional_detector import BidirectionalDetector


class AutoregressiveDetector(BidirectionalDetector):
    """
    Autoregressive detector that analyzes each round with limited sequence visibility
    Can only see rounds 1 through current round (no future context)
    Inherits all other functionality from BidirectionalDetector
    """
    
    def __init__(self, 
                 detector_config: Dict[str, Any],
                 detector_prompt: str,
                 session_dir: str,
                 max_parallel: int = 4):
        """
        Initialize autoregressive detector
        
        Args:
            detector_config: LLM configuration for detector
            detector_prompt: Detailed prompt with taxonomy and rubrics
            session_dir: Directory containing result.json
            max_parallel: Maximum parallel LLM calls (default 4)
        """
        # Call parent constructor
        super().__init__(detector_config, detector_prompt, session_dir, max_parallel)
        
        # Update detector type
        self.detector_type = "autoregressive"
        
        print(f"[AUTOREGRESSIVE_DETECTOR] Initialized for session: {self.session_name}")
        print(f"[AUTOREGRESSIVE_DETECTOR] Max parallel: {max_parallel}")
    
    def prepare_context_for_round(self, global_round: int) -> Dict[str, Any]:
        """
        Prepare LIMITED context for analyzing a specific round
        For autoregressive: includes ONLY rounds 1 through current round (no future context)
        
        Args:
            global_round: Global round number to analyze (1-indexed)
            
        Returns:
            Context dictionary with limited historical information
        """
        # Find the target round data
        target_round_data = None
        target_task_data = None
        
        for task_data in self.experiment_data['experiment']['tasks']:
            for round_data in task_data['rounds']:
                if round_data['global_round'] == global_round:
                    target_round_data = round_data
                    target_task_data = task_data
                    break
            if target_round_data:
                break
        
        if not target_round_data:
            raise ValueError(f"Global round {global_round} not found")
        
        # Collect ONLY rounds 1 through current round (autoregressive constraint)
        limited_rounds = []
        for task_data in self.experiment_data['experiment']['tasks']:
            for round_data in task_data['rounds']:
                if round_data['global_round'] <= global_round:  # Only past and current
                    limited_rounds.append({
                        'global_round': round_data['global_round'],
                        'task_title': task_data['task']['title'],
                        'task_description': task_data['task']['base_prompt'],
                        'event': task_data['event'],
                        'llm_response': round_data['llm_response'],
                        'manager_evaluation': round_data['manager_evaluation'],
                        'is_current': (round_data['global_round'] == global_round)
                    })
        
        # Sort by global round
        limited_rounds.sort(key=lambda x: x['global_round'])
        
        return {
            'detector_type': self.detector_type,
            'target_global_round': global_round,
            'target_task': target_task_data['task'],
            'target_event': target_task_data['event'],
            'target_round_data': target_round_data,
            'complete_history': limited_rounds,  # Limited to past + current only
            'total_rounds': len(limited_rounds)   # Only count available rounds
        }