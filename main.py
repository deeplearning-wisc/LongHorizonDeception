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
from tqdm import tqdm
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.config_handler import load_config
from tasks.task import TaskLoader, TaskStream
from tasks.event import EventSystem
from core.LLM import LLM
from core.manager import Manager
from utils.result_saver import ResultSaver

# Constants
NO_EVENT_NAME = "NO_EVENT"
NO_EVENT_CONTENT = "Normal conditions"
NO_EVENT_INDICATOR = "-"

def print_unified_task_overview(task_event_stream: Dict[str, Any], config: Dict[str, Any]) -> None:
    """Display unified task and event overview"""
    # Extract all needed information from task_event_stream
    metadata = task_event_stream['metadata']
    stream_data = task_event_stream['stream']
    
    project_name = metadata['name']
    max_tasks = metadata['total_tasks']
    phase_info = metadata['phase_description']
    
    # Extract control parameters from config
    control_category = config['control_category']
    control_pressure_level = config['control_pressure_level']
    
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
        for i, task_info in enumerate(stream_data, 1):
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
        raise ValueError("Missing required configuration: 'control_category'")
    control_category = config['control_category']
    
    if 'control_pressure_level' not in config:
        raise ValueError("Missing required configuration: 'control_pressure_level'")
    control_pressure_level = config['control_pressure_level']
    
    if 'event_seed' not in config:
        raise ValueError("Missing required configuration: 'event_seed' (use null for auto-generation)")
    event_seed = config['event_seed']
    
    # Generate actual seed if null
    if event_seed is None:
        import time
        event_seed = int(time.time() * 1000000) % (2**32)
        config['event_seed'] = event_seed  # Update config with actual seed
    
    # Initialize event system with seed
    if 'p_event' not in config:
        raise ValueError("Missing required configuration: 'p_event'")
    
    event_system = EventSystem(
        config['task_stream_name'],
        p_event=config['p_event'],
        control_category=control_category,
        control_pressure_level=control_pressure_level,
        seed=event_seed,
        total_tasks=total_tasks
    )
    
    # Generate task stream with events - new structure with metadata
    stream_data = []
    
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
                'category': event_variant['category']
            }
        else:
            event = {
                'name': NO_EVENT_NAME,
                'content': NO_EVENT_CONTENT,
                'pressure_level': NO_EVENT_INDICATOR,
                'category': NO_EVENT_INDICATOR
            }
        
        stream_data.append({
            'task': task,
            'event': event
        })
    
    # Create task_event_stream with metadata
    task_event_stream = {
        'metadata': {
            'name': task_stream.name,
            'total_tasks': task_stream.total_tasks,
            'phase_description': task_stream.get_phase_info()
        },
        'stream': stream_data
    }
    
    # Display unified task and event overview
    print_unified_task_overview(task_event_stream, config)
    
    # Run LLM-Manager interaction
    run_llm_manager_interaction_rounds(task_event_stream, config, config_name)
    

def run_llm_manager_interaction_rounds(task_event_stream: Dict, config: Dict, config_name: str = None) -> None:
    """Run LLM-Manager interaction for all tasks"""
    
    # Get LLM and Manager configurations from config
    # Note: config_handler has already resolved the API profiles
    if 'llm_api_config' not in config:
        raise ValueError("Missing required configuration: 'llm_api_config'")
    llm_api_config = config['llm_api_config']
    print(f"llm_api_config: {llm_api_config}")
    
    # Extract the actual configurations
    # llm_api_config['llm'] is already the full config with structure:
    # {'provider': 'azure', 'azure': {...actual config...}}
    llm_wrapper = llm_api_config['llm']
    manager_wrapper = llm_api_config['manager']
    
    # Get the actual config based on provider
    llm_provider = llm_wrapper['provider']
    manager_provider = manager_wrapper['provider']
    
    _llm_api_config = llm_wrapper[llm_provider]
    _manager_api_config = manager_wrapper[manager_provider]
    
    # Initialize LLM
    if 'llm_system_prompt' not in config:
        raise ValueError("Missing required configuration: 'llm_system_prompt'")
    system_prompt = config['llm_system_prompt']
    llm = LLM(_llm_api_config, system_prompt)
    
    # Initialize Manager
    if 'manager_initial_state' not in config:
        raise ValueError("Missing required configuration: 'manager_initial_state'")
    initial_state = config['manager_initial_state']
    
    if 'manager_evaluation_prompt' not in config:
        raise ValueError("Missing required configuration: 'manager_evaluation_prompt'")
    evaluation_prompt = config['manager_evaluation_prompt']
    
    if 'manager_feedback_prompt' not in config:
        raise ValueError("Missing required configuration: 'manager_feedback_prompt'")
    feedback_prompt = config['manager_feedback_prompt']
    
    if 'manager_memory_prompt' not in config:
        raise ValueError("Missing required configuration: 'manager_memory_prompt'")
    memory_prompt = config['manager_memory_prompt']
    
    if 'task_completion_threshold' not in config:
        raise ValueError("Missing required configuration: 'task_completion_threshold'")
    task_completion_threshold = config['task_completion_threshold']
    
    if 'memory_k_window' not in config:
        raise ValueError("Missing required configuration: 'memory_k_window'")
    memory_k_window = config['memory_k_window']
    
    if 'max_rounds_per_task' not in config:
        raise ValueError("Missing required configuration: 'max_rounds_per_task'")
    max_rounds_per_task = config['max_rounds_per_task']
    
    manager = Manager(
        _manager_api_config, evaluation_prompt, feedback_prompt, memory_prompt,
        initial_state, task_completion_threshold, memory_k_window, max_rounds_per_task
    )
    
    # Initialize result saver with complete context  
    config_filename = f"{config_name}.yaml" if config_name else "config.yaml"
    result_saver = ResultSaver(task_event_stream, config, config_filename)
    global_round = 0
    
    #print("\nStarting LLM-Manager Interaction...")
    #print("=" * 60)
    
    # Main interaction loop with progress bar
    stream_data = task_event_stream['stream']
    total_tasks = task_event_stream['metadata']['total_tasks']
    task_pbar = tqdm(stream_data, desc="Tasks", unit="task")
    
    for task_sequence_num, task_info in enumerate(task_pbar, 1):
        # Create unified task_event object
        task_event = {
            'task': task_info['task'],
            'event': task_info['event'],
            'task_sequence_num': task_sequence_num
        }
        
       #print(f"\n--- Task {task_sequence_num}: {task_event['task'].title} ---")
        #print(f"Event: {task_event['event']['name']}")
        
        # Add task to result saver
        result_saver.add_task_data(task_event)
        
        round_num = 1
        
        # Single task multi-round interaction
        while round_num <= max_rounds_per_task:
            global_round += 1
            
            # Update progress bar to show current task and round
            task_pbar.set_description(f"Task {task_sequence_num}/{total_tasks} - Round {round_num}")
            
            # 1. LLM processes - distinguish first round vs subsequent rounds
            if round_num == 1:
                # First round: LLM processes task with event
                llm_response = llm.process_task_with_event(task_event)
            else:
                # Subsequent rounds: LLM continues conversation based on history
                llm_response = llm.continue_conversation()
            
            #print(f"LLM Response: {llm_response}")
            #print(f"LLM Response: {llm_response[:200]}...")  # Preview
            
            # 2. Manager evaluates (returns clean LLM results) - FAIL-FAST ON PARSE ERRORS
            try:
                manager_raw_result = manager.evaluate(llm_response, task_event, round_num)
            except RuntimeError as e:
                if "FATAL:" in str(e):
                    print(f"\n=== EXPERIMENT TERMINATED ===")
                    print(f"Fatal error during Manager evaluation:")
                    print(f"Task: {task_sequence_num}, Round: {round_num}, Global Round: {global_round}")
                    print(f"Error: {str(e)}")
                    print(f"=== EXPERIMENT FAILED - NO FALLBACK USED ===")
                    
                    # Save incomplete experiment state
                    result_saver.add_error_data(task_sequence_num, round_num, global_round, str(e))
                    result_saver.finalize_experiment()
                    
                    sys.exit(1)
                else:
                    # Re-raise if not our expected fatal error
                    raise
            
            # CRITICAL FIX: Manager.evaluate() has ALREADY updated manager.state internally
            # Use previous_state returned by Manager for accurate state transition tracking
            previous_state = manager_raw_result['previous_state']
            
            # Calculate task completion using threshold
            task_complete = manager_raw_result['state']['work_satisfaction'] >= task_completion_threshold
            
            # Organize final result for result_saver
            manager_result = {
                'evaluation_reasoning': manager_raw_result['evaluation_reasoning'],
                'state_updates': {
                    'previous_state': previous_state,
                    'new_state': manager_raw_result['state']
                },
                'feedback_reasoning': manager_raw_result['feedback_reasoning'],
                'feedback_response': manager_raw_result['feedback_response'],
                'task_complete': task_complete
            }
            
            # Print round-level state changes
            prev_state = previous_state
            curr_state = manager_raw_result['state']
            print(f"  Round {round_num}: Manager evaluation (trust_level: {prev_state['trust_level']}→{curr_state['trust_level']}, work_satisfaction: {prev_state['work_satisfaction']}→{curr_state['work_satisfaction']}, relational_valence: {prev_state['relational_valence']}→{curr_state['relational_valence']})")
            
            if task_complete:
                print(f"  ✓ Task {task_sequence_num} completed after {round_num} rounds!")
            
            # 3. Save interaction round
            result_saver.save_interaction_round(
                task_sequence_num, round_num, global_round,
                llm_response, manager_result
            )
            
            # 4. Check task completion
            if task_complete:
                break
            
            # 5. Add manager feedback, prepare for next round
            llm.add_manager_feedback_response(manager_raw_result['feedback_response'])
            round_num += 1
        
        if round_num > max_rounds_per_task:
            print(f"  → Max rounds reached ({max_rounds_per_task})")
    
    # Finalize experiment
    result_saver.finalize_experiment()
    
    print(f"\nExperiment completed! Total rounds: {global_round}")

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

