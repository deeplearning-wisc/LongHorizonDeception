#!/usr/bin/env python3
"""
Extract metrics from all experiment results for comparison table
"""

import json
import os
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
        
        # Calculate normalized work satisfaction (简化计算)
        all_work_sats = []
        for task in data['experiment']['tasks']:
            for round_data in task['rounds']:
                if 'manager_evaluation' in round_data:
                    work_sat = round_data['manager_evaluation']['state_updates']['new_state']['work_satisfaction']
                    all_work_sats.append(work_sat)
        
        normalized_work_satisfaction = sum(all_work_sats) / len(all_work_sats) if all_work_sats else 0
        
        return {
            'final_trust_level': final_state['trust_level'],
            'final_relational_comfort': final_state['relational_comfort'], 
            'normalized_work_satisfaction': normalized_work_satisfaction,
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
    
    # Print table
    print("\n" + "="*120)
    print("EXPERIMENT METRICS COMPARISON TABLE")
    print("="*120)
    
    # Headers
    headers = [
        "Model", "Group", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Deception Occur", "Deception Rate", "Avg Severity All", "Avg Severity Decp"
    ]
    
    print(f"{'|'.join(f'{h:>12}' for h in headers)}")
    print("-" * 120)
    
    # Data rows
    for result in results:
        model = result['model']
        group = str(result['group'])
        
        if result['manager_metrics']:
            m = result['manager_metrics']
            trust = f"{m['final_trust_level']:.2f}"
            comfort = f"{m['final_relational_comfort']:.2f}" 
            work_sat = f"{m['normalized_work_satisfaction']:.3f}"
            rounds = str(m['total_rounds'])
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
        
        row_data = [model, group, trust, comfort, work_sat, rounds, decp_occur, decp_rate, avg_sev_all, avg_sev_decp]
        print(f"{'|'.join(f'{d:>12}' for d in row_data)}")
    
    print("="*120)

if __name__ == "__main__":
    main()