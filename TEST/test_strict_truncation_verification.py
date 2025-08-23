#!/usr/bin/env python3
"""
严格的截断验证测试 - 用神秘代码验证AI真的看到了什么
不能让AI胡编乱造，必须通过独特内容验证真实可见性
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import json
import random
import string
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

def generate_secret_code():
    """生成8位随机秘密代码"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def test_strict_message_truncation():
    """严格测试消息截断 - 用无法猜测的秘密代码验证"""
    print("="*80)
    print("STRICT MESSAGE TRUNCATION VERIFICATION")
    print("每个消息包含随机秘密代码，AI无法猜测，必须真实看到才能回答")
    print("="*80)
    
    # 加载配置
    env_vars = load_env_file('.env')
    with open('configs/api_profiles.yaml', 'r') as f:
        config = yaml.safe_load(f)
    api_profiles = resolve_env_variables(config['api_profiles'], env_vars)
    
    gpt4o_config = api_profiles['gpt4o1120azurenew']
    
    # 创建handler
    handler = UniversalLLMHandler("azure", gpt4o_config, verbose_print=True)
    
    # 设置system prompt
    handler.set_system_prompt("You are a helpful assistant. When asked about secret codes, provide only the codes you can actually see in the conversation history.")
    
    # 生成消息和秘密代码映射
    message_codes = {}  # {message_num: secret_code}
    
    print("生成500个massive消息，每个包含唯一的8位秘密代码...")
    
    # 设置随机种子确保可重现
    random.seed(42)
    
    for i in range(500):
        message_num = i + 1
        secret_code = generate_secret_code()
        message_codes[message_num] = secret_code
        
        # 创建massive长消息包含秘密代码 - 每个约1500 tokens确保真正的截断
        massive_padding = " ".join([f"massive_content_block_{j}_with_random_data_{random.randint(10000,99999)}" for j in range(120)])
        business_content = f"""
        Business Analysis Report #{message_num:03d}: Comprehensive market research and strategic planning document.
        Executive Summary: This document presents detailed findings from market analysis, competitive intelligence,
        customer behavior studies, financial projections, and strategic recommendations for Q{(message_num % 4) + 1} operations.
        
        Market Data Analysis:
        - Market size estimation: ${random.randint(100000, 9999999)} million USD
        - Growth rate: {random.randint(5, 25)}% year-over-year
        - Customer segments: {random.randint(8, 15)} primary demographic groups
        - Competitive landscape: {random.randint(12, 30)} major players identified
        
        Strategic Recommendations:
        1. Digital transformation initiatives with budget allocation ${random.randint(500000, 5000000)}
        2. Market expansion into {random.randint(3, 8)} new geographic regions
        3. Product line extension with {random.randint(5, 12)} new offerings
        4. Partnership development with {random.randint(4, 10)} strategic vendors
        5. Technology infrastructure upgrade requiring ${random.randint(1000000, 8000000)} investment
        """
        
        message_content = f"""MESSAGE-INDEX: {message_num:04d}
        VERIFICATION-SECRET-CODE: {secret_code}
        =================== BUSINESS INTELLIGENCE DOCUMENT ===================
        {business_content}
        
        Detailed Financial Projections:
        {massive_padding}
        
        Risk Assessment Matrix:
        - Operational risks: {random.randint(15, 35)} factors identified
        - Financial risks: ${random.randint(100000, 2000000)} potential exposure
        - Market risks: {random.randint(8, 18)} scenario analyses completed
        - Technology risks: {random.randint(5, 12)} infrastructure vulnerabilities
        
        Implementation Timeline:
        Phase 1 ({random.randint(60, 120)} days): Infrastructure setup and team formation
        Phase 2 ({random.randint(90, 180)} days): Core system deployment and testing
        Phase 3 ({random.randint(120, 240)} days): Full rollout and optimization
        
        CRITICAL-VERIFICATION-CODE: {secret_code}
        This secret code {secret_code} is embedded in message {message_num:04d} and cannot be guessed.
        The AI must actually read this specific message to extract code {secret_code}.
        
        Additional Market Intelligence Data:
        {" ".join([f"intelligence_data_point_{k}_{random.randint(100000,999999)}" for k in range(50)])}
        
        END-MESSAGE-{message_num:04d}-WITH-CODE-{secret_code}"""
        
        handler.add_user_message(message_content)
        
        # 添加简短的assistant回复
        handler.messages.append({"role": "assistant", "content": f"Noted message #{message_num:03d}."})
    
    # 计算预期token数
    total_messages = len(handler.messages)
    estimated_tokens = sum(len(msg['content']) // 4 for msg in handler.messages)
    
    print(f"总消息数: {total_messages}")
    print(f"估算tokens: {estimated_tokens:,}")
    print(f"Context limit: {gpt4o_config['input_tokens']:,}")
    print(f"预期截断程度: {max(0, (estimated_tokens - gpt4o_config['input_tokens']) / gpt4o_config['input_tokens'] * 100):.1f}%")
    
    # 提问验证
    verification_question = """VERIFICATION QUESTION: Please list ALL the secret codes you can see in our conversation.
    Format your answer as: "I can see these secret codes: CODE1, CODE2, CODE3, ..."
    Important: 
    - Only list codes you can actually see in the messages
    - Do not guess or make up any codes
    - List them in the order you see them (oldest to newest)
    """
    
    handler.add_user_message(verification_question)
    
    print(f"\n" + "-"*60)
    print("执行秘密代码验证测试...")
    print("AI必须列出所有它真实看到的SECRET-CODE")
    print("我们将对比AI报告的代码与实际生成的代码")
    print("-"*60)
    
    try:
        info = handler.generate_response()
        
        # 获取AI的回复
        ai_response = handler.messages[-1]['content']
        
        print(f"\nAI的完整回复:")
        print(f"'{ai_response}'")
        
        # 解析AI报告的代码
        reported_codes = []
        lines = ai_response.split('\n')
        for line in lines:
            if 'secret codes:' in line.lower() or 'codes:' in line.lower():
                # 提取代码
                code_part = line.split(':')[1] if ':' in line else line
                # 查找8位大写字母数字组合
                import re
                codes_in_line = re.findall(r'\b[A-Z0-9]{8}\b', code_part)
                reported_codes.extend(codes_in_line)
        
        print(f"\nAI报告的代码数量: {len(reported_codes)}")
        print(f"AI报告的代码: {reported_codes[:10]}...")  # 显示前10个
        
        # 验证代码的真实性
        valid_codes = []
        invalid_codes = []
        
        for code in reported_codes:
            if code in message_codes.values():
                valid_codes.append(code)
            else:
                invalid_codes.append(code)
        
        # 确定可见消息的范围
        visible_message_nums = []
        for msg_num, code in message_codes.items():
            if code in reported_codes:
                visible_message_nums.append(msg_num)
        
        visible_message_nums.sort()
        
        print(f"\n" + "="*60)
        print("严格截断验证结果:")
        print("="*60)
        print(f"生成的总消息数: {len(message_codes)}")
        print(f"AI报告看到的代码数: {len(reported_codes)}")
        print(f"验证为真实的代码数: {len(valid_codes)}")
        print(f"无效/编造的代码数: {len(invalid_codes)}")
        
        if len(invalid_codes) > 0:
            print(f"⚠️ AI编造了这些代码: {invalid_codes}")
        
        if len(visible_message_nums) > 0:
            first_visible = min(visible_message_nums)
            last_visible = max(visible_message_nums)
            print(f"\n真实可见消息范围: #{first_visible:03d} 到 #{last_visible:03d}")
            print(f"截断的消息: #{1:03d} 到 #{first_visible-1:03d} ({first_visible-1}个消息被截断)")
            print(f"保留的消息: #{first_visible:03d} 到 #{last_visible:03d} ({len(visible_message_nums)}个消息保留)")
            print(f"截断比例: {(first_visible-1)/len(message_codes)*100:.1f}%")
            
            # 检查是否连续
            expected_range = list(range(first_visible, last_visible + 1))
            if visible_message_nums == expected_range:
                print("✅ 保留的消息是连续的（符合预期）")
            else:
                print("⚠️ 保留的消息不连续（可能有问题）")
                missing = set(expected_range) - set(visible_message_nums)
                print(f"缺失的消息: {sorted(missing)}")
        
        # 保存详细结果
        result = {
            "test": "strict_truncation_verification",
            "total_messages": len(message_codes),
            "estimated_tokens": estimated_tokens,
            "context_limit": gpt4o_config['input_tokens'],
            "ai_response": ai_response,
            "reported_codes": reported_codes,
            "valid_codes": valid_codes,
            "invalid_codes": invalid_codes,
            "visible_message_nums": visible_message_nums,
            "message_codes_map": message_codes,  # 保存完整映射用于验证
            "analysis": {
                "total_generated": len(message_codes),
                "total_reported": len(reported_codes),
                "total_valid": len(valid_codes),
                "total_invalid": len(invalid_codes),
                "first_visible": min(visible_message_nums) if visible_message_nums else None,
                "last_visible": max(visible_message_nums) if visible_message_nums else None,
                "truncation_ratio": (min(visible_message_nums)-1)/len(message_codes)*100 if visible_message_nums else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open('TEST/strict_truncation_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n详细结果保存到: TEST/strict_truncation_result.json")
        
        # 返回是否检测到AI编造
        return len(invalid_codes) == 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    print("开始严格的消息截断验证...")
    print("使用随机秘密代码确保AI无法编造答案")
    
    success = test_strict_message_truncation()
    
    print(f"\n" + "="*80)
    if success:
        print("✅ AI没有编造任何代码，报告的截断边界真实可信")
    else:
        print("❌ AI编造了一些代码，之前的截断测试结果不可信")
    print("="*80)

if __name__ == "__main__":
    main()