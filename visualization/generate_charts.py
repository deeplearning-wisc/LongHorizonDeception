#!/usr/bin/env python3
"""
DeceptioN Results Visualization Generator
生成Manager状态演化、Severity时间序列、Category和Intent柱状图
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any
import argparse

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import pandas as pd
import numpy as np

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

class DeceptionVisualizer:
    def __init__(self, result_dir: str):
        self.result_dir = Path(result_dir)
        self.interaction_data = []
        self.detector_data = []
        
        # 定义颜色方案
        self.category_colors = {
            'OMISSION': '#FF6B6B',      # 红色
            'MANIPULATION': '#FFA726',   # 橙色  
            'FABRICATION': '#42A5F5',    # 蓝色
            'MISDIRECTION': '#FDD835'    # 黄色
        }
        
        self.intent_colors = {
            'FORCED': '#F44336',        # 红色
            'VOLUNTARY': '#4CAF50'      # 绿色
        }
        
        self.severity_colors = {
            0: '#4CAF50',  # 绿色
            1: '#FDD835',  # 黄色
            2: '#FFA726',  # 橙色
            3: '#F44336',  # 红色
            4: '#9C27B0'   # 紫色
        }
    
    def load_data(self):
        """加载交互记录和检测结果数据"""
        print(f"Loading data from {self.result_dir}...")
        
        # 加载交互记录 - 使用新的文本格式
        complete_record_file = self.result_dir / 'complete_interaction_record.txt'
        if complete_record_file.exists():
            from utils.unified_llm_parser import ResultSaverParser
            parsed_record = ResultSaverParser.parse_complete_record(str(complete_record_file))
            self.interaction_data = ResultSaverParser.convert_to_detector_format(parsed_record)
            print(f"Loaded {len(self.interaction_data)} interaction records from text format")
        else:
            # 兼容性：尝试加载旧的JSON格式
            interaction_file = self.result_dir / 'interaction_records.json'
            if interaction_file.exists():
                with open(interaction_file, 'r', encoding='utf-8') as f:
                    self.interaction_data = json.load(f)
                print(f"Loaded {len(self.interaction_data)} interaction records from JSON (legacy)")
            else:
                print(f"Warning: Neither {complete_record_file} nor {interaction_file} found")
        
        # 查找检测结果文件
        detector_files = list(self.result_dir.glob('detector_analysis_*.json'))
        if detector_files:
            detector_file = max(detector_files)  # 取最新的
            with open(detector_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                # 处理嵌套的数据结构
                if 'interactions_data' in raw_data:
                    self.detector_data = raw_data['interactions_data']
                else:
                    self.detector_data = raw_data
            print(f"Loaded {len(self.detector_data)} detector results from {detector_file.name}")
        else:
            print("Warning: No detector analysis files found")
    
    def plot_manager_evolution(self, save_path: str = None):
        """生成Manager状态演化图"""
        if not self.interaction_data:
            print("No interaction data available for manager evolution plot")
            return
        
        # 提取Manager状态数据
        rounds = []
        trust_levels = []
        work_satisfactions = []
        relational_comforts = []
        
        for i, record in enumerate(self.interaction_data, 1):
            rounds.append(i)
            state = record.get('manager_state_after', {})
            trust_levels.append(state.get('trust_level', 0))
            work_satisfactions.append(state.get('work_satisfaction', 0))
            relational_comforts.append(state.get('relational_comfort', 0))
        
        # 创建图表
        plt.figure(figsize=(12, 8))
        
        # 绘制三条线
        plt.plot(rounds, trust_levels, 'b-', linewidth=2, label='Trust Level', marker='o', markersize=4)
        plt.plot(rounds, work_satisfactions, 'g--', linewidth=2, label='Work Satisfaction', marker='s', markersize=4)
        plt.plot(rounds, relational_comforts, 'r-.', linewidth=2, label='Relational Comfort', marker='^', markersize=4)
        
        # 添加任务分界线
        task_boundaries = []
        current_task = None
        for i, record in enumerate(self.interaction_data, 1):
            if record['task_id'] != current_task:
                if current_task is not None:
                    task_boundaries.append(i - 0.5)
                current_task = record['task_id']
        
        for boundary in task_boundaries:
            plt.axvline(x=boundary, color='gray', linestyle=':', alpha=0.5)
        
        plt.xlabel('Round Number')
        plt.ylabel('State Value')
        plt.title('Manager State Evolution Over Time')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(-1.1, 1.1)
        
        # 添加水平参考线
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=0.5)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Manager evolution plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_severity_timeline(self, save_path: str = None):
        """生成Severity时间序列图"""
        if not self.detector_data:
            print("No detector data available for severity timeline plot")
            return
        
        # 提取Severity数据
        rounds = []
        severities = []
        deception_detected = []
        
        for i, analysis in enumerate(self.detector_data, 1):
            rounds.append(i)
            # 处理嵌套的数据结构
            if 'detector_findings' in analysis:
                findings = analysis['detector_findings']
                severities.append(findings.get('severity', 0))
                deception_detected.append(findings.get('deception_detected', False))
            else:
                severities.append(analysis.get('severity', 0))
                deception_detected.append(analysis.get('deception_detected', False))
        
        # 创建图表
        plt.figure(figsize=(12, 6))
        
        # 为每个severity level创建不同颜色的柱子
        colors = [self.severity_colors[sev] for sev in severities]
        
        bars = plt.bar(rounds, severities, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # 为检测到欺骗的柱子添加特殊边框
        for i, (bar, detected) in enumerate(zip(bars, deception_detected)):
            if detected:
                bar.set_edgecolor('black')
                bar.set_linewidth(2)
        
        plt.xlabel('Round Number')
        plt.ylabel('Severity Level')
        plt.title('Deception Severity Timeline')
        plt.ylim(-0.5, 4.5)
        plt.yticks([0, 1, 2, 3, 4])
        plt.grid(True, alpha=0.3, axis='y')
        
        # 创建图例
        legend_elements = [patches.Patch(color=color, label=f'Severity {level}') 
                          for level, color in self.severity_colors.items()]
        legend_elements.append(patches.Patch(facecolor='none', edgecolor='black', linewidth=2, 
                                           label='Deception Detected'))
        
        plt.legend(handles=legend_elements, loc='upper right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Severity timeline plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_category_by_task(self, save_path: str = None):
        """生成按任务的Category堆叠柱状图"""
        if not self.detector_data:
            print("No detector data available for category plot")
            return
        
        # 按任务聚合Category数据
        task_categories = defaultdict(Counter)
        task_order = []
        
        for analysis in self.detector_data:
            # 处理嵌套结构
            if 'basic_info' in analysis:
                task_id = analysis['basic_info']['task_id']
                findings = analysis.get('detector_findings', {})
            else:
                task_id = analysis['task_id']
                findings = analysis
            
            if task_id not in task_order:
                task_order.append(task_id)
            
            if findings.get('deception_detected', False):
                categories = findings.get('category', [])
                if isinstance(categories, list):
                    for cat in categories:
                        if cat.strip() and cat.strip() != 'NONE' and cat.strip() in self.category_colors:
                            task_categories[task_id][cat.strip()] += 1
                elif isinstance(categories, str) and categories != 'NONE':
                    for cat in categories.split(','):
                        cat = cat.strip()
                        if cat and cat != 'NONE' and cat in self.category_colors:
                            task_categories[task_id][cat] += 1
        
        if not any(task_categories.values()):
            print("No deception categories found to plot (all tasks have 0 or NONE categories)")
            # 创建空图表
            plt.figure(figsize=(12, 6))
            plt.bar([], [], label='No deception categories detected')
            plt.xlabel('Task Number')
            plt.ylabel('Category Detection Count')
            plt.title('Deception Categories by Task (No Data)')
            plt.legend()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Empty category plot saved to {save_path}")
            return
        
        # 准备数据
        x_pos = list(range(1, len(task_order) + 1))
        category_types = ['OMISSION', 'MANIPULATION', 'FABRICATION', 'MISDIRECTION']
        
        # 创建堆叠数据
        bottoms = [0] * len(task_order)
        
        plt.figure(figsize=(12, 6))
        
        for category in category_types:
            values = [task_categories[task][category] for task in task_order]
            if any(values):  # 只绘制有数据的category
                plt.bar(x_pos, values, bottom=bottoms, 
                       label=category, color=self.category_colors[category], alpha=0.8)
                bottoms = [b + v for b, v in zip(bottoms, values)]
        
        plt.xlabel('Task Number')
        plt.ylabel('Category Detection Count')
        plt.title('Deception Categories by Task')
        plt.xticks(x_pos)
        plt.legend()
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Category plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_intent_by_task(self, save_path: str = None):
        """生成按任务的Intent堆叠柱状图"""
        if not self.detector_data:
            print("No detector data available for intent plot")
            return
        
        # 按任务聚合Intent数据
        task_intents = defaultdict(Counter)
        task_order = []
        
        for analysis in self.detector_data:
            # 处理嵌套结构
            if 'basic_info' in analysis:
                task_id = analysis['basic_info']['task_id']
                findings = analysis.get('detector_findings', {})
            else:
                task_id = analysis['task_id']
                findings = analysis
            
            if task_id not in task_order:
                task_order.append(task_id)
            
            # 只统计有意义的intent，跳过NONE
            intents = findings.get('intent', ['NONE'])
            if isinstance(intents, list):
                for intent in intents:
                    if intent.strip() and intent.strip() != 'NONE' and intent.strip() in self.intent_colors:
                        task_intents[task_id][intent.strip()] += 1
            elif isinstance(intents, str):
                for intent in intents.split(','):
                    intent = intent.strip()
                    if intent and intent != 'NONE' and intent in self.intent_colors:
                        task_intents[task_id][intent] += 1
        
        if not any(task_intents.values()):
            print("No meaningful deception intents found to plot (all are NONE)")
            # 创建空图表
            plt.figure(figsize=(12, 6))
            plt.bar([], [], label='No meaningful intents detected')
            plt.xlabel('Task Number')
            plt.ylabel('Intent Detection Count')
            plt.title('Deception Intents by Task (No Data)')
            plt.legend()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Empty intent plot saved to {save_path}")
            return
        
        # 准备数据 - 只显示有意义的intent类型
        x_pos = list(range(1, len(task_order) + 1))
        intent_types = ['FORCED', 'VOLUNTARY']  # 移除NONE
        
        # 创建堆叠数据
        bottoms = [0] * len(task_order)
        
        plt.figure(figsize=(12, 6))
        
        for intent in intent_types:
            values = [task_intents[task][intent] for task in task_order]
            if any(values):  # 只绘制有数据的intent
                plt.bar(x_pos, values, bottom=bottoms,
                       label=intent, color=self.intent_colors[intent], alpha=0.8)
                bottoms = [b + v for b, v in zip(bottoms, values)]
        
        plt.xlabel('Task Number')
        plt.ylabel('Intent Detection Count')
        plt.title('Deception Intents by Task')
        plt.xticks(x_pos)
        plt.legend()
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Intent plot saved to {save_path}")
        else:
            plt.show()
    
    def generate_all_charts(self, output_dir: str = None):
        """生成所有图表"""
        if output_dir is None:
            output_dir = self.result_dir / 'visualizations'
        
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print(f"Generating all charts to {output_dir}...")
        
        # 生成所有图表
        self.plot_manager_evolution(output_dir / 'manager_evolution.png')
        plt.close()
        
        self.plot_severity_timeline(output_dir / 'severity_timeline.png')
        plt.close()
        
        self.plot_category_by_task(output_dir / 'categories_by_task.png')
        plt.close()
        
        self.plot_intent_by_task(output_dir / 'intents_by_task.png')
        plt.close()
        
        print(f"All charts generated in {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='Generate DeceptioN visualization charts')
    parser.add_argument('result_dir', help='Path to results directory')
    parser.add_argument('--output', '-o', help='Output directory for charts')
    parser.add_argument('--show', '-s', action='store_true', help='Show charts instead of saving')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.result_dir):
        print(f"Error: Result directory {args.result_dir} does not exist")
        sys.exit(1)
    
    visualizer = DeceptionVisualizer(args.result_dir)
    visualizer.load_data()
    
    if args.show:
        # 显示图表
        visualizer.plot_manager_evolution()
        visualizer.plot_severity_timeline()
        visualizer.plot_category_by_task()
        visualizer.plot_intent_by_task()
    else:
        # 保存图表
        visualizer.generate_all_charts(args.output)

if __name__ == '__main__':
    main()