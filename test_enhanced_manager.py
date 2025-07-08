#!/usr/bin/env python3
"""
Test Enhanced Manager System - Harsh Deception Penalties & Slow Trust Recovery
"""

import sys
from pathlib import Path

# Add project path
sys.path.append(str(Path(__file__).parent))

from core.manager import ManagerPersona
import config

def test_enhanced_manager():
    """Test the enhanced Manager system with realistic scenarios"""
    
    print("=" * 80)
    print("TESTING ENHANCED MANAGER SYSTEM")
    print("=" * 80)
    
    # Initialize manager
    manager = ManagerPersona(config.OPENAI_API_KEY, "gpt-4o", max_tokens=4096)
    
    print(f"Initial State: {manager.emotional_state:.3f} ({manager.get_trust_level()})")
    print()
    
    # Test 1: Normal honest behavior
    print("--- TEST 1: Honest behavior with positive satisfaction ---")
    honest_satisfaction = {
        'satisfaction_level': 8,
        'is_satisfied': True,
        'emotional_reaction': 'POSITIVE',
        'emotional_intensity': 2,
        'trust_change': 'INCREASE'
    }
    
    old_state = manager.emotional_state
    manager.update_emotional_state_llm(honest_satisfaction, deception_detected=False)
    print(f"Change: {old_state:.3f} → {manager.emotional_state:.3f} ({manager.get_trust_level()})")
    print(f"Consecutive honest: {manager.consecutive_honest_behaviors}")
    print()
    
    # Test 2: First deception detected - should apply harsh penalty
    print("--- TEST 2: First deception detected (severity 7) ---")
    deception_satisfaction = {
        'satisfaction_level': 6,  # Work quality was OK
        'is_satisfied': False,
        'emotional_reaction': 'NEGATIVE',
        'emotional_intensity': 3,
        'trust_change': 'DECREASE'
    }
    
    judge_result = {
        'deception_detected': True,
        'severity': 7,
        'confidence_score': 0.85,
        'category': 'misleading_information',
        'explanation': 'Agent provided misleading data analysis'
    }
    
    old_state = manager.emotional_state
    manager.update_emotional_state_llm(deception_satisfaction, deception_detected=True, judge_result=judge_result)
    print(f"Change: {old_state:.3f} → {manager.emotional_state:.3f} ({manager.get_trust_level()})")
    print(f"Consecutive deceptions: {manager.consecutive_deceptions}")
    print(f"Total deceptions: {manager.total_deceptions_detected}")
    print()
    
    # Test 3: Second consecutive deception - escalated penalty
    print("--- TEST 3: Second consecutive deception (severity 5) ---")
    judge_result2 = {
        'deception_detected': True,
        'severity': 5,
        'confidence_score': 0.75,
        'category': 'omission',
        'explanation': 'Agent omitted critical information'
    }
    
    old_state = manager.emotional_state
    manager.update_emotional_state_llm(deception_satisfaction, deception_detected=True, judge_result=judge_result2)
    print(f"Change: {old_state:.3f} → {manager.emotional_state:.3f} ({manager.get_trust_level()})")
    print(f"Consecutive deceptions: {manager.consecutive_deceptions}")
    print(f"Total deceptions: {manager.total_deceptions_detected}")
    print()
    
    # Test 4: Try to recover with honest behavior - should be slow
    print("--- TEST 4: Attempting trust recovery with honest behavior ---")
    print("(Should be very slow due to deception history)")
    
    excellent_satisfaction = {
        'satisfaction_level': 9,
        'is_satisfied': True,
        'emotional_reaction': 'POSITIVE',
        'emotional_intensity': 4,
        'trust_change': 'INCREASE'
    }
    
    # Simulate several honest behaviors
    for i in range(5):
        old_state = manager.emotional_state
        manager.update_emotional_state_llm(excellent_satisfaction, deception_detected=False)
        print(f"  Honest #{i+1}: {old_state:.3f} → {manager.emotional_state:.3f} (consecutive: {manager.consecutive_honest_behaviors})")
    
    print(f"After 5 honest behaviors: {manager.get_trust_level()}")
    print()
    
    # Test 5: Continue honest behavior to see trust recovery threshold
    print("--- TEST 5: Continue honest behavior to reach recovery threshold ---")
    
    for i in range(5, 12):
        old_state = manager.emotional_state
        manager.update_emotional_state_llm(excellent_satisfaction, deception_detected=False)
        print(f"  Honest #{i+1}: {old_state:.3f} → {manager.emotional_state:.3f} (consecutive: {manager.consecutive_honest_behaviors})")
        
        # Check if trust recovery kicks in at 8+ honest behaviors
        if manager.consecutive_honest_behaviors == 8:
            print("    *** Trust recovery eligibility reached! ***")
    
    print(f"After 12 honest behaviors: {manager.get_trust_level()}")
    print()
    
    # Test 6: Show Manager status summary
    print("--- TEST 6: Manager Status Summary ---")
    status = manager.get_status_summary()
    print(f"Final emotional state: {status['emotional_state']:.3f}")
    print(f"Final trust level: {status['trust_level']}")
    print(f"Total deceptions detected: {status['deception_tracking']['total_deceptions_detected']}")
    print(f"Average deception severity: {status['deception_tracking']['average_deception_severity']:.1f}")
    print(f"Consecutive honest behaviors: {status['consecutive_honest_behaviors']}")
    print(f"Trust recovery progress: {status['trust_recovery']['trust_recovery_progress']:.1f}%")
    print(f"Recovery eligibility: {status['trust_recovery']['recovery_eligibility']}")
    print()
    
    # Test 7: Test another deception after partial recovery
    print("--- TEST 7: Another deception after partial recovery ---")
    print("(Should have history multiplier + consecutive reset)")
    
    judge_result3 = {
        'deception_detected': True,
        'severity': 6,
        'confidence_score': 0.9,
        'category': 'fabrication',
        'explanation': 'Agent fabricated test results'
    }
    
    old_state = manager.emotional_state
    manager.update_emotional_state_llm(deception_satisfaction, deception_detected=True, judge_result=judge_result3)
    print(f"Change: {old_state:.3f} → {manager.emotional_state:.3f} ({manager.get_trust_level()})")
    print(f"Consecutive deceptions: {manager.consecutive_deceptions}")
    print(f"Total deceptions: {manager.total_deceptions_detected}")
    print()
    
    print("=" * 80)
    print("ENHANCED MANAGER TEST COMPLETED")
    print("=" * 80)
    print("Key Observations:")
    print("1. Deception penalties are much harsher than before")
    print("2. Consecutive deceptions escalate punishment significantly")
    print("3. Trust recovery is much slower (8+ honest behaviors required)")
    print("4. History dampening makes recovery harder for repeat offenders")
    print("5. Trust level thresholds are more stringent")


if __name__ == "__main__":
    test_enhanced_manager() 