#!/usr/bin/env python3
"""
Smart Logging System Test Script
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project path
sys.path.append(str(Path(__file__).parent))

from utils.logger import start_smart_logging, stop_smart_logging, auto_register_content

def test_smart_logging():
    """Test smart logging system"""
    
    print("=" * 60)
    print("Testing Smart Logging System - Keep original print unchanged, save non-truncated versions")
    print("=" * 60)
    
    # Create test session
    test_session_path = f"Deception/results/test/test_smart_logging_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Start smart logging
    logger = start_smart_logging(test_session_path)
    
    try:
        print("[TEST] Smart logging system started")
        
        # Test 1: Long Agent response
        print("\n--- Test 1: Agent Response Truncation ---")
        long_agent_response = "This is a very long Agent response containing extensive detail information. " * 50
        auto_register_content(agent_response=long_agent_response, task_id="test_task_1")
        
        # Simulate original print behavior (truncated)
        print(f"[AGENT RESPONSE]:\n{long_agent_response[:500]}{'...' if len(long_agent_response) > 500 else ''}\n")
        
        # Test 2: Judge reasoning truncation
        print("\n--- Test 2: Judge Reasoning Truncation ---")
        long_judge_explanation = "Judge's detailed reasoning process includes in-depth analysis of various factors, considering context, intent, potential risks and multiple dimensions. " * 20
        auto_register_content(judge_explanation=long_judge_explanation, task_id="test_task_2")
        
        print(f"[JUDGE VERDICT]: Deception detected: True")
        print(f"  Reasoning: {long_judge_explanation[:300]}{'...' if len(long_judge_explanation) > 300 else ''}")
        
        # Test 3: Manager feedback truncation
        print("\n--- Test 3: Manager Feedback Truncation ---")
        long_manager_feedback = "Manager's detailed feedback includes comprehensive evaluation and guidance on work quality, completion level, improvement suggestions and other aspects. " * 30
        auto_register_content(manager_feedback=long_manager_feedback, task_id="test_task_3")
        
        print(f"[MANAGER TO AGENT]: {long_manager_feedback[:800]}{'...' if len(long_manager_feedback) > 800 else ''}")
        
        # Test 4: Full prompt truncation
        print("\n--- Test 4: Prompt Truncation ---")
        long_prompt = "This is a very detailed task prompt containing background information, specific requirements, constraints, expected output and complete content. " * 40
        auto_register_content(prompt_used=long_prompt, task_id="test_task_4")
        
        print(f"Task context includes full prompt: {long_prompt[:300]}{'...' if len(long_prompt) > 300 else ''}")
        
        # Test 5: Comprehensive test
        print("\n--- Test 5: Comprehensive Test ---")
        all_content = {
            'agent_response': "Complete Agent response content includes all necessary analysis and conclusions. " * 25,
            'judge_explanation': "Complete Judge reasoning process explains detected issues in detail. " * 15,
            'manager_feedback': "Complete Manager feedback provides comprehensive evaluation and suggestions. " * 20,
            'prompt_used': "Complete task prompt includes all background and requirement information. " * 35
        }
        
        auto_register_content(**all_content, task_id="test_task_5")
        
        print(f"[COMPREHENSIVE TEST] All content registered")
        print(f"Agent: {all_content['agent_response'][:200]}...")
        print(f"Judge: {all_content['judge_explanation'][:150]}...")
        print(f"Manager: {all_content['manager_feedback'][:180]}...")
        
        print("\n[TEST] All tests completed!")
        
    finally:
        # Stop logging system
        stop_smart_logging()
        
        # Check generated log file
        log_file = Path(test_session_path) / "execution_stream.log"
        if log_file.exists():
            print(f"\n✅ Log file generated: {log_file}")
            
            # Show log file size
            file_size = log_file.stat().st_size
            print(f"📊 Log file size: {file_size} bytes")
            
            # Show partial log content
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"📝 Total log lines: {len(lines)}")
                
                print("\n--- Log file beginning ---")
                for line in lines[:10]:
                    print(line.rstrip())
                
                if len(lines) > 20:
                    print("\n--- Log file ending ---")
                    for line in lines[-10:]:
                        print(line.rstrip())
        else:
            print(f"❌ Log file not found: {log_file}")

if __name__ == "__main__":
    test_smart_logging() 