"""
Common utility functions for DeceptioN project
提供全项目通用的验证和工具函数
"""

from typing import List, Set, Any, Optional

# 定义系统支持的categories和pressure_levels
VALID_CATEGORIES: Set[str] = {
    "GOAL_CONFLICT",
    "COMPETITIVE_INTERACTION", 
    "MORAL_DILEMMA",
    "AUTHORITY_DIRECTIVE",
    "INFORMATION_GAP"
}

VALID_PRESSURE_LEVELS: Set[str] = {
    "LOW",
    "MEDIUM", 
    "HIGH",
    "CRITICAL"
}

def validate_category(category: str, context: str = "") -> str:
    """
    验证category是否在允许的5个值中
    
    Args:
        category: 要验证的category
        context: 错误上下文信息
        
    Returns:
        str: 验证通过的category
        
    Raises:
        ValueError: 如果category不在允许的值中
    """
    if category not in VALID_CATEGORIES:
        context_info = f" in {context}" if context else ""
        raise ValueError(
            f"Invalid category '{category}'{context_info}. "
            f"Must be one of: {sorted(VALID_CATEGORIES)}"
        )
    return category

def validate_pressure_level(pressure_level: str, context: str = "") -> str:
    """
    验证pressure_level是否在允许的4个值中
    
    Args:
        pressure_level: 要验证的pressure level
        context: 错误上下文信息
        
    Returns:
        str: 验证通过的pressure_level
        
    Raises:
        ValueError: 如果pressure_level不在允许的值中
    """
    # 转换为大写进行比较，保持一致性
    pressure_upper = pressure_level.upper()
    
    if pressure_upper not in VALID_PRESSURE_LEVELS:
        context_info = f" in {context}" if context else ""
        raise ValueError(
            f"Invalid pressure level '{pressure_level}'{context_info}. "
            f"Must be one of: {sorted(VALID_PRESSURE_LEVELS)}"
        )
    return pressure_upper

def validate_categories_list(categories: List[str], context: str = "") -> List[str]:
    """
    批量验证categories列表
    
    Args:
        categories: 要验证的categories列表
        context: 错误上下文信息
        
    Returns:
        List[str]: 验证通过的categories列表
    """
    validated = []
    for category in categories:
        validated.append(validate_category(category, context))
    return validated

def validate_pressure_levels_list(pressure_levels: List[str], context: str = "") -> List[str]:
    """
    批量验证pressure levels列表
    
    Args:
        pressure_levels: 要验证的pressure levels列表
        context: 错误上下文信息
        
    Returns:
        List[str]: 验证通过的pressure levels列表
    """
    validated = []
    for pressure_level in pressure_levels:
        validated.append(validate_pressure_level(pressure_level, context))
    return validated

def check_json_format_integrity(event_data: dict, source_file: str = "unknown") -> dict:
    """
    检查event JSON数据的完整性，确保categories和pressure levels正确
    
    Args:
        event_data: 事件JSON数据
        source_file: 源文件名，用于错误报告
        
    Returns:
        dict: 验证通过的事件数据（原地修改）
        
    Raises:
        ValueError: 如果发现无效的category或pressure level
    """
    if "phases" not in event_data:
        raise ValueError(f"Missing 'phases' in {source_file}")
    
    phases = event_data["phases"]
    
    for phase_name, phase_data in phases.items():
        if "events" not in phase_data:
            continue
            
        events = phase_data["events"]
        
        for event_idx, event in enumerate(events):
            # 验证category
            if "category" in event:
                event["category"] = validate_category(
                    event["category"], 
                    f"{source_file} phase {phase_name} event {event_idx}"
                )
            
            # 验证variants中的pressure levels
            if "variants" in event:
                variants = event["variants"]
                for variant_name, variant_data in variants.items():
                    if "pressure_level" in variant_data:
                        variant_data["pressure_level"] = validate_pressure_level(
                            variant_data["pressure_level"],
                            f"{source_file} phase {phase_name} event {event_idx} variant {variant_name}"
                        )
    
    return event_data

def get_valid_categories() -> List[str]:
    """获取所有有效的categories列表（排序后）"""
    return sorted(VALID_CATEGORIES)

def get_valid_pressure_levels() -> List[str]:
    """获取所有有效的pressure levels列表（排序后）"""
    return sorted(VALID_PRESSURE_LEVELS)

def is_valid_category(category: str) -> bool:
    """检查category是否有效（不抛出异常）"""
    return category in VALID_CATEGORIES

def is_valid_pressure_level(pressure_level: str) -> bool:
    """检查pressure level是否有效（不抛出异常）"""
    return pressure_level.upper() in VALID_PRESSURE_LEVELS