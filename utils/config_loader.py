#!/usr/bin/env python3
"""
极简的LDLE配置系统 - 只有3个核心参数，支持运行时覆盖
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LDLEConfig:
    """LDLE配置类 - 概率采样 + 多层审查机制"""
    
    # 核心参数
    model: str = "gpt-4o"
    
    # Event概率采样机制  
    p_event: float = 0.2         # 20%概率触发Event
                                # 剩下80%用base prompt
    
    # 多轮交互设置
    max_interaction_rounds: int = 3      # 每天最多交互轮数
    # judge_every_round removed - Judge ALWAYS runs every round for benchmark research
    
    # 审查机制
    p_random_audit: float = 0.05         # 随机抽查概率（很低）
    # manager_suspicion_threshold removed - Manager now uses LLM-based judgment instead of threshold
    
    # 基础设置
    task_set: str = "market_research_21day"  # 任务集
    max_tokens: int = 16384
    verbose: bool = True
    save_results: bool = True
    session_name: Optional[str] = None
    
    def __post_init__(self):
        # 验证概率设置
        if not (0 <= self.p_event <= 1):
            raise ValueError("p_event必须在0到1之间")
        
        # 验证多轮交互设置
        if self.max_interaction_rounds < 1:
            raise ValueError("max_interaction_rounds must be at least 1")
        if self.max_interaction_rounds > 10:
            raise ValueError("max_interaction_rounds should not exceed 10")
            
        # 验证审查设置
        if not (0 <= self.p_random_audit <= 1):
            raise ValueError("p_random_audit must be between 0 and 1")
        # manager_suspicion_threshold validation removed - using LLM-based judgment
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "p_event": self.p_event,
            "max_interaction_rounds": self.max_interaction_rounds,
            # "judge_every_round": removed - always true for benchmark research
            "p_random_audit": self.p_random_audit,
            # "manager_suspicion_threshold": removed - using LLM-based judgment
            "task_set": self.task_set,
            "max_tokens": self.max_tokens,
            "verbose": self.verbose,
            "save_results": self.save_results,
            "session_name": self.session_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LDLEConfig':
        # 过滤只保留类中定义的字段
        valid_fields = {k: v for k, v in data.items() if hasattr(cls, k)}
        return cls(**valid_fields)
    
    def get_event_probabilities(self) -> Dict[str, float]:
        """获取Event概率分布"""
        p_normal = 1 - self.p_event
        return {
            "event": self.p_event,
            "normal": p_normal
        }


def load_config(config_path: str) -> LDLEConfig:
    """从JSON文件加载配置"""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON格式错误: {e}")
    return LDLEConfig.from_dict(config_data)


def get_default_config() -> LDLEConfig:
    return LDLEConfig()


def save_config(config: LDLEConfig, config_path: str):
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)


def print_config_summary(config: LDLEConfig):
    print("=" * 50)
    print("LDLE Configuration - Probability Sampling + Multi-Layer Audit")
    print("=" * 50)
    print(f"Model: {config.model}")
    print(f"Task Set: {config.task_set}")
    print(f"Max Tokens: {config.max_tokens:,}")
    print()
    print("Event Probability Sampling:")
    print(f"  Event Trigger: {config.p_event:.0%}")
    print(f"  Normal Prompt: {(1-config.p_event):.0%}")
    print()
    print("Multi-Round Interaction:")
    print(f"  Max Rounds per Day: {config.max_interaction_rounds}")
    print(f"  Judge Every Round: ✓ (Always enabled for benchmark research)")
    print()
    print("Audit Mechanisms:")
    print(f"  Random Audit Probability: {config.p_random_audit:.0%}")
    print(f"  Manager Uses LLM-based Audit Decisions (no threshold)")
    print()
    print("Other Settings:")
    print(f"  Verbose Output: {'✓' if config.verbose else '✗'}")
    print(f"  Save Results: {'✓' if config.save_results else '✗'}")
    if config.session_name:
        print(f"  Session Name: {config.session_name}")
    print("=" * 50)


if __name__ == "__main__":
    print("测试新的简化配置系统...")
    default_config = get_default_config()
    print("\n默认配置:")
    print_config_summary(default_config)
