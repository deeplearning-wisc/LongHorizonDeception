# yaml_config_loader.py
# YAML configuration loader for LDLE system - NO FALLBACKS

import yaml
from pathlib import Path
from typing import Dict, Any

class YAMLConfigLoader:
    """严格的YAML配置加载器 - 无默认值，无fallback"""
    
    def __init__(self, config_path: str):
        """
        加载YAML配置文件
        
        Args:
            config_path: YAML配置文件路径
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML解析错误
            ValueError: 缺少必需字段或值无效
        """
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML config: {e}")
        
        if self.config is None:
            raise ValueError("Config file is empty or invalid")
        
        # 静默验证
        self._validate()
        
        # 显示简洁的配置摘要
        self._print_config_summary(config_path)
    
    def _validate(self):
        """严格验证所有必需字段"""
        required_fields = [
            'agent_system_prompt',
            'manager_system_prompt',
            'manager_update_prompt', 
            'manager_initial_state',
            'p_event',
            'summary_level',
            'max_rounds_per_task',
            'experiment_mode',
            'logging',
            'llm_api_config'
        ]
        
        # 静默检查必需字段
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required field: {field}")
            if self.config[field] is None:
                raise ValueError(f"Field '{field}' cannot be None")
        
        # 静默验证字符串字段
        string_fields = ['agent_system_prompt', 'manager_system_prompt', 'manager_update_prompt']
        for field in string_fields:
            if not isinstance(self.config[field], str):
                raise ValueError(f"Field '{field}' must be a string")
            if not self.config[field].strip():
                raise ValueError(f"Field '{field}' cannot be empty")
        
        # 验证manager_initial_state结构
        initial_state = self.config['manager_initial_state']
        if not isinstance(initial_state, dict):
            raise ValueError("manager_initial_state must be a dictionary")
        
        required_state_fields = ['trust_level', 'work_satisfaction', 'relational_valence']
        for state_field in required_state_fields:
            if state_field not in initial_state:
                raise ValueError(f"Missing state field: {state_field}")
            if not isinstance(initial_state[state_field], (int, float)):
                raise ValueError(f"State field '{state_field}' must be a number")
            if not (-1.0 <= initial_state[state_field] <= 1.0):
                raise ValueError(f"State field '{state_field}' must be between -1.0 and 1.0")
        
        # 验证数值字段
        if not isinstance(self.config['p_event'], (int, float)):
            raise ValueError("p_event must be a number")
        if not (0.0 <= self.config['p_event'] <= 1.0):
            raise ValueError("p_event must be between 0.0 and 1.0")
        
        if not isinstance(self.config['summary_level'], int):
            raise ValueError("summary_level must be an integer")
        if not (1 <= self.config['summary_level'] <= 3):
            raise ValueError("summary_level must be between 1 and 3")
        
        if not isinstance(self.config['max_rounds_per_task'], int):
            raise ValueError("max_rounds_per_task must be an integer")
        if self.config['max_rounds_per_task'] < 1:
            raise ValueError("max_rounds_per_task must be at least 1")
        
        # 验证experiment_mode
        if self.config['experiment_mode'] not in ['quick', 'full']:
            raise ValueError("experiment_mode must be 'quick' or 'full'")
        
        # 验证logging配置
        logging_config = self.config['logging']
        if not isinstance(logging_config, dict):
            raise ValueError("logging must be a dictionary")
        
        required_logging_fields = ['enable_logger', 'enable_result_saver']
        for field in required_logging_fields:
            if field not in logging_config:
                raise ValueError(f"Missing logging field: {field}")
            if not isinstance(logging_config[field], bool):
                raise ValueError(f"logging.{field} must be boolean")
        
        # 验证llm_api_config配置
        llm_config = self.config['llm_api_config']
        if not isinstance(llm_config, dict):
            raise ValueError("llm_api_config must be a dictionary")
        
        required_components = ['agent', 'manager', 'detector']
        for component in required_components:
            if component not in llm_config:
                raise ValueError(f"Missing llm_api_config component: {component}")
            
            component_config = llm_config[component]
            if not isinstance(component_config, dict):
                raise ValueError(f"llm_api_config.{component} must be a dictionary")
            
            if 'provider' not in component_config:
                raise ValueError(f"Missing provider in llm_api_config.{component}")
            
            if component_config['provider'] not in ['openai', 'azure', 'openrouter']:
                raise ValueError(f"llm_api_config.{component}.provider must be 'openai', 'azure', or 'openrouter'")
    
    def _print_config_summary(self, config_path: str):
        """显示简洁的配置摘要 - 严格模式，无默认值"""
        print(f"Config loaded: {config_path}")
        
        # 实验配置 - 严格获取，必须存在
        experiment_mode = self.config['experiment_mode'].upper()
        if experiment_mode == 'QUICK':
            task_count = 7
        else:
            task_count = 21
        
        print(f"- Experiment: {experiment_mode} ({task_count} tasks, max {self.config['max_rounds_per_task']} rounds per task)")
        
        # 模型配置 - 根据provider显示正确的模型名
        llm_config = self.config['llm_api_config']
        
        # Agent模型
        if llm_config['agent']['provider'] == 'openai':
            agent_model = llm_config['agent']['openai']['model']
        else:
            agent_model = "gpt-4o (Azure)"
            
        # Manager模型  
        if llm_config['manager']['provider'] == 'openai':
            manager_model = llm_config['manager']['openai']['model']
        else:
            manager_model = "gpt-4o (Azure)"
            
        # Detector模型
        if llm_config['detector']['provider'] == 'openai':
            detector_model = llm_config['detector']['openai']['model']
        elif llm_config['detector']['provider'] == 'openrouter':
            detector_model = f"{llm_config['detector']['openrouter']['model']} (OpenRouter)"
        else:
            detector_model = "gpt-4o (Azure)"
            
        print(f"- Models: Agent({agent_model}) Manager({manager_model}) Detector({detector_model})")
        
        # 实验参数
        print(f"- Event probability: {self.config['p_event']}, Summary level: {self.config['summary_level']}")
        
        # Manager初始状态
        initial_state = self.config['manager_initial_state']
        print(f"- Manager initial: trust={initial_state['trust_level']}, work_satisfaction={initial_state['work_satisfaction']}, relational_valence={initial_state['relational_valence']}")
        
        # 日志控制 - 严格获取，必须存在
        logging_config = self.config['logging']
        enable_logger = logging_config['enable_logger']
        enable_result_saver = logging_config['enable_result_saver']
        print(f"- Logging: {'enabled' if enable_logger else 'disabled'}, ResultSaver: {'enabled' if enable_result_saver else 'disabled'}")
        print()
    
    def get(self, key: str) -> Any:
        """获取配置值 - 严格模式，不存在则抛异常"""
        if key not in self.config:
            raise KeyError(f"Configuration key '{key}' not found")
        return self.config[key]
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config.copy()

def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """便捷函数：加载YAML配置"""
    loader = YAMLConfigLoader(config_path)
    return loader.get_all()
