#!/usr/bin/env python3
"""
更严格的context overflow处理测试
测试各种边界情况和异常场景
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.Universal_LLM_Client import UniversalLLMClient

def create_realistic_messages():
    """创建更真实的消息序列，模拟实际DeceptioN运行"""
    messages = []
    
    # Task 1 - 完整的3轮对话
    messages.append({"role": "user", "content": "[TASK_01 Round 1] Please continue with your assigned task.\n\nAnalyze market data for Q4 strategy"})
    messages.append({"role": "assistant", "content": "Based on the market data analysis, I recommend the following strategy:\n1. Increase marketing budget by 15%\n2. Focus on digital channels\n3. Target demographic age 25-45" * 50})
    messages.append({"role": "user", "content": "Manager Feedback: Your analysis is good but lacks specific metrics. Please provide more quantitative data."})
    
    messages.append({"role": "user", "content": "[TASK_01 Round 2] Please continue based on feedback"})
    messages.append({"role": "assistant", "content": "Adding quantitative metrics:\n- Expected ROI: 23%\n- Customer acquisition cost: $45\n- Lifetime value: $1,200" * 50})
    messages.append({"role": "user", "content": "Manager Feedback: Better. Now add risk assessment."})
    
    messages.append({"role": "user", "content": "[TASK_01 Round 3] Please finalize with risk assessment"})
    messages.append({"role": "assistant", "content": "Risk assessment complete:\n- Market volatility risk: Medium\n- Competition risk: High\n- Execution risk: Low" * 50})
    messages.append({"role": "user", "content": "Manager Feedback (Task Complete): Well done. Task completed successfully."})
    
    return messages

def test_edge_cases():
    """测试各种边界情况"""
    print("=" * 60)
    print("🧪 STRICT CONTEXT OVERFLOW TESTS")
    print("=" * 60)
    
    # 创建测试客户端
    test_config = {
        'azure_api_key': 'test',
        'azure_endpoint': 'test',
        'azure_api_version': '2024-02-01',
        'azure_deployment': 'test',
        'model_name': 'gpt-4o'
    }
    
    client = UniversalLLMClient('azure', test_config)
    
    # Test 1: 只有2条消息的情况（不应该截断）
    print("\n🔬 Test 1: Minimum messages (should not truncate)")
    print("-" * 40)
    
    min_messages = [
        {"role": "user", "content": "Current task"},
        {"role": "assistant", "content": "Response"}
    ]
    
    result = client._truncate_messages_by_task(min_messages.copy(), 1)
    assert len(result) == 2, f"Should preserve 2 messages, got {len(result)}"
    print("   ✅ Correctly preserved minimum messages")
    
    # Test 2: Task ID格式变化（TASK_01 vs TASK_10 vs TASK_100）
    print("\n🔬 Test 2: Different task ID formats")
    print("-" * 40)
    
    mixed_tasks = [
        {"role": "user", "content": "[TASK_09 Round 1] Task 9"},
        {"role": "assistant", "content": "Response 9"},
        {"role": "user", "content": "Feedback 9"},
        
        {"role": "user", "content": "[TASK_10 Round 1] Task 10"},
        {"role": "assistant", "content": "Response 10"},
        {"role": "user", "content": "Feedback 10"},
        
        {"role": "user", "content": "[TASK_100 Round 1] Task 100"},
        {"role": "assistant", "content": "Response 100"},
        {"role": "user", "content": "Feedback 100"},
        
        {"role": "user", "content": "[TASK_11 Round 1] Current"},
    ]
    
    result = client._truncate_messages_by_task(mixed_tasks.copy(), 1)
    
    # 验证只删除了TASK_09
    has_task_09 = any('[TASK_09' in msg['content'] for msg in result)
    has_task_10 = any('[TASK_10' in msg['content'] for msg in result)
    has_task_100 = any('[TASK_100' in msg['content'] for msg in result)
    
    assert not has_task_09, "Task 09 should be removed"
    assert has_task_10, "Task 10 should remain"
    assert has_task_100, "Task 100 should remain"
    print("   ✅ Correctly handles different task ID formats")
    
    # Test 3: Task内有非标准消息（没有task标记的中间消息）
    print("\n🔬 Test 3: Mixed messages within task")
    print("-" * 40)
    
    mixed_messages = [
        {"role": "user", "content": "[TASK_01 Round 1] Start task"},
        {"role": "assistant", "content": "Working on it..."},
        {"role": "user", "content": "Manager: Continue"},  # 没有task标记
        {"role": "assistant", "content": "More work..."},  # 没有task标记
        {"role": "user", "content": "Manager: Almost there"},  # 没有task标记
        
        {"role": "user", "content": "[TASK_02 Round 1] New task"},
        {"role": "assistant", "content": "Starting new task"},
    ]
    
    result = client._truncate_messages_by_task(mixed_messages.copy(), 1)
    
    # Task 1的所有5条消息都应该被删除
    assert len(result) == 2, f"Should have 2 messages left, got {len(result)}"
    assert '[TASK_02' in result[0]['content'], "Task 2 should be first"
    print("   ✅ Correctly removes all messages of a task")
    
    # Test 4: 连续调用截断
    print("\n🔬 Test 4: Sequential truncations")
    print("-" * 40)
    
    many_tasks = []
    for i in range(1, 6):  # 5个tasks
        many_tasks.append({"role": "user", "content": f"[TASK_{i:02d} Round 1] Task {i}"})
        many_tasks.append({"role": "assistant", "content": f"Response {i}"})
        many_tasks.append({"role": "user", "content": f"Feedback {i}"})
    
    many_tasks.append({"role": "user", "content": "[TASK_06 Round 1] Current"})
    
    # 第1次截断
    result1 = client._truncate_messages_by_task(many_tasks.copy(), 1)
    task1_present = any('[TASK_01' in msg['content'] for msg in result1)
    assert not task1_present, "Task 1 should be removed after first truncation"
    
    # 第2次截断
    result2 = client._truncate_messages_by_task(result1.copy(), 2)
    task2_present = any('[TASK_02' in msg['content'] for msg in result2)
    assert not task2_present, "Task 2 should be removed after second truncation"
    
    # 第3次应该报错
    try:
        result3 = client._truncate_messages_by_task(result2.copy(), 3)
        assert False, "Should have raised error on 3rd attempt"
    except RuntimeError as e:
        assert "persists after removing 2 tasks" in str(e)
    
    print("   ✅ Sequential truncations work correctly")
    
    # Test 5: 只有一个task的多轮对话
    print("\n🔬 Test 5: Single task with multiple rounds")
    print("-" * 40)
    
    single_task = [
        {"role": "user", "content": "[TASK_01 Round 1] Start"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Manager: Continue"},
        
        {"role": "user", "content": "[TASK_01 Round 2] Continue"},  # 同一个task！
        {"role": "assistant", "content": "Response 2"},
        {"role": "user", "content": "Manager: More"},
        
        {"role": "user", "content": "[TASK_01 Round 3] Final"},  # 还是同一个task！
        {"role": "assistant", "content": "Response 3"},
        {"role": "user", "content": "Manager: Done"},
        
        {"role": "user", "content": "[TASK_02 Round 1] New task"},
    ]
    
    result = client._truncate_messages_by_task(single_task.copy(), 1)
    
    # 所有TASK_01的消息都应该被删除（包括Round 2和3）
    task1_present = any('[TASK_01' in msg['content'] for msg in result)
    assert not task1_present, "All rounds of Task 1 should be removed"
    assert len(result) == 1, f"Should have 1 message (Task 2), got {len(result)}"
    
    print("   ✅ Correctly removes all rounds of same task")
    
    # Test 6: 空列表和单消息
    print("\n🔬 Test 6: Edge cases - empty and single message")
    print("-" * 40)
    
    # 空列表
    empty_result = client._truncate_messages_by_task([], 1)
    assert len(empty_result) == 0, "Empty list should remain empty"
    
    # 单消息
    single = [{"role": "user", "content": "Only message"}]
    single_result = client._truncate_messages_by_task(single.copy(), 1)
    assert len(single_result) == 1, "Single message should be preserved"
    
    print("   ✅ Edge cases handled correctly")
    
    # Test 7: 实际DeceptioN格式测试
    print("\n🔬 Test 7: Realistic DeceptioN message format")
    print("-" * 40)
    
    realistic = create_realistic_messages()
    
    # 添加更多tasks
    for i in range(2, 5):
        realistic.append({"role": "user", "content": f"[TASK_{i:02d} Round 1] Please continue with task {i}"})
        realistic.append({"role": "assistant", "content": f"Working on task {i}..." * 100})
        realistic.append({"role": "user", "content": f"Manager Feedback (Task Complete): Task {i} done"})
    
    realistic.append({"role": "user", "content": "[TASK_05 Round 1] Current task in progress"})
    
    print(f"   Initial: {len(realistic)} messages")
    
    # 第1次截断
    result1 = client._truncate_messages_by_task(realistic.copy(), 1)
    print(f"   After 1st truncation: {len(result1)} messages")
    
    # 验证Task 1被完全删除
    task1_rounds = [msg for msg in result1 if '[TASK_01' in msg['content']]
    assert len(task1_rounds) == 0, f"Task 1 should be completely removed, found {len(task1_rounds)} messages"
    
    print("   ✅ Realistic format handled correctly")
    
    print("\n" + "=" * 60)
    print("✅ ALL STRICT TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_edge_cases()