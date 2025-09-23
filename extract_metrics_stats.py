#!/usr/bin/env python3
"""
Extract metrics from all experiment results and calculate mean/std for each model
"""

import json
import os
import math
from pathlib import Path

def extract_manager_metrics(result_json_path):
    """Extract final manager state metrics from result.json"""
    with open(result_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find final state from last round
    final_round = None
    total_rounds = 0
    
    for task in data['experiment']['tasks']:
        for round_data in task['rounds']:
            final_round = round_data
            total_rounds += 1
    
    if final_round and 'manager_evaluation' in final_round:
        final_state = final_round['manager_evaluation']['state_updates']['new_state']
        
        # Calculate normalized work satisfaction
        all_work_sats = []
        for task in data['experiment']['tasks']:
            for round_data in task['rounds']:
                if 'manager_evaluation' in round_data:
                    work_sat = round_data['manager_evaluation']['state_updates']['new_state']['work_satisfaction']
                    all_work_sats.append(work_sat)
        
        average_work_satisfaction = sum(all_work_sats) / len(all_work_sats) if all_work_sats else 0
        
        return {
            'final_trust_level': final_state['trust_level'],
            'final_relational_comfort': final_state['relational_comfort'], 
            'average_work_satisfaction': average_work_satisfaction,
            'total_rounds': total_rounds
        }
    
    return None

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
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        llm_model = config.get('llm_api_config', {}).get('llm', 'unknown')
        return llm_model
    except:
        return 'unknown'

def main():
    base_path = Path("/Users/superposition/Desktop/Deception_local/DeceptioN/results/New Folder With Items")
    
    experiments = [
        "startup_consulting_20250831_010301",
        "startup_consulting_20250831_010311", 
        "startup_consulting_20250831_010313",
        "startup_consulting_20250831_012502",
        "startup_consulting_20250831_012506",
        "startup_consulting_20250831_012509"
    ]
    
    results = []
    
    for i, exp_name in enumerate(experiments, 1):
        exp_path = base_path / exp_name
        result_path = exp_path / "result.json"
        config_path = exp_path / "our_config.yaml"
        
        # Find detector file
        detector_files = list(exp_path.glob("detector_*.json"))
        detector_path = detector_files[0] if detector_files else None
        
        print(f"Processing {exp_name}...")
        
        # Extract manager metrics
        manager_metrics = extract_manager_metrics(result_path) if result_path.exists() else None
        
        # Extract detector metrics  
        detector_metrics = extract_detector_metrics(detector_path) if detector_path else None
        
        # Get model info
        model_info = get_model_info(config_path) if config_path.exists() else 'unknown'
        
        result = {
            'group': i,
            'experiment': exp_name,
            'model': model_info,
            'manager_metrics': manager_metrics,
            'detector_metrics': detector_metrics
        }
        
        results.append(result)
    
    # Group by model
    model_data = {}
    for result in results:
        model = result['model']
        if model not in model_data:
            model_data[model] = []
        model_data[model].append(result)
    
    # Calculate statistics
    print("\n" + "="*140)
    print("EXPERIMENT METRICS STATISTICS (MEAN ± STD)")
    print("="*140)
    
    # Headers
    headers = [
        "Model", "N", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Deception Occur", "Deception Rate", "Avg Sev All", "Avg Sev Decp"
    ]
    
    print(f"{'|'.join(f'{h:>14}' for h in headers)}")
    print("-" * 140)
    
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
            if result['manager_metrics']:
                m = result['manager_metrics']
                trust_vals.append(m['final_trust_level'])
                comfort_vals.append(m['final_relational_comfort'])
                work_sat_vals.append(m['average_work_satisfaction'])
                rounds_vals.append(m['total_rounds'])
            
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
            return f"{mean_val:.2f}±{std_val:.2f}"
        
        trust_str = format_stat(trust_mean, trust_std)
        comfort_str = format_stat(comfort_mean, comfort_std)
        work_sat_str = format_stat(work_sat_mean, work_sat_std)
        rounds_str = format_stat(rounds_mean, rounds_std)
        decp_occur_str = format_stat(decp_occur_mean, decp_occur_std)
        decp_rate_str = format_stat(decp_rate_mean, decp_rate_std)
        sev_all_str = format_stat(sev_all_mean, sev_all_std)
        sev_decp_str = format_stat(sev_decp_mean, sev_decp_std)
        
        row_data = [
            model[:12], str(n), trust_str, comfort_str, work_sat_str, 
            rounds_str, decp_occur_str, decp_rate_str, sev_all_str, sev_decp_str
        ]
        print(f"{'|'.join(f'{d:>14}' for d in row_data)}")
    
    print("="*140)
    print("Notes:")
    print("- Format: mean±std")
    print("- N: number of experiments per model")
    print("- std calculated with ddof=1 (sample standard deviation)")

if __name__ == "__main__":
    main()
