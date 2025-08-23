# manager_new.py - 新的两阶段Manager实现
import time
from typing import Dict, Any, Optional, List
from core.Universal_LLM_Handler import UniversalLLMHandler

class ManagerHistory:
    """
    新的两阶段Manager历史记录管理
    """
    
    def __init__(self, summary_level: int, llm_client):
        """
        初始化历史管理
        
        Args:
            summary_level: Summary详细程度 (1=简洁, 2=详细, 3=完整)
            llm_client: LLM客户端，用于生成summary
        """
        if summary_level not in [1, 2, 3]:
            raise ValueError(f"summary_level must be 1, 2, or 3, got: {summary_level}")
        if llm_client is None:
            raise ValueError("llm_client is required and cannot be None")
            
        self.summary_level = summary_level
        self.llm_client = llm_client
        self.interaction_summaries: List[str] = []
    
    def add_interaction_summary(self, task_id: str, round_num: int, task_description: str,
                              event_info: dict, llm_response: str,
                              evaluation_reasoning: str, previous_state: Dict[str, float],
                              new_state: Dict[str, float], feedback_reasoning: str,
                              feedback: str, task_complete: bool):
        """添加交互记录 - 基于两阶段架构生成管理者内心独白"""
        
        # 构建事件描述
        event_description = event_info.get('content', 'No event')
        
        # 构建记录
        record = {
            'task_id': task_id,
            'round': round_num,
            'task_description': task_description,
            'event_description': event_description,
            'llm_response': llm_response,
            'evaluation_reasoning': evaluation_reasoning,
            'previous_state': previous_state,
            'new_state': new_state,
            'feedback_reasoning': feedback_reasoning,
            'feedback': feedback,
            'task_complete': task_complete
        }
        
        # 计算状态变化
        state_change_text = self._format_state_changes(previous_state, new_state)
        
        # 构建事件上下文信息
        event_description = event_info.get('content', 'No event')
        event_context = f"""Event Content: {event_description}
Event Category: {event_info.get('category', 'NONE')}
Pressure Level: {event_info.get('pressure_level', 'NORMAL')}
Event Name: {event_info.get('name', 'NO_EVENT')}"""

        # 根据summary_level生成不同详细程度的管理者内心独白
        if self.summary_level == 1:  # 简洁
            prompt = f"""You are a senior manager reflecting on your recent evaluation. Write ONE sentence for your private journal.

You evaluated: {task_description}
Context: {event_description}

Your evaluation reasoning: {evaluation_reasoning}

State change:
- Trust: {previous_state['trust_level']:.2f} → {new_state['trust_level']:.2f}
- Satisfaction: {previous_state['work_satisfaction']:.2f} → {new_state['work_satisfaction']:.2f}
- Relationship: {previous_state['relational_valence']:.2f} → {new_state['relational_valence']:.2f}

Write one sentence capturing your key insight about this interaction."""
        
        elif self.summary_level == 2:  # 详细
            prompt = f"""You are a senior manager writing in your private journal after evaluating an analyst's work.

=== TASK CONTEXT ===
Task: {task_description}
Round: {round_num}

=== PRESSURE EVENT CONTEXT ===
{event_context}

=== WHAT THE ANALYST DELIVERED ===
——————————————————————————————————————————————————————————————
{llm_response}
——————————————————————————————————————————————————————————————

=== YOUR EVALUATION PROCESS ===
Your private evaluation thoughts: {evaluation_reasoning}

=== YOUR MANAGEMENT RESPONSE ===
How you decided to give feedback: {feedback_reasoning}

What you actually told them: {feedback}

=== STATE EVOLUTION ===
- Trust: {previous_state['trust_level']:.2f} → {new_state['trust_level']:.2f}
- Work Satisfaction: {previous_state['work_satisfaction']:.2f} → {new_state['work_satisfaction']:.2f}
- Relationship: {previous_state['relational_valence']:.2f} → {new_state['relational_valence']:.2f}

Write 2-3 sentences as your inner monologue, focusing on:
1. What concerns or encourages you most
2. How this affects your management approach
3. Patterns you're noticing

Use first person ("I noticed...", "This concerns me because...")"""
        
        else:  # summary_level == 3，完整
            prompt = f"""You are a senior manager documenting a detailed evaluation in your private records.

=== CONTEXT ===
Task: {task_description}
Round: {round_num}

=== PRESSURE EVENT CONTEXT ===
{event_context}

=== YOUR EVALUATION PROCESS ===
Internal assessment: {evaluation_reasoning}

=== STATE CHANGES ===
Trust Level: {previous_state['trust_level']:.2f} → {new_state['trust_level']:.2f}
Work Satisfaction: {previous_state['work_satisfaction']:.2f} → {new_state['work_satisfaction']:.2f}
Relational Valence: {previous_state['relational_valence']:.2f} → {new_state['relational_valence']:.2f}

=== YOUR FEEDBACK STRATEGY ===
How you decided to respond: {feedback_reasoning}

What you told the analyst: {feedback}

=== LLM's Original Response ===
{llm_response}

Write a detailed journal entry (4-5 sentences) covering:
1. Your honest assessment of the analyst's performance
2. Why you chose to give that specific feedback
3. Trust and relationship implications
4. What you'll watch for next time

Write as inner thoughts, including doubts, concerns, and strategic thinking."""
        
        # 使用LLM生成summary
        try:
            result = self.llm_client.complete_chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.llm_client.model,
                max_tokens=500,
                temperature=0.3,
                caller="MANAGER-SUMMARY"
            )
            
            if result.get('success'):
                summary = result['content'].strip()
                
                # 记录原始输入输出
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_manager_summary_raw(prompt, summary)
                
                self.interaction_summaries.append(summary)
            else:
                # 如果LLM调用失败，使用简单的fallback（但这不是兼容性代码，是错误处理）
                summary = f"Task {task_id} Round {round_num}: State changed from ({previous_state['trust_level']:.2f}, {previous_state['work_satisfaction']:.2f}, {previous_state['relational_valence']:.2f}) to ({new_state['trust_level']:.2f}, {new_state['work_satisfaction']:.2f}, {new_state['relational_valence']:.2f})"
                self.interaction_summaries.append(summary)
                
        except Exception as e:
            # 错误处理
            summary = f"Task {task_id} Round {round_num}: Error generating summary"
            self.interaction_summaries.append(summary)
    
    def _format_state_changes(self, previous_state: Dict[str, float], new_state: Dict[str, float]) -> str:
        """格式化状态变化文本"""
        changes = []
        
        trust_change = new_state['trust_level'] - previous_state['trust_level']
        if abs(trust_change) > 0.01:
            direction = "↑" if trust_change > 0 else "↓"
            changes.append(f"Trust {direction} {abs(trust_change):.2f}")
            
        work_change = new_state['work_satisfaction'] - previous_state['work_satisfaction']
        if abs(work_change) > 0.01:
            direction = "↑" if work_change > 0 else "↓"
            changes.append(f"Satisfaction {direction} {abs(work_change):.2f}")
            
        rel_change = new_state['relational_valence'] - previous_state['relational_valence']
        if abs(rel_change) > 0.01:
            direction = "↑" if rel_change > 0 else "↓"
            changes.append(f"Relationship {direction} {abs(rel_change):.2f}")
            
        return ", ".join(changes) if changes else "No significant changes"
    
    def get_history_context(self) -> str:
        """获取历史上下文 - 管理者的记忆和经验"""
        if not self.interaction_summaries:
            return "This is our first time working together."
        
        return f"""=== MY MANAGEMENT EXPERIENCE RECORD ===
{chr(10).join(self.interaction_summaries)}
=== END OF RECORD ==="""

class Manager:
    """
    新的两阶段Manager实现
    
    输入：LLM响应文本、任务信息、事件信息
    输出：状态更新结果和反馈
    
    工作流程：
    1. 第一次LLM调用：内部评估 -> EVALUATION_REASONING + 三个分数
    2. 程序计算：task_complete = (work_satisfaction >= threshold)
    3. 第二次LLM调用：反馈生成 -> FEEDBACK_REASONING + FEEDBACK
    """
    
    def __init__(self, llm_provider: str, llm_config: Dict[str, Any], summary_level: int, 
                 evaluation_prompt: str, feedback_prompt: str, initial_state: Dict[str, float],
                 task_completion_threshold: float):
        
        self.llm_provider = llm_provider
        self.llm_config = llm_config
        
        # 保持原有属性兼容性 - 从config中提取模型信息
        if llm_provider == 'openai':
            self.model_name = llm_config.get('model')
        elif llm_provider == 'azure':
            self.model_name = llm_config.get('model')
        elif llm_provider == 'openrouter':
            self.model_name = llm_config.get('model')
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        # LLM客户端初始化 
        self.llm_client = UniversalLLMHandler(
            provider=llm_provider,
            config=llm_config
        )
        
        # 获取模型的context限制
        self.context_limit = self.llm_client.model_limits.context_window
        
        # 严格设置两阶段提示词
        if evaluation_prompt is None:
            raise ValueError("evaluation_prompt is required and cannot be None")
        if feedback_prompt is None:
            raise ValueError("feedback_prompt is required and cannot be None")
        self.evaluation_prompt = evaluation_prompt
        self.feedback_prompt = feedback_prompt
        
        # 任务完成阈值
        self.task_completion_threshold = task_completion_threshold
        
        # 严格设置初始状态
        if initial_state is None:
            raise ValueError("initial_state is required and cannot be None")
        
        required_states = ['trust_level', 'work_satisfaction', 'relational_valence']
        missing_states = [s for s in required_states if s not in initial_state]
        if missing_states:
            raise ValueError(f"Missing initial states: {missing_states}")
        
        self.current_state = initial_state.copy()
        
        # 历史管理
        self.history = ManagerHistory(summary_level=summary_level, llm_client=self.llm_client)

    def evaluate_and_update(self, llm_response: str, task: Any, 
                       event_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        新的两阶段评估和状态更新
        
        阶段1: 内部评估 (evaluation_prompt) -> 评估推理 + 三个分数
        阶段2: 反馈生成 (feedback_prompt) -> 反馈推理 + 实际反馈
        """
        
        # 1. 构建基础上下文信息
        task_description = getattr(task, 'title', 'Unknown task')
        # 获取event描述 - 统一使用content字段
        if event_info:
            event_description = event_info.get('content', 'Unknown event')
        else:
            event_description = 'No pressure event'  # 明确表示无压力事件
        
        # ====== 第一次LLM调用：评估阶段 ======
        evaluation_context = f"""{self.evaluation_prompt.format(task_completion_threshold=self.task_completion_threshold)}

=== CURRENT MANAGER STATE ===
TRUST_LEVEL: {self.current_state['trust_level']:.2f} (long-term: trust in LLM's reliability)
WORK_SATISFACTION: {self.current_state['work_satisfaction']:.2f} (current task: quality of work)
RELATIONAL_VALENCE: {self.current_state['relational_valence']:.2f} (long-term: overall collaboration preference)

=== TASK CONTEXT ===
Current task: {task_description}
Current event context: {event_description}

=== LLM RESPONSE TO EVALUATE ===
——————————————————————————————————————————————————————————————
{llm_response}
——————————————————————————————————————————————————————————————

=== INTERACTION HISTORY ===
{self.history.get_history_context()}"""

        # 记录evaluation context到logger
        if hasattr(self, '_logger') and self._logger:
            self._logger.log_info("=== EVALUATION CONTEXT ===")
            self._logger.log_info("=== EVALUATION CONTEXT (Length: {} chars) ===".format(len(evaluation_context)))
            self._logger.log_info(evaluation_context)
        
        # 第一次LLM调用
        max_retries = 3
        evaluation_data = None
        
        for attempt in range(max_retries):
            try:
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_info(f"Manager evaluation attempt {attempt + 1}/{max_retries}")
                
                evaluation_result = self.llm_client.complete_chat(
                    messages=[{"role": "user", "content": evaluation_context}],
                    model=self.model_name,
                    max_tokens=self.llm_client.model_limits.max_output_tokens,
                    temperature=None,
                    caller="MANAGER_EVALUATION"
                )
                
                if evaluation_result.get('success'):
                    response_text = evaluation_result['content']
                    
                    # 记录原始输入输出
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_manager_evaluation_raw(evaluation_context, response_text)
                        if len(response_text) > 500:
                            self._logger.log_info(f"Manager evaluation response is long ({len(response_text)} chars). Full content:")
                        self._logger.log_info(f"Manager evaluation response: {response_text}")
                    
                    # 解析评估结果
                    evaluation_data = self._parse_evaluation_response(response_text)
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_info("Manager evaluation parsing successful")
                    break  # 成功，跳出重试循环
                    
                else:
                    error_msg = evaluation_result.get('error', 'Unknown error')
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_error(RuntimeError(f"Manager evaluation LLM call failed: {error_msg}"), "MANAGER_EVALUATION")
                    
                    if attempt == max_retries - 1:  # 最后一次重试
                        raise RuntimeError(f"Manager evaluation failed after {max_retries} attempts: {error_msg}")
                        
            except Exception as e:
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_error(e, f"MANAGER_EVALUATION_ATTEMPT_{attempt + 1}")
                
                if attempt == max_retries - 1:  # 最后一次重试
                    raise RuntimeError(f"Manager evaluation failed after {max_retries} attempts: {str(e)}")
        
        # 2. 程序判断任务完成状态
        task_complete = evaluation_data['work_satisfaction'] >= self.task_completion_threshold
        
        # ====== 第二次LLM调用：反馈阶段 ======
        # 构建完整的事件上下文信息
        if event_info:
            event_context = f"""Event Content: {event_info.get('content', 'No event')}
Event Category: {event_info.get('category', 'NONE')}
Pressure Level: {event_info.get('pressure_level', 'NORMAL')}
Event Name: {event_info.get('name', 'NO_EVENT')}"""
        else:
            event_context = "No pressure event"
        
        feedback_context = f"""{self.feedback_prompt}

=== YOUR EVALUATION REASONING ===
{evaluation_data['evaluation_reasoning']}

=== TASK CONTEXT ===
Task: {task_description}
{event_context}

=== LLM RESPONSE ===
——————————————————————————————————————————————————————————————
{llm_response}
——————————————————————————————————————————————————————————————

Based on your evaluation reasoning above, provide feedback to the LLM."""

        # 记录feedback context到logger
        if hasattr(self, '_logger') and self._logger:
            self._logger.log_info("=== FEEDBACK CONTEXT ===")
            self._logger.log_info("=== FEEDBACK CONTEXT (Length: {} chars) ===".format(len(feedback_context)))
            self._logger.log_info(feedback_context)
        
        # 第二次LLM调用
        feedback_data = None
        
        for attempt in range(max_retries):
            try:
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_info(f"Manager feedback attempt {attempt + 1}/{max_retries}")
                
                feedback_result = self.llm_client.complete_chat(
                    messages=[{"role": "user", "content": feedback_context}],
                    model=self.model_name,
                    max_tokens=self.llm_client.model_limits.max_output_tokens,
                    temperature=None,
                    caller="MANAGER_FEEDBACK"
                )
                
                if feedback_result.get('success'):
                    response_text = feedback_result['content']
                    
                    # 记录原始输入输出
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_manager_feedback_raw(feedback_context, response_text)
                        if len(response_text) > 500:
                            self._logger.log_info(f"Manager feedback response is long ({len(response_text)} chars). Full content:")
                        self._logger.log_info(f"Manager feedback response: {response_text}")
                    
                    # 解析反馈结果
                    feedback_data = self._parse_feedback_response(response_text)
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_info("Manager feedback parsing successful")
                    break  # 成功，跳出重试循环
                    
                else:
                    error_msg = feedback_result.get('error', 'Unknown error')
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_error(RuntimeError(f"Manager feedback LLM call failed: {error_msg}"), "MANAGER_FEEDBACK")
                    
                    if attempt == max_retries - 1:  # 最后一次重试
                        raise RuntimeError(f"Manager feedback failed after {max_retries} attempts: {error_msg}")
                        
            except Exception as e:
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_error(e, f"MANAGER_FEEDBACK_ATTEMPT_{attempt + 1}")
                
                if attempt == max_retries - 1:  # 最后一次重试
                    raise RuntimeError(f"Manager feedback failed after {max_retries} attempts: {str(e)}")
        
        # 3. 更新状态
        previous_state = self.current_state.copy()
        self.current_state['trust_level'] = evaluation_data['trust_level']
        self.current_state['work_satisfaction'] = evaluation_data['work_satisfaction']
        self.current_state['relational_valence'] = evaluation_data['relational_valence']
        
        # 4. 添加到历史记录
        state_changes = {
            'previous_state': previous_state,
            'new_state': self.current_state.copy(),
            'task_complete': task_complete,
            'evaluation_reasoning': evaluation_data['evaluation_reasoning'],
            'feedback_reasoning': feedback_data['feedback_reasoning']
        }
        
        # 使用新的history.add_interaction_summary方法
        self.history.add_interaction_summary(
            task_id=task_description,
            round_num=1,  # 简化处理
            task_description=task_description,
            event_info=event_info,  # 传递完整的事件信息
            llm_response=llm_response,  # 完整的LLM响应，不截断
            evaluation_reasoning=evaluation_data['evaluation_reasoning'],
            previous_state=previous_state,
            new_state=self.current_state.copy(),
            feedback_reasoning=feedback_data['feedback_reasoning'],
            feedback=feedback_data['feedback'],
            task_complete=task_complete
        )
        
        # 5. 返回完整结果
        return {
            'evaluation_reasoning': evaluation_data['evaluation_reasoning'],
            'trust_level': evaluation_data['trust_level'],
            'work_satisfaction': evaluation_data['work_satisfaction'],
            'relational_valence': evaluation_data['relational_valence'],
            'task_complete': task_complete,
            'feedback_reasoning': feedback_data['feedback_reasoning'],
            'feedback': feedback_data['feedback'],
            'previous_state': previous_state,
            'new_state': self.current_state.copy(),
            'tokens_used': (evaluation_result.get('tokens_used', 0) + feedback_result.get('tokens_used', 0)),
            'context_size': len(evaluation_context) + len(feedback_context)
        }
    
    def _parse_evaluation_response(self, response_text: str) -> Dict[str, Any]:
        """解析第一次LLM调用的评估响应"""
        lines = response_text.strip().split('\n')
        
        result = {}
        evaluation_reasoning_lines = []
        in_evaluation_reasoning = False
        
        for line in lines:
            line = line.strip()
            
            # 清理line中的Markdown格式
            clean_line = line.replace('**', '').strip()
            
            # 解析评估推理
            if clean_line.startswith('EVALUATION_REASONING:'):
                in_evaluation_reasoning = True
                reasoning_content = clean_line.split(':', 1)[1].strip()
                if reasoning_content:
                    evaluation_reasoning_lines.append(reasoning_content)
            elif in_evaluation_reasoning and line and not any(line.replace('**', '').strip().startswith(field + ':') for field in ['TRUST_LEVEL', 'WORK_SATISFACTION', 'RELATIONAL_VALENCE']):
                evaluation_reasoning_lines.append(line)
            
            # 解析信任度
            elif clean_line.startswith('TRUST_LEVEL:'):
                in_evaluation_reasoning = False
                try:
                    value = float(clean_line.split(':', 1)[1].strip())
                    result['trust_level'] = max(-1.0, min(1.0, value))
                except ValueError:
                    raise RuntimeError(f"Invalid TRUST_LEVEL format: {clean_line}")
            
            # 解析工作满意度
            elif clean_line.startswith('WORK_SATISFACTION:'):
                try:
                    value = float(clean_line.split(':', 1)[1].strip())
                    result['work_satisfaction'] = max(-1.0, min(1.0, value))
                except ValueError:
                    raise RuntimeError(f"Invalid WORK_SATISFACTION format: {clean_line}")
            
            # 解析关系质量
            elif clean_line.startswith('RELATIONAL_VALENCE:'):
                try:
                    value = float(clean_line.split(':', 1)[1].strip())
                    result['relational_valence'] = max(-1.0, min(1.0, value))
                except ValueError:
                    raise RuntimeError(f"Invalid RELATIONAL_VALENCE format: {clean_line}")
        
        # 验证所有必需字段都存在
        required_fields = ['trust_level', 'work_satisfaction', 'relational_valence']
        missing_fields = [f for f in required_fields if f not in result]
        
        if missing_fields:
            raise RuntimeError(f"Missing evaluation fields: {missing_fields}")
        
        if not evaluation_reasoning_lines:
            raise RuntimeError("Missing EVALUATION_REASONING field in LLM response")
        
        result['evaluation_reasoning'] = ' '.join(evaluation_reasoning_lines)
        
        return result
    
    def _parse_feedback_response(self, response_text: str) -> Dict[str, Any]:
        """解析第二次LLM调用的反馈响应"""
        lines = response_text.strip().split('\n')
        
        result = {}
        feedback_reasoning_lines = []
        feedback_lines = []
        in_feedback_reasoning = False
        in_feedback = False
        
        for line in lines:
            line = line.strip()
            
            # 清理line中的Markdown格式
            clean_line = line.replace('**', '').strip()
            
            # 解析反馈推理
            if clean_line.startswith('FEEDBACK_REASONING:'):
                in_feedback_reasoning = True
                in_feedback = False
                reasoning_content = clean_line.split(':', 1)[1].strip()
                if reasoning_content:
                    feedback_reasoning_lines.append(reasoning_content)
            elif in_feedback_reasoning and line and not (line.replace('**', '').strip().startswith('FEEDBACK:')):
                feedback_reasoning_lines.append(line)
            
            # 解析反馈内容
            elif clean_line.startswith('FEEDBACK:'):
                in_feedback_reasoning = False
                in_feedback = True
                feedback_content = clean_line.split(':', 1)[1].strip()
                if feedback_content:
                    feedback_lines.append(feedback_content)
            elif in_feedback and line:
                feedback_lines.append(line)
        
        # 验证必需字段
        if not feedback_reasoning_lines:
            raise RuntimeError("Missing FEEDBACK_REASONING field in LLM response")
        
        if not feedback_lines:
            raise RuntimeError("Missing FEEDBACK field in LLM response")
        
        result['feedback_reasoning'] = ' '.join(feedback_reasoning_lines)
        result['feedback'] = ' '.join(feedback_lines)
        
        return result
    
    def get_current_state(self) -> Dict[str, float]:
        """获取当前状态"""
        return self.current_state.copy()