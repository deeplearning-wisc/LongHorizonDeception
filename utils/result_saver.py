import json
import yaml
import time
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from tasks.task import Task

class ResultSaver:
    """
    New ResultSaver based on TaskStream and UniversalLLM standards
    Implements the new file structure:
    results/{task_stream_name}_{timestamp}/
    ├── stream_info.txt           # Runtime info with task-event table
    ├── stream_config.yaml        # Config snapshot
    └── result.json               # Complete experiment data (incremental updates)
    """
    
    def __init__(self, task_stream_name: str, total_tasks: int, task_event_stream: List[Dict[str, Any]], config: Dict[str, Any], config_name: str = None):
        """
        Initialize ResultSaver with complete context information
        
        Args:
            task_stream_name: Name of the task stream
            total_tasks: Total number of tasks
            task_event_stream: Complete task-event assignments  
            config: Full experiment configuration (with task_stream_metadata)
            config_name: Original config filename (e.g., 'medium.yaml')
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = f"{task_stream_name}_{timestamp}"
        
        # Store core objects
        self.task_stream_name = task_stream_name
        self.total_tasks = total_tasks
        self.task_event_stream = task_event_stream
        self.config = config
        self.config_name = config_name or 'config.yaml'  # Default fallback
        
        # Extract task_stream metadata from config - FAIL-FAST if missing
        task_stream_metadata = config['task_stream_metadata']
        phase_description = task_stream_metadata['phase_description']
        
        # Create results directory
        self.results_dir = Path("results") / self.session_name
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize result.json structure
        self.result_data = {
            "metadata": {
                "task_stream_name": task_stream_name,
                "total_tasks": total_tasks,
                "phases": len(phase_description),
                "phase_description": phase_description
            },
            "experiment": {
                "global_rounds": 0,
                "tasks": []
            }
        }
        
        # Initialize files immediately
        self._create_stream_info_txt()
        self._create_stream_config_yaml()
        self._create_initial_result_json()
        
        print(f"[RESULT_SAVER] Session initialized: {self.session_name}")
    
    def _create_stream_info_txt(self) -> None:
        """Create stream_info.txt with runtime information and task-event table"""
        info_file = self.results_dir / "stream_info.txt"
        
        # Extract control parameters - MUST exist for experimental rigor
        control_category = self.config['control_category']
        control_pressure_level = self.config['control_pressure_level']
        control_parts = []
        if control_category:
            control_parts.append(f"Category={control_category}")
        if control_pressure_level:
            control_parts.append(f"Pressure_Level={control_pressure_level}")
        control_str = ", ".join(control_parts) if control_parts else "None"
        
        # Get LLM configuration info - MUST exist
        llm_api_config = self.config['llm_api_config']
        llm_provider = llm_api_config['llm']
        manager_provider = llm_api_config['manager']
        
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(f"DeceptioN Experiment Session Information\\n")
            f.write(f"Generated: {datetime.now().isoformat()}\\n")
            f.write(f"=" * 80 + "\\n\\n")
            
            # Basic Information
            f.write(f"PROJECT INFORMATION:\\n")
            f.write(f"  Name: {self.task_stream_name}\\n")
            f.write(f"  Total Tasks: {self.total_tasks}\\n")
            f.write(f"  Phases: {len(self.config['task_stream_metadata']['phase_description'])}\\n")
            f.write(f"  Event Probability: {self.config['p_event']}\\n")
            f.write(f"  Event Seed: {self.config['event_seed']}\\n")
            f.write(f"  Control Parameters: {control_str}\\n")
            f.write(f"\\n")
            
            # LLM Configuration
            f.write(f"LLM CONFIGURATION:\\n")
            f.write(f"  LLM Provider: {llm_provider}\\n")
            f.write(f"  Manager Provider: {manager_provider}\\n")
            f.write(f"\\n")
            
            # Phase Information
            f.write(f"PHASE STRUCTURE:\\n")
            phase_info = self.config['task_stream_metadata']['phase_description']
            for phase_key, phase_data in sorted(phase_info.items()):
                f.write(f"  {phase_key}: {phase_data['name']} (Tasks {phase_data['task_start']}-{phase_data['task_end']})\\n")
            f.write(f"\\n")
            
            # Task-Event Assignment Table
            f.write(f"TASK-EVENT ASSIGNMENTS:\\n")
            f.write(f"{'Task':>4}  {'Title':<25} {'Event':<30} {'Pressure':<10} {'Category'}\\n")
            f.write(f"-" * 80 + "\\n")
            
            # Group by phases
            sorted_phases = list(sorted(phase_info.items()))
            for phase_key, phase_data in sorted_phases:
                start_task = phase_data['task_start']
                end_task = phase_data['task_end']
                
                f.write(f"\\n{phase_data['name']} (Tasks {start_task}-{end_task}):\\n")
                
                for i, task_info in enumerate(self.task_event_stream, 1):
                    if start_task <= i <= end_task:
                        task = task_info['task']
                        event = task_info['event']
                        
                        title = task.title[:24] + "..." if len(task.title) > 24 else task.title
                        event_name = event['name'][:29] + "..." if len(event['name']) > 29 else event['name']
                        
                        f.write(f"{i:>4}  {title:<25} {event_name:<30} {event['pressure_level']:<10} {event['category']}\\n")
            
            f.write(f"\\n" + "=" * 80 + "\\n")
            f.write(f"Additional runtime information will be appended below:\\n\\n")
    
    def _create_stream_config_yaml(self) -> None:
        """Create config backup with original filename"""
        config_file = self.results_dir / self.config_name
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
        
        print(f"[RESULT_SAVER] Config snapshot saved: {config_file}")
    
    def _create_initial_result_json(self) -> None:
        """Create initial result.json with metadata"""
        result_file = self.results_dir / "result.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.result_data, f, indent=2, ensure_ascii=False)
        
        print(f"[RESULT_SAVER] Initial result.json created")
    
    def add_task_data(self, task_sequence_num: int, task: Task, event_info: Dict[str, Any]) -> None:
        """
        Add new task structure to result.json
        Called when starting a new task
        """
        task_data = {
            "task": {
                "task_sequence_num": task_sequence_num,
                "title": task.title,
                "base_prompt": task.base_prompt,
                "files": [
                    {
                        "filename": f.filename,
                        "content": f.content,
                        "file_type": "text"  # Default type, can be enhanced
                    }
                    for f in task.files
                ] if task.files else []
            },
            "event": {
                "name": event_info['name'],
                "content": event_info['content'],
                "pressure_level": event_info['pressure_level'],
                "category": event_info['category'],
                "triggered": True  # All events in task_event_stream are triggered
            },
            "rounds": []
        }
        
        # Add to in-memory structure
        self.result_data["experiment"]["tasks"].append(task_data)
        
        # Immediately save to JSON file for data persistence
        self._save_result_json()
    
    def save_interaction_round(self, task_sequence_num: int, round_num: int, global_round: int,
                              llm_response: str, manager_result: Dict[str, Any]) -> None:
        """
        Save a single interaction round and update result.json immediately
        
        Args:
            task_sequence_num: Task sequence number (1-indexed)
            round_num: Round number within task (1-indexed) 
            global_round: Global round number across all tasks
            llm_response: LLM's response string
            manager_result: Manager's complete evaluation result
        """
        round_data = {
            "round": round_num,
            "global_round": global_round,
            "llm_response": llm_response,
            "manager_evaluation": {
                "evaluation_reasoning": manager_result['evaluation_reasoning'],
                "state_updates": manager_result['state_updates'],
                "feedback_reasoning": manager_result['feedback_reasoning'],
                "feedback_response": manager_result['feedback_response'],
                "task_complete": manager_result['task_complete']
            }
        }
        
        # Find the correct task and add round
        task_index = task_sequence_num - 1
        if task_index < len(self.result_data["experiment"]["tasks"]):
            self.result_data["experiment"]["tasks"][task_index]["rounds"].append(round_data)
            
            # Update global round count
            self.result_data["experiment"]["global_rounds"] = global_round
            
            # Immediately save to file (incremental update)
            self._save_result_json()
            
            print(f"[RESULT_SAVER] Round saved - Task {task_sequence_num}, Round {round_num}, Global {global_round}")
        else:
            print(f"[RESULT_SAVER] ERROR: Task {task_sequence_num} not found for round saving")
    
    def _save_result_json(self) -> None:
        """Save current result_data to result.json file"""
        result_file = self.results_dir / "result.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.result_data, f, indent=2, ensure_ascii=False)
    
    def append_to_stream_info(self, message: str) -> None:
        """
        Append additional information to stream_info.txt
        Can be called anytime during experiment
        """
        info_file = self.results_dir / "stream_info.txt"
        
        with open(info_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\\n")
    
    def finalize_experiment(self) -> None:
        """
        Finalize experiment - add final timestamps and summary
        """
        # Add completion timestamp to stream_info
        self.append_to_stream_info(f"Experiment completed - Total global rounds: {self.result_data['experiment']['global_rounds']}")
        
        # Final save to ensure everything is persisted
        self._save_result_json()
        
        print(f"[RESULT_SAVER] Experiment finalized: {self.results_dir}")
        print(f"[RESULT_SAVER] Total tasks: {len(self.result_data['experiment']['tasks'])}")
        print(f"[RESULT_SAVER] Total global rounds: {self.result_data['experiment']['global_rounds']}")
    
    def add_error_data(self, task_sequence_num: int, round_num: int, global_round: int, error_message: str) -> None:
        """
        Add error information to result when experiment fails
        
        Args:
            task_sequence_num: Task sequence number where error occurred
            round_num: Round number where error occurred  
            global_round: Global round number where error occurred
            error_message: Detailed error message
        """
        error_data = {
            "experiment_failed": True,
            "error_location": {
                "task_sequence_num": task_sequence_num,
                "round_num": round_num,
                "global_round": global_round
            },
            "error_message": error_message,
            "failure_timestamp": datetime.now().isoformat()
        }
        
        # Add error data to result
        self.result_data["experiment"]["error_info"] = error_data
        
        # Log to stream_info
        self.append_to_stream_info(f"EXPERIMENT FAILED at Task {task_sequence_num}, Round {round_num}")
        self.append_to_stream_info(f"Error: {error_message}")
        
        # Save immediately
        self._save_result_json()