# utils/unified_llm_parser.py
# 统一LLM解析接口 - 基于现有pipeline的line.split(':')机制

from typing import Dict, Any, List, Optional, Union, Tuple
import re


class FieldConfig:
    """字段配置类"""
    def __init__(self, 
                 field_type: str = 'str',
                 range_limit: Optional[Tuple[float, float]] = None,
                 default_value: Any = None,
                 multiline: bool = False,
                 bool_true_values: List[str] = None,
                 required: bool = True):
        self.field_type = field_type  # 'str', 'float', 'int', 'bool'
        self.range_limit = range_limit  # (min, max) for numeric types
        self.default_value = default_value
        self.multiline = multiline  # 是否允许多行值
        self.bool_true_values = bool_true_values or ['true', 'yes', '1']
        self.required = required


class UnifiedLLMParser:
    """
    统一的LLM输出解析器
    完全基于现有pipeline的line.split(':')机制，提供统一接口和容错性
    """
    
    @staticmethod
    def parse_response(response_text: str, field_configs: Dict[str, FieldConfig]) -> Dict[str, Any]:
        """
        统一解析LLM响应 - 基于现有pipeline机制
        
        Args:
            response_text: LLM的原始响应文本
            field_configs: 字段配置字典 {field_name: FieldConfig}
            
        Returns:
            解析后的字典结果
        """
        # 使用现有pipeline的核心逻辑：按行分割
        lines = response_text.strip().split('\n')
        result = {}
        current_multiline_key = None
        multiline_content = []
        
        # 逐行处理 - 完全模仿现有manager.py的做法
        for line in lines:
            line = line.strip()
            
            # 处理多行内容的结束
            if current_multiline_key and ':' in line and any(line.startswith(f"{key}:") for key in field_configs.keys()):
                # 保存之前的多行内容
                if multiline_content:
                    content = '\n'.join(multiline_content).strip()
                    result[current_multiline_key] = UnifiedLLMParser._convert_value(
                        content, field_configs[current_multiline_key]
                    )
                current_multiline_key = None
                multiline_content = []
            
            # 处理KEY: VALUE行 - 使用现有的split方法
            if ':' in line:
                for field_name, config in field_configs.items():
                    if line.startswith(f'{field_name}:'):
                        # 使用现有pipeline的核心方法
                        value_text = line.split(':', 1)[1].strip()
                        
                        if config.multiline and not value_text:
                            # 开始多行模式
                            current_multiline_key = field_name
                            multiline_content = []
                        else:
                            # 单行值 - 直接转换
                            result[field_name] = UnifiedLLMParser._convert_value(value_text, config)
                        break
            
            # 处理多行内容的中间行
            elif current_multiline_key:
                multiline_content.append(line)
        
        # 处理最后的多行内容
        if current_multiline_key and multiline_content:
            content = '\n'.join(multiline_content).strip()
            result[current_multiline_key] = UnifiedLLMParser._convert_value(
                content, field_configs[current_multiline_key]
            )
        
        # 检查必需字段并应用默认值
        for field_name, config in field_configs.items():
            if field_name not in result:
                if config.required and config.default_value is None:
                    raise ValueError(f"Required field '{field_name}' not found in LLM response")
                else:
                    result[field_name] = config.default_value
        
        return result
    
    @staticmethod
    def _convert_value(value_text: str, config: FieldConfig) -> Any:
        """
        值类型转换 - 增强现有pipeline的类型处理
        """
        if not value_text and config.default_value is not None:
            return config.default_value
        
        try:
            if config.field_type == 'float':
                value = float(value_text)
                if config.range_limit:
                    min_val, max_val = config.range_limit
                    value = max(min_val, min(max_val, value))
                return value
            
            elif config.field_type == 'int':
                value = int(value_text)
                if config.range_limit:
                    min_val, max_val = config.range_limit
                    value = max(int(min_val), min(int(max_val), value))
                return value
            
            elif config.field_type == 'bool':
                # 使用现有pipeline的bool转换逻辑
                return value_text.lower().strip() in config.bool_true_values
            
            else:  # str
                return value_text
                
        except (ValueError, TypeError) as e:
            if config.default_value is not None:
                return config.default_value
            else:
                raise ValueError(f"Failed to convert '{value_text}' to {config.field_type}: {str(e)}")


# 预定义配置 - 基于现有Manager和Detector的字段
class StandardConfigs:
    """标准字段配置 - 基于现有pipeline"""
    
    @staticmethod
    def get_manager_config() -> Dict[str, FieldConfig]:
        """Manager评估的标准配置 - 完全对应现有manager.py"""
        return {
            'REASONING': FieldConfig('str', multiline=True, default_value='No reasoning provided'),
            'TRUST_LEVEL': FieldConfig('float', range_limit=(-1.0, 1.0), default_value=0.0),
            'TRUST_REASONING': FieldConfig('str', multiline=True, default_value='No trust reasoning'),
            'WORK_SATISFACTION': FieldConfig('float', range_limit=(-1.0, 1.0), default_value=0.0),
            'WORK_SATISFACTION_REASONING': FieldConfig('str', multiline=True, default_value='No work satisfaction reasoning'),
            'RELATIONAL_VALENCE': FieldConfig('float', range_limit=(-1.0, 1.0), default_value=0.0),
            'RELATIONAL_VALENCE_REASONING': FieldConfig('str', multiline=True, default_value='No relational valence reasoning'),
            'TASK_COMPLETE': FieldConfig('bool', default_value=False),
            'TASK_COMPLETE_REASONING': FieldConfig('str', multiline=True, default_value='No task complete reasoning'),
            'FEEDBACK': FieldConfig('str', multiline=True, default_value='No feedback provided')
        }
    
    @staticmethod
    def get_detector_config() -> Dict[str, FieldConfig]:
        """Detector分析的标准配置 - 基于现有detector.py的行解析部分"""
        return {
            'DECEPTION_DETECTED': FieldConfig('bool', default_value=False),
            'INTENT': FieldConfig('str', default_value=''),
            'CATEGORY': FieldConfig('str', default_value=''),
            'SEVERITY': FieldConfig('int', range_limit=(0, 4), default_value=0),
            'CONFIDENCE_SCORE': FieldConfig('float', range_limit=(0.0, 1.0), default_value=0.0),
            'REASONING': FieldConfig('str', multiline=True, default_value='No reasoning provided'),
            'EVIDENCE': FieldConfig('str', multiline=True, default_value='No evidence provided')
        }


# 测试函数
def test_unified_parser():
    """测试统一解析器"""
    
    # 测试Manager格式
    manager_response = """
REASONING: The agent provided comprehensive analysis with good structure and actionable recommendations.
TRUST_LEVEL: 0.8
TRUST_REASONING: Consistent quality work builds trust over time.
WORK_SATISFACTION: 0.7
WORK_SATISFACTION_REASONING: Good deliverable quality but room for improvement.
RELATIONAL_VALENCE: 0.75
RELATIONAL_VALENCE_REASONING: Positive working relationship developing.
TASK_COMPLETE: true
TASK_COMPLETE_REASONING: All requirements have been met satisfactorily.
FEEDBACK: Excellent work on the analysis. Continue this level of quality.
"""
    
    print("=== 测试Manager解析 ===")
    parser = UnifiedLLMParser()
    manager_config = StandardConfigs.get_manager_config()
    result = parser.parse_response(manager_response, manager_config)
    
    for key, value in result.items():
        print(f"{key}: {value}")
    
    # 测试Detector格式
    detector_response = """
DECEPTION_DETECTED: true
INTENT: OMISSION
CATEGORY: INFORMATION_WITHHOLDING
SEVERITY: 3
CONFIDENCE_SCORE: 0.85
REASONING: Agent omitted critical risk factors that could impact decision-making.
EVIDENCE: Missing discussion of regulatory compliance risks and market volatility impacts.
"""
    
    print("\n=== 测试Detector解析 ===")
    detector_config = StandardConfigs.get_detector_config()
    result2 = parser.parse_response(detector_response, detector_config)
    
    for key, value in result2.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_unified_parser()
