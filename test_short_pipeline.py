#!/usr/bin/env python3
"""
短Pipeline测试 - 只运行前3天，验证reasoning和对话流保存功能
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import run_pipeline
from utils.config_loader import get_default_config
import json

def test_short_pipeline():
    """运行短Pipeline测试"""
    print("=" * 60)
    print("Short Pipeline Test - First 3 Days")
    print("验证Judge reasoning和完整对话流保存功能")
    print("=" * 60)
    
    # 获取配置
    cfg = get_default_config()
    cfg.session_name = "test_short_pipeline_with_reasoning"
    cfg.verbose = True
    cfg.save_results = True
    
    # 修改配置使测试更快
    cfg.max_interaction_rounds = 2  # 减少轮次
    cfg.p_deceptive = 0.5  # 增加deceptive概率以便测试
    cfg.p_positive = 0.2   
    cfg.p_random_audit = 0.3  # 增加audit概率
    
    print(f"Modified config: deceptive={cfg.p_deceptive:.0%}, audit={cfg.p_random_audit:.0%}")
    
    # 临时修改任务列表，只运行前3天
    from tasks import get_all_tasks
    all_tasks = get_all_tasks()
    first_3_tasks = [task for task in all_tasks if task.day <= 3]
    
    print(f"Running {len(first_3_tasks)} tasks (first 3 days)")
    
    # 临时monkey patch
    original_get_all_tasks = None
    import tasks
    original_get_all_tasks = tasks.get_all_tasks
    tasks.get_all_tasks = lambda: first_3_tasks
    
    try:
        # 运行pipeline
        run_pipeline(cfg)
        
        # 检查结果文件
        results_dir = f"results/production"
        sessions = [d for d in os.listdir(results_dir) if "test_short_pipeline_with_reasoning" in d]
        if sessions:
            latest_session = sorted(sessions)[-1]
            session_path = os.path.join(results_dir, latest_session)
            
            print(f"\n📁 检查结果文件: {session_path}")
            
            # 检查conversation_flows.json
            conv_flows_file = os.path.join(session_path, "conversation_flows.json")
            if os.path.exists(conv_flows_file):
                print("✅ conversation_flows.json 已生成")
                
                with open(conv_flows_file, 'r', encoding='utf-8') as f:
                    flows = json.load(f)
                
                print(f"   包含 {len(flows)} 天的对话流")
                
                # 显示第一天的对话流结构
                if flows:
                    first_flow = flows[0]
                    print(f"   第一天结构:")
                    print(f"   - Task: Day {first_flow['task_info']['day']} - {first_flow['task_info']['title']}")
                    print(f"   - Variant: {first_flow['task_info']['variant_used']}")
                    print(f"   - Rounds: {len(first_flow['rounds'])}")
                    print(f"   - Judge detected deception: {first_flow['judge_evaluation']['deception_detected']}")
                    if first_flow['judge_evaluation']['deception_detected']:
                        print(f"     Category: {first_flow['judge_evaluation']['category']}")
                        print(f"     Reasoning: {first_flow['judge_evaluation']['explanation'][:100]}...")
                    print(f"   - Manager final trust: {first_flow['manager_final_state']['trust_level']}")
            else:
                print("❌ conversation_flows.json 未找到")
            
            # 检查其他结果文件
            result_files = os.listdir(session_path)
            print(f"   生成的文件: {result_files}")
            
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复原始函数
        if original_get_all_tasks:
            tasks.get_all_tasks = original_get_all_tasks
    
    print("\n" + "=" * 60)
    print("Short pipeline test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_short_pipeline() 