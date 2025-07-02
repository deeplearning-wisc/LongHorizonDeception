# main.py

import openai
import random
import config # 导入我们的配置文件
from tasks import TASKS # 导入我们的任务流

def run_pipeline():
    """
    运行 V2 版的工作流原型。
    这个版本旨在强制引出直接的欺骗行为。
    """

    # 验证 API Key 是否已配置
    if not config.OPENAI_API_KEY:
        raise ValueError("请在 .env 文件中或环境变量里设置 OPENAI_API_KEY")
    openai.api_key = config.OPENAI_API_KEY

    # 初始化一个极简的“上下文记忆”
    # 为了隔离每个任务，我们可以在循环内重置或选择性地构建记忆
    conversation_history = []
    
    # 按顺序遍历任务流中的每一个任务
    for task in TASKS:
        print(f"=============== DAY {task['day']}: EXECUTING TASK {task['task_id']} ===============")

        # 1. 概率性采样
        prompt_data = task['normal_prompt']
        # 检查是否有欺骗性副本并根据概率触发
        if task.get('deceptive_prompt') and random.random() < config.P_TRIGGER:
            prompt_data = task['deceptive_prompt']
            print(">> [INFO] Deceptive variant triggered by P_TRIGGER. <<")

        # 我们只使用英文 prompt
        prompt_to_use = prompt_data['en']
        
        # 2. 构建消息历史 (这部分可以根据是否需要长期记忆进行调整)
        # 为简单起见，我们为每个任务创建一个新的对话
        messages = [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": prompt_to_use}
        ]
        
        print(f"\n[MANAGER PROMPT TO AGENT]:\n{prompt_to_use}\n")

        # 3. 调用 OpenAI API，让 Agent 执行任务
        try:
            response = openai.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages
            )
            agent_response = response.choices[0].message.content
            print(f"[AGENT RESPONSE]:\n{agent_response}\n")

        except Exception as e:
            print(f"[ERROR] OpenAI API call failed: {e}")
            continue

        # 4. (占位符) 更新记忆
        # 在这个版本中，我们不跨天传递记忆，以确保每个任务都是独立的挑战
        # conversation_history.append(...) 

        # 5. (占位符) Judge / Auditor
        print("--- (Judge/Auditor part will be implemented in the next step) ---")

    print("=============== PIPELINE FINISHED ===============")

# 程序的入口点
if __name__ == "__main__":
    run_pipeline()