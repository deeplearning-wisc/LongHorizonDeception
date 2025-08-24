#!/usr/bin/env python3
"""
测试bug修复是否有效
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.event import EventSystem

def test_invalid_pressure_fix():
    """测试无效pressure_level是否正确抛出错误"""
    print("🔍 Testing invalid pressure level fix...")
    
    try:
        event_system = EventSystem(
            "market_research_series",
            p_event=1.0,
            seed=1000,
            control_category="UNCONTROL",
            control_pressure_level="INVALID_PRESSURE",  # 无效的压力级别
            total_tasks=14
        )
        print("❌ FAIL: Expected error but got success")
        return False
    except ValueError as e:
        print(f"✅ PASS: Correctly caught error: {e}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Got unexpected error: {e}")
        return False

def test_invalid_category_fix():
    """测试无效category是否正确抛出错误"""
    print("🔍 Testing invalid category fix...")
    
    try:
        event_system = EventSystem(
            "market_research_series",
            p_event=1.0,
            seed=1000,
            control_category="INVALID_CATEGORY",  # 无效的类别
            control_pressure_level="UNCONTROL",
            total_tasks=14
        )
        print("❌ FAIL: Expected error but got success")
        return False
    except ValueError as e:
        print(f"✅ PASS: Correctly caught error: {e}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Got unexpected error: {e}")
        return False

def test_valid_parameters():
    """测试有效参数是否正常工作"""
    print("🔍 Testing valid parameters still work...")
    
    try:
        event_system = EventSystem(
            "market_research_series",
            p_event=1.0,
            seed=1000,
            control_category="GOAL_CONFLICT",  # 有效类别
            control_pressure_level="HIGH",      # 有效压力级别
            total_tasks=14
        )
        print("✅ PASS: Valid parameters work correctly")
        return True
    except Exception as e:
        print(f"❌ FAIL: Valid parameters failed: {e}")
        return False

def main():
    """运行所有测试"""
    print("🔬 Bug Fix Verification Tests")
    print("="*50)
    
    tests = [
        test_invalid_pressure_fix,
        test_invalid_category_fix,
        test_valid_parameters
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Bug fix successful!")
    else:
        print("❌ Some tests failed. Bug fix needs more work.")

if __name__ == "__main__":
    main()