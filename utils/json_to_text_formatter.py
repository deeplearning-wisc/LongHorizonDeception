# utils/json_to_text_formatter.py
# JSON to LLM-friendly text formatter - ZERO TRUNCATION, ZERO DEFAULTS
# Strict fail-fast scientific code: any missing data throws exception

from typing import Dict, Any, List


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


def format_detector_context_for_llm(round_data: Dict[str, Any], global_round: int) -> str:
    """
    Convert detector analysis context JSON to LLM-friendly text format
    ZERO TRUNCATION, ZERO DEFAULTS - complete data preservation for detector analysis
    
    Args:
        round_data: Single round data from result.json
        global_round: Global round number for context
        
    Returns:
        Formatted text string with complete context for detector analysis
    """
    # Direct access - fail-fast if data missing
    task = round_data['task']
    event = round_data['event']
    round_info = round_data['rounds'][0]
    llm_response = round_info['llm_response']
    manager_eval = round_info['manager_evaluation']
    
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
    
    # Format event with full details - complete data
    if event['name'] == 'NO_EVENT':
        event_text = "Normal conditions - No pressure event"
    else:
        event_text = f"""PRESSURE EVENT DETECTED:
Type: {event['name']}
Category: {event['category']}
Pressure Level: {event['pressure_level']}
Content: {event['content']}"""
    
    # Format manager's complete analysis - full visibility for detector
    manager_reasoning = manager_eval['evaluation_reasoning']
    feedback_reasoning = manager_eval['feedback_reasoning']
    feedback_response = manager_eval['feedback_response']
    
    # State transitions with full detail - complete data
    prev_state = manager_eval['state_updates']['previous_state']
    new_state = manager_eval['state_updates']['new_state']
    
    state_analysis = f"""MANAGER STATE TRANSITIONS:
Trust Level: {prev_state['trust_level']} → {new_state['trust_level']}
Work Satisfaction: {prev_state['work_satisfaction']} → {new_state['work_satisfaction']}  
Relational Comfort: {prev_state['relational_comfort']} → {new_state['relational_comfort']}"""

    return f"""=== DETECTOR ANALYSIS CONTEXT - ROUND {global_round:03d} ===

TASK INFORMATION:
Task #{task['task_sequence_num']}: {task['title']}

Task Requirements:
{task['base_prompt']}
════════════════════════════════════════

TASK FILES PROVIDED:
{files_text}
════════════════════════════════════════

EVENT CONTEXT:
{event_text}
════════════════════════════════════════

LLM RESPONSE:
{llm_response}
════════════════════════════════════════

MANAGER COMPLETE ANALYSIS (Full Visibility):

Manager Evaluation Reasoning:
{manager_reasoning}

{state_analysis}

Manager Feedback Strategy:
{feedback_reasoning}

Manager Feedback to LLM:
{feedback_response}

Task Completion Status: {manager_eval['task_complete']}
════════════════════════════════════════

=== END CONTEXT ==="""


def format_full_conversation_history(all_rounds_data: List[Dict[str, Any]]) -> str:
    """
    Format complete conversation history for detector pattern analysis
    ZERO TRUNCATION - complete data preservation
    
    Args:
        all_rounds_data: List of all rounds from experiment
        
    Returns:
        Complete conversation history in text format
    """
    history_sections = []
    
    for i, round_data in enumerate(all_rounds_data, 1):
        context = format_detector_context_for_llm(round_data, i)
        history_sections.append(context)
    
    return "\n\n".join(history_sections)


def format_manager_memory_summary(recent_rounds: List[Dict[str, Any]], 
                                  summarized_history: str = "") -> str:
    """
    Format manager memory with K-window recent rounds plus summarized history
    ZERO TRUNCATION - complete data preservation
    
    Args:
        recent_rounds: List of recent K rounds in full detail
        summarized_history: Summarized older history text
        
    Returns:
        Complete memory context for manager
    """
    sections = []
    
    if summarized_history:
        sections.append(f"=== SUMMARIZED HISTORY ===\n{summarized_history}\n")
    
    sections.append("=== RECENT DETAILED ROUNDS ===")
    
    for round_data in recent_rounds:
        memory_text = format_memory_for_llm(round_data)
        sections.append(memory_text)
    
    return "\n".join(sections)