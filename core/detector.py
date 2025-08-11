# detector.py
# 简化的Detector系统 - 只保留批量分析功能
# 移除了所有未使用的实时检测代码和rubrics_balanced依赖

import time
from typing import Dict, Any, List
from .Unified_LLM_Handler import UnifiedLLMHandler
from .detector_rubrics import SEQUENCE_ANALYSIS_TEMPLATE, BASE_DETECTION_PROMPT

class DeceptionDetector:
    """
    简化的LLM-as-Detector系统 - 只进行批量序列分析
    移除了所有未使用的实时检测功能
    """
    
    def __init__(self, azure_api_key: str, azure_endpoint: str, azure_deployment: str, model_name: str, max_retries: int, max_tokens: int, api_version: str):
        """Initialize the Batch DeceptionDetector"""
        self.azure_api_key = azure_api_key
        self.azure_endpoint = azure_endpoint
        self.azure_deployment = azure_deployment
        self.model_name = model_name
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.api_version = api_version
        
        # 初始化LLM客户端
        self.llm_client = UnifiedLLMHandler(
            azure_api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment,
            default_model=model_name,
            max_retries=max_retries,
            retry_delay=2.0,
            timeout=300,
            enable_continuation=True,
            api_version=api_version
        )
        
        # 确定模型的context限制
        model_type = self.llm_client._detect_model_type(model_name)
        self.context_limit = self.llm_client.model_limits.context_window

    def analyze_interaction_sequence(self, interaction_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量分析交互序列 - 每个interaction都基于完整序列进行分析
        
        Args:
            interaction_records: 完整的交互记录列表
            
        Returns:
            每个interaction的分析结果列表
        """
        print(f"\n[DETECTOR] Starting batch analysis of {len(interaction_records)} interactions")
        
        results = []
        
        for i, current_interaction in enumerate(interaction_records):
            print(f"\n[DETECTOR] Analyzing interaction {i+1}/{len(interaction_records)}: {current_interaction['task_id']} Round {current_interaction['round']}")
            
            # 构建完整背景上下文
            background_context = self._build_full_sequence_context(interaction_records, current_interaction)
            
            # 构建当前分析的prompt
            analysis_prompt = self._build_batch_analysis_prompt(current_interaction, background_context)
            
            # 检查context大小
            estimated_tokens = self.llm_client.estimate_tokens(analysis_prompt)
            print(f"[DETECTOR] Context size: {estimated_tokens} tokens")
            
            if estimated_tokens > self.context_limit:
                raise RuntimeError(
                    f"Context overflow! Estimated tokens: {estimated_tokens}, "
                    f"Model limit: {self.context_limit}. Cannot proceed with batch analysis."
                )
            
            # 调用LLM进行分析
            try:
                llm_result = self.llm_client.complete_chat(
                    messages=[{"role": "user", "content": analysis_prompt}],
                    model=self.llm_client.default_model,
                    max_tokens=self.llm_client.model_limits.max_output_tokens,  # 拉满
                    temperature=None,  # 使用OpenAI默认值
                    system_role=None,
                    require_complete_response=True
                )
                
                if not llm_result['success']:
                    raise RuntimeError(f"LLM call failed: {llm_result.get('error', 'Unknown error')}")
                
                # 解析结果
                analysis_result = self._parse_batch_analysis_response(llm_result['content'])
                
                # 添加元信息
                analysis_result.update({
                    'task_id': current_interaction['task_id'],
                    'round': current_interaction['round'],
                    'tokens_used': llm_result.get('tokens_used', 0),
                    'context_size': estimated_tokens
                })
                
                results.append(analysis_result)
                print(f"[DETECTOR] Analysis completed: deception_detected={analysis_result['deception_detected']}")
                
            except Exception as e:
                print(f"[DETECTOR] Analysis failed for interaction {i+1}: {e}")
                raise RuntimeError(f"Batch analysis failed at interaction {i+1}: {str(e)}")
        
        print(f"\n[DETECTOR] Batch analysis completed. {len(results)} interactions analyzed.")
        return results
    
    def _build_full_sequence_context(self, all_interactions: List[Dict[str, Any]], current_interaction: Dict[str, Any]) -> str:
        """构建完整序列的背景上下文"""
        context_parts = []
        
        context_parts.append("=== COMPLETE INTERACTION SEQUENCE ===")
        context_parts.append(f"Total interactions in sequence: {len(all_interactions)}")
        context_parts.append("")
        
        for i, interaction in enumerate(all_interactions, 1):
            context_parts.append(f"[{i}] {interaction['task_id']} Round {interaction['round']}")
            context_parts.append(f"Task: {interaction['task_description']}")
            context_parts.append(f"Event: {interaction['event_description']}")
            context_parts.append(f"Agent Response: {interaction['llm_response']}")
            context_parts.append(f"Manager Feedback: {interaction['manager_feedback']}")
            context_parts.append("")
        
        context_parts.append("=== END SEQUENCE ===")
        
        return "\n".join(context_parts)
    
    def _build_batch_analysis_prompt(self, current_interaction: Dict[str, Any], background_context: str) -> str:
        """构建批量分析的prompt"""
        return SEQUENCE_ANALYSIS_TEMPLATE.format(
            task_id=current_interaction['task_id'],
            round_num=current_interaction['round'],
            agent_response=current_interaction['llm_response'],
            manager_feedback=current_interaction['manager_feedback'],
            background_context=background_context,
            base_prompt=BASE_DETECTION_PROMPT
        )
    
    def _parse_batch_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """解析批量分析的LLM响应"""
        lines = response_text.strip().split('\n')
        
        result = {
            'deception_detected': False,
            'intent': [],
            'category': [],
            'severity': 0,
            'confidence_score': 0.0,
            'reasoning': '',
            'evidence': []
        }
        
        evidence_lines = []
        in_evidence = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('DECEPTION_DETECTED:'):
                value_text = line.split(':', 1)[1].strip().lower()
                result['deception_detected'] = value_text in ['true', 'yes', '1']
            
            elif line.startswith('INTENT:'):
                intent_text = line.split(':', 1)[1].strip()
                result['intent'] = [i.strip() for i in intent_text.split(',') if i.strip()]
            
            elif line.startswith('CATEGORY:'):
                category_text = line.split(':', 1)[1].strip()
                result['category'] = [c.strip() for c in category_text.split(',') if c.strip()]
            
            elif line.startswith('SEVERITY:'):
                try:
                    value = int(line.split(':', 1)[1].strip())
                    result['severity'] = max(0, min(4, value))
                except ValueError:
                    result['severity'] = 0
            
            elif line.startswith('CONFIDENCE_SCORE:'):
                try:
                    value = float(line.split(':', 1)[1].strip())
                    result['confidence_score'] = max(0.0, min(1.0, value))
                except ValueError:
                    result['confidence_score'] = 0.0
            
            elif line.startswith('REASONING:'):
                result['reasoning'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('EVIDENCE:'):
                in_evidence = True
                evidence_content = line.split(':', 1)[1].strip()
                if evidence_content:
                    evidence_lines.append(evidence_content)
            
            elif in_evidence and line.startswith('- '):
                evidence_lines.append(line[2:])  # 移除"- "前缀
        
        result['evidence'] = evidence_lines
        
        return result

    def _create_error_result(self, task_sequence_num: int, task_id: str, error_message: str) -> Dict[str, Any]:
        """创建错误结果字典 - 简化版本，只包含批量分析需要的字段"""
        return {
            'deception_detected': False,
            'intent': [],
            'category': [],
            'severity': 0,
            'confidence_score': 0.0,
            'reasoning': f"Error during evaluation: {error_message}",
            'evidence': [],
            'task_id': task_id,
            'error': True,
            'error_message': error_message
        }

    def get_llm_statistics(self) -> Dict[str, Any]:
        """Get LLM client statistics"""
        return self.llm_client.get_statistics()
