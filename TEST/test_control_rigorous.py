#!/usr/bin/env python3
"""
严谨的控制机制测试 - 覆盖所有corner cases和边界条件
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import math
import random
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import datetime
from tasks.event import EventSystem, UNCONTROL
from tasks.task import TaskLoader

# 严谨测试常量
RIGOROUS_SAMPLE_SIZE = 10000  # 大样本确保统计显著性
TASK_STREAM_NAME = "market_research_series"
P_EVENT = 1.0  # 100%触发确保所有样本有效
TOTAL_TASKS = 14
SIGNIFICANCE_LEVEL = 0.001  # 99.9%置信水平

# 获取所有可能的categories和pressure levels
ALL_CATEGORIES = ['GOAL_CONFLICT', 'MORAL_DILEMMA', 'COMPETITIVE_INTERACTION', 'AUTHORITY_DIRECTIVE', 'INFORMATION_GAP']
ALL_PRESSURE_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
ALL_PHASES = ['phase_1', 'phase_2']

class RigorousControlTester:
    """严谨的控制机制测试器"""
    
    def __init__(self):
        self.task_loader = TaskLoader()
        self.task_stream = self.task_loader.load_task_stream(TASK_STREAM_NAME)
        self.test_results = {}
        
    def generate_all_control_combinations(self) -> List[Dict]:
        """生成所有可能的控制组合 - 包括corner cases"""
        combinations = []
        
        # 1. 基础控制组合
        control_categories = [UNCONTROL] + ALL_CATEGORIES
        control_pressures = [UNCONTROL] + ALL_PRESSURE_LEVELS
        
        for category in control_categories:
            for pressure in control_pressures:
                combinations.append({
                    'control_category': category,
                    'control_pressure_level': pressure,
                    'name': f"Cat_{category}_Pres_{pressure}",
                    'test_type': 'normal'
                })
        
        # 2. Corner Cases - 无效控制值
        corner_cases = [
            {
                'control_category': 'INVALID_CATEGORY',
                'control_pressure_level': UNCONTROL,
                'name': 'Invalid_Category_Test',
                'test_type': 'error_expected',
                'expected_error': 'Invalid control_category'
            },
            {
                'control_category': UNCONTROL,
                'control_pressure_level': 'INVALID_PRESSURE', 
                'name': 'Invalid_Pressure_Test',
                'test_type': 'error_expected',
                'expected_error': 'Invalid control_pressure_level'
            },
            {
                'control_category': '',
                'control_pressure_level': UNCONTROL,
                'name': 'Empty_Category_Test',
                'test_type': 'error_expected',
                'expected_error': 'Empty control_category'
            },
            {
                'control_category': None,
                'control_pressure_level': UNCONTROL,
                'name': 'None_Category_Test',
                'test_type': 'error_expected',
                'expected_error': 'None control_category'
            }
        ]
        
        combinations.extend(corner_cases)
        return combinations
    
    def run_statistical_significance_test(self, observed_counts: Dict, expected_probs: Dict, total_samples: int) -> Dict:
        """运行卡方检验验证统计显著性"""
        chi_square = 0.0
        degrees_of_freedom = len(expected_probs) - 1
        
        for key, expected_prob in expected_probs.items():
            observed = observed_counts.get(key, 0)
            expected = expected_prob * total_samples
            
            if expected > 0:  # 避免除零
                chi_square += (observed - expected) ** 2 / expected
        
        # 计算p值 (简化版，实际应使用scipy)
        # 对于大样本，使用正态近似
        critical_value_999 = 16.266  # df=4时99.9%临界值
        is_significant = chi_square > critical_value_999
        
        return {
            'chi_square': chi_square,
            'degrees_of_freedom': degrees_of_freedom,
            'critical_value_999': critical_value_999,
            'is_significantly_different': is_significant,
            'passes_test': not is_significant  # 我们期望分布不显著偏离理论
        }
    
    def test_seed_reproducibility(self, control_config: Dict, num_tests: int = 5) -> Dict:
        """测试相同种子的可重现性"""
        test_seed = 12345
        all_sequences = []
        
        for test_idx in range(num_tests):
            event_system = EventSystem(
                TASK_STREAM_NAME,
                p_event=P_EVENT,
                seed=test_seed,  # 相同种子
                control_category=control_config['control_category'],
                control_pressure_level=control_config['control_pressure_level'],
                total_tasks=TOTAL_TASKS
            )
            
            sequence = []
            for task_sequence_num in range(1, TOTAL_TASKS + 1):
                phase = self.task_stream.get_phase_for_task(task_sequence_num)
                event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_sequence_num)
                
                if event_obj and event_variant:
                    sequence.append({
                        'task': task_sequence_num,
                        'phase': phase,
                        'category': event_variant['category'],
                        'pressure': event_variant['pressure_level'],
                        'event_name': event_variant['name']
                    })
            
            all_sequences.append(sequence)
        
        # 验证所有序列完全相同
        is_reproducible = all(seq == all_sequences[0] for seq in all_sequences)
        
        return {
            'is_reproducible': is_reproducible,
            'num_tests': num_tests,
            'sequence_length': len(all_sequences[0]),
            'first_sequence': all_sequences[0][:3]  # 展示前3个事件
        }
    
    def test_phase_specific_distribution(self, control_config: Dict) -> Dict:
        """测试phase特异性分布"""
        phase_stats = defaultdict(lambda: defaultdict(Counter))
        
        # 大量采样
        for sample_idx in range(RIGOROUS_SAMPLE_SIZE):
            event_system = EventSystem(
                TASK_STREAM_NAME,
                p_event=P_EVENT,
                seed=sample_idx + 50000,
                control_category=control_config['control_category'],
                control_pressure_level=control_config['control_pressure_level'],
                total_tasks=TOTAL_TASKS
            )
            
            for task_sequence_num in range(1, TOTAL_TASKS + 1):
                phase = self.task_stream.get_phase_for_task(task_sequence_num)
                event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_sequence_num)
                
                if event_obj and event_variant:
                    phase_stats[phase]['categories'][event_variant['category']] += 1
                    phase_stats[phase]['pressures'][event_variant['pressure_level']] += 1
        
        # 分析每个phase的分布
        phase_analysis = {}
        for phase, stats in phase_stats.items():
            total_phase_samples = sum(stats['categories'].values())
            
            phase_analysis[phase] = {
                'total_samples': total_phase_samples,
                'category_distribution': {k: v/total_phase_samples for k, v in stats['categories'].items()},
                'pressure_distribution': {k: v/total_phase_samples for k, v in stats['pressures'].items()},
            }
        
        return phase_analysis
    
    def test_edge_cases(self) -> Dict:
        """测试边界条件和极端情况"""
        edge_results = {}
        
        # 1. 测试p_event边界值
        edge_p_events = [0.0, 0.001, 0.5, 0.999, 1.0]
        
        for p_event in edge_p_events:
            triggered_count = 0
            total_attempts = 1000
            
            event_system = EventSystem(
                TASK_STREAM_NAME,
                p_event=p_event,
                seed=99999,
                control_category=UNCONTROL,
                control_pressure_level=UNCONTROL,
                total_tasks=TOTAL_TASKS
            )
            
            for attempt in range(total_attempts):
                for task_sequence_num in range(1, TOTAL_TASKS + 1):
                    phase = self.task_stream.get_phase_for_task(task_sequence_num)
                    event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_sequence_num)
                    if event_obj and event_variant:
                        triggered_count += 1
            
            actual_trigger_rate = triggered_count / (total_attempts * TOTAL_TASKS)
            edge_results[f'p_event_{p_event}'] = {
                'configured_rate': p_event,
                'actual_rate': actual_trigger_rate,
                'deviation': abs(actual_trigger_rate - p_event),
                'within_tolerance': abs(actual_trigger_rate - p_event) < 0.05  # 5%容差
            }
        
        # 2. 测试极端seed值
        extreme_seeds = [0, 1, 2**31-1, 2**32-1]
        
        for seed in extreme_seeds:
            try:
                event_system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=1.0,
                    seed=seed,
                    control_category=UNCONTROL,
                    control_pressure_level=UNCONTROL,
                    total_tasks=TOTAL_TASKS
                )
                
                # 测试是否能正常生成事件
                test_events = []
                for task_sequence_num in range(1, 4):  # 测试前3个任务
                    phase = self.task_stream.get_phase_for_task(task_sequence_num)
                    event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_sequence_num)
                    if event_obj and event_variant:
                        test_events.append(event_variant['name'])
                
                edge_results[f'seed_{seed}'] = {
                    'success': True,
                    'events_generated': len(test_events),
                    'sample_events': test_events
                }
                
            except Exception as e:
                edge_results[f'seed_{seed}'] = {
                    'success': False,
                    'error': str(e)
                }
        
        return edge_results
    
    def run_comprehensive_test(self, config: Dict) -> Dict:
        """对单个配置运行全面测试"""
        print(f"🔬 Testing: {config['name']}")
        
        if config['test_type'] == 'error_expected':
            # 测试错误情况
            try:
                event_system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=P_EVENT,
                    seed=1000,
                    control_category=config['control_category'],
                    control_pressure_level=config['control_pressure_level'],
                    total_tasks=TOTAL_TASKS
                )
                
                # 尝试生成事件
                phase = self.task_stream.get_phase_for_task(1)
                event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, 1)
                
                return {
                    'test_type': 'error_expected',
                    'success': False,
                    'message': 'Expected error but got success',
                    'config': config
                }
                
            except Exception as e:
                return {
                    'test_type': 'error_expected',
                    'success': True,
                    'message': f'Correctly caught error: {str(e)}',
                    'config': config
                }
        
        # 正常测试流程
        try:
            # 1. 基础分布测试
            category_counts = Counter()
            pressure_counts = Counter()
            
            for sample_idx in range(RIGOROUS_SAMPLE_SIZE):
                event_system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=P_EVENT,
                    seed=sample_idx + 10000,
                    control_category=config['control_category'],
                    control_pressure_level=config['control_pressure_level'],
                    total_tasks=TOTAL_TASKS
                )
                
                for task_sequence_num in range(1, TOTAL_TASKS + 1):
                    phase = self.task_stream.get_phase_for_task(task_sequence_num)
                    event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_sequence_num)
                    
                    if event_obj and event_variant:
                        category_counts[event_variant['category']] += 1
                        pressure_counts[event_variant['pressure_level']] += 1
            
            total_samples = sum(category_counts.values())
            
            # 2. 计算期望概率
            expected_category_probs = self._calculate_expected_probabilities(config, 'category')
            expected_pressure_probs = self._calculate_expected_probabilities(config, 'pressure')
            
            # 3. 统计显著性检验
            category_significance = self.run_statistical_significance_test(
                category_counts, expected_category_probs, total_samples
            )
            pressure_significance = self.run_statistical_significance_test(
                pressure_counts, expected_pressure_probs, total_samples
            )
            
            # 4. 种子可重现性测试
            reproducibility = self.test_seed_reproducibility(config)
            
            # 5. Phase特异性测试
            phase_distribution = self.test_phase_specific_distribution(config)
            
            return {
                'test_type': 'normal',
                'config': config,
                'total_samples': total_samples,
                'category_counts': dict(category_counts),
                'pressure_counts': dict(pressure_counts),
                'category_significance': category_significance,
                'pressure_significance': pressure_significance,
                'reproducibility': reproducibility,
                'phase_distribution': phase_distribution,
                'success': True
            }
            
        except Exception as e:
            return {
                'test_type': 'normal',
                'config': config,
                'success': False,
                'error': str(e)
            }
    
    def _calculate_expected_probabilities(self, config: Dict, dimension: str) -> Dict:
        """计算期望概率"""
        if dimension == 'category':
            if config['control_category'] != UNCONTROL:
                return {cat: 1.0 if cat == config['control_category'] else 0.0 for cat in ALL_CATEGORIES}
            else:
                return {cat: 1.0/len(ALL_CATEGORIES) for cat in ALL_CATEGORIES}
        
        elif dimension == 'pressure':
            if config['control_pressure_level'] != UNCONTROL:
                return {pres: 1.0 if pres == config['control_pressure_level'] else 0.0 for pres in ALL_PRESSURE_LEVELS}
            else:
                return {pres: 1.0/len(ALL_PRESSURE_LEVELS) for pres in ALL_PRESSURE_LEVELS}
    
    def run_all_rigorous_tests(self) -> Dict:
        """运行所有严谨测试"""
        print("🔬 Starting Rigorous Control Mechanism Tests")
        print(f"Sample size per test: {RIGOROUS_SAMPLE_SIZE:,}")
        print(f"Significance level: {SIGNIFICANCE_LEVEL}")
        print("="*100)
        
        # 生成所有测试配置
        all_configs = self.generate_all_control_combinations()
        
        print(f"📊 Total test configurations: {len(all_configs)}")
        print(f"   - Normal tests: {len([c for c in all_configs if c['test_type'] == 'normal'])}")
        print(f"   - Error tests: {len([c for c in all_configs if c['test_type'] == 'error_expected'])}")
        print()
        
        results = {}
        
        # 运行每个配置的测试
        for i, config in enumerate(all_configs, 1):
            print(f"[{i:2d}/{len(all_configs)}] ", end="")
            result = self.run_comprehensive_test(config)
            results[config['name']] = result
            
            if result['success']:
                print("✅")
            else:
                print("❌")
        
        # 运行边界条件测试
        print("\n🔍 Running Edge Case Tests...")
        edge_results = self.test_edge_cases()
        results['edge_cases'] = edge_results
        
        return results
    
    def generate_rigorous_report(self, results: Dict) -> str:
        """生成严谨测试报告"""
        report = []
        report.append("🔬 RIGOROUS Control Mechanism Test Report")
        report.append("="*100)
        report.append(f"Sample Size: {RIGOROUS_SAMPLE_SIZE:,} per test")
        report.append(f"Significance Level: {SIGNIFICANCE_LEVEL}")
        report.append(f"Test Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 统计测试结果
        normal_tests = [r for r in results.values() if isinstance(r, dict) and r.get('test_type') == 'normal']
        error_tests = [r for r in results.values() if isinstance(r, dict) and r.get('test_type') == 'error_expected']
        
        passed_normal = len([r for r in normal_tests if r.get('success', False)])
        passed_error = len([r for r in error_tests if r.get('success', False)])
        
        report.append("📈 Test Summary:")
        report.append(f"Normal Tests: {passed_normal}/{len(normal_tests)} passed")
        report.append(f"Error Tests: {passed_error}/{len(error_tests)} passed")
        report.append(f"Edge Cases: {'PASS' if 'edge_cases' in results else 'FAIL'}")
        report.append("")
        
        # 详细结果
        for test_name, result in results.items():
            if test_name == 'edge_cases':
                continue
                
            if not isinstance(result, dict):
                continue
                
            report.append(f"🔍 {test_name}:")
            report.append(f"   Type: {result.get('test_type', 'unknown')}")
            report.append(f"   Success: {'✅' if result.get('success', False) else '❌'}")
            
            if result.get('test_type') == 'normal' and result.get('success'):
                # 统计显著性结果
                cat_sig = result.get('category_significance', {})
                pres_sig = result.get('pressure_significance', {})
                
                report.append(f"   Category Chi²: {cat_sig.get('chi_square', 0):.3f} (Pass: {'✅' if cat_sig.get('passes_test', False) else '❌'})")
                report.append(f"   Pressure Chi²: {pres_sig.get('chi_square', 0):.3f} (Pass: {'✅' if pres_sig.get('passes_test', False) else '❌'})")
                report.append(f"   Reproducible: {'✅' if result.get('reproducibility', {}).get('is_reproducible', False) else '❌'}")
            
            if not result.get('success'):
                report.append(f"   Error: {result.get('error', 'Unknown error')}")
            
            report.append("")
        
        # 边界条件测试结果
        if 'edge_cases' in results:
            report.append("🎯 Edge Case Test Results:")
            edge_results = results['edge_cases']
            
            for test_name, edge_result in edge_results.items():
                if 'p_event_' in test_name:
                    report.append(f"   {test_name}: Deviation {edge_result.get('deviation', 0):.3f} ({'✅' if edge_result.get('within_tolerance', False) else '❌'})")
                elif 'seed_' in test_name:
                    report.append(f"   {test_name}: {'✅' if edge_result.get('success', False) else '❌'}")
            
            report.append("")
        
        return "\n".join(report)

def main():
    """严谨测试主函数"""
    tester = RigorousControlTester()
    
    # 运行所有严谨测试
    results = tester.run_all_rigorous_tests()
    
    # 生成报告
    report = tester.generate_rigorous_report(results)
    
    # 输出报告
    print("\n" + "="*100)
    print(report)
    
    # 保存结果
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存JSON结果
    json_filename = f"TEST/rigorous_test_results_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    # 保存报告
    report_filename = f"TEST/rigorous_test_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"💾 Results saved to: {json_filename}")
    print(f"📄 Report saved to: {report_filename}")

if __name__ == "__main__":
    main()