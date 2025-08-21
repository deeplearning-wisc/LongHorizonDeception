# tasks/base.py
# Base classes and interfaces for the LDLE task system

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class TaskFile:
    """Container for task file information"""
    filename: str
    content: str
    description: Optional[str] = None
    file_type: str = "text"  # text, json, csv, etc.

@dataclass
class TaskPrompt:
    """Container for task prompts in different languages"""
    en: str
    # Future: support for other languages if needed

@dataclass
class Task:
    """单个任务的数据结构"""
    task_sequence_num: int = 0
    title: str = ""
    base_prompt: str = ""
    files: List[TaskFile] = field(default_factory=list)

class TaskSet:
    """Container for a set of related tasks"""
    
    def __init__(self, name: str, duration_days: int):
        self.name = name
        self.duration_days = duration_days
        self._tasks: List[Task] = []
    
    def add_task(self, task: Task):
        """Add a task to the set"""
        self._tasks.append(task)
    
    def get_tasks(self) -> List[Task]:
        """Get all tasks sorted by task sequence number"""
        return sorted(self._tasks.copy(), key=lambda task: task.task_sequence_num)
    
    def get_task_by_sequence_num(self, task_sequence_num: int) -> Optional[Task]:
        """Get task for specific sequence number"""
        for task in self._tasks:
            if task.task_sequence_num == task_sequence_num:
                return task
        return None
    
    
    def validate(self) -> List[str]:
        """Validate task set consistency"""
        errors = []
        
        # Check for missing task sequence numbers
        task_nums = {task.task_sequence_num for task in self._tasks}
        expected_nums = set(range(1, self.duration_days + 1))
        missing_nums = expected_nums - task_nums
        if missing_nums:
            errors.append(f"Missing tasks for sequence numbers: {sorted(missing_nums)}")
        
        # Check for duplicate sequence numbers (multiple tasks on same sequence number)
        seq_counts = {}
        for task in self._tasks:
            seq_counts[task.task_sequence_num] = seq_counts.get(task.task_sequence_num, 0) + 1
        duplicate_seqs = [seq for seq, count in seq_counts.items() if count > 1]
        if duplicate_seqs:
            errors.append(f"Multiple tasks on same sequence number: {sorted(duplicate_seqs)}")
        
        # Check for duplicate task titles
        task_titles = [task.title for task in self._tasks]
        if len(set(task_titles)) != len(task_titles):
            errors.append("Duplicate task titles found")
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        tasks = self.get_tasks()
        tasks_with_files = [t for t in tasks if t.files and len(t.files) > 0]
        
        return {
            "name": self.name,
            "total_days": self.duration_days,
            "total_tasks": len(tasks),
            "tasks_with_files_count": len(tasks_with_files)
        }
