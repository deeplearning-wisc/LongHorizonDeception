#!/usr/bin/env python3
# test_task_stream.py
# 测试连续Task Stream的多轮交互

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.yaml_config_loader import load_yaml_config
from core.manager import Manager
from core.agent import LDLEAgent
from core.detector import DeceptionDetector
from tasks.json_loader import JSONTaskLoader
from tasks.event_loader import get_event_system, DeceptiveEvent
from tasks.base import Task

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
    
    print("="*80)
    print("CONTINUOUS TASK STREAM TEST")
    print("Testing Manager's task completion judgment and continuous context")
    print("="*80)
    
    # Step 1: 加载配置系统
    print("\n[CONFIGURATION LOADING]")
    try:
        # 加载基础配置 (从环境变量)
        print("Loading base configuration from environment variables...")
        base_config = {
            'azure_api_key': config.AZURE_API_KEY,
            'azure_endpoint': config.AZURE_ENDPOINT,
            'azure_deployment': config.AZURE_DEPLOYMENT_NAME,
            'model_name': config.MODEL_NAME,
            'api_version': config.AZURE_API_VERSION
        }
        print(f"✅ Base config loaded:")
        print(f"  - Endpoint: {base_config['azure_endpoint']}")
        print(f"  - Deployment: {base_config['azure_deployment']}")
        print(f"  - Model: {base_config['model_name']}")
        print(f"  - API Version: {base_config['api_version']}")
        print(f"  - API Key: {'***' + base_config['azure_api_key'][-4:] if len(base_config['azure_api_key']) > 4 else '***'}")
        
        # 加载测试特定配置 (从YAML文件)
        print("\nLoading test configuration from YAML file...")
        test_config = load_yaml_config("test_task_stream_config.yaml")
        test_config_dict = test_config  # YAML loader already returns a dict
        print(f"✅ Test config loaded:")
        print(f"  - Agent system prompt: {len(test_config_dict['agent_system_prompt'])} chars")
        print(f"  - Manager system prompt: {len(test_config_dict['manager_system_prompt'])} chars")
        print(f"  - Manager update prompt: {len(test_config_dict['manager_update_prompt'])} chars")
        print(f"  - Manager initial state: {test_config_dict['manager_initial_state']}")
        print(f"  - Event probability: {test_config_dict['p_event']}")
        print(f"  - Summary level: {test_config_dict['summary_level']}")
        print(f"  - Max rounds per task: {test_config_dict['max_rounds_per_task']}")
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Step 2: 合并配置和验证
    print("\n[CONFIGURATION VALIDATION]")
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
            print(f"❌ Missing required configuration: {config_key}")
            return False
    
    print("✅ All required configurations validated")
    print(f"Total configuration items: {len(merged_config)}")
    
    # 打印完整的合并后配置 - 完全不截断
    print(f"\n[MERGED CONFIGURATION - COMPLETE]")
    print("="*80)
    for key, value in merged_config.items():
        print(f"{key}:")
        print(value)
        print()
    print("="*80)
    
    # Step 3: 初始化组件
    print("\n[COMPONENT INITIALIZATION]")
    
    # 初始化Agent - 使用配置系统，严格提供所有参数
    print("Initializing Agent with strict configuration...")
    agent = LDLEAgent(
        azure_api_key=merged_config['azure_api_key'],
        azure_endpoint=merged_config['azure_endpoint'],
        azure_deployment=merged_config['azure_deployment'],
        model_name=merged_config['model_name'],
        system_prompt=merged_config['agent_system_prompt'],
        max_tokens=16384,
        api_version=merged_config['api_version']
    )
    print(f"✅ Agent initialized")
    
    # 初始化Manager - 使用配置系统，一次性完成所有配置
    print("Initializing Manager with strict configuration...")
    manager = Manager(
        azure_api_key=merged_config['azure_api_key'],
        azure_endpoint=merged_config['azure_endpoint'],
        azure_deployment=merged_config['azure_deployment'],
        model_name=merged_config['model_name'],
        api_version=merged_config['api_version'],
        summary_level=merged_config['summary_level'],
        system_prompt=merged_config['manager_system_prompt'],
        initial_state=merged_config['manager_initial_state'],
        update_prompt=merged_config['manager_update_prompt']
    )
    print(f"✅ Manager initialized")
    print(f"  - System prompt: {len(manager.system_prompt)} chars")
    print(f"  - Initial state: {manager.current_state}")
    print(f"  - Summary level: {merged_config['summary_level']}")
    print(f"  - Context limit: {manager.context_limit}")
    
    # 保存Manager状态变化的结构
    manager_state_history = []
    
    # Step 4: 加载真实任务数据 - 前7天
    print("\n[LOADING REAL TASKS]")
    task_loader = JSONTaskLoader()
    
    # 加载market_research_21day任务集
    task_set = task_loader.load_task_set("market_research_21day")
    all_tasks = task_set.get_tasks()
    
    # 只取前7天的任务 (phase_1)
    day_7_tasks = [task for task in all_tasks if task.day <= 7]
    
    print(f"✅ Loaded {len(day_7_tasks)} tasks for first 7 days")
    for task in day_7_tasks:
        print(f"  Day {task.day}: {task.task_id} - {task.title}")
    
    # 初始化事件系统 - 使用配置系统
    print(f"\n[EVENT SYSTEM INITIALIZATION]")
    event_system = get_event_system("market_research_21day", global_event_probability=merged_config['p_event'])
    
    print(f"✅ Event system initialized:")
    print(f"  - Phases loaded: {len(event_system.phase_events)}")
    print(f"  - Event probability: {merged_config['p_event']}")
    
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
        
        print(f"  Task {task.task_id}: Event '{event['content'][:50]}...' ({event['category']}, Pressure: {event['pressure_level']})")
    
    # Agent现在自己管理全局对话历史
    
    # 处理Task Stream
    for task_idx, task_info in enumerate(task_stream):
        task = task_info['task']
        event = task_info['event']
        
        print(f"\n\n{'#'*80}")
        print(f"TASK {task_idx + 1}: {task.task_id}")
        print(f"{'#'*80}")
        print(f"Description: {task.description}")
        print(f"Event: {event['content']} (Category: {event['category']}, Pressure: {event['pressure_level']})")
        
        # 显示Agent全局历史状态
        if len(agent.global_conversation_history) > 0:
            print(f"📚 [CONTINUOUS MEMORY] Agent has {len(agent.global_conversation_history)} interactions from previous tasks")
        
        # 多轮交互直到任务完成 - 使用配置的最大轮数
        max_rounds = merged_config['max_rounds_per_task']
        task_completed = False
        
        for round_num in range(1, max_rounds + 1):
            print(f"\n{'-'*60}")
            print(f"ROUND {round_num}")
            print(f"{'-'*60}")
            
            # 重要：确保任务文件完整保留
            print(f"Task files count: {len(task.files) if task.files else 0}")
            if task.files:
                for i, file_obj in enumerate(task.files):
                    print(f"  File {i+1}: {file_obj.filename} ({len(file_obj.content)} chars)")
            
            print(f"Agent processing round {round_num}...")
            
            # 🆕 使用Agent的封装好的context管理
            try:
                # Agent自动处理context管理、历史截断、prompt构建
                agent_result = agent.process_task_with_event(task, event['content'])
                agent_response = agent_result['response']
                
                print(f"\n[AGENT OUTPUT]")
                print(f"Response length: {len(agent_response)} characters")
                print(f"Tokens used: {agent_result.get('llm_metadata', {}).get('tokens_used', 'N/A')}")
                print(f"Full Response:")
                print(agent_response)
                print(f"[END AGENT OUTPUT]")
                
            except Exception as e:
                print(f"❌ FATAL ERROR in Agent processing: {e}")
                print(f"Task {task.task_id}, Round {round_num} failed")
                raise  # 直接抛出异常，fail-fast原则
            
            # Manager评估
            print(f"\n[MANAGER EVALUATION]")
            
            try:
                # 将event dict转换为event_info格式 - 只传递content，不暴露系统字段
                event_info = {
                    'description': event['content']        # Manager只需要知道实际的事件内容
                }
                
                # Manager会自动打印完整context，然后获取结果
                manager_result = manager.evaluate_and_update(agent_response, task, event_info)
                
                task_completed = manager_result['task_complete']
                
                print(f"\n[MANAGER OUTPUT]")
                print(f"Task Complete: {task_completed}")
                print(f"Trust Level: {manager_result['state_updates']['trust_level']:.3f}")
                print(f"Work Satisfaction: {manager_result['state_updates']['work_satisfaction']:.3f}")
                print(f"Relational Valence: {manager_result['state_updates']['relational_valence']:.3f}")
                print(f"Manager tokens used: {manager_result.get('tokens_used', 'N/A')}")
                print(f"\nComplete Manager Reasoning:")
                print(manager_result['comprehensive_reasoning'])
                print(f"\nManager Feedback to Agent:")
                print(manager_result['feedback_response'])
                print(f"[END MANAGER OUTPUT]")
                
                # 🆕 记录这一轮的完整交互到Agent的全局历史
                agent.add_interaction_to_global_history(
                    task_id=task.task_id,
                    round_num=round_num,
                    agent_response=agent_response,
                    manager_feedback=manager_result['feedback_response'],
                    task_complete=task_completed
                )
                
                if task_completed:
                    print(f"\n✅ Task {task.task_id} completed successfully in {round_num} rounds!")
                    break
                else:
                    print(f"\n⏳ Task not complete, continuing to round {round_num + 1}...")
                    
            except Exception as e:
                print(f"❌ FATAL ERROR in Manager evaluation: {e}")
                print(f"Task {task.task_id}, Round {round_num} failed")
                raise  # 直接抛出异常，fail-fast原则
        
        if not task_completed:
            print(f"\n❌ Task {task.task_id} not completed after {max_rounds} rounds")
        
        # 显示当前状态和历史
        print(f"\nCurrent Manager State after Task {task_idx + 1}:")
        current_state = manager.get_current_state()
        print(f"  Trust Level: {current_state['trust_level']:.3f}")
        print(f"  Work Satisfaction: {current_state['work_satisfaction']:.3f}")
        print(f"  Relational Valence: {current_state['relational_valence']:.3f}")
        print(f"  Total History Entries: {len(manager.history.interaction_records)}")
    
    # 最终总结
    print(f"\n\n{'*'*80}")
    print("TASK STREAM COMPLETED")
    print(f"{'*'*80}")
    
    final_state = manager.get_current_state()
    print(f"Final Manager State:")
    print(f"  Trust Level: {final_state['trust_level']:.3f}")
    print(f"  Work Satisfaction: {final_state['work_satisfaction']:.3f}")
    print(f"  Relational Valence: {final_state['relational_valence']:.3f}")
    
    print(f"\nTotal Interactions: {len(manager.history.interaction_records)}")
    print("\nInteraction History Summary:")
    for i, record in enumerate(manager.history.interaction_records, 1):
        print(f"  [{i}] {record['task_id']} Round {record['round']}")
    
    print(f"\nManager History Context:")
    print(manager.history.get_history_context())
    
    # 现在进行Detector的批量分析
    print(f"\n\n{'*'*80}")
    print("DETECTOR BATCH ANALYSIS")
    print(f"{'*'*80}")
    
    # 初始化Detector - 使用配置系统，严格提供所有参数
    print("Initializing Detector with strict configuration...")
    detector = DeceptionDetector(
        azure_api_key=merged_config['azure_api_key'],
        azure_endpoint=merged_config['azure_endpoint'],
        azure_deployment=merged_config['azure_deployment'],
        model_name=merged_config['model_name'],
        max_retries=3,
        max_tokens=16384,
        api_version=merged_config['api_version']
    )
    
    print(f"Detector initialized with context limit: {detector.context_limit}")
    
    # 获取所有交互记录进行批量分析
    interaction_records = manager.history.interaction_records
    print(f"Analyzing {len(interaction_records)} interactions with full sequence context...")
    
    try:
        detector_results = detector.analyze_interaction_sequence(interaction_records)
        
        print(f"\n[DETECTOR RESULTS SUMMARY]")
        for i, result in enumerate(detector_results, 1):
            print(f"\n[{i}] {result['task_id']} Round {result['round']}:")
            print(f"  Deception Detected: {result['deception_detected']}")
            print(f"  Intent: {result['intent']}")
            print(f"  Category: {result['category']}")
            print(f"  Severity: {result['severity']}")
            print(f"  Confidence: {result['confidence_score']:.2f}")
            print(f"  Reasoning: {result['reasoning'][:150]}...")
            print(f"  Evidence: {len(result['evidence'])} points")
            print(f"  Context Size: {result['context_size']} tokens")
        
        return True
        
    except Exception as e:
        print(f"❌ FATAL ERROR in Detector batch analysis: {e}")
        print("Complete interaction sequence analysis failed")
        raise  # 直接抛出异常，fail-fast原则

if __name__ == "__main__":
    try:
        if test_task_stream():
            print("\n✅ Task Stream test completed successfully!")
        else:
            print("\n❌ Task Stream test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)
