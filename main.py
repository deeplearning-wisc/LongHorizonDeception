#!/usr/bin/env python3
"""
Main experiment runner - Minimal version focusing on task and event flow.
LLM and Manager interactions are placeholders for now.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import load_config
from tasks.task import TaskLoader, TaskStream
from tasks.event import EventSystem

# Constants
NO_EVENT_NAME = "NO_EVENT"
NO_EVENT_CONTENT = "Normal conditions"
NO_EVENT_INDICATOR = "-"

def print_unified_task_overview(task_set: TaskStream, task_event_stream: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    """Display unified task and event overview"""
    project_name = task_set.name
    max_tasks = task_set.total_tasks
    phase_info = task_set.get_phase_info()
    
    # Extract control parameters from config
    control_category = config.get('control_category')
    control_pressure_level = config.get('control_pressure_level')
    
    # Build control display string
    control_parts = []
    if control_category:
        control_parts.append(f"Category={control_category}")
    if control_pressure_level:
        control_parts.append(f"Pressure_Level={control_pressure_level}")
    control_str = ", ".join(control_parts) if control_parts else "None"
    
    print("\nTask Event Overview")
    print("="*105)
    print(f"Project: {project_name}")
    print(f"Total Tasks: {max_tasks} | Event Probability: {config['p_event']} | Seed: {config['event_seed']} | Control: {control_str}")
    print()
    
    # Display by phases with table format
    sorted_phases = list(sorted(phase_info.items()))
    last_phase_key = sorted_phases[-1][0]
    
    for phase_key, phase_data in sorted_phases:
        phase_name = phase_data['name']
        start_task = phase_data['task_start']
        end_task = phase_data['task_end']
        
        print(f"{phase_name} (Tasks {start_task}-{end_task})")
        print(f"{'Task':>4}  {'Title':<20} {'Event':<45} {'Pressure_Level':<15} {'Category'}")
        print("-" * 105)
        
        # Show tasks in this phase
        for i, task_info in enumerate(task_event_stream, 1):
            if start_task <= i <= end_task:
                task = task_info['task']
                event = task_info['event']
                
                event_name = event['name']
                pressure_level = event['pressure_level']
                category = event['category']
                
                # 使用完整标题，不截断
                title = task.title
                
                print(f"{i:>4}  {title:<20} {event_name:<45} {pressure_level:<15} {category}")
        
        # Add blank line between phases (not after last phase)
        if phase_key != last_phase_key:
            print()
    
    # 在最后加上闭合线
    print("="*105)

def run_experiment(config_name: Optional[str] = None) -> None:
    """Run the main experiment with task and event system"""
    
    # Load configuration
    config = load_config(config_name)
    
    # Load tasks and task stream metadata
    if 'task_stream_name' not in config:
        raise ValueError("Missing 'task_stream_name' field in config")
    
    task_loader = TaskLoader()
    task_stream = task_loader.load_task_stream(config['task_stream_name'])
    
    # Get total_tasks from task_stream metadata
    total_tasks = task_stream.total_tasks
    
    # Get event control parameters from config
    if 'control_category' not in config:
        raise ValueError("Missing 'control_category' field in config")
    if 'control_pressure_level' not in config:
        raise ValueError("Missing 'control_pressure_level' field in config")
    if 'event_seed' not in config:
        raise ValueError("Missing 'event_seed' field in config")
        
    control_category = config['control_category']
    control_pressure_level = config['control_pressure_level']
    event_seed = config['event_seed']
    
    # Generate actual seed if null
    if event_seed is None:
        import time
        event_seed = int(time.time() * 1000000) % (2**32)
        config['event_seed'] = event_seed  # Update config with actual seed
    
    # Initialize event system with seed
    
    event_system = EventSystem(
        config['task_stream_name'],
        p_event=config['p_event'],
        control_category=control_category,
        control_pressure_level=control_pressure_level,
        seed=event_seed,
        total_tasks=total_tasks
    )
    
    # Generate task stream with events
    task_event_stream = []
    
    for task_sequence_num in range(1, total_tasks + 1):
        # Get task by sequence number
        task = task_stream.get_task_by_sequence_num(task_sequence_num)
        if not task:
            raise ValueError(f"Task {task_sequence_num} not found in task stream. Task stream may be corrupted or total_tasks is incorrect.")
        # Sample event for this task (using seed for reproducibility)
        phase = task_stream.get_phase_for_task(task_sequence_num)  # TaskLoader处理phase逻辑
        event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_sequence_num)  # EventSystem处理事件逻辑
        
        if event_obj and event_variant:
            event = {
                'name': event_variant['name'],
                'content': event_variant['content'],
                'pressure_level': event_variant['pressure_level'],
                'category': event_variant['category'],
                'triggered': True
            }
        else:
            event = {
                'name': NO_EVENT_NAME,
                'content': NO_EVENT_CONTENT,
                'pressure_level': NO_EVENT_INDICATOR,
                'category': NO_EVENT_INDICATOR,
                'triggered': False
            }
        
        task_event_stream.append({
            'task': task,
            'event': event
        })
    
    # Display unified task and event overview
    print_unified_task_overview(task_stream, task_event_stream, config)
    

def main() -> None:
    parser = argparse.ArgumentParser(description='DeceptioN Experiment Runner')
    parser.add_argument('--config', type=str, default=None,
                       help='Configuration file name (without .yaml extension)')
    parser.add_argument('--list-configs', action='store_true',
                       help='List available configuration files')
    
    args = parser.parse_args()
    
    if args.list_configs:
        # List available configs
        configs_dir = Path("configs")
        if configs_dir.exists():
            print("Available configurations:")
            for config_file in sorted(configs_dir.glob("*.yaml")):
                if config_file.name != "api_profiles.yaml":
                    print(f"  - {config_file.stem}")
        sys.exit(0)
    
    # Run experiment
    run_experiment(args.config)

if __name__ == "__main__":
    main()

