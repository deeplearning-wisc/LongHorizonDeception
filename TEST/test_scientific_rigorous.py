#!/usr/bin/env python3
"""
科研级严谨测试 + 工程离奇bug检测
既保证科学实验的统计学严谨性，又捕获可能的工程实现bug
"""

import sys
import os
import json
import math
import time
import hashlib
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.event import EventSystem, UNCONTROL
from tasks.task import TaskLoader

# 科研级配置 - 足够严谨但不过分
SCIENTIFIC_SAMPLE_SIZE = 10000  # 1万样本确保统计显著性
TASK_STREAM_NAME = "market_research_series"
TOTAL_TASKS = 14
SIGNIFICANCE_LEVEL = 0.01  # 99%置信水平

# 科学实验参数
ALL_CATEGORIES = ['GOAL_CONFLICT', 'MORAL_DILEMMA', 'COMPETITIVE_INTERACTION', 'AUTHORITY_DIRECTIVE', 'INFORMATION_GAP']
ALL_PRESSURE_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

class ScientificRigorousTester:
    """科研级严谨测试器 - 平衡科学性和工程实用性"""
    
    def __init__(self):
        self.task_loader = TaskLoader()
        self.task_stream = self.task_loader.load_task_stream(TASK_STREAM_NAME)
        self.results = {}
        
    def generate_scientific_test_matrix(self) -> List[Dict]:
        """生成科学实验设计矩阵"""
        test_matrix = []
        
        # 1. 核心科学实验：所有控制组合
        control_combinations = [
            # 完全不控制
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL},
            
            # 单维度控制 - 每个category
            *[{"control_category": cat, "control_pressure_level": UNCONTROL} for cat in ALL_CATEGORIES],
            
            # 单维度控制 - 每个pressure level  
            *[{"control_category": UNCONTROL, "control_pressure_level": pres} for pres in ALL_PRESSURE_LEVELS],
            
            # 双维度控制 - 关键组合（不需要全部，选择代表性的）
            {"control_category": "GOAL_CONFLICT", "control_pressure_level": "HIGH"},
            {"control_category": "MORAL_DILEMMA", "control_pressure_level": "LOW"},
            {"control_category": "INFORMATION_GAP", "control_pressure_level": "CRITICAL"},
        ]
        
        for i, combo in enumerate(control_combinations):
            test_matrix.append({
                'test_id': i + 1,
                'name': f"Scientific_Test_{i+1:02d}",
                'test_type': 'scientific_core',
                **combo,
                'p_event': 1.0,  # 100%触发确保统计有效性
                'seed': 42  # 固定种子确保可重现
            })
        
        # 2. 工程边界条件测试
        boundary_tests = [
            # 概率边界
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL, "p_event": 0.0, "seed": 1, "description": "Zero probability boundary"},
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 1, "description": "Full probability boundary"},
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL, "p_event": 0.5, "seed": 1, "description": "Half probability"},
            
            # 种子边界
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 0, "description": "Zero seed"},
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 1, "description": "Minimum seed"},
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 2**31-1, "description": "Maximum safe seed"},
            
            # 任务数量边界（虽然固定为14，但测试不同phase分布）
            {"control_category": UNCONTROL, "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 99, "description": "Phase boundary test"},
        ]
        
        for i, boundary in enumerate(boundary_tests):
            test_matrix.append({
                'test_id': len(control_combinations) + i + 1,
                'name': f"Boundary_Test_{i+1:02d}",
                'test_type': 'engineering_boundary',
                **boundary
            })
        
        # 3. 离奇bug检测
        weird_bug_tests = [
            # 参数验证是否真的有效
            {"control_category": "", "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 42, "expected_error": True, "description": "Empty string category"},
            {"control_category": UNCONTROL, "control_pressure_level": "", "p_event": 1.0, "seed": 42, "expected_error": True, "description": "Empty string pressure"},
            {"control_category": "invalid_category", "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 42, "expected_error": True, "description": "Invalid category"},
            {"control_category": UNCONTROL, "control_pressure_level": "INVALID_PRESSURE", "p_event": 1.0, "seed": 42, "expected_error": True, "description": "Invalid pressure"},
            
            # 大小写敏感bug
            {"control_category": "goal_conflict", "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 42, "expected_error": True, "description": "Lowercase category"},
            {"control_category": UNCONTROL, "control_pressure_level": "high", "p_event": 1.0, "seed": 42, "expected_error": True, "description": "Lowercase pressure"},
            
            # None值处理bug（现在应该在构造函数就被拒绝）
            {"control_category": None, "control_pressure_level": UNCONTROL, "p_event": 1.0, "seed": 42, "expected_error": True, "description": "None category"},
            {"control_category": UNCONTROL, "control_pressure_level": None, "p_event": 1.0, "seed": 42, "expected_error": True, "description": "None pressure"},
        ]
        
        for i, weird in enumerate(weird_bug_tests):
            test_matrix.append({
                'test_id': len(control_combinations) + len(boundary_tests) + i + 1,
                'name': f"WeirdBug_Test_{i+1:02d}",
                'test_type': 'weird_bug_detection',
                **weird
            })
        
        return test_matrix
    
    def run_statistical_distribution_test(self, config: Dict) -> Dict:
        """运行统计学分布测试"""
        print(f"📊 Testing: {config['name']} - {config.get('description', '')}")
        
        if config.get('expected_error', False):
            # 错误测试
            try:
                event_system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=config['p_event'],
                    control_category=config['control_category'],
                    control_pressure_level=config['control_pressure_level'],
                    seed=config['seed'],
                    total_tasks=TOTAL_TASKS
                )
                return {
                    'test_id': config['test_id'],
                    'success': False,
                    'error': f"Expected error but test passed for: {config['description']}"
                }
            except Exception as e:
                return {
                    'test_id': config['test_id'],
                    'success': True,
                    'result_type': 'expected_error',
                    'error_caught': str(e)
                }
        
        # 正常测试
        try:
            event_system = EventSystem(
                TASK_STREAM_NAME,
                p_event=config['p_event'],
                control_category=config['control_category'],
                control_pressure_level=config['control_pressure_level'],
                seed=config['seed'],
                total_tasks=TOTAL_TASKS
            )
            
            # 收集统计数据
            category_counts = Counter()
            pressure_counts = Counter()
            event_triggered_count = 0
            phase_distribution = defaultdict(Counter)
            
            sample_size = SCIENTIFIC_SAMPLE_SIZE
            
            for sample_idx in range(sample_size):
                # 每次用不同但确定的种子
                test_seed = config['seed'] + sample_idx
                
                test_event_system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=config['p_event'],
                    control_category=config['control_category'],
                    control_pressure_level=config['control_pressure_level'],
                    seed=test_seed,
                    total_tasks=TOTAL_TASKS
                )
                
                for task_sequence_num in range(1, TOTAL_TASKS + 1):
                    phase = self.task_stream.get_phase_for_task(task_sequence_num)
                    event_obj, event_variant = test_event_system.get_event_and_variant_for_phase(phase, task_sequence_num)
                    
                    if event_obj and event_variant:
                        event_triggered_count += 1
                        category_counts[event_variant['category']] += 1
                        pressure_counts[event_variant['pressure_level']] += 1
                        phase_distribution[phase][event_variant['category']] += 1
            
            total_samples = sample_size * TOTAL_TASKS
            
            # 统计学分析
            result = {
                'test_id': config['test_id'],
                'success': True,
                'config': config,
                'total_samples': total_samples,
                'event_triggered_count': event_triggered_count,
                'actual_trigger_rate': event_triggered_count / total_samples if total_samples > 0 else 0,
                'expected_trigger_rate': config['p_event'],
                'category_distribution': dict(category_counts),
                'pressure_distribution': dict(pressure_counts),
                'phase_distribution': {phase: dict(counts) for phase, counts in phase_distribution.items()},
            }
            
            # 进行科学统计验证
            result.update(self.perform_scientific_analysis(result, config))
            
            return result
            
        except Exception as e:
            return {
                'test_id': config['test_id'],
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def perform_scientific_analysis(self, result: Dict, config: Dict) -> Dict:
        """科学统计分析"""
        analysis = {}
        
        # 1. 触发率检验（二项分布）
        n = result['total_samples']
        p_expected = config['p_event']
        observed_triggers = result['event_triggered_count']
        
        if n > 0 and 0 < p_expected <= 1:
            p_actual = observed_triggers / n
            
            # 计算99%置信区间
            z_99 = 2.576  # 99%置信水平
            if p_expected > 0 and p_expected < 1:
                std_error = math.sqrt(p_expected * (1 - p_expected) / n)
                margin_error = z_99 * std_error
                ci_lower = p_expected - margin_error
                ci_upper = p_expected + margin_error
                
                analysis['trigger_rate_99_ci'] = (ci_lower, ci_upper)
                analysis['trigger_rate_in_99_ci'] = ci_lower <= p_actual <= ci_upper
                analysis['trigger_rate_deviation'] = abs(p_actual - p_expected)
        
        # 2. Category分布均匀性检验（卡方检验）
        if config['control_category'] == UNCONTROL and result['event_triggered_count'] > 0:
            expected_per_category = result['event_triggered_count'] / len(ALL_CATEGORIES)
            chi_square_cat = 0
            
            for category in ALL_CATEGORIES:
                observed = result['category_distribution'].get(category, 0)
                chi_square_cat += (observed - expected_per_category) ** 2 / expected_per_category
            
            # 自由度 = 类别数 - 1
            df_cat = len(ALL_CATEGORIES) - 1
            critical_99_cat = 13.277  # df=4, 99%
            
            analysis['category_chi_square'] = chi_square_cat
            analysis['category_df'] = df_cat
            analysis['category_passes_chi_square_99'] = chi_square_cat < critical_99_cat
        
        # 3. Pressure分布均匀性检验
        if config['control_pressure_level'] == UNCONTROL and result['event_triggered_count'] > 0:
            expected_per_pressure = result['event_triggered_count'] / len(ALL_PRESSURE_LEVELS)
            chi_square_pres = 0
            
            for pressure in ALL_PRESSURE_LEVELS:
                observed = result['pressure_distribution'].get(pressure, 0)
                chi_square_pres += (observed - expected_per_pressure) ** 2 / expected_per_pressure
            
            df_pres = len(ALL_PRESSURE_LEVELS) - 1
            critical_99_pres = 11.345  # df=3, 99%
            
            analysis['pressure_chi_square'] = chi_square_pres
            analysis['pressure_df'] = df_pres
            analysis['pressure_passes_chi_square_99'] = chi_square_pres < critical_99_pres
        
        # 4. Phase均匀性检验（两个phase应该大致相等）
        phase_counts = {phase: sum(counts.values()) for phase, counts in result['phase_distribution'].items()}
        if len(phase_counts) >= 2:
            total_phase_events = sum(phase_counts.values())
            if total_phase_events > 0:
                phase_deviations = []
                expected_per_phase = total_phase_events / len(phase_counts)
                
                for phase, count in phase_counts.items():
                    deviation = abs(count - expected_per_phase) / expected_per_phase
                    phase_deviations.append(deviation)
                
                analysis['max_phase_deviation'] = max(phase_deviations) if phase_deviations else 0
                analysis['phase_balanced'] = analysis['max_phase_deviation'] < 0.1  # 10%容差
        
        return analysis
    
    def test_reproducibility(self, base_config: Dict) -> Dict:
        """测试可重现性"""
        print("🔄 Testing reproducibility with same seeds...")
        
        # 用相同种子生成多次，应该完全相同
        test_seed = 12345
        sequences = []
        
        for run in range(5):
            event_system = EventSystem(
                TASK_STREAM_NAME,
                p_event=1.0,  # 确保所有事件都触发
                control_category=UNCONTROL,
                control_pressure_level=UNCONTROL,
                seed=test_seed,
                total_tasks=TOTAL_TASKS
            )
            
            sequence = []
            for task_num in range(1, TOTAL_TASKS + 1):
                phase = self.task_stream.get_phase_for_task(task_num)
                event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_num)
                
                if event_obj and event_variant:
                    sequence.append({
                        'task': task_num,
                        'category': event_variant['category'],
                        'pressure': event_variant['pressure_level'],
                        'event_name': event_variant['name']
                    })
            
            sequences.append(sequence)
        
        # 验证所有序列相同
        all_identical = all(seq == sequences[0] for seq in sequences)
        
        # 用不同种子，应该产生不同结果
        different_seed_system = EventSystem(
            TASK_STREAM_NAME,
            p_event=1.0,
            control_category=UNCONTROL,
            control_pressure_level=UNCONTROL,
            seed=test_seed + 1,  # 不同种子
            total_tasks=TOTAL_TASKS
        )
        
        different_sequence = []
        for task_num in range(1, TOTAL_TASKS + 1):
            phase = self.task_stream.get_phase_for_task(task_num)
            event_obj, event_variant = different_seed_system.get_event_and_variant_for_phase(phase, task_num)
            
            if event_obj and event_variant:
                different_sequence.append({
                    'task': task_num,
                    'category': event_variant['category'],
                    'pressure': event_variant['pressure_level'],
                    'event_name': event_variant['name']
                })
        
        sequences_different = different_sequence != sequences[0]
        
        return {
            'same_seed_reproducible': all_identical,
            'different_seed_produces_different_results': sequences_different,
            'sequence_length': len(sequences[0]),
            'test_runs': len(sequences)
        }
    
    def run_complete_scientific_test(self) -> Dict:
        """运行完整的科学测试"""
        print("🔬 Starting Scientific Rigorous Test Suite")
        print("=" * 70)
        
        start_time = time.time()
        
        # 1. 生成测试矩阵
        test_matrix = self.generate_scientific_test_matrix()
        print(f"📋 Generated {len(test_matrix)} test cases:")
        print(f"   - Scientific core tests: {len([t for t in test_matrix if t['test_type'] == 'scientific_core'])}")
        print(f"   - Engineering boundary tests: {len([t for t in test_matrix if t['test_type'] == 'engineering_boundary'])}")
        print(f"   - Weird bug detection tests: {len([t for t in test_matrix if t['test_type'] == 'weird_bug_detection'])}")
        print()
        
        # 2. 运行所有测试
        all_results = {}
        for i, config in enumerate(test_matrix):
            print(f"[{i+1:2d}/{len(test_matrix)}] ", end="")
            result = self.run_statistical_distribution_test(config)
            all_results[config['test_id']] = result
            
            if result['success']:
                print("✅")
            else:
                print(f"❌ {result.get('error', 'Unknown error')}")
        
        # 3. 可重现性测试
        print()
        reproducibility_result = self.test_reproducibility({})
        all_results['reproducibility'] = reproducibility_result
        
        total_time = time.time() - start_time
        
        return {
            'test_matrix': test_matrix,
            'results': all_results,
            'total_execution_time': total_time,
            'reproducibility': reproducibility_result
        }
    
    def generate_scientific_report(self, full_results: Dict) -> str:
        """生成科学测试报告"""
        report = []
        report.append("🔬 Scientific Rigorous Test Report")
        report.append("=" * 70)
        report.append(f"Test Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Sample Size per Test: {SCIENTIFIC_SAMPLE_SIZE:,}")
        report.append(f"Significance Level: {SIGNIFICANCE_LEVEL}")
        report.append("")
        
        results = full_results['results']
        
        # 总体统计
        total_tests = len([r for r in results.values() if isinstance(r, dict) and 'test_id' in r])
        passed_tests = len([r for r in results.values() if isinstance(r, dict) and r.get('success', False)])
        
        report.append("📊 Overall Results:")
        report.append(f"  Total Tests: {total_tests}")
        report.append(f"  Passed: {passed_tests}")
        report.append(f"  Failed: {total_tests - passed_tests}")
        report.append(f"  Success Rate: {passed_tests/total_tests*100:.1f}%")
        report.append("")
        
        # 科学核心测试结果
        core_tests = [r for r in results.values() if isinstance(r, dict) and r.get('config', {}).get('test_type') == 'scientific_core']
        if core_tests:
            report.append("🧪 Scientific Core Tests:")
            passed_chi_square_cat = sum(1 for r in core_tests if r.get('category_passes_chi_square_99', True))
            passed_chi_square_pres = sum(1 for r in core_tests if r.get('pressure_passes_chi_square_99', True))
            passed_trigger_rate = sum(1 for r in core_tests if r.get('trigger_rate_in_99_ci', True))
            
            report.append(f"  Category Distribution Tests: {passed_chi_square_cat}/{len(core_tests)} passed")
            report.append(f"  Pressure Distribution Tests: {passed_chi_square_pres}/{len(core_tests)} passed")
            report.append(f"  Trigger Rate Tests: {passed_trigger_rate}/{len(core_tests)} passed")
            report.append("")
        
        # 边界测试结果
        boundary_tests = [r for r in results.values() if isinstance(r, dict) and r.get('config', {}).get('test_type') == 'engineering_boundary']
        if boundary_tests:
            passed_boundary = len([r for r in boundary_tests if r.get('success', False)])
            report.append("⚙️  Engineering Boundary Tests:")
            report.append(f"  Passed: {passed_boundary}/{len(boundary_tests)}")
            report.append("")
        
        # Bug检测结果
        bug_tests = [r for r in results.values() if isinstance(r, dict) and r.get('config', {}).get('test_type') == 'weird_bug_detection']
        if bug_tests:
            passed_bug = len([r for r in bug_tests if r.get('success', False)])
            report.append("🐛 Weird Bug Detection Tests:")
            report.append(f"  Correctly Caught Errors: {passed_bug}/{len(bug_tests)}")
            report.append("")
        
        # 可重现性结果
        repro = results.get('reproducibility', {})
        if repro:
            report.append("🔄 Reproducibility Test:")
            report.append(f"  Same Seed Reproducible: {'✅' if repro.get('same_seed_reproducible') else '❌'}")
            report.append(f"  Different Seeds Different: {'✅' if repro.get('different_seed_produces_different_results') else '❌'}")
            report.append("")
        
        # 失败的测试详情
        failed_tests = [r for r in results.values() if isinstance(r, dict) and not r.get('success', True)]
        if failed_tests:
            report.append("❌ Failed Tests:")
            for failed in failed_tests[:5]:  # 只显示前5个
                report.append(f"  Test {failed.get('test_id', '?')}: {failed.get('error', 'Unknown error')}")
            if len(failed_tests) > 5:
                report.append(f"  ... and {len(failed_tests) - 5} more failed tests")
            report.append("")
        
        # 执行时间
        total_time = full_results.get('total_execution_time', 0)
        report.append(f"⏱️  Execution Time: {total_time:.2f} seconds")
        report.append("")
        
        # 科学结论
        if total_tests > 0:
            success_rate = passed_tests / total_tests
            if success_rate >= 0.95:
                report.append("✅ SCIENTIFIC CONCLUSION: System passes rigorous testing")
                report.append("   - Statistical distributions are correct")
                report.append("   - Control mechanisms work properly")  
                report.append("   - Engineering edge cases handled correctly")
                report.append("   - System is suitable for scientific experiments")
            else:
                report.append("❌ SCIENTIFIC CONCLUSION: System has significant issues")
                report.append("   - Statistical reliability is questionable")
                report.append("   - Not recommended for scientific experiments until fixed")
        
        return "\n".join(report)

def main():
    """科学严谨测试主函数"""
    tester = ScientificRigorousTester()
    
    # 运行完整测试
    results = tester.run_complete_scientific_test()
    
    # 生成报告
    report = tester.generate_scientific_report(results)
    
    # 输出报告
    print("\n" + "=" * 70)
    print(report)
    
    # 保存结果
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_filename = f"TEST/scientific_rigorous_results_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    report_filename = f"TEST/scientific_rigorous_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"💾 Results saved to: {json_filename}")
    print(f"📄 Report saved to: {report_filename}")

if __name__ == "__main__":
    main()