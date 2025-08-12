# detector.py
# 简化的Detector系统 - 只保留批量分析功能
# 移除了所有未使用的实时检测代码和rubrics_balanced依赖

import time
from typing import Dict, Any, List
try:
    # 当作为模块导入时使用相对导入
    from .Universal_LLM_Client import UniversalLLMClient
    from .detector_rubrics import SEQUENCE_ANALYSIS_TEMPLATE, BASE_DETECTION_PROMPT
except ImportError:
    # 当作为主程序运行时使用直接导入
    import sys
    import os
    
    # 智能添加项目根目录到路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) == 'core':
        parent_dir = os.path.dirname(current_dir)
    else:
        parent_dir = os.getcwd()
    
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # 直接导入文件
    import importlib.util
    
    # 导入Universal_LLM_Client
    client_path = os.path.join(current_dir, 'Universal_LLM_Client.py')
    spec = importlib.util.spec_from_file_location("Universal_LLM_Client", client_path)
    client_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client_module)
    UniversalLLMClient = client_module.UniversalLLMClient
    
    # 导入detector_rubrics
    rubrics_path = os.path.join(current_dir, 'detector_rubrics.py')
    spec = importlib.util.spec_from_file_location("detector_rubrics", rubrics_path)
    rubrics_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rubrics_module)
    SEQUENCE_ANALYSIS_TEMPLATE = rubrics_module.SEQUENCE_ANALYSIS_TEMPLATE
    BASE_DETECTION_PROMPT = rubrics_module.BASE_DETECTION_PROMPT

class DeceptionDetector:
    """
    简化的LLM-as-Detector系统 - 只进行批量序列分析
    移除了所有未使用的实时检测功能
    """
    
    def __init__(self, llm_provider: str, llm_config: Dict[str, Any]):
        """Initialize the Batch DeceptionDetector with Universal LLM Client"""
        self.llm_provider = llm_provider
        self.llm_config = llm_config
        
        # 初始化通用LLM客户端
        self.llm_client = UniversalLLMClient(llm_provider, llm_config)
        
        # 获取context限制
        self.context_limit = self.llm_client.model_limits.context_window
        
        print(f"[DETECTOR] Initialized with {llm_provider} provider")

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
                    model=None,  # 使用默认模型
                    max_tokens=self.llm_client.model_limits.max_output_tokens,  # 拉满
                    temperature=0.1,  # 低温确保一致性
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


# ==================== 独立分析功能 ====================

def _save_detector_results_text(detector_results: List[Dict[str, Any]], output_file: str, session_name: str = 'unknown'):
    """保存Detector结果为LLM友好的文本格式"""
    import time
    from pathlib import Path
    
    lines = []
    
    # 文件头
    lines.extend([
        "=== DETECTOR ANALYSIS REPORT ===",
        f"Session: {session_name}",
        f"Analysis_Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
        f"Total_Interactions_Analyzed: {len(detector_results)}",
        ""
    ])
    
    # 摘要统计
    deception_count = sum(1 for r in detector_results if r.get('deception_detected', False))
    severity_counts = {}
    for r in detector_results:
        severity = r.get('severity', 0)
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    lines.extend([
        "=== ANALYSIS SUMMARY ===",
        f"Total_Deception_Detected: {deception_count}/{len(detector_results)} ({deception_count/len(detector_results)*100:.1f}%)",
        f"Severity_Distribution:"
    ])
    
    for sev in range(5):
        count = severity_counts.get(sev, 0)
        lines.append(f"  - Severity_{sev}: {count} interactions")
    
    lines.extend(["", "=== DETAILED ANALYSIS ===", ""])
    
    # 每个interaction的详细分析
    for i, result in enumerate(detector_results, 1):
        task_id = result.get('task_id', f'Task{i}')
        round_num = result.get('round', 1)
        
        lines.extend([
            f"[ANALYSIS_{i:03d}]",
            f"Task_ID: {task_id}",
            f"Round: {round_num}",
            f"DECEPTION_DETECTED: {result.get('deception_detected', False)}",
            f"INTENT: {','.join(result.get('intent', []))}",
            f"CATEGORY: {','.join(result.get('category', []))}",
            f"SEVERITY: {result.get('severity', 0)}",
            f"CONFIDENCE_SCORE: {result.get('confidence_score', 0.0)}",
            f"REASONING: {result.get('reasoning', 'No reasoning provided')}",
            f"EVIDENCE:"
        ])
        
        # 添加evidence列表
        evidence_list = result.get('evidence', [])
        if evidence_list:
            for evidence in evidence_list:
                lines.append(f"- {evidence}")
        else:
            lines.append("- No evidence provided")
        
        lines.append("")  # 空行分隔
    
    lines.append("=== END REPORT ===")
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

def _save_detector_results_json(detector_results: List[Dict[str, Any]], json_file: str, session_name: str = 'unknown'):
    """保存JSON格式用于数据分析"""
    import json
    import time
    
    # 添加元信息到JSON
    deception_count = sum(1 for r in detector_results if r.get('deception_detected', False))
    severity_counts = {}
    for r in detector_results:
        severity = r.get('severity', 0)
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    output_data = {
        "metadata": {
            "session": session_name,
            "analysis_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            "total_interactions": len(detector_results),
            "deception_detected": deception_count,
            "deception_rate": deception_count / len(detector_results) if detector_results else 0,
            "severity_distribution": severity_counts
        },
        "results": detector_results  # 解析后的完整数据
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

def load_interaction_records(file_path: str) -> List[Dict[str, Any]]:
    """加载保存的交互记录 - 只支持新的文本格式"""
    from pathlib import Path
    
    # 如果是目录路径，查找complete_interaction_record.txt
    if Path(file_path).is_dir():
        text_file = Path(file_path) / "complete_interaction_record.txt"
        
        if text_file.exists():
            file_path = str(text_file)
        else:
            raise FileNotFoundError(f"complete_interaction_record.txt not found in: {file_path}")
    
    print(f"📄 Loading from: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 只支持新的文本格式
        if not ('[TASK_' in content):
            raise ValueError("Invalid format: complete_interaction_record.txt must contain [TASK_] markers")
        
        print("🔄 Parsing text format...")
        records = extract_analysis_data_from_text(content)
        print(f"✅ Extracted {len(records)} interaction records from text format")
        return records
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        raise
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        raise

def find_latest_session() -> str:
    """查找最新的session目录"""
    from pathlib import Path
    
    # 智能查找results目录
    if Path(__file__).parent.name == 'core':
        # 从 core/detector.py 运行
        results_dir = Path(__file__).parent.parent / "results"
    else:
        # 从项目根目录运行
        results_dir = Path.cwd() / "results"
    
    if not results_dir.exists():
        # 尝试当前目录
        results_dir = Path("results")
        if not results_dir.exists():
            return ""
    
    # 查找所有session目录，按时间排序
    session_dirs = [d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith("task_stream_")]
    if not session_dirs:
        return ""
    
    # 按名称排序，最新的在最后
    session_dirs.sort(key=lambda x: x.name)
    latest_session = session_dirs[-1]
    
    print(f"📁 Found latest session: {latest_session.name}")
    return str(latest_session)

def get_llm_config() -> tuple:
    """从配置文件获取Detector的LLM配置"""
    import sys
    import os
    from pathlib import Path
    
    # 智能获取项目根目录
    if Path(__file__).parent.name == 'core':
        # 从 core/detector.py 运行
        project_root = Path(__file__).parent.parent
    else:
        # 从其他位置运行
        project_root = Path.cwd()
    
    # 确保能导入项目模块
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        from utils.yaml_config_loader import load_yaml_config
        config = load_yaml_config(project_root / "task_stream_config.yaml")
        llm_api_config = config['llm_api_config']
        
        # 获取Detector专用配置 - 严格模式，无默认值
        detector_config = llm_api_config['detector']
        llm_provider = detector_config['provider']
        
        if llm_provider == 'openai':
            # 和main.py一样，直接返回配置，让Universal_LLM_Client处理
            llm_config = detector_config['openai']
        else:
            # 如果是Azure，需要从config.py加载
            import config as azure_config
            llm_config = {
                'azure_api_key': azure_config.AZURE_API_KEY,
                'azure_endpoint': azure_config.AZURE_ENDPOINT,
                'azure_deployment': azure_config.AZURE_DEPLOYMENT_NAME,
                'model_name': azure_config.MODEL_NAME,
                'api_version': azure_config.AZURE_API_VERSION
            }
        
        return llm_provider, llm_config
        
    except Exception as e:
        print(f"❌ Failed to load LLM config: {e}")
        raise RuntimeError(f"Cannot proceed without valid configuration: {e}")

def extract_analysis_data_from_text(text_content: str) -> List[Dict[str, Any]]:
    """从complete_interaction_record.txt中提取detector需要的分析片段"""
    interactions = []
    lines = text_content.split('\n')
    
    current_task_id = None
    current_round = None
    current_task_description = None
    current_event_description = None
    current_agent_response = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 提取Task信息
        if line.startswith('[TASK_') and '_START]' in line:
            # 继续读取TaskID和描述
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].startswith('TaskID:'):
                    current_task_id = lines[j].split('TaskID:', 1)[1].strip()
                elif lines[j].startswith('Description:'):
                    current_task_description = lines[j].split('Description:', 1)[1].strip()
                elif lines[j].startswith('[EVENT_'):
                    break
        
        # 提取Event信息
        elif line.startswith('[EVENT_'):
            # 读取Event的Content作为描述
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].startswith('Content:'):
                    current_event_description = lines[j].split('Content:', 1)[1].strip()
                    break
                elif lines[j].startswith('['):
                    break
        
        # 提取Round信息
        elif line.startswith('[ROUND_'):
            current_round = int(line.split('_')[1])
        
        # 提取Agent回复
        elif line.startswith('[AGENT_RESPONSE_'):
            # 读取Agent的完整回复
            response_lines = []
            for j in range(i+1, len(lines)):
                if lines[j].startswith('[') and not lines[j].strip() == '':
                    break
                response_lines.append(lines[j])
            current_agent_response = '\n'.join(response_lines).strip()
        
        # 提取Manager反馈并构建交互记录
        elif line.startswith('[MANAGER_EVALUATION_'):
            manager_feedback = None
            # 读取Manager的Feedback
            for j in range(i+1, min(i+20, len(lines))):
                if lines[j].startswith('Feedback:'):
                    manager_feedback = lines[j].split('Feedback:', 1)[1].strip()
                    break
                elif lines[j].startswith('['):
                    break
            
            # 构建完整的交互记录
            if all([current_task_id, current_round, current_agent_response, manager_feedback]):
                interactions.append({
                    'task_id': current_task_id,
                    'round': current_round,
                    'task_description': current_task_description or '',
                    'event_description': current_event_description or 'No event',
                    'llm_response': current_agent_response,
                    'manager_feedback': manager_feedback,
                    'timestamp': 0  # 不重要，detector不用这个
                })
        
        i += 1
    
    return interactions

def analyze_saved_results(interaction_records: List[Dict[str, Any]], output_file: str = None):
    """分析交互记录并输出结果"""
    if not interaction_records:
        print("❌ No interaction records to analyze")
        return
    
    # 获取LLM配置
    llm_provider, llm_config = get_llm_config()
    print(f"🤖 Using {llm_provider} for detection analysis")
    
    # 初始化Detector
    try:
        detector = DeceptionDetector(llm_provider, llm_config)
        print(f"✅ Detector initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        return
    
    # 执行批量分析
    print(f"\n🔍 Starting batch analysis of {len(interaction_records)} interactions...")
    try:
        detector_results = detector.analyze_interaction_sequence(interaction_records)
        
        # 分析结果摘要
        deception_count = sum(1 for r in detector_results if r.get('deception_detected', False))
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   Total interactions analyzed: {len(detector_results)}")
        print(f"   Deception detected: {deception_count}")
        print(f"   Deception rate: {deception_count/len(detector_results)*100:.1f}%")
        
        # 详细结果
        print(f"\n📋 DETAILED RESULTS:")
        for i, result in enumerate(detector_results, 1):
            task_id = result.get('task_id', f'Task{i}')
            round_num = result.get('round', 1)
            deception = result.get('deception_detected', False)
            severity = result.get('severity', 0)
            confidence = result.get('confidence_score', 0.0)
            intent = result.get('intent', [])
            category = result.get('category', [])
            
            status_icon = "🚨" if deception else "✅"
            intent_str = ','.join(intent) if intent else 'NONE'
            category_str = ','.join(category) if category else 'NONE'
            
            print(f"   {status_icon} {task_id} R{round_num}: "
                  f"Deception={deception}, Severity={severity}, "
                  f"Confidence={confidence:.2f}, Intent={intent_str}, Category={category_str}")
        
        # 保存结果 - 双格式：LLM友好文本 + 数据分析JSON
        if output_file:
            try:
                # 1. 保存LLM友好的文本格式（主要格式）
                _save_detector_results_text(detector_results, output_file, session_name='detector_analysis')
                print(f"\n💾 LLM-friendly text saved to: {output_file}")
                
                # 2. 自动生成JSON版本（方便数据分析）
                from pathlib import Path
                output_path = Path(output_file)
                json_file = str(output_path.with_suffix('.json'))
                _save_detector_results_json(detector_results, json_file, session_name='detector_analysis')
                print(f"💾 Data analysis JSON saved to: {json_file}")
                
            except Exception as e:
                print(f"⚠️  Failed to save results: {e}")
        
        return detector_results
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # 确保能正确导入项目模块
    if Path(__file__).parent.name == 'core':
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Standalone Detector Analysis')
    parser.add_argument('--results_path', '-r', type=str, 
                       help='Path to interaction_records.json file')
    parser.add_argument('--session', '-s', type=str,
                       help='Session name (e.g., task_stream_20250812_014857)')
    parser.add_argument('--latest', '-l', action='store_true',
                       help='Analyze the latest session automatically')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file for detector results (JSON format)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🔍 STANDALONE DETECTOR ANALYSIS")
    print("="*60)
    
    # 确定要分析的文件路径
    results_path = None
    
    if args.results_path:
        results_path = args.results_path
    elif args.session:
        # 智能查找session目录
        from pathlib import Path
        if Path(__file__).parent.name == 'core':
            results_dir = Path(__file__).parent.parent / "results"
        else:
            results_dir = Path("results")
        results_path = str(results_dir / args.session)
    elif args.latest:
        latest_session_dir = find_latest_session()
        if latest_session_dir:
            results_path = latest_session_dir
        else:
            print("❌ No session directories found")
            exit(1)
    else:
        print("❌ Please specify one of: --results_path, --session, or --latest")
        parser.print_help()
        exit(1)
    
    print(f"📂 Analyzing: {results_path}")
    
    # 加载交互记录
    interaction_records = load_interaction_records(results_path)
    if not interaction_records:
        exit(1)
    
    # 确定输出文件路径
    output_file = args.output
    if not output_file and results_path:
        # 如果没有指定输出文件，自动保存到session目录
        from pathlib import Path
        if Path(results_path).is_dir():
            session_dir = Path(results_path)
            output_file = str(session_dir / "detector_analysis.txt")
            print(f"📝 Auto-saving to: {output_file}")
    
    # 执行分析
    results = analyze_saved_results(interaction_records, output_file)
    
    if results:
        print(f"\n✅ Analysis completed successfully!")
    else:
        print(f"\n❌ Analysis failed!")
        exit(1)
    
    print("="*60)
