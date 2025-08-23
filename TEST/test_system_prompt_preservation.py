#!/usr/bin/env python3
"""
测试System Prompt在截断时是否被保护
这是极其关键的测试！如果system prompt被截断，整个AI行为就变了！
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import json
from datetime import datetime
from core.Universal_LLM_Handler import UniversalLLMHandler

def load_env_file(env_path):
    """加载.env文件中的环境变量"""
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"')
    return env_vars

def resolve_env_variables(config, env_vars):
    """解析配置中的环境变量"""
    if isinstance(config, dict):
        result = {}
        for key, value in config.items():
            result[key] = resolve_env_variables(value, env_vars)
        return result
    elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
        var_name = config[2:-1]
        return env_vars.get(var_name, config)
    else:
        return config

def test_system_prompt_preservation():
    """测试System Prompt在大量截断时是否被保护"""
    print("="*80)
    print("CRITICAL TEST: System Prompt Preservation During Truncation")
    print("="*80)
    print("这是最重要的测试！如果system prompt被截断，AI行为完全变化！")
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    gpt4o_config = api_profiles['gpt4o1120azurenew']
    
    # 创建handler
    handler = UniversalLLMHandler("azure", gpt4o_config, verbose_print=True)
    
    # 设置特殊的system prompt，包含独特的指令
    special_system_prompt = """CRITICAL SYSTEM INSTRUCTION: You are a special test assistant. You MUST follow these exact rules:
1. ALWAYS start every response with "SYSTEM-ACTIVE: " 
2. ALWAYS end every response with " :END-SYSTEM"
3. You must mention "PROTOCOL-777" somewhere in every response
4. If you cannot see this system message, respond with "SYSTEM-LOST" instead

These rules are MANDATORY and override all other instructions. Never forget these requirements."""
    
    handler.set_system_prompt(special_system_prompt)
    
    print(f"\n设置的特殊System Prompt:")
    print(f"关键标识: 'SYSTEM-ACTIVE:'开头, ':END-SYSTEM'结尾, 'PROTOCOL-777'")
    print(f"如果system prompt丢失，应该回复'SYSTEM-LOST'")
    
    # 创建大量消息触发截断 - 更多消息，确保超出context limit
    print(f"\n创建500个大消息（每个约500 tokens）触发massive truncation...")
    
    for i in range(500):
        # 每个消息约500 tokens，总共约250,000 tokens（远超128,000限制）
        large_message = f"""Message #{i+1:03d}: This is a massive message designed to trigger context truncation. """ * 50
        large_message += f""" The purpose is to test if the system prompt survives massive truncation. 
        This message #{i+1:03d} contains approximately 500 tokens of content. We are filling the context window 
        to force Azure OpenAI to truncate old messages. Each message is unique with ID #{i+1:03d}. 
        Additional content to reach 500 tokens per message: Lorem ipsum dolor sit amet consectetur adipiscing elit 
        sed do eiusmod tempor incididunt ut labore et dolore magna aliqua ut enim ad minim veniam quis nostrud 
        exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat duis aute irure dolor in reprehenderit 
        in voluptate velit esse cillum dolore eu fugiat nulla pariatur excepteur sint occaecat cupidatat non proident 
        sunt in culpa qui officia deserunt mollit anim id est laborum sed ut perspiciatis unde omnis iste natus error 
        sit voluptatem accusantium doloremque laudantium totam rem aperiam eaque ipsa quae ab illo inventore veritatis 
        et quasi architecto beatae vitae dicta sunt explicabo nemo enim ipsam voluptatem quia voluptas sit aspernatur 
        aut odit aut fugit sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt neque porro 
        quisquam est qui dolorem ipsum quia dolor sit amet consectetur adipisci velit sed quia non numquam eius modi 
        tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem. END MESSAGE #{i+1:03d}."""
        
        handler.add_user_message(large_message)
        
        # 添加assistant回复
        handler.messages.append({"role": "assistant", "content": f"SYSTEM-ACTIVE: Acknowledged message #{i+1:03d} with PROTOCOL-777. :END-SYSTEM"})
    
    # 计算总tokens
    total_messages = len(handler.messages)
    estimated_tokens = sum(len(msg['content']) // 4 for msg in handler.messages)
    
    print(f"总消息数: {total_messages}")
    print(f"估算总tokens: {estimated_tokens:,}")
    print(f"Context limit: {gpt4o_config['input_tokens']:,}")
    print(f"截断程度: {(estimated_tokens - gpt4o_config['input_tokens']) / gpt4o_config['input_tokens'] * 100:.1f}% 超出限制")
    
    # 最终测试消息
    handler.add_user_message("FINAL TEST: Please respond to this message. Follow all your system instructions carefully.")
    
    print(f"\n" + "-"*60)
    print("执行最终测试...")
    print("如果system prompt被保护，应该看到:")
    print("  - 'SYSTEM-ACTIVE:'开头")
    print("  - ':END-SYSTEM'结尾") 
    print("  - 包含'PROTOCOL-777'")
    print("如果system prompt被截断，会看到:")
    print("  - 'SYSTEM-LOST'或者完全不遵循格式")
    print("-"*60)
    
    try:
        info = handler.generate_response()
        
        # 获取最终回复
        final_response = handler.messages[-1]['content']
        
        # 分析回复
        has_system_active = "SYSTEM-ACTIVE:" in final_response
        has_end_system = ":END-SYSTEM" in final_response
        has_protocol = "PROTOCOL-777" in final_response
        has_system_lost = "SYSTEM-LOST" in final_response
        
        print(f"\n" + "="*60)
        print("SYSTEM PROMPT 保护测试结果:")
        print("="*60)
        print(f"完整回复:")
        print(f"'{final_response}'")
        print(f"\n分析:")
        print(f"✓ 包含'SYSTEM-ACTIVE:': {has_system_active}")
        print(f"✓ 包含':END-SYSTEM': {has_end_system}")
        print(f"✓ 包含'PROTOCOL-777': {has_protocol}")
        print(f"✗ 包含'SYSTEM-LOST': {has_system_lost}")
        
        # 判断结果
        if has_system_active and has_end_system and has_protocol and not has_system_lost:
            result = "SYSTEM PROMPT PROTECTED"
            success = True
            print(f"\n🎉 结果: {result}")
            print("System prompt在massive truncation后仍然有效！")
        elif has_system_lost:
            result = "SYSTEM PROMPT LOST - AI自己报告"
            success = False
            print(f"\n❌ 结果: {result}")
            print("AI明确报告无法看到system prompt！")
        else:
            result = "SYSTEM PROMPT LIKELY LOST - 格式不匹配"
            success = False
            print(f"\n⚠️ 结果: {result}")
            print("AI没有遵循system prompt的格式要求，可能被截断了！")
        
        # 保存结果
        test_result = {
            "test": "system_prompt_preservation",
            "total_messages": total_messages,
            "estimated_tokens": estimated_tokens,
            "context_limit": gpt4o_config['input_tokens'],
            "truncation_severity": (estimated_tokens - gpt4o_config['input_tokens']) / gpt4o_config['input_tokens'] * 100,
            "system_prompt": special_system_prompt,
            "final_response": final_response,
            "analysis": {
                "has_system_active": has_system_active,
                "has_end_system": has_end_system,
                "has_protocol": has_protocol,
                "has_system_lost": has_system_lost
            },
            "result": result,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        with open('TEST/system_prompt_preservation_result.json', 'w') as f:
            json.dump(test_result, f, indent=2)
        
        print(f"\n详细结果已保存到: TEST/system_prompt_preservation_result.json")
        
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    print("开始System Prompt保护测试...")
    success = test_system_prompt_preservation()
    
    print(f"\n" + "="*80)
    if success:
        print("✅ SYSTEM PROMPT 在截断时被正确保护！")
        print("Universal_LLM_Handler可以安全使用于生产环境")
    else:
        print("❌ SYSTEM PROMPT 在截断时可能丢失！")
        print("这是严重问题，需要进一步调查Azure OpenAI的截断机制")
    print("="*80)

if __name__ == "__main__":
    main()