#!/usr/bin/env python3
"""
测试Azure OpenAI API 2024-10-21是否能访问GPT-4o 2024-11-20模型
验证API版本和模型版本的对应关系
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from openai import AzureOpenAI
import json

def test_azure_gpt4o_1120():
    """测试新的Azure配置：只使用AZURE_ENDPOINT和AZURE_KEY"""
    
    # 使用新的环境变量
    api_key = os.getenv('AZURE_KEY')
    endpoint = os.getenv('AZURE_ENDPOINT')
    deployment = "gpt-4o"  # 尝试标准部署名
    api_version = "2024-10-21"  # GA版本
    
    if not api_key:
        print("❌ AZURE_KEY environment variable not found")
        return
    if not endpoint:
        print("❌ AZURE_ENDPOINT environment variable not found")
        return
    
    print("🚀 Testing Azure OpenAI GPT-4o 2024-11-20 access via API 2024-10-21")
    print(f"📍 Endpoint: {endpoint}")
    print(f"🔧 Deployment: {deployment}")
    print(f"📅 API Version: {api_version}")
    print()
    
    try:
        # 初始化Azure OpenAI客户端
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        
        # 测试消息：询问模型版本
        test_messages = [
            {
                "role": "system", 
                "content": "You are a helpful assistant. Please tell me exactly what model version you are."
            },
            {
                "role": "user", 
                "content": "What is your model version? Please be specific about the date (e.g., 2024-11-20, 2024-08-06, etc.). Also tell me about your training cutoff date."
            }
        ]
        
        print("📤 Sending test request...")
        response = client.chat.completions.create(
            model=deployment,  # 使用deployment名称
            messages=test_messages,
            max_tokens=500,
            temperature=0.0  # 确保一致的回答
        )
        
        # 解析响应
        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        tokens_used = response.usage.total_tokens if response.usage else "N/A"
        
        print("✅ API调用成功!")
        print(f"🔄 Finish Reason: {finish_reason}")
        print(f"🎯 Tokens Used: {tokens_used}")
        print()
        print("📋 模型回答:")
        print("-" * 60)
        print(content)
        print("-" * 60)
        print()
        
        # 分析回答中是否提到2024-11-20
        if "2024-11-20" in content or "November 2024" in content:
            print("🎉 SUCCESS: 模型确认是2024-11-20版本!")
        elif "2024-08-06" in content or "August 2024" in content:
            print("⚠️  WARNING: 模型显示是2024-08-06版本，不是最新的2024-11-20")
        elif "2024-05-13" in content or "May 2024" in content:
            print("❌ ERROR: 模型显示是旧的2024-05-13版本")
        else:
            print("🤔 UNCLEAR: 模型回答中没有明确的版本信息")
            
        # 额外测试：询问最新能力
        print("\n🧪 测试最新模型能力...")
        capability_messages = [
            {
                "role": "user",
                "content": "Do you have access to structured outputs and JSON schema validation? Can you use reasoning tokens or chain-of-thought? What are your latest capabilities as of November 2024?"
            }
        ]
        
        capability_response = client.chat.completions.create(
            model=deployment,
            messages=capability_messages,
            max_tokens=300,
            temperature=0.0
        )
        
        capability_content = capability_response.choices[0].message.content
        print("📋 能力测试回答:")
        print("-" * 40)
        print(capability_content)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ API调用失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("Azure OpenAI GPT-4o 2024-11-20 版本测试")
    print("测试API版本2024-10-21是否能访问模型版本2024-11-20")
    print("=" * 80)
    print()
    
    # 加载环境变量
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
        print(f"✅ 已加载环境变量从 {env_file}")
    else:
        print(f"⚠️  .env文件未找到: {env_file}")
    
    success = test_azure_gpt4o_1120()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 测试完成! 请查看上面的输出确认模型版本")
    else:
        print("❌ 测试失败! 请检查配置")
    print("=" * 80)

if __name__ == "__main__":
    main()