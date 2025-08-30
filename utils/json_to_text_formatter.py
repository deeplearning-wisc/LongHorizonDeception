# utils/json_to_text_formatter.py
# JSON to LLM-friendly text formatter - ZERO TRUNCATION, ZERO DEFAULTS
# Strict fail-fast scientific code: any missing data throws exception

from typing import Dict, Any


def format_memory_for_llm(round_data: Dict[str, Any]) -> str:
    """
    Convert manager memory JSON to LLM-friendly text format
    ZERO TRUNCATION, ZERO DEFAULTS - fail-fast on missing data
    
    Args:
        round_data: Single round data from result.json
        
    Returns:
        Formatted text string with complete data preservation
    """
    # Direct access - fail-fast if data missing
    # Manager's actual input format: llm_response and manager_evaluation at top level
    task = round_data['task']
    event = round_data['event'] 
    llm_response = round_data['llm_response']
    manager_eval = round_data['manager_evaluation']
    
    # Format task files information - complete data (same format as memory.py)
    files_text = "No files provided"
    if task['files']:
        files_info = []
        for file in task['files']:
            filename = file['filename']
            content = file['content']  # Complete content, no truncation
            # Use same format as memory.py: FILE: name, separator, indented content, separator
            files_info.append(f"FILE: {filename}")
            files_info.append("----------------------------------------")
            # Indent each line of file content for clarity (same as Manager format)
            indented_content = '\n'.join(['    ' + line for line in content.split('\n')])
            files_info.append(indented_content)
            files_info.append("----------------------------------------")
        files_text = "\n".join(files_info)
    
    # Format event information - complete data
    if event['name'] == 'NO_EVENT':
        event_text = "Normal conditions"
    else:
        event_text = f"{event['name']} (Pressure: {event['pressure_level']})\nContent: {event['content']}"
    

    # print(f"\033[92m[format_memory_for_llm] event_text: {event_text}\033[0m")
    # Format state changes - complete data
    prev_state = manager_eval['state_updates']['previous_state']
    new_state = manager_eval['state_updates']['new_state']
    
    trust_change = f"{prev_state['trust_level']} → {new_state['trust_level']}"
    work_change = f"{prev_state['work_satisfaction']} → {new_state['work_satisfaction']}"
    comfort_change = f"{prev_state['relational_comfort']} → {new_state['relational_comfort']}"
    
    state_text = f"Trust: {trust_change} | Work: {work_change} | Comfort: {comfort_change}"

    ret=f"""=== ROUND MEMORY START ===

TASK INFORMATION:
Task: {task['title']}
Prompt: 
{task['base_prompt']}
════════════════════════════════════════

TASK FILES:
{files_text}
════════════════════════════════════════

EVENT CONTEXT:
{event_text}
════════════════════════════════════════

LLM RESPONSE:
{llm_response}
════════════════════════════════════════

MANAGER ANALYSIS:
Evaluation Reasoning:
{manager_eval['evaluation_reasoning']}

State Changes: {state_text}

Feedback Response:
{manager_eval['feedback_response']}

Task Complete: {manager_eval['task_complete']}
════════════════════════════════════════

══════════════ROUND MEMORY END══════════════"""

    # print(f"\033[92m[format_memory_for_llm] ret: {ret}\033[0m")
    return ret


def format_detector_context_for_llm_single(experiment_data: Dict[str, Any], 
                                           target_global_round: int) -> str:
    """
    Format single round detector analysis context from result.json to LLM-friendly text format
    ZERO TRUNCATION, ZERO DEFAULTS - complete data preservation for detector analysis
    
    Args:
        experiment_data: Complete experiment data from result.json
        target_global_round: Specific global round number to format
        
    Returns:
        Formatted text string for single round context
    """
    # Find the target round across all tasks
    target_task_data = None
    target_round_index = None
    target_round_data = None
    previous_task_sequence_num = None
    
    for task_data in experiment_data['experiment']['tasks']:
        current_task_sequence_num = task_data['task']['task_sequence_num']
        
        for round_index, round_data in enumerate(task_data['rounds']):
            if round_data['global_round'] == target_global_round:
                target_task_data = task_data
                target_round_index = round_index
                target_round_data = round_data
                break
        
        if target_round_data:
            # Determine if this is first round of new task by checking previous rounds
            is_first_round_of_task = True  # Default assume first
            if round_index > 0:
                # Not first round within this task
                is_first_round_of_task = False
            else:
                # First round within this task, check if task changed
                # Find previous global round to see if task changed
                prev_global_round = target_global_round - 1
                if prev_global_round > 0:
                    for prev_task_data in experiment_data['experiment']['tasks']:
                        for prev_round_data in prev_task_data['rounds']:
                            if prev_round_data['global_round'] == prev_global_round:
                                if prev_task_data['task']['task_sequence_num'] == current_task_sequence_num:
                                    is_first_round_of_task = False
                                break
            break
    
    if not target_round_data:
        raise ValueError(f"Global round {target_global_round} not found in experiment data")
    
    # Fix is_first_round_of_task logic: should only be True for round 1 of each task
    task = target_task_data['task']
    event = target_task_data['event'] 
    round_data = target_round_data
    task_round = round_data['round']
    
    # CORRECT logic: first round of task means task_round == 1
    is_first_round_of_task = (task_round == 1)
    
    sections = []
    sections.append(f"=== ROUND {target_global_round:03d} CONTEXT ===")
    sections.append("")
    
    # Include TASK and EVENT information for first round of new task
    if is_first_round_of_task:
        # Task Information
        sections.append("TASK INFORMATION:")
        sections.append(f"Task #{task['task_sequence_num']}: {task['title']}")
        sections.append("")
        sections.append("Task Requirements:")
        sections.append(task['base_prompt'])
        sections.append("=" * 80)
        sections.append("")
        
        # Task Files
        if task['files']:
            sections.append("TASK FILES PROVIDED:")
            for file_data in task['files']:
                filename = file_data['filename']
                content = file_data['content']
                sections.append(f"FILE: {filename}")
                sections.append("-" * 40)
                # Indent each line of file content for clarity
                indented_content = '\n'.join(['    ' + line for line in content.split('\n')])
                sections.append(indented_content)
                sections.append("-" * 40)
                sections.append("")
        else:
            sections.append("TASK FILES PROVIDED:")
            sections.append("No files provided")
            sections.append("")
        
        sections.append("=" * 80)
        sections.append("")
        
        # Event Context
        sections.append("EVENT CONTEXT:")
        if event['name'] == 'NO_EVENT':
            sections.append("Name: NO_EVENT")
            sections.append("Category: -")
            sections.append("Pressure Level: -")
            sections.append("Content: Normal conditions")
        else:
            sections.append(f"Name: {event['name']}")
            sections.append(f"Category: {event['category']}")
            sections.append(f"Pressure Level: {event['pressure_level']}")
            sections.append(f"Content: {event['content']}")
        
        sections.append("=" * 80)
        sections.append("")
    else:
        # Subsequent rounds: only show continuation context
        sections.append(f"Task {task['task_sequence_num']} and its event remains unchanged. Continue the interaction.")
        
        sections.append("=" * 80)
        sections.append("")
    
    # LLM Response (always included)
    llm_response = round_data['llm_response']
    task_round = round_data['round']
    sections.append(f"LLM RESPONSE (Global Round {target_global_round}, Task {task['task_sequence_num']} Round {task_round}):")
    sections.append(llm_response)
    sections.append("=" * 80)
    sections.append("")
    
    # Manager Complete Analysis (always included)
    manager_eval = round_data['manager_evaluation']
    sections.append(f"MANAGER COMPLETE ANALYSIS (Global Round {target_global_round}):")
    sections.append("")
    sections.append("Manager Evaluation Reasoning:")
    sections.append(manager_eval['evaluation_reasoning'])
    sections.append("")
    
    # Manager State Transitions
    prev_state = manager_eval['state_updates']['previous_state']
    new_state = manager_eval['state_updates']['new_state']
    
    sections.append("MANAGER STATE TRANSITIONS:")
    sections.append(f"Trust Level: {prev_state['trust_level']} → {new_state['trust_level']}")
    sections.append(f"Work Satisfaction: {prev_state['work_satisfaction']} → {new_state['work_satisfaction']}")
    sections.append(f"Relational Comfort: {prev_state['relational_comfort']} → {new_state['relational_comfort']}")
    sections.append("")
    
    # Manager Feedback Strategy
    sections.append("Manager Feedback Strategy:")
    sections.append(manager_eval['feedback_reasoning'])
    sections.append("")
    sections.append("Manager Feedback to LLM:")
    sections.append(manager_eval['feedback_response'])
    sections.append("")
    
    sections.append(f"Task Completion Status: {manager_eval['task_complete']}")
    sections.append("=" * 80)
    
    sections.append("=== END CONTEXT ===")
    
    return "\n".join(sections)


def format_detector_context_for_llm_full(experiment_data: Dict[str, Any]) -> str:
    """
    Format complete conversation history for detector pattern analysis
    ZERO TRUNCATION - complete data preservation
    
    Args:
        experiment_data: Complete experiment data from result.json
        
    Returns:
        Complete conversation history in text format using detector format
    """
    history_sections = []
    previous_task_sequence_num = None
    
    for task_data in experiment_data['experiment']['tasks']:
        current_task_sequence_num = task_data['task']['task_sequence_num']
        
        for round_index, round_data in enumerate(task_data['rounds']):
            global_round = round_data['global_round']
            
            # Use single round formatter for each round
            single_context = format_detector_context_for_llm_single(experiment_data, global_round)
            history_sections.append(single_context)
            
            # Update previous task tracking
            previous_task_sequence_num = current_task_sequence_num
    
    return "\n\n".join(history_sections)
