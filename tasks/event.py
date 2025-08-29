"""
Enhanced Event System with Variants Support
Supports attribute + category random sampling from event_set.json
"""

import json
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Import validation functions
from utils.common_funcs import check_json_format_integrity, validate_category, validate_pressure_level

# Constants
UNCONTROL = "UNCONTROL"

@dataclass 
class Event:
    """Event with complete variant information directly accessible"""
    name: str
    category: str
    variants: Dict[str, Dict[str, str]]  # Store variant data directly without creating EventVariant objects
    
    def get_variant_info(self, pressure_level: str) -> Dict[str, str]:
        """Get complete variant information including Event data"""
        pressure_level = pressure_level.lower()
        if pressure_level not in self.variants:
            available_levels = list(self.variants.keys())
            raise ValueError(f"Invalid pressure_level '{pressure_level}'. Available levels: {available_levels}")
            
        variant_data = self.variants[pressure_level]
        return {
            'name': self.name,
            'category': self.category,
            'content': variant_data['content'],
            'pressure_level': variant_data['pressure_level']
        }
    
    def get_content(self, pressure_level: str) -> str:
        """Get content for specific pressure level"""
        pressure_level = pressure_level.lower()
        if pressure_level in self.variants:
            return self.variants[pressure_level]['content']
        # No fallback - fail fast
        available_levels = list(self.variants.keys())
        raise ValueError(f"Invalid pressure_level '{pressure_level}'. Available levels: {available_levels}")
    
    def get_random_variant_info(self) -> Dict[str, str]:
        """Get random variant with complete information"""
        random_level = random.choice(list(self.variants.keys()))
        return self.get_variant_info(random_level)
    
    def get_available_pressure_levels(self) -> List[str]:
        """Get list of available pressure levels for this event"""
        return list(self.variants.keys())

class EventLoader:
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
            
            # Validate JSON format integrity
            event_set_data = check_json_format_integrity(event_set_data, str(event_set_file))
            return event_set_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in event set file {event_set_file}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load event set from {event_set_file}: {e}")
    
    def parse_events_from_json(self, event_set_data: Dict) -> Dict[str, List[Event]]:
        """Parse event data from JSON with variants support"""
        
        if "phases" not in event_set_data:
            raise ValueError("Missing 'phases' in event set data")
        
        phase_events = {}
        phases_data = event_set_data["phases"]
        
        for phase_key, phase_data in phases_data.items():
            # Use phase key directly as string
            phase_string = phase_key
            
            # Parse events for this phase
            if "events" not in phase_data:
                raise ValueError(f"Missing 'events' in phase {phase_key}")
            
            events = []
            for event_data in phase_data["events"]:
                # Validate required fields for new format
                required_fields = ["category", "name", "variants"]
                for field in required_fields:
                    if field not in event_data:
                        raise ValueError(f"Missing '{field}' in event data for phase {phase_key}")
                
                # Validate category using common_funcs
                if 'name' not in event_data:
                    raise ValueError(f"Missing 'name' field in event data of phase {phase_key}")
                category = validate_category(event_data["category"], f"phase {phase_key} event {event_data['name']}")
                
                # Parse variants - store variant data directly
                variants = {}
                variants_data = event_data["variants"]
                for variant_key, variant_data in variants_data.items():
                    if "content" not in variant_data or "pressure_level" not in variant_data:
                        raise ValueError(f"Missing content/pressure_level in variant {variant_key}")
                    
                    variants[variant_key] = {
                        'content': variant_data["content"],
                        'pressure_level': variant_data["pressure_level"]
                    }
                
                event = Event(
                    name=event_data["name"],  # Read name field like GC_E1
                    category=category,  # Use validated category
                    variants=variants
                )
                events.append(event)
            
            phase_events[phase_string] = events
        
        return phase_events

class EventSystem:
    """
    Enhanced event system with variants and attribute+category sampling support
    """
    
    def __init__(self, task_load_folder_name: str, p_event: float, 
                 control_category: str, control_pressure_level: str, 
                 seed: int = None, total_tasks: int = 14):
        self.task_load_folder_name = task_load_folder_name
        self.p_event = p_event
        self.seed = seed
        
        # Validate control parameters - must be explicitly provided
        valid_categories = ['GOAL_CONFLICT', 'MORAL_DILEMMA', 'COMPETITIVE_INTERACTION', 'AUTHORITY_DIRECTIVE', 'INFORMATION_GAP']
        valid_pressures = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        if control_category not in valid_categories + [UNCONTROL, "NONE"]:
            raise ValueError(f"Invalid control_category: '{control_category}'. Valid categories: {valid_categories + [UNCONTROL, 'NONE']}")
        
        if control_pressure_level not in valid_pressures + [UNCONTROL, "NONE"]:
            raise ValueError(f"Invalid control_pressure_level: '{control_pressure_level}'. Valid levels: {valid_pressures + [UNCONTROL, 'NONE']}")
            
        self.control_category = control_category
        self.control_pressure_level = control_pressure_level
        
        if seed is not None:
            random.seed(seed)  # Set global random seed
        self.loader = EventLoader()
        self._load_event_sets()
        
    
    def _load_event_sets(self) -> None:
        """Load phase-specific event sets from JSON"""
        try:
            self.event_set_data = self.loader.load_event_set(self.task_load_folder_name)
            self.event_set = self.loader.parse_events_from_json(self.event_set_data)
            
            # Build category index for fast lookup
            self._build_category_index()
            
        except Exception as e:
            raise RuntimeError(f"Failed to load event sets for {self.task_load_folder_name}: {e}")
    
    def _build_category_index(self) -> None:
        """Build index for category-based sampling"""
        self.category_index = {}  # category -> {phase -> [events]}
        
        for phase, events in self.event_set.items():
            for event in events:
                category = event.category
                if category not in self.category_index:
                    self.category_index[category] = {}
                if phase not in self.category_index[category]:
                    self.category_index[category][phase] = []
                self.category_index[category][phase].append(event)

    
    def should_trigger_event(self, task_sequence_num: int = None) -> bool:
        """Determine if an event should be triggered based on probability with seed support"""
        return random.random() < self.p_event
    
    def sample_event_by_category(self, phase: str, category: str, task_sequence_num: int = None) -> Optional[Event]:
        """Sample event by specific category and phase with seed support"""
        if category not in self.category_index:
            return None
        
        if phase not in self.category_index[category]:
            return None
        
        events = self.category_index[category][phase]
        if not events:
            return None
        
        return random.choice(events)
    
    def sample_event(self, phase: str, task_sequence_num: int = None) -> Event:
        """Sample a random event from the specified phase event set with seed support"""
        if phase not in self.event_set:
            raise ValueError(f"No events loaded for phase: {phase}")
        
        events = self.event_set[phase]
        if not events:
            raise ValueError(f"No events available for phase: {phase}")
        
        return random.choice(events)
    
    def get_event_and_variant_for_phase(self, phase: str, task_sequence_num: int) -> tuple[Optional[Event], Optional[Dict[str, str]]]:
        """
        Get event and variant using three-layer independent random algorithm with consistent state
        
        Core algorithm: Always generate 3 random numbers, selectively use results when controlled
        
        Args:
            phase: Phase string (e.g., "phase_1")
            task_sequence_num: Task sequence number
            
        Returns:
            (selected_event, selected_variant) or (None, None) if no event triggered
        """
        # NONE control: Force no events when either category or pressure is NONE
        if self.control_category == "NONE" or self.control_pressure_level == "NONE":
            return None, None
            
        # Step 1: Check if event should be triggered
        if not self.should_trigger_event(task_sequence_num):
            return None, None
        
        # Step 2: Get events for this phase
        phase_events = self.event_set[phase]
        
        # Step 3: **Always generate 3 random numbers to ensure consistent state consumption**
        # These 3 random numbers must be consumed in the same order across all control modes
        random_category_idx = random.randint(0, len(self.category_index) - 1)  # 第1个随机数
        random_event_idx = random.randint(0, len(phase_events) - 1)            # 第2个随机数  
        random_pressure_idx = random.randint(0, 3)                             # 第3个随机数 (4个pressure levels)
        
        # 第4步：根据有效控制参数决定使用随机值还是固定值
        categories_list = list(self.category_index.keys())
        
        if self.control_category != UNCONTROL:
            # Category被控制，使用指定的category
            if self.control_category in categories_list:
                category = self.control_category
            else:
                # 指定的category不存在，直接报错
                raise ValueError(f"Invalid control_category: '{self.control_category}'. Valid categories: {categories_list}")
        else:
            # Category不被控制，使用随机索引
            category = categories_list[random_category_idx]
        
        # 第5步：根据最终category选择event
        category_events = self.category_index[category][phase]
        if not category_events:
            # This should NEVER happen with proper 5x2x4x4 JSON structure - fail fast for extreme bugs
            raise ValueError(f"CRITICAL: Category '{category}' has no events in phase '{phase}'. JSON structure corrupted!")
        
        # 使用event随机索引选择该category下的事件
        event_idx_in_category = random_event_idx % len(category_events)
        selected_event = category_events[event_idx_in_category]
        
        # 第6步：根据有效控制参数选择pressure_level
        pressure_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        if self.control_pressure_level != UNCONTROL:
            # Pressure被控制，使用指定的pressure_level
            pressure_level = self.control_pressure_level
        else:
            # Pressure不被控制，使用随机索引
            pressure_level = pressure_levels[random_pressure_idx]
        
        # 第7步：获取最终variant信息
        selected_variant_info = selected_event.get_variant_info(pressure_level)
        
        return selected_event, selected_variant_info
    
    
    

# Factory function for backwards compatibility and easy integration

