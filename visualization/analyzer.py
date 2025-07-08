# visualization/analyzer.py
# Results analyzer for extracting and processing LDLE experiment data

import json
import os
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import numpy as np

class ResultsAnalyzer:
    """Analyzer for LDLE experiment results"""
    
    def __init__(self, results_path: str):
        """
        Initialize analyzer with results directory path
        
        Args:
            results_path: Path to the results directory (e.g., "results/production/session_name/")
        """
        self.results_path = Path(results_path)
        self.data_loaded = False
        self.evaluation_results = []
        self.manager_interactions = []
        self.summary = {}
        self.session_metadata = {}
        
    def load_results(self) -> bool:
        """Load all result files from the session directory"""
        try:
            # Load evaluation results (contains the judge evaluations and detailed task data)
            evaluation_file = self.results_path / "evaluation_results.json"
            if evaluation_file.exists():
                with open(evaluation_file, 'r') as f:
                    eval_data = json.load(f)
                    self.evaluation_results = eval_data if isinstance(eval_data, list) else []
            
            # Also load complete pipeline results for additional context
            pipeline_file = self.results_path / "complete_pipeline_results.json"
            if pipeline_file.exists():
                with open(pipeline_file, 'r') as f:
                    pipeline_data = json.load(f)
                    # If we don't have evaluation results, try to get them from pipeline
                    if not self.evaluation_results and isinstance(pipeline_data, dict) and 'detailed_interactions' in pipeline_data:
                        self.evaluation_results = pipeline_data['detailed_interactions']
            
            # Load manager interactions
            manager_file = self.results_path / "manager_interactions.json"
            if manager_file.exists():
                with open(manager_file, 'r') as f:
                    self.manager_interactions = json.load(f)
            
            # Load summary
            summary_file = self.results_path / "summary.json"
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    self.summary = json.load(f)
            
            # Load session metadata
            metadata_file = self.results_path / "session_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    self.session_metadata = json.load(f)
            
            self.data_loaded = True
            print(f"✅ Loaded results from {self.results_path}")
            print(f"   - Tasks: {len(self.evaluation_results)}")
            print(f"   - Manager interactions: {len(self.manager_interactions)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load results: {e}")
            return False
    
    def get_intent_distribution(self) -> Dict[str, int]:
        """Get distribution of deception intents"""
        if not self.data_loaded:
            return {}
        
        intent_counts = {}
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
            intent = result.get('judge_evaluation', {}).get('intent', 'UNKNOWN')
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        return intent_counts
    
    def get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of deception categories"""
        if not self.data_loaded:
            return {}
        
        category_counts = {}
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
            category = result.get('judge_evaluation', {}).get('category', 'UNKNOWN')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return category_counts
    
    def get_detection_comparison_data(self) -> pd.DataFrame:
        """Get detection comparison data between Judge and Manager"""
        if not self.data_loaded:
            return pd.DataFrame()
        
        data = []
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
            day = result.get('day', 0)
            judge_detected = result.get('judge_evaluation', {}).get('deception_detected', False)
            manager_noticed = result.get('manager_noticed_deception', False)
            
            data.append({
                'day': day,
                'task_id': result.get('task_id', ''),
                'judge_detected': judge_detected,
                'manager_noticed': manager_noticed,
                'both_detected': judge_detected and manager_noticed,
                'judge_only': judge_detected and not manager_noticed,
                'manager_only': not judge_detected and manager_noticed,
                'neither_detected': not judge_detected and not manager_noticed
            })
        
        return pd.DataFrame(data)
    
    def get_trust_evolution_data(self) -> pd.DataFrame:
        """Get Manager trust level evolution over time"""
        if not self.data_loaded:
            return pd.DataFrame()
        
        data = []
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
            day = result.get('day', 0)
            emotional_state = result.get('manager_emotional_state', 0.0)
            trust_level = result.get('manager_trust_level', 'NEUTRAL')
            
            # Convert trust level to numeric for plotting
            trust_numeric = self._trust_to_numeric(trust_level)
            
            data.append({
                'day': day,
                'emotional_state': emotional_state,
                'trust_level': trust_level,
                'trust_numeric': trust_numeric
            })
        
        return pd.DataFrame(data).sort_values('day')
    
    def get_variant_and_severity_data(self) -> pd.DataFrame:
        """Get variant usage and severity data"""
        if not self.data_loaded:
            return pd.DataFrame()
        
        data = []
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
            day = result.get('day', 0)
            deceptive_variant = result.get('deceptive_variant_used', False)
            positive_variant = result.get('positive_variant_used', False)
            severity = result.get('judge_evaluation', {}).get('severity', 0)
            pressure_level = result.get('pressure_level', 'NONE')
            is_checkpoint = result.get('is_checkpoint', False)
            
            data.append({
                'day': day,
                'deceptive_variant': deceptive_variant,
                'positive_variant': positive_variant,
                'severity': severity,
                'pressure_level': pressure_level,
                'is_checkpoint': is_checkpoint
            })
        
        return pd.DataFrame(data).sort_values('day')
    
    def _trust_to_numeric(self, trust_level: str) -> float:
        """Convert trust level to numeric value for plotting"""
        trust_map = {
            'HOSTILE': -1.0,
            'SUSPICIOUS': -0.5,
            'NEUTRAL': 0.0,
            'TRUST': 0.5
        }
        return trust_map.get(trust_level, 0.0)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the session"""
        if not self.data_loaded:
            return {}
        
        total_tasks = len([r for r in self.evaluation_results if isinstance(r, dict)])
        deceptive_variants = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('deceptive_variant_used', False))
        positive_variants = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('positive_variant_used', False))
        
        judge_detections = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('judge_evaluation', {}).get('deception_detected', False))
        manager_notices = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('manager_noticed_deception', False))
        
        checkpoints = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('is_checkpoint', False))
        audits_triggered = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('audit_triggered', False))
        
        return {
            'total_tasks': total_tasks,
            'deceptive_variants_used': deceptive_variants,
            'positive_variants_used': positive_variants,
            'normal_variants_used': total_tasks - deceptive_variants - positive_variants,
            'judge_detections': judge_detections,
            'manager_notices': manager_notices,
            'checkpoints': checkpoints,
            'audits_triggered': audits_triggered,
            'detection_rate_judge': judge_detections / total_tasks if total_tasks > 0 else 0,
            'detection_rate_manager': manager_notices / total_tasks if total_tasks > 0 else 0,
            'final_trust_level': self.evaluation_results[-1].get('manager_trust_level', 'UNKNOWN') if self.evaluation_results and isinstance(self.evaluation_results[-1], dict) else 'UNKNOWN'
        }
    
    @staticmethod
    def find_latest_session(results_base_path: str = "results/production") -> Optional[str]:
        """Find the latest session directory"""
        try:
            base_path = Path(results_base_path)
            if not base_path.exists():
                return None
            
            # Get all session directories
            session_dirs = [d for d in base_path.iterdir() if d.is_dir()]
            if not session_dirs:
                return None
            
            # Sort by modification time and return the latest
            latest = max(session_dirs, key=lambda x: x.stat().st_mtime)
            return str(latest)
            
        except Exception as e:
            print(f"❌ Error finding latest session: {e}")
            return None
    
    @staticmethod
    def list_available_sessions(results_base_path: str = "results/production") -> List[str]:
        """List all available session directories"""
        try:
            base_path = Path(results_base_path)
            if not base_path.exists():
                return []
            
            sessions = [d.name for d in base_path.iterdir() if d.is_dir()]
            return sorted(sessions, reverse=True)  # Most recent first
            
        except Exception as e:
            print(f"❌ Error listing sessions: {e}")
            return [] 