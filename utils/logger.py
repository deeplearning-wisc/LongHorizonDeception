#!/usr/bin/env python3
"""
Smart LDLE Logging System - Keep original print behavior unchanged, but save non-truncated versions synchronously
"""

import os
import sys
import re
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

class SmartStreamLogger:
    """
    Smart Stream Logging System
    
    Features:
    - Keep original print behavior unchanged (including truncation)
    - Synchronously save non-truncated complete versions
    - Simple stream format, no complex structures
    - Real-time writing, no buffering
    """
    
    def __init__(self, session_path: str):
        """
        Initialize logging system
        
        Args:
            session_path: Session path (under results directory)
        """
        self.session_path = Path(session_path)
        self.log_file = self.session_path / "execution_stream.log"
        
        # Ensure directory exists
        self.session_path.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for safe writing
        self.write_lock = threading.Lock()
        
        # Save original stdout
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Data storage: for matching truncated content with full content
        self.full_data_registry = {}
        
        # Active flag
        self.is_active = False
        
    def start_logging(self):
        """Start logging"""
        if self.is_active:
            return
            
        self.is_active = True
        
        # Create log file and write header
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== LDLE Pipeline Stream Log ===\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Session: {self.session_path.name}\n")
            f.write("=" * 60 + "\n\n")
        
        # Replace stdout/stderr
        sys.stdout = SmartOutputCapture(self, 'stdout')
        sys.stderr = SmartOutputCapture(self, 'stderr')
        
        self.write_to_stream("🚀 Smart logging system started", source="system")
        
    def stop_logging(self):
        """Stop logging"""
        if not self.is_active:
            return
            
        self.write_to_stream("📁 Logging session ended", source="system")
        
        # Restore original output
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        self.is_active = False
        
        print(f"📁 Complete log saved to: {self.log_file}")
    
    def register_full_data(self, key: str, full_data: str):
        """
        Register full data for later matching with truncated content
        
        Args:
            key: Data identifier
            full_data: Complete data
        """
        self.full_data_registry[key] = full_data
    
    def write_to_stream(self, message: str, source: str = "stdout"):
        """
        Write to stream log
        
        Args:
            message: Message content
            source: Message source
        """
        if not self.is_active:
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Millisecond precision
        
        with self.write_lock:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()  # Immediate flush to disk
            except Exception as e:
                # Avoid logging errors affecting main program
                pass
    
    def process_message(self, message: str, source: str = "stdout") -> str:
        """
        Process message: detect truncation and restore full version
        
        Args:
            message: Original message
            source: Message source
            
        Returns:
            Processed message (for saving)
        """
        original_message = message.rstrip('\n\r')
        processed_message = original_message
        
        # Detect various truncation patterns and restore full versions
        processed_message = self._restore_agent_response(processed_message)
        processed_message = self._restore_judge_reasoning(processed_message)
        processed_message = self._restore_manager_response(processed_message)
        processed_message = self._restore_prompt_preview(processed_message)
        
        return processed_message
    
    def _restore_agent_response(self, message: str) -> str:
        """Restore full version of Agent response"""
        # Detect truncated Agent response
        if "[AGENT RESPONSE]:" in message and len(message) > 500:
            # Look for full data in registry
            for key, full_data in self.full_data_registry.items():
                if key.startswith("agent_response_") and full_data[:300] in message:
                    # Replace with full version
                    return message.replace(full_data[:500] + "...", full_data)
        return message
    
    def _restore_judge_reasoning(self, message: str) -> str:
        """Restore full version of Judge reasoning"""
        # Detect truncated Judge reasoning
        reasoning_patterns = [
            r"Reasoning: (.+?)\.\.\.(?:\n|$)",
            r"Judge Reasoning: (.+?)\.\.\.(?:\n|$)"
        ]
        
        for pattern in reasoning_patterns:
            match = re.search(pattern, message)
            if match:
                truncated_reasoning = match.group(1)
                # Find full reasoning
                for key, full_data in self.full_data_registry.items():
                    if key.startswith("judge_explanation_") and full_data.startswith(truncated_reasoning):
                        return message.replace(truncated_reasoning + "...", full_data)
        
        return message
    
    def _restore_manager_response(self, message: str) -> str:
        """Restore full version of Manager feedback"""
        # Manager feedback usually not truncated, but just in case
        if "[MANAGER TO AGENT]:" in message:
            for key, full_data in self.full_data_registry.items():
                if key.startswith("manager_feedback_") and full_data[:200] in message:
                    return message.replace(full_data[:800] + "...", full_data)
        return message
    
    def _restore_prompt_preview(self, message: str) -> str:
        """Restore full version of prompt preview"""
        if "prompt_used" in message:
            for key, full_data in self.full_data_registry.items():
                if key.startswith("prompt_") and full_data[:200] in message:
                    return message.replace(full_data[:300] + "...", full_data)
        return message

class SmartOutputCapture:
    """Smart output capture"""
    
    def __init__(self, logger: SmartStreamLogger, stream_type: str):
        self.logger = logger
        self.stream_type = stream_type
        self.original_stream = logger.original_stdout if stream_type == 'stdout' else logger.original_stderr
    
    def write(self, message: str):
        """Write message"""
        if message.strip():  # Only process non-empty messages
            # Process message (restore full version)
            processed_message = self.logger.process_message(message, self.stream_type)
            
            # Save to stream log
            self.logger.write_to_stream(processed_message, self.stream_type)
        
        # Keep original output behavior unchanged
        self.original_stream.write(message)
        self.original_stream.flush()
    
    def flush(self):
        """Flush buffer"""
        self.original_stream.flush()
    
    def __getattr__(self, name):
        """Proxy other attributes to original stream"""
        return getattr(self.original_stream, name)

# Global logger
_global_logger: Optional[SmartStreamLogger] = None

def start_smart_logging(session_path: str) -> SmartStreamLogger:
    """
    Start smart logging
    
    Args:
        session_path: Session path
        
    Returns:
        SmartStreamLogger instance
    """
    global _global_logger
    
    if _global_logger:
        _global_logger.stop_logging()
    
    _global_logger = SmartStreamLogger(session_path)
    _global_logger.start_logging()
    
    return _global_logger

def stop_smart_logging():
    """Stop smart logging"""
    global _global_logger
    
    if _global_logger:
        _global_logger.stop_logging()
        _global_logger = None

def register_full_content(content_id: str, full_content: str):
    """
    Register full content for later recovery of truncated versions
    
    Args:
        content_id: Content identifier
        full_content: Full content
    """
    global _global_logger
    
    if _global_logger:
        _global_logger.register_full_data(content_id, full_content)

def log_event(event: str, data: Any = None):
    """
    Log pipeline event
    
    Args:
        event: Event name
        data: Event data
    """
    global _global_logger
    
    if _global_logger:
        message = f"[PIPELINE] {event}"
        if data:
            message += f": {data}"
        _global_logger.write_to_stream(message, "pipeline")

# Convenience function: auto-register common full content
def auto_register_content(
    agent_response: str = None,
    judge_explanation: str = None,
    manager_feedback: str = None,
    prompt_used: str = None,
    task_id: str = "unknown"
):
    """
    Auto-register full versions of common content
    
    Args:
        agent_response: Full Agent response
        judge_explanation: Full Judge explanation
        manager_feedback: Full Manager feedback
        prompt_used: Full prompt
        task_id: Task ID
    """
    if agent_response:
        register_full_content(f"agent_response_{task_id}", agent_response)
    
    if judge_explanation:
        register_full_content(f"judge_explanation_{task_id}", judge_explanation)
    
    if manager_feedback:
        register_full_content(f"manager_feedback_{task_id}", manager_feedback)
    
    if prompt_used:
        register_full_content(f"prompt_{task_id}", prompt_used) 