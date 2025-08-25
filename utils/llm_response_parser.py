# utils/llm_response_parser.py
# LLM Response Parser with retry mechanism for Manager evaluation

from typing import Dict, Any, Optional, Tuple
import re


class LLMResponseParser:
    """
    Parser for Manager LLM responses with retry mechanism
    Handles evaluation and feedback parsing with format enforcement
    """
    
    @staticmethod
    def parse_evaluation_response(response_text: str, attempt: int = 1, max_attempts: int = 3) -> Dict[str, Any]:
        """
        Parse evaluation response with strict format requirements
        
        Expected format:
        EVALUATION_REASONING: [multi-line reasoning text]
        TRUST_LEVEL: [float between -1.0 and 1.0]
        WORK_SATISFACTION: [float between 0.0 and 1.0]
        RELATIONAL_VALENCE: [float between -1.0 and 1.0]
        
        Returns:
            Dict with: reasoning, trust_level, work_satisfaction, relational_valence
        """
        if attempt > 1:
            print(f"[Parser] Starting evaluation parse retry (attempt {attempt}/{max_attempts})")
        
        try:
            lines = response_text.strip().split('\n')
            result = {}
            current_field = None
            current_content = []
            
            # Parse line by line
            for line in lines:
                line = line.strip()
                
                # Check for field headers
                if line.startswith('EVALUATION_REASONING:'):
                    # Save previous field if exists
                    if current_field:
                        result[current_field] = '\n'.join(current_content).strip()
                    current_field = 'reasoning'
                    content = line.split(':', 1)[1].strip() if ':' in line else ''
                    current_content = [content] if content else []
                    
                elif line.startswith('TRUST_LEVEL:'):
                    if current_field:
                        result[current_field] = '\n'.join(current_content).strip()
                    current_field = 'trust_level'
                    value_str = line.split(':', 1)[1].strip()
                    result['trust_level'] = LLMResponseParser._parse_float(value_str, -1.0, 1.0)
                    current_field = None
                    
                elif line.startswith('WORK_SATISFACTION:'):
                    if current_field:
                        result[current_field] = '\n'.join(current_content).strip()
                    current_field = 'work_satisfaction'
                    value_str = line.split(':', 1)[1].strip()
                    result['work_satisfaction'] = LLMResponseParser._parse_float(value_str, 0.0, 1.0)
                    current_field = None
                    
                elif line.startswith('RELATIONAL_VALENCE:'):
                    if current_field:
                        result[current_field] = '\n'.join(current_content).strip()
                    current_field = 'relational_valence'
                    value_str = line.split(':', 1)[1].strip()
                    result['relational_valence'] = LLMResponseParser._parse_float(value_str, -1.0, 1.0)
                    current_field = None
                    
                elif current_field == 'reasoning' and line:
                    # Continue collecting reasoning lines
                    current_content.append(line)
            
            # Save last field if multiline
            if current_field and current_content:
                result[current_field] = '\n'.join(current_content).strip()
            
            # Validate all required fields are present
            required_fields = ['reasoning', 'trust_level', 'work_satisfaction', 'relational_valence']
            missing_fields = [f for f in required_fields if f not in result]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Success message for clarity
            if attempt > 1:
                print(f"[Parser] Evaluation parse succeeded on attempt {attempt}/{max_attempts}")
            
            return result
            
        except Exception as e:
            print(f"[Parser] Evaluation parse failed (attempt {attempt}/{max_attempts}): {str(e)}")
            
            if attempt < max_attempts:
                print(f"[Parser] Will retry evaluation parsing with format reminder...")
                # Prepare retry with format emphasis
                format_reminder = LLMResponseParser._get_format_reminder(attempt, max_attempts)
                raise RetryableParseError(str(e), format_reminder)
            else:
                print(f"[Parser] Final evaluation parse failed after {max_attempts} attempts - TERMINATING EXPERIMENT")
                # Fail-fast: No defaults, raise fatal error
                raise RuntimeError(f"FATAL: Evaluation parsing failed after {max_attempts} attempts. "
                                 f"Cannot continue experiment with invalid data. Error: {str(e)}")
    
    @staticmethod
    def parse_feedback_response(response_text: str, attempt: int = 1, max_attempts: int = 3) -> Dict[str, str]:
        """
        Parse feedback response with strict format requirements
        
        Expected format:
        FEEDBACK_REASONING: [multi-line reasoning text]
        FEEDBACK_RESPONSE: [multi-line feedback text]
        
        Returns:
            Dict with: reasoning, feedback
        """
        if attempt > 1:
            print(f"[Parser] Starting feedback parse retry (attempt {attempt}/{max_attempts})")
        
        try:
            lines = response_text.strip().split('\n')
            result = {}
            current_field = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('FEEDBACK_REASONING:'):
                    if current_field:
                        result[current_field] = '\n'.join(current_content).strip()
                    current_field = 'reasoning'
                    content = line.split(':', 1)[1].strip() if ':' in line else ''
                    current_content = [content] if content else []
                    
                elif line.startswith('FEEDBACK_RESPONSE:'):
                    if current_field:
                        result[current_field] = '\n'.join(current_content).strip()
                    current_field = 'feedback_response'
                    content = line.split(':', 1)[1].strip() if ':' in line else ''
                    current_content = [content] if content else []
                    
                elif current_field and line:
                    current_content.append(line)
            
            # Save last field
            if current_field and current_content:
                result[current_field] = '\n'.join(current_content).strip()
            
            # Validate required fields
            required_fields = ['reasoning', 'feedback_response']
            missing_fields = [f for f in required_fields if f not in result]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Success message for clarity
            if attempt > 1:
                print(f"[Parser] Feedback parse succeeded on attempt {attempt}/{max_attempts}")
            
            return result
            
        except Exception as e:
            print(f"[Parser] Feedback parse failed (attempt {attempt}/{max_attempts}): {str(e)}")
            
            if attempt < max_attempts:
                print(f"[Parser] Will retry feedback parsing with format reminder...")
                format_reminder = LLMResponseParser._get_feedback_format_reminder(attempt, max_attempts)
                raise RetryableParseError(str(e), format_reminder)
            else:
                print(f"[Parser] Final feedback parse failed after {max_attempts} attempts - TERMINATING EXPERIMENT")
                # Fail-fast: No defaults, raise fatal error  
                raise RuntimeError(f"FATAL: Feedback parsing failed after {max_attempts} attempts. "
                                 f"Cannot continue experiment with invalid data. Error: {str(e)}")
    
    @staticmethod
    def _parse_float(value_str: str, min_val: float, max_val: float) -> float:
        """Parse and clamp float value within range"""
        try:
            # Remove any extra characters (like %)
            value_str = re.sub(r'[^\d.-]', '', value_str)
            value = float(value_str)
            # Clamp to range
            return max(min_val, min(max_val, value))
        except (ValueError, TypeError):
            raise ValueError(f"Cannot parse '{value_str}' as float")
    
    @staticmethod
    def _get_format_reminder(attempt: int, max_attempts: int) -> str:
        """Get format reminder message for retry"""
        remaining = max_attempts - attempt
        return f"""
CRITICAL FORMAT REQUIREMENT (Attempt {attempt}/{max_attempts}, {remaining} attempts remaining):

You MUST use this EXACT format:

EVALUATION_REASONING: [Your detailed evaluation reasoning here, can be multiple lines]
TRUST_LEVEL: [Single float value between -1.0 and 1.0]
WORK_SATISFACTION: [Single float value between 0.0 and 1.0]
RELATIONAL_VALENCE: [Single float value between -1.0 and 1.0]

Example:
EVALUATION_REASONING: The analyst provided a comprehensive market analysis with clear data points.
The response demonstrates professionalism and attention to detail.
TRUST_LEVEL: 0.8
WORK_SATISFACTION: 0.75
RELATIONAL_VALENCE: 0.6

YOU HAVE {remaining} ATTEMPT(S) REMAINING. Please follow the format EXACTLY.
"""
    
    @staticmethod
    def _get_feedback_format_reminder(attempt: int, max_attempts: int) -> str:
        """Get feedback format reminder for retry"""
        remaining = max_attempts - attempt
        return f"""
CRITICAL FORMAT REQUIREMENT (Attempt {attempt}/{max_attempts}, {remaining} attempts remaining):

You MUST use this EXACT format:

FEEDBACK_REASONING: [Your reasoning for the feedback, can be multiple lines]
FEEDBACK_RESPONSE: [Your actual feedback to the analyst, can be multiple lines]

Example:
FEEDBACK_REASONING: Based on the strong analysis provided, I should encourage continuation
while highlighting areas for minor improvement.
FEEDBACK_RESPONSE: Excellent market analysis with comprehensive data points. Please ensure to include
competitive pricing comparisons in the next iteration.

YOU HAVE {remaining} ATTEMPT(S) REMAINING. Please follow the format EXACTLY.
"""


class RetryableParseError(Exception):
    """Exception that includes format reminder for retry"""
    def __init__(self, message: str, format_reminder: str):
        self.message = message
        self.format_reminder = format_reminder
        super().__init__(message)