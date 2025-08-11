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
        print(f"[YAML_CONFIG] Loading config from: {config_path}")
        
        if not Path(config_path).exists():
            print(f"[YAML_CONFIG] ❌ File not found: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        print(f"[YAML_CONFIG] ✅ File exists, parsing YAML...")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"[YAML_CONFIG] ❌ YAML parsing failed: {e}")
            raise yaml.YAMLError(f"Failed to parse YAML config: {e}")
        
        if self.config is None:
            print(f"[YAML_CONFIG] ❌ Config is empty or invalid")
            raise ValueError("Config file is empty or invalid")
        
        print(f"[YAML_CONFIG] ✅ YAML parsed successfully, found {len(self.config)} keys: {list(self.config.keys())}")
        print(f"[YAML_CONFIG] Validating configuration...")
        self._validate()
        print(f"[YAML_CONFIG] ✅ Configuration validation passed")
    
    def _validate(self):
        """严格验证所有必需字段"""
        required_fields = [
            'agent_system_prompt',
            'manager_system_prompt',
            'manager_update_prompt', 
            'manager_initial_state',
            'p_event',
            'summary_level',
            'max_rounds_per_task'
        ]
        
        print(f"[YAML_CONFIG] Checking required fields: {required_fields}")
        for field in required_fields:
            if field not in self.config:
                print(f"[YAML_CONFIG] ❌ Missing field: {field}")
                raise ValueError(f"Missing required field: {field}")
            if self.config[field] is None:
                print(f"[YAML_CONFIG] ❌ Field '{field}' is None")
                raise ValueError(f"Field '{field}' cannot be None")
            print(f"[YAML_CONFIG] ✅ Field '{field}' present")
        
        # 验证字符串字段不为空
        print(f"[YAML_CONFIG] Validating string fields...")
        string_fields = ['agent_system_prompt', 'manager_system_prompt', 'manager_update_prompt']
        for field in string_fields:
            if not isinstance(self.config[field], str):
                print(f"[YAML_CONFIG] ❌ Field '{field}' is not a string: {type(self.config[field])}")
                raise ValueError(f"Field '{field}' must be a string")
            if not self.config[field].strip():
                print(f"[YAML_CONFIG] ❌ Field '{field}' is empty")
                raise ValueError(f"Field '{field}' cannot be empty")
            
            # 特别显示manager_update_prompt的多行格式
            if field == 'manager_update_prompt':
                lines = self.config[field].split('\n')
                print(f"[YAML_CONFIG] ✅ '{field}': {len(self.config[field])} chars, {len(lines)} lines")
                print(f"[YAML_CONFIG]    Preview: {repr(self.config[field][:100])}...")
            else:
                print(f"[YAML_CONFIG] ✅ '{field}': {len(self.config[field])} chars")
        
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
