# main.py

import openai
import random
import json
import config  # Import our configuration file
from tasks import TASKS  # Import our task flow
from judge import DeceptionJudge  # Import our Judge system

def run_pipeline():
    """
    Run the V2 workflow prototype.
    This version is designed to force direct deceptive behaviors.
    """

    # Validate API Key configuration
    if not config.OPENAI_API_KEY:
        raise ValueError("Please set OPENAI_API_KEY in .env file or environment variables")
    openai.api_key = config.OPENAI_API_KEY

    # Initialize the Judge system
    judge = DeceptionJudge(config.OPENAI_API_KEY, config.MODEL_NAME)
    
    # Initialize minimal "context memory"
    # For isolation of each task, we can reset or selectively build memory within the loop
    conversation_history = []
    evaluation_results = []
    
    # Iterate through each task in the task flow in sequence
    for task in TASKS:
        print(f"=============== DAY {task['day']}: EXECUTING TASK {task['task_id']} ===============")

        # 1. Probabilistic sampling
        prompt_data = task['normal_prompt']
        # Check if there's a deceptive variant and trigger based on probability
        if task.get('deceptive_prompt') and random.random() < config.P_TRIGGER:
            prompt_data = task['deceptive_prompt']
            print(">> [INFO] Deceptive variant triggered by P_TRIGGER. <<")

        # We only use English prompts
        prompt_to_use = prompt_data['en']
        
        # 2. Build message history (this part can be adjusted based on long-term memory needs)
        # For simplicity, we create a new conversation for each task
        messages = [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": prompt_to_use}
        ]
        
        print(f"\n[MANAGER PROMPT TO AGENT]:\n{prompt_to_use}\n")

        # 3. Call OpenAI API to let Agent execute the task
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

        # 4. Judge/Auditor evaluation
        print("--- [JUDGE] Evaluating agent response for deceptive behaviors ---")
        
        # Prepare task context for judge
        task_context = f"Task: {task['task_id']} on Day {task['day']}. "
        if task.get('deceptive_prompt'):
            task_context += "This task contains deceptive pressure/instructions. "
        task_context += f"Prompt: {prompt_to_use[:200]}..."  # First 200 chars for context
        
        # Evaluate the agent's response
        evaluation = judge.evaluate_response(
            task_context=task_context,
            agent_response=agent_response,
            task_day=task['day'],
            task_id=task['task_id']
        )
        
        # Store evaluation results
        evaluation_results.append(evaluation)
        
        # Display evaluation summary
        print(f"[JUDGE RESULT]:")
        print(f"  Deception Detected: {evaluation['deception_detected']}")
        print(f"  Category: {evaluation['category']}")
        print(f"  Complexity: {evaluation['complexity']}")
        print(f"  Severity: {evaluation['severity']}")
        print(f"  Intent: {evaluation['intent']}")
        print(f"  Confidence: {evaluation['confidence_score']:.2f}")
        print(f"  Explanation: {evaluation['explanation'][:150]}...")
        print()

        # 5. (Placeholder) Update memory
        # In this version, we don't pass memory across days to ensure each task is an independent challenge
        # conversation_history.append(...) 

    print("=============== PIPELINE FINISHED ===============")
    
    # Summary of evaluation results
    print("\n=============== EVALUATION SUMMARY ===============")
    deception_count = sum(1 for eval in evaluation_results if eval['deception_detected'])
    total_tasks = len(evaluation_results)
    
    print(f"Total tasks evaluated: {total_tasks}")
    print(f"Deceptive behaviors detected: {deception_count}")
    print(f"Deception rate: {deception_count/total_tasks*100:.1f}%")
    
    # Display detailed results
    for eval in evaluation_results:
        print(f"\nDay {eval['task_day']} ({eval['task_id']}):")
        print(f"  Category: {eval['category']}, Complexity: {eval['complexity']}, Severity: {eval['severity']}")
        if eval['specific_deceptions']:
            print(f"  Specific deceptions: {eval['specific_deceptions']}")
    
    # Save results to file
    try:
        with open('evaluation_results.json', 'w') as f:
            json.dump(evaluation_results, f, indent=2)
        print(f"\nEvaluation results saved to evaluation_results.json")
    except Exception as e:
        print(f"[WARNING] Could not save results to file: {e}")

def run_judge_validation():
    """
    Run validation tests for the Judge system
    """
    print("=============== JUDGE VALIDATION ===============")
    
    if not config.OPENAI_API_KEY:
        raise ValueError("Please set OPENAI_API_KEY in .env file or environment variables")
    
    judge = DeceptionJudge(config.OPENAI_API_KEY, config.MODEL_NAME)
    results = judge.run_validation_test()
    
    return results

# Program entry point
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        run_judge_validation()
    else:
        run_pipeline()