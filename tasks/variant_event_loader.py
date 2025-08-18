"""
Enhanced Event System with Variants Support
Supports attribute + category random sampling from event_set.json
"""

import json
import random
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

class EventPhase(Enum):
    PHASE_1 = "phase_1"  # Tasks 1-7: Building relationship, light-medium pressure
    PHASE_2 = "phase_2"  # Tasks 8-14: Deep collaboration, medium-high pressure

class PressureLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class EventVariant:
    """Represents a specific variant of an event with pressure level"""
    content: str
    pressure_level: str

@dataclass 
class DeceptiveEvent:
    """Enhanced event with variants support"""
    description: str
    category: str
    variants: Dict[str, EventVariant]
    
    def get_variant(self, pressure_level: str) -> EventVariant:
        """Get specific variant by pressure level"""
        return self.variants.get(pressure_level.lower())
    
    def get_random_variant(self) -> EventVariant:
        """Get random variant"""
        return random.choice(list(self.variants.values()))

class VariantEventLoader:
    """Loads event sets with variants support"""
    
    def __init__(self, data_directory: str = "tasks/data"):
        self.data_directory = Path(data_directory)
    
    def load_event_set(self, task_set_name: str) -> Dict:
        """Load event set JSON for a specific task set"""
        event_set_file = self.data_directory / task_set_name / "event_set.json"
        
        if not event_set_file.exists():
            raise FileNotFoundError(f"Event set file not found: {event_set_file}")
        
        try:
            with open(event_set_file, 'r', encoding='utf-8') as f:
                event_set_data = json.load(f)
            return event_set_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in event set file {event_set_file}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load event set from {event_set_file}: {e}")
    
    def parse_events_from_json(self, event_set_data: Dict) -> Dict[EventPhase, List[DeceptiveEvent]]:
        """Parse event data from JSON with variants support"""
        
        if "phases" not in event_set_data:
            raise ValueError("Missing 'phases' in event set data")
        
        phase_events = {}
        phases_data = event_set_data["phases"]
        
        for phase_key, phase_data in phases_data.items():
            # Map phase key to enum
            if phase_key == "phase_1":
                phase_enum = EventPhase.PHASE_1
            elif phase_key == "phase_2":
                phase_enum = EventPhase.PHASE_2
            # Only phase_1 and phase_2 supported in 14-task format
            else:
                raise ValueError(f"Unknown phase key: {phase_key}")
            
            # Parse events for this phase
            if "events" not in phase_data:
                raise ValueError(f"Missing 'events' in phase {phase_key}")
            
            events = []
            for event_data in phase_data["events"]:
                # Validate required fields for new format
                required_fields = ["description", "category", "variants"]
                for field in required_fields:
                    if field not in event_data:
                        raise ValueError(f"Missing '{field}' in event data for phase {phase_key}")
                
                # Parse variants
                variants = {}
                variants_data = event_data["variants"]
                for variant_key, variant_data in variants_data.items():
                    if "content" not in variant_data or "pressure_level" not in variant_data:
                        raise ValueError(f"Missing content/pressure_level in variant {variant_key}")
                    
                    variants[variant_key] = EventVariant(
                        content=variant_data["content"],
                        pressure_level=variant_data["pressure_level"]
                    )
                
                event = DeceptiveEvent(
                    description=event_data["description"],
                    category=event_data["category"],
                    variants=variants
                )
                events.append(event)
            
            phase_events[phase_enum] = events
        
        return phase_events

class VariantEventSystem:
    """
    Enhanced event system with variants and attribute+category sampling support
    """
    
    def __init__(self, task_set_name: str, global_event_probability: float = 0.3):
        self.task_set_name = task_set_name
        self.global_event_probability = global_event_probability
        self.loader = VariantEventLoader()
        self._load_event_sets()
    
    def _load_event_sets(self):
        """Load phase-specific event sets from JSON"""
        try:
            self.event_set_data = self.loader.load_event_set(self.task_set_name)
            self.phase_events = self.loader.parse_events_from_json(self.event_set_data)
            
            # Build category index for fast lookup
            self._build_category_index()
            
        except Exception as e:
            raise RuntimeError(f"Failed to load event sets for {self.task_set_name}: {e}")
    
    def _build_category_index(self):
        """Build index for category-based sampling"""
        self.category_index = {}  # category -> {phase -> [events]}
        
        for phase, events in self.phase_events.items():
            for event in events:
                category = event.category
                if category not in self.category_index:
                    self.category_index[category] = {}
                if phase not in self.category_index[category]:
                    self.category_index[category][phase] = []
                self.category_index[category][phase].append(event)
    
    def get_phase_for_task(self, task_sequence_num: int) -> EventPhase:
        """Determine which phase a given task sequence number belongs to"""
        if task_sequence_num <= 7:
            return EventPhase.PHASE_1
        else:
            return EventPhase.PHASE_2
    
    def should_trigger_event(self) -> bool:
        """Determine if an event should be triggered based on probability"""
        return random.random() < self.global_event_probability
    
    def sample_event_by_category(self, phase: EventPhase, category: str) -> Optional[DeceptiveEvent]:
        """Sample event by specific category and phase"""
        if category not in self.category_index:
            return None
        
        if phase not in self.category_index[category]:
            return None
        
        events = self.category_index[category][phase]
        if not events:
            return None
        
        return random.choice(events)
    
    def sample_event_by_attributes(self, phase: EventPhase, 
                                  category: Optional[str] = None,
                                  pressure_preference: Optional[str] = None) -> Optional[DeceptiveEvent]:
        """
        Sample event based on attributes (category + pressure preference)
        
        Args:
            phase: Which phase to sample from
            category: Specific category to filter by (optional)
            pressure_preference: Preferred pressure level (optional)
        """
        if category:
            # Sample from specific category
            event = self.sample_event_by_category(phase, category)
        else:
            # Sample from any category in phase
            event = self.sample_event(phase)
        
        return event
    
    def sample_event(self, phase: EventPhase) -> DeceptiveEvent:
        """Sample a random event from the specified phase event set"""
        if phase not in self.phase_events:
            raise ValueError(f"No events loaded for phase: {phase}")
        
        events = self.phase_events[phase]
        if not events:
            raise ValueError(f"No events available for phase: {phase}")
        
        return random.choice(events)
    
    def get_event_for_task(self, task_sequence_num: int, 
                         category: Optional[str] = None,
                         pressure_preference: Optional[str] = None) -> Optional[DeceptiveEvent]:
        """
        Main interface: Get an event for a specific task sequence number with attribute filtering
        
        Args:
            task_sequence_num: Task sequence number
            category: Optional category filter
            pressure_preference: Optional pressure level preference
            
        Returns:
            DeceptiveEvent or None if no event should be triggered
        """
        if not self.should_trigger_event():
            return None
        
        phase = self.get_phase_for_task(task_sequence_num)
        return self.sample_event_by_attributes(phase, category, pressure_preference)
    
    def get_variant_content(self, event: DeceptiveEvent, pressure_level: str) -> str:
        """Get specific variant content from an event"""
        variant = event.get_variant(pressure_level)
        if variant:
            return variant.content
        else:
            # Fallback to random variant if requested level not found
            variant = event.get_random_variant()
            return variant.content
    
    def create_enhanced_prompt(self, base_prompt: str, event: Optional[DeceptiveEvent], 
                              pressure_level: str = None) -> str:
        """
        Create the final prompt by concatenating event variant to base prompt
        
        Args:
            base_prompt: Original task prompt
            event: Selected event (can be None)
            pressure_level: Specific pressure level to use (optional)
        """
        if event is None:
            return base_prompt
        
        # Get variant content
        if pressure_level:
            content = self.get_variant_content(event, pressure_level)
        else:
            # Use random variant
            variant = event.get_random_variant()
            content = variant.content
        
        # Natural concatenation
        enhanced_prompt = f"{base_prompt}\n\n{content}"
        return enhanced_prompt
    
    def get_event_info_for_manager(self, event: Optional[DeceptiveEvent], 
                                  variant_used: Optional[EventVariant] = None) -> Dict:
        """
        Create event info dictionary for manager context
        """
        if event is None:
            return {}
        
        info = {
            'category': event.category,
            'description': event.description,
            'triggered': True
        }
        
        if variant_used:
            info.update({
                'pressure_level': variant_used.pressure_level,
                'content_preview': variant_used.content[:100] + "..." if len(variant_used.content) > 100 else variant_used.content
            })
        
        return info
    
    def get_available_categories(self, phase: Optional[EventPhase] = None) -> List[str]:
        """Get list of available categories, optionally filtered by phase"""
        if phase is None:
            return list(self.category_index.keys())
        else:
            categories = []
            for category, phase_dict in self.category_index.items():
                if phase in phase_dict and phase_dict[phase]:
                    categories.append(category)
            return categories

# Factory function for backwards compatibility and easy integration
def get_variant_event_system(task_set_name: str, global_event_probability: float = 0.3) -> VariantEventSystem:
    """Factory function to create variant event system for a task set"""
    return VariantEventSystem(task_set_name, global_event_probability)

# For backwards compatibility - maps to new system
def get_event_system(task_set_name: str, global_event_probability: float = 0.3) -> VariantEventSystem:
    """Backwards compatible factory function"""
    return get_variant_event_system(task_set_name, global_event_probability)
