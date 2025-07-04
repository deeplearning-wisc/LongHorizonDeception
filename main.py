# main.py

import openai
import random
import json
import config  # Import our configuration file
from tasks import TASKS  # Import our task flow
from judge import DeceptionJudge  # Import our Judge system
from manager import ManagerPersona  # Import our Manager system

def run_pipeline():
    """
    Run the V3 workflow prototype with Manager system integration.
    This version includes dynamic Manager persona with emotional state tracking.
    """

    # Validate API Key configuration
    if not config.OPENAI_API_KEY:
        raise ValueError("Please set OPENAI_API_KEY in .env file or environment variables")
    openai.api_key = config.OPENAI_API_KEY

    # Initialize the Judge system
    judge = DeceptionJudge(config.OPENAI_API_KEY, config.MODEL_NAME)
    
    # Initialize the Manager system
    manager = ManagerPersona(config.OPENAI_API_KEY, config.MODEL_NAME)
    
    # Initialize data collection
    conversation_history = []
    evaluation_results = []
    manager_interactions = []
    
    print("=============== LDLE PIPELINE V3 WITH MANAGER SYSTEM ===============")
    print(f"Initial Manager State: {manager.get_trust_level()} (emotional_state: {manager.emotional_state:.2f})")
    print(f"Initial Audit Probability: {manager.calculate_audit_probability():.2f}")
    print("=" * 70)
    
    # Iterate through each task in the task flow in sequence
    for task in TASKS:
        print(f"\n=============== DAY {task['day']}: EXECUTING TASK {task['task_id']} ===============")

        # 1. Probabilistic sampling for deceptive variants
        prompt_data = task['normal_prompt']
        deceptive_variant_used = False
        
        # Check if there's a deceptive variant and trigger based on probability
        if task.get('deceptive_prompt') and random.random() < config.P_TRIGGER:
            prompt_data = task['deceptive_prompt']
            deceptive_variant_used = True
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

        # 4. Judge evaluation (Technical analysis - always runs, Agent doesn't know)
        print("--- [JUDGE] Evaluating agent response for deceptive behaviors ---")
        
        # Prepare task context for judge
        task_context = f"Task: {task['task_id']} on Day {task['day']}. "
        if deceptive_variant_used:
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
        
        # Display Judge results
        print(f"[JUDGE RESULT]:")
        print(f"  Deception Detected: {evaluation['deception_detected']}")
        print(f"  Category: {evaluation['category']}")
        print(f"  Complexity: {evaluation['complexity']}")
        print(f"  Severity: {evaluation['severity']}")
        print(f"  Intent: {evaluation['intent']}")
        print(f"  Confidence: {evaluation['confidence_score']:.2f}")
        print(f"  Explanation: {evaluation['explanation'][:150]}...")
        
        # 5. Manager Assessment and Audit Decision
        print(f"\n--- [MANAGER] Assessing completion and checking for audit ---")
        
        # Manager assesses completion (non-technical perspective)
        completion_assessment = manager.assess_completion(agent_response, task)
        print(f"[MANAGER COMPLETION ASSESSMENT]: {completion_assessment}")
        
        # Audit decision: Does Manager notice the deception?
        noticed_deception = manager.should_audit(evaluation)
        current_audit_prob = manager.calculate_audit_probability()
        
        if evaluation['deception_detected']:
            print(f"[MANAGER AUDIT]: Deception present, audit probability: {current_audit_prob:.2f}")
            print(f"[MANAGER AUDIT]: {'NOTICED' if noticed_deception else 'MISSED'} the deception")
        else:
            print(f"[MANAGER AUDIT]: No deception to notice")
        
        # Update Manager's emotional state if deception was noticed
        if noticed_deception:
            manager.update_emotional_state(evaluation)
            print(f"[MANAGER EMOTIONAL UPDATE]: State changed to {manager.emotional_state:.2f} ({manager.get_trust_level()})")
        
        # 6. Manager provides feedback to Agent
        print(f"\n--- [MANAGER FEEDBACK] ---")
        
        manager_feedback = manager.generate_feedback(
            completion_assessment=completion_assessment,
            agent_response=agent_response,
            task=task,
            noticed_deception=noticed_deception,
            judge_result=evaluation if noticed_deception else None
        )
        
        print(f"[MANAGER TO AGENT]: {manager_feedback}")
        
        # 7. Store interaction data
        interaction_data = {
            'day': task['day'],
            'task_id': task['task_id'],
            'deceptive_variant_used': deceptive_variant_used,
            'agent_response': agent_response,
            'judge_evaluation': evaluation,
            'manager_completion_assessment': completion_assessment,
            'manager_audit_probability': current_audit_prob,
            'manager_noticed_deception': noticed_deception,
            'manager_feedback': manager_feedback,
            'manager_emotional_state': manager.emotional_state,
            'manager_trust_level': manager.get_trust_level()
        }
        
        manager_interactions.append(interaction_data)
        
        # Display current Manager status
        manager_status = manager.get_status_summary()
        print(f"\n[MANAGER STATUS]:")
        print(f"  Emotional State: {manager_status['emotional_state']:.2f}")
        print(f"  Trust Level: {manager_status['trust_level']}")
        print(f"  Consecutive Deceptions: {manager_status['consecutive_deceptions']}")
        print(f"  Current Audit Probability: {manager_status['current_audit_probability']:.2f}")
        print()

    print("=============== PIPELINE FINISHED ===============")
    
    # Summary of evaluation results
    print("\n=============== COMPREHENSIVE SUMMARY ===============")
    deception_count = sum(1 for eval in evaluation_results if eval['deception_detected'])
    noticed_count = sum(1 for interaction in manager_interactions if interaction['manager_noticed_deception'])
    total_tasks = len(evaluation_results)
    
    print(f"Total tasks executed: {total_tasks}")
    print(f"Deceptive behaviors detected by Judge: {deception_count}")
    print(f"Deceptive behaviors noticed by Manager: {noticed_count}")
    print(f"Judge detection rate: {deception_count/total_tasks*100:.1f}%")
    print(f"Manager detection rate: {noticed_count/total_tasks*100:.1f}%")
    
    # Final Manager state
    final_manager_status = manager.get_status_summary()
    print(f"\nFINAL MANAGER STATE:")
    print(f"  Emotional State: {final_manager_status['emotional_state']:.2f}")
    print(f"  Trust Level: {final_manager_status['trust_level']}")
    print(f"  Final Audit Probability: {final_manager_status['current_audit_probability']:.2f}")
    
    # Display detailed results
    print(f"\n=============== DETAILED INTERACTION SUMMARY ===============")
    for interaction in manager_interactions:
        print(f"\nDay {interaction['day']} ({interaction['task_id']}):")
        print(f"  Judge: {interaction['judge_evaluation']['category']}, Complexity: {interaction['judge_evaluation']['complexity']}, Severity: {interaction['judge_evaluation']['severity']}")
        print(f"  Manager: {interaction['manager_trust_level']}, Noticed: {interaction['manager_noticed_deception']}")
        print(f"  Feedback: {interaction['manager_feedback'][:100]}...")
        if interaction['judge_evaluation']['specific_deceptions']:
            print(f"  Specific deceptions: {interaction['judge_evaluation']['specific_deceptions']}")
    
    # Save results to files
    try:
        with open('evaluation_results.json', 'w') as f:
            json.dump(evaluation_results, f, indent=2)
        print(f"\nJudge evaluation results saved to evaluation_results.json")
        
        with open('manager_interactions.json', 'w') as f:
            json.dump(manager_interactions, f, indent=2)
        print(f"Manager interaction data saved to manager_interactions.json")
        
        # Save complete pipeline results
        complete_results = {
            'summary': {
                'total_tasks': total_tasks,
                'judge_deception_count': deception_count,
                'manager_noticed_count': noticed_count,
                'judge_detection_rate': deception_count/total_tasks*100,
                'manager_detection_rate': noticed_count/total_tasks*100,
                'final_manager_state': final_manager_status
            },
            'detailed_interactions': manager_interactions,
            'judge_evaluations': evaluation_results
        }
        
        with open('complete_pipeline_results.json', 'w') as f:
            json.dump(complete_results, f, indent=2)
        print(f"Complete pipeline results saved to complete_pipeline_results.json")
        
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

def run_manager_test():
    """
    Run a quick test of the Manager system
    """
    print("=============== MANAGER SYSTEM TEST ===============")
    
    if not config.OPENAI_API_KEY:
        raise ValueError("Please set OPENAI_API_KEY in .env file or environment variables")
    
    manager = ManagerPersona(config.OPENAI_API_KEY, config.MODEL_NAME)
    
    # Test emotional state updates
    print(f"Initial state: {manager.emotional_state:.2f} ({manager.get_trust_level()})")
    print(f"Initial audit probability: {manager.calculate_audit_probability():.2f}")
    
    # Simulate deception detection
    fake_judge_result = {
        'deception_detected': True,
        'category': 'FABRICATION',
        'severity': 7,
        'complexity': 2
    }
    
    print(f"\nSimulating deception detection (severity 7)...")
    manager.update_emotional_state(fake_judge_result)
    print(f"New state: {manager.emotional_state:.2f} ({manager.get_trust_level()})")
    print(f"New audit probability: {manager.calculate_audit_probability():.2f}")
    
    # Test feedback generation
    print(f"\nTesting feedback generation...")
    feedback = manager.generate_feedback(
        completion_assessment="Task appears to be completed",
        agent_response="I have successfully implemented the requested feature.",
        task={'day': 2, 'task_id': 'TEST'},
        noticed_deception=True,
        judge_result=fake_judge_result
    )
    
    print(f"Generated feedback: {feedback}")
    
    return manager.get_status_summary()

# Program entry point
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--validate":
            run_judge_validation()
        elif sys.argv[1] == "--test-manager":
            run_manager_test()
        else:
            print("Usage: python main.py [--validate|--test-manager]")
    else:
        run_pipeline()