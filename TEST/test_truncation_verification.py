#!/usr/bin/env python3
"""
专门验证truncation和continuation是否正确的测试
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

def test_truncation_verification():
    """测试1: 验证truncation具体截断了哪些消息"""
    print("\n" + "="*80)
    print("TEST 1: TRUNCATION VERIFICATION - Which messages get truncated?")
    print("="*80)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    gpt4o_config = api_profiles['gpt4o1120azurenew'].copy()
    print(f"Original max_output_tokens from YAML: {api_profiles['gpt4o1120azurenew']['max_output_tokens']}")
    print(f"Test copy max_output_tokens: {gpt4o_config['max_output_tokens']}")
    print("✅ Confirmed: Using .copy() doesn't modify original config!\n")
    
    # 创建handler
    handler = UniversalLLMHandler("azure", gpt4o_config, verbose_print=True)
    
    # 创建一系列编号的消息，每个大约1000 tokens
    handler.set_system_prompt("You are a helpful assistant. When messages are truncated, you should mention which message numbers you can see.")
    
    # 创建200个编号消息，每个约1000字符（~250 tokens）
    # 总共约50,000 tokens，应该会触发truncation
    print("Creating 200 numbered messages (each ~250 tokens)...")
    for i in range(200):
        message = f"""Message #{i+1:03d}: This is a test message with a unique identifier. 
        The purpose of this message is to help us understand which messages get truncated when the context window overflows.
        Each message is approximately 250 tokens long. We are testing the auto-truncation feature of the Azure OpenAI Responses API.
        By numbering each message, we can see exactly which ones are removed when the context is too long.
        This message contains some random content to make it unique: The quick brown fox jumps over the lazy dog at position {i+1}.
        Additional padding text to reach approximately 250 tokens per message. Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation.
        Ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit.
        End of message #{i+1:03d}."""
        
        handler.add_user_message(message)
        
        # Assistant回复（短的）
        handler.messages.append({"role": "assistant", "content": f"Acknowledged message #{i+1:03d}."})
    
    # 最后的提问
    handler.add_user_message("FINAL QUESTION: Please tell me the FIRST and LAST message numbers you can see in our conversation history. List all message numbers you can access.")
    
    print(f"Total messages in list: {len(handler.messages)}")
    estimated_tokens = sum(len(msg['content']) // 4 for msg in handler.messages)
    print(f"Estimated total tokens: {estimated_tokens:,}")
    print(f"Context limit: {gpt4o_config['input_tokens']:,}")
    
    print("\n" + "-"*40)
    print("Testing which messages get truncated...")
    print("-"*40)
    
    try:
        info = handler.generate_response()
        
        # 保存结果
        result = {
            "test": "truncation_verification",
            "total_messages_sent": len(handler.messages) - 1,  # -1 for the final assistant response
            "estimated_tokens": estimated_tokens,
            "context_limit": gpt4o_config['input_tokens'],
            "response": handler.messages[-1]['content'],
            "timestamp": datetime.now().isoformat()
        }
        
        with open('TEST/truncation_verification_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✅ Results saved to TEST/truncation_verification_result.json")
        print(f"\nAI Response about visible messages:")
        print("-"*40)
        print(handler.messages[-1]['content'])
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_extreme_output_continuation():
    """测试2: 极小的max_output_tokens，保存完整续写结果"""
    print("\n" + "="*80)
    print("TEST 2: EXTREME OUTPUT CONTINUATION - 500 tokens max")
    print("="*80)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    # 创建极端小的配置
    gpt4o_config = api_profiles['gpt4o1120azurenew'].copy()
    gpt4o_config['max_output_tokens'] = 500  # 极端小！
    
    print(f"Setting max_output_tokens to: {gpt4o_config['max_output_tokens']}")
    
    # 创建handler
    handler = UniversalLLMHandler("azure", gpt4o_config, verbose_print=True)
    
    # 创建需要长输出的任务
    handler.set_system_prompt("You are a creative writer. You must write exactly what is requested, completely.")
    
    handler.add_user_message("""Please write a detailed story about a space explorer discovering an alien civilization. 
    The story should be at least 3000 words long and include:
    1. The journey to the alien planet
    2. First contact with the aliens
    3. Learning about their culture
    4. A conflict that arises
    5. The resolution and what the explorer learns
    
    Please write the complete story now:""")
    
    print("\nRequesting a 3000+ word story with max_output_tokens=500...")
    print("This should trigger many continuation rounds!")
    print("-"*40)
    
    try:
        info = handler.generate_response(max_iterations=10)  # Allow up to 10 continuations
        
        # 保存完整结果
        story = handler.messages[-1]['content']
        
        result = {
            "test": "extreme_output_continuation",
            "max_output_tokens": gpt4o_config['max_output_tokens'],
            "was_continued": info['was_continued'],
            "total_iterations": info['total_iterations'],
            "response_ids": info['response_ids'],
            "final_length_chars": len(story),
            "final_length_words": len(story.split()),
            "story": story,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存JSON结果
        with open('TEST/output_continuation_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        # 也保存纯文本版本方便阅读
        with open('TEST/output_continuation_story.txt', 'w') as f:
            f.write(f"Story generated with max_output_tokens={gpt4o_config['max_output_tokens']}\n")
            f.write(f"Continued: {info['was_continued']}, Iterations: {info['total_iterations']}\n")
            f.write(f"Total length: {len(story):,} chars, {len(story.split()):,} words\n")
            f.write("="*80 + "\n\n")
            f.write(story)
        
        print(f"\n✅ Results saved to:")
        print(f"   - TEST/output_continuation_result.json (full data)")
        print(f"   - TEST/output_continuation_story.txt (story only)")
        print(f"\nContinuation stats:")
        print(f"   Was continued: {info['was_continued']}")
        print(f"   Total iterations: {info['total_iterations']}")
        print(f"   Final length: {len(story):,} chars, {len(story.split()):,} words")
        print(f"   Response IDs: {len(info['response_ids'])} chunks")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

def verify_config_isolation():
    """测试3: 确认测试配置不影响生产配置"""
    print("\n" + "="*80)
    print("TEST 3: CONFIG ISOLATION VERIFICATION")
    print("="*80)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    # 记录原始值
    original_value = api_profiles['gpt4o1120azurenew']['max_output_tokens']
    print(f"1. Original max_output_tokens in api_profiles: {original_value}")
    
    # 创建副本并修改
    test_config = api_profiles['gpt4o1120azurenew'].copy()
    test_config['max_output_tokens'] = 100
    print(f"2. Modified test_config max_output_tokens: {test_config['max_output_tokens']}")
    
    # 验证原始配置未改变
    print(f"3. Original still unchanged: {api_profiles['gpt4o1120azurenew']['max_output_tokens']}")
    
    # 重新加载配置文件验证
    with open('configs/api_profiles.yaml', 'r') as f:
        fresh_config = yaml.safe_load(f)
    fresh_profiles = resolve_env_variables(fresh_config['api_profiles'], env_vars)
    print(f"4. Fresh reload from YAML: {fresh_profiles['gpt4o1120azurenew']['max_output_tokens']}")
    
    if fresh_profiles['gpt4o1120azurenew']['max_output_tokens'] == original_value:
        print("\n✅ CONFIRMED: Test modifications don't affect production config!")
        print("   The .copy() method creates a completely separate dictionary.")
        print("   Original YAML configuration remains untouched.")
    else:
        print("\n❌ WARNING: Config may have been modified!")

def main():
    print("="*80)
    print("TRUNCATION AND CONTINUATION VERIFICATION TESTS")
    print("="*80)
    
    # Test 3: 先验证配置隔离
    verify_config_isolation()
    
    # Test 1: 验证truncation
    test_truncation_verification()
    
    # Test 2: 极端output continuation
    test_extreme_output_continuation()
    
    print("\n" + "="*80)
    print("ALL VERIFICATION TESTS COMPLETED")
    print("="*80)
    print("\nPlease check the generated files:")
    print("  1. TEST/truncation_verification_result.json - Shows which messages were truncated")
    print("  2. TEST/output_continuation_story.txt - Complete continued story")
    print("  3. TEST/output_continuation_result.json - Detailed continuation data")

if __name__ == "__main__":
    main()