#!/usr/bin/env python3
# main.py
# DeceptioN主程序 - 运行欺骗检测实验

import sys
import os
import argparse
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import load_config
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

def run_deception_experiment(config_name=None):
    """运行长期Task序列的欺骗实验"""
    
    # Step 1: 加载配置系统 (统一YAML配置)
    logger = None  # 初始化logger变量
    try:
        # 加载统一配置
        config = load_config(config_name)
        
        # 检查是否启用logger
        enable_logger = config['logging']['enable_logger']
        
        # 根据配置决定是否初始化logger
        logger = None
        session_info = None
        if enable_logger:
            logger = TaskStreamLogger()
            session_info = logger.get_session_info()
            safe_log(logger, 'log_config_loading', "Full Configuration", config)
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
    
    # 配置已经通过config_manager验证过了，这里只需要记录
    safe_log(logger, "log_config_loading", "Configuration validation passed", config)
    
    # 根据experiment_mode确定实验模式
    if config['experiment_mode'].lower() == "quick":
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
    logging_config = config['logging']
    enable_logger = logging_config['enable_logger']
    enable_result_saver = logging_config['enable_result_saver']
    
    # 初始化ResultSaver (如果启用)
    result_saver = None
    if enable_result_saver:
        result_saver = ResultSaver(session_info['session_name'])
        result_saver.set_experiment_config(config)
        
        # 🆕 直接复制配置文件作为metadata！
        import shutil
        session_dir = Path(f"results/{session_info['session_name']}")
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 确定使用的配置文件名
        if config_name is None:
            config_file = "medium.yaml"  # 默认使用medium配置
        else:
            if not config_name.endswith(".yaml"):
                config_name += ".yaml"
            config_file = config_name
        
        # 复制配置文件
        source_config = Path("configs") / config_file
        target_config = session_dir / f"experiment_config_{config_file}"
        shutil.copy2(source_config, target_config)
        print(f"📄 Configuration saved: {target_config}")
        
        print("📝 ResultSaver initialized - Complete interaction records will be saved")
    
    # 获取分组件LLM配置 - 严格模式，无默认值
    llm_api_config = config['llm_api_config']
    
    def get_component_llm_config(component_name: str):
        """为指定组件获取LLM配置 - 严格模式，无默认值"""
        component_config = llm_api_config[component_name]
        provider = component_config['provider']
        
        # 严格按照provider返回对应配置，无默认值
        if provider not in component_config:
            raise ValueError(f"Provider '{provider}' config not found for component '{component_name}'")
        
        return provider, component_config[provider]
    
    # 初始化Agent - 使用专用配置
    agent_provider, agent_config = get_component_llm_config('agent')
    # 显示agent使用的模型名
    agent_model_ref = config['llm_api_config']['agent']
    print(f"[AGENT] Using: {agent_model_ref}")
    
    agent_params = {
        'llm_provider': agent_provider,
        'llm_config': agent_config,
        'system_prompt': config['agent_system_prompt'],
        'max_tokens': 16384
    }
    safe_log(logger, "log_component_init", "Agent", agent_params)
    agent = LLM(**agent_params)
    agent._logger = logger  # 传递logger给Agent
    agent.llm_client._logger = logger  # 传递logger给LLM客户端
    
    # 初始化Manager - 使用专用配置
    manager_provider, manager_config = get_component_llm_config('manager')
    # 显示manager使用的模型名
    manager_model_ref = config['llm_api_config']['manager']
    print(f"[MANAGER] Using: {manager_model_ref}")
    
    manager_params = {
        'llm_provider': manager_provider,
        'llm_config': manager_config,
        'summary_level': config['summary_level'],
        'system_prompt': config['manager_system_prompt'],
        'initial_state': config['manager_initial_state'],
        'update_prompt': config['manager_update_prompt']
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
    safe_log(logger, "log_info", f"ra{len(selected_tasks)} tasks for {experiment_mode}")
    for i, task in enumerate(selected_tasks, 1):
        safe_log(logger, "log_info", f"  Task {i}: {task.task_id} - {task.title}")
    
    # 初始化事件系统 - 使用配置系统
    event_system = get_event_system("market_research_21day", global_event_probability=config['p_event'])
    safe_log(logger, "log_info", f"Event system initialized with {len(event_system.phase_events)} phases, probability: {config['p_event']}")
    
    # 为每个任务生成事件 - 使用配置的概率
    import random
    p_event = config['p_event']
    
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
        max_rounds = config['max_rounds_per_task']
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
    # 显示detector使用的模型名
    detector_model_ref = config['llm_api_config']['detector']
    print(f"[DETECTOR] Using: {detector_model_ref}")
    
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
        
        try:
            # 保存LLM友好的文本格式
            _save_detector_results_text(detector_results, detector_output_file, session_info['session_name'])
            print(f"💾 Detector analysis (text) saved to: {detector_output_file}")
            
            # 💡 从manager历史中提取每轮的状态数据用于JSON
            manager_states = []
            for record in manager.history.interaction_records:
                # 从manager历史记录中获取每轮后的状态
                manager_states.append({
                    'trust_level': record.get('manager_state_after', {}).get('trust_level', 0.0),
                    'work_satisfaction': record.get('manager_state_after', {}).get('work_satisfaction', 0.0),
                    'relational_valence': record.get('manager_state_after', {}).get('relational_valence', 0.0)
                })
            
            # 自动生成JSON版本 - 传递manager状态数据
            json_file = str(Path(detector_output_file).with_suffix('.json'))
            _save_detector_results_json(detector_results, json_file, session_info['session_name'], manager_states)
            print(f"💾 Detector analysis (JSON) saved to: {json_file}")
        except Exception as e:
            print(f"⚠️  Failed to save detector results: {e}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
        
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

def main():
    """主函数 - 处理命令行参数并运行实验"""
    parser = argparse.ArgumentParser(description='DeceptioN - AI Deception Detection Experiment Framework')
    parser.add_argument('--config', '-c', type=str, help='Configuration file name (e.g., normal, high_pressure, test)')
    parser.add_argument('--list-configs', action='store_true', help='Show available configuration files')
    
    args = parser.parse_args()
    
    # 显示可用配置文件
    if args.list_configs:
        from config_manager import config_manager
        config_manager.show_available_configs()
        return
    
    # 运行实验
    try:
        if run_deception_experiment(args.config):
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

if __name__ == "__main__":
    main()
