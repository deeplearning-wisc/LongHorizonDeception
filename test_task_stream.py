#!/usr/bin/env python3
# test_task_stream.py
# 测试连续Task Stream的多轮交互

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.yaml_config_loader import load_yaml_config
from utils.task_stream_logger import TaskStreamLogger
from core.manager import Manager
from core.agent import LDLEAgent
from core.detector import DeceptionDetector
from tasks.json_loader import JSONTaskLoader
from tasks.event_loader import get_event_system, DeceptiveEvent
from tasks.base import Task
from tqdm import tqdm

class TaskStreamTask:
    def __init__(self, task_id, title, description, day=1):
        self.day = day
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

def test_task_stream():
    """测试连续Task Stream的多轮交互"""
    
    # 初始化logger
    logger = TaskStreamLogger()
    session_info = logger.get_session_info()
    
    # 控制台只显示基本信息
    print(f"🚀 Starting Task Stream Test")
    print(f"📁 Session: {session_info['session_name']}")
    print(f"📄 Log file: {session_info['log_file']}")
    
    # Step 1: 加载配置系统
    try:
        # 加载基础配置 (从环境变量)
        base_config = {
            'azure_api_key': config.AZURE_API_KEY,
            'azure_endpoint': config.AZURE_ENDPOINT,
            'azure_deployment': config.AZURE_DEPLOYMENT_NAME,
            'model_name': config.MODEL_NAME,
            'api_version': config.AZURE_API_VERSION
        }
        logger.log_config_loading("Base Configuration (Environment Variables)", base_config)
        
        # 加载测试特定配置 (从YAML文件)
        test_config = load_yaml_config("test_task_stream_config.yaml")
        test_config_dict = test_config  # YAML loader already returns a dict
        logger.log_config_loading("Test Configuration (YAML)", test_config_dict)
        
    except Exception as e:
        logger.log_error(e, "Configuration loading")
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Step 2: 合并配置和验证
    merged_config = {
        **base_config,
        **test_config_dict
    }
    
    # 验证所有必需配置都存在
    required_configs = [
        'azure_api_key', 'azure_endpoint', 'azure_deployment', 'model_name', 'api_version',
        'agent_system_prompt', 'manager_system_prompt', 'manager_update_prompt', 'manager_initial_state',
        'p_event', 'summary_level', 'max_rounds_per_task'
    ]
    
    for config_key in required_configs:
        if config_key not in merged_config or merged_config[config_key] is None:
            logger.log_error(ValueError(f"Missing required configuration: {config_key}"), "Configuration validation")
            print(f"❌ Missing required configuration: {config_key}")
            return False
    
    logger.log_config_loading("Merged Configuration", merged_config)
    
    # Step 3: 初始化组件
    print("🔧 Initializing components...")
    
    # 初始化Agent - 使用配置系统，严格提供所有参数
    agent_params = {
        'azure_api_key': merged_config['azure_api_key'],
        'azure_endpoint': merged_config['azure_endpoint'],
        'azure_deployment': merged_config['azure_deployment'],
        'model_name': merged_config['model_name'],
        'system_prompt': merged_config['agent_system_prompt'],
        'max_tokens': 16384,
        'api_version': merged_config['api_version']
    }
    logger.log_component_init("Agent", agent_params)
    agent = LDLEAgent(**agent_params)
    agent._logger = logger  # 传递logger给Agent
    agent.llm_client._logger = logger  # 传递logger给LLM客户端
    
    # 初始化Manager - 使用配置系统，一次性完成所有配置
    manager_params = {
        'azure_api_key': merged_config['azure_api_key'],
        'azure_endpoint': merged_config['azure_endpoint'],
        'azure_deployment': merged_config['azure_deployment'],
        'model_name': merged_config['model_name'],
        'api_version': merged_config['api_version'],
        'summary_level': merged_config['summary_level'],
        'system_prompt': merged_config['manager_system_prompt'],
        'initial_state': merged_config['manager_initial_state'],
        'update_prompt': merged_config['manager_update_prompt']
    }
    logger.log_component_init("Manager", manager_params)
    manager = Manager(**manager_params)
    manager._logger = logger  # 传递logger给Manager
    manager.llm_client._logger = logger  # 传递logger给Manager的LLM客户端
    
    # Step 4: 加载真实任务数据 - 前7天
    print("📋 Loading tasks and events...")
    task_loader = JSONTaskLoader()
    
    # 加载market_research_21day任务集
    task_set = task_loader.load_task_set("market_research_21day")
    all_tasks = task_set.get_tasks()
    
    # 只取前7天的任务 (phase_1)
    day_7_tasks = [task for task in all_tasks if task.day <= 7]
    logger.log_info(f"Loaded {len(day_7_tasks)} tasks for first 7 days")
    for task in day_7_tasks:
        logger.log_info(f"  Day {task.day}: {task.task_id} - {task.title}")
    
    # 初始化事件系统 - 使用配置系统
    event_system = get_event_system("market_research_21day", global_event_probability=merged_config['p_event'])
    logger.log_info(f"Event system initialized with {len(event_system.phase_events)} phases, probability: {merged_config['p_event']}")
    
    # 为每个任务生成事件 - 使用配置的概率
    import random
    p_event = merged_config['p_event']
    
    task_stream = []
    for task in day_7_tasks:
        # 生成事件
        should_have_event = random.random() < p_event
        if should_have_event:
            # Phase 1 事件 (Day 1-7) - 使用事件系统
            from tasks.variant_event_loader import EventPhase
            deceptive_event = event_system.sample_event(EventPhase.PHASE_1)
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
        
        logger.log_info(f"Task {task.task_id}: Event '{event['content'][:50]}...' ({event['category']}, Pressure: {event['pressure_level']})")
    
    # 处理Task Stream - 添加进度条
    print("🚀 Processing tasks...")
    
    for task_idx, task_info in enumerate(tqdm(task_stream, desc="Tasks", unit="task")):
        task = task_info['task']
        event = task_info['event']
        
        # 记录任务开始
        logger.log_task_start(task_idx + 1, task.task_id, task.description or task.title)
        logger.log_event_info(event)
        
        # 记录Agent全局历史状态
        if len(agent.global_conversation_history) > 0:
            logger.log_info(f"Agent has {len(agent.global_conversation_history)} interactions from previous tasks")
        
        # 多轮交互直到任务完成 - 使用配置的最大轮数
        max_rounds = merged_config['max_rounds_per_task']
        task_completed = False
        
        # 🆕 任务内的交互历史 - 实现真正的交错对话
        task_manager_feedback_history = []
        
        # 轮次进度条
        rounds_desc = f"Task {task.task_id}"
        for round_num in tqdm(range(1, max_rounds + 1), desc=rounds_desc, unit="round", leave=False):
            logger.log_round_start(round_num, max_rounds)
            
            # 记录任务文件信息
            logger.log_info(f"Task files count: {len(task.files) if task.files else 0}")
            if task.files:
                for i, file_obj in enumerate(task.files):
                    logger.log_info(f"  File {i+1}: {file_obj.filename} ({len(file_obj.content)} chars)")
            
            if round_num > 1:
                logger.log_info(f"Agent has {len(task_manager_feedback_history)} manager feedback(s) from this task")
            
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
                logger.log_agent_output(agent_response, agent_result.get('llm_metadata', {}))
                
            except Exception as e:
                logger.log_error(e, f"Agent processing - Task {task.task_id}, Round {round_num}")
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
                logger.log_manager_output(
                    task_completed,
                    manager_result['state_updates'],
                    manager_result['comprehensive_reasoning'],
                    manager_result['feedback_response'],
                    manager_result.get('tokens_used', 0),
                    manager_result.get('detailed_reasoning', {})
                )
                
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
                    logger.log_task_completion(task.task_id, True, round_num)
                    break
                else:
                    logger.log_info(f"Task not complete, continuing to round {round_num + 1}")
                    
            except Exception as e:
                logger.log_error(e, f"Manager evaluation - Task {task.task_id}, Round {round_num}")
                raise  # 直接抛出异常，fail-fast原则
        
        if not task_completed:
            logger.log_task_completion(task.task_id, False, max_rounds)
        
        # 记录当前状态和历史
        current_state = manager.get_current_state()
        logger.log_info(f"Manager State after Task {task_idx + 1}:")
        logger.log_info(f"  Trust Level: {current_state['trust_level']:.3f}")
        logger.log_info(f"  Work Satisfaction: {current_state['work_satisfaction']:.3f}")
        logger.log_info(f"  Relational Valence: {current_state['relational_valence']:.3f}")
        logger.log_info(f"  Total History Entries: {len(manager.history.interaction_records)}")
    
    # 最终总结
    final_state = manager.get_current_state()
    total_interactions = len(manager.history.interaction_records)
    logger.log_final_summary(final_state, total_interactions)
    
    # 现在进行Detector的批量分析
    print("🔍 Running detector analysis...")
    
    # 初始化Detector - 使用配置系统，严格提供所有参数
    detector_params = {
        'azure_api_key': merged_config['azure_api_key'],
        'azure_endpoint': merged_config['azure_endpoint'],
        'azure_deployment': merged_config['azure_deployment'],
        'model_name': merged_config['model_name'],
        'max_retries': 3,
        'max_tokens': 16384,
        'api_version': merged_config['api_version']
    }
    logger.log_component_init("Detector", detector_params)
    detector = DeceptionDetector(**detector_params)
    
    # 获取所有交互记录进行批量分析
    interaction_records = manager.history.interaction_records
    logger.log_info(f"Analyzing {len(interaction_records)} interactions with full sequence context")
    
    try:
        detector_results = detector.analyze_interaction_sequence(interaction_records)
        logger.log_detector_analysis(detector_results)
        
        # 控制台显示简要结果
        print(f"✅ Detector analysis completed: {len(detector_results)} interactions analyzed")
        deception_count = sum(1 for r in detector_results if r['deception_detected'])
        print(f"📊 Deception detected in {deception_count}/{len(detector_results)} interactions")
        
        # 关闭logger
        logger.close()
        
        return True
        
    except Exception as e:
        logger.log_error(e, "Detector batch analysis")
        print(f"❌ FATAL ERROR in Detector batch analysis: {e}")
        logger.close()
        raise  # 直接抛出异常，fail-fast原则

if __name__ == "__main__":
    try:
        if test_task_stream():
            print("✅ Task Stream test completed successfully!")
        else:
            print("❌ Task Stream test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"💥 FATAL ERROR: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)
