#!/usr/bin/env python3
"""
测试最新的GPT-4o模型版本
检查Azure OpenAI和OpenAI直接API的最新可用版本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from core.Universal_LLM_Client import UniversalLLMClient

def load_env_file():
    """加载.env文件"""
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ[key] = value
        print(f"✅ Loaded .env from {env_file}")

def test_azure_gpt4o_versions():
    """测试Azure OpenAI GPT-4o 2024-11-20版本"""
    print("\n🔵 === Azure OpenAI GPT-4o 2024-11-20 测试 ===")
    
    config = {
        "azure_api_key": os.getenv("AZURE_API"),
        "azure_endpoint": os.getenv("AZURE_URL"),
        "azure_deployment": "gpt-4o",
        "azure_api_version": "2024-10-21",  # GA版本
        "model_name": "gpt-4o",
        "model_version": "2024-11-20"  # 指定GPT-4o 2024-11-20版本
    }
    
    try:
        client = UniversalLLMClient("azure", config)
        
        # 简单测试调用
        result = client.complete_chat(
            messages=[{"role": "user", "content": "What is 2+2? Answer briefly."}],
            max_tokens=20,
            temperature=0.0
        )
        
        if result['success']:
            print("✅ Azure GPT-4o 2024-11-20 工作正常")
            print(f"   响应: {result['content']}")
            print(f"   Token使用: {result.get('tokens_used', 'N/A')}")
        else:
            print(f"❌ 测试失败: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"💥 测试异常: {str(e)}")

def test_openai_gpt4o_versions():
    """测试OpenAI直接API的GPT-4o版本"""
    print("\n🟢 === OpenAI 直接API GPT-4o 版本测试 ===")
    
    # 测试不同的模型名称
    model_names = [
        "gpt-4o",              # 标准版本
        "gpt-4o-2024-05-13",   # 特定日期版本
        "gpt-4o-2024-08-06",   # 更新的日期版本
        "gpt-4o-latest",       # 最新版本别名
        "gpt-4o-mini",         # mini版本
        "o1-mini",             # o1系列mini
        "o1-preview"           # o1系列预览版
    ]
    
    for model_name in model_names:
        print(f"\n📋 测试模型: {model_name}")
        
        config = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": model_name
        }
        
        try:
            client = UniversalLLMClient("openai", config)
            
            # 对o1系列使用不同的参数
            if "o1" in model_name:
                result = client.complete_chat(
                    messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}],
                    max_completion_tokens=10  # o1系列使用max_completion_tokens
                    # 不设置temperature，o1系列有固定的temperature
                )
            else:
                result = client.complete_chat(
                    messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}],
                    max_tokens=10,
                    temperature=0.0
                )
            
            if result['success']:
                print(f"✅ 模型 {model_name} 工作正常")
                print(f"   响应: {result['content'][:50]}")
                print(f"   Token使用: {result.get('tokens_used', 'N/A')}")
            else:
                print(f"❌ 模型 {model_name} 失败: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"💥 模型 {model_name} 异常: {str(e)[:100]}")

def test_openrouter_versions():
    """测试OpenRouter的最新模型"""
    print("\n🔴 === OpenRouter 最新模型测试 ===")
    
    model_names = [
        "google/gemini-2.5-pro",           # 当前使用的
        "anthropic/claude-3.5-sonnet",    # Claude最新
        "openai/gpt-4o",                  # OpenRouter的GPT-4o
        "openai/gpt-4o-2024-08-06"        # 特定版本
    ]
    
    for model_name in model_names:
        print(f"\n📋 测试模型: {model_name}")
        
        config = {
            "api_key": os.getenv("OPENROUTER"),
            "model": model_name
        }
        
        try:
            client = UniversalLLMClient("openrouter", config)
            
            result = client.complete_chat(
                messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}],
                max_tokens=10,
                temperature=0.0
            )
            
            if result['success']:
                print(f"✅ 模型 {model_name} 工作正常")
                print(f"   响应: {result['content'][:50]}")
                print(f"   Token使用: {result.get('tokens_used', 'N/A')}")
            else:
                print(f"❌ 模型 {model_name} 失败: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"💥 模型 {model_name} 异常: {str(e)[:100]}")

if __name__ == "__main__":
    print("🚀 Azure OpenAI GPT-4o 版本测试开始")
    
    # 加载环境变量
    load_env_file()
    
    # 只运行Azure测试
    test_azure_gpt4o_versions()
    
    print("\n✅ Azure测试完成！")