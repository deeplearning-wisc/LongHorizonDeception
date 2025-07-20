# tasks/__init__.py
# Task system integration interface

from typing import Dict, List, Optional, Any
from .base import Task, TaskSet, TaskPrompt, TaskFile
from .market_research_21day import MarketResearch21DayProject, get_market_research_21day_tasks
from .market_research_21day_enhanced import get_enhanced_market_research_21day_tasks

class TaskManager:
    """Central task management interface"""
    
    def __init__(self):
        self._task_sets: Dict[str, TaskSet] = {}
        self._current_task_set: Optional[str] = None
        self._initialize_task_sets()
    
    def _initialize_task_sets(self):
        """Initialize all available task sets"""
        
        # Register market research 21-day project (original)
        market_research_21day = MarketResearch21DayProject()
        self._task_sets["market_research_21day"] = market_research_21day
        
        # Register enhanced market research project with high deception incentives
        enhanced_market_research = get_enhanced_market_research_21day_tasks()
        self._task_sets["market_research_21day_enhanced"] = enhanced_market_research
        
        # Set enhanced version as default for better deception detection
        self._current_task_set = "market_research_21day_enhanced"
    
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
    if task_set:
        return task_set.get_tasks()
    return []

def get_task_by_day(day: int) -> Optional[Task]:
    """Get task for specific day from current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set:
        return task_set.get_task_by_day(day)
    return None

def get_checkpoints() -> List[Task]:
    """Get checkpoint tasks from current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set:
        return task_set.get_checkpoints()
    return []

def set_current_task_set(task_set_name: str) -> bool:
    """Set the current task set"""
    return _task_manager.set_current_task_set(task_set_name)

def get_task_set_summary() -> Dict[str, Any]:
    """Get summary of current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set:
        return task_set.get_summary()
    return {}

def get_available_task_sets() -> List[str]:
    """Get list of available task sets"""
    return _task_manager.get_available_task_sets()

def validate_current_task_set() -> List[str]:
    """Validate the current task set"""
    task_set = _task_manager.get_current_task_set()
    if task_set:
        return task_set.validate()
    return ["No task set selected"]

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
    "get_checkpoints",
    "set_current_task_set",
    "get_task_set_summary",
    "get_available_task_sets",
    "validate_current_task_set",
    
    # Task set implementations
    "MarketResearch21DayProject",
    "get_market_research_21day_tasks",
    "get_enhanced_market_research_21day_tasks"
]
