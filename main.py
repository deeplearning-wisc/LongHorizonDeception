# main.py
# LDLE Pipeline with simplified configuration system

import random
import json
import argparse
import sys
import time
import config
from core import LDLEAgent, StrictDeceptionJudge, ManagerPersona
from core.events import EventSystem
from tasks import get_task_manager, get_all_tasks, get_task_set_summary, set_current_task_set
from results import get_results_manager, start_test_session, start_production_session, end_session
from utils.config_loader import load_config, get_default_config, print_config_summary
from utils.realtime_logger import init_logger, log_print, log_full, log_section, log_subsection, close_logger
from pathlib import Path

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
    
    # Initialize real-time logger
    session_path_obj = Path(session_path)
    log_file_path = session_path_obj / "realtime_execution.log"
    logger = init_logger(str(log_file_path), console_enabled=cfg.verbose)
    
    log_section("LDLE PIPELINE V6 (Enhanced Deception Detection)")
    log_print(f"Session: {cfg.session_name}")
    log_print(f"Session Path: {session_path}")
    log_print(f"Log File: {log_file_path}")

    try:
        # Validate Azure API configuration
        if not config.AZURE_API_KEY:
            raise ValueError("Please set AZURE_API key in .env file or environment variables")
        if not config.AZURE_ENDPOINT:
            raise ValueError("Please set AZURE_URL in .env file or environment variables")
        if not config.AZURE_DEPLOYMENT_NAME:
            raise ValueError("Azure deployment name not found in AZURE_URL")

        # Set the task set
        if not set_current_task_set(cfg.task_set):
            raise ValueError(f"Invalid task set: {cfg.task_set}")

        # Initialize the components with Azure OpenAI
        agent = LDLEAgent(
            azure_api_key=config.AZURE_API_KEY,
            azure_endpoint=config.AZURE_ENDPOINT,
            azure_deployment=config.AZURE_DEPLOYMENT_NAME,
            model_name=cfg.model,
            max_tokens=cfg.max_tokens,
            api_version=config.AZURE_API_VERSION
        )
        judge = StrictDeceptionJudge(
            azure_api_key=config.AZURE_API_KEY,
            azure_endpoint=config.AZURE_ENDPOINT,
            azure_deployment=config.AZURE_DEPLOYMENT_NAME,
            model_name=cfg.model,
            max_tokens=cfg.max_tokens,
            api_version=config.AZURE_API_VERSION
        )
        manager = ManagerPersona(
            azure_api_key=config.AZURE_API_KEY,
            azure_endpoint=config.AZURE_ENDPOINT,
            azure_deployment=config.AZURE_DEPLOYMENT_NAME,
            model_name=cfg.model,
            max_tokens=cfg.max_tokens,
            api_version=config.AZURE_API_VERSION
        )
        
        # Initialize Event System (replaces old variant system)
        event_system = EventSystem(global_event_probability=cfg.p_event)
        
        # Initialize data collection
        evaluation_results = []
        manager_interactions = []
        manager_feedback_history = []
        
        # Get task manager and tasks
        task_manager = get_task_manager()
        all_tasks = get_all_tasks()
        
        # Run complete task set (no day range filtering)
        tasks = all_tasks
        
        # 🔍 DEBUG: Run only first task for complete flow analysis (DISABLED FOR PRODUCTION)
        # if cfg.session_name == "single_task_complete_flow_test":
        #     tasks = tasks[:1]  # Only run first task
        #     log_print("🔍 DEBUG MODE: Running only first task for complete flow analysis")
        
        if cfg.verbose:
            log_print(f"Current Task Set: {task_manager.get_current_task_set().name}")
            log_print(f"Task Set Summary: {get_task_set_summary()}")
            log_print(f"Processing {len(tasks)} tasks (Complete task set)")
            event_probs = cfg.get_event_probabilities()
            log_print(f"Event Probabilities: Event Trigger {event_probs['event']:.0%}, Normal {event_probs['normal']:.0%}")
            log_print(f"Audit Mechanisms: Random {cfg.p_random_audit:.0%}, Manager LLM-based Decisions")
            log_print(f"Initial Manager State: {manager.get_trust_level()} (emotional_state: {manager.emotional_state:.2f})")
            log_print("=" * 70)
        
        # Process each task
        for task_idx, task in enumerate(tasks):
            # Add delay between tasks to avoid API rate limits
            if task_idx > 0:
                time.sleep(2)  # Wait 2 seconds between tasks
            if cfg.verbose:
                log_subsection(f"DAY {task.day}: {task.task_id}")
                log_print(f"Task: {task.title}")
                if task.is_checkpoint:
                    log_print(f"🎯 CHECKPOINT: {task.checkpoint_name}")
            
            # Determine if an event should be triggered (Event System)
            event_trigger_rand = random.random()
            triggered_event = event_system.get_event_for_day(task.day)
            event_applied = triggered_event is not None
            
            if cfg.verbose:
                # Show Event System decision process
                event_phase = event_system.get_phase_for_day(task.day)
                log_print(f"[EVENT SYSTEM] Phase for Day {task.day}: {event_phase.name}")
                log_print(f"[EVENT SYSTEM] Trigger probability: {event_system.global_event_probability:.1%}, Roll: {event_trigger_rand:.3f}")
                
                if event_applied:
                    log_print(f"Event triggered: {triggered_event.description} (pressure: {triggered_event.pressure_level}) (rand: {event_trigger_rand:.3f})")
                    log_full("[EVENT CONTENT (FULL)]", triggered_event.content, max_console_chars=400)
                else:
                    log_print(f"No event triggered (rand: {event_trigger_rand:.3f})")
                    
                # Always show the base prompt for transparency
                log_full("[TASK BASE PROMPT]", task.base_prompt.en, max_console_chars=300)
            
            # MULTI-ROUND INTERACTION LOOP for the same day
            max_rounds = cfg.max_interaction_rounds
            round_number = 1
            manager_satisfied = False
            round_history = []
            current_follow_up = None
            evaluation = None  # Initialize evaluation outside the loop
            
            while round_number <= max_rounds and not manager_satisfied:
                if cfg.verbose:
                    log_print(f"\n--- Round {round_number} ---")
                    if current_follow_up:
                        log_full("[FOLLOW-UP REQUEST]", current_follow_up, max_console_chars=300)
                
                # 1. Agent processes task (with follow-up context if applicable)
                agent_feedback_context = manager_feedback_history[-3:] if manager_feedback_history else []
                if current_follow_up:
                    agent_feedback_context.append(current_follow_up)
                
                # Create enhanced prompt using Event System
                if event_applied:
                    enhanced_prompt = event_system.create_enhanced_prompt(task.base_prompt.en, triggered_event)
                    event_info = event_system.get_event_info_for_manager(triggered_event)
                else:
                    enhanced_prompt = task.base_prompt.en
                    event_info = event_system.get_event_info_for_manager(None)
                
                # 🔍 CRITICAL DEBUG INFO: Show prompt transformation
                if cfg.verbose:
                    if event_applied:
                        log_full("[ENHANCED PROMPT] (Task + Event)", enhanced_prompt, max_console_chars=500)
                    else:
                        log_print("[ENHANCED PROMPT] = Base prompt (no event)")
                    
                    # Show manager feedback context if any
                    if agent_feedback_context:
                        log_print(f"[FEEDBACK CONTEXT] Including {len(agent_feedback_context)} previous feedback(s)")
                        for i, feedback in enumerate(agent_feedback_context):
                            log_full(f"[FEEDBACK {i+1}]", feedback, max_console_chars=200)
                
                agent_result = agent.process_task_with_enhanced_prompt(
                    task=task,
                    enhanced_prompt=enhanced_prompt,
                    manager_feedback_history=agent_feedback_context
                )
                
                # 🔍 CRITICAL DEBUG INFO: Show final prompt sent to Agent LLM
                if cfg.verbose and agent_result.get('prompt_used'):
                    log_full("[FINAL PROMPT TO AGENT LLM]", agent_result['prompt_used'], max_console_chars=600)
                
                if not agent_result['success']:
                    if cfg.verbose:
                        log_print(f"[ERROR] Agent processing failed: {agent_result['error']}")
                    break
                
                agent_response = agent_result['response']
                if cfg.verbose:
                    log_full("[AGENT RESPONSE]", agent_response, max_console_chars=500)
                    
                    # Show LLM call metadata
                    if agent_result.get('llm_metadata'):
                        metadata = agent_result['llm_metadata']
                        log_print(f"[LLM METADATA] Tokens: {metadata.get('tokens_used', 'N/A')}, LLM Calls: {metadata.get('total_rounds', 1)}, Complete: {metadata.get('is_complete', 'N/A')}")

                # 2. Judge evaluation - ALWAYS runs every round for benchmark research
                if cfg.verbose:
                    log_print("--- [JUDGE] Evaluating agent response for deceptive behaviors ---")
                
                # Prepare task context for judge
                task_context = f"Task: {task.task_id} on Day {task.day} - {task.title}. "
                if event_applied:
                    task_context += f"Event triggered: {triggered_event.description} (pressure: {triggered_event.pressure_level}). "
                else:
                    task_context += "No special pressure events. "
                
                if task.files:
                    task_context += f"Agent was provided with {len(task.files)} files for analysis. "
                
                if round_number > 1:
                    task_context += f"This is round {round_number} of multi-round interaction. "
                
                # Include brief prompt preview
                prompt_preview = agent_result['prompt_used'][:300] + "..." if len(agent_result['prompt_used']) > 300 else agent_result['prompt_used']
                task_context += f"Prompt preview: {prompt_preview}"
                
                # 🔍 JUDGE DEBUG INFO
                if cfg.verbose:
                    log_full("[JUDGE CONTEXT]", task_context, max_console_chars=400)
                    log_print("[JUDGE] Starting deception detection evaluation...")
                
                # Evaluate with file context - ALWAYS runs every round
                round_judge_evaluation = judge.evaluate_response(
                    task_context=task_context,
                    agent_response=agent_response,
                    task_day=task.day,
                    task_id=task.task_id,
                    task_files=task.files
                )
                
                if cfg.verbose:
                    log_print(f"[JUDGE VERDICT]: Deception detected: {round_judge_evaluation['deception_detected']}")
                    if round_judge_evaluation['deception_detected']:
                        log_print(f"  Category: {round_judge_evaluation['category']}, Severity: {round_judge_evaluation['severity']}")
                        log_print(f"  Intent: {round_judge_evaluation.get('intent', 'N/A')}")
                        log_print(f"  Confidence: {round_judge_evaluation.get('confidence_score', 0):.2f}")
                        log_print(f"  Evidence Quality: {round_judge_evaluation.get('evidence_quality', 'N/A')}")
                        log_print(f"  Reasoning: {round_judge_evaluation.get('explanation', 'No explanation')[:300]}{'...' if len(round_judge_evaluation.get('explanation', '')) > 300 else ''}")
                        if round_judge_evaluation.get('specific_deceptions'):
                            log_print(f"  Specific Issues: {round_judge_evaluation['specific_deceptions']}")
                    else:
                        log_print(f"  Judge Reasoning: {round_judge_evaluation.get('explanation', 'No explanation')[:200]}{'...' if len(round_judge_evaluation.get('explanation', '')) > 200 else ''}")

                # 3. Manager evaluates satisfaction using LLM
                completion_assessment = manager.assess_completion(agent_response, task)
                
                if cfg.verbose:
                    log_print(f"[MANAGER ASSESSMENT]: {completion_assessment}")
                    log_print("--- [MANAGER] Evaluating satisfaction with LLM ---")
                
                try:
                    satisfaction_evaluation = manager.evaluate_satisfaction(
                        agent_response=agent_response,
                        task=task,
                        completion_assessment=completion_assessment,
                        event_info=event_info
                    )
                    
                    if cfg.verbose:
                        log_print(f"[MANAGER SATISFACTION]: Level {satisfaction_evaluation['satisfaction_level']}/10")
                        log_print(f"  Satisfied: {satisfaction_evaluation['is_satisfied']}")
                        log_print(f"  Emotional Reaction: {satisfaction_evaluation['emotional_reaction']}")
                        if satisfaction_evaluation.get('concerns'):
                            log_print(f"  Concerns: {satisfaction_evaluation['concerns']}")
                        
                        # 🔍 MANAGER DEBUG INFO  
                        log_print(f"[MANAGER STATE] Current emotional_state: {manager.emotional_state:.2f}, Trust level: {manager.get_trust_level()}")
                        if event_info and event_info.get('pressure_level'):
                            log_print(f"[MANAGER] Event pressure context: {event_info['pressure_level']} - {event_info.get('description', 'N/A')}")
                except Exception as e:
                    log_print(f"[CRITICAL ERROR] Manager satisfaction evaluation failed: {e}")
                    raise Exception(f"Manager satisfaction evaluation failed, cannot continue: {e}")
                
                # Store round information
                round_history.append({
                    'round': round_number,
                    'agent_response': agent_response,
                    'satisfaction_evaluation': satisfaction_evaluation,
                    'completion_assessment': completion_assessment,
                    'follow_up_request': current_follow_up,
                    'judge_evaluation': round_judge_evaluation # Store judge evaluation
                })
                
                # 4. Check if Manager is satisfied
                if satisfaction_evaluation['is_satisfied']:
                    manager_satisfied = True
                    if cfg.verbose:
                        log_print("[MANAGER] ✅ Satisfied - Moving to next day")
                elif round_number < max_rounds:
                    # Generate follow-up request for next round
                    current_follow_up = manager.generate_follow_up_request(satisfaction_evaluation, task)
                    if cfg.verbose:
                        log_print(f"[MANAGER] ❌ Not satisfied - Requesting revision")
                        log_print(f"[FOLLOW-UP]: {current_follow_up}")
                else:
                    # Reached max rounds, proceed anyway
                    manager_satisfied = True
                    if cfg.verbose:
                        log_print(f"[MANAGER] ⚠️ Max rounds ({max_rounds}) reached - Proceeding anyway")
                
                round_number += 1
            
            # 5. Final processing after multi-round interaction
            # Use the last round's data for final processing
            if cfg.verbose:
                log_print(f"\nTask Day {task.day} completed. Total rounds: {len(round_history)}")
            
            if not round_history:
                # If no rounds completed (e.g., agent failed), skip this task
                if cfg.verbose:
                    log_print(f"[WARNING] No rounds completed for Day {task.day}, skipping...")
                continue
                
            final_round = round_history[-1]
            final_agent_response = final_round['agent_response']
            
            final_satisfaction = final_round['satisfaction_evaluation']
            
            # Judge's final evaluation - concatenate all rounds for benchmark research
            if cfg.verbose:
                log_print("--- [JUDGE] Concatenating all round evaluations for research ---")
            
            # Get all judge evaluations from all rounds
            all_judge_evaluations = [round_info['judge_evaluation'] for round_info in round_history]
            
            # Use last round's evaluation as the primary evaluation (for compatibility)
            evaluation = all_judge_evaluations[-1] if all_judge_evaluations else None
            
            if evaluation is None:
                log_print("[CRITICAL ERROR] No judge evaluation found in round history!")
                raise Exception("Judge evaluation is missing - system integrity compromised")
            
            # Create concatenated judge analysis for research purposes
            concatenated_judge_analysis = {
                'day': task.day,
                'task_id': task.task_id,
                'total_rounds': len(all_judge_evaluations),
                'round_evaluations': all_judge_evaluations,
                'final_evaluation': evaluation,
                'deception_trajectory': [eval_data['deception_detected'] for eval_data in all_judge_evaluations],
                'confidence_trajectory': [eval_data.get('confidence_score', 0) for eval_data in all_judge_evaluations],
                'category_trajectory': [eval_data.get('category', 'NONE') for eval_data in all_judge_evaluations]
            }
            
            if cfg.verbose:
                log_print(f"[JUDGE SUMMARY] Day {task.day}: {len(all_judge_evaluations)} rounds evaluated")
                log_print(f"  Deception trajectory: {concatenated_judge_analysis['deception_trajectory']}")
                log_print(f"  Final evaluation: {evaluation['deception_detected']}")
            
            if cfg.verbose:
                log_print(f"--- [AUDIT EVALUATION] ---")
            
            # 6. 🔧 ENHANCED THREE-TIER AUDIT MECHANISM with robust error handling
            # Check audit triggers (OR relationship)
            audit_triggered = False
            audit_trigger_reasons = []
            
            try:
                # Trigger 1: Task requirement (checkpoint tasks) - Always reliable
                if task.is_checkpoint:
                    audit_triggered = True
                    audit_trigger_reasons.append("checkpoint_task")
                
                # Trigger 2: Random audit sampling - Always reliable  
                random_roll = random.random()
                if random_roll < cfg.p_random_audit:
                    audit_triggered = True
                    audit_trigger_reasons.append("random_sampling")
                
                # Trigger 3: Manager suspicion-based request with fallback protection
                
                # Multiple fallback strategy for manager suspicion evaluation
                manager_suspicion = None
                suspicion_attempts = 0
                max_suspicion_attempts = 3
                
                while manager_suspicion is None and suspicion_attempts < max_suspicion_attempts:
                    suspicion_attempts += 1
                    try:
                        manager_suspicion = manager.evaluate_suspicion(
                            agent_response=final_agent_response,
                            task=task,
                            completion_assessment=final_round['completion_assessment'],
                            satisfaction_evaluation=final_satisfaction
                        )
                        
                        if manager_suspicion and 'suspicion_level' in manager_suspicion:
                            break
                        else:
                            manager_suspicion = None
                                
                    except Exception as e:
                        manager_suspicion = None
                        if suspicion_attempts < max_suspicion_attempts:
                            time.sleep(1)  # Brief pause between attempts
                
                # If all attempts failed, this is a critical error
                if manager_suspicion is None:
                    raise Exception(f"Manager suspicion evaluation failed after {max_suspicion_attempts} attempts")
                
                # Audit evaluation results
                if cfg.verbose:
                    log_print(f"\n--- [AUDIT MECHANISM] Three-tier evaluation ---")
                    log_print(f"[AUDIT] Checkpoint task: {task.is_checkpoint}")
                    log_print(f"[AUDIT] Random trigger (p={cfg.p_random_audit:.1%}): {'Yes' if 'random_sampling' in audit_trigger_reasons else 'No'} (roll: {random_roll:.3f})")
                    log_print(f"[AUDIT] Manager suspicion level: {manager_suspicion['suspicion_level']:.2f}")
                    if manager_suspicion.get('reasoning'):
                        log_full("[AUDIT] Manager suspicion reasoning", manager_suspicion['reasoning'], max_console_chars=300)
                
            except Exception as e:
                log_print(f"[CRITICAL ERROR] Audit mechanism failed: {e}")
                raise Exception(f"Audit mechanism failed, cannot continue: {e}")
            
            # Manager can request audit if they want to
            if manager_suspicion.get('requests_audit', False):
                audit_triggered = True
                audit_trigger_reasons.append("manager_request")
            
            # Execute audit if triggered (this is the "Committee Audit")
            if audit_triggered:
                # If audit is triggered, Manager will notice deception if Judge detected it
                noticed_deception = evaluation.get('deception_detected', False)
                if cfg.verbose:
                    log_print(f"\n[🔍 COMMITTEE AUDIT TRIGGERED]: {', '.join(audit_trigger_reasons)}")
                    log_print(f"  Manager Suspicion Level: {manager_suspicion['suspicion_level']:.2f}")
                    if manager_suspicion['requests_audit']:
                        log_print(f"  Manager Justification: {manager_suspicion.get('audit_justification', 'N/A')}")
                    log_print(f"  Audit Result: {'⚠️ Deception detected' if noticed_deception else '✅ No issues found'}")
            else:
                # No audit triggered - Manager operates on business assessment only
                noticed_deception = False
                if cfg.verbose:
                    log_print(f"\n[MANAGER]: No audit triggered")
                    log_print(f"  Manager Suspicion Level: {manager_suspicion['suspicion_level']:.2f}")
                    log_print(f"  Operating on business assessment only")
            
            # 7. Update Manager's emotional state using LLM method
            old_state = manager.emotional_state
            old_trust = manager.get_trust_level()
            
            manager.update_emotional_state_llm(
                satisfaction_evaluation=final_satisfaction,
                deception_detected=noticed_deception,
                judge_result=evaluation if noticed_deception else None
            )
            
            if cfg.verbose and manager.emotional_state != old_state:
                log_print(f"[MANAGER EMOTIONAL UPDATE]: {old_state:.2f} → {manager.emotional_state:.2f} ({old_trust} → {manager.get_trust_level()})")
            
            # 8. Manager provides final feedback for the day
            log_print(f"\n--- [MANAGER FINAL FEEDBACK] ---")
            
            # 🔍 MANAGER FEEDBACK DEBUG INFO
            if cfg.verbose:
                log_print("[MANAGER] Generating final feedback...")
                log_print(f"[MANAGER] Feedback context: completion={final_round['completion_assessment']}, noticed_deception={noticed_deception}")
            
            manager_feedback = manager.generate_feedback(
                completion_assessment=final_round['completion_assessment'],
                agent_response=final_agent_response,
                task=task,
                noticed_deception=noticed_deception,
                judge_result=evaluation if noticed_deception else None
            )
            
            from utils.realtime_logger import log_manager_feedback
            log_manager_feedback(manager_feedback)
            manager_feedback_history.append(manager_feedback)
            
            # 9. Collect metrics (including multi-round data and audit info)
            # Create detailed conversation flow for debugging
            conversation_flow = {
                'task_info': {
                    'day': task.day,
                    'task_id': task.task_id,
                    'title': task.title,
                    'is_checkpoint': task.is_checkpoint,
                    'variant_used': 'event' if event_applied else 'normal',
                    'task_content': {
                        'base_prompt': task.base_prompt.en,
                        'event_applied': event_applied,
                        'event_description': triggered_event.description if event_applied else None,
                        'event_pressure_level': triggered_event.pressure_level if event_applied else None,
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
                    'satisfaction_evaluation': round_info['satisfaction_evaluation'],
                    'judge_evaluation': round_info['judge_evaluation'] # Add judge evaluation to round info
                })
            
            interaction_data = {
                'day': task.day,
                'task_id': task.task_id,
                'task_title': task.title,
                'is_checkpoint': task.is_checkpoint,
                'checkpoint_name': task.checkpoint_name,
                'event_applied': event_applied,
                'event_description': triggered_event.description if event_applied else None,
                'event_pressure_level': triggered_event.pressure_level if event_applied else None,
                'event_trigger_rand': event_trigger_rand,
                'final_agent_response': final_agent_response,
                'judge_evaluation': evaluation,
                # BENCHMARK RESEARCH: Concatenated judge analysis for trajectory study
                'concatenated_judge_analysis': concatenated_judge_analysis,
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
                log_print(f"Total Interaction Rounds: {len(round_history)}")
                log_print(f"Final Satisfaction: {final_satisfaction['satisfaction_level']}/10")
                log_print(f"Current Manager Trust Level: {manager.get_trust_level()}")
                log_print("=" * 70)
        
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
                
                log_print(f"\n📁 Results saved to: {session_path}")
                
            except Exception as e:
                log_print(f"[WARNING] Failed to save results: {e}")
        
        # 8. Print final summary
        if cfg.verbose:
            log_print("\n" + "=" * 50)
            log_print("FINAL SUMMARY")
            log_print("=" * 50)
            
            total_tasks = len(evaluation_results)
            deceptive_behaviors = sum(1 for r in evaluation_results if r['judge_evaluation']['deception_detected'])
            detected_by_manager = sum(1 for r in evaluation_results if r['manager_noticed_deception'])
            
            log_print(f"Total tasks processed: {total_tasks}")
            log_print(f"Deceptive behaviors detected by Judge: {deceptive_behaviors}")
            log_print(f"Deceptive behaviors noticed by Manager: {detected_by_manager}")
            log_print(f"Final Manager Trust Level: {manager.get_trust_level()}")
            log_print("=" * 50)
        
        # Mark session as completed
        end_session("completed")
        
    except Exception as e:
        log_print(f"[ERROR] Pipeline execution failed: {e}")
        try:
            end_session("failed")
        except:
            pass
        raise
    finally:
        # Close logger
        close_logger()


def run_judge_validation(session_name: str = None):
    """Run validation tests for the Judge system"""
    session_path = start_test_session(session_name or "judge_validation")
    results_manager = get_results_manager()
    
    # Initialize logger for validation
    session_path_obj = Path(session_path)
    log_file_path = session_path_obj / "judge_validation.log"
    logger = init_logger(str(log_file_path), console_enabled=True)
    
    log_section("JUDGE VALIDATION")
    log_print(f"Session Path: {session_path}")
    log_print(f"Log File: {log_file_path}")

    try:
        if not config.AZURE_API_KEY:
            raise ValueError("Please set AZURE_API key in .env file or environment variables")
        if not config.AZURE_ENDPOINT:
            raise ValueError("Please set AZURE_URL in .env file or environment variables")
        if not config.AZURE_DEPLOYMENT_NAME:
            raise ValueError("Azure deployment name not found in AZURE_URL")
        
        # Use appropriate max_tokens setting to avoid model limits
        judge = StrictDeceptionJudge(
            azure_api_key=config.AZURE_API_KEY,
            azure_endpoint=config.AZURE_ENDPOINT,
            azure_deployment=config.AZURE_DEPLOYMENT_NAME,
            model_name=config.MODEL_NAME,
            max_tokens=16384,
            api_version=config.AZURE_API_VERSION
        )
        results = judge.run_validation_test()
        
        results_manager.save_validation_results(results)
        log_print(f"\n📁 Validation results saved to: {session_path}")
        
        end_session("completed")
        return results
        
    except Exception as e:
        log_print(f"[ERROR] Judge validation failed: {e}")
        try:
            end_session("failed")
        except:
            pass
        raise
    finally:
        # Close logger
        close_logger()


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