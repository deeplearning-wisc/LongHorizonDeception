# config_handler.py
# 统一优雅的配置管理系统
# 支持YAML配置文件 + 环境变量安全机制

import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigHandler:
    """统一配置管理器 - 支持YAML配置文件和环境变量替换"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.configs_dir = self.project_root / 'configs'
        self.env_file = self.project_root / '.env'
        self._load_env_file()
    
    def _load_env_file(self):
        """加载.env文件到环境变量"""
        if not self.env_file.exists():
            raise FileNotFoundError(f".env file not found at {self.env_file}")
        
        with open(self.env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ[key] = value
        
        print(f"Loaded environment variables from {self.env_file}")
    
    def _substitute_env_vars(self, text: str) -> str:
        """替换文本中的环境变量占位符 ${VAR_NAME}"""
        def replace_match(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            if env_value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return env_value
        
        # 使用正则表达式找到并替换所有 ${VAR_NAME} 模式
        return re.sub(r'\$\{([^}]+)\}', replace_match, str(text))
    
    def _process_config_recursive(self, obj: Any) -> Any:
        """递归处理配置对象，替换所有环境变量"""
        if isinstance(obj, dict):
            return {key: self._process_config_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._process_config_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_env_vars(obj)
        else:
            return obj
    
    def _load_api_profiles(self) -> Dict[str, Any]:
        """加载API配置档案文件"""
        api_profiles_path = self.configs_dir / 'api_profiles.yaml'
        
        if not api_profiles_path.exists():
            raise FileNotFoundError(f"API profiles file not found: {api_profiles_path}")
        
        try:
            with open(api_profiles_path, 'r', encoding='utf-8') as f:
                api_profiles = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in api_profiles.yaml: {e}")
        
        if not api_profiles:
            raise ValueError("Empty API profiles file")
        
        # 递归处理API配置，替换环境变量
        return self._process_config_recursive(api_profiles)
    
    def _resolve_api_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解析API配置引用系统 - 支持直接模型名引用和已扩展配置"""
        if 'llm_api_config' not in config:
            return config
        
        llm_api_config = config['llm_api_config']
        
        # 检查是否包含llm/manager/detector的配置
        required_components = ['llm', 'manager', 'detector']
        has_required_components = all(key in llm_api_config for key in required_components)
        
        if not has_required_components:
            print("⚠️  Missing required components in llm_api_config")
            print("   Expected: llm, manager, detector")
            return config
        
        # 检查第一个组件的格式来判断是否需要解析
        first_component = llm_api_config[required_components[0]]
        
        if isinstance(first_component, str):
            # 格式1: 模型引用格式 (需要解析)
            print("Resolving model references from API profiles")
            
            # 加载API档案
            api_profiles = self._load_api_profiles()
            
            # 检查profiles部分是否存在
            if 'api_profiles' not in api_profiles:
                raise ValueError("No api_profiles section found in api_profiles.yaml")
            
            profiles = api_profiles['api_profiles']
            
            # 解析每个组件的模型引用
            resolved_config = {}
            for component_name in required_components:
                model_name = llm_api_config[component_name]
                
                # 检查模型配置是否存在
                if model_name not in profiles:
                    available_models = list(profiles.keys())
                    raise ValueError(f"Model '{model_name}' not found for component '{component_name}'. Available: {available_models}")
                
                # 获取完整的模型配置
                model_config = profiles[model_name].copy()
                provider = model_config['provider']
                
                # 构建符合main.py期望的格式
                resolved_config[component_name] = {
                    'provider': provider,
                    provider: model_config  # 将完整配置放在provider名称下
                }
                
                print(f"  - {component_name}: {model_name}")
            
            # 替换原有的llm_api_config
            config['llm_api_config'] = resolved_config
            print(f"API model references resolved successfully")
            
        elif isinstance(first_component, dict):
            # 格式2: 已扩展配置格式 (无需解析)
            print("Using pre-expanded API configuration")
            # 已经是完整格式，直接使用
            
        else:
            raise ValueError(f"Invalid llm_api_config format: expected string (model name) or dict (expanded config)")
            
        return config
    
    def load_config(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_name: 配置文件名，如果为None则使用默认配置
        
        Returns:
            处理后的配置字典
        """
        # 确定配置文件名
        if config_name is None:
            config_file = "medium.yaml"  # 默认使用medium配置（50%压力）
        else:
            # 添加.yaml扩展名（如果没有）
            if not config_name.endswith(".yaml"):
                config_name += ".yaml"
            config_file = config_name
        
        config_path = self.configs_dir / config_file
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        print(f"Loading configuration: {config_file}")
        
        # 加载YAML文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {config_file}: {e}")
        
        if not raw_config:
            raise ValueError(f"Empty configuration file: {config_file}")
        
        # 递归处理配置，替换环境变量
        processed_config = self._process_config_recursive(raw_config)
        
        # 处理API配置引用系统
        processed_config = self._resolve_api_config(processed_config)
        
        # 基本验证
        self._validate_config(processed_config, config_file)
        
        print(f"Configuration loaded successfully from {config_file}")
        return processed_config
    
    def _validate_config(self, config: Dict[str, Any], config_file: str):
        """基本配置验证"""
        required_sections = [
            'llm_system_prompt',
            'manager_evaluation_prompt',
            'manager_feedback_prompt', 
            'task_completion_threshold',
            'manager_initial_state',
            'llm_api_config',
            'p_event',
            'max_rounds_per_task',
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            raise ValueError(f"Missing required sections in {config_file}: {missing_sections}")
        
        # 验证环境变量配置
        if 'environment' in config:
            env_config = config['environment']
            required_env = ['azure_api_key', 'azure_endpoint', 'azure_deployment']
            
            for env_var in required_env:
                if env_var in env_config:
                    value = env_config[env_var]
                    if not value or not value.strip():
                        raise ValueError(f"Environment variable {env_var} is empty or missing")
        
        # Additional strict validation for ranges and types
        self._validate_ranges_and_types(config, config_file)
        
        print(f"Configuration validation passed")
    
    def _validate_ranges_and_types(self, config: Dict[str, Any], config_file: str):
        """Validate configuration ranges and types"""
        # p_event: 0.0-1.0
        if 'p_event' not in config:
            raise ValueError("Missing required configuration: 'p_event'")
        p_event = config['p_event']
        if not isinstance(p_event, (int, float)) or not (0.0 <= float(p_event) <= 1.0):
            raise ValueError(f"Invalid p_event: {p_event}. Must be a float in [0.0, 1.0]")

        # event_seed is now provided via CLI; config may not contain it. No strict validation here.

        # max_rounds_per_task: > 0
        if 'max_rounds_per_task' not in config:
            raise ValueError("Missing required configuration: 'max_rounds_per_task'")
        max_rounds = config['max_rounds_per_task']
        if not isinstance(max_rounds, int) or max_rounds <= 0:
            raise ValueError(f"Invalid max_rounds_per_task: {max_rounds}. Must be integer > 0")

        # task_completion_threshold: should be reasonable for [-1,1] work_satisfaction
        if 'task_completion_threshold' not in config:
            raise ValueError("Missing required configuration: 'task_completion_threshold'")
        threshold = config['task_completion_threshold']
        if not isinstance(threshold, (int, float)) or not (-1.0 <= float(threshold) <= 1.0):
            raise ValueError(f"Invalid task_completion_threshold: {threshold}. Must be a float in [-1.0, 1.0]")

        # manager_initial_state ranges
        if 'manager_initial_state' not in config:
            raise ValueError("Missing required configuration: 'manager_initial_state'")
        mis = config['manager_initial_state']
        def _check_range(name: str, val: Any, min_v: float, max_v: float):
            if not isinstance(val, (int, float)):
                raise ValueError(f"manager_initial_state.{name} must be a float in [{min_v}, {max_v}]")
            if float(val) < min_v or float(val) > max_v:
                raise ValueError(f"manager_initial_state.{name} out of range: {val}. Expected [{min_v}, {max_v}]")

        _check_range('trust_level', mis.get('trust_level'), -1.0, 1.0)
        _check_range('work_satisfaction', mis.get('work_satisfaction'), -1.0, 1.0)
        _check_range('relational_comfort', mis.get('relational_comfort'), -1.0, 1.0)

    def load_config_from_file(self, config_file_path: Path) -> Dict[str, Any]:
        """
        Load config directly from specified file path (for detector loading from results)
        
        Args:
            config_file_path: Path to config file
            
        Returns:
            Processed configuration dictionary
        """
        if not config_file_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file_path}")
        
        print(f"Loading configuration from file: {config_file_path}")
        
        # Load YAML file
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {config_file_path}: {e}")
        
        if not raw_config:
            raise ValueError(f"Empty configuration file: {config_file_path}")
        
        # Process environment variables recursively (reuse existing logic)
        processed_config = self._process_config_recursive(raw_config)
        
        # Resolve API configuration references (reuse existing logic)
        processed_config = self._resolve_api_config(processed_config)
        
        print(f"Configuration loaded successfully from {config_file_path}")
        return processed_config

    def show_available_configs(self):
        """显示可用的配置文件"""
        if not self.configs_dir.exists():
            print("No configs directory found")
            return
            
        config_files = list(self.configs_dir.glob("*.yaml"))
        
        if not config_files:
            print("No configuration files found")
            return
        
        print("Available configuration files:")
        for config_file in sorted(config_files):
            name = config_file.stem
            if name == "medium":
                print(f"  - {config_file.name} (default)")
            else:
                print(f"  - {config_file.name} (use: --config {name})")


# 全局配置管理器实例
config_handler = ConfigHandler()

# 兼容性函数，供其他模块使用
def load_config(config_name: Optional[str] = None) -> Dict[str, Any]:
    """加载配置的便捷函数"""
    return config_handler.load_config(config_name)
