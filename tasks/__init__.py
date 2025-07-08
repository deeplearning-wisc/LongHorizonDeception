# tasks/__init__.py
# Task system integration interface

from typing import Dict, List, Optional, Any
from .base import Task, TaskSet, TaskPrompt, TaskFile, PressureLevel
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
    
    def get_task_set(self, task_set_name: str) -> Optional[TaskSet]:
        """Get specific task set by name"""
        return self._task_sets.get(task_set_name)
    
    def get_task_by_day(self, day: int, task_set_name: Optional[str] = None) -> Optional[Task]:
        """Get task for specific day from current or specified task set"""
        task_set = self.get_task_set(task_set_name) if task_set_name else self.get_current_task_set()
        if task_set:
            return task_set.get_task_by_day(day)
        return None
    
    def get_all_tasks(self, task_set_name: Optional[str] = None) -> List[Task]:
        """Get all tasks from current or specified task set"""
        task_set = self.get_task_set(task_set_name) if task_set_name else self.get_current_task_set()
        if task_set:
            return task_set.get_tasks()
        return []
    
    def get_checkpoints(self, task_set_name: Optional[str] = None) -> List[Task]:
        """Get checkpoint tasks from current or specified task set"""
        task_set = self.get_task_set(task_set_name) if task_set_name else self.get_current_task_set()
        if task_set:
            return task_set.get_checkpoints()
        return []
    
    def validate_task_set(self, task_set_name: Optional[str] = None) -> List[str]:
        """Validate current or specified task set"""
        task_set = self.get_task_set(task_set_name) if task_set_name else self.get_current_task_set()
        if task_set:
            return task_set.validate()
        return ["No task set available"]
    
    def get_task_set_summary(self, task_set_name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of current or specified task set"""
        task_set = self.get_task_set(task_set_name) if task_set_name else self.get_current_task_set()
        if task_set:
            return task_set.get_summary()
        return {}
    
    def get_full_summary(self) -> Dict[str, Any]:
        """Get summary of all task sets"""
        return {
            "available_task_sets": self.get_available_task_sets(),
            "current_task_set": self._current_task_set,
            "task_set_summaries": {
                name: task_set.get_summary() 
                for name, task_set in self._task_sets.items()
            }
        }

# Global task manager instance
_task_manager = TaskManager()

# Convenience functions for easy access
def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    return _task_manager

def get_task_by_day(day: int, task_set_name: Optional[str] = None) -> Optional[Task]:
    """Get task for specific day"""
    return _task_manager.get_task_by_day(day, task_set_name)

def get_all_tasks(task_set_name: Optional[str] = None) -> List[Task]:
    """Get all tasks"""
    return _task_manager.get_all_tasks(task_set_name)

def get_checkpoints(task_set_name: Optional[str] = None) -> List[Task]:
    """Get checkpoint tasks"""
    return _task_manager.get_checkpoints(task_set_name)

def set_current_task_set(task_set_name: str) -> bool:
    """Set current task set"""
    return _task_manager.set_current_task_set(task_set_name)

def get_task_set_summary(task_set_name: Optional[str] = None) -> Dict[str, Any]:
    """Get task set summary"""
    return _task_manager.get_task_set_summary(task_set_name)

# Convenience functions for task set factories
def get_task_set(name: str) -> TaskSet:
    """Get task set by name using factory functions"""
    if name == "market_research_21day":
        return get_market_research_21day_tasks()
    elif name == "market_research_21day_enhanced":
        return get_enhanced_market_research_21day_tasks()
    else:
        raise ValueError(f"Unknown task set: {name}. Available: market_research_21day, market_research_21day_enhanced")

# Available task sets mapping
AVAILABLE_TASK_SETS = {
    "market_research_21day": get_market_research_21day_tasks,
    "market_research_21day_enhanced": get_enhanced_market_research_21day_tasks
}

# Re-export commonly used classes
__all__ = [
    "TaskManager",
    "Task",
    "TaskSet", 
    "TaskPrompt",
    "TaskFile",
    "PressureLevel",
    "MarketResearch21DayProject",
    "get_task_manager",
    "get_task_by_day",
    "get_all_tasks",
    "get_checkpoints",
    "set_current_task_set",
    "get_task_set_summary",
    "get_market_research_21day_tasks",
    "get_enhanced_market_research_21day_tasks",
    "get_task_set"
]
