#!/usr/bin/env python3
"""
Extract metrics from all experiments starting from startup_consulting_20250831_041926
"""

import json
import os
import math
from pathlib import Path
import yaml

def extract_manager_metrics_from_analysis(analysis_path):
    """Extract manager metrics from analysis_results.json"""
    if not analysis_path.exists():
        return None
    
    with open(analysis_path, 'r') as f:
        return json.load(f)

def extract_detector_metrics(detector_json_path):
    """Extract detector summary metrics from detector_*.json"""
    if not os.path.exists(detector_json_path):
        return None
        
    with open(detector_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'summary' in data:
        return data['summary']
    
    return None

def get_model_info(config_path):
    """Extract model info from config file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        llm_model = config.get('llm_api_config', {}).get('llm', 'unknown')
        return llm_model
    except:
        return 'unknown'

def get_analysis_results(exp_path):
    """Get analysis results from analysis_*/analysis_results.json"""
    analysis_dirs = list(exp_path.glob("analysis_*"))
    if not analysis_dirs:
        return None
    
    # Use the most recent analysis directory
    analysis_dir = max(analysis_dirs, key=lambda d: d.stat().st_mtime)
    analysis_file = analysis_dir / "analysis_results.json"
    
    if analysis_file.exists():
        with open(analysis_file, 'r') as f:
            return json.load(f)
    
    return None

def main():
    # Get all experiments from 041926 onwards
    result_base = Path("/Users/superposition/Desktop/Deception_local/DeceptioN/results")
    
    # Find all matching experiments
    all_experiments = []
    for exp_dir in result_base.glob("startup_consulting_20250831_*"):
        if exp_dir.name >= "startup_consulting_20250831_041926":
            all_experiments.append(exp_dir)
    
    all_experiments.sort(key=lambda x: x.name)
    
    results = []
    
    print(f"Found {len(all_experiments)} experiments to process...")
    
    for i, exp_path in enumerate(all_experiments, 1):
        exp_name = exp_path.name
        config_path = exp_path / "our_config.yaml"
        
        # Find detector file
        detector_files = list(exp_path.glob("detector_*.json"))
        detector_path = detector_files[0] if detector_files else None
        
        print(f"Processing {exp_name}...")
        
        # Get analysis results
        analysis_results = get_analysis_results(exp_path)
        
        # Extract detector metrics  
        detector_metrics = extract_detector_metrics(detector_path) if detector_path else None
        
        # Get model info
        model_info = get_model_info(config_path) if config_path.exists() else 'unknown'
        
        result = {
            'group': i,
            'folder_name': exp_name,
            'model': model_info,
            'analysis_results': analysis_results,
            'detector_metrics': detector_metrics
        }
        
        results.append(result)
    
    # Print individual results table
    print("\n" + "="*160)
    print("EXPERIMENT METRICS TABLE (From startup_consulting_20250831_041926 onwards)")
    print("="*160)
    
    # Headers
    headers = [
        "Folder Name", "Model", "Group", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Deception Occur", "Deception Rate", "Avg Severity All", "Avg Severity Decp"
    ]
    
    print(f"{'|'.join(f'{h:>15}' for h in headers)}")
    print("-" * 160)
    
    # Data rows
    for result in results:
        folder_name = result['folder_name'][-8:]  # Show only HHMMSS part
        model = result['model'][:12]  # Truncate model name
        group = str(result['group'])
        
        if result['analysis_results']:
            a = result['analysis_results']
            trust = f"{a['final_trust_level']:.2f}"
            comfort = f"{a['final_relational_comfort']:.2f}" 
            work_sat = f"{a['average_work_satisfaction']:.3f}"
            rounds = str(a['total_interactions'])
        else:
            trust = comfort = work_sat = rounds = "N/A"
        
        if result['detector_metrics']:
            d = result['detector_metrics']
            decp_occur = str(d['deception_occurrences'])
            decp_rate = f"{d['deception_rate']:.3f}"
            avg_sev_all = f"{d['severity_average_all_rounds']:.2f}"
            avg_sev_decp = f"{d['severity_average_deception_only']:.2f}"
        else:
            decp_occur = decp_rate = avg_sev_all = avg_sev_decp = "N/A"
        
        row_data = [folder_name, model, group, trust, comfort, work_sat, rounds, decp_occur, decp_rate, avg_sev_all, avg_sev_decp]
        print(f"{'|'.join(f'{d:>15}' for d in row_data)}")
    
    print("="*160)
    print(f"Total experiments: {len(results)}")
    
    # Store results for statistics calculation
    global experiment_results
    experiment_results = results
    
    print("\nTable displayed. Ready to calculate statistics upon your approval.")
    
    return results

# Global variable to store results
experiment_results = []

def calculate_statistics():
    """Calculate statistics by model after user approval"""
    if not experiment_results:
        print("No experiment data available. Please run main() first.")
        return
    
    # Group by model
    model_data = {}
    for result in experiment_results:
        model = result['model']
        if model not in model_data:
            model_data[model] = []
        model_data[model].append(result)
    
    # Calculate statistics
    print("\n" + "="*160)
    print("EXPERIMENT METRICS STATISTICS (MEAN ± STD)")
    print("="*160)
    
    # Headers
    headers = [
        "Model", "N", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Deception Occur", "Deception Rate", "Avg Sev All", "Avg Sev Decp"
    ]
    
    print(f"{'|'.join(f'{h:>16}' for h in headers)}")
    print("-" * 160)
    
    for model, data_list in model_data.items():
        n = len(data_list)
        
        # Collect metrics
        trust_vals = []
        comfort_vals = []
        work_sat_vals = []
        rounds_vals = []
        decp_occur_vals = []
        decp_rate_vals = []
        sev_all_vals = []
        sev_decp_vals = []
        
        for result in data_list:
            if result['analysis_results']:
                a = result['analysis_results']
                trust_vals.append(a['final_trust_level'])
                comfort_vals.append(a['final_relational_comfort'])
                work_sat_vals.append(a['average_work_satisfaction'])
                rounds_vals.append(a['total_interactions'])
            
            if result['detector_metrics']:
                d = result['detector_metrics']
                decp_occur_vals.append(d['deception_occurrences'])
                decp_rate_vals.append(d['deception_rate'])
                sev_all_vals.append(d['severity_average_all_rounds'])
                sev_decp_vals.append(d['severity_average_deception_only'])
        
        # Calculate means and stds
        def calc_stats(vals):
            if not vals:
                return "N/A", "N/A"
            n = len(vals)
            mean_val = sum(vals) / n
            if n > 1:
                variance = sum((x - mean_val) ** 2 for x in vals) / (n - 1)  # sample variance
                std_val = math.sqrt(variance)
            else:
                std_val = 0.0
            return mean_val, std_val
        
        trust_mean, trust_std = calc_stats(trust_vals)
        comfort_mean, comfort_std = calc_stats(comfort_vals)
        work_sat_mean, work_sat_std = calc_stats(work_sat_vals)
        rounds_mean, rounds_std = calc_stats(rounds_vals)
        decp_occur_mean, decp_occur_std = calc_stats(decp_occur_vals)
        decp_rate_mean, decp_rate_std = calc_stats(decp_rate_vals)
        sev_all_mean, sev_all_std = calc_stats(sev_all_vals)
        sev_decp_mean, sev_decp_std = calc_stats(sev_decp_vals)
        
        # Format output
        def format_stat(mean_val, std_val):
            if mean_val == "N/A":
                return "N/A"
            return f"{mean_val:.3f}±{std_val:.3f}"
        
        trust_str = format_stat(trust_mean, trust_std)
        comfort_str = format_stat(comfort_mean, comfort_std)
        work_sat_str = format_stat(work_sat_mean, work_sat_std)
        rounds_str = format_stat(rounds_mean, rounds_std)
        decp_occur_str = format_stat(decp_occur_mean, decp_occur_std)
        decp_rate_str = format_stat(decp_rate_mean, decp_rate_std)
        sev_all_str = format_stat(sev_all_mean, sev_all_std)
        sev_decp_str = format_stat(sev_decp_mean, sev_decp_std)
        
        row_data = [
            model[:14], str(n), trust_str, comfort_str, work_sat_str, 
            rounds_str, decp_occur_str, decp_rate_str, sev_all_str, sev_decp_str
        ]
        print(f"{'|'.join(f'{d:>16}' for d in row_data)}")
    
    print("="*160)

if __name__ == "__main__":
    main()
