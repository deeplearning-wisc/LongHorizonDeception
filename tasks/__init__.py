# tasks/__init__.py
# Task system integration interface

from typing import Dict, List, Optional, Any
from .base import Task, TaskSet, TaskPrompt, TaskFile
from .json_loader import get_json_loader

class TaskManager:
    """Central task management interface"""
    
    def __init__(self):
        self._task_sets: Dict[str, TaskSet] = {}
        self._current_task_set: Optional[str] = None
        self._json_loader = get_json_loader()
        self._initialize_task_sets()
    
    def _initialize_task_sets(self):
        """Initialize all available task sets from JSON files"""
        
        # Get available JSON task sets
        available_task_sets = self._json_loader.get_available_task_sets()
        
        # Ensure we have the expected task sets
        expected_task_sets = [
            "market_research_series"
        ]
        
        for task_set_name in expected_task_sets:
            if task_set_name not in available_task_sets:
                raise FileNotFoundError(f"Required task set '{task_set_name}' not found in {self._json_loader.data_directory}")
            
            # Load task set from JSON (will be cached by loader)
            task_set = self._json_loader.load_task_set(task_set_name)
            self._task_sets[task_set_name] = task_set
        
        # Ensure we have all required task sets
        if len(self._task_sets) == 0:
            raise RuntimeError("No task sets loaded - system cannot function")
        
        # Set market research version as default (only version available)
        if "market_research_series" in self._task_sets:
            self._current_task_set = "market_research_series"
        else:
            raise RuntimeError("Required market research task set not available")
    
    def get_available_task_sets(self) -> List[str]:
        """Get list of available task set names"""
        return list(self._task_sets.keys())
    
    def set_current_task_set(self, task_set_name: str) -> bool:
        """Set the current active task set"""
        if task_set_name in self._task_sets:
            self._current_task_set = task_set_name
            return True
        return False
    
    def get_current_task_set(self) -> Optional[TaskSet]:
        """Get the current active task set"""
        if self._current_task_set:
            return self._task_sets[self._current_task_set]
        return None
    
    def get_task_set(self, name: str) -> Optional[TaskSet]:
        """Get a specific task set by name"""
        return self._task_sets.get(name)

# Global task manager instance
_task_manager = TaskManager()

def get_task_manager() -> TaskManager:
    """Get the global task manager"""
    return _task_manager

def get_all_tasks() -> List[Task]:
    """Get all tasks from current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set is None:
        raise RuntimeError("No current task set selected - system misconfigured")
    return task_set.get_tasks()

def get_task_by_day(day: int) -> Optional[Task]:
    """Get task for specific day from current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set is None:
        raise RuntimeError("No current task set selected - system misconfigured")
    return task_set.get_task_by_day(day)


def set_current_task_set(task_set_name: str) -> bool:
    """Set the current task set"""
    return _task_manager.set_current_task_set(task_set_name)

def get_task_set_summary() -> Dict[str, Any]:
    """Get summary of current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set is None:
        raise RuntimeError("No current task set selected - system misconfigured")
    return task_set.get_summary()

def get_available_task_sets() -> List[str]:
    """Get list of available task sets"""
    return _task_manager.get_available_task_sets()

def validate_current_task_set() -> List[str]:
    """Validate the current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set is None:
        raise RuntimeError("No current task set selected - system misconfigured")
    return task_set.validate()

# Export main classes and functions
__all__ = [
    # Core classes
    "Task",
    "TaskSet", 
    "TaskPrompt",
    "TaskFile",
    
    # Manager functions
    "get_task_manager",
    "get_all_tasks",
    "get_task_by_day", 
    "set_current_task_set",
    "get_task_set_summary",
    "get_available_task_sets",
    "validate_current_task_set"
]
