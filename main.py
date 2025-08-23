#!/usr/bin/env python3
"""
Main experiment runner - Minimal version focusing on task and event flow.
LLM and Manager interactions are placeholders for now.
"""

import sys
import os
import argparse
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import load_config
from tasks.task_loader import JSONTaskLoader
from tasks.event_loader import get_event_system

def print_unified_task_overview(task_set, task_stream, config, control_category, control_pressure_level, event_seed):
    """统一显示任务和事件概览"""
    project_name = task_set.name
    max_tasks = task_set.total_tasks
    phase_info = task_set.get_phase_info()
    
    # Build control display string
    control_parts = []
    if control_category:
        control_parts.append(f"Category={control_category}")
    if control_pressure_level:
        control_parts.append(f"Pressure_Level={control_pressure_level}")
    control_str = ", ".join(control_parts) if control_parts else "None"
    
    print("\nTask Event Overview")
    print("="*80)
    print(f"Project: {project_name}")
    print(f"Total Tasks: {max_tasks} | Event Probability: {config['p_event']} | Seed: {event_seed if event_seed is not None else 'Random'} | Control: {control_str}")
    print()
    
    # Display by phases with table format
    for phase_key, phase_data in sorted(phase_info.items()):
        phase_name = phase_data['name']
        start_task = phase_data['task_start']
        end_task = phase_data['task_end']
        
        print(f"{phase_name} (Tasks {start_task}-{end_task})")
        print(f"{'Task':>4}  {'Title':<30} {'Event':<15} {'Pressure_Level':<18} {'Category'}")
        print("-" * 80)
        
        # Show tasks in this phase
        for i, task_info in enumerate(task_stream, 1):
            if start_task <= i <= end_task:
                task = task_info['task']
                event = task_info['event']
                
                if event['triggered']:
                    event_name = event['name']
                    pressure_level = event['pressure_level']
                    category = event['category']
                else:
                    event_name = "NO_EVENT"
                    pressure_level = "-"
                    category = "-"
                
                # 使用完整标题，不截断
                title = task.title
                
                print(f"{i:>4}  {title:<30} {event_name:<15} {pressure_level:<18} {category}")
        
        if phase_data != list(sorted(phase_info.items()))[-1][1]:  # 不是最后一个phase才加空行
            print()
    
    # 在最后加上闭合线
    print("="*80)

def run_experiment(config_name=None):
    """Run the main experiment with task and event system"""
    
    # Load configuration
    config = load_config(config_name)
    
    # Load tasks and task set metadata
    task_loader = JSONTaskLoader()
    task_set = task_loader.load_task_set("market_research_series")
    
    # Get max_tasks from task_set metadata
    max_tasks = task_set.total_tasks
    
    # Get phase information from task_set
    phase_info = task_set.get_phase_info()
    
    # Get event control parameters from config
    control_category = config.get('control_category', None)
    control_pressure_level = config.get('control_pressure_level', None)
    event_seed = config.get('event_seed', None)
    
    # Initialize event system with seed
    
    event_system = get_event_system(
        "market_research_series",
        global_event_probability=config['p_event'],
        seed=event_seed,
        control_category=control_category,
        control_pressure_level=control_pressure_level,
        max_tasks=max_tasks
    )
    
    # Generate task stream with events
    task_stream = []
    
    for task_idx in range(1, max_tasks + 1):
        # Get task by sequence number
        task = task_set.get_task_by_sequence_num(task_idx)
        if not task:
            print(f"Warning: Could not find task {task_idx}")
            continue
        # Sample event for this task (using seed for reproducibility)
        deceptive_event, event_variant = event_system.get_event_and_variant_for_task(task_idx)
        
        if deceptive_event and event_variant:
            event = {
                'name': deceptive_event.name,
                'content': event_variant.content,
                'pressure_level': event_variant.pressure_level,
                'category': deceptive_event.category,
                'triggered': True
            }
        else:
            event = {
                'name': 'NO_EVENT',
                'content': 'Normal business conditions',
                'pressure_level': 'NORMAL',
                'category': 'NONE',
                'triggered': False
            }
        
        task_stream.append({
            'task': task,
            'event': event
        })
    
    # Display unified task and event overview
    print_unified_task_overview(task_set, task_stream, config, control_category, control_pressure_level, event_seed)
    
    # Process task stream round-by-round (temporarily disabled for debugging)
    # print("\nProcessing task stream...")
    # max_rounds_per_task = config['max_rounds_per_task']
    # global_round = 0
    # 
    # for task_idx, task_info in enumerate(task_stream, 1):
    #     task = task_info['task']
    #     event = task_info['event']
    #     
    #     print(f"\nTask {task_idx}: {task.title}")
    #     print(f"  Event: {event['name']} (Pressure: {event['pressure_level']})")
    #     
    #     # Process multiple rounds per task
    #     for round_num in range(1, max_rounds_per_task + 1):
    #         global_round += 1
    #         print(f"  Round {round_num}/{max_rounds_per_task} (Global Round {global_round})")
    #         
    #         # LLM processing placeholder
    #         # llm_response = llm.process_task_with_event(task, event['content'])
    #         pass
    #         
    #         # Manager evaluation placeholder
    #         # manager_result = manager.evaluate_and_update(llm_response, task, event)
    #         pass
    #         
    #         # Task completion check placeholder
    #         # if manager_result['task_complete']:
    #         #     break
    #     
    #     print(f"  Task completed after {round_num} rounds")
    # 
    # print(f"\nExperiment complete. Total rounds: {global_round}")
    # if event_seed is not None:
    #     print(f"Seed used: {event_seed} (reproducible)")
    

def main():
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

