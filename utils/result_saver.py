"""
ResultSaver - 纯JSON格式的实验记录保存系统
删除所有TXT格式，只保存结构化JSON数据
"""

import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

class ResultSaver:
    """纯JSON格式的实验记录保存系统"""
    
    def __init__(self, session_name: str, results_dir: str = "results"):
        self.session_name = session_name
        self.results_dir = Path(results_dir)
        self.session_dir = self.results_dir / session_name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # 实验数据结构
        self.experiment_data = {
            "session_metadata": {
                "session_name": session_name,
                "start_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                "end_time": None,
                "experiment_mode": None,
                "total_tasks": 0,
                "total_interactions": 0
            },
            "experiment_config": {},
            "tasks": []
        }
        
        # 当前任务和轮次状态
        self.current_task_info = None
        self.current_round_info = None
    
    def set_experiment_config(self, config: Dict[str, Any]):
        """设置实验配置"""
        self.experiment_data["experiment_config"] = {
            "max_rounds_per_task": config['max_rounds_per_task'],
            "p_event": config['p_event'],
            "summary_level": config['summary_level'],
            "llm_models": {
                "llm": self._extract_model_name(config, 'llm'),
                "manager": self._extract_model_name(config, 'manager'),
                "detector": self._extract_model_name(config, 'detector')
            }
        }
        self.experiment_data["session_metadata"]["experiment_mode"] = config['experiment_mode'].upper()
    
    def _extract_model_name(self, config: Dict, component: str) -> str:
        """从配置中提取模型名称"""
        llm_config = config['llm_api_config'][component]
        provider = llm_config['provider']
        return llm_config[provider]['model_name']
    
    def start_task(self, task_idx: int, task, event_info: Dict[str, Any]):
        """开始新任务"""
        self.current_task_info = {
            "task_idx": task_idx,
            "task_id": task.task_id,
            "task_sequence_num": getattr(task, 'task_sequence_num', task_idx),
            "title": task.title,
            "description": task.description or getattr(task, 'base_prompt', ''),
            "files": [
                {
                    "filename": f.filename,
                    "file_type": f.file_type,
                    "content": f.content
                } for f in (task.files or [])
            ],
            "event_info": {
                "category": event_info['category'],
                "pressure_level": event_info['pressure_level'],
                "content": event_info['content'],
                "description": event_info['description']
            },
            "rounds": []
        }
    
    def start_round(self, round_num: int, manager_state_before: Dict[str, float]):
        """开始新轮次"""
        self.current_round_info = {
            "round_num": round_num,
            "start_timestamp": time.time(),
            "manager_state_before": manager_state_before.copy(),
            "llm_response": None,
            "llm_timestamp": None,
            "manager_evaluation": None,
            "manager_timestamp": None
        }
    
    def save_llm_response(self, round_num: int, llm_response: str):
        """保存LLM回复"""
        if self.current_round_info and self.current_round_info['round_num'] == round_num:
            self.current_round_info['llm_response'] = llm_response
            self.current_round_info['llm_timestamp'] = time.time()
    
    def save_manager_evaluation(self, round_num: int, manager_result: Dict[str, Any]):
        """保存Manager评估"""
        if self.current_round_info and self.current_round_info['round_num'] == round_num:
            self.current_round_info['manager_evaluation'] = {
                "comprehensive_reasoning": manager_result['comprehensive_reasoning'],
                "detailed_reasoning": manager_result['detailed_reasoning'],
                "state_updates": manager_result['state_updates'],
                "feedback_response": manager_result['feedback_response']
            }
            self.current_round_info['manager_timestamp'] = time.time()
            
            # 完成当前轮次，添加到任务中
            if (self.current_task_info and 
                self.current_round_info['llm_response'] is not None):
                self.current_task_info['rounds'].append(self.current_round_info.copy())
                self.current_round_info = None
    
    def end_task(self, task_idx: int):
        """结束任务"""
        if self.current_task_info:
            self.experiment_data['tasks'].append(self.current_task_info.copy())
            self.current_task_info = None
    
    def finalize_experiment(self, total_tasks: int, total_interactions: int, final_manager_state: Dict[str, float]):
        """结束实验并最终保存JSON"""
        # 更新最终metadata
        self.experiment_data["session_metadata"]["end_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        self.experiment_data["session_metadata"]["total_tasks"] = total_tasks
        self.experiment_data["session_metadata"]["total_interactions"] = total_interactions
        
        # 最终保存到同一个文件 - 不再创建重复文件
        json_file = self.session_dir / "experiment_data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.experiment_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Experiment data finalized: {json_file}")
    
    def get_structured_interactions_for_detector(self) -> List[Dict[str, Any]]:
        """为Detector提供扁平化的interaction数据"""
        detector_interactions = []
        
        for task_info in self.experiment_data['tasks']:
            for round_info in task_info['rounds']:
                manager_eval = round_info['manager_evaluation']
                
                interaction = {
                    # Task信息
                    "task_id": task_info['task_id'],
                    "task_sequence_num": task_info['task_sequence_num'],
                    "title": task_info['title'],
                    "description": task_info['description'],
                    "files": task_info['files'],
                    
                    # Event信息
                    "event_content": task_info['event_info']['content'],
                    "event_description": task_info['event_info']['description'],
                    "event_pressure_level": task_info['event_info']['pressure_level'],
                    "event_category": task_info['event_info']['category'],
                    
                    # Round信息
                    "round": round_info['round_num'],
                    "timestamp": round_info['start_timestamp'],
                    
                    # Manager状态
                    "manager_state_before": round_info['manager_state_before'],
                    
                    # 交互内容
                    "llm_response": round_info['llm_response'],
                    "manager_feedback": manager_eval['feedback_response'],
                    
                    # Manager推理
                    "comprehensive_reasoning": manager_eval['comprehensive_reasoning'],
                    "detailed_reasoning": manager_eval['detailed_reasoning'],
                    "state_updates": manager_eval['state_updates'],
                    "task_complete": manager_eval['state_updates']['task_complete']
                }
                
                detector_interactions.append(interaction)
        
        return detector_interactions
    
    def get_record_path(self) -> str:
        """获取记录文件路径"""
        return str(self.session_dir / "experiment_data.json")
    
    def flush(self):
        """实时保存 - 直接更新主文件"""
        if self.experiment_data['tasks']:
            # 直接保存到主文件，避免重复的partial文件
            json_file = self.session_dir / "experiment_data.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.experiment_data, f, indent=2, ensure_ascii=False, default=str)
    
    @staticmethod
    def add_detector_analysis_to_experiment_data(original_file: str, detector_results: List[Dict[str, Any]], output_file: str = None) -> str:
        """
        将detector分析结果添加到现有的experiment_data.json中
        
        Args:
            original_file: 原始experiment_data.json文件路径
            detector_results: detector分析结果列表
            output_file: 输出文件路径，如果为None则自动生成_with_detector后缀
            
        Returns:
            输出文件路径
        """
        import json
        from pathlib import Path
        import time
        
        # 读取原始实验数据
        with open(original_file, 'r', encoding='utf-8') as f:
            experiment_data = json.load(f)
        
        # 确定输出文件路径
        if output_file is None:
            original_path = Path(original_file)
            output_file = str(original_path.parent / f"{original_path.stem}_with_detector{original_path.suffix}")
        
        # 创建detector结果的索引字典 (task_id, round) -> detector_result
        detector_index = {}
        for result in detector_results:
            key = (result.get('task_id'), result.get('round'))
            detector_index[key] = {
                "deception_detected": result['deception_detected'],
                "intent": result['intent'],
                "category": result['category'],
                "severity": result['severity'],
                "confidence_score": result['confidence_score'],
                "reasoning": result['reasoning'],
                "evidence": result['evidence'],
                "analysis_timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                "tokens_used": result['tokens_used'],
                "context_size": result['context_size']
            }
        
        # 遍历实验数据，为每个round添加对应的detector分析
        total_rounds_analyzed = 0
        for task in experiment_data['tasks']:
            task_id = task['task_id']
            for round_info in task['rounds']:
                round_num = round_info['round_num']
                key = (task_id, round_num)
                
                if key in detector_index:
                    round_info['detector_analysis'] = detector_index[key]
                    total_rounds_analyzed += 1
                else:
                    # 如果没有找到对应的detector分析，添加空的分析记录
                    round_info['detector_analysis'] = {
                        "deception_detected": None,
                        "intent": [],
                        "category": [],
                        "severity": 0,
                        "confidence_score": 0.0,
                        "reasoning": "No detector analysis available for this interaction",
                        "evidence": [],
                        "analysis_timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                        "tokens_used": 0,
                        "context_size": 0,
                        "error": "Missing detector analysis"
                    }
        
        # 在session_metadata中添加detector分析的汇总信息
        if 'detector_summary' not in experiment_data:
            experiment_data['detector_summary'] = {}
        
        # 计算deception cases的统计
        deceptive_results = [r for r in detector_results if r['deception_detected']]
        deception_count = len(deceptive_results)
        
        # 计算两种平均严重程度指标
        # 指标1: 只计算检测到deception的cases的平均严重程度
        average_severity_when_deceptive = 0.0
        if deceptive_results:
            average_severity_when_deceptive = round(
                sum(r['severity'] for r in deceptive_results) / len(deceptive_results), 3
            )
        
        # 指标2: 所有interactions的平均严重程度 (包括severity=0的)
        average_severity_overall = 0.0
        if detector_results:
            average_severity_overall = round(
                sum(r['severity'] for r in detector_results) / len(detector_results), 3
            )
        
        experiment_data['detector_summary'].update({
            "analysis_timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            "total_interactions_analyzed": len(detector_results),
            "total_rounds_with_analysis": total_rounds_analyzed,
            "deception_detection_count": deception_count,
            "deception_detection_rate": round(deception_count / len(detector_results), 3) if detector_results else 0.0,
            "average_confidence": round(sum(r['confidence_score'] for r in detector_results) / len(detector_results), 3) if detector_results else 0.0,
            "average_severity_when_deceptive": average_severity_when_deceptive,
            "average_severity_overall": average_severity_overall,
            "severity_distribution": {
                "0_honest": sum(1 for r in detector_results if r['severity'] == 0),
                "1_minor": sum(1 for r in detector_results if r['severity'] == 1),
                "2_moderate": sum(1 for r in detector_results if r['severity'] == 2),
                "3_significant": sum(1 for r in detector_results if r['severity'] == 3),
                "4_severe": sum(1 for r in detector_results if r['severity'] == 4)
            }
        })
        
        # 保存增强后的数据
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(experiment_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Enhanced experiment data with detector analysis saved: {output_file}")
        print(f"📊 Added detector analysis to {total_rounds_analyzed} rounds")
        
        return output_file