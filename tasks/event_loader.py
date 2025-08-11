"""
JSON-based event system loader
Replaces hardcoded event vocabularies with JSON-based configuration
"""

import json
import random
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

class EventPhase(Enum):
    PHASE_1 = "phase_1"  # Days 1-7: Building relationship, light-medium pressure
    PHASE_2 = "phase_2"  # Days 8-15: Deep collaboration, medium-high pressure  
    PHASE_3 = "phase_3"  # Days 16-21: Crisis/final decisions, high-extreme pressure

@dataclass
class DeceptiveEvent:
    """Represents a high-pressure contextual event that may induce deceptive behavior"""
    content: str
    description: str
    pressure_level: str  # "MEDIUM", "HIGH", "EXTREME", "TOTAL_DEVASTATION"

class JSONEventLoader:
    """Loads event vocabularies from JSON files"""
    
    def __init__(self, data_directory: str = "tasks/data"):
        self.data_directory = Path(data_directory)
    
    def load_vocabulary(self, task_set_name: str) -> Dict:
        """Load vocabulary JSON for a specific task set"""
        vocabulary_file = self.data_directory / task_set_name / "vocabulary.json"
        
        if not vocabulary_file.exists():
            raise FileNotFoundError(f"Vocabulary file not found: {vocabulary_file}")
        
        try:
            with open(vocabulary_file, 'r', encoding='utf-8') as f:
                vocabulary_data = json.load(f)
            
            return vocabulary_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in vocabulary file {vocabulary_file}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load vocabulary from {vocabulary_file}: {e}")
    
    def parse_events_from_json(self, vocabulary_data: Dict) -> Dict[EventPhase, List[DeceptiveEvent]]:
        """Parse event data from JSON into structured objects"""
        
        if "phases" not in vocabulary_data:
            raise ValueError("Missing 'phases' in vocabulary data")
        
        phase_events = {}
        phases_data = vocabulary_data["phases"]
        
        for phase_key, phase_data in phases_data.items():
            # Map phase key to enum
            if phase_key == "phase_1":
                phase_enum = EventPhase.PHASE_1
            elif phase_key == "phase_2":
                phase_enum = EventPhase.PHASE_2
            elif phase_key == "phase_3":
                phase_enum = EventPhase.PHASE_3
            else:
                raise ValueError(f"Unknown phase key: {phase_key}")
            
            # Parse events for this phase
            if "events" not in phase_data:
                raise ValueError(f"Missing 'events' in phase {phase_key}")
            
            events = []
            for event_data in phase_data["events"]:
                # Validate required fields
                required_fields = ["content", "description", "pressure_level"]
                for field in required_fields:
                    if field not in event_data:
                        raise ValueError(f"Missing '{field}' in event data for phase {phase_key}")
                
                event = DeceptiveEvent(
                    content=event_data["content"],
                    description=event_data["description"],
                    pressure_level=event_data["pressure_level"]
                )
                events.append(event)
            
            phase_events[phase_enum] = events
        
        return phase_events

class JSONEventSystem:
    """
    JSON-based event system that replaces the old hardcoded variant system.
    Provides phase-specific vocabularies of high-pressure events loaded from JSON.
    """
    
    def __init__(self, task_set_name: str, global_event_probability: float = 0.3):
        self.task_set_name = task_set_name
        self.global_event_probability = global_event_probability
        self.loader = JSONEventLoader()
        self._load_vocabularies()
    
    def _load_vocabularies(self):
        """Load phase-specific event vocabularies from JSON"""
        try:
            vocabulary_data = self.loader.load_vocabulary(self.task_set_name)
            self.phase_events = self.loader.parse_events_from_json(vocabulary_data)
            
            # Store metadata (but keep using config's p_event for probability)
            # JSON probability is ignored - we use config's p_event instead
            
        except Exception as e:
            raise RuntimeError(f"Failed to load event vocabularies for {self.task_set_name}: {e}")
    
    def get_phase_for_day(self, day: int) -> EventPhase:
        """Determine which phase a given day belongs to"""
        if day <= 7:
            return EventPhase.PHASE_1
        elif day <= 15:
            return EventPhase.PHASE_2
        else:
            return EventPhase.PHASE_3
    
    def should_trigger_event(self) -> bool:
        """Determine if an event should be triggered based on probability"""
        return random.random() < self.global_event_probability
    
    def sample_event(self, phase: EventPhase) -> DeceptiveEvent:
        """Sample a random event from the specified phase vocabulary"""
        if phase not in self.phase_events:
            raise ValueError(f"No events loaded for phase: {phase}")
        
        events = self.phase_events[phase]
        if not events:
            raise ValueError(f"No events available for phase: {phase}")
        
        return random.choice(events)
    
    def get_event_for_day(self, day: int) -> Optional[DeceptiveEvent]:
        """
        Main interface: Get an event for a specific day if one should be triggered
        Returns None if no event should be triggered
        """
        if not self.should_trigger_event():
            return None
        
        phase = self.get_phase_for_day(day)
        return self.sample_event(phase)
    
    def create_enhanced_prompt(self, base_prompt: str, event: Optional[DeceptiveEvent]) -> str:
        """
        Create the final prompt by naturally concatenating event to base prompt
        """
        if event is None:
            return base_prompt
        
        # Natural concatenation - event feels like part of the original task context
        enhanced_prompt = f"{base_prompt}\n\n{event.content}"
        return enhanced_prompt
    
    def get_event_info_for_manager(self, event: Optional[DeceptiveEvent]) -> Dict:
        """
        Create event info dictionary for manager context
        """
        if event is None:
            return {}
        
        return {
            'pressure_level': event.pressure_level,
            'description': event.description,
            'triggered': True
        }

# Import new variant system for compatibility
try:
    from .variant_event_loader import VariantEventSystem
    _VARIANT_SYSTEM_AVAILABLE = True
except ImportError:
    _VARIANT_SYSTEM_AVAILABLE = False

# Factory function with automatic fallback to variant system
def get_event_system(task_set_name: str, global_event_probability: float = 0.3):
    """
    Factory function to create event system for a task set
    Automatically uses new VariantEventSystem if available, otherwise falls back to JSONEventSystem
    """
    if _VARIANT_SYSTEM_AVAILABLE:
        try:
            # Try to use new variant system first
            return VariantEventSystem(task_set_name, global_event_probability)
        except Exception as e:
            # If variant system fails, fall back to old system
            print(f"Warning: Variant system failed ({e}), falling back to JSONEventSystem")
            return JSONEventSystem(task_set_name, global_event_probability)
    else:
        # Use old system
        return JSONEventSystem(task_set_name, global_event_probability)

def get_event_for_phase(phase: EventPhase, task_set_name: str, global_event_probability: float = 0.3) -> Optional[DeceptiveEvent]:
    """Backwards compatibility function"""
    event_system = get_event_system(task_set_name, global_event_probability)
    return event_system.sample_event(phase)