# config_manager.py
# 统一优雅的配置管理系统
# 支持YAML配置文件 + 环境变量安全机制

import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    """统一配置管理器 - 支持YAML配置文件和环境变量替换"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
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
        
        print(f"✅ Loaded environment variables from {self.env_file}")
    
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
        
        print(f"📄 Loading configuration: {config_file}")
        
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
        
        # 基本验证
        self._validate_config(processed_config, config_file)
        
        print(f"✅ Configuration loaded successfully from {config_file}")
        return processed_config
    
    def _validate_config(self, config: Dict[str, Any], config_file: str):
        """基本配置验证"""
        required_sections = [
            'agent_system_prompt',
            'manager_system_prompt', 
            'manager_update_prompt',
            'manager_initial_state',
            'llm_api_config',
            'p_event',
            'summary_level',
            'max_rounds_per_task',
            'experiment_mode'
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
        
        print(f"✅ Configuration validation passed")
    
    def get_azure_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """从配置中提取Azure相关配置"""
        if 'environment' not in config:
            raise ValueError("No environment section found in configuration")
        
        env = config['environment']
        
        # 从AZURE_URL解析endpoint和deployment (如果需要)
        azure_url = env.get('azure_endpoint', '')
        if azure_url and '/openai/deployments/' in azure_url:
            # 解析Azure URL格式: https://endpoint/openai/deployments/deployment-name/...
            endpoint = azure_url.split('/openai/deployments/')[0]
            deployment_part = azure_url.split('/deployments/')[1]
            deployment_from_url = deployment_part.split('/')[0]
        else:
            endpoint = azure_url
            deployment_from_url = None
        
        # 提取必需的Azure配置
        azure_config = {
            'azure_api_key': env.get('azure_api_key'),
            'azure_endpoint': endpoint or env.get('azure_endpoint'),
            'azure_deployment': env.get('azure_deployment') or deployment_from_url,
            'azure_api_version': env.get('azure_api_version', '2024-02-15-preview'),  # 默认API版本
            'model_name': env.get('azure_deployment') or deployment_from_url  # 使用deployment名作为model名
        }
        
        # 验证所有必需字段都存在
        for key, value in azure_config.items():
            if not value or not str(value).strip():
                raise ValueError(f"Missing or empty Azure configuration: {key}")
        
        return azure_config
    
    def show_available_configs(self):
        """显示可用的配置文件"""
        if not self.configs_dir.exists():
            print("❌ No configs directory found")
            return
            
        config_files = list(self.configs_dir.glob("*.yaml"))
        
        if not config_files:
            print("❌ No configuration files found")
            return
        
        print("📋 Available configuration files:")
        for config_file in sorted(config_files):
            name = config_file.stem
            if name == "medium":
                print(f"  - {config_file.name} (default)")
            else:
                print(f"  - {config_file.name} (use: --config {name})")


# 全局配置管理器实例
config_manager = ConfigManager()

# 兼容性函数，供其他模块使用
def load_config(config_name: Optional[str] = None) -> Dict[str, Any]:
    """加载配置的便捷函数"""
    return config_manager.load_config(config_name)

def get_azure_config(config: Dict[str, Any]) -> Dict[str, str]:
    """获取Azure配置的便捷函数"""
    return config_manager.get_azure_config(config)