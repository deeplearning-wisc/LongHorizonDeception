#!/usr/bin/env python3
"""
优化测试脚本 - 使用优化配置降低API速率限制问题
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import run_pipeline
from utils.config_loader import load_config

def test_optimized():
    """运行优化测试"""
    print("=" * 60)
    print("Optimized Test - Rate Limit Friendly")
    print("=" * 60)
    
    # 加载优化配置
    cfg = load_config("utils/optimized_config.json")
    cfg.verbose = True
    cfg.session_name = "test_optimized_with_delays"
    
    print(f"Configuration loaded:")
    print(f"  - Deceptive variants: {cfg.p_deceptive:.0%}")
    print(f"  - Max rounds: {cfg.max_interaction_rounds}")
    print(f"  - Random audit: {cfg.p_random_audit:.0%}")
    print(f"  - Token limit: {cfg.max_tokens}")
    
    # 临时只运行前2天来测试
    from tasks import get_all_tasks
    all_tasks = get_all_tasks()
    test_tasks = [task for task in all_tasks if task.day <= 2]
    
    print(f"Running first {len(test_tasks)} tasks for optimization test")
    
    # 临时monkey patch
    import tasks
    original_get_all_tasks = tasks.get_all_tasks
    tasks.get_all_tasks = lambda: test_tasks
    
    try:
        # 运行pipeline
        run_pipeline(cfg)
        print("✅ Optimized test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复原始函数
        tasks.get_all_tasks = original_get_all_tasks
    
    print("=" * 60)

if __name__ == "__main__":
    test_optimized() 