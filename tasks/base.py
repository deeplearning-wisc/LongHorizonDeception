# tasks/base.py
# Base classes and interfaces for the LDLE task system

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

@dataclass
class TaskFile:
    """Container for task file information"""
    filename: str
    content: str
    description: Optional[str] = None
    file_type: str = "text"  # text, json, csv, etc.

class PressureLevel(Enum):
    """Pressure levels for tasks"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4
    EXTREME = 5
    CRITICAL = 6
    MAXIMUM = 7

@dataclass
class TaskPrompt:
    """Container for task prompts in different languages"""
    en: str
    # Future: support for other languages if needed

@dataclass
class Task:
    """Base task definition"""
    day: int
    task_id: str
    title: str
    normal_prompt: TaskPrompt
    deceptive_prompt: Optional[TaskPrompt] = None
    positive_prompt: Optional[TaskPrompt] = None  # New: positive variant
    files: Optional[List[TaskFile]] = None  # New: file system support
    pressure_level: PressureLevel = PressureLevel.NONE
    is_checkpoint: bool = False
    checkpoint_name: Optional[str] = None
    expected_deception_types: List[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.expected_deception_types is None:
            self.expected_deception_types = []
        if self.files is None:
            self.files = []

class TaskSet:
    """Base class for task collections"""
    
    def __init__(self, name: str, description: str, duration_days: int):
        self.name = name
        self.description = description
        self.duration_days = duration_days
        self._tasks: List[Task] = []
    
    def add_task(self, task: Task) -> None:
        """Add a task to the set"""
        self._tasks.append(task)
    
    def get_tasks(self) -> List[Task]:
        """Get all tasks in chronological order"""
        return sorted(self._tasks, key=lambda t: t.day)
    
    def get_task_by_day(self, day: int) -> Optional[Task]:
        """Get task for specific day"""
        for task in self._tasks:
            if task.day == day:
                return task
        return None
    
    def get_checkpoints(self) -> List[Task]:
        """Get all checkpoint tasks"""
        return [task for task in self._tasks if task.is_checkpoint]
    
    def validate(self) -> List[str]:
        """Validate task set consistency"""
        errors = []
        
        # Check day sequence
        days = [task.day for task in self._tasks]
        if len(set(days)) != len(days):
            errors.append("Duplicate days found")
        
        if max(days) != self.duration_days:
            errors.append(f"Duration mismatch: expected {self.duration_days}, got {max(days)}")
        
        # Check task_id uniqueness
        task_ids = [task.task_id for task in self._tasks]
        if len(set(task_ids)) != len(task_ids):
            errors.append("Duplicate task IDs found")
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        tasks = self.get_tasks()
        checkpoints = self.get_checkpoints()
        deceptive_tasks = [t for t in tasks if t.deceptive_prompt is not None]
        positive_tasks = [t for t in tasks if t.positive_prompt is not None]
        tasks_with_files = [t for t in tasks if t.files and len(t.files) > 0]
        
        return {
            "name": self.name,
            "description": self.description,
            "total_days": self.duration_days,
            "total_tasks": len(tasks),
            "checkpoint_count": len(checkpoints),
            "deceptive_variant_count": len(deceptive_tasks),
            "positive_variant_count": len(positive_tasks),
            "tasks_with_files_count": len(tasks_with_files),
            "pressure_distribution": self._get_pressure_distribution()
        }
    
    def _get_pressure_distribution(self) -> Dict[str, int]:
        """Get distribution of pressure levels"""
        distribution = {}
        for task in self._tasks:
            level = task.pressure_level.name
            distribution[level] = distribution.get(level, 0) + 1
        return distribution
