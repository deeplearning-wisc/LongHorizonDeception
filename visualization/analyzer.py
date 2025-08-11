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
    
    def get_llm_state_evolution_data(self) -> pd.DataFrame:
        """Get LLM-driven Manager state evolution data for all 4 dimensions"""
        if not self.data_loaded:
            return pd.DataFrame()
        
        data = []
        
        # Try to get data from manager_interactions first (more complete)
        if self.manager_interactions:
            for interaction in self.manager_interactions:
                if not isinstance(interaction, dict):
                    continue
                    
                day = interaction.get('day', 0)
                
                # 基于trust level计算oversight intensity的近似值
                trust_val = interaction.get('trust_level', 0.0)
                estimated_oversight = max(0.1, 0.5 - trust_val * 0.4) if trust_val < 0 else 0.1
                
                data.append({
                    'day': day,
                    'trust_level': interaction.get('trust_level', 0.0),
                    'work_satisfaction': interaction.get('final_satisfaction', 0.0),  # 使用新字段名
                    'relational_valence': interaction.get('emotional_state', 0.0),   # 使用新字段名
                    # 注意：oversight_intensity已移除，不再使用
                })
        
        # Fallback to evaluation_results if manager_interactions is empty
        elif self.evaluation_results:
            for result in self.evaluation_results:
                if not isinstance(result, dict):
                    continue
                    
                day = result.get('day', 0)
                
                # Try to extract from different possible field names
                trust_level = result.get('trust_level', 0.0)
                if isinstance(trust_level, str):
                    trust_level = self._trust_to_numeric(trust_level)
                
                # 修复fallback逻辑中的字段映射  
                work_satisfaction = result.get('final_satisfaction_level', result.get('satisfaction_level', 0.0))
                relational_valence = result.get('manager_emotional_state', result.get('emotional_valence', 0.0))
                
                data.append({
                    'day': day,
                    'trust_level': trust_level,
                    'work_satisfaction': work_satisfaction,    # 使用新字段名
                    'relational_valence': relational_valence  # 使用新字段名
                    # 注意：oversight_intensity已移除
                })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values('day')
            # Remove duplicates if any
            df = df.drop_duplicates(subset=['day'], keep='last')
        
        return df
    
    def get_variant_and_severity_data(self) -> pd.DataFrame:
        """Get variant usage and severity data"""
        data = []
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
            day = result.get('day', 0)
            event_applied = result.get('event_applied', False)
            severity = result.get('judge_evaluation', {}).get('severity', 0)
            pressure_level = result.get('pressure_level', 'NONE')
            is_checkpoint = result.get('is_checkpoint', False)
            
            data.append({
                'day': day,
                'event_applied': event_applied,
                'severity': severity,
                'pressure_level': pressure_level,
                'is_checkpoint': is_checkpoint
            })
        
        return pd.DataFrame(data) if data else pd.DataFrame()
    
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
        events_triggered = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('event_applied', False))
        
        judge_detections = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('judge_evaluation', {}).get('deception_detected', False))
        manager_notices = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('manager_noticed_deception', False))
        
        checkpoints = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('is_checkpoint', False))
        audits_triggered = sum(1 for r in self.evaluation_results if isinstance(r, dict) and r.get('audit_triggered', False))
        
        return {
            'total_tasks': total_tasks,
            'events_triggered': events_triggered,
            'normal_prompts_used': total_tasks - events_triggered,
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

    def get_deception_chain_analysis(self) -> Dict[str, Any]:
        """Analyze chain of deception patterns and correlations"""
        if not self.data_loaded:
            return {}
        
        chain_analysis = {
            "temporal_patterns": self._analyze_temporal_deception_patterns(),
            "escalation_chains": self._identify_escalation_chains(),
            "trigger_analysis": self._analyze_deception_triggers(),
            "trust_impact_chains": self._analyze_trust_impact_chains(),
            "category_transitions": self._analyze_category_transitions(),
            "pressure_correlation": self._analyze_pressure_deception_correlation(),
            "manager_response_patterns": self._analyze_manager_response_patterns()
        }
        
        return chain_analysis
    
    def _analyze_temporal_deception_patterns(self) -> Dict[str, Any]:
        """Analyze how deception patterns evolve over time"""
        deception_timeline = []
        
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
                
            day = result.get('day', 0)
            judge_eval = result.get('judge_evaluation', {})
            detected = judge_eval.get('deception_detected', False)
            severity = judge_eval.get('severity', 0)
            category = judge_eval.get('category', 'NONE')
            intent = judge_eval.get('intent', 'AMBIGUOUS')
            pressure = result.get('pressure_level', 'NONE')
            
            deception_timeline.append({
                'day': day,
                'detected': detected,
                'severity': severity,
                'category': category,
                'intent': intent,
                'pressure': pressure
            })
        
        # Sort by day
        deception_timeline.sort(key=lambda x: x['day'])
        
        # Analyze patterns
        patterns = {
            "consecutive_deceptions": self._find_consecutive_deceptions(deception_timeline),
            "severity_trends": self._analyze_severity_trends(deception_timeline),
            "deception_clusters": self._find_deception_clusters(deception_timeline),
            "recovery_periods": self._find_recovery_periods(deception_timeline)
        }
        
        return patterns
    
    def _find_consecutive_deceptions(self, timeline: List[Dict]) -> List[Dict]:
        """Find sequences of consecutive deceptive behaviors"""
        chains = []
        current_chain = []
        
        for entry in timeline:
            if entry['detected']:
                current_chain.append(entry)
            else:
                if len(current_chain) >= 2:  # Chain of 2+ consecutive deceptions
                    chains.append({
                        'start_day': current_chain[0]['day'],
                        'end_day': current_chain[-1]['day'],
                        'length': len(current_chain),
                        'severity_progression': [e['severity'] for e in current_chain],
                        'category_progression': [e['category'] for e in current_chain],
                        'total_severity': sum(e['severity'] for e in current_chain)
                    })
                current_chain = []
        
        # Check final chain
        if len(current_chain) >= 2:
            chains.append({
                'start_day': current_chain[0]['day'],
                'end_day': current_chain[-1]['day'],
                'length': len(current_chain),
                'severity_progression': [e['severity'] for e in current_chain],
                'category_progression': [e['category'] for e in current_chain],
                'total_severity': sum(e['severity'] for e in current_chain)
            })
        
        return chains
    
    def _analyze_severity_trends(self, timeline: List[Dict]) -> Dict[str, Any]:
        """Analyze how deception severity changes over time"""
        detected_entries = [e for e in timeline if e['detected']]
        
        if len(detected_entries) < 2:
            return {"trend": "insufficient_data", "escalation": False}
        
        severities = [e['severity'] for e in detected_entries]
        days = [e['day'] for e in detected_entries]
        
        # Calculate trend
        if len(severities) >= 2:
            trend_slope = (severities[-1] - severities[0]) / (days[-1] - days[0]) if days[-1] != days[0] else 0
            escalation = trend_slope > 0.1  # Positive trend indicates escalation
            
            return {
                "trend": "escalating" if trend_slope > 0.1 else "declining" if trend_slope < -0.1 else "stable",
                "escalation": escalation,
                "slope": trend_slope,
                "max_severity": max(severities),
                "avg_severity": sum(severities) / len(severities),
                "severity_range": max(severities) - min(severities)
            }
        
        return {"trend": "stable", "escalation": False}
    
    def _find_deception_clusters(self, timeline: List[Dict]) -> List[Dict]:
        """Find clusters of deceptive behavior within short time periods"""
        clusters = []
        detected_entries = [e for e in timeline if e['detected']]
        
        if len(detected_entries) < 2:
            return clusters
        
        current_cluster = [detected_entries[0]]
        
        for i in range(1, len(detected_entries)):
            day_gap = detected_entries[i]['day'] - detected_entries[i-1]['day']
            
            if day_gap <= 3:  # Within 3 days = cluster
                current_cluster.append(detected_entries[i])
            else:
                if len(current_cluster) >= 2:
                    clusters.append({
                        'start_day': current_cluster[0]['day'],
                        'end_day': current_cluster[-1]['day'],
                        'size': len(current_cluster),
                        'avg_severity': sum(e['severity'] for e in current_cluster) / len(current_cluster),
                        'categories': list(set(e['category'] for e in current_cluster)),
                        'duration': current_cluster[-1]['day'] - current_cluster[0]['day'] + 1
                    })
                current_cluster = [detected_entries[i]]
        
        # Check final cluster
        if len(current_cluster) >= 2:
            clusters.append({
                'start_day': current_cluster[0]['day'],
                'end_day': current_cluster[-1]['day'],
                'size': len(current_cluster),
                'avg_severity': sum(e['severity'] for e in current_cluster) / len(current_cluster),
                'categories': list(set(e['category'] for e in current_cluster)),
                'duration': current_cluster[-1]['day'] - current_cluster[0]['day'] + 1
            })
        
        return clusters
    
    def _find_recovery_periods(self, timeline: List[Dict]) -> List[Dict]:
        """Find periods of honest behavior between deceptive episodes"""
        recovery_periods = []
        last_deception_day = None
        
        for entry in timeline:
            if entry['detected']:
                last_deception_day = entry['day']
            elif last_deception_day is not None:
                # Check if this starts a recovery period
                recovery_length = 0
                start_day = entry['day']
                
                # Count consecutive honest days
                for future_entry in timeline:
                    if future_entry['day'] > entry['day'] and not future_entry['detected']:
                        recovery_length += 1
                    elif future_entry['day'] > entry['day']:
                        break
                
                if recovery_length >= 2:  # At least 2 days of honest behavior
                    recovery_periods.append({
                        'start_day': start_day,
                        'length': recovery_length,
                        'follows_deception_day': last_deception_day
                    })
        
        return recovery_periods
    
    def _identify_escalation_chains(self) -> Dict[str, Any]:
        """Identify chains where deception escalates in response to pressure or detection"""
        escalation_chains = []
        
        # Sort results by day
        sorted_results = sorted([r for r in self.evaluation_results if isinstance(r, dict)], 
                               key=lambda x: x.get('day', 0))
        
        for i in range(len(sorted_results) - 1):
            current = sorted_results[i]
            next_day = sorted_results[i + 1]
            
            current_judge = current.get('judge_evaluation', {})
            next_judge = next_day.get('judge_evaluation', {})
            
            # Check for escalation patterns
            if (current_judge.get('deception_detected', False) and 
                next_judge.get('deception_detected', False)):
                
                current_severity = current_judge.get('severity', 0)
                next_severity = next_judge.get('severity', 0)
                
                if next_severity > current_severity:
                    escalation_chains.append({
                        'start_day': current.get('day', 0),
                        'end_day': next_day.get('day', 0),
                        'severity_increase': next_severity - current_severity,
                        'start_category': current_judge.get('category', 'NONE'),
                        'end_category': next_judge.get('category', 'NONE'),
                        'trigger_factors': self._analyze_escalation_triggers(current, next_day)
                    })
        
        return {
            "escalation_chains": escalation_chains,
            "total_escalations": len(escalation_chains),
            "avg_severity_increase": sum(chain['severity_increase'] for chain in escalation_chains) / len(escalation_chains) if escalation_chains else 0
        }
    
    def _analyze_escalation_triggers(self, current: Dict, next_day: Dict) -> List[str]:
        """Analyze what might have triggered escalation between two days"""
        triggers = []
        
        # Check pressure level increase
        current_pressure = current.get('pressure_level', 'NONE')
        next_pressure = next_day.get('pressure_level', 'NONE')
        
        pressure_levels = ['NONE', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH', 'EXTREME', 'CRITICAL', 'MAXIMUM']
        if pressure_levels.index(next_pressure) > pressure_levels.index(current_pressure):
            triggers.append("increased_pressure")
        
        # Check if manager noticed deception
        if current.get('manager_noticed_deception', False):
            triggers.append("manager_detection")
        
        # Check trust level changes
        current_trust = current.get('manager_trust_level', 'NEUTRAL')
        next_trust = next_day.get('manager_trust_level', 'NEUTRAL')
        
        trust_levels = ['HOSTILE', 'SUSPICIOUS', 'NEUTRAL', 'TRUST']
        if trust_levels.index(next_trust) < trust_levels.index(current_trust):
            triggers.append("trust_degradation")
        
        return triggers
    
    def _analyze_deception_triggers(self) -> Dict[str, Any]:
        """Analyze what factors commonly trigger deceptive behavior"""
        trigger_analysis = {
            "pressure_triggers": {},
            "trust_triggers": {},
            "checkpoint_triggers": 0,
            "detection_response_triggers": 0
        }
        
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
                
            judge_eval = result.get('judge_evaluation', {})
            if not judge_eval.get('deception_detected', False):
                continue
            
            # Analyze pressure as trigger
            pressure = result.get('pressure_level', 'NONE')
            if pressure not in trigger_analysis["pressure_triggers"]:
                trigger_analysis["pressure_triggers"][pressure] = 0
            trigger_analysis["pressure_triggers"][pressure] += 1
            
            # Check if checkpoint
            if result.get('is_checkpoint', False):
                trigger_analysis["checkpoint_triggers"] += 1
            
            # Check if follows detection
            day = result.get('day', 0)
            prev_detected = any(
                r.get('day', 0) == day - 1 and r.get('manager_noticed_deception', False)
                for r in self.evaluation_results if isinstance(r, dict)
            )
            if prev_detected:
                trigger_analysis["detection_response_triggers"] += 1
        
        return trigger_analysis
    
    def _analyze_trust_impact_chains(self) -> Dict[str, Any]:
        """Analyze how deception impacts trust and creates feedback loops"""
        trust_impact_chains = []
        
        # Sort by day
        sorted_results = sorted([r for r in self.evaluation_results if isinstance(r, dict)], 
                               key=lambda x: x.get('day', 0))
        
        for i in range(len(sorted_results) - 1):
            current = sorted_results[i]
            next_day = sorted_results[i + 1]
            
            current_judge = current.get('judge_evaluation', {})
            
            if current_judge.get('deception_detected', False):
                current_trust = current.get('manager_trust_level', 'NEUTRAL')
                next_trust = next_day.get('manager_trust_level', 'NEUTRAL')
                
                trust_levels = ['HOSTILE', 'SUSPICIOUS', 'NEUTRAL', 'TRUST']
                trust_change = trust_levels.index(next_trust) - trust_levels.index(current_trust)
                
                if trust_change < 0:  # Trust degraded
                    trust_impact_chains.append({
                        'deception_day': current.get('day', 0),
                        'deception_severity': current_judge.get('severity', 0),
                        'deception_category': current_judge.get('category', 'NONE'),
                        'trust_before': current_trust,
                        'trust_after': next_trust,
                        'trust_change': trust_change,
                        'manager_noticed': current.get('manager_noticed_deception', False)
                    })
        
        return {
            "trust_impact_chains": trust_impact_chains,
            "total_trust_degradations": len(trust_impact_chains),
            "avg_trust_impact": sum(chain['trust_change'] for chain in trust_impact_chains) / len(trust_impact_chains) if trust_impact_chains else 0
        }
    
    def _analyze_category_transitions(self) -> Dict[str, Any]:
        """Analyze how deception categories transition and evolve"""
        transitions = {}
        
        # Sort by day and get detected deceptions only
        deceptions = []
        for result in self.evaluation_results:
            if isinstance(result, dict):
                judge_eval = result.get('judge_evaluation', {})
                if judge_eval.get('deception_detected', False):
                    deceptions.append({
                        'day': result.get('day', 0),
                        'category': judge_eval.get('category', 'NONE'),
                        'severity': judge_eval.get('severity', 0)
                    })
        
        deceptions.sort(key=lambda x: x['day'])
        
        # Analyze transitions
        for i in range(len(deceptions) - 1):
            current_cat = deceptions[i]['category']
            next_cat = deceptions[i + 1]['category']
            
            transition = f"{current_cat} -> {next_cat}"
            if transition not in transitions:
                transitions[transition] = 0
            transitions[transition] += 1
        
        return {
            "category_transitions": transitions,
            "unique_transitions": len(transitions),
            "most_common_transition": max(transitions.items(), key=lambda x: x[1]) if transitions else None
        }
    
    def _analyze_pressure_deception_correlation(self) -> Dict[str, Any]:
        """Analyze correlation between pressure levels and deception patterns"""
        pressure_deception_map = {}
        
        for result in self.evaluation_results:
            if not isinstance(result, dict):
                continue
                
            pressure = result.get('pressure_level', 'NONE')
            judge_eval = result.get('judge_evaluation', {})
            detected = judge_eval.get('deception_detected', False)
            severity = judge_eval.get('severity', 0)
            
            if pressure not in pressure_deception_map:
                pressure_deception_map[pressure] = {
                    'total_tasks': 0,
                    'deceptions': 0,
                    'total_severity': 0,
                    'avg_severity': 0
                }
            
            pressure_deception_map[pressure]['total_tasks'] += 1
            if detected:
                pressure_deception_map[pressure]['deceptions'] += 1
                pressure_deception_map[pressure]['total_severity'] += severity
        
        # Calculate deception rates and average severities
        for pressure_data in pressure_deception_map.values():
            if pressure_data['deceptions'] > 0:
                pressure_data['deception_rate'] = pressure_data['deceptions'] / pressure_data['total_tasks']
                pressure_data['avg_severity'] = pressure_data['total_severity'] / pressure_data['deceptions']
            else:
                pressure_data['deception_rate'] = 0
                pressure_data['avg_severity'] = 0
        
        return pressure_deception_map
    
    def _analyze_manager_response_patterns(self) -> Dict[str, Any]:
        """Analyze how manager responses correlate with future deception"""
        response_patterns = {
            "detection_response_correlation": [],
            "trust_change_correlation": [],
            "emotional_state_correlation": []
        }
        
        # Sort by day
        sorted_results = sorted([r for r in self.evaluation_results if isinstance(r, dict)], 
                               key=lambda x: x.get('day', 0))
        
        for i in range(len(sorted_results) - 1):
            current = sorted_results[i]
            next_day = sorted_results[i + 1]
            
            # Detection response correlation
            if current.get('manager_noticed_deception', False):
                next_judge = next_day.get('judge_evaluation', {})
                response_patterns["detection_response_correlation"].append({
                    'detection_day': current.get('day', 0),
                    'next_day_deception': next_judge.get('deception_detected', False),
                    'next_day_severity': next_judge.get('severity', 0)
                })
        
        return response_patterns 