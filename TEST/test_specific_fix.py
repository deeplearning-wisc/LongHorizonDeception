#!/usr/bin/env python3
"""
专门测试之前失败的Invalid_Pressure_Test现在是否正确通过
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.event import EventSystem

def test_invalid_pressure_now_works():
    """测试Invalid_Pressure_Test现在应该正确失败"""
    print("🔍 Testing Invalid_Pressure_Test fix...")
    
    # 模拟严谨测试中的Invalid_Pressure_Test场景
    config = {
        'control_category': 'UNCONTROL',
        'control_pressure_level': 'INVALID_PRESSURE',  # 这个应该导致错误
        'name': 'Invalid_Pressure_Test',
        'test_type': 'error_expected',
        'expected_error': 'Invalid control_pressure_level'
    }
    
    try:
        # 尝试创建EventSystem - 这应该失败
        event_system = EventSystem(
            "market_research_series",
            p_event=1.0,
            control_category=config['control_category'],
            control_pressure_level=config['control_pressure_level'],
            seed=1000,
            total_tasks=14
        )
        
        print("❌ FAIL: Expected error but EventSystem creation succeeded")
        return False
        
    except ValueError as e:
        if "Invalid control_pressure_level" in str(e):
            print(f"✅ PASS: Correctly caught expected error: {e}")
            return True
        else:
            print(f"❌ FAIL: Got ValueError but wrong message: {e}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Got unexpected error type: {type(e).__name__}: {e}")
        return False

def test_empty_category_still_works():
    """测试Empty_Category_Test仍然正确工作"""
    print("🔍 Testing Empty_Category_Test still works...")
    
    try:
        event_system = EventSystem(
            "market_research_series",
            p_event=1.0,
            control_category="",  # 空字符串应该失败
            control_pressure_level="UNCONTROL",
            seed=1000,
            total_tasks=14
        )
        
        print("❌ FAIL: Expected error but EventSystem creation succeeded")
        return False
        
    except ValueError as e:
        if "Invalid control_category" in str(e):
            print(f"✅ PASS: Correctly caught error: {e}")
            return True
        else:
            print(f"❌ FAIL: Got ValueError but wrong message: {e}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Got unexpected error: {type(e).__name__}: {e}")
        return False

def main():
    """运行关键修复验证测试"""
    print("🔬 Specific Bug Fix Verification")
    print("="*50)
    
    tests = [
        test_invalid_pressure_now_works,
        test_empty_category_still_works
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Critical Fix Tests: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 Critical bug fixes working correctly!")
        print("   - Invalid pressure levels now properly rejected")
        print("   - Parameter validation working as expected")
        print("   - No fallback mechanisms remaining")
    else:
        print("❌ Some critical fixes still not working properly")

if __name__ == "__main__":
    main()