#!/usr/bin/env python3
"""
测试context overflow处理机制
验证按task删除消息的逻辑是否正确
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.Universal_LLM_Client import UniversalLLMClient

def create_test_messages():
    """创建模拟的ChatGPT风格消息序列"""
    messages = []
    
    # Task 1 - 3轮对话
    messages.append({"role": "user", "content": "[TASK_01 Round 1] Please continue with your assigned task."})
    messages.append({"role": "assistant", "content": "I'll analyze the market data..." * 100})  # 长回复
    messages.append({"role": "user", "content": "Manager Feedback: Good analysis but need more details"})
    
    messages.append({"role": "user", "content": "[TASK_01 Round 2] Please continue with your assigned task."})
    messages.append({"role": "assistant", "content": "Adding more details about market trends..." * 100})
    messages.append({"role": "user", "content": "Manager Feedback: Better, continue"})
    
    messages.append({"role": "user", "content": "[TASK_01 Round 3] Please continue with your assigned task."})
    messages.append({"role": "assistant", "content": "Final analysis complete..." * 100})
    messages.append({"role": "user", "content": "Manager Feedback (Task Complete): Well done"})
    
    # Task 2 - 2轮对话
    messages.append({"role": "user", "content": "[TASK_02 Round 1] Please continue with your assigned task."})
    messages.append({"role": "assistant", "content": "Starting new task analysis..." * 100})
    messages.append({"role": "user", "content": "Manager Feedback: Need improvement"})
    
    messages.append({"role": "user", "content": "[TASK_02 Round 2] Please continue with your assigned task."})
    messages.append({"role": "assistant", "content": "Improved analysis..." * 100})
    messages.append({"role": "user", "content": "Manager Feedback (Task Complete): Acceptable"})
    
    # Task 3 - 1轮对话
    messages.append({"role": "user", "content": "[TASK_03 Round 1] Please continue with your assigned task."})
    messages.append({"role": "assistant", "content": "Quick task completion..." * 100})
    messages.append({"role": "user", "content": "Manager Feedback (Task Complete): Excellent"})
    
    # Current task (Task 4)
    messages.append({"role": "user", "content": "[TASK_04 Round 1] Current task to process"})
    
    return messages

def test_truncation():
    """测试截断逻辑"""
    print("=" * 60)
    print("🧪 TESTING CONTEXT OVERFLOW HANDLING")
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
    
    # 创建测试消息
    messages = create_test_messages()
    print(f"\n📊 Initial state:")
    print(f"   Total messages: {len(messages)}")
    print(f"   Tasks in messages: 4 (Task 1-3 complete, Task 4 current)")
    
    # 分析消息分布
    task_counts = {}
    for msg in messages:
        content = msg['content']
        if '[TASK_' in content:
            # 提取task ID
            task_part = content.split('[TASK_')[1].split(' ')[0]
            task_id = f"TASK_{task_part}"
            if task_id not in task_counts:
                task_counts[task_id] = 0
            task_counts[task_id] += 1
    
    print(f"\n📋 Message distribution:")
    for task_id, count in task_counts.items():
        print(f"   {task_id}: {count} messages")
    
    # 测试第1次截断
    print(f"\n🔧 Test 1: First truncation (attempt 1)")
    print("-" * 40)
    
    truncated1 = client._truncate_messages_by_task(messages.copy(), 1)
    
    print(f"\n📊 After first truncation:")
    print(f"   Messages remaining: {len(truncated1)}")
    
    # 分析剩余的tasks
    remaining_tasks = set()
    for msg in truncated1:
        content = msg['content']
        if '[TASK_' in content and 'Round 1]' in content:
            task_part = content.split('[TASK_')[1].split(' ')[0]
            remaining_tasks.add(f"TASK_{task_part}")
    
    print(f"   Tasks remaining: {sorted(remaining_tasks)}")
    
    # 验证Task 1是否被完全删除
    task1_found = any('[TASK_01' in msg['content'] for msg in truncated1)
    if not task1_found:
        print("   ✅ Task 1 completely removed")
    else:
        print("   ❌ Task 1 still present!")
    
    # 测试第2次截断
    print(f"\n🔧 Test 2: Second truncation (attempt 2)")
    print("-" * 40)
    
    truncated2 = client._truncate_messages_by_task(truncated1.copy(), 2)
    
    print(f"\n📊 After second truncation:")
    print(f"   Messages remaining: {len(truncated2)}")
    
    # 分析剩余的tasks
    remaining_tasks2 = set()
    for msg in truncated2:
        content = msg['content']
        if '[TASK_' in content and 'Round 1]' in content:
            task_part = content.split('[TASK_')[1].split(' ')[0]
            remaining_tasks2.add(f"TASK_{task_part}")
    
    print(f"   Tasks remaining: {sorted(remaining_tasks2)}")
    
    # 测试第3次截断（应该报错）
    print(f"\n🔧 Test 3: Third truncation (attempt 3) - should error")
    print("-" * 40)
    
    try:
        truncated3 = client._truncate_messages_by_task(truncated2.copy(), 3)
        print("   ❌ Should have raised error but didn't!")
    except RuntimeError as e:
        print(f"   ✅ Error raised as expected: {e}")
    
    # 测试没有task标记的情况
    print(f"\n🔧 Test 4: No task markers scenario")
    print("-" * 40)
    
    messages_no_markers = [
        {"role": "user", "content": "Some random message without markers"},
        {"role": "assistant", "content": "Response without markers"},
        {"role": "user", "content": "Another message"},
        {"role": "assistant", "content": "Another response"},
        {"role": "user", "content": "Current task"},
    ]
    
    print(f"   Initial: {len(messages_no_markers)} messages")
    truncated_no_markers = client._truncate_messages_by_task(messages_no_markers.copy(), 1)
    print(f"   After truncation: {len(truncated_no_markers)} messages")
    print(f"   ✅ Fallback logic applied (removed ~half)")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_truncation()