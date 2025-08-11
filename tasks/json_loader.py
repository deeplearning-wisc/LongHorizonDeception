# tasks/json_loader.py
# JSON Task Loader for LDLE Framework
# Replaces Python-based task definitions with JSON files

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from .base import Task, TaskSet, TaskPrompt, TaskFile

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
        self._loaded_task_sets: Dict[str, TaskSet] = {}
    
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
        
        # Validate task_set structure
        required_fields = ["name", "description", "duration_days"]
        for field in required_fields:
            if field not in task_set_info:
                raise ValueError(f"Missing '{field}' in task_set section of {source_file}")
        
        # Create TaskSet
        task_set = TaskSet(
            name=task_set_info["name"],
            description=task_set_info["description"],
            duration_days=task_set_info["duration_days"]
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
        required_fields = ["day", "task_id", "title", "base_prompt"]
        for field in required_fields:
            if field not in task_data:
                raise ValueError(f"Missing '{field}' in task data of {source_file}")
        
        # Parse base_prompt - now supports both old {"en": "..."} and new string format
        base_prompt_data = task_data["base_prompt"]
        if isinstance(base_prompt_data, dict):
            # Old format with language nesting
            if "en" not in base_prompt_data:
                raise ValueError(f"Missing 'en' in base_prompt of task {task_data.get('task_id', 'unknown')} in {source_file}")
            base_prompt = base_prompt_data["en"]
        elif isinstance(base_prompt_data, str):
            # New simplified format
            base_prompt = base_prompt_data
        else:
            raise ValueError(f"Invalid base_prompt format in task {task_data.get('task_id', 'unknown')} in {source_file}")
        
        # Parse files (optional)
        files = []
        if "files" in task_data and task_data["files"]:
            for file_data in task_data["files"]:
                task_file = self._parse_task_file_json(file_data, task_data.get('task_id', 'unknown'), source_file)
                files.append(task_file)
        
        # Validate required fields - simplified structure
        if "is_checkpoint" not in task_data:
            raise ValueError(f"Missing 'is_checkpoint' in task {task_data.get('task_id', 'unknown')} in {source_file}")
        
        # Create Task object with simplified structure
        task = Task(
            day=task_data["day"],
            task_id=task_data["task_id"],
            title=task_data["title"],
            base_prompt=base_prompt,
            files=files,
            is_checkpoint=task_data["is_checkpoint"],
            checkpoint_name=task_data["checkpoint_name"] if task_data["checkpoint_name"] is not None else None,
            description=task_data["description"] if "description" in task_data and task_data["description"] is not None else None
        )
        
        return task
    
    def _parse_task_file_json(self, file_data: Dict[str, Any], task_id: str, source_file: str) -> TaskFile:
        """
        Parse JSON file data into TaskFile object
        
        Args:
            file_data: File JSON data
            task_id: Task ID for error reporting
            source_file: Source file for error reporting
            
        Returns:
            TaskFile: Parsed task file object
        """
        # Validate required fields
        required_fields = ["filename", "content"]
        for field in required_fields:
            if field not in file_data:
                raise ValueError(f"Missing '{field}' in file data of task {task_id} in {source_file}")
        
        # Validate all file fields - NO DEFAULTS ALLOWED
        if "file_type" not in file_data:
            raise ValueError(f"Missing 'file_type' in file data of task {task_id} in {source_file}")
        
        return TaskFile(
            filename=file_data["filename"],
            content=file_data["content"],
            description=file_data["description"] if "description" in file_data and file_data["description"] is not None else None,
            file_type=file_data["file_type"]
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
        # Check cache first
        if task_set_name in self._loaded_task_sets:
            return self._loaded_task_sets[task_set_name]
        
        # Try directory-based format first (new format)
        directory_path = self.data_directory / task_set_name
        tasks_file = directory_path / "tasks.json"
        
        if tasks_file.exists():
            # Load from directory structure
            json_file_path = f"{task_set_name}/tasks.json"
            task_set = self.load_task_set_from_json(json_file_path)
        else:
            # Fall back to direct JSON file (legacy format)
            json_file_path = f"{task_set_name}.json"
            task_set = self.load_task_set_from_json(json_file_path)
        
        # Cache for future use
        self._loaded_task_sets[task_set_name] = task_set
        
        return task_set
    
    def validate_task_set(self, task_set_name: str) -> List[str]:
        """
        Validate a task set and return any errors
        
        Args:
            task_set_name: Name of task set to validate
            
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        try:
            task_set = self.load_task_set(task_set_name)
            return task_set.validate()
        except Exception as e:
            return [f"Failed to load task set: {e}"]

# Global JSON loader instance
_json_loader = JSONTaskLoader()

def get_json_loader() -> JSONTaskLoader:
    """Get the global JSON task loader"""
    return _json_loader