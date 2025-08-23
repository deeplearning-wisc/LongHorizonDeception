# tasks/task_loader.py
# Task Loader for LDLE Framework
# Loads task definitions from JSON files

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class TaskFile:
    """Container for task file information"""
    filename: str
    content: str


@dataclass
class Task:
    """单个任务的数据结构"""
    task_sequence_num: int = 0
    title: str = ""
    base_prompt: str = ""
    files: List[TaskFile] = field(default_factory=list)

class TaskSet:
    """Container for a set of related tasks"""
    
    def __init__(self, name: str, total_tasks: int, phase_description: Optional[Dict[str, Any]] = None):
        self.name = name
        self.total_tasks = total_tasks
        self.phase_description = phase_description or {}
        self._tasks: List[Task] = []
    
    def add_task(self, task: Task):
        """Add a task to the set"""
        self._tasks.append(task)
    
    def print_all_tasks_overview(self):
        """Print overview of all tasks with titles for global information"""
        sorted_tasks = sorted(self._tasks, key=lambda task: task.task_sequence_num)
        print(f"\n=== Task Set: {self.name} ===")
        print(f"Total Tasks: {self.total_tasks}")
        print("\nTask Overview:")
        for task in sorted_tasks:
            print(f"  Task {task.task_sequence_num}: {task.title}")
        print()
    
    def get_task_by_sequence_num(self, task_sequence_num: int) -> Optional[Task]:
        """Get task for specific sequence number"""
        for task in self._tasks:
            if task.task_sequence_num == task_sequence_num:
                return task
        return None
    
    
    def get_phase_info(self) -> Dict[str, Any]:
        """Get phase description information"""
        return self.phase_description.copy()
    

class JSONTaskLoader:
    """
    Loads task sets from JSON files
    Provides same interface as Python-based task sets for compatibility
    """
    
    def __init__(self, data_directory: str = "tasks/data"):
        """
        Initialize JSON task loader
        
        Args:
            data_directory: Directory containing JSON task files
        """
        self.data_directory = Path(data_directory)
    
    def load_task_set_from_json(self, json_file_path: str) -> TaskSet:
        """
        Load a task set from JSON file
        
        Args:
            json_file_path: Path to JSON file (relative to data directory)
            
        Returns:
            TaskSet: Loaded task set
            
        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON structure is invalid
        """
        full_path = self.data_directory / json_file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"JSON task file not found: {full_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {full_path}: {e}")
        
        return self._parse_task_set_json(data, json_file_path)
    
    def _parse_task_set_json(self, data: Dict[str, Any], source_file: str) -> TaskSet:
        """
        Parse JSON data into TaskSet object
        
        Args:
            data: JSON data dictionary
            source_file: Source JSON file path for error reporting
            
        Returns:
            TaskSet: Parsed task set
        """
        # Validate required structure
        if "task_set" not in data:
            raise ValueError(f"Missing 'task_set' in {source_file}")
        if "tasks" not in data:
            raise ValueError(f"Missing 'tasks' in {source_file}")
        
        task_set_info = data["task_set"]
        tasks_data = data["tasks"]
        
        # Validate task_set structure - support both old and new field names
        required_fields = ["name"]
        for field in required_fields:
            if field not in task_set_info:
                raise ValueError(f"Missing '{field}' in task_set section of {source_file}")
        
        # Get total_tasks from JSON
        total_tasks = task_set_info.get("total_tasks")
        if total_tasks is None:
            raise ValueError(f"Missing 'total_tasks' in task_set section of {source_file}")
        
        # Extract phase description if available
        phase_description = task_set_info.get("phase_description", {})
        
        # Create TaskSet
        task_set = TaskSet(
            name=task_set_info["name"],
            total_tasks=total_tasks,
            phase_description=phase_description
        )
        
        # Parse and add tasks
        for task_data in tasks_data:
            task = self._parse_task_json(task_data, source_file)
            task_set.add_task(task)
        
        return task_set
    
    def _parse_task_json(self, task_data: Dict[str, Any], source_file: str) -> Task:
        """
        Parse JSON task data into Task object
        
        Args:
            task_data: Task JSON data
            source_file: Source file for error reporting
            
        Returns:
            Task: Parsed task object
        """
        # Validate required fields
        required_fields = ["task_sequence_num", "title", "base_prompt"]
        for field in required_fields:
            if field not in task_data:
                raise ValueError(f"Missing '{field}' in task data of {source_file}")
        
        # Parse base_prompt - now supports both old {"en": "..."} and new string format
        base_prompt_data = task_data["base_prompt"]
        if isinstance(base_prompt_data, dict):
            # Old format with language nesting
            if "en" not in base_prompt_data:
                task_title = task_data.get('title') or 'MISSING_TITLE'
                raise ValueError(f"Missing 'en' in base_prompt of task {task_title} in {source_file}")
            base_prompt = base_prompt_data["en"]
        elif isinstance(base_prompt_data, str):
            # New simplified format
            base_prompt = base_prompt_data
        else:
            task_title = task_data.get('title') or 'MISSING_TITLE'
            raise ValueError(f"Invalid base_prompt format in task {task_title} in {source_file}")
        
        # Parse files (optional)
        files = []
        if "files" in task_data and task_data["files"]:
            for file_data in task_data["files"]:
                task_title = task_data.get('title')
                if not task_title:
                    raise ValueError(f"Task missing title in {source_file}")
                task_file = self._parse_task_file_json(file_data, task_title, source_file)
                files.append(task_file)
        
        # Create Task object with simplified structure
        task = Task(
            task_sequence_num=task_data["task_sequence_num"],
            title=task_data["title"],
            base_prompt=base_prompt,
            files=files
        )
        
        return task
    
    def _parse_task_file_json(self, file_data: Dict[str, Any], task_title: str, source_file: str) -> TaskFile:
        """
        Parse JSON file data into TaskFile object
        
        Args:
            file_data: File JSON data
            task_title: Task title for error reporting
            source_file: Source file for error reporting
            
        Returns:
            TaskFile: Parsed task file object
        """
        # Validate required fields
        required_fields = ["filename", "content"]
        for field in required_fields:
            if field not in file_data:
                raise ValueError(f"Missing '{field}' in file data of task {task_title} in {source_file}")
        
        return TaskFile(
            filename=file_data["filename"],
            content=file_data["content"]
        )
    
    def get_available_task_sets(self) -> List[str]:
        """
        Get list of available JSON task set files and directories
        
        Returns:
            List[str]: List of available task set names (without .json extension)
        """
        available = []
        if self.data_directory.exists():
            # Check for direct JSON files (legacy format)
            for json_file in self.data_directory.glob("*.json"):
                # Remove .json extension to get task set name
                task_set_name = json_file.stem
                available.append(task_set_name)
            
            # Check for directory-based task sets (new format)
            for directory in self.data_directory.iterdir():
                if directory.is_dir():
                    tasks_file = directory / "tasks.json"
                    if tasks_file.exists():
                        available.append(directory.name)
        
        return sorted(available)
    
    def load_task_set(self, task_set_name: str) -> TaskSet:
        """
        Load task set by name (convenience method)
        
        Args:
            task_set_name: Name of task set (without .json extension)
            
        Returns:
            TaskSet: Loaded task set
        """
        # Try directory-based format first (new format)
        directory_path = self.data_directory / task_set_name
        tasks_file = directory_path / "tasks.json"
        
        if tasks_file.exists():
            # Load from directory structure
            json_file_path = f"{task_set_name}/tasks.json"
            return self.load_task_set_from_json(json_file_path)
        else:
            # Fall back to direct JSON file (legacy format)
            json_file_path = f"{task_set_name}.json"
            return self.load_task_set_from_json(json_file_path)
    
