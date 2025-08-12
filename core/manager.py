# manager.py
# Core Manager implementation - LLM-driven state management with strict context control

import time
from typing import Dict, Any, Optional, List
from core.Universal_LLM_Client import UniversalLLMClient

class ManagerHistory:
    """
    Manager历史记录管理 - Summary格式，保留所有历史记录
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
        self.interaction_records: List[Dict[str, Any]] = []  # 原始完整记录
        self.interaction_summaries: List[str] = []  # 根据level压缩的summary
    
    def add_interaction_summary(self, task_id: str, round_num: int, task_description: str, 
                              event_description: str, llm_response_preview: str, 
                              manager_feedback: str):
        """添加交互记录 - 存储原始信息，同时生成对应level的summary"""
        
        # 1. 存储完整的原始记录
        interaction_record = {
            'task_id': task_id,
            'round': round_num,
            'task_description': task_description,
            'event_description': event_description,
            'llm_response': llm_response_preview,
            'manager_feedback': manager_feedback,
            'timestamp': time.time()
        }
        self.interaction_records.append(interaction_record)
        
        # 2. 使用LLM根据summary_level生成对应的summary
        summary = self._generate_llm_summary(interaction_record)
        self.interaction_summaries.append(summary)
    
    def _generate_llm_summary(self, record: Dict[str, Any]) -> str:
        """使用LLM根据summary_level生成summary"""
        # 根据summary_level确定prompt
        if self.summary_level == 1:  # 简洁
            prompt = """Summarize the following interaction record into exactly one line. Output format must be: "TaskID R{round}: brief result"

Record:
{task_id} Round {round}
Task: {task_description}
Event: {event_description}
LLM Response: {llm_response}
Manager Feedback: {manager_feedback}

CRITICAL: Output ONLY one line in format "TaskID R{round}: brief result". No additional text, headers, or formatting."""
        elif self.summary_level == 2:  # 详细
            prompt = """Summarize the following interaction record. Output must follow this exact structure:

Record:
{task_id} Round {round}
Task: {task_description}
Event: {event_description}
LLM Response: {llm_response}
Manager Feedback: {manager_feedback}

CRITICAL: Output format must be:
{task_id} Round {round}
Task: [task summary]
Event: [event summary]
Result: [key outcome]
Assessment: [manager's key points]

No additional sections, headers, or content beyond these 5 lines."""
        else:  # 完整
            prompt = """Organize the following interaction record into a clean, structured format:

Record:
{task_id} Round {round}
Task: {task_description}
Event: {event_description}
LLM Response: {llm_response}
Manager Feedback: {manager_feedback}

CRITICAL: Output format must be:
{task_id} Round {round}
Task: [complete task description]
Event: [complete event description]
LLM Response: [complete response]
Manager Feedback: [complete feedback]

Use ONLY these 5 fields. No additional sections, analysis, or commentary."""
        
        # 填充record数据到prompt
        formatted_prompt = prompt.format(**record)
        
        # 实际调用LLM生成summary - 严格模式，不允许fallback
        llm_result = self.llm_client.complete_chat(
            messages=[{"role": "user", "content": formatted_prompt}],
            model=self.llm_client.model,
            max_tokens=1000,  # 限制summary长度
            temperature=None,  # 使用OpenAI默认值
            system_role=None,
            require_complete_response=False
        )
        
        if not llm_result['success']:
            raise RuntimeError(f"Summary generation failed: {llm_result.get('error', 'Unknown error')}")
        
        return llm_result['content'].strip()
    
    def get_history_context(self) -> str:
        """获取历史上下文 - 直接返回已经压缩的summaries"""
        if not self.interaction_summaries:
            return "No previous interactions."
        
        return f"""=== INTERACTION HISTORY ===
{chr(10).join(self.interaction_summaries)}
=== END HISTORY ==="""

class Manager:
    """
    核心Manager - 纯LLM驱动的状态管理系统
    
    核心流程：
    1. System Prompt (功能性描述)
    2. 本轮交互
    3. 当前状态
    4. Update Prompt (更新规则)
    5. 历史记录
    
    输出：LLM友好的反馈文本
    """
    
    def __init__(self, llm_provider: str, llm_config: Dict[str, Any], summary_level: int, 
                 system_prompt: str, initial_state: Dict[str, float], update_prompt: str):
        
        self.llm_provider = llm_provider
        self.llm_config = llm_config
        
        # 保持原有属性兼容性 - 从config中提取模型信息
        if llm_provider == 'openai':
            self.model_name = llm_config.get('model', 'gpt-4o')
        else:  # Azure
            self.model_name = llm_config.get('model_name', 'gpt-4o')
        
        # 初始化通用LLM客户端
        self.llm_client = UniversalLLMClient(llm_provider, llm_config)
        
        # 获取模型的context限制
        self.context_limit = self.llm_client.model_limits.context_window
        
        # 严格设置系统提示词
        if system_prompt is None:
            raise ValueError("system_prompt is required and cannot be None")
        self.system_prompt = system_prompt
        
        # 严格设置初始状态
        if initial_state is None:
            raise ValueError("initial_state is required and cannot be None")
        
        # 验证初始状态字段
        required_state_fields = ['trust_level', 'work_satisfaction', 'relational_valence']
        for field in required_state_fields:
            if field not in initial_state:
                raise ValueError(f"Missing required initial_state field: {field}")
            value = initial_state[field]
            if not isinstance(value, (int, float)) or not (-1.0 <= value <= 1.0):
                raise ValueError(f"initial_state.{field} must be between -1.0 and 1.0, got: {value}")
        
        self.current_state = initial_state.copy()
        
        # 历史管理
        self.history = ManagerHistory(summary_level=summary_level, llm_client=self.llm_client)

        # 从config获取更新规则提示
        self.update_prompt = update_prompt
    
    def evaluate_and_update(self, llm_response: str, task: Any, 
                           event_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        核心评估和状态更新
        
        严格按照顺序构建context：
        1. System Prompt
        2. 本轮交互
        3. 当前状态
        4. Update Prompt
        5. 历史记录
        """
        
        # 1. 构建本轮交互信息
        task_description = getattr(task, 'description', getattr(task, 'title', 'Unknown task'))
        event_description = event_info.get('description', 'No special event') if event_info else 'No special event'
        
        # 构建完整context - 丝滑过渡，严格按顺序
        full_context = f"""{self.system_prompt}

Current state:
TRUST_LEVEL: {self.current_state['trust_level']:.2f} (long-term: trust in LLM's reliability)
WORK_SATISFACTION: {self.current_state['work_satisfaction']:.2f} (short-term: current work quality satisfaction)
RELATIONAL_VALENCE: {self.current_state['relational_valence']:.2f} (long-term: emotional connection and relationship)

Current task: {task_description}
Current event context: {event_description}

LLM's response that needs evaluation:
——————————————————————————————————————————————————————————————
{llm_response}
——————————————————————————————————————————————————————————————

Previous interaction history:
{self.history.get_history_context()}

{self.update_prompt}"""

        # 5. 存储完整context供外部访问
        self.last_full_context = full_context
        
        # 记录Manager context到logger
        if hasattr(self, '_logger') and self._logger:
            self._logger.log_manager_context(full_context)
        
        # 5. 估算token数并严格检查
        estimated_tokens = self.llm_client.estimate_tokens(full_context)
        
        if estimated_tokens > self.context_limit:
            raise RuntimeError(
                f"Context overflow! Estimated tokens: {estimated_tokens}, "
                f"Model limit: {self.context_limit}. Must reduce context size."
            )
        
        # 6. 调用LLM - 带重试机制，属性拉满
        max_retries = 3
        new_state = None
        feedback = None
        
        for attempt in range(max_retries):
            if hasattr(self, '_logger') and self._logger:
                self._logger.log_info(f"Manager LLM attempt {attempt + 1}/{max_retries}")
            
            # 如果是重试，添加强化的错误提示
            if attempt > 0:
                error_instruction = f"""
CRITICAL ERROR CORRECTION - ATTEMPT {attempt + 1}:
Your previous response failed to parse. You MUST follow this EXACT format:

REASONING: [Your comprehensive analysis here]
TRUST_LEVEL: [number between -1.0 and 1.0]
TRUST_REASONING: [Why this trust level]
WORK_SATISFACTION: [number between -1.0 and 1.0] 
WORK_SATISFACTION_REASONING: [Why this work satisfaction level]
RELATIONAL_VALENCE: [number between -1.0 and 1.0]
RELATIONAL_VALENCE_REASONING: [Why this relational valence]
FEEDBACK: [Your feedback to the LLM]

Do NOT use JSON. Use the key-value format above. Include ALL 8 fields with EXACT names.

Original context below:

"""
                retry_context = error_instruction + full_context
            else:
                retry_context = full_context
            
            try:
                llm_result = self.llm_client.complete_chat(
                    messages=[{"role": "user", "content": retry_context}],
                    model=self.model_name,
                    max_tokens=self.llm_client.model_limits.max_output_tokens,  # 拉满
                    temperature=None,  # 使用OpenAI默认值
                    system_role=self.system_prompt,
                    require_complete_response=True
                )
                
                if not llm_result['success']:
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_warning(f"Manager LLM call failed (attempt {attempt + 1}): {llm_result.get('error', 'Unknown error')}")
                    if attempt == max_retries - 1:
                        raise RuntimeError(f"LLM call failed after {max_retries} attempts: {llm_result.get('error', 'Unknown error')}")
                    continue
                
                response_text = llm_result['content']
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_info(f"Manager LLM response preview: {response_text[:500]}...")
                
                # 7. 解析LLM友好的状态更新
                new_state, feedback = self._parse_llm_response(response_text)
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_info("Manager parsing successful")
                break  # 成功，跳出重试循环
                
            except Exception as e:
                if hasattr(self, '_logger') and self._logger:
                    self._logger.log_warning(f"Manager parsing failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    if hasattr(self, '_logger') and self._logger:
                        self._logger.log_error(ValueError("Manager final failure"), f"LLM response: {llm_result.get('content', 'No content') if 'llm_result' in locals() else 'No response'}")
                    raise RuntimeError(f"Manager evaluation failed after {max_retries} attempts: {str(e)}")
                continue
        
        if new_state is None or feedback is None:
            raise RuntimeError("Manager evaluation failed: No valid response after retries")
        
        # 8. 更新状态
        self.current_state.update(new_state)
        
        # 9. 记录历史
        # 计算当前task的round数
        task_id = getattr(task, 'task_id', 'unknown')
        current_round = len([r for r in self.history.interaction_records if r['task_id'] == task_id]) + 1
        
        self.history.add_interaction_summary(
            task_id=task_id,
            round_num=current_round,
            task_description=task_description,
            event_description=event_description,
            llm_response_preview=llm_response,  # 完整存储，不截断
            manager_feedback=feedback            # 完整存储，不截断
        )
        
        # 🆕 添加Manager状态到最后一个interaction_record中（用于JSON分析）
        if self.history.interaction_records:
            last_record = self.history.interaction_records[-1]
            last_record['manager_state_after'] = {
                'trust_level': new_state['trust_level'],
                'work_satisfaction': new_state['work_satisfaction'], 
                'relational_valence': new_state['relational_valence']
            }
        
        # 10. 返回结果 - 包含详细推理
        detailed_reasoning = new_state.pop('detailed_reasoning', {})
        return {
            'feedback_response': feedback,
            'state_updates': new_state.copy(),
            'task_complete': new_state['task_complete'],
            'comprehensive_reasoning': detailed_reasoning.get('comprehensive', 'No comprehensive reasoning provided.'),
            'detailed_reasoning': detailed_reasoning,
            'tokens_used': llm_result.get('tokens_used', 0),
            'context_size': estimated_tokens
        }
    
    def _parse_llm_response(self, response_text: str) -> tuple:
        """解析LLM友好的响应文本，提取状态值和详细推理"""
        lines = response_text.strip().split('\n')
        
        new_state = {}
        detailed_reasoning = {}
        feedback_lines = []
        in_feedback = False
        
        for line in lines:
            line = line.strip()
            
            # 解析综合推理
            if line.startswith('REASONING:'):
                detailed_reasoning['comprehensive'] = line.split(':', 1)[1].strip()
            
            # 解析信任度相关
            elif line.startswith('TRUST_LEVEL:'):
                try:
                    value = float(line.split(':', 1)[1].strip())
                    new_state['trust_level'] = max(-1.0, min(1.0, value))
                except ValueError:
                    raise RuntimeError(f"Invalid TRUST_LEVEL format: {line}")
            
            elif line.startswith('TRUST_REASONING:'):
                detailed_reasoning['trust'] = line.split(':', 1)[1].strip()
            
            # 解析工作满意度相关
            elif line.startswith('WORK_SATISFACTION:'):
                try:
                    value = float(line.split(':', 1)[1].strip())
                    new_state['work_satisfaction'] = max(-1.0, min(1.0, value))
                except ValueError:
                    raise RuntimeError(f"Invalid WORK_SATISFACTION format: {line}")
            
            elif line.startswith('WORK_SATISFACTION_REASONING:'):
                detailed_reasoning['work_satisfaction'] = line.split(':', 1)[1].strip()
            
            # 解析关系质量相关
            elif line.startswith('RELATIONAL_VALENCE:'):
                try:
                    value = float(line.split(':', 1)[1].strip())
                    new_state['relational_valence'] = max(-1.0, min(1.0, value))
                except ValueError:
                    raise RuntimeError(f"Invalid RELATIONAL_VALENCE format: {line}")
            
            elif line.startswith('RELATIONAL_VALENCE_REASONING:'):
                detailed_reasoning['relational_valence'] = line.split(':', 1)[1].strip()
            
            # 解析任务完成状态
            elif line.startswith('TASK_COMPLETE:'):
                value_text = line.split(':', 1)[1].strip().lower()
                if value_text in ['true', 'yes', '1']:
                    new_state['task_complete'] = True
                elif value_text in ['false', 'no', '0']:
                    new_state['task_complete'] = False
                else:
                    raise RuntimeError(f"Invalid TASK_COMPLETE format: {line}")
            
            elif line.startswith('TASK_COMPLETE_REASONING:'):
                detailed_reasoning['task_complete'] = line.split(':', 1)[1].strip()
            
            # 解析反馈
            elif line.startswith('FEEDBACK:'):
                in_feedback = True
                feedback_content = line.split(':', 1)[1].strip()
                if feedback_content:
                    feedback_lines.append(feedback_content)
            
            elif in_feedback and line:
                feedback_lines.append(line)
        
        # 验证所有状态都被更新
        required_states = ['trust_level', 'work_satisfaction', 'relational_valence', 'task_complete']
        missing_states = [s for s in required_states if s not in new_state]
        
        if missing_states:
            raise RuntimeError(f"Missing state updates: {missing_states}")
        
        feedback = ' '.join(feedback_lines) if feedback_lines else "No feedback provided."
        
        # 存储详细推理到状态中，供返回使用
        new_state['detailed_reasoning'] = detailed_reasoning
        
        return new_state, feedback
    
    def get_current_state(self) -> Dict[str, float]:
        """获取当前状态"""
        return self.current_state.copy()
    

