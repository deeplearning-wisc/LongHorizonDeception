#!/usr/bin/env python3
"""
Analyzer for DeceptioN experiment results
Analyzes manager state evolution and calculates key metrics
"""

import json
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import numpy as np
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_handler import ConfigHandler

class ExperimentAnalyzer:
    """Analyzer for DeceptioN experiment results"""
    
    def __init__(self, results_path: str):
        """Initialize analyzer with results directory path"""
        self.results_path = Path(results_path)
        self.results_data = None
        self.state_evolution = []
        
    def load_results(self) -> None:
        """Load experiment results from JSON file"""
        result_file = self.results_path / "result.json"
        if not result_file.exists():
            raise FileNotFoundError(f"No result.json found in {self.results_path}")
            
        with open(result_file, 'r', encoding='utf-8') as f:
            self.results_data = json.load(f)
            
        print(f"Loaded results from: {result_file}")
        print(f"Experiment: {self.results_data['metadata']['task_stream_name']}")
        print(f"Total tasks: {len(self.results_data['experiment']['tasks'])}")
        
    def extract_state_evolution(self) -> List[Dict[str, Any]]:
        """Extract state evolution from experiment results"""
        evolution = []
        global_round = 0
        
        # Access tasks array from experiment
        tasks = self.results_data['experiment']['tasks']
        
        for task_idx, task_data in enumerate(tasks):
            task_info = task_data['task']
            task_num = task_info['task_sequence_num']
            task_title = task_info['title']
            
            # Process rounds array
            rounds = task_data['rounds']
            for round_idx, round_data in enumerate(rounds):
                global_round += 1
                
                # Get state from manager evaluation
                manager_eval = round_data['manager_evaluation']
                current_state = manager_eval['state_updates']['new_state']
                
                evolution.append({
                    'global_round': global_round,
                    'task_num': task_num,
                    'round_num': round_data['round'],
                    'task_title': task_title,
                    'trust_level': current_state['trust_level'],
                    'work_satisfaction': current_state['work_satisfaction'],
                    'relational_comfort': current_state['relational_comfort']
                })
                
        self.state_evolution = evolution
        return evolution
        
    def plot_state_evolution(self, save_path: str = None) -> None:
        """Plot state evolution over time"""
        if not self.state_evolution:
            self.extract_state_evolution()
            
        # Extract data for plotting
        rounds = [item['global_round'] for item in self.state_evolution]
        trust_levels = [item['trust_level'] for item in self.state_evolution]
        work_satisfactions = [item['work_satisfaction'] for item in self.state_evolution]
        relational_comforts = [item['relational_comfort'] for item in self.state_evolution]
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        # Plot three lines
        plt.plot(rounds, trust_levels, 'b-', label='Trust Level', linewidth=2, marker='o', markersize=4)
        plt.plot(rounds, work_satisfactions, 'r-', label='Work Satisfaction', linewidth=2, marker='s', markersize=4)
        plt.plot(rounds, relational_comforts, 'g-', label='Relational Comfort', linewidth=2, marker='^', markersize=4)
        
        # Customize plot
        plt.xlabel('Global Round', fontsize=12)
        plt.ylabel('State Value', fontsize=12)
        plt.title('Manager State Evolution Over Time', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        
        # Add task completion threshold for work satisfaction
        # Load threshold from config file
        threshold = self._load_threshold_from_config()
        if threshold is not None:
            plt.axhline(y=threshold, color='orange', linestyle='-.', alpha=0.7, 
                       label=f'Task Completion Threshold ({threshold})')
        else:
            # Fallback if config not found
            threshold = 0.2
            plt.axhline(y=threshold, color='orange', linestyle='-.', alpha=0.7, 
                       label=f'Task Completion Threshold ({threshold}) [default]')
        
        # Add legend after all lines are plotted
        plt.legend(fontsize=11)
        
        # === 计算每个任务的 start/end（基于已提取的 state_evolution） ===
        task_ranges = {}  # task_num -> [start_round, end_round]
        for item in self.state_evolution:
            tnum = item['task_num']
            rnd  = item['global_round']
            if tnum not in task_ranges:
                task_ranges[tnum] = [rnd, rnd]   # start = end = 第一次出现
            else:
                task_ranges[tnum][1] = rnd       # 持续更新为最后一次出现

        # === 画任务区间底纹 + 竖线边界 + 标签 ===
        # 建议用淡灰底纹区分任务块，标签放在中点
        ymin, ymax = plt.ylim()
        for tnum in sorted(task_ranges.keys()):
            start_r, end_r = task_ranges[tnum]
            left  = start_r - 0.5
            right = end_r   + 0.5

            # 任务区间底纹
            plt.axvspan(left, right, color='lightgrey', alpha=0.08, zorder=0)

            # 右侧边界线（任务分隔）
            plt.axvline(x=right, color='gray', linestyle=':', alpha=0.7, zorder=1)

            # 任务标签（放在底部靠内）
            mid = (left + right) / 2.0
            plt.text(mid, ymin + 0.05*(ymax - ymin), f'T{tnum}',
                     ha='center', va='bottom', fontsize=9, alpha=0.9)

        # 把坐标轴范围设到半格对齐
        N = rounds[-1]  # 最大 global_round
        plt.xlim(0.5, N + 0.5)
        
        plt.tight_layout()
        
        # Save plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        else:
            plot_path = self.results_path / "state_evolution.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {plot_path}")
            
    def _load_threshold_from_config(self) -> float:
        """Load task_completion_threshold from config file in results directory"""
        try:
            # Look for config file in results directory
            config_files = list(self.results_path.glob("*.yaml"))
            if not config_files:
                return None
                
            config_file = config_files[0]
            config_handler = ConfigHandler()
            config = config_handler.load_config_from_file(config_file)
            
            return config.get('task_completion_threshold', 0.2)
        except Exception as e:
            print(f"Warning: Could not load threshold from config: {e}")
            return None
            
        
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate key metrics from state evolution"""
        if not self.state_evolution:
            self.extract_state_evolution()
            
        # Final states (last round)
        final_state = self.state_evolution[-1]
        final_trust_level = final_state['trust_level']
        final_relational_comfort = final_state['relational_comfort']
        
        # Calculate normalized work satisfaction
        # Sum of each task's final work satisfaction / total interaction rounds
        task_final_work_satisfactions = []
        total_interactions = len(self.state_evolution)
        
        # Group by task to find final work satisfaction for each task
        tasks_data = {}
        for item in self.state_evolution:
            task_num = item['task_num']
            if task_num not in tasks_data:
                tasks_data[task_num] = []
            tasks_data[task_num].append(item)
            
        # Get final work satisfaction for each task
        for task_num, task_rounds in tasks_data.items():
            final_work_sat = task_rounds[-1]['work_satisfaction']  # Last round of each task
            task_final_work_satisfactions.append(final_work_sat)
            
        normalized_work_satisfaction = sum(task_final_work_satisfactions) / total_interactions
        
        metrics = {
            'final_trust_level': final_trust_level,
            'final_relational_comfort': final_relational_comfort,
            'normalized_work_satisfaction': normalized_work_satisfaction,
            'total_tasks': len(tasks_data),
            'total_interactions': total_interactions,
            'task_final_work_satisfactions': task_final_work_satisfactions
        }
        
        return metrics
        
    def save_analysis_results(self, metrics: Dict[str, Any], output_path: str) -> str:
        """Save analysis results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        analysis_results = {
            'experiment_path': str(self.results_path),
            'final_trust_level': metrics['final_trust_level'],
            'final_relational_comfort': metrics['final_relational_comfort'],
            'normalized_work_satisfaction': metrics['normalized_work_satisfaction'],
            'total_tasks': metrics['total_tasks'],
            'total_interactions': metrics['total_interactions'],
            'task_final_work_satisfactions': metrics['task_final_work_satisfactions'],
            'analysis_timestamp': timestamp
        }
        
        output_file = Path(output_path)
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
            
        print(f"Analysis results saved to: {output_file}")
        return str(output_file)
        
    def run_full_analysis(self, save_plot: bool = True) -> Dict[str, Any]:
        """Run complete analysis pipeline"""
        print("=" * 60)
        print("DeceptioN Experiment Analysis")
        print("=" * 60)
        
        # Create analysis directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_dir = self.results_path / f"analysis_{timestamp}"
        analysis_dir.mkdir(exist_ok=True)
        print(f"Analysis directory: {analysis_dir}")
        
        # Load and process data
        self.load_results()
        self.extract_state_evolution()
        
        # Generate plot
        if save_plot:
            plot_path = analysis_dir / "state_evolution.png"
            self.plot_state_evolution(str(plot_path))
        else:
            self.plot_state_evolution()
            
        # Calculate metrics
        metrics = self.calculate_metrics()
        
        # Print summary
        print("\nAnalysis Summary:")
        print("-" * 40)
        print(f"Final Trust Level: {metrics['final_trust_level']:.3f}")
        print(f"Final Relational Comfort: {metrics['final_relational_comfort']:.3f}")
        print(f"Normalized Work Satisfaction: {metrics['normalized_work_satisfaction']:.3f}")
        print(f"Total Tasks: {metrics['total_tasks']}")
        print(f"Total Interactions: {metrics['total_interactions']}")
        
        # Save results to analysis directory
        output_file = analysis_dir / "analysis_results.json"
        self.save_analysis_results(metrics, str(output_file))
        
        print(f"\nAnalysis completed! Results saved to: {analysis_dir}")
        return metrics


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Analyze DeceptioN experiment results")
    parser.add_argument("--result_name", required=True, help="Path to experiment results directory")
    parser.add_argument("--no-plot", action="store_true", help="Skip generating plot")
    
    args = parser.parse_args()
    
    try:
        analyzer = ExperimentAnalyzer(args.result_name)
        analyzer.run_full_analysis(
            save_plot=not args.no_plot
        )
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())