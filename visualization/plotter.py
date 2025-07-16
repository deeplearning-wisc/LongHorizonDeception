import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import matplotlib.dates as mdates
from datetime import datetime

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class DeceptionPlotter:
    """Plotter for LDLE experiment visualizations"""
    
    def __init__(self, save_path: str = "./"):
        """
        Initialize plotter with save directory
        
        Args:
            save_path: Directory to save generated plots
        """
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # Plot styling
        self.figure_size = (12, 8)
        self.dpi = 300
        self.color_palette = {
            'deceptive': '#ff4444',
            'positive': '#44ff44', 
            'normal': '#4444ff',
            'detected': '#ff6b6b',
            'missed': '#74c0fc',
            'trust_hostile': '#d63031',
            'trust_suspicious': '#fdcb6e',
            'trust_neutral': '#6c5ce7',
            'trust_high': '#00b894'
        }
    
    def plot_intent_distribution(self, intent_data: Dict[str, int]) -> str:
        """
        Create pie chart for deception intent distribution
        
        Args:
            intent_data: Dictionary with intent counts
            
        Returns:
            Path to saved plot
        """
        if not intent_data:
            print("⚠️ No intent data to plot")
            return ""
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Prepare data
        labels = list(intent_data.keys())
        sizes = list(intent_data.values())
        total = sum(sizes)
        
        # Calculate exact percentages that sum to 100%
        percentages = []
        for size in sizes:
            percentages.append(size / total * 100)
        
        # Round percentages and ensure they sum to 100%
        rounded_percentages = [round(p, 1) for p in percentages]
        difference = 100.0 - sum(rounded_percentages)
        
        # Adjust the largest segment to make sum exactly 100%
        if difference != 0:
            max_idx = rounded_percentages.index(max(rounded_percentages))
            rounded_percentages[max_idx] += difference
        
        # Create pie chart without autopct first
        wedges, texts = ax.pie(
            sizes, 
            labels=labels, 
            startangle=90,
            explode=[0.05] * len(labels)
        )
        
        # Manually add percentage labels
        for i, (wedge, percentage) in enumerate(zip(wedges, rounded_percentages)):
            angle = (wedge.theta2 + wedge.theta1) / 2
            x = wedge.r * 0.7 * np.cos(np.radians(angle))
            y = wedge.r * 0.7 * np.sin(np.radians(angle))
            ax.text(x, y, f'{percentage:.1f}%', 
                   horizontalalignment='center', 
                   verticalalignment='center',
                   fontsize=10, fontweight='bold')
        
        # Styling
        ax.set_title('Deception Intent Distribution', fontsize=16, fontweight='bold')
        
        # Save plot
        save_file = self.save_path / "intent_distribution.png"
        plt.tight_layout()
        plt.savefig(save_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Intent distribution plot saved: {save_file}")
        return str(save_file)
    
    def plot_category_distribution(self, category_data: Dict[str, int]) -> str:
        """
        Create pie chart for deception category distribution
        
        Args:
            category_data: Dictionary with category counts
            
        Returns:
            Path to saved plot
        """
        if not category_data:
            print("⚠️ No category data to plot")
            return ""
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Prepare data
        labels = list(category_data.keys())
        sizes = list(category_data.values())
        total = sum(sizes)
        
        # Calculate exact percentages that sum to 100%
        percentages = []
        for size in sizes:
            percentages.append(size / total * 100)
        
        # Round percentages and ensure they sum to 100%
        rounded_percentages = [round(p, 1) for p in percentages]
        difference = 100.0 - sum(rounded_percentages)
        
        # Adjust the largest segment to make sum exactly 100%
        if difference != 0:
            max_idx = rounded_percentages.index(max(rounded_percentages))
            rounded_percentages[max_idx] += difference
        
        # Create pie chart without autopct first
        wedges, texts = ax.pie(
            sizes, 
            labels=labels, 
            startangle=90,
            explode=[0.05] * len(labels)
        )
        
        # Manually add percentage labels
        for i, (wedge, percentage) in enumerate(zip(wedges, rounded_percentages)):
            angle = (wedge.theta2 + wedge.theta1) / 2
            x = wedge.r * 0.7 * np.cos(np.radians(angle))
            y = wedge.r * 0.7 * np.sin(np.radians(angle))
            ax.text(x, y, f'{percentage:.1f}%', 
                   horizontalalignment='center', 
                   verticalalignment='center',
                   fontsize=10, fontweight='bold')
        
        # Styling
        ax.set_title('Deception Category Distribution', fontsize=16, fontweight='bold')
        
        # Save plot
        save_file = self.save_path / "category_distribution.png"
        plt.tight_layout()
        plt.savefig(save_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Category distribution plot saved: {save_file}")
        return str(save_file)
    
    def plot_detection_comparison(self, detection_df: pd.DataFrame) -> str:
        """
        Create bar chart comparing Judge vs Manager detection over time
        
        Args:
            detection_df: DataFrame with detection comparison data
            
        Returns:
            Path to saved plot
        """
        if detection_df.empty:
            print("⚠️ No detection data to plot")
            return ""
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Group by day and aggregate detection counts
        day_stats = detection_df.groupby('day').agg({
            'judge_detected': 'sum',
            'manager_noticed': 'sum',
            'both_detected': 'sum',
            'judge_only': 'sum',
            'manager_only': 'sum',
            'neither_detected': 'sum'
        }).reset_index()
        
        # Create grouped bar chart
        x = day_stats['day']
        width = 0.35
        
        x_pos = np.arange(len(x))
        ax.bar(x_pos - width/2, day_stats['judge_detected'], width, 
               label='Judge Detected', color=self.color_palette['detected'], alpha=0.8)
        ax.bar(x_pos + width/2, day_stats['manager_noticed'], width,
               label='Manager Noticed', color=self.color_palette['missed'], alpha=0.8)
        
        # Styling
        ax.set_xlabel('Day', fontsize=12)
        ax.set_ylabel('Detection Count', fontsize=12)
        ax.set_title('Detection Comparison: Judge vs Manager Over Time', fontsize=16, fontweight='bold')
        
        # Fix x-axis to show integer days
        ax.set_xticks(x_pos)
        ax.set_xticklabels([int(day) for day in x])
        
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Save plot
        save_file = self.save_path / "detection_comparison.png"
        plt.tight_layout()
        plt.savefig(save_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Detection comparison plot saved: {save_file}")
        return str(save_file)
    
    def plot_trust_evolution(self, trust_df: pd.DataFrame) -> str:
        """
        Create line chart for Manager trust level evolution
        
        Args:
            trust_df: DataFrame with trust evolution data
            
        Returns:
            Path to saved plot
        """
        if trust_df.empty:
            print("⚠️ No trust data to plot")
            return ""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Plot 1: Trust level (categorical)
        trust_colors = {
            'HOSTILE': self.color_palette['trust_hostile'],
            'SUSPICIOUS': self.color_palette['trust_suspicious'], 
            'NEUTRAL': self.color_palette['trust_neutral'],
            'TRUST': self.color_palette['trust_high']
        }
        
        for trust_level in trust_df['trust_level'].unique():
            trust_data = trust_df[trust_df['trust_level'] == trust_level]
            ax1.scatter(trust_data['day'], [trust_level] * len(trust_data), 
                       color=trust_colors.get(trust_level, 'gray'), 
                       s=50, alpha=0.7, label=trust_level)
        
        ax1.set_xlabel('Day', fontsize=12)
        ax1.set_ylabel('Trust Level', fontsize=12)
        ax1.set_title('Manager Trust Level Evolution (Categorical)', fontsize=14, fontweight='bold')
        
        # Fix x-axis to show integer days
        days = sorted(trust_df['day'].unique())
        ax1.set_xticks(days)
        ax1.set_xticklabels([int(day) for day in days])
        
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Trust level (numeric) and emotional state
        ax2_twin = ax2.twinx()
        
        line1 = ax2.plot(trust_df['day'], trust_df['trust_numeric'], 
                        'o-', color='blue', linewidth=2, markersize=6, 
                        label='Trust Level (Numeric)')
        line2 = ax2_twin.plot(trust_df['day'], trust_df['emotional_state'], 
                             's-', color='red', linewidth=2, markersize=6, 
                             label='Emotional State')
        
        ax2.set_xlabel('Day', fontsize=12)
        ax2.set_ylabel('Trust Level (Numeric)', color='blue', fontsize=12)
        ax2_twin.set_ylabel('Emotional State', color='red', fontsize=12)
        ax2.set_title('Manager Trust & Emotional State Evolution', fontsize=14, fontweight='bold')
        
        # Fix x-axis to show integer days
        ax2.set_xticks(days)
        ax2.set_xticklabels([int(day) for day in days])
        
        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax2.legend(lines, labels, loc='upper left')
        
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='y', labelcolor='blue')
        ax2_twin.tick_params(axis='y', labelcolor='red')
        
        # Save plot
        save_file = self.save_path / "trust_evolution.png"
        plt.tight_layout()
        plt.savefig(save_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Trust evolution plot saved: {save_file}")
        return str(save_file)
    
    def plot_variant_severity_combined(self, variant_df: pd.DataFrame) -> str:
        """
        Create combined plot with variant markers and severity trajectory
        
        Args:
            variant_df: DataFrame with variant and severity data
            
        Returns:
            Path to saved plot
        """
        if variant_df.empty:
            print("⚠️ No variant/severity data to plot")
            return ""
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Plot severity trajectory as line
        ax.plot(variant_df['day'], variant_df['severity'], 
               'k-', linewidth=2, alpha=0.7, label='Severity Trajectory')
        
        # Add variant markers
        deceptive_days = variant_df[variant_df['deceptive_variant'] == True]
        positive_days = variant_df[variant_df['positive_variant'] == True]
        normal_days = variant_df[(variant_df['deceptive_variant'] == False) & 
                                (variant_df['positive_variant'] == False)]
        checkpoint_days = variant_df[variant_df['is_checkpoint'] == True]
        
        # Plot variant markers
        if not deceptive_days.empty:
            ax.scatter(deceptive_days['day'], deceptive_days['severity'], 
                      color=self.color_palette['deceptive'], s=100, 
                      marker='v', alpha=0.8, label='Deceptive Variant', zorder=5)
        
        if not positive_days.empty:
            ax.scatter(positive_days['day'], positive_days['severity'], 
                      color=self.color_palette['positive'], s=100, 
                      marker='^', alpha=0.8, label='Positive Variant', zorder=5)
        
        if not normal_days.empty:
            ax.scatter(normal_days['day'], normal_days['severity'], 
                      color=self.color_palette['normal'], s=100, 
                      marker='o', alpha=0.8, label='Normal Variant', zorder=5)
        
        if not checkpoint_days.empty:
            ax.scatter(checkpoint_days['day'], checkpoint_days['severity'], 
                      color='gold', s=150, marker='*', 
                      edgecolor='black', linewidth=1, 
                      alpha=0.9, label='Checkpoint', zorder=6)
        
        # Styling
        ax.set_xlabel('Day', fontsize=12)
        ax.set_ylabel('Severity Score', fontsize=12)
        ax.set_title('Deception Severity Trajectory with Variant Usage', fontsize=16, fontweight='bold')
        
        # Fix x-axis to show integer days
        days = sorted(variant_df['day'].unique())
        ax.set_xticks(days)
        ax.set_xticklabels([int(day) for day in days])
        
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Add pressure level annotations
        for idx, row in variant_df.iterrows():
            if row['pressure_level'] != 'NONE':
                ax.annotate(row['pressure_level'], 
                           (row['day'], row['severity']), 
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, alpha=0.7)
        
        # Save plot
        save_file = self.save_path / "variant_severity_combined.png"
        plt.tight_layout()
        plt.savefig(save_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Variant-severity combined plot saved: {save_file}")
        return str(save_file)
    
    def create_summary_stats_plot(self, stats: Dict[str, Any]) -> str:
        """
        Create summary statistics visualization
        
        Args:
            stats: Dictionary with comprehensive statistics
            
        Returns:
            Path to saved plot
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Variant usage pie chart
        variant_data = {
            'Deceptive': stats.get('deceptive_variants_used', 0),
            'Positive': stats.get('positive_variants_used', 0),
            'Normal': stats.get('normal_variants_used', 0)
        }
        
        # Calculate percentages that sum to 100%
        variant_sizes = list(variant_data.values())
        variant_total = sum(variant_sizes)
        if variant_total > 0:
            variant_percentages = []
            for size in variant_sizes:
                variant_percentages.append(size / variant_total * 100)
            
            # Round and adjust to ensure sum is 100%
            rounded_variant_percentages = [round(p, 1) for p in variant_percentages]
            difference = 100.0 - sum(rounded_variant_percentages)
            
            if difference != 0:
                max_idx = rounded_variant_percentages.index(max(rounded_variant_percentages))
                rounded_variant_percentages[max_idx] += difference
            
            # Create pie chart without autopct
            wedges, texts = ax1.pie(variant_sizes, labels=variant_data.keys(), startangle=90)
            
            # Manually add percentage labels
            for i, (wedge, percentage) in enumerate(zip(wedges, rounded_variant_percentages)):
                angle = (wedge.theta2 + wedge.theta1) / 2
                x = wedge.r * 0.7 * np.cos(np.radians(angle))
                y = wedge.r * 0.7 * np.sin(np.radians(angle))
                ax1.text(x, y, f'{percentage:.1f}%', 
                        horizontalalignment='center', 
                        verticalalignment='center',
                        fontsize=10, fontweight='bold')
        else:
            ax1.pie([1], labels=['No Data'])
        
        ax1.set_title('Variant Usage Distribution', fontweight='bold')
        
        # 2. Detection rates comparison
        detection_data = {
            'Judge Detection Rate': stats.get('detection_rate_judge', 0) * 100,
            'Manager Detection Rate': stats.get('detection_rate_manager', 0) * 100
        }
        bars = ax2.bar(detection_data.keys(), detection_data.values(), 
                      color=[self.color_palette['detected'], self.color_palette['missed']])
        ax2.set_ylabel('Detection Rate (%)')
        ax2.set_title('Detection Rate Comparison', fontweight='bold')
        ax2.set_ylim(0, 100)
        
        # Add value labels on bars
        for bar, value in zip(bars, detection_data.values()):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{value:.1f}%', ha='center', va='bottom')
        
        # 3. Task statistics
        task_stats = {
            'Total Tasks': stats.get('total_tasks', 0),
            'Checkpoints': stats.get('checkpoints', 0),
            'Audits Triggered': stats.get('audits_triggered', 0)
        }
        ax3.bar(task_stats.keys(), task_stats.values(), color='skyblue')
        ax3.set_ylabel('Count')
        ax3.set_title('Task Statistics', fontweight='bold')
        
        # 4. Final trust level
        ax4.text(0.5, 0.5, f"Final Trust Level:\n{stats.get('final_trust_level', 'UNKNOWN')}", 
                ha='center', va='center', fontsize=20, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
        ax4.set_xlim(0, 1)
        ax4.set_ylim(0, 1)
        ax4.axis('off')
        ax4.set_title('Final Outcome', fontweight='bold')
        
        # Save plot
        save_file = self.save_path / "summary_statistics.png"
        plt.tight_layout()
        plt.savefig(save_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Summary statistics plot saved: {save_file}")
        return str(save_file) 