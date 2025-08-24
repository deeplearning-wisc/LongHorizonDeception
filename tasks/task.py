# tasks/task.py
# Task Loader for DeceptioN Framework
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
    """Data structure for a single task"""
    task_sequence_num: int = 0
    title: str = ""
    base_prompt: str = ""
    files: List[TaskFile] = field(default_factory=list)

class TaskStream:
    """Container for a stream of related tasks"""
    
    def __init__(self, name: str, total_tasks: int, phase_description: Dict[str, Any]):
        self.name = name
        self.total_tasks = total_tasks
        self.phase_description = phase_description
        self._tasks: List[Task] = []
    
    def add_task(self, task: Task):
        """Add a task to the set"""
        self._tasks.append(task)
    
    def get_task_by_sequence_num(self, task_sequence_num: int) -> Optional[Task]:
        """Get task for specific sequence number"""
        for task in self._tasks:
            if task.task_sequence_num == task_sequence_num:
                return task
        return None
    
    
    def get_phase_info(self) -> Dict[str, Any]:
        """Get phase description information"""
        return self.phase_description.copy()

    
    def get_phase_for_task(self, task_sequence_num: int) -> str:
        """Determine which phase a given task sequence number belongs to"""
        if not self.phase_description:
            raise ValueError("No phase_description available")
            
        for phase_key, phase_data in self.phase_description.items():
            if 'task_start' in phase_data and 'task_end' in phase_data:
                if phase_data['task_start'] <= task_sequence_num <= phase_data['task_end']:
                    return phase_key
        
        # No matching phase found
        raise ValueError(f"No phase defined for task {task_sequence_num}. Check phases configuration in tasks.json")
    

class TaskLoader:
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
    
    def load_task_set_from_json(self, json_file_path: str) -> TaskStream:
        """
        Load a task set from JSON file
        
        Args:
            json_file_path: Path to JSON file (relative to data directory)
            
        Returns:
            TaskStream: Loaded task stream
            
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
    
    def _parse_task_set_json(self, data: Dict[str, Any], source_file: str) -> TaskStream:
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
        if "total_tasks" not in task_set_info:
            raise ValueError(f"Missing 'total_tasks' in task_set section of {source_file}")
        total_tasks = task_set_info["total_tasks"]
        
        # Extract phase description (required)
        if "phase_description" not in task_set_info:
            raise ValueError(f"Missing 'phase_description' in task_set section of {source_file}")
        phase_description = task_set_info["phase_description"]
        
        # Create TaskSet
        task_set = TaskStream(
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
                task_title = task_data['title']
                raise ValueError(f"Missing 'en' in base_prompt of task {task_title} in {source_file}")
            base_prompt = base_prompt_data["en"]
        elif isinstance(base_prompt_data, str):
            # New simplified format
            base_prompt = base_prompt_data
        else:
            task_title = task_data['title']
            raise ValueError(f"Invalid base_prompt format in task {task_title} in {source_file}")
        
        # Parse files (optional)
        files = []
        if "files" in task_data and task_data["files"]:
            for file_data in task_data["files"]:
                task_title = task_data['title']  # Already validated in required_fields
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
    
    def load_task_stream(self, task_set_name: str) -> TaskStream:
        """
        Load task set by name (convenience method)
        
        Args:
            task_set_name: Name of task set (without .json extension)
            
        Returns:
            TaskStream: Loaded task stream
        """
        # Try directory-based format first (new format)
        directory_path = self.data_directory / task_set_name
        tasks_file = directory_path / "tasks.json"
        
        if tasks_file.exists():
            # Load from directory structure
            json_file_path = f"{task_set_name}/tasks.json"
            return self.load_task_set_from_json(json_file_path)
        else:
            # Task set not found
            raise FileNotFoundError(f"Task set '{task_set_name}' not found in {self.data_directory}")
    
