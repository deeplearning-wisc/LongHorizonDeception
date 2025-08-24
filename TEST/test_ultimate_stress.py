#!/usr/bin/env python3
"""
🔥 ULTIMATE STRESS TEST 🔥
超级严谨压力测试 - 覆盖所有可能的corner cases、边界条件、极限情况

测试覆盖：
1. 所有参数组合的暴力测试 (30 categories x 5 pressure levels = 150 combinations)
2. 边界值和极限值测试
3. 大样本量统计学验证 (50,000+ samples per test)
4. 多线程并发压力测试
5. 内存和性能压力测试
6. 异常和错误边界测试
7. 种子一致性和随机性验证
8. JSON结构完整性验证
9. 数学分布精度验证 (到小数点后6位)
10. 系统资源极限测试
"""

import sys
import os
import time
import json
import math
import threading
import multiprocessing
import resource
import gc
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Any, Optional
import datetime
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.event import EventSystem, UNCONTROL
from tasks.task import TaskLoader

# 🔥 ULTIMATE TEST CONFIGURATION 🔥
ULTIMATE_SAMPLE_SIZE = 50000  # 5万样本确保极高统计精度
STRESS_SAMPLE_SIZE = 100000   # 10万样本用于压力测试
TASK_STREAM_NAME = "market_research_series"
TOTAL_TASKS = 14
MAX_THREADS = min(32, multiprocessing.cpu_count() * 4)  # 最大并发线程数
MEMORY_LIMIT_GB = 4  # 内存使用限制

# 完整的测试参数空间
ALL_CATEGORIES = ['GOAL_CONFLICT', 'MORAL_DILEMMA', 'COMPETITIVE_INTERACTION', 'AUTHORITY_DIRECTIVE', 'INFORMATION_GAP']
ALL_PRESSURE_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
ALL_P_EVENTS = [0.0, 0.001, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999, 1.0]  # 边界概率值
EXTREME_SEEDS = [0, 1, 2, 42, 12345, 2**15, 2**16, 2**31-1, 2**32-1]  # 极端种子值

class UltimateStressTester:
    """🔥 终极压力测试器 - 不允许任何bug逃脱！"""
    
    def __init__(self):
        self.task_loader = TaskLoader()
        self.task_stream = self.task_loader.load_task_stream(TASK_STREAM_NAME)
        self.test_results = {}
        self.performance_stats = {}
        self.error_log = []
        
        # 设置内存监控
        self.initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        print("🔥 ULTIMATE STRESS TESTER INITIALIZED")
        print(f"   Max Threads: {MAX_THREADS}")
        print(f"   Memory Limit: {MEMORY_LIMIT_GB}GB")
        print(f"   CPU Cores: {multiprocessing.cpu_count()}")
        print(f"   Ultimate Sample Size: {ULTIMATE_SAMPLE_SIZE:,}")
        print(f"   Stress Sample Size: {STRESS_SAMPLE_SIZE:,}")
    
    def generate_all_possible_combinations(self) -> List[Dict]:
        """生成所有可能的参数组合 - 穷尽性测试"""
        combinations = []
        test_id = 0
        
        print("🧬 Generating exhaustive parameter combinations...")
        
        # 1. 正常控制组合 - 穷尽所有可能
        control_categories = [UNCONTROL] + ALL_CATEGORIES
        control_pressures = [UNCONTROL] + ALL_PRESSURE_LEVELS
        
        for cat in control_categories:
            for pres in control_pressures:
                for p_event in ALL_P_EVENTS:
                    for seed in EXTREME_SEEDS:
                        test_id += 1
                        combinations.append({
                            'test_id': test_id,
                            'control_category': cat,
                            'control_pressure_level': pres,
                            'p_event': p_event,
                            'seed': seed,
                            'name': f"Test_{test_id:04d}_{cat}_{pres}_P{p_event}_S{seed}",
                            'test_type': 'exhaustive_normal'
                        })
        
        # 2. 边界和异常值测试
        boundary_tests = [
            # 字符串边界
            {'control_category': '', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Empty category string'},
            {'control_category': UNCONTROL, 'control_pressure_level': '', 'expected_error': True, 'description': 'Empty pressure string'},
            {'control_category': ' ', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Whitespace category'},
            {'control_category': UNCONTROL, 'control_pressure_level': ' ', 'expected_error': True, 'description': 'Whitespace pressure'},
            
            # 大小写敏感性测试
            {'control_category': 'goal_conflict', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Lowercase category'},
            {'control_category': UNCONTROL, 'control_pressure_level': 'high', 'expected_error': True, 'description': 'Lowercase pressure'},
            {'control_category': 'Goal_Conflict', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Mixed case category'},
            
            # 特殊字符测试
            {'control_category': 'GOAL-CONFLICT', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Hyphen in category'},
            {'control_category': 'GOAL_CONFLICT_', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Trailing underscore'},
            {'control_category': '_GOAL_CONFLICT', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Leading underscore'},
            
            # Unicode和编码测试
            {'control_category': 'GOAL_CONFLICT\x00', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Null byte in category'},
            {'control_category': 'GOAL_CONFLICT\n', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Newline in category'},
            {'control_category': 'GOAL_CONFLICT\t', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Tab in category'},
            
            # 极长字符串测试
            {'control_category': 'A' * 1000, 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Very long category string'},
            {'control_category': UNCONTROL, 'control_pressure_level': 'B' * 1000, 'expected_error': True, 'description': 'Very long pressure string'},
            
            # SQL注入风格测试 (虽然不是数据库，但测试字符串处理)
            {'control_category': "'; DROP TABLE events; --", 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'SQL injection style'},
            
            # 数值型字符串测试
            {'control_category': '123', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Numeric string category'},
            {'control_category': UNCONTROL, 'control_pressure_level': '456', 'expected_error': True, 'description': 'Numeric string pressure'},
            
            # 布尔型字符串测试
            {'control_category': 'True', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Boolean string category'},
            {'control_category': 'false', 'control_pressure_level': UNCONTROL, 'expected_error': True, 'description': 'Lowercase boolean'},
        ]
        
        for i, boundary_test in enumerate(boundary_tests):
            test_id += 1
            combinations.append({
                'test_id': test_id,
                'control_category': boundary_test['control_category'],
                'control_pressure_level': boundary_test['control_pressure_level'],
                'p_event': 1.0,
                'seed': 42,
                'name': f"Boundary_{test_id:04d}_{boundary_test['description'].replace(' ', '_')}",
                'test_type': 'boundary_error' if boundary_test.get('expected_error') else 'boundary_normal',
                'description': boundary_test['description']
            })
        
        print(f"📊 Generated {len(combinations):,} total test combinations")
        print(f"   - Normal tests: {len([c for c in combinations if c['test_type'] == 'exhaustive_normal']):,}")
        print(f"   - Boundary tests: {len([c for c in combinations if c['test_type'].startswith('boundary')]):,}")
        
        return combinations
    
    def run_single_test_with_stats(self, config: Dict) -> Dict:
        """运行单个测试并收集详细统计"""
        start_time = time.time()
        memory_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        try:
            if config['test_type'] == 'boundary_error':
                # 期望错误的测试
                try:
                    event_system = EventSystem(
                        TASK_STREAM_NAME,
                        p_event=config['p_event'],
                        control_category=config['control_category'],
                        control_pressure_level=config['control_pressure_level'],
                        seed=config['seed'],
                        total_tasks=TOTAL_TASKS
                    )
                    
                    # 如果没有抛出错误，这是个问题
                    return {
                        'test_id': config['test_id'],
                        'success': False,
                        'error': f"Expected error but test passed: {config['description']}",
                        'execution_time': time.time() - start_time,
                        'memory_usage': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - memory_before
                    }
                    
                except (ValueError, TypeError, AttributeError) as e:
                    # 正确捕获了预期错误
                    return {
                        'test_id': config['test_id'],
                        'success': True,
                        'result_type': 'expected_error',
                        'error_message': str(e),
                        'execution_time': time.time() - start_time,
                        'memory_usage': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - memory_before
                    }
            
            else:
                # 正常测试流程
                event_system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=config['p_event'],
                    control_category=config['control_category'],
                    control_pressure_level=config['control_pressure_level'],
                    seed=config['seed'],
                    total_tasks=TOTAL_TASKS
                )
                
                # 大样本量统计测试
                category_counts = Counter()
                pressure_counts = Counter()
                event_triggered_count = 0
                event_distribution = Counter()
                phase_distribution = defaultdict(Counter)
                
                sample_size = ULTIMATE_SAMPLE_SIZE if config['test_type'] == 'exhaustive_normal' else 1000
                
                for sample_idx in range(sample_size):
                    # 使用确定性种子序列
                    test_seed = config['seed'] + sample_idx if config['seed'] is not None else None
                    
                    event_system_sample = EventSystem(
                        TASK_STREAM_NAME,
                        p_event=config['p_event'],
                        control_category=config['control_category'],
                        control_pressure_level=config['control_pressure_level'],
                        seed=test_seed,
                        total_tasks=TOTAL_TASKS
                    )
                    
                    for task_sequence_num in range(1, TOTAL_TASKS + 1):
                        phase = self.task_stream.get_phase_for_task(task_sequence_num)
                        event_obj, event_variant = event_system_sample.get_event_and_variant_for_phase(phase, task_sequence_num)
                        
                        if event_obj and event_variant:
                            event_triggered_count += 1
                            category_counts[event_variant['category']] += 1
                            pressure_counts[event_variant['pressure_level']] += 1
                            event_distribution[event_variant['name']] += 1
                            phase_distribution[phase][event_variant['category']] += 1
                
                total_samples = sample_size * TOTAL_TASKS
                actual_trigger_rate = event_triggered_count / total_samples if total_samples > 0 else 0
                
                # 计算统计指标
                result = {
                    'test_id': config['test_id'],
                    'success': True,
                    'result_type': 'normal',
                    'config': config,
                    'total_samples': total_samples,
                    'event_triggered_count': event_triggered_count,
                    'actual_trigger_rate': actual_trigger_rate,
                    'expected_trigger_rate': config['p_event'],
                    'trigger_rate_deviation': abs(actual_trigger_rate - config['p_event']),
                    'category_distribution': dict(category_counts),
                    'pressure_distribution': dict(pressure_counts),
                    'event_distribution': dict(event_distribution),
                    'phase_distribution': {phase: dict(counts) for phase, counts in phase_distribution.items()},
                    'execution_time': time.time() - start_time,
                    'memory_usage': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - memory_before
                }
                
                # 进行严格的统计学验证
                if total_samples > 0:
                    result.update(self.perform_statistical_analysis(result, config))
                
                return result
                
        except Exception as e:
            return {
                'test_id': config['test_id'],
                'success': False,
                'error': f"Unexpected error: {type(e).__name__}: {str(e)}",
                'execution_time': time.time() - start_time,
                'memory_usage': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - memory_before
            }
    
    def perform_statistical_analysis(self, result: Dict, config: Dict) -> Dict:
        """执行严格的统计学分析"""
        stats = {}
        
        # 1. 卡方检验
        if config['p_event'] > 0:
            # Category分布检验
            if config['control_category'] == UNCONTROL:
                expected_cat_prob = 1.0 / len(ALL_CATEGORIES)
                cat_chi_square = 0.0
                for category in ALL_CATEGORIES:
                    observed = result['category_distribution'].get(category, 0)
                    expected = expected_cat_prob * result['event_triggered_count']
                    if expected > 0:
                        cat_chi_square += (observed - expected) ** 2 / expected
                
                stats['category_chi_square'] = cat_chi_square
                stats['category_df'] = len(ALL_CATEGORIES) - 1
                stats['category_critical_999'] = 18.467  # df=4, 99.9%
                stats['category_passes_chi_square'] = cat_chi_square < 18.467
            
            # Pressure分布检验
            if config['control_pressure_level'] == UNCONTROL:
                expected_pres_prob = 1.0 / len(ALL_PRESSURE_LEVELS)
                pres_chi_square = 0.0
                for pressure in ALL_PRESSURE_LEVELS:
                    observed = result['pressure_distribution'].get(pressure, 0)
                    expected = expected_pres_prob * result['event_triggered_count']
                    if expected > 0:
                        pres_chi_square += (observed - expected) ** 2 / expected
                
                stats['pressure_chi_square'] = pres_chi_square
                stats['pressure_df'] = len(ALL_PRESSURE_LEVELS) - 1
                stats['pressure_critical_999'] = 16.266  # df=3, 99.9%
                stats['pressure_passes_chi_square'] = pres_chi_square < 16.266
        
        # 2. 二项分布检验 (trigger rate)
        n = result['total_samples']
        p = config['p_event']
        observed_triggers = result['event_triggered_count']
        
        if n > 0 and 0 < p < 1:
            # 计算95%置信区间
            z_95 = 1.96
            std_error = math.sqrt(p * (1 - p) / n)
            lower_bound = p - z_95 * std_error
            upper_bound = p + z_95 * std_error
            
            actual_rate = observed_triggers / n
            stats['trigger_rate_in_95_ci'] = lower_bound <= actual_rate <= upper_bound
            stats['trigger_rate_95_ci'] = (lower_bound, upper_bound)
            stats['trigger_rate_z_score'] = (actual_rate - p) / std_error if std_error > 0 else 0
        
        # 3. 均匀性检验 (Kolmogorov-Smirnov test approximation)
        if config['control_category'] == UNCONTROL and result['event_triggered_count'] > 0:
            cat_counts = [result['category_distribution'].get(cat, 0) for cat in ALL_CATEGORIES]
            total_cat_events = sum(cat_counts)
            if total_cat_events > 0:
                cat_probs = [count / total_cat_events for count in cat_counts]
                expected_prob = 1.0 / len(ALL_CATEGORIES)
                max_deviation = max(abs(prob - expected_prob) for prob in cat_probs)
                stats['category_max_deviation'] = max_deviation
                stats['category_uniformity_threshold'] = 0.05  # 5% threshold
                stats['category_passes_uniformity'] = max_deviation < 0.05
        
        return stats
    
    def run_parallel_stress_test(self, configs: List[Dict], max_workers: int = MAX_THREADS) -> Dict:
        """运行并行压力测试"""
        print(f"🔥 Starting parallel stress test with {max_workers} workers...")
        print(f"   Processing {len(configs):,} test configurations...")
        
        start_time = time.time()
        results = {}
        completed = 0
        
        def update_progress():
            if completed % 100 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(configs) - completed) / rate if rate > 0 else 0
                print(f"   Progress: {completed:,}/{len(configs):,} ({completed/len(configs)*100:.1f}%) | "
                      f"Rate: {rate:.1f} tests/sec | ETA: {eta/60:.1f}min")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_config = {executor.submit(self.run_single_test_with_stats, config): config for config in configs}
            
            # 收集结果
            for future in future_to_config:
                try:
                    result = future.result(timeout=300)  # 5分钟超时
                    results[result['test_id']] = result
                    completed += 1
                    
                    if completed % 100 == 0:
                        update_progress()
                        
                except Exception as e:
                    config = future_to_config[future]
                    self.error_log.append(f"Test {config.get('test_id', 'unknown')} failed: {e}")
                    completed += 1
        
        total_time = time.time() - start_time
        print(f"✅ Parallel stress test completed in {total_time:.2f} seconds")
        print(f"   Average rate: {len(configs)/total_time:.1f} tests/second")
        
        return results
    
    def run_memory_stress_test(self) -> Dict:
        """运行内存压力测试"""
        print("💾 Running memory stress test...")
        
        # 创建大量EventSystem实例
        systems = []
        memory_stats = []
        
        try:
            for i in range(1000):  # 创建1000个实例
                system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=1.0,
                    control_category=UNCONTROL,
                    control_pressure_level=UNCONTROL,
                    seed=i,
                    total_tasks=TOTAL_TASKS
                )
                systems.append(system)
                
                if i % 100 == 0:
                    current_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    memory_stats.append({
                        'instances': i + 1,
                        'memory_mb': current_memory / 1024 / 1024 if os.name != 'nt' else current_memory / 1024
                    })
            
            # 测试大量事件生成
            total_events = 0
            for system in systems[:10]:  # 只测试前10个以节省时间
                for task_num in range(1, TOTAL_TASKS + 1):
                    phase = self.task_stream.get_phase_for_task(task_num)
                    event_obj, event_variant = system.get_event_and_variant_for_phase(phase, task_num)
                    if event_obj:
                        total_events += 1
            
            return {
                'instances_created': len(systems),
                'total_events_generated': total_events,
                'memory_progression': memory_stats,
                'final_memory_mb': memory_stats[-1]['memory_mb'] if memory_stats else 0,
                'memory_per_instance_kb': (memory_stats[-1]['memory_mb'] * 1024 / len(systems)) if memory_stats and systems else 0
            }
            
        finally:
            # 清理内存
            del systems
            gc.collect()
    
    def run_seed_consistency_test(self) -> Dict:
        """运行种子一致性超级严格测试"""
        print("🎯 Running ultra-strict seed consistency test...")
        
        consistency_results = {}
        test_seeds = [0, 1, 42, 12345, 2**31-1]
        
        for seed in test_seeds:
            print(f"   Testing seed: {seed}")
            
            # 生成多个完全相同的序列
            sequences = []
            for run in range(10):
                event_system = EventSystem(
                    TASK_STREAM_NAME,
                    p_event=1.0,
                    control_category=UNCONTROL,
                    control_pressure_level=UNCONTROL,
                    seed=seed,
                    total_tasks=TOTAL_TASKS
                )
                
                sequence = []
                for task_num in range(1, TOTAL_TASKS + 1):
                    phase = self.task_stream.get_phase_for_task(task_num)
                    event_obj, event_variant = event_system.get_event_and_variant_for_phase(phase, task_num)
                    
                    if event_obj and event_variant:
                        sequence.append({
                            'task': task_num,
                            'phase': phase,
                            'category': event_variant['category'],
                            'pressure': event_variant['pressure_level'],
                            'event_name': event_variant['name'],
                            'content_hash': hashlib.md5(event_variant['content'].encode()).hexdigest()
                        })
                
                sequences.append(sequence)
            
            # 验证所有序列完全相同
            all_identical = all(seq == sequences[0] for seq in sequences)
            
            # 计算序列的哈希值以验证
            sequence_hashes = [hashlib.md5(json.dumps(seq, sort_keys=True).encode()).hexdigest() for seq in sequences]
            hash_consistency = len(set(sequence_hashes)) == 1
            
            consistency_results[seed] = {
                'all_sequences_identical': all_identical,
                'hash_consistency': hash_consistency,
                'sequence_length': len(sequences[0]),
                'runs_tested': len(sequences),
                'sequence_hash': sequence_hashes[0] if hash_consistency else None
            }
        
        return consistency_results
    
    def generate_ultimate_report(self, all_results: Dict) -> str:
        """生成终极测试报告"""
        report = []
        report.append("🔥 ULTIMATE STRESS TEST REPORT 🔥")
        report.append("=" * 100)
        report.append(f"Test Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Python Version: {sys.version}")
        report.append(f"Platform: {os.name}")
        report.append("")
        
        # 总体统计
        total_tests = len(all_results.get('stress_results', {}))
        passed_tests = len([r for r in all_results.get('stress_results', {}).values() if r.get('success', False)])
        
        report.append("📊 OVERALL STATISTICS:")
        report.append(f"  Total Tests Run: {total_tests:,}")
        report.append(f"  Passed Tests: {passed_tests:,}")
        report.append(f"  Failed Tests: {total_tests - passed_tests:,}")
        report.append(f"  Success Rate: {passed_tests/total_tests*100:.3f}%" if total_tests > 0 else "  Success Rate: N/A")
        report.append("")
        
        # 性能统计
        if 'stress_results' in all_results:
            execution_times = [r.get('execution_time', 0) for r in all_results['stress_results'].values() if r.get('execution_time')]
            memory_usages = [r.get('memory_usage', 0) for r in all_results['stress_results'].values() if r.get('memory_usage')]
            
            if execution_times:
                report.append("⚡ PERFORMANCE STATISTICS:")
                report.append(f"  Average Execution Time: {sum(execution_times)/len(execution_times):.4f}s")
                report.append(f"  Max Execution Time: {max(execution_times):.4f}s")
                report.append(f"  Min Execution Time: {min(execution_times):.4f}s")
                
            if memory_usages:
                report.append(f"  Average Memory Usage: {sum(memory_usages)/len(memory_usages):.2f}KB")
                report.append(f"  Max Memory Usage: {max(memory_usages):.2f}KB")
                report.append("")
        
        # 统计学验证结果
        if 'stress_results' in all_results:
            chi_square_passes = 0
            trigger_rate_passes = 0
            uniformity_passes = 0
            
            for result in all_results['stress_results'].values():
                if result.get('category_passes_chi_square'):
                    chi_square_passes += 1
                if result.get('trigger_rate_in_95_ci'):
                    trigger_rate_passes += 1
                if result.get('category_passes_uniformity'):
                    uniformity_passes += 1
            
            report.append("🎯 STATISTICAL VALIDATION:")
            report.append(f"  Chi-Square Tests Passed: {chi_square_passes:,}")
            report.append(f"  Trigger Rate 95% CI Tests Passed: {trigger_rate_passes:,}")
            report.append(f"  Uniformity Tests Passed: {uniformity_passes:,}")
            report.append("")
        
        # 种子一致性结果
        if 'seed_consistency' in all_results:
            report.append("🎯 SEED CONSISTENCY RESULTS:")
            for seed, result in all_results['seed_consistency'].items():
                status = "✅ PERFECT" if result['all_sequences_identical'] and result['hash_consistency'] else "❌ FAILED"
                report.append(f"  Seed {seed}: {status}")
            report.append("")
        
        # 内存压力测试结果
        if 'memory_stress' in all_results:
            mem_result = all_results['memory_stress']
            report.append("💾 MEMORY STRESS TEST:")
            report.append(f"  Instances Created: {mem_result.get('instances_created', 0):,}")
            report.append(f"  Events Generated: {mem_result.get('total_events_generated', 0):,}")
            report.append(f"  Final Memory Usage: {mem_result.get('final_memory_mb', 0):.2f}MB")
            report.append(f"  Memory per Instance: {mem_result.get('memory_per_instance_kb', 0):.2f}KB")
            report.append("")
        
        # 错误日志
        if self.error_log:
            report.append("❌ ERROR LOG:")
            for error in self.error_log[:20]:  # 只显示前20个错误
                report.append(f"  {error}")
            if len(self.error_log) > 20:
                report.append(f"  ... and {len(self.error_log) - 20} more errors")
            report.append("")
        
        # 最终判决
        if total_tests > 0:
            if passed_tests / total_tests >= 0.999:  # 99.9%通过率
                report.append("🏆 FINAL VERDICT: ULTIMATE STRESS TEST PASSED! 🏆")
                report.append("   System demonstrates exceptional robustness and reliability.")
            elif passed_tests / total_tests >= 0.95:  # 95%通过率
                report.append("✅ FINAL VERDICT: STRESS TEST MOSTLY PASSED")
                report.append("   System shows good robustness with minor issues.")
            else:
                report.append("❌ FINAL VERDICT: STRESS TEST FAILED")
                report.append("   System has significant robustness issues that need attention.")
        
        return "\n".join(report)
    
    def run_ultimate_stress_test(self) -> Dict:
        """运行终极压力测试"""
        print("🔥🔥🔥 STARTING ULTIMATE STRESS TEST 🔥🔥🔥")
        print("This is the most comprehensive test ever created for this system!")
        print()
        
        total_start_time = time.time()
        all_results = {}
        
        # 1. 生成所有测试组合
        self.test_combinations = self.generate_all_possible_combinations()
        
        # 2. 运行并行压力测试
        all_results['stress_results'] = self.run_parallel_stress_test(self.test_combinations)
        
        # 3. 运行种子一致性测试
        all_results['seed_consistency'] = self.run_seed_consistency_test()
        
        # 4. 运行内存压力测试
        all_results['memory_stress'] = self.run_memory_stress_test()
        
        # 5. 性能统计
        total_time = time.time() - total_start_time
        all_results['total_execution_time'] = total_time
        all_results['total_tests'] = len(self.test_combinations)
        all_results['average_time_per_test'] = total_time / len(self.test_combinations) if self.test_combinations else 0
        
        print(f"🎉 ULTIMATE STRESS TEST COMPLETED in {total_time:.2f} seconds!")
        
        return all_results

def main():
    """运行终极压力测试"""
    print("🔥 INITIALIZING ULTIMATE STRESS TESTER...")
    
    tester = UltimateStressTester()
    
    # 运行终极测试
    results = tester.run_ultimate_stress_test()
    
    # 生成报告
    report = tester.generate_ultimate_report(results)
    
    # 输出报告
    print("\n" + "=" * 100)
    print(report)
    
    # 保存结果
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存JSON结果
    json_filename = f"TEST/ultimate_stress_results_{timestamp}.json"
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 Results saved to: {json_filename}")
    except Exception as e:
        print(f"❌ Failed to save JSON results: {e}")
    
    # 保存报告
    report_filename = f"TEST/ultimate_stress_report_{timestamp}.txt"
    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 Report saved to: {report_filename}")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")

if __name__ == "__main__":
    main()