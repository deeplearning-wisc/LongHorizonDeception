import json
import os
import time
from typing import Dict, Any, List
from pathlib import Path
from tasks.task import Task

class ResultSaver:
    """
    New ResultSaver for LLM-Manager interaction experiments
    Saves complete interaction data in structured JSON format
    """
    
    def __init__(self, experiment_name: str):
        """Initialize ResultSaver with experiment name"""
        self.experiment_name = experiment_name
        self.experiment_data = {
            'experiment_info': {
                'name': experiment_name,
                'start_timestamp': time.time(),
                'total_tasks': 0,
                'total_rounds': 0,
                'config': {}
            },
            'task_interactions': []
        }
        
        # Create results directory
        self.results_dir = Path("results") / experiment_name
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def set_experiment_config(self, config: Dict[str, Any]) -> None:
        """Set experiment configuration"""
        self.experiment_data['experiment_info']['config'] = config
    
    def add_task_interaction(self, task_sequence_num: int, task: Task, event_info: Dict[str, Any]) -> None:
        """Add new task interaction structure"""
        task_interaction = {
            'task_info': {
                'sequence_num': task_sequence_num,
                'title': task.title,
                'base_prompt': task.base_prompt,
                'files': [{'name': f.filename, 'content': f.content} for f in task.files] if task.files else []
            },
            'event_info': event_info,
            'rounds': []
        }
        
        self.experiment_data['task_interactions'].append(task_interaction)
    
    def save_interaction_round(self, task_sequence_num: int, round_num: int, global_round: int,
                              llm_response: str, manager_result: Dict[str, Any]) -> None:
        """
        Save a single interaction round
        
        Args:
            task_sequence_num: Task sequence number (1-indexed)
            round_num: Round number within task (1-indexed) 
            global_round: Global round number across all tasks
            llm_response: LLM's response string
            manager_result: Manager's complete evaluation result
        """
        round_data = {
            'round_num': round_num,
            'global_round': global_round,
            'task_complete': manager_result['task_complete'],
            'llm_response': llm_response,
            'manager_evaluation': manager_result
        }
        
        # Find the correct task interaction and add round
        task_interaction = self.experiment_data['task_interactions'][task_sequence_num - 1]
        task_interaction['rounds'].append(round_data)
        
        # Update counters
        self.experiment_data['experiment_info']['total_rounds'] = global_round
    
    def save_experiment_summary(self, total_tasks: int) -> None:
        """Save final experiment summary"""
        self.experiment_data['experiment_info']['total_tasks'] = total_tasks
        self.experiment_data['experiment_info']['end_timestamp'] = time.time()
        
        # Calculate duration
        start_time = self.experiment_data['experiment_info']['start_timestamp']
        end_time = self.experiment_data['experiment_info']['end_timestamp']
        self.experiment_data['experiment_info']['duration_seconds'] = end_time - start_time
        
        # Save complete experiment data
        output_file = self.results_dir / "experiment_results.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.experiment_data, f, indent=2, ensure_ascii=False)
        
        print(f"Experiment results saved to: {output_file}")
        
        # Save summary file
        self._save_summary_file()
    
    def _save_summary_file(self) -> None:
        """Save human-readable summary"""
        summary_file = self.results_dir / "experiment_summary.txt"
        
        info = self.experiment_data['experiment_info']
        duration = info['duration_seconds']
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Experiment: {info['name']}\n")
            f.write(f"Duration: {duration:.2f} seconds\n")
            f.write(f"Total Tasks: {info['total_tasks']}\n")
            f.write(f"Total Rounds: {info['total_rounds']}\n")
            f.write("\nTask Completion Summary:\n")
            
            for i, task_interaction in enumerate(self.experiment_data['task_interactions'], 1):
                task_title = task_interaction['task_info']['title']
                rounds = len(task_interaction['rounds'])
                completed = task_interaction['rounds'][-1]['task_complete'] if rounds > 0 else False
                
                f.write(f"Task {i}: {task_title} - {rounds} rounds - {'Completed' if completed else 'Incomplete'}\n")