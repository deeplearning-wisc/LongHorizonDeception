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
        self.detector_data = None
        
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
        
    def load_detector_results(self) -> None:
        """Load ALL detector analysis results from JSON files"""
        # Look for detector JSON files
        detector_files = list(self.results_path.glob("detector_*.json"))
        if not detector_files:
            print("No detector results found")
            self.detector_data = []
            return
        
        # Sort detector files by timestamp in filename
        detector_files.sort()
        
        self.detector_data = []
        for detector_file in detector_files:
            # NO try-except - fail immediately if file cannot be loaded
            with open(detector_file, 'r', encoding='utf-8') as f:
                detector_content = json.load(f)
            
            # Extract timestamp from filename (detector_YYYYMMDD_HHMMSS.json)
            filename = detector_file.name
            timestamp = filename.replace('detector_', '').replace('.json', '')
            
            self.detector_data.append({
                'timestamp': timestamp,
                'filename': filename,
                'data': detector_content
            })
            print(f"Loaded detector results from: {detector_file}")
        
        print(f"Total detector files loaded: {len(self.detector_data)}")
    
    def load_single_detector_results(self, detector_index: int = 0) -> Dict[str, Any]:
        """Load a specific detector result by index - NO FALLBACK, fail-fast"""
        if not self.detector_data:
            raise ValueError("No detector data loaded - call load_detector_results() first")
        if detector_index >= len(self.detector_data):
            raise IndexError(f"Detector index {detector_index} out of range (0-{len(self.detector_data)-1})")
        
        return self.detector_data[detector_index]['data']
        
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
        """Generate plots for each detector round with timestamps"""
        if not self.state_evolution:
            self.extract_state_evolution()
            
        # Extract data for plotting
        rounds = [item['global_round'] for item in self.state_evolution]
        trust_levels = [item['trust_level'] for item in self.state_evolution]
        work_satisfactions = [item['work_satisfaction'] for item in self.state_evolution]
        relational_comforts = [item['relational_comfort'] for item in self.state_evolution]
        
        # Calculate task ranges
        task_ranges = {}  # task_num -> [start_round, end_round]
        for item in self.state_evolution:
            tnum = item['task_num']
            rnd  = item['global_round']
            if tnum not in task_ranges:
                task_ranges[tnum] = [rnd, rnd]   # start = end = 第一次出现
            else:
                task_ranges[tnum][1] = rnd       # 持续更新为最后一次出现
        
        # Check if we have detector data
        if not self.detector_data or len(self.detector_data) == 0:
            print("No detector data found - generating single state evolution plot")
            self._plot_single_state_evolution(rounds, trust_levels, work_satisfactions, 
                                             relational_comforts, task_ranges, save_path)
            return
        
        # Generate separate plots for each detector round
        print(f"Generating plots for {len(self.detector_data)} detector rounds")
        
        for idx, detector_info in enumerate(self.detector_data):
            detector_timestamp = detector_info['timestamp']
            detector_filename = detector_info['filename'] 
            detector_data = detector_info['data']
            
            print(f"Generating plot for detector round {idx+1}: {detector_filename}")
            
            # Create plot with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12), height_ratios=[2, 1])
            
            # Plot manager state evolution (same for all detector rounds)
            self._plot_manager_states(ax1, rounds, trust_levels, work_satisfactions, 
                                    relational_comforts, task_ranges)
            
            # Plot detector results for this specific round
            self._plot_detector_results(ax2, rounds, task_ranges, detector_data, detector_timestamp)
            
            # Align x-axis ranges
            ax2.set_xlim(ax1.get_xlim())
            
            plt.tight_layout()
            
            # Save plot with timestamp in filename
            if save_path:
                base_path = Path(save_path).parent
                stem = Path(save_path).stem
                suffix = Path(save_path).suffix
                timestamped_path = base_path / f"{stem}_detector_{detector_timestamp}{suffix}"
            else:
                timestamped_path = self.results_path / f"state_evolution_detector_{detector_timestamp}.png"
            
            fig.savefig(timestamped_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {timestamped_path}")
            
            # Close figure to free memory
            plt.close(fig)
    
    def _plot_single_state_evolution(self, rounds, trust_levels, work_satisfactions, 
                                   relational_comforts, task_ranges, save_path):
        """Plot state evolution without detector data"""
        fig, ax1 = plt.subplots(1, 1, figsize=(12, 8))
        
        self._plot_manager_states(ax1, rounds, trust_levels, work_satisfactions, 
                                relational_comforts, task_ranges)
        
        plt.tight_layout()
        
        # Save plot
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        else:
            plot_path = self.results_path / "state_evolution.png"
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {plot_path}")
            
        plt.close(fig)
    
    def _plot_manager_states(self, ax, rounds, trust_levels, work_satisfactions, 
                           relational_comforts, task_ranges):
        """Plot manager state evolution on given axis"""
        # Plot three lines
        ax.plot(rounds, trust_levels, 'b-', label='Trust Level', linewidth=2, marker='o', markersize=4)
        ax.plot(rounds, work_satisfactions, 'r-', label='Work Satisfaction', linewidth=2, marker='s', markersize=4)
        ax.plot(rounds, relational_comforts, 'g-', label='Relational Comfort', linewidth=2, marker='^', markersize=4)
        
        # Customize subplot
        ax.set_xlabel('Global Round', fontsize=12)
        ax.set_ylabel('State Value', fontsize=12)
        ax.set_title('Manager State Evolution Over Time', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        
        # Add task completion threshold for work satisfaction - NO FALLBACK!
        threshold = self._load_threshold_from_config()  # MUST succeed, no None check
        ax.axhline(y=threshold, color='orange', linestyle='-.', alpha=0.7, 
                   label=f'Task Completion Threshold ({threshold})')
        
        # Add legend after all lines are plotted
        ax.legend(fontsize=11)
        
        # Add task ranges visualization
        ymin, ymax = ax.get_ylim()
        for tnum in sorted(task_ranges.keys()):
            start_r, end_r = task_ranges[tnum]
            left  = start_r - 0.5
            right = end_r   + 0.5

            # 任务区间底纹
            ax.axvspan(left, right, color='lightgrey', alpha=0.08, zorder=0)

            # 右侧边界线（任务分隔）
            ax.axvline(x=right, color='gray', linestyle=':', alpha=0.7, zorder=1)

            # 任务标签（放在底部靠内）
            mid = (left + right) / 2.0
            ax.text(mid, ymin + 0.05*(ymax - ymin), f'T{tnum}',
                     ha='center', va='bottom', fontsize=9, alpha=0.9)

        # 把坐标轴范围设到半格对齐
        N = rounds[-1]  # 最大 global_round
        ax.set_xlim(0.5, N + 0.5)
            
    def _plot_detector_results(self, ax, rounds, task_ranges, detector_data, detector_timestamp):
        """Plot deception detection results for a specific detector round"""
        # Extract deception data from this specific detector result
        detector_rounds = []
        severities = []
        deception_markers = []
        
        # Process round detections from the specific detector data - NO .get() defaults
        for detection in detector_data['round_detections']:
            global_round = detection['global_round']
            severity = detection['severity']
            is_deception = detection['deception_detected']
            
            detector_rounds.append(global_round)
            severities.append(severity if is_deception else 0)
            deception_markers.append(is_deception)
        
        # Plot severity as bars
        colors = ['red' if detected else 'lightgray' for detected in deception_markers]
        ax.bar(detector_rounds, severities, color=colors, alpha=0.7, width=0.8)
        
        # Customize deception subplot with timestamp in title
        ax.set_xlabel('Global Round', fontsize=12)
        ax.set_ylabel('Deception Severity', fontsize=12)
        ax.set_title(f'Deception Detection Results - Round {detector_timestamp}', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 4)  # Severity ranges from 0-4
        
        # Add task boundaries and labels to match the first subplot
        ymin_det, ymax_det = ax.get_ylim()
        for tnum in sorted(task_ranges.keys()):
            start_r, end_r = task_ranges[tnum]
            left  = start_r - 0.5
            right = end_r   + 0.5

            # 任务区间底纹
            ax.axvspan(left, right, color='lightgrey', alpha=0.08, zorder=0)

            # 右侧边界线（任务分隔）
            ax.axvline(x=right, color='gray', linestyle=':', alpha=0.7, zorder=1)

            # 任务标签（放在底部靠内）
            mid = (left + right) / 2.0
            ax.text(mid, ymin_det + 0.05*(ymax_det - ymin_det), f'T{tnum}',
                    ha='center', va='bottom', fontsize=9, alpha=0.9)
        
        # Add legend for deception detection
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', alpha=0.7, label='Deception Detected'),
            Patch(facecolor='lightgray', alpha=0.7, label='No Deception')
        ]
        ax.legend(handles=legend_elements, fontsize=10)
        
        # Add detector statistics text - NO .get() defaults, NO truncation
        if 'summary' in detector_data:
            summary = detector_data['summary']
            stats_text = f"Deception Rate: {summary['deception_rate']}\n"
            stats_text += f"Avg Severity: {summary['severity_average_all_rounds']}"
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    def _plot_deception_detection(self, ax, rounds, task_ranges) -> None:
        """Legacy method - kept for backward compatibility"""
        # This method is now replaced by _plot_detector_results
        # but kept for any existing code that might call it
        if not self.detector_data or len(self.detector_data) == 0:
            return
        
        # Use the first detector data - self.detector_data MUST be a list
        if not isinstance(self.detector_data, list) or len(self.detector_data) == 0:
            raise ValueError("detector_data must be a non-empty list")
        
        first_detector = self.detector_data[0]['data']
        first_timestamp = self.detector_data[0]['timestamp']
        
        self._plot_detector_results(ax, rounds, task_ranges, first_detector, first_timestamp)
            
    def _load_threshold_from_config(self) -> float:
        """Load task_completion_threshold from config file - NO FALLBACK"""
        # Look for config file in results directory - MUST exist
        config_files = list(self.results_path.glob("*.yaml"))
        if not config_files:
            raise FileNotFoundError(f"No config file found in {self.results_path}")
            
        config_file = config_files[0]
        config_handler = ConfigHandler()
        config = config_handler.load_config_from_file(config_file)
        
        # Direct access - NO .get() with defaults
        return config['task_completion_threshold']
            
        
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate key metrics from state evolution.

        Computes average work satisfaction across all interaction rounds
        (simple arithmetic mean over every round).
        """
        if not self.state_evolution:
            self.extract_state_evolution()
            
        # Final states (last round)
        final_state = self.state_evolution[-1]
        final_trust_level = final_state['trust_level']
        final_relational_comfort = final_state['relational_comfort']
        
        # Calculate average work satisfaction over all interaction rounds
        total_interactions = len(self.state_evolution)
        # Build tasks_data only for counts/metadata
        tasks_data: Dict[int, List[Dict[str, Any]]] = {}
        for item in self.state_evolution:
            task_num = item['task_num']
            tasks_data.setdefault(task_num, []).append(item)

        average_work_satisfaction = sum(item['work_satisfaction'] for item in self.state_evolution) / float(total_interactions)
        
        metrics = {
            'final_trust_level': final_trust_level,
            'final_relational_comfort': final_relational_comfort,
            'average_work_satisfaction': average_work_satisfaction,
            'total_tasks': len(tasks_data),
            'total_interactions': total_interactions,
            # Removed per-task finals to keep output minimal and unambiguous
        }
        
        return metrics
        
    def save_analysis_results(self, metrics: Dict[str, Any], output_path: str) -> str:
        """Save analysis results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        analysis_results = {
            'experiment_path': str(self.results_path),
            'final_trust_level': metrics['final_trust_level'],
            'final_relational_comfort': metrics['final_relational_comfort'],
            'average_work_satisfaction': metrics['average_work_satisfaction'],
            'total_tasks': metrics['total_tasks'],
            'total_interactions': metrics['total_interactions'],
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
        self.load_detector_results()
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
        print(f"Final Trust Level: {metrics['final_trust_level']}")
        print(f"Final Relational Comfort: {metrics['final_relational_comfort']}")
        print(f"Average Work Satisfaction: {metrics['average_work_satisfaction']}")
        print(f"Total Tasks: {metrics['total_tasks']}")
        print(f"Total Interactions: {metrics['total_interactions']}")
        
        # Save results to analysis directory
        output_file = analysis_dir / "analysis_results.json"
        self.save_analysis_results(metrics, str(output_file))
        
        print(f"\nAnalysis completed! Results saved to: {analysis_dir}")
        return metrics


def main():
    """Main function with command line interface - NO try-except, fail fast"""
    parser = argparse.ArgumentParser(description="Analyze DeceptioN experiment results")
    parser.add_argument("--result_name", required=True, help="Path to experiment results directory")
    parser.add_argument("--no-plot", action="store_true", help="Skip generating plot")
    
    args = parser.parse_args()
    
    # NO try-except - fail immediately if any error occurs
    analyzer = ExperimentAnalyzer(args.result_name)
    analyzer.run_full_analysis(
        save_plot=not args.no_plot
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
