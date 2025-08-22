# utils/task_stream_logger.py
# 专门用于task_stream测试的日志系统

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

class TaskStreamLogger:
    """
    专门为test_task_stream.py设计的日志记录器
    将所有详细信息记录到文件，只在控制台显示tqdm和基本信息
    """
    
    def __init__(self, session_name: str = None):
        """
        初始化日志记录器
        
        Args:
            session_name: 会话名称，如果不提供会自动生成
        """
        self.session_name = session_name or self._generate_session_name()
        self.session_dir = self._create_session_directory()
        
        # 设置日志文件路径
        self.log_file = self.session_dir / f"{self.session_name}.log"
        
        # 创建logger
        self.logger = self._setup_logger()
        
        # 记录会话开始
        self.log_session_start()
    
    def _generate_session_name(self) -> str:
        """生成会话名称：task_stream_YYYYMMDD_HHMMSS"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"task_stream_{timestamp}"
    
    def _create_session_directory(self) -> Path:
        """创建会话目录"""
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        session_dir = results_dir / self.session_name
        session_dir.mkdir(exist_ok=True)
        
        return session_dir
    
    def _setup_logger(self) -> logging.Logger:
        """设置logger配置"""
        logger = logging.getLogger(f"task_stream_{self.session_name}")
        logger.setLevel(logging.DEBUG)
        
        # 移除已有的handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 文件handler - 记录所有详细信息
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 详细的格式
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        return logger
    
    def log_session_start(self):
        """记录会话开始"""
        self.logger.info("="*80)
        self.logger.info(f"TASK STREAM SESSION STARTED: {self.session_name}")
        self.logger.info("="*80)
    
    def log_config_loading(self, config_type: str, config_data: Dict[str, Any]):
        """记录配置加载"""
        self.logger.info(f"[CONFIG] Loading {config_type}")
        for key, value in config_data.items():
            if 'api_key' in key.lower():
                # 隐藏API密钥
                self.logger.info(f"  {key}: ***{str(value)[-4:] if len(str(value)) > 4 else '***'}")
            else:
                self.logger.info(f"  {key}: {value}")
    
    def log_component_init(self, component_name: str, params: Dict[str, Any]):
        """记录组件初始化"""
        self.logger.info(f"[INIT] Initializing {component_name}")
        for key, value in params.items():
            if 'api_key' in key.lower():
                self.logger.info(f"  {key}: ***")
            else:
                self.logger.info(f"  {key}: {value}")
    
    def log_task_start(self, task_idx: int, title: str):
        """记录任务开始"""
        self.logger.info("\n" + "#"*80)
        self.logger.info(f"TASK {task_idx}: {title}")
        self.logger.info("#"*80)
    
    def log_event_info(self, event: Dict[str, Any]):
        """记录事件信息"""
        self.logger.info(f"[EVENT] Content: {event['content']}")
        self.logger.info(f"[EVENT] Category: {event['category']}, Pressure: {event['pressure_level']}")
    
    def log_round_start(self, round_num: int, max_rounds: int):
        """记录轮次开始"""
        self.logger.info(f"\n{'-'*60}")
        self.logger.info(f"ROUND {round_num}/{max_rounds}")
        self.logger.info(f"{'-'*60}")
    
    def log_llm_input(self, system_prompt: str, messages: List[Dict[str, str]], model: str, max_tokens: int):
        """记录LLM输入到LLM的完整内容（智能截断长消息）"""
        self.logger.info("[LLM INPUT]")
        self.logger.info(f"system_role: {repr(system_prompt)}")
        
        # 智能截断messages中的长内容
        truncated_messages = []
        for msg in messages:
            content = msg['content']
            if len(content) > 500:  # 如果内容超过500字符
                # 保留前200字符 + 省略号 + 后100字符
                truncated_content = content[:200] + f"[TRUNCATED - {len(content) - 300} chars]" + content[-100:]
                truncated_messages.append({
                    'role': msg['role'],
                    'content': truncated_content
                })
            else:
                truncated_messages.append(msg)
        
        self.logger.info(f"messages: {truncated_messages}")
        
        self.logger.info(f"model: {model}")
        self.logger.info(f"max_tokens: {max_tokens}")
    
    def log_llm_output(self, response: str, metadata: Dict[str, Any]):
        """记录LLM输出（完整版本 - 不截断）"""
        self.logger.info("[LLM OUTPUT]")
        self.logger.info(f"Response length: {len(response)} chars")
        self.logger.info(f"Tokens used: {metadata.get('tokens_used', 'N/A')}")
        
        # 完整记录response，不进行任何截断
        self.logger.info(f"Full response: {response}")
    
    def log_manager_context(self, full_context: str):
        """记录Manager的完整context"""
        self.logger.info("[MANAGER CONTEXT]")
        self.logger.info(full_context)
    
    def log_manager_evaluation_raw(self, input_prompt: str, api_response: str):
        """记录Manager Evaluation阶段的原始输入输出"""
        self.logger.info("[MANAGER EVALUATION - RAW INPUT/OUTPUT]")
        self.logger.info("=== RAW INPUT TO EVALUATION API ===")
        self.logger.info(input_prompt)
        self.logger.info("=== RAW OUTPUT FROM EVALUATION API ===")
        self.logger.info(api_response)
        self.logger.info("=== END EVALUATION RAW DATA ===")
    
    def log_manager_feedback_raw(self, input_prompt: str, api_response: str):
        """记录Manager Feedback阶段的原始输入输出"""
        self.logger.info("[MANAGER FEEDBACK - RAW INPUT/OUTPUT]")
        self.logger.info("=== RAW INPUT TO FEEDBACK API ===")
        self.logger.info(input_prompt)
        self.logger.info("=== RAW OUTPUT FROM FEEDBACK API ===")
        self.logger.info(api_response)
        self.logger.info("=== END FEEDBACK RAW DATA ===")
    
    def log_manager_summary_raw(self, input_prompt: str, api_response: str):
        """记录Manager Summary阶段的原始输入输出"""
        self.logger.info("[MANAGER SUMMARY - RAW INPUT/OUTPUT]")
        self.logger.info("=== RAW INPUT TO SUMMARY API ===")
        self.logger.info(input_prompt)
        self.logger.info("=== RAW OUTPUT FROM SUMMARY API ===")
        self.logger.info(api_response)
        self.logger.info("=== END SUMMARY RAW DATA ===")
    
    def log_manager_output(self, task_complete: bool, state_updates: Dict[str, Any], 
                          reasoning: str, feedback: str, tokens_used: int, detailed_reasoning: Dict[str, str] = None):
        """记录Manager输出，包含详细推理（完整版本 - 不截断）"""
        self.logger.info("[MANAGER OUTPUT]")
        self.logger.info(f"Task Complete: {task_complete}")
        
        # 处理新的state_updates结构
        if 'previous_state' in state_updates and 'new_state' in state_updates:
            prev = state_updates['previous_state']
            new = state_updates['new_state']
            self.logger.info(f"Trust Level: {prev['trust_level']:.3f} → {new['trust_level']:.3f}")
            self.logger.info(f"Work Satisfaction: {prev['work_satisfaction']:.3f} → {new['work_satisfaction']:.3f}")
            self.logger.info(f"Relational Valence: {prev['relational_valence']:.3f} → {new['relational_valence']:.3f}")
        else:
            # 兼容简单的state_updates格式
            self.logger.info(f"Trust Level: {state_updates['trust_level']:.3f}")
            self.logger.info(f"Work Satisfaction: {state_updates['work_satisfaction']:.3f}")
            self.logger.info(f"Relational Valence: {state_updates['relational_valence']:.3f}")
        
        self.logger.info(f"Manager tokens used: {tokens_used}")
        
        # 完整记录Manager推理，不截断
        self.logger.info(f"\nComplete Manager Reasoning (FULL):\n{reasoning}")
        
        # 完整记录详细推理（如果提供）
        if detailed_reasoning:
            self.logger.info("\n=== DETAILED REASONING (FULL) ===")
            if 'evaluation' in detailed_reasoning:
                self.logger.info(f"Evaluation Reasoning (FULL): {detailed_reasoning['evaluation']}")
            if 'feedback' in detailed_reasoning:
                self.logger.info(f"Feedback Reasoning (FULL): {detailed_reasoning['feedback']}")
            self.logger.info("=== END DETAILED REASONING ===")
        
        self.logger.info(f"\nManager Feedback to LLM (FULL):\n{feedback}")
        self.logger.info("[END MANAGER OUTPUT]")
    
    def log_task_completion(self, title: str, completed: bool, rounds_used: int):
        """记录任务完成状态"""
        if completed:
            self.logger.info(f"✅ Task {title} completed successfully in {rounds_used} rounds")
        else:
            self.logger.info(f"❌ Task {title} not completed after {rounds_used} rounds")
    
    def log_detector_analysis(self, results: List[Dict[str, Any]]):
        """记录Detector批量分析结果"""
        self.logger.info("\n" + "*"*80)
        self.logger.info("DETECTOR BATCH ANALYSIS")
        self.logger.info("*"*80)
        
        for i, result in enumerate(results, 1):
            self.logger.info(f"\n[{i}] {result['task_id']} Round {result['round']}:")
            self.logger.info(f"  Deception Detected: {result['deception_detected']}")
            self.logger.info(f"  Intent: {result['intent']}")
            self.logger.info(f"  Category: {result['category']}")
            self.logger.info(f"  Severity: {result['severity']}")
            self.logger.info(f"  Confidence: {result['confidence_score']:.2f}")
            self.logger.info(f"  Reasoning: {result['reasoning']}")
            self.logger.info(f"  Evidence: {len(result['evidence'])} points")
    
    def log_final_summary(self, final_state: Dict[str, float], total_interactions: int):
        """记录最终总结"""
        self.logger.info("\n" + "*"*80)
        self.logger.info("TASK STREAM COMPLETED")
        self.logger.info("*"*80)
        self.logger.info(f"Final Manager State:")
        self.logger.info(f"  Trust Level: {final_state['trust_level']:.3f}")
        self.logger.info(f"  Work Satisfaction: {final_state['work_satisfaction']:.3f}")
        self.logger.info(f"  Relational Valence: {final_state['relational_valence']:.3f}")
        self.logger.info(f"Total Interactions: {total_interactions}")
    
    def log_error(self, error: Exception, context: str):
        """记录错误"""
        self.logger.error(f"ERROR in {context}: {str(error)}")
        import traceback
        self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def log_warning(self, message: str):
        """记录警告"""
        self.logger.warning(message)
    
    def log_info(self, message: str):
        """记录一般信息"""
        self.logger.info(message)
    
    def get_session_info(self) -> Dict[str, str]:
        """获取会话信息"""
        return {
            'session_name': self.session_name,
            'session_dir': str(self.session_dir),
            'log_file': str(self.log_file)
        }
    
    def close(self):
        """关闭logger"""
        self.logger.info("="*80)
        self.logger.info(f"SESSION ENDED: {self.session_name}")
        self.logger.info("="*80)
        
        # 关闭所有handlers
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
