#!/usr/bin/env python3
"""
控制机制和概率均等性测试
测试4种控制情况下的事件选择概率分布
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
from tasks.event import EventSystem
from tasks.task import TaskLoader

# 测试常量
SAMPLE_SIZE = 1000  # 每种配置的采样次数
TASK_STREAM_NAME = "market_research_series"
P_EVENT = 1.0  # 100%触发率确保所有样本都有事件
TOTAL_TASKS = 14

# 4种控制情况配置
CONTROL_SCENARIOS = [
    {
        "name": "No Control",
        "control_category": "UNCONTROL",
        "control_pressure_level": "UNCONTROL",
        "description": "Both category and pressure level are uncontrolled"
    },
    {
        "name": "Category Control",
        "control_category": "GOAL_CONFLICT", 
        "control_pressure_level": "UNCONTROL",
        "description": "Category fixed to GOAL_CONFLICT, pressure level uncontrolled"
    },
    {
        "name": "Pressure Control",
        "control_category": "UNCONTROL",
        "control_pressure_level": "HIGH",
        "description": "Pressure level fixed to HIGH, category uncontrolled"
    },
    {
        "name": "Full Control",
        "control_category": "GOAL_CONFLICT",
        "control_pressure_level": "HIGH", 
        "description": "Both category and pressure level controlled"
    }
]

class ControlProbabilityTester:
    """控制机制概率分布测试器"""
    
    def __init__(self):
        self.task_loader = TaskLoader()
        self.task_stream = self.task_loader.load_task_stream(TASK_STREAM_NAME)
        self.results = {}
        
    def run_single_scenario_test(self, scenario: Dict) -> Dict:
        """对单个控制场景进行大量采样测试"""
        print(f"Testing scenario: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        
        # 统计数据收集
        category_counts = Counter()
        pressure_counts = Counter()
        event_counts = Counter()
        phase_category_counts = defaultdict(Counter)
        phase_pressure_counts = defaultdict(Counter)
        
        # 大量采样测试
        for sample_idx in range(SAMPLE_SIZE):
            # 使用不同seed确保随机性
            event_system = EventSystem(
                TASK_STREAM_NAME,
                p_event=P_EVENT,
                seed=sample_idx + 1000,  # 确保seed不同
                control_category=scenario['control_category'],
                control_pressure_level=scenario['control_pressure_level'],
                total_tasks=TOTAL_TASKS
            )
            
            # 测试每个任务的事件选择
            for task_sequence_num in range(1, TOTAL_TASKS + 1):
                phase = self.task_stream.get_phase_for_task(task_sequence_num)
                event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_sequence_num)
                
                if event_obj and event_variant:
                    category = event_variant['category']
                    pressure_level = event_variant['pressure_level']
                    event_name = event_variant['name']
                    
                    # 全局统计
                    category_counts[category] += 1
                    pressure_counts[pressure_level] += 1
                    event_counts[event_name] += 1
                    
                    # 按phase统计
                    phase_category_counts[phase][category] += 1
                    phase_pressure_counts[phase][pressure_level] += 1
        
        # 计算总样本数
        total_samples = SAMPLE_SIZE * TOTAL_TASKS
        
        return {
            'scenario': scenario,
            'total_samples': total_samples,
            'category_distribution': dict(category_counts),
            'pressure_distribution': dict(pressure_counts),
            'event_distribution': dict(event_counts),
            'phase_category_distribution': {phase: dict(counts) for phase, counts in phase_category_counts.items()},
            'phase_pressure_distribution': {phase: dict(counts) for phase, counts in phase_pressure_counts.items()}
        }
    
    def calculate_probabilities(self, result: Dict) -> Dict:
        """计算概率和理论期望值"""
        total_samples = result['total_samples']
        scenario = result['scenario']
        
        # 计算实际概率
        category_probs = {k: v/total_samples for k, v in result['category_distribution'].items()}
        pressure_probs = {k: v/total_samples for k, v in result['pressure_distribution'].items()}
        
        # 计算理论期望概率
        expected_probs = self._calculate_expected_probabilities(scenario)
        
        # 计算偏差
        category_deviations = {}
        pressure_deviations = {}
        
        for category in expected_probs['categories']:
            actual = category_probs.get(category, 0.0)
            expected = expected_probs['categories'][category]
            category_deviations[category] = abs(actual - expected)
        
        for pressure in expected_probs['pressures']:
            actual = pressure_probs.get(pressure, 0.0)
            expected = expected_probs['pressures'][pressure]
            pressure_deviations[pressure] = abs(actual - expected)
        
        return {
            'actual_category_probs': category_probs,
            'actual_pressure_probs': pressure_probs,
            'expected_category_probs': expected_probs['categories'],
            'expected_pressure_probs': expected_probs['pressures'],
            'category_deviations': category_deviations,
            'pressure_deviations': pressure_deviations,
            'max_category_deviation': max(category_deviations.values()) if category_deviations else 0,
            'max_pressure_deviation': max(pressure_deviations.values()) if pressure_deviations else 0
        }
    
    def _calculate_expected_probabilities(self, scenario: Dict) -> Dict:
        """计算理论期望概率"""
        # 基于JSON结构：5 categories, 4 pressure levels
        all_categories = ['GOAL_CONFLICT', 'MORAL_DILEMMA', 'COMPETITIVE_INTERACTION', 'AUTHORITY_DIRECTIVE', 'INFORMATION_GAP']
        all_pressures = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        if scenario['control_category'] != 'UNCONTROL':
            # Category被控制，只有一个category有概率1.0
            category_probs = {cat: 1.0 if cat == scenario['control_category'] else 0.0 for cat in all_categories}
        else:
            # Category不被控制，均匀分布
            category_probs = {cat: 1.0/5 for cat in all_categories}
        
        if scenario['control_pressure_level'] != 'UNCONTROL':
            # Pressure被控制，只有一个pressure有概率1.0
            pressure_probs = {pres: 1.0 if pres == scenario['control_pressure_level'] else 0.0 for pres in all_pressures}
        else:
            # Pressure不被控制，均匀分布
            pressure_probs = {pres: 1.0/4 for pres in all_pressures}
        
        return {
            'categories': category_probs,
            'pressures': pressure_probs
        }
    
    def run_all_tests(self) -> Dict:
        """运行所有4种控制情况的测试"""
        print("🔬 Starting Control & Probability Distribution Tests")
        print(f"Sample size per scenario: {SAMPLE_SIZE}")
        print(f"Total tasks per sample: {TOTAL_TASKS}")
        print(f"Event trigger probability: {P_EVENT}")
        print("="*80)
        
        all_results = {}
        
        for scenario in CONTROL_SCENARIOS:
            # 运行单个场景测试
            raw_result = self.run_single_scenario_test(scenario)
            
            # 计算概率和偏差
            probability_analysis = self.calculate_probabilities(raw_result)
            
            # 合并结果
            all_results[scenario['name']] = {
                **raw_result,
                **probability_analysis
            }
            
            print(f"✅ Completed: {scenario['name']}")
            print()
        
        return all_results
    
    def generate_test_report(self, results: Dict) -> str:
        """生成详细测试报告"""
        report = []
        report.append("🔬 Control Mechanism & Probability Distribution Test Report")
        report.append("="*80)
        report.append(f"Sample Size per Scenario: {SAMPLE_SIZE:,}")
        report.append(f"Total Tasks per Sample: {TOTAL_TASKS}")
        report.append(f"Total Samples per Scenario: {SAMPLE_SIZE * TOTAL_TASKS:,}")
        report.append("")
        
        for scenario_name, result in results.items():
            scenario = result['scenario']
            report.append(f"📊 Scenario: {scenario_name}")
            report.append(f"Description: {scenario['description']}")
            report.append("-" * 60)
            
            # Category分布
            report.append("📈 Category Distribution:")
            report.append(f"{'Category':<25} {'Actual':<10} {'Expected':<10} {'Deviation':<10}")
            report.append("-" * 55)
            
            for category in ['GOAL_CONFLICT', 'MORAL_DILEMMA', 'COMPETITIVE_INTERACTION', 'AUTHORITY_DIRECTIVE', 'INFORMATION_GAP']:
                actual = result['actual_category_probs'].get(category, 0.0)
                expected = result['expected_category_probs'].get(category, 0.0)
                deviation = result['category_deviations'].get(category, 0.0)
                
                report.append(f"{category:<25} {actual:<10.3f} {expected:<10.3f} {deviation:<10.3f}")
            
            report.append(f"Max Category Deviation: {result['max_category_deviation']:.3f}")
            report.append("")
            
            # Pressure分布
            report.append("📈 Pressure Level Distribution:")
            report.append(f"{'Pressure Level':<15} {'Actual':<10} {'Expected':<10} {'Deviation':<10}")
            report.append("-" * 45)
            
            for pressure in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
                actual = result['actual_pressure_probs'].get(pressure, 0.0)
                expected = result['expected_pressure_probs'].get(pressure, 0.0)
                deviation = result['pressure_deviations'].get(pressure, 0.0)
                
                report.append(f"{pressure:<15} {actual:<10.3f} {expected:<10.3f} {deviation:<10.3f}")
            
            report.append(f"Max Pressure Deviation: {result['max_pressure_deviation']:.3f}")
            report.append("")
            report.append("="*80)
            report.append("")
        
        return "\n".join(report)

def main():
    """主测试函数"""
    tester = ControlProbabilityTester()
    
    # 运行所有测试
    results = tester.run_all_tests()
    
    # 生成报告
    report = tester.generate_test_report(results)
    
    # 输出报告
    print(report)
    
    # 保存结果到文件
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存JSON结果
    json_filename = f"TEST/control_probability_results_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 保存文本报告
    report_filename = f"TEST/control_probability_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"💾 Results saved to: {json_filename}")
    print(f"📄 Report saved to: {report_filename}")

if __name__ == "__main__":
    main()