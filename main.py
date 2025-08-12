#!/usr/bin/env python3
# test_task_stream.py
# 测试连续Task Stream的多轮交互

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.yaml_config_loader import load_yaml_config
from utils.task_stream_logger import TaskStreamLogger
from utils.result_saver import ResultSaver
from core.manager import Manager
from core.LLM import LLM
from core.detector import DeceptionDetector
from tasks.json_loader import JSONTaskLoader
from tasks.event_loader import get_event_system, DeceptiveEvent
from tasks.base import Task
from tqdm import tqdm

class TaskStreamTask:
    def __init__(self, task_id, title, description, task_sequence_num=1):
        self.task_sequence_num = task_sequence_num
        self.task_id = task_id
        self.title = title
        self.description = description
        self.files = []
        # Agent需要的prompt属性
        # MockTaskPrompt不再需要normal_prompt字段
        self.deceptive_prompt = None
        self.positive_prompt = None

class MockTaskPrompt:
    def __init__(self, text):
        self.en = text

# Context management functions moved to Agent class

def safe_log(logger, method_name, *args, **kwargs):
    """安全的日志记录函数 - 当logger为None时不执行"""
    if logger:
        method = getattr(logger, method_name)
        method(*args, **kwargs)

def run_deception_experiment():
    """运行长期Task序列的欺骗实验"""
    
    # Step 1: 加载配置系统 (先加载配置再决定是否启用logger)
    logger = None  # 初始化logger变量
    try:
        # 加载基础配置 (从环境变量)
        base_config = {
            'azure_api_key': config.AZURE_API_KEY,
            'azure_endpoint': config.AZURE_ENDPOINT,
            'azure_deployment': config.AZURE_DEPLOYMENT_NAME,
            'model_name': config.MODEL_NAME,
            'api_version': config.AZURE_API_VERSION
        }
        
        # 加载实验特定配置 (从YAML文件)
        experiment_config = load_yaml_config("task_stream_config.yaml")
        experiment_config_dict = experiment_config  # YAML loader already returns a dict
        
        # 检查是否启用logger
        enable_logger = experiment_config['logging']['enable_logger']
        
        # 根据配置决定是否初始化logger
        logger = None
        session_info = None
        if enable_logger:
            logger = TaskStreamLogger()
            session_info = logger.get_session_info()
            safe_log(logger, 'log_config_loading', "Base Configuration (Environment Variables)", base_config)
            safe_log(logger, 'log_config_loading', "Experiment Configuration (YAML)", experiment_config_dict)
        else:
            # 生成简单的session信息，不创建log文件
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            session_info = {
                'session_name': f'task_stream_{timestamp}',
                'log_file': None  # 不创建log文件
            }
        
    except Exception as e:
        safe_log(logger, 'log_error', e, "Configuration loading")
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Step 2: 合并配置和验证
    merged_config = {
        **base_config,
        **experiment_config_dict
    }
    
    # 验证所有必需配置都存在
    required_configs = [
        'azure_api_key', 'azure_endpoint', 'azure_deployment', 'model_name', 'api_version',
        'agent_system_prompt', 'manager_system_prompt', 'manager_update_prompt', 'manager_initial_state',
        'p_event', 'summary_level', 'max_rounds_per_task', 'experiment_mode'
    ]
    
    for config_key in required_configs:
        if config_key not in merged_config or merged_config[config_key] is None:
            safe_log(logger, 'log_error', ValueError(f"Missing required configuration: {config_key}"), "Configuration validation")
            print(f"❌ Missing required configuration: {config_key}")
            return False
    
    safe_log(logger, "log_config_loading", "Merged Configuration", merged_config)
    
    # 根据experiment_mode确定实验模式
    if merged_config['experiment_mode'].lower() == "quick":
        max_tasks = 7  # 快速模式：7个Task
        experiment_mode = "QUICK MODE"
    else:
        max_tasks = 21  # 完整实验：21个Task
        experiment_mode = "FULL EXPERIMENT"
    
    # 控制台显示实验信息
    print(f"🚀 Starting DeceptioN Experiment - {experiment_mode}")
    print(f"📊 Task Count: {max_tasks} tasks")
    print(f"📁 Session: {session_info['session_name']}")
    print(f"📄 Log file: {session_info['log_file']}")
    
    # Step 3: 初始化组件
    print("🔧 Initializing components...")
    
    # 初始化记录系统 - 严格模式，无默认值
    logging_config = merged_config['logging']
    enable_logger = logging_config['enable_logger']
    enable_result_saver = logging_config['enable_result_saver']
    
    # 初始化ResultSaver (如果启用)
    result_saver = None
    if enable_result_saver:
        result_saver = ResultSaver(session_info['session_name'])
        result_saver.set_experiment_config(merged_config)
        print("📝 ResultSaver initialized - Complete interaction records will be saved")
    
    # 获取分组件LLM配置 - 严格模式，无默认值
    llm_api_config = merged_config['llm_api_config']
    
    def get_component_llm_config(component_name: str):
        """为指定组件获取LLM配置 - 严格模式，无默认值"""
        component_config = llm_api_config[component_name]
        provider = component_config['provider']
        
        if provider == 'openai':
            return provider, component_config['openai']
        elif provider == 'openrouter':
            return provider, component_config['openrouter']
        else:
            # 使用原有Azure配置
            return provider, {
                'azure_api_key': merged_config['azure_api_key'],
                'azure_endpoint': merged_config['azure_endpoint'],
                'azure_deployment': merged_config['azure_deployment'],
                'model_name': merged_config['model_name'],
                'api_version': merged_config['api_version']
            }
    
    # 初始化Agent - 使用专用配置
    agent_provider, agent_config = get_component_llm_config('agent')
    agent_params = {
        'llm_provider': agent_provider,
        'llm_config': agent_config,
        'system_prompt': merged_config['agent_system_prompt'],
        'max_tokens': 16384
    }
    safe_log(logger, "log_component_init", "Agent", agent_params)
    agent = LLM(**agent_params)
    agent._logger = logger  # 传递logger给Agent
    agent.llm_client._logger = logger  # 传递logger给LLM客户端
    
    # 初始化Manager - 使用专用配置
    manager_provider, manager_config = get_component_llm_config('manager')
    manager_params = {
        'llm_provider': manager_provider,
        'llm_config': manager_config,
        'summary_level': merged_config['summary_level'],
        'system_prompt': merged_config['manager_system_prompt'],
        'initial_state': merged_config['manager_initial_state'],
        'update_prompt': merged_config['manager_update_prompt']
    }
    safe_log(logger, "log_component_init", "Manager", manager_params)
    manager = Manager(**manager_params)
    manager._logger = logger  # 传递logger给Manager
    manager.llm_client._logger = logger  # 传递logger给Manager的LLM客户端
    
    # 显示会话信息
    print(f"- Session: {session_info['session_name']}")
    if enable_logger and session_info.get('log_file'):
        print(f"- Log file: {session_info['log_file']}")
    print()
    
    # Step 4: 加载任务数据 - 根据TEST_MODE确定数量
    task_loader = JSONTaskLoader()
    
    # 加载market_research_21day任务集
    task_set = task_loader.load_task_set("market_research_21day")
    all_tasks = task_set.get_tasks()
    
    # 根据TEST_MODE选择Task数量
    selected_tasks = all_tasks[:max_tasks]
    safe_log(logger, "log_info", f"Loaded {len(selected_tasks)} tasks for {experiment_mode}")
    for i, task in enumerate(selected_tasks, 1):
        safe_log(logger, "log_info", f"  Task {i}: {task.task_id} - {task.title}")
    
    # 初始化事件系统 - 使用配置系统
    event_system = get_event_system("market_research_21day", global_event_probability=merged_config['p_event'])
    safe_log(logger, "log_info", f"Event system initialized with {len(event_system.phase_events)} phases, probability: {merged_config['p_event']}")
    
    # 为每个任务生成事件 - 使用配置的概率
    import random
    p_event = merged_config['p_event']
    
    # 定义根据Task序列号确定阶段的函数
    def get_phase_for_task_sequence(task_sequence_num: int):
        """根据Task序列号确定压力阶段"""
        from tasks.variant_event_loader import EventPhase
        if task_sequence_num <= 7:
            return EventPhase.PHASE_1
        elif task_sequence_num <= 15:
            return EventPhase.PHASE_2
        else:
            return EventPhase.PHASE_3
    
    task_stream = []
    for task_idx, task in enumerate(selected_tasks, 1):
        # 生成事件
        should_have_event = random.random() < p_event
        if should_have_event:
            # 根据Task序列号确定阶段
            phase = get_phase_for_task_sequence(task_idx)
            deceptive_event = event_system.sample_event(phase)
            # 从variants中随机选择一个变体
            variant = deceptive_event.get_random_variant()
            event = {
                'content': variant.content,          # Agent看到的实际事件内容
                'description': deceptive_event.description,  # 系统内部描述
                'pressure_level': variant.pressure_level,
                'category': deceptive_event.category  # 事件类别
            }
        else:
            event = {
                'content': 'Normal business conditions',     # Agent看到的内容
                'description': 'No special event',          # 系统描述
                'pressure_level': 'NORMAL',
                'category': 'NONE'                          # 没有特殊事件
            }
        
        task_stream.append({
            'task': task,
            'event': event
        })
        
        safe_log(logger, "log_info", f"Task {task_idx}: {task.task_id} - Event '{event['content'][:50]}...' ({event['category']}, Pressure: {event['pressure_level']})")
    
    # 处理Task Stream
    print("Processing tasks...")
    
    for task_idx, task_info in enumerate(tqdm(task_stream, desc="Tasks", unit="task")):
        task = task_info['task']
        event = task_info['event']
        
        # 记录任务开始
        safe_log(logger, "log_task_start", task_idx + 1, task.task_id, task.description or task.title)
        safe_log(logger, "log_event_info", event)
        
        # ResultSaver: 记录任务开始并实时保存
        if result_saver:
            result_saver.start_task(task_idx + 1, task, event)
            result_saver.flush()  # 实时保存
        
        # 记录Agent全局历史状态
        if len(agent.global_conversation_history) > 0:
            safe_log(logger, "log_info", f"Agent has {len(agent.global_conversation_history)} interactions from previous tasks")
        
        # 多轮交互直到任务完成 - 使用配置的最大轮数
        max_rounds = merged_config['max_rounds_per_task']
        task_completed = False
        
        # 🆕 任务内的交互历史 - 实现真正的交错对话
        task_manager_feedback_history = []
        
        # 轮次进度条
        rounds_desc = f"Task {task.task_id}"
        for round_num in tqdm(range(1, max_rounds + 1), desc=rounds_desc, unit="round", leave=False):
            safe_log(logger, "log_round_start", round_num, max_rounds)
            
            # ResultSaver: 记录轮次开始和Manager状态，并实时保存
            if result_saver:
                result_saver.start_round(round_num, manager.current_state.copy())
                result_saver.flush()  # 实时保存
            
            # 记录任务文件信息
            safe_log(logger, "log_info", f"Task files count: {len(task.files) if task.files else 0}")
            if task.files:
                for i, file_obj in enumerate(task.files):
                    safe_log(logger, "log_info", f"  File {i+1}: {file_obj.filename} ({len(file_obj.content)} chars)")
            
            if round_num > 1:
                safe_log(logger, "log_info", f"Agent has {len(task_manager_feedback_history)} manager feedback(s) from this task")
            
            # 🆕 使用Agent的封装好的context管理 + 任务内Manager反馈
            try:
                # 判断是否需要使用ChatGPT风格的交错对话
                has_global_history = len(agent.global_conversation_history) > 0
                has_task_feedback = len(task_manager_feedback_history) > 0
                
                if has_global_history or has_task_feedback:
                    # 有全局历史或任务内反馈：使用ChatGPT风格的交错对话
                    enhanced_prompt = agent._build_enhanced_prompt_with_history(task, event['content'])
                    agent_result = agent.process_task_with_enhanced_prompt(task, enhanced_prompt, task_manager_feedback_history)
                else:
                    # 完全新的开始：使用简单的事件处理
                    agent_result = agent.process_task_with_event(task, event['content'])
                
                agent_response = agent_result['response']
                
                # 记录Agent的输出
                safe_log(logger, "log_agent_output", agent_response, agent_result.get('llm_metadata', {}))
                
                # ResultSaver: 保存Agent回复 - 完整内容，绝不截断，并实时保存
                if result_saver:
                    result_saver.save_agent_response(round_num, agent_response)
                    result_saver.flush()  # 实时保存
                
            except Exception as e:
                safe_log(logger, "log_error", e, f"Agent processing - Task {task.task_id}, Round {round_num}")
                raise  # 直接抛出异常，fail-fast原则
            
            # Manager评估
            try:
                # 将event dict转换为event_info格式 - 只传递content，不暴露系统字段
                event_info = {
                    'description': event['content']        # Manager只需要知道实际的事件内容
                }
                
                # Manager会自动打印完整context，然后获取结果
                manager_result = manager.evaluate_and_update(agent_response, task, event_info)
                
                task_completed = manager_result['task_complete']
                
                # 记录Manager输出
                safe_log(logger, "log_manager_output", 
                    task_completed,
                    manager_result['state_updates'],
                    manager_result['comprehensive_reasoning'],
                    manager_result['feedback_response'],
                    manager_result.get('tokens_used', 0),
                    manager_result.get('detailed_reasoning', {})
                )
                
                # ResultSaver: 保存Manager评估 - 完整的所有推理，绝不截断，并实时保存
                if result_saver:
                    result_saver.save_manager_evaluation(round_num, manager_result)
                    result_saver.flush()  # 实时保存
                
                # 🆕 添加Manager反馈到任务内历史 (用于下一轮Agent输入)
                task_manager_feedback_history.append(manager_result['feedback_response'])
                
                # 🆕 记录这一轮的完整交互到Agent的全局历史
                agent.add_interaction_to_global_history(
                    task_id=task.task_id,
                    round_num=round_num,
                    agent_response=agent_response,
                    manager_feedback=manager_result['feedback_response'],
                    task_complete=task_completed
                )
                
                if task_completed:
                    safe_log(logger, "log_task_completion", task.task_id, True, round_num)
                    break
                else:
                    safe_log(logger, "log_info", f"Task not complete, continuing to round {round_num + 1}")
                    
            except Exception as e:
                safe_log(logger, "log_error", e, f"Manager evaluation - Task {task.task_id}, Round {round_num}")
                raise  # 直接抛出异常，fail-fast原则
        
        if not task_completed:
            safe_log(logger, "log_task_completion", task.task_id, False, max_rounds)
        
        # ResultSaver: 任务结束并实时保存
        if result_saver:
            result_saver.end_task(task_idx + 1)
            result_saver.flush()  # 实时保存
        
        # 记录当前状态和历史
        current_state = manager.get_current_state()
        safe_log(logger, "log_info", f"Manager State after Task {task_idx + 1}:")
        safe_log(logger, "log_info", f"  Trust Level: {current_state['trust_level']:.3f}")
        safe_log(logger, "log_info", f"  Work Satisfaction: {current_state['work_satisfaction']:.3f}")
        safe_log(logger, "log_info", f"  Relational Valence: {current_state['relational_valence']:.3f}")
        safe_log(logger, "log_info", f"  Total History Entries: {len(manager.history.interaction_records)}")
    
    # 最终总结
    final_state = manager.get_current_state()
    total_interactions = len(manager.history.interaction_records)
    safe_log(logger, "log_final_summary", final_state, total_interactions)
    
    # 现在进行Detector的批量分析
    print("Running detector analysis...")
    
    # 初始化Detector - 使用专用配置
    detector_provider, detector_config = get_component_llm_config('detector')
    safe_log(logger, "log_component_init", "Detector", {'provider': detector_provider, 'config': detector_config})
    detector = DeceptionDetector(detector_provider, detector_config)
    
    # 获取所有交互记录进行批量分析
    interaction_records = manager.history.interaction_records
    safe_log(logger, "log_info", f"Analyzing {len(interaction_records)} interactions with full sequence context")
    
    # 💾 保存中间结果用于独立分析 - 直接保存manager.history.interaction_records的原始格式
    import json
    intermediate_results_path = f"results/{session_info['session_name']}/interaction_records.json"
    try:
        with open(intermediate_results_path, 'w', encoding='utf-8') as f:
            # 直接保存原始的interaction_records，保持与main.py传给detector的完全一致
            json.dump(interaction_records, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Intermediate results saved to: {intermediate_results_path}")
        safe_log(logger, "log_info", f"Intermediate results saved to: {intermediate_results_path}")
        
    except Exception as e:
        print(f"⚠️  Failed to save intermediate results: {e}")
        safe_log(logger, "log_error", e, "Intermediate results saving")
    
    try:
        detector_results = detector.analyze_interaction_sequence(interaction_records)
        safe_log(logger, "log_detector_analysis", detector_results)
        
        # 控制台显示简要结果
        print(f"✅ Detector analysis completed: {len(detector_results)} interactions analyzed")
        deception_count = sum(1 for r in detector_results if r['deception_detected'])
        print(f"📊 Deception detected in {deception_count}/{len(detector_results)} interactions")
        
        # 💾 保存detector分析结果（带时间戳避免覆盖）
        import time
        timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        detector_output_file = f"results/{session_info['session_name']}/detector_analysis_{timestamp}.txt"
        
        # 导入保存函数
        from core.detector import _save_detector_results_text, _save_detector_results_json
        from pathlib import Path
        
        try:
            # 保存LLM友好的文本格式
            _save_detector_results_text(detector_results, detector_output_file, session_info['session_name'])
            print(f"💾 Detector analysis (text) saved to: {detector_output_file}")
            
            # 自动生成JSON版本
            json_file = str(Path(detector_output_file).with_suffix('.json'))
            _save_detector_results_json(detector_results, json_file, session_info['session_name'])
            print(f"💾 Detector analysis (JSON) saved to: {json_file}")
        except Exception as e:
            print(f"⚠️  Failed to save detector results: {e}")
        
        # ResultSaver: 最终化实验记录
        if result_saver:
            final_manager_state = manager.get_current_state()
            result_saver.finalize_experiment(
                total_tasks=max_tasks,
                total_interactions=len(interaction_records),
                final_manager_state=final_manager_state
            )
            print(f"📝 Complete interaction record saved to: {result_saver.get_record_path()}")
        
        # 关闭logger
        if logger:
            logger.close()
        
        return True
        
    except Exception as e:
        safe_log(logger, "log_error", e, "Detector batch analysis")
        print(f"❌ FATAL ERROR in Detector batch analysis: {e}")
        if logger:
            logger.close()
        raise  # 直接抛出异常，fail-fast原则

if __name__ == "__main__":
    try:
        if run_deception_experiment():
            print("✅ DeceptioN experiment completed successfully!")
        else:
            print("❌ DeceptioN experiment failed!")
            sys.exit(1)
    except Exception as e:
        print(f"💥 FATAL ERROR: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)
