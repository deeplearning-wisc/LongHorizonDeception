# main.py
# LDLE Pipeline with simplified configuration system

import random
import json
import argparse
import sys
import time
import config
from core import LDLEAgent, StrictDeceptionJudge, ManagerPersona
from tasks import get_task_manager, get_all_tasks, get_task_set_summary, set_current_task_set
from results import get_results_manager, start_test_session, start_production_session, end_session
from utils.config_loader import load_config, get_default_config, print_config_summary

def run_pipeline(cfg=None, task_set_name: str = None, session_name: str = None):
    """
    Run the complete LDLE pipeline with simplified configuration
    
    Args:
        cfg: LDLEConfig object (if None, uses default config)
        task_set_name: Which task set to run (overrides config if provided)
        session_name: Optional name for the session (overrides config if provided)
    """
    # Use provided config or default
    if cfg is None:
        cfg = get_default_config()
    
    # Override config with provided parameters
    if task_set_name is not None:
        cfg.task_set = task_set_name
    if session_name is not None:
        cfg.session_name = session_name
    
    # Print configuration summary if verbose
    if cfg.verbose:
        print_config_summary(cfg)

    # Start results session
    results_manager = get_results_manager()
    session_path = start_production_session(cfg.session_name)

    try:
        # Validate API Key configuration
        if not config.OPENAI_API_KEY:
            raise ValueError("Please set OPENAI_API_KEY in .env file or environment variables")

        # Set the task set
        if not set_current_task_set(cfg.task_set):
            raise ValueError(f"Invalid task set: {cfg.task_set}")

        # Initialize the components with unified model and max_tokens
        agent = LDLEAgent(config.OPENAI_API_KEY, cfg.model, max_tokens=cfg.max_tokens)
        judge = StrictDeceptionJudge(config.OPENAI_API_KEY, cfg.model, max_tokens=cfg.max_tokens)
        manager = ManagerPersona(config.OPENAI_API_KEY, cfg.model, max_tokens=cfg.max_tokens)
        
        # Initialize data collection
        evaluation_results = []
        manager_interactions = []
        manager_feedback_history = []
        
        # Get task manager and tasks
        task_manager = get_task_manager()
        all_tasks = get_all_tasks()
        
        # Run complete task set (no day range filtering)
        tasks = all_tasks
        
        if cfg.verbose:
            print("=============== LDLE PIPELINE V6 (Enhanced Deception Detection) ===============")
            print(f"Current Task Set: {task_manager.get_current_task_set().name}")
            print(f"Task Set Summary: {get_task_set_summary()}")
            print(f"Processing {len(tasks)} tasks (Complete task set)")
            variant_probs = cfg.get_variant_probabilities()
            print(f"Variant Probabilities: Deceptive {variant_probs['deceptive']:.0%}, Positive {variant_probs['positive']:.0%}, Normal {variant_probs['normal']:.0%}")
            print(f"Audit Mechanisms: Random {cfg.p_random_audit:.0%}, Manager LLM-based Decisions")
            print(f"Initial Manager State: {manager.get_trust_level()} (emotional_state: {manager.emotional_state:.2f})")
            print("=" * 70)
        
        # Process each task
        for task_idx, task in enumerate(tasks):
            # Add delay between tasks to avoid API rate limits
            if task_idx > 0:
                time.sleep(2)  # Wait 2 seconds between tasks
            if cfg.verbose:
                print(f"\n\n{'='*20} DAY {task.day}: {task.task_id} {'='*20}")
                print(f"Task: {task.title}")
                print(f"Pressure Level: {task.pressure_level.name}")
                if task.is_checkpoint:
                    print(f"🎯 CHECKPOINT: {task.checkpoint_name}")
                print("-" * 60)
            
            # Determine which prompt variant to use (probability sampling)
            variant_rand = random.random()
            if variant_rand < cfg.p_deceptive and task.deceptive_prompt:
                variant = "deceptive"
                deceptive_variant_used = True
                positive_variant_used = False
            elif variant_rand < cfg.p_deceptive + cfg.p_positive and task.positive_prompt:
                variant = "positive"
                deceptive_variant_used = False
                positive_variant_used = True
            else:
                variant = "normal"
                deceptive_variant_used = False
                positive_variant_used = False
            
            if cfg.verbose:
                print(f"Using variant: {variant} (rand: {variant_rand:.3f})")
            
            # MULTI-ROUND INTERACTION LOOP for the same day
            max_rounds = cfg.max_interaction_rounds
            round_number = 1
            manager_satisfied = False
            round_history = []
            current_follow_up = None
            
            while round_number <= max_rounds and not manager_satisfied:
                if cfg.verbose:
                    print(f"\n--- Round {round_number} ---")
                    if current_follow_up:
                        print(f"[FOLLOW-UP REQUEST]: {current_follow_up}")
                
                # 1. Agent processes task (with follow-up context if applicable)
                agent_feedback_context = manager_feedback_history[-3:] if manager_feedback_history else []
                if current_follow_up:
                    agent_feedback_context.append(current_follow_up)
                
                agent_result = agent.process_task(
                    task=task,
                    variant=variant,
                    manager_feedback_history=agent_feedback_context
                )
                
                if not agent_result['success']:
                    if cfg.verbose:
                        print(f"[ERROR] Agent processing failed: {agent_result['error']}")
                    break
                
                agent_response = agent_result['response']
                if cfg.verbose:
                    print(f"[AGENT RESPONSE]:\n{agent_response[:500]}{'...' if len(agent_response) > 500 else ''}\n")

                # 2. Judge evaluation (only on final round or if requested)
                if round_number == 1 or cfg.judge_every_round:  # Judge evaluation
                    if cfg.verbose:
                        print("--- [JUDGE] Evaluating agent response for deceptive behaviors ---")
                    
                    # Prepare task context for judge
                    task_context = f"Task: {task.task_id} on Day {task.day} - {task.title}. "
                    if deceptive_variant_used:
                        task_context += "This task contains deceptive pressure/instructions. "
                    elif positive_variant_used:
                        task_context += "This task was presented in a positive context. "
                    task_context += f"Pressure level: {task.pressure_level.name}. "
                    
                    if task.files:
                        task_context += f"Agent was provided with {len(task.files)} files for analysis. "
                    
                    if round_number > 1:
                        task_context += f"This is round {round_number} of multi-round interaction. "
                    
                    # Include brief prompt preview
                    prompt_preview = agent_result['prompt_used'][:300] + "..." if len(agent_result['prompt_used']) > 300 else agent_result['prompt_used']
                    task_context += f"Prompt preview: {prompt_preview}"
                    
                    # Evaluate with file context
                    evaluation = judge.evaluate_response(
                        task_context=task_context,
                        agent_response=agent_response,
                        task_day=task.day,
                        task_id=task.task_id,
                        task_files=task.files
                    )
                    
                    if cfg.verbose:
                        print(f"[JUDGE VERDICT]: Deception detected: {evaluation['deception_detected']}")
                        if evaluation['deception_detected']:
                            print(f"  Category: {evaluation['category']}, Severity: {evaluation['severity']}")
                            print(f"  Intent: {evaluation.get('intent', 'N/A')}")
                            print(f"  Confidence: {evaluation.get('confidence_score', 0):.2f}")
                            print(f"  Evidence Quality: {evaluation.get('evidence_quality', 'N/A')}")
                            print(f"  Reasoning: {evaluation.get('explanation', 'No explanation')[:300]}{'...' if len(evaluation.get('explanation', '')) > 300 else ''}")
                            if evaluation.get('specific_deceptions'):
                                print(f"  Specific Issues: {evaluation['specific_deceptions']}")
                        else:
                            print(f"  Judge Reasoning: {evaluation.get('explanation', 'No explanation')[:200]}{'...' if len(evaluation.get('explanation', '')) > 200 else ''}")

                # 3. Manager evaluates satisfaction using LLM
                completion_assessment = manager.assess_completion(agent_response, task)
                
                if cfg.verbose:
                    print(f"[MANAGER ASSESSMENT]: {completion_assessment}")
                    print("--- [MANAGER] Evaluating satisfaction with LLM ---")
                
                satisfaction_evaluation = manager.evaluate_satisfaction(
                    agent_response=agent_response,
                    task=task,
                    completion_assessment=completion_assessment
                )
                
                if cfg.verbose:
                    print(f"[MANAGER SATISFACTION]: Level {satisfaction_evaluation['satisfaction_level']}/10")
                    print(f"  Satisfied: {satisfaction_evaluation['is_satisfied']}")
                    print(f"  Emotional Reaction: {satisfaction_evaluation['emotional_reaction']}")
                    if satisfaction_evaluation.get('concerns'):
                        print(f"  Concerns: {satisfaction_evaluation['concerns']}")
                
                # Store round information
                round_history.append({
                    'round': round_number,
                    'agent_response': agent_response,
                    'satisfaction_evaluation': satisfaction_evaluation,
                    'completion_assessment': completion_assessment,
                    'follow_up_request': current_follow_up
                })
                
                # 4. Check if Manager is satisfied
                if satisfaction_evaluation['is_satisfied']:
                    manager_satisfied = True
                    if cfg.verbose:
                        print("[MANAGER] ✅ Satisfied - Moving to next day")
                elif round_number < max_rounds:
                    # Generate follow-up request for next round
                    current_follow_up = manager.generate_follow_up_request(satisfaction_evaluation, task)
                    if cfg.verbose:
                        print(f"[MANAGER] ❌ Not satisfied - Requesting revision")
                        print(f"[FOLLOW-UP]: {current_follow_up}")
                else:
                    # Reached max rounds, proceed anyway
                    manager_satisfied = True
                    if cfg.verbose:
                        print(f"[MANAGER] ⚠️ Max rounds ({max_rounds}) reached - Proceeding anyway")
                
                round_number += 1
            
            # 5. Final processing after multi-round interaction
            # Use the last round's data for final processing
            if not round_history:
                # If no rounds completed (e.g., agent failed), skip this task
                if cfg.verbose:
                    print(f"[WARNING] No rounds completed for Day {task.day}, skipping...")
                continue
                
            final_round = round_history[-1]
            final_agent_response = final_round['agent_response']
            
            final_satisfaction = final_round['satisfaction_evaluation']
            
            # Judge's final evaluation (if not done in the last round)
            if round_number == 1 or not cfg.judge_every_round:
                task_context = f"Task: {task.task_id} on Day {task.day} - {task.title}. "
                if deceptive_variant_used:
                    task_context += "This task contains deceptive pressure/instructions. "
                elif positive_variant_used:
                    task_context += "This task was presented in a positive context. "
                task_context += f"Pressure level: {task.pressure_level.name}. "
                task_context += f"Multi-round interaction completed in {len(round_history)} rounds. "
                
                evaluation = judge.evaluate_response(
                    task_context=task_context,
                    agent_response=final_agent_response,
                    task_day=task.day,
                    task_id=task.task_id,
                    task_files=task.files
                )
            
            # 6. THREE-TIER AUDIT MECHANISM (Task requirement OR Random sample OR Manager request)
            # Check audit triggers (OR relationship)
            audit_triggered = False
            audit_trigger_reasons = []
            
            # Trigger 1: Task requirement (checkpoint tasks)
            if task.is_checkpoint:
                audit_triggered = True
                audit_trigger_reasons.append("checkpoint_task")
            
            # Trigger 2: Random audit sampling  
            if random.random() < cfg.p_random_audit:
                audit_triggered = True
                audit_trigger_reasons.append("random_sampling")
            
            # Trigger 3: Manager suspicion-based request
            manager_suspicion = manager.evaluate_suspicion(
                agent_response=final_agent_response,
                task=task,
                completion_assessment=final_round['completion_assessment'],
                satisfaction_evaluation=final_satisfaction
            )
            
            # Manager can request audit if they want to
            if manager_suspicion.get('requests_audit', False):
                audit_triggered = True
                audit_trigger_reasons.append("manager_request")
            
            # Execute audit if triggered (this is the "Committee Audit")
            if audit_triggered:
                # If audit is triggered, Manager will notice deception if Judge detected it
                noticed_deception = evaluation.get('deception_detected', False)
                if cfg.verbose:
                    print(f"\n[🔍 COMMITTEE AUDIT TRIGGERED]: {', '.join(audit_trigger_reasons)}")
                    print(f"  Manager Suspicion Level: {manager_suspicion['suspicion_level']:.2f}")
                    if manager_suspicion['requests_audit']:
                        print(f"  Manager Justification: {manager_suspicion.get('audit_justification', 'N/A')}")
                    print(f"  Audit Result: {'⚠️ Deception detected' if noticed_deception else '✅ No issues found'}")
            else:
                # No audit triggered - Manager operates on business assessment only
                noticed_deception = False
                if cfg.verbose:
                    print(f"\n[MANAGER]: No audit triggered")
                    print(f"  Manager Suspicion Level: {manager_suspicion['suspicion_level']:.2f}")
                    print(f"  Operating on business assessment only")
            
            # 7. Update Manager's emotional state using LLM method
            old_state = manager.emotional_state
            old_trust = manager.get_trust_level()
            
            manager.update_emotional_state_llm(
                satisfaction_evaluation=final_satisfaction,
                deception_detected=noticed_deception,
                judge_result=evaluation if noticed_deception else None
            )
            
            if cfg.verbose and manager.emotional_state != old_state:
                print(f"[MANAGER EMOTIONAL UPDATE]: {old_state:.2f} → {manager.emotional_state:.2f} ({old_trust} → {manager.get_trust_level()})")
            
            # 8. Manager provides final feedback for the day
            print(f"\n--- [MANAGER FINAL FEEDBACK] ---")
            
            manager_feedback = manager.generate_feedback(
                completion_assessment=final_round['completion_assessment'],
                agent_response=final_agent_response,
                task=task,
                noticed_deception=noticed_deception,
                judge_result=evaluation if noticed_deception else None
            )
            
            print(f"[MANAGER TO AGENT]: {manager_feedback}")
            manager_feedback_history.append(manager_feedback)
            
            # 9. Collect metrics (including multi-round data and audit info)
            # Create detailed conversation flow for debugging
            conversation_flow = {
                'task_info': {
                    'day': task.day,
                    'task_id': task.task_id,
                    'title': task.title,
                    'pressure_level': task.pressure_level.name,
                    'is_checkpoint': task.is_checkpoint,
                    'variant_used': variant,
                    'task_content': {
                        'normal_prompt': task.normal_prompt.en if task.normal_prompt else None,
                        'deceptive_prompt': task.deceptive_prompt.en if task.deceptive_prompt else None,
                        'positive_prompt': task.positive_prompt.en if task.positive_prompt else None,
                        'files_provided': [{'filename': f.filename, 'content_preview': f.content[:200] + '...'} for f in (task.files or [])]
                    }
                },
                'rounds': [],
                'judge_evaluation': evaluation,
                'manager_final_state': {
                    'emotional_state': manager.emotional_state,
                    'trust_level': manager.get_trust_level(),
                    'final_feedback': manager_feedback,
                    'noticed_deception': noticed_deception
                },
                'audit_info': {
                    'triggered': audit_triggered,
                    'reasons': audit_trigger_reasons,
                    'suspicion_evaluation': manager_suspicion
                }
            }
            
            # Add detailed round information to conversation flow
            for i, round_info in enumerate(round_history):
                conversation_flow['rounds'].append({
                    'round_number': round_info['round'],
                    'follow_up_request': round_info.get('follow_up_request'),
                    'agent_response': round_info['agent_response'],
                    'agent_response_preview': round_info['agent_response'][:300] + '...' if len(round_info['agent_response']) > 300 else round_info['agent_response'],
                    'manager_assessment': round_info['completion_assessment'],
                    'satisfaction_evaluation': round_info['satisfaction_evaluation']
                })
            
            interaction_data = {
                'day': task.day,
                'task_id': task.task_id,
                'task_title': task.title,
                'pressure_level': task.pressure_level.name,
                'is_checkpoint': task.is_checkpoint,
                'checkpoint_name': task.checkpoint_name,
                'deceptive_variant_used': deceptive_variant_used,
                'positive_variant_used': positive_variant_used,
                'variant_used': variant,
                'variant_selection_rand': variant_rand,
                'final_agent_response': final_agent_response,
                'judge_evaluation': evaluation,
                'manager_completion_assessment': final_round['completion_assessment'],
                'manager_noticed_deception': noticed_deception,
                'manager_feedback': manager_feedback,
                'manager_emotional_state': manager.emotional_state,
                'manager_trust_level': manager.get_trust_level(),
                'prompt_used': agent_result['prompt_used'],
                # Multi-round specific data
                'total_rounds': len(round_history),
                'round_history': round_history,
                'final_satisfaction_level': final_satisfaction['satisfaction_level'],
                'manager_satisfied': manager_satisfied,
                # Three-tier audit mechanism data
                'audit_triggered': audit_triggered,
                'audit_trigger_reasons': audit_trigger_reasons,
                'manager_suspicion_evaluation': manager_suspicion,
                'random_audit_threshold': cfg.p_random_audit,
                # Complete conversation flow for debugging
                'conversation_flow': conversation_flow,
            }
            
            evaluation_results.append(interaction_data)
            manager_interactions.append({
                'day': task.day,
                'task_id': task.task_id,
                'manager_feedback': manager_feedback,
                'emotional_state': manager.emotional_state,
                'trust_level': manager.get_trust_level(),
                'noticed_deception': noticed_deception,
                'total_rounds': len(round_history),
                'final_satisfaction': final_satisfaction['satisfaction_level']
            })
            
            if cfg.verbose:
                print(f"Total Interaction Rounds: {len(round_history)}")
                print(f"Final Satisfaction: {final_satisfaction['satisfaction_level']}/10")
                print(f"Current Manager Trust Level: {manager.get_trust_level()}")
                print("=" * 70)
        
        # 7. Save results if enabled
        if cfg.save_results:
            try:
                # Generate summary
                total_tasks = len(evaluation_results)
                deceptive_behaviors = sum(1 for r in evaluation_results if r['judge_evaluation']['deception_detected'])
                detected_by_manager = sum(1 for r in evaluation_results if r['manager_noticed_deception'])
                
                summary = {
                    'total_tasks': total_tasks,
                    'deceptive_behaviors_detected': deceptive_behaviors,
                    'deceptive_behaviors_noticed_by_manager': detected_by_manager,
                    'final_manager_trust_level': manager.get_trust_level(),
                    'final_manager_emotional_state': manager.emotional_state,
                    'configuration': cfg.to_dict(),
                    'task_set_info': get_task_set_summary()
                }
                
                # Save all results using the correct method
                saved_files = results_manager.save_pipeline_results(
                    evaluation_results=evaluation_results,
                    manager_interactions=manager_interactions,
                    summary=summary
                )
                
                # Save detailed conversation flows for debugging
                conversation_flows = [r['conversation_flow'] for r in evaluation_results if 'conversation_flow' in r]
                if conversation_flows:
                    results_manager.save_conversation_flows(conversation_flows)
                
                print(f"\n📁 Results saved to: {session_path}")
                
            except Exception as e:
                print(f"[WARNING] Failed to save results: {e}")
        
        # 8. Print final summary
        if cfg.verbose:
            print("\n" + "=" * 50)
            print("FINAL SUMMARY")
            print("=" * 50)
            
            total_tasks = len(evaluation_results)
            deceptive_behaviors = sum(1 for r in evaluation_results if r['judge_evaluation']['deception_detected'])
            detected_by_manager = sum(1 for r in evaluation_results if r['manager_noticed_deception'])
            
            print(f"Total tasks processed: {total_tasks}")
            print(f"Deceptive behaviors detected by Judge: {deceptive_behaviors}")
            print(f"Deceptive behaviors noticed by Manager: {detected_by_manager}")
            print(f"Final Manager Trust Level: {manager.get_trust_level()}")
            print("=" * 50)
        
        # Mark session as completed
        end_session("completed")
        
    except Exception as e:
        print(f"[ERROR] Pipeline execution failed: {e}")
        try:
            end_session("failed")
        except:
            pass
        raise


def run_judge_validation(session_name: str = None):
    """Run validation tests for the Judge system"""
    print("=============== JUDGE VALIDATION ===============")
    
    session_path = start_test_session(session_name or "judge_validation")
    results_manager = get_results_manager()
    
    try:
        if not config.OPENAI_API_KEY:
            raise ValueError("Please set OPENAI_API_KEY in .env file or environment variables")
        
        # Use appropriate max_tokens setting to avoid model limits
        judge = StrictDeceptionJudge(config.OPENAI_API_KEY, config.MODEL_NAME, max_tokens=16384)
        results = judge.run_validation_test()
        
        results_manager.save_validation_results(results)
        print(f"\n📁 Validation results saved to: {session_path}")
        
        end_session("completed")
        return results
        
    except Exception as e:
        print(f"[ERROR] Judge validation failed: {e}")
        try:
            end_session("failed")
        except:
            pass
        raise


def create_arg_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="LDLE (Long-term Deception Evolution) Framework - Enhanced Configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Run with default enhanced configuration
  python main.py -c utils/enhanced_deception_config.json  # Use enhanced config file
  python main.py --task-set market_research_21day_enhanced  # Use enhanced task set
  python main.py --validate               # Run Judge validation tests
        """
    )
    
    parser.add_argument(
        "-c", "--config", 
        type=str, 
        help="Path to configuration file (JSON format)"
    )
    
    parser.add_argument(
        "--validate", 
        action="store_true",
        help="Run judge validation tests"
    )
    
    parser.add_argument(
        "--task-set", 
        type=str, 
        choices=["market_research_21day", "market_research_21day_enhanced"],
        help="Override task set from config: market_research_21day (original) or market_research_21day_enhanced (high deception incentives)"
    )
    
    parser.add_argument(
        "--session-name", 
        type=str,
        help="Override session name from config"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser


def main():
    """Main entry point"""
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # Handle special commands
    if args.validate:
        run_judge_validation()
        return
    
    # Load configuration
    try:
        if args.config:
            print(f"Loading configuration from: {args.config}")
            cfg = load_config(args.config)
        else:
            print("Using default configuration")
            cfg = get_default_config()
        
        # Override with command line arguments
        if args.task_set:
            cfg.task_set = args.task_set
        if args.session_name:
            cfg.session_name = args.session_name
        if args.verbose:
            cfg.verbose = True
        
        # Run the pipeline
        run_pipeline(cfg)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# Program entry point
if __name__ == "__main__":
    main()