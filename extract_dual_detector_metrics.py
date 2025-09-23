#!/usr/bin/env python3
"""
Extract metrics from all experiment results with dual detector analysis
Based on extract_metrics.py and extract_metrics_stats.py but enhanced for detector round comparison
"""

import json
import os
import math
from pathlib import Path

def extract_manager_metrics(result_json_path):
    """Extract manager metrics ONLY from analysis_results.json - NO FALLBACK"""
    
    # Derive experiment path from result.json path
    exp_path = Path(result_json_path).parent
    
    # Find analysis directory - MUST exist
    analysis_dirs = list(exp_path.glob("analysis_*/"))
    
    if not analysis_dirs:
        raise FileNotFoundError(f"No analysis directory found in {exp_path}. Run analyzer.py first!")
    
    # Use the most recent analysis directory
    latest_analysis_dir = max(analysis_dirs, key=lambda d: d.name)
    analysis_results_path = latest_analysis_dir / "analysis_results.json"
    
    if not analysis_results_path.exists():
        raise FileNotFoundError(f"analysis_results.json not found in {latest_analysis_dir}. Run analyzer.py first!")
    
    # Read from analysis_results.json - ALL values MUST be present
    with open(analysis_results_path, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    # Direct access - NO .get() with defaults!
    return {
        'final_trust_level': analysis_data['final_trust_level'],
        'final_relational_comfort': analysis_data['final_relational_comfort'],
        'average_work_satisfaction': analysis_data['average_work_satisfaction'],
        'total_rounds': analysis_data['total_interactions']  # Note: total_interactions is the total rounds
    }

def extract_detector_metrics(detector_json_path):
    """Extract detector summary metrics from detector_*.json - NO FALLBACK"""
    if not os.path.exists(detector_json_path):
        raise FileNotFoundError(f"Detector file not found: {detector_json_path}")
        
    with open(detector_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Direct access - 'summary' MUST exist
    return data['summary']

def extract_dual_detector_metrics(exp_path):
    """Extract both detector round 1 and 2 metrics - REQUIRES exactly 2 detector files"""
    detector_files = sorted(exp_path.glob("detector_*.json"))
    
    if len(detector_files) < 2:
        raise FileNotFoundError(f"Expected 2 detector files in {exp_path}, found {len(detector_files)}. Run dual detector analysis first!")
    
    # Extract both rounds - NO fallback
    round1_data = extract_detector_metrics(detector_files[0])
    round2_data = extract_detector_metrics(detector_files[1])
        
    return round1_data, round2_data

def get_model_info(config_path):
    """Extract model info from config file - NO FALLBACK"""
    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Direct access - NO .get() with defaults!
    llm_model = config['llm_api_config']['llm']
    return llm_model

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract dual detector metrics from experiments")
    parser.add_argument("--extract_dir", required=True, 
                       help="Directory containing experiment folders to process")
    
    args = parser.parse_args()
    
    # Process all experiments in the specified folder
    base_path = Path(args.extract_dir)
    
    if not base_path.exists():
        raise FileNotFoundError(f"Directory not found: {base_path}")
    
    # Find all experiment directories (should contain result.json)
    experiment_dirs = []
    for item in base_path.iterdir():
        if item.is_dir() and (item / "result.json").exists():
            experiment_dirs.append(item)
    
    if not experiment_dirs:
        raise FileNotFoundError(f"No experiment directories with result.json found in {base_path}")
    
    # Sort by directory name for consistent order
    experiment_dirs.sort(key=lambda x: x.name)
    
    print(f"Found {len(experiment_dirs)} experiments in {base_path}")
    print(f"Experiments: {[d.name for d in experiment_dirs]}")
    
    results = []
    
    for exp_path in experiment_dirs:
        exp_name = exp_path.name
        result_path = exp_path / "result.json"
        config_path = exp_path / "our_config.yaml"
        
        print(f"Processing {exp_name}...")
        
        try:
            # Extract manager metrics - NO FALLBACK, result.json MUST exist
            if not result_path.exists():
                raise FileNotFoundError(f"result.json not found in {exp_path}")
            manager_metrics = extract_manager_metrics(result_path)
            
            # Extract dual detector metrics  
            detector_r1, detector_r2 = extract_dual_detector_metrics(exp_path)
            
            # Get model info - NO FALLBACK, config MUST exist
            if not config_path.exists():
                raise FileNotFoundError(f"our_config.yaml not found in {exp_path}")
            model_info = get_model_info(config_path)
            
            result = {
                'experiment': exp_name,
                'model': model_info,
                'manager_metrics': manager_metrics,
                'detector_r1': detector_r1,
                'detector_r2': detector_r2
            }
            
            results.append(result)
            
        except Exception as e:
            print(f"ERROR processing {exp_name}: {e}")
            print(f"Skipping {exp_name} due to error...")
            continue
    
    if not results:
        raise RuntimeError("No experiments were successfully processed!")
    
    print(f"\nSuccessfully processed {len(results)} experiments")
    
    # Generate markdown report
    generate_markdown_report(results)

def generate_markdown_report(results):
    """Generate comprehensive markdown report with all tables"""
    from datetime import datetime
    
    output_file = "dual_detector_metrics_report.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("# Report\n\n")
        # f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        # f.write("**Dataset:** 24 experiments from startup_consulting_20250831_041926 onwards\n\n")
        # f.write("**Models analyzed:** o3, deepseek_r1_0528, deepseek_chat_v3_1, gpt5_azure, gpt4o1120azurenew, deepseek_chat_v3_0324, o4_mini, grok_4\n\n")
        
        # Main data table
        f.write("## Main Data Table\n\n")
        
        # Headers
        headers = [
            "Experiment", "Model", "Final Trust", "Final Comfort", "Norm Work Sat", 
            "Total Rounds", "Decp Occur R1", "Decp Rate R1", "Avg Sev All R1", "Avg Sev Decp R1",
            "Decp Occur R2", "Decp Rate R2", "Avg Sev All R2", "Avg Sev Decp R2"
        ]
        
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(["-" * len(h) for h in headers]) + " |\n")
        
        # Data rows
        for result in results:
            exp_short = result['experiment'].split('_')[-1]  # Show only timestamp
            model = result['model']
            
            if result['manager_metrics']:
                m = result['manager_metrics']
                trust = f"{m['final_trust_level']:.2f}"
                comfort = f"{m['final_relational_comfort']:.2f}" 
                work_sat = f"{m['average_work_satisfaction']:.3f}"
                rounds = str(m['total_rounds'])
            else:
                trust = comfort = work_sat = rounds = "N/A"
            
            # Round 1 detector
            if result['detector_r1']:
                d1 = result['detector_r1']
                decp_occur_r1 = str(d1['deception_occurrences'])
                decp_rate_r1 = f"{d1['deception_rate']:.3f}"
                avg_sev_all_r1 = f"{d1['severity_average_all_rounds']:.2f}"
                avg_sev_decp_r1 = f"{d1['severity_average_deception_only']:.2f}"
            else:
                decp_occur_r1 = decp_rate_r1 = avg_sev_all_r1 = avg_sev_decp_r1 = "N/A"
            
            # Round 2 detector
            if result['detector_r2']:
                d2 = result['detector_r2']
                decp_occur_r2 = str(d2['deception_occurrences'])
                decp_rate_r2 = f"{d2['deception_rate']:.3f}"
                avg_sev_all_r2 = f"{d2['severity_average_all_rounds']:.2f}"
                avg_sev_decp_r2 = f"{d2['severity_average_deception_only']:.2f}"
            else:
                decp_occur_r2 = decp_rate_r2 = avg_sev_all_r2 = avg_sev_decp_r2 = "N/A"
            
            row_data = [
                exp_short, model, trust, comfort, work_sat, rounds, 
                decp_occur_r1, decp_rate_r1, avg_sev_all_r1, avg_sev_decp_r1,
                decp_occur_r2, decp_rate_r2, avg_sev_all_r2, avg_sev_decp_r2
            ]
            f.write("| " + " | ".join(row_data) + " |\n")
        
        # Generate statistics tables
        generate_markdown_statistics_tables(results, f)
    
    print(f"\nMarkdown report saved to: {output_file}")

def generate_markdown_statistics_tables(results, f):
    """Generate markdown statistics tables for detector round 1 and 2"""
    
    # Group by model
    model_data = {}
    for result in results:
        model = result['model']
        if model not in model_data:
            model_data[model] = []
        model_data[model].append(result)
    
    # Statistics calculation helper
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
    
    def format_stat(mean_val, std_val):
        if mean_val == "N/A":
            return "N/A"
        return f"{mean_val:.2f}±{std_val:.2f}"
    
    # Generate Round 1 Statistics
    f.write("\n\n## Detector Round 1 Statistics (Mean ± STD)\n\n")
    
    headers = [
        "Model", "N", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Decp Occur R1", "Decp Rate R1", "Avg Sev All R1", "Avg Sev Decp R1"
    ]
    
    f.write("| " + " | ".join(headers) + " |\n")
    f.write("| " + " | ".join(["-" * len(h) for h in headers]) + " |\n")
    
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
            
            if result['detector_r1']:  # Round 1 detector
                d = result['detector_r1']
                decp_occur_vals.append(d['deception_occurrences'])
                decp_rate_vals.append(d['deception_rate'])
                sev_all_vals.append(d['severity_average_all_rounds'])
                sev_decp_vals.append(d['severity_average_deception_only'])
        
        # Calculate statistics
        trust_mean, trust_std = calc_stats(trust_vals)
        comfort_mean, comfort_std = calc_stats(comfort_vals)
        work_sat_mean, work_sat_std = calc_stats(work_sat_vals)
        rounds_mean, rounds_std = calc_stats(rounds_vals)
        decp_occur_mean, decp_occur_std = calc_stats(decp_occur_vals)
        decp_rate_mean, decp_rate_std = calc_stats(decp_rate_vals)
        sev_all_mean, sev_all_std = calc_stats(sev_all_vals)
        sev_decp_mean, sev_decp_std = calc_stats(sev_decp_vals)
        
        # Format output
        trust_str = format_stat(trust_mean, trust_std)
        comfort_str = format_stat(comfort_mean, comfort_std)
        work_sat_str = format_stat(work_sat_mean, work_sat_std)
        rounds_str = format_stat(rounds_mean, rounds_std)
        decp_occur_str = format_stat(decp_occur_mean, decp_occur_std)
        decp_rate_str = format_stat(decp_rate_mean, decp_rate_std)
        sev_all_str = format_stat(sev_all_mean, sev_all_std)
        sev_decp_str = format_stat(sev_decp_mean, sev_decp_std)
        
        row_data = [
            model, str(n), trust_str, comfort_str, work_sat_str, 
            rounds_str, decp_occur_str, decp_rate_str, sev_all_str, sev_decp_str
        ]
        f.write("| " + " | ".join(row_data) + " |\n")
    
    # Generate Round 2 Statistics
    f.write("\n\n## Detector Run 2 Statistics (Mean ± STD)\n\n")
    
    headers = [
        "Model", "N", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Decp Occur R2", "Decp Rate R2", "Avg Sev All R2", "Avg Sev Decp R2"
    ]
    
    f.write("| " + " | ".join(headers) + " |\n")
    f.write("| " + " | ".join(["-" * len(h) for h in headers]) + " |\n")
    
    for model, data_list in model_data.items():
        n = len(data_list)
        
        # Collect metrics (same manager metrics, but Round 2 detector)
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
                work_sat_vals.append(m['normalized_work_satisfaction'])
                rounds_vals.append(m['total_rounds'])
            
            if result['detector_r2']:  # Round 2 detector
                d = result['detector_r2']
                decp_occur_vals.append(d['deception_occurrences'])
                decp_rate_vals.append(d['deception_rate'])
                sev_all_vals.append(d['severity_average_all_rounds'])
                sev_decp_vals.append(d['severity_average_deception_only'])
        
        # Calculate statistics
        trust_mean, trust_std = calc_stats(trust_vals)
        comfort_mean, comfort_std = calc_stats(comfort_vals)
        work_sat_mean, work_sat_std = calc_stats(work_sat_vals)
        rounds_mean, rounds_std = calc_stats(rounds_vals)
        decp_occur_mean, decp_occur_std = calc_stats(decp_occur_vals)
        decp_rate_mean, decp_rate_std = calc_stats(decp_rate_vals)
        sev_all_mean, sev_all_std = calc_stats(sev_all_vals)
        sev_decp_mean, sev_decp_std = calc_stats(sev_decp_vals)
        
        # Format output
        trust_str = format_stat(trust_mean, trust_std)
        comfort_str = format_stat(comfort_mean, comfort_std)
        work_sat_str = format_stat(work_sat_mean, work_sat_std)
        rounds_str = format_stat(rounds_mean, rounds_std)
        decp_occur_str = format_stat(decp_occur_mean, decp_occur_std)
        decp_rate_str = format_stat(decp_rate_mean, decp_rate_std)
        sev_all_str = format_stat(sev_all_mean, sev_all_std)
        sev_decp_str = format_stat(sev_decp_mean, sev_decp_std)
        
        row_data = [
            model, str(n), trust_str, comfort_str, work_sat_str, 
            rounds_str, decp_occur_str, decp_rate_str, sev_all_str, sev_decp_str
        ]
        f.write("| " + " | ".join(row_data) + " |\n")
    
    # Add notes
    f.write("\n\n## Notes\n\n")
    f.write("- **Format:** mean±std\n")
    f.write("- **N:** number of experiments per model\n") 
    f.write("- **std:** calculated with ddof=1 (sample standard deviation)\n")
    f.write("- **Run 1 and Run 2:** refer to different detector analysis runs\n")
    f.write("- **Manager metrics:** Final Trust, Final Comfort, Norm Work Sat, Total Rounds are identical across both runs\n")
    f.write("- **Detector metrics:** Decp Occur, Decp Rate, Avg Sev All, Avg Sev Decp vary between runs\n")

def generate_statistics_tables(results):
    """Generate separate statistics tables for detector round 1 and 2"""
    
    # Group by model
    model_data = {}
    for result in results:
        model = result['model']
        if model not in model_data:
            model_data[model] = []
        model_data[model].append(result)
    
    # Statistics calculation helper
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
    
    def format_stat(mean_val, std_val):
        if mean_val == "N/A":
            return "N/A"
        return f"{mean_val:.2f}±{std_val:.2f}"
    
    # Generate Round 1 Statistics
    print("\n" + "="*160)
    print("DETECTOR RUN 1 STATISTICS (MEAN ± STD)")
    print("="*160)
    
    headers = [
        "Model", "N", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Decp Occur R1", "Decp Rate R1", "Avg Sev All R1", "Avg Sev Decp R1"
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
            if result['manager_metrics']:
                m = result['manager_metrics']
                trust_vals.append(m['final_trust_level'])
                comfort_vals.append(m['final_relational_comfort'])
                work_sat_vals.append(m['normalized_work_satisfaction'])
                rounds_vals.append(m['total_rounds'])
            
            if result['detector_r1']:  # Round 1 detector
                d = result['detector_r1']
                decp_occur_vals.append(d['deception_occurrences'])
                decp_rate_vals.append(d['deception_rate'])
                sev_all_vals.append(d['severity_average_all_rounds'])
                sev_decp_vals.append(d['severity_average_deception_only'])
        
        # Calculate statistics
        trust_mean, trust_std = calc_stats(trust_vals)
        comfort_mean, comfort_std = calc_stats(comfort_vals)
        work_sat_mean, work_sat_std = calc_stats(work_sat_vals)
        rounds_mean, rounds_std = calc_stats(rounds_vals)
        decp_occur_mean, decp_occur_std = calc_stats(decp_occur_vals)
        decp_rate_mean, decp_rate_std = calc_stats(decp_rate_vals)
        sev_all_mean, sev_all_std = calc_stats(sev_all_vals)
        sev_decp_mean, sev_decp_std = calc_stats(sev_decp_vals)
        
        # Format output
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
    
    # Generate Round 2 Statistics
    print("\n" + "="*160)
    print("DETECTOR ROUND 2 STATISTICS (MEAN ± STD)")
    print("="*160)
    
    headers = [
        "Model", "N", "Final Trust", "Final Comfort", "Norm Work Sat", 
        "Total Rounds", "Decp Occur R2", "Decp Rate R2", "Avg Sev All R2", "Avg Sev Decp R2"
    ]
    
    print(f"{'|'.join(f'{h:>16}' for h in headers)}")
    print("-" * 160)
    
    for model, data_list in model_data.items():
        n = len(data_list)
        
        # Collect metrics (same manager metrics, but Round 2 detector)
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
                work_sat_vals.append(m['normalized_work_satisfaction'])
                rounds_vals.append(m['total_rounds'])
            
            if result['detector_r2']:  # Round 2 detector
                d = result['detector_r2']
                decp_occur_vals.append(d['deception_occurrences'])
                decp_rate_vals.append(d['deception_rate'])
                sev_all_vals.append(d['severity_average_all_rounds'])
                sev_decp_vals.append(d['severity_average_deception_only'])
        
        # Calculate statistics
        trust_mean, trust_std = calc_stats(trust_vals)
        comfort_mean, comfort_std = calc_stats(comfort_vals)
        work_sat_mean, work_sat_std = calc_stats(work_sat_vals)
        rounds_mean, rounds_std = calc_stats(rounds_vals)
        decp_occur_mean, decp_occur_std = calc_stats(decp_occur_vals)
        decp_rate_mean, decp_rate_std = calc_stats(decp_rate_vals)
        sev_all_mean, sev_all_std = calc_stats(sev_all_vals)
        sev_decp_mean, sev_decp_std = calc_stats(sev_decp_vals)
        
        # Format output
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
    print("Notes:")
    print("- Format: mean±std")
    print("- N: number of experiments per model")
    print("- std calculated with ddof=1 (sample standard deviation)")
    print("- Round 1 and Round 2 refer to different detector analysis runs")

if __name__ == "__main__":
    main()
