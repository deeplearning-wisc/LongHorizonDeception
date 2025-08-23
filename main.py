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

def run_experiment(config_name=None):
    """Run the main experiment with task and event system"""
    
    # Load configuration
    config = load_config(config_name)
    
    # Load tasks and task set metadata
    print("Loading tasks...")
    task_loader = JSONTaskLoader()
    task_set = task_loader.load_task_set("market_research_series")
    
    # Print task overview
    task_set.print_all_tasks_overview()
    
    # Get max_tasks from task_set metadata
    max_tasks = task_set.total_tasks
    
    # Get phase information from task_set
    phase_info = task_set.get_phase_info()
    
    print(f"Starting DeceptioN Experiment")
    print(f"Task Count: {max_tasks} tasks")
    
    # Display phase breakdown
    for phase_key, phase_data in sorted(phase_info.items()):
        phase_name = phase_data['name']
        start = phase_data['task_start']
        end = phase_data['task_end']
        print(f"  {phase_key}: Tasks {start}-{end} ({phase_name})")
    
    print(f"Will process {max_tasks} tasks")
    
    # Get event control parameters from config
    control_category = config.get('control_category', None)
    control_pressure_level = config.get('control_pressure_level', None)
    event_seed = config.get('event_seed', None)
    
    # Initialize event system with seed
    print(f"\nInitializing event system...")
    print(f"  Seed: {event_seed if event_seed is not None else 'Random'}")
    print(f"  P(event): {config['p_event']}")
    if control_category:
        print(f"  Control Category: {control_category}")
    if control_pressure_level:
        print(f"  Control Pressure Level: {control_pressure_level}")
    
    event_system = get_event_system(
        "market_research_series",
        global_event_probability=config['p_event'],
        seed=event_seed,
        control_category=control_category,
        control_pressure_level=control_pressure_level,
        max_tasks=max_tasks
    )
    
    # Generate task stream with events
    print(f"\nGenerating task-event stream...")
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
    
    # Display event sequence
    print("\n" + "="*60)
    print("EVENT SEQUENCE (Generated with seed)")
    print("="*60)
    
    # Use already loaded phase information
    
    for i, task_info in enumerate(task_stream, 1):
        task = task_info['task']
        event = task_info['event']
        
        # Determine phase based on loaded phase_description
        phase = None
        for phase_key, phase_data in phase_info.items():
            if phase_data['task_start'] <= i <= phase_data['task_end']:
                phase = phase_key.replace('_', '').capitalize()  # phase_1 -> Phase1
                break
        
        if not phase:
            phase = f"Phase?"  # Fallback if task is outside defined phases
        
        if event['triggered']:
            print(f"Task {i:2d} [{phase}]: {event['name']:<20} | {event['pressure_level']:<8} | {event['category']}")
        else:
            print(f"Task {i:2d} [{phase}]: NO_EVENT")
    
    print("="*60)
    
    # Process task stream round-by-round
    print("\nProcessing task stream...")
    max_rounds_per_task = config['max_rounds_per_task']
    global_round = 0
    
    for task_idx, task_info in enumerate(task_stream, 1):
        task = task_info['task']
        event = task_info['event']
        
        print(f"\nTask {task_idx}: {task.title}")
        print(f"  Event: {event['name']} (Pressure: {event['pressure_level']})")
        
        # Process multiple rounds per task
        for round_num in range(1, max_rounds_per_task + 1):
            global_round += 1
            print(f"  Round {round_num}/{max_rounds_per_task} (Global Round {global_round})")
            
            # LLM processing placeholder
            # llm_response = llm.process_task_with_event(task, event['content'])
            pass
            
            # Manager evaluation placeholder
            # manager_result = manager.evaluate_and_update(llm_response, task, event)
            pass
            
            # Task completion check placeholder
            # if manager_result['task_complete']:
            #     break
        
        print(f"  Task completed after {round_num} rounds")
    
    print(f"\nExperiment complete. Total rounds: {global_round}")
    if event_seed is not None:
        print(f"Seed used: {event_seed} (reproducible)")

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

