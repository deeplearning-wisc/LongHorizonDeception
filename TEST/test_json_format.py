#!/usr/bin/env python3
"""
JSON Format Validation Test
验证event_set.json和tasks.json格式的正确性，特别是检查：
1. categories应该是5个，没有typo
2. pressure levels应该是4个，没有typo  
3. 其他格式一致性检查
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_event_set_format():
    """测试event_set.json的格式正确性"""
    print("=== Testing event_set.json ===")
    
    event_file = project_root / "tasks" / "data" / "market_research_series" / "event_set.json"
    
    with open(event_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 收集所有categories和pressure levels
    categories = set()
    pressure_levels = set()
    
    phases = data.get("phases", {})
    
    for phase_name, phase_data in phases.items():
        print(f"\n--- Phase: {phase_name} ---")
        events = phase_data.get("events", [])
        print(f"Events count: {len(events)}")
        
        for event in events:
            # 收集category
            category = event.get("category")
            if category:
                categories.add(category)
            
            # 收集pressure levels
            variants = event.get("variants", {})
            for variant_name, variant_data in variants.items():
                pressure_level = variant_data.get("pressure_level")
                if pressure_level:
                    pressure_levels.add(pressure_level)
    
    print(f"\n=== RESULTS ===")
    print(f"Categories found ({len(categories)}): {sorted(categories)}")
    print(f"Pressure levels found ({len(pressure_levels)}): {sorted(pressure_levels)}")
    
    # 验证数量
    expected_categories = 5
    expected_pressure_levels = 4
    
    if len(categories) != expected_categories:
        print(f"ERROR: Expected {expected_categories} categories, found {len(categories)}")
        return False
    else:
        print(f"Categories count correct: {len(categories)}")
    
    if len(pressure_levels) != expected_pressure_levels:
        print(f"ERROR: Expected {expected_pressure_levels} pressure levels, found {len(pressure_levels)}")
        return False
    else:
        print(f"Pressure levels count correct: {len(pressure_levels)}")
    
    # 检查预期的值（基于你之前提到的）
    expected_categories_list = {
        "GOAL_CONFLICT", 
        "COMPETITIVE_INTERACTION", 
        "MORAL_DILEMMA", 
        "AUTHORITY_DIRECTIVE", 
        "INFORMATION_GAP"
    }
    
    expected_pressure_levels_list = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    
    if categories != expected_categories_list:
        print(f"ERROR: Categories mismatch!")
        print(f"Expected: {sorted(expected_categories_list)}")
        print(f"Found: {sorted(categories)}")
        print(f"Missing: {sorted(expected_categories_list - categories)}")
        print(f"Extra: {sorted(categories - expected_categories_list)}")
        return False
    
    if pressure_levels != expected_pressure_levels_list:
        print(f"ERROR: Pressure levels mismatch!")
        print(f"Expected: {sorted(expected_pressure_levels_list)}")
        print(f"Found: {sorted(pressure_levels)}")
        print(f"Missing: {sorted(expected_pressure_levels_list - pressure_levels)}")
        print(f"Extra: {sorted(pressure_levels - expected_pressure_levels_list)}")
        return False
    
    print("All categories and pressure levels match expected values")
    return True

def test_tasks_format():
    """测试tasks.json的格式正确性"""
    print("\n=== Testing tasks.json ===")
    
    tasks_file = project_root / "tasks" / "data" / "market_research_series" / "tasks.json"
    
    with open(tasks_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    task_set = data.get("task_set", {})
    tasks = data.get("tasks", [])
    
    print(f"Task set name: {task_set.get('name')}")
    print(f"Total tasks: {task_set.get('total_tasks')}")
    print(f"Tasks count in array: {len(tasks)}")
    
    # 检查total_tasks和实际tasks数量一致
    expected_count = task_set.get('total_tasks')
    actual_count = len(tasks)
    
    if expected_count != actual_count:
        print(f"ERROR: total_tasks ({expected_count}) != actual tasks count ({actual_count})")
        return False
    else:
        print(f"Task count consistency: {expected_count}")
    
    # 检查task sequence numbers
    sequence_nums = []
    for task in tasks:
        seq_num = task.get('task_sequence_num')
        if seq_num:
            sequence_nums.append(seq_num)
    
    expected_sequence = list(range(1, len(tasks) + 1))
    actual_sequence = sorted(sequence_nums)
    
    if actual_sequence != expected_sequence:
        print(f"ERROR: Task sequence numbers mismatch")
        print(f"Expected: {expected_sequence}")
        print(f"Found: {actual_sequence}")
        return False
    else:
        print(f"Task sequence numbers correct: 1-{len(tasks)}")
    
    # 检查phase_description
    phase_desc = task_set.get('phase_description', {})
    print(f"Phases defined: {list(phase_desc.keys())}")
    
    for phase_key, phase_info in phase_desc.items():
        start = phase_info.get('task_start')
        end = phase_info.get('task_end')
        name = phase_info.get('name')
        print(f"  {phase_key}: Tasks {start}-{end} ({name})")
    
    print("tasks.json format validation complete")
    return True

def main():
    """运行所有测试"""
    print("JSON Format Validation Test")
    print("=" * 50)
    
    success = True
    
    # 测试event_set.json
    if not test_event_set_format():
        success = False
    
    # 测试tasks.json  
    if not test_tasks_format():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("ALL TESTS PASSED - JSON formats are correct!")
        print("Ready to proceed with code modifications.")
    else:
        print("TESTS FAILED - Found issues in JSON format!")
        print("Please fix JSON files before proceeding.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)