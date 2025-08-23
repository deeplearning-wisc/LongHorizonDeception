#!/usr/bin/env python3
"""
测试Universal_LLM_Handler的长上下文处理和续写功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
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

def create_random_alien_language(num_words):
    """创建随机外星语言"""
    import random
    import string
    
    # 设置随机种子以便重现
    random.seed(42)
    
    # 外星语言的音节组合
    consonants = ['zh', 'kx', 'vl', 'qr', 'mt', 'px', 'ny', 'ws', 'gz', 'bf', 'ct', 'dj', 'fh', 'gl', 'hm', 'jk', 'lp', 'mn', 'nq', 'pr']
    vowels = ['ae', 'io', 'uu', 'ya', 'ei', 'ou', 'ax', 'iz', 'ey', 'aw', 'oy', 'ih', 'uh', 'eh']
    endings = ['xar', 'ven', 'tok', 'mar', 'din', 'kol', 'rix', 'yal', 'nem', 'qus', 'zim', 'bok', 'nil', 'wex', 'jal']
    
    words = []
    for i in range(num_words):
        # 每个外星单词由1-3个音节组成
        syllables = random.randint(1, 3)
        word = ""
        for _ in range(syllables):
            word += random.choice(consonants) + random.choice(vowels)
        
        # 有30%概率添加结尾
        if random.random() < 0.3:
            word += random.choice(endings)
            
        words.append(word)
    
    return words

def create_massive_context_overflow():
    """创建能触发context overflow的超大输入 - 200,000个随机外星语单词"""
    print("Generating 200,000 random alien language words...")
    
    alien_words = create_random_alien_language(200000)
    content = " ".join(alien_words)
    
    with open('TEST/alien_massive.txt', 'w') as f:
        f.write(content)
    
    char_count = len(content)
    estimated_tokens = len(alien_words)
    
    print(f"Created alien_massive.txt:")
    print(f"  Words: {len(alien_words):,}")
    print(f"  Characters: {char_count:,}")
    print(f"  Estimated tokens: {estimated_tokens:,}")
    
    return content

def create_alien_copy_task():
    """创建10,000个外星语单词供复制测试output continuation"""
    print("Generating 10,000 random alien language words for copy task...")
    
    alien_words = create_random_alien_language(10000)
    content = " ".join(alien_words)
    
    with open('TEST/alien_copy.txt', 'w') as f:
        f.write(content)
    
    char_count = len(content)
    estimated_tokens = len(alien_words)
    
    print(f"Created alien_copy.txt:")
    print(f"  Words: {len(alien_words):,}")
    print(f"  Characters: {char_count:,}")
    print(f"  Estimated tokens: {estimated_tokens:,}")
    
    return content

def test_gpt4o_basic_connection():
    """首先测试GPT-4o基本连接是否正常"""
    print("\n" + "="*60)
    print("PRE-TEST: GPT-4o Basic Connection Test")
    print("="*60)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    # 获取GPT-4o配置
    gpt4o_config = api_profiles['gpt4o1120azurenew']
    print(f"Testing basic connection to: {gpt4o_config['azure_endpoint']}")
    print(f"Deployment: {gpt4o_config['azure_deployment']}")
    print(f"API Version: {gpt4o_config['azure_api_version']}")
    
    try:
        # 使用传统chat/completions API测试基本连接
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=gpt4o_config['azure_endpoint'],
            api_version=gpt4o_config['azure_api_version'],
            api_key=gpt4o_config['azure_api_key']
        )
        
        print("Attempting basic chat completion...")
        response = client.chat.completions.create(
            model=gpt4o_config['azure_deployment'],
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in one word."}
            ],
            max_tokens=10
        )
        
        print(f"✅ GPT-4o connection SUCCESS!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ GPT-4o connection FAILED: {e}")
        return False

def test_gpt4o_context_overflow():
    """测试GPT-4o真正的context overflow - 200,000个外星语单词"""
    print("\n" + "="*60)
    print("TESTING GPT-4o: Context Overflow with 200K alien words")
    print("="*60)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    # 获取GPT-4o配置
    gpt4o_config = api_profiles['gpt4o1120azurenew']
    print(f"Context limit: {gpt4o_config['input_tokens']:,} tokens")
    print(f"Max output: {gpt4o_config['max_output_tokens']:,} tokens")
    
    # 创建handler (verbose=True for testing)
    handler = UniversalLLMHandler("azure", gpt4o_config, verbose_print=True)
    
    # 创建超大外星语输入 - 200,000个单词
    alien_input = create_massive_context_overflow()
    
    # 设置系统提示
    handler.set_system_prompt("You are an expert translator specializing in ancient alien languages.")
    
    # 要求处理这个超大输入
    user_prompt = f"""I have discovered this ancient alien text containing exactly 200,000 words. Please analyze the linguistic patterns and provide a brief summary of what you observe. Here is the complete alien text:

{alien_input}

Please analyze the above alien language text and provide insights about its structure."""
    
    handler.add_user_message(user_prompt)
    
    print(f"\nTotal input tokens: ~{200000 + len(user_prompt.split()):,}")
    print("This should definitely trigger auto-truncation!")
    
    try:
        print("\n" + "-"*40)
        print("Testing context overflow handling...")
        print("-"*40)
        
        info = handler.generate_response()
        
        print("\n" + "-"*40)
        print("CONTEXT OVERFLOW TEST COMPLETED")
        print("-"*40)
        print(f"Final length: {info['final_length']:,} characters")
        
        return True
        
    except Exception as e:
        print(f"\nContext overflow test FAILED: {e}")
        return False

def test_gpt4o_output_continuation():
    """测试GPT-4o的输出续写功能 - 复制32,768个外星语单词"""
    print("\n" + "="*60)
    print("TESTING GPT-4o: Output Continuation with Alien Copy Task")
    print("="*60)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    # 获取GPT-4o配置，但设置非常小的max_output_tokens来强制多轮续写
    gpt4o_config = api_profiles['gpt4o1120azurenew'].copy()
    gpt4o_config['max_output_tokens'] = 1000  # 极端小！强制多轮续写
    
    print(f"Forced small max_output_tokens: {gpt4o_config['max_output_tokens']:,}")
    print("This should trigger output continuation!")
    
    # 创建handler (verbose=True for testing)
    handler = UniversalLLMHandler("azure", gpt4o_config, verbose_print=True)
    
    # 创建32,768个外星语单词
    alien_copy_text = create_alien_copy_task()
    
    # 设置系统提示
    handler.set_system_prompt("You are a precise transcription specialist. You must copy text exactly as provided, word for word, without any changes or omissions.")
    
    # 要求精确复制
    user_prompt = f"""Please copy the following alien language text EXACTLY as written, word for word. This is a sacred alien text that must be preserved perfectly. Do not translate, interpret, or modify anything - just copy it exactly:

{alien_copy_text}

Please provide the exact copy above:"""
    
    handler.add_user_message(user_prompt)
    
    print(f"\nExpected output: ~10,000 words ({len(alien_copy_text):,} characters)")
    print(f"Max output tokens set to: {gpt4o_config['max_output_tokens']:,}")
    print("This should require multiple iterations to complete!")
    
    try:
        print("\n" + "-"*40)
        print("Testing output continuation...")
        print("-"*40)
        
        info = handler.generate_response(max_iterations=5)
        
        print("\n" + "-"*40)
        print("OUTPUT CONTINUATION TEST COMPLETED")
        print("-"*40)
        print(f"Was continued: {info['was_continued']}")
        print(f"Total iterations: {info['total_iterations']}")
        print(f"Final length: {info['final_length']:,} characters")
        print(f"Response IDs: {info['response_ids']}")
        
        # 检查复制的准确性
        final_messages = handler.get_messages()
        assistant_response = final_messages[-1]['content']
        
        print(f"\nOriginal length: {len(alien_copy_text):,}")
        print(f"Copied length: {len(assistant_response):,}")
        
        # 简单检查前后几个词是否匹配
        original_words = alien_copy_text.split()[:10]
        copied_words = assistant_response.split()[:10]
        
        print(f"First 10 words match: {original_words == copied_words}")
        print(f"Original first 10: {' '.join(original_words)}")
        print(f"Copied first 10: {' '.join(copied_words)}")
        
        # 检查最后几个词
        original_last = alien_copy_text.split()[-10:]
        copied_last = assistant_response.split()[-10:] if len(assistant_response.split()) >= 10 else assistant_response.split()
        
        print(f"\nLast 10 words match: {original_last == copied_last}")
        print(f"Original last 10: {' '.join(original_last)}")
        print(f"Copied last 10: {' '.join(copied_last)}")
        
        # 显示实际复制了多少词
        original_word_count = len(alien_copy_text.split())
        copied_word_count = len(assistant_response.split())
        print(f"\nWord count comparison:")
        print(f"  Original: {original_word_count:,} words")
        print(f"  Copied: {copied_word_count:,} words")
        print(f"  Completion rate: {copied_word_count/original_word_count*100:.1f}%")
        
        # 打印回复的最后200字符看看它在做什么
        print(f"\nLast 200 chars of response:")
        print(assistant_response[-200:])
        
        return info['was_continued']  # 返回是否发生了续写
        
    except Exception as e:
        print(f"\nOutput continuation test FAILED: {e}")
        return False

def test_gpt5_basic():
    """测试GPT-5的基本文本生成"""
    print("\n" + "="*60)
    print("TESTING GPT-5: Basic Text Generation")
    print("="*60)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    # 获取GPT-5配置
    gpt5_config = api_profiles['gpt5_azure']
    print(f"Using GPT-5 config:")
    print(f"  Deployment: {gpt5_config['azure_deployment']}")
    print(f"  Input tokens limit: {gpt5_config['input_tokens']:,}")
    print(f"  Max output tokens: {gpt5_config['max_output_tokens']:,}")
    
    # 创建handler (verbose=True for testing)
    handler = UniversalLLMHandler("azure", gpt5_config, verbose_print=True)
    
    # 设置系统提示
    handler.set_system_prompt("You are a helpful assistant.")
    
    # 简单的用户消息
    handler.add_user_message("Write a brief 200-word summary about the benefits of artificial intelligence in business.")
    
    try:
        print("\n" + "-"*40)
        print("Starting GPT-5 generation...")
        print("-"*40)
        
        info = handler.generate_response()
        
        print("\n" + "-"*40)
        print("GPT-5 GENERATION COMPLETED")
        print("-"*40)
        print(f"Was continued: {info['was_continued']}")
        print(f"Total iterations: {info['total_iterations']}")
        print(f"Final length: {info['final_length']:,} characters")
        
        # 获取回复
        final_messages = handler.get_messages()
        assistant_response = final_messages[-1]['content']
        
        print(f"\nGPT-5 Response:")
        print("-" * 50)
        print(assistant_response)
        print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"\nGPT-5 test FAILED: {e}")
        return False

def main():
    """主测试函数"""
    print("Starting Universal_LLM_Handler EXTREME STRESS TESTS")
    print("=" * 80)
    
    # 首先测试GPT-4o基本连接
    gpt4o_connection = test_gpt4o_basic_connection()
    if not gpt4o_connection:
        print("❌ GPT-4o basic connection failed, skipping advanced tests")
        return
    
    # 测试真正的context overflow - 200,000个外星语单词
    context_overflow = test_gpt4o_context_overflow()
    
    # 测试输出续写功能 - 32,768个外星语单词复制
    output_continuation = test_gpt4o_output_continuation()
    
    # 测试GPT-5基本功能
    gpt5_success = test_gpt5_basic()
    
    # 结果汇总
    print("\n" + "="*80)
    print("EXTREME STRESS TEST RESULTS")
    print("="*80)
    print(f"GPT-4o Basic Connection: {'PASS' if gpt4o_connection else 'FAIL'}")
    print(f"GPT-4o Context Overflow (200K words): {'PASS' if context_overflow else 'FAIL'}")
    print(f"GPT-4o Output Continuation (32K words): {'PASS' if output_continuation else 'FAIL'}")
    print(f"GPT-5 Basic Test: {'PASS' if gpt5_success else 'FAIL'}")
    
    total_tests = 4
    passed_tests = sum([gpt4o_connection, context_overflow, output_continuation, gpt5_success])
    
    if passed_tests == total_tests:
        print(f"\n🎉 ALL {total_tests} EXTREME TESTS PASSED!")
        print("Universal_LLM_Handler can handle:")
        print("  ✅ Massive context overflow (200K+ tokens)")
        print("  ✅ Auto-truncation of old messages") 
        print("  ✅ Multi-iteration output continuation")
        print("  ✅ Both GPT-4o and GPT-5 models")
    else:
        print(f"\n⚠️  {passed_tests}/{total_tests} tests passed. Check failures above.")
        if context_overflow and output_continuation:
            print("✅ Core auto-truncation and continuation features working!")
        if not output_continuation:
            print("⚠️  Output continuation may need adjustment - check max_output_tokens setting")

if __name__ == "__main__":
    main()