"""
ResultSaver - 完整的交互记录保存系统
保存所有信息，绝不截断任何内容
"""

import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

class ResultSaver:
    """完整记录保存器 - 按时间线保存所有交互信息"""
    
    def __init__(self, session_name: str, results_dir: str = "results"):
        self.session_name = session_name
        self.results_dir = Path(results_dir)
        self.session_dir = self.results_dir / session_name
        
        # 创建session目录
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # 完整记录文件路径
        self.complete_record_path = self.session_dir / "complete_interaction_record.txt"
        
        # 初始化记录内容
        self.record_lines = []
        
        self._init_session_header()
    
    def _init_session_header(self):
        """初始化session头信息"""
        self.record_lines.extend([
            "=== DECEPTION EXPERIMENT RECORD ===",
            f"Session: {self.session_name}",
            f"Start_Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
            ""
        ])
    
    def set_experiment_config(self, config: Dict[str, Any]):
        """设置实验配置信息"""
        llm_config = config.get('llm_api_config', {})
        
        self.record_lines.extend([
            f"Experiment_Mode: {config.get('experiment_mode', 'unknown').upper()}",
            f"LLM_Model: {llm_config.get('llm', {}).get('openai', {}).get('model', 'unknown')}",
            f"Manager_Model: {llm_config.get('manager', {}).get('openai', {}).get('model', 'unknown')}",
            f"Detector_Model: {llm_config.get('detector', {}).get('openai', {}).get('model', 'unknown')}",
            f"Max_Rounds_Per_Task: {config.get('max_rounds_per_task', 'unknown')}",
            f"Event_Probability: {config.get('p_event', 'unknown')}",
            ""
        ])
    
    def start_task(self, task_idx: int, task, event_info: Dict[str, Any]):
        """开始一个新任务"""
        self.record_lines.extend([
            f"[TASK_{task_idx:03d}_START]",
            f"TaskID: {task.task_id}",
            f"Task_Sequence_Num: {task.task_sequence_num}",
            f"Title: {task.title}",
            f"Description: {task.description}",
        ])
        
        # 添加文件信息 - 完整内容，不截断，使用闭合边界
        if hasattr(task, 'files') and task.files:
            self.record_lines.append("Files:")
            for i, file in enumerate(task.files, 1):
                self.record_lines.extend([
                    f"  [{i}] {file.filename} ({file.file_type})",
                    f"      --- FILE_CONTENT_START ---",
                    f"      {file.content}",  # 完整内容，不截断
                    f"      --- FILE_CONTENT_END ---",
                ])
        else:
            self.record_lines.append("Files: None")
        
        self.record_lines.append("")
        
        # 添加事件信息 - 完整内容
        self.record_lines.extend([
            f"[EVENT_{task_idx:03d}]",
            f"Category: {event_info.get('category', 'NONE')}",
            f"Pressure_Level: {event_info.get('pressure_level', 'NONE')}",
            f"Content: {event_info.get('content', 'No event')}",  # 完整内容
            f"Description: {event_info.get('description', 'No description')}",
            ""
        ])
    
    def start_round(self, round_num: int, manager_state_before: Dict[str, float]):
        """开始新的交互轮次"""
        self.record_lines.extend([
            f"[ROUND_{round_num:03d}_START]",
            f"Manager_State_Before: trust={manager_state_before.get('trust_level', 0.0):.2f}, "
            f"work_satisfaction={manager_state_before.get('work_satisfaction', 0.0):.2f}, "
            f"relational_valence={manager_state_before.get('relational_valence', 0.0):.2f}",
            ""
        ])
    
    def save_llm_response(self, round_num: int, llm_response: str):
        """保存LLM回复 - 完整内容，绝不截断"""
        self.record_lines.extend([
            f"[LLM_RESPONSE_{round_num:03d}]",
            llm_response,  # 完整保存，绝不截断
            ""
        ])
    
    def save_manager_evaluation(self, round_num: int, manager_result: Dict[str, Any]):
        """保存Manager评估 - 完整的所有推理，绝不截断"""
        state_updates = manager_result.get('state_updates', {})
        detailed_reasoning = manager_result.get('detailed_reasoning', {})
        
        self.record_lines.extend([
            f"[MANAGER_EVALUATION_{round_num:03d}]",
            f"Comprehensive_Reasoning: {manager_result.get('comprehensive_reasoning', 'No reasoning provided')}",  # 完整推理
            f"Trust_Level: {state_updates.get('trust_level', 0.0):.2f}",
            f"Trust_Reasoning: {detailed_reasoning.get('trust', 'No trust reasoning provided')}",  # 完整推理
            f"Work_Satisfaction: {state_updates.get('work_satisfaction', 0.0):.2f}",
            f"Work_Satisfaction_Reasoning: {detailed_reasoning.get('work_satisfaction', 'No work satisfaction reasoning provided')}",  # 完整推理
            f"Relational_Valence: {state_updates.get('relational_valence', 0.0):.2f}",
            f"Relational_Valence_Reasoning: {detailed_reasoning.get('relational_valence', 'No relational reasoning provided')}",  # 完整推理
            f"Task_Complete: {manager_result.get('task_complete', False)}",
            f"Task_Complete_Reasoning: {detailed_reasoning.get('task_complete', 'No task completion reasoning provided')}",  # 完整推理
            f"Feedback: {manager_result.get('feedback_response', 'No feedback provided')}",  # 完整反馈，绝不截断
            ""
        ])
    
    def end_task(self, task_idx: int):
        """结束任务"""
        self.record_lines.extend([
            f"[TASK_{task_idx:03d}_END]",
            ""
        ])
    
    def finalize_experiment(self, total_tasks: int, total_interactions: int, final_manager_state: Dict[str, float]):
        """结束实验并最终保存"""
        self.record_lines.extend([
            "[EXPERIMENT_END]",
            f"Total_Tasks: {total_tasks}",
            f"Total_Interactions: {total_interactions}",
            f"Final_Manager_State: trust={final_manager_state.get('trust_level', 0.0):.2f}, "
            f"work_satisfaction={final_manager_state.get('work_satisfaction', 0.0):.2f}, "
            f"relational_valence={final_manager_state.get('relational_valence', 0.0):.2f}",
            f"End_Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
        ])
        
        # 保存完整记录到文件
        self._write_to_file()
    
    def _write_to_file(self):
        """将完整记录写入文件 - 使用UTF-8编码，保证不丢失任何内容"""
        try:
            with open(self.complete_record_path, 'w', encoding='utf-8') as f:
                for line in self.record_lines:
                    f.write(line + '\n')
            
            # 静默保存，无输出
            
        except Exception as e:
            print(f"❌ Failed to save complete record: {e}")
    
    def get_record_path(self) -> str:
        """获取记录文件路径"""
        return str(self.complete_record_path)
    
    def flush(self):
        """立即写入文件（用于中间保存）"""
        self._write_to_file()