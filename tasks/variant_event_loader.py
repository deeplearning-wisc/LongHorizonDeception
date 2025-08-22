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
    PHASE_1 = "phase_1"  # Building relationship, light-medium pressure
    PHASE_2 = "phase_2"  # Deep collaboration, medium-high pressure

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
    name: str  # 新增name字段，如GC_E1, CI_E2等
    category: str
    variants: Dict[str, EventVariant]
    
    def get_variant(self, pressure_level: str) -> EventVariant:
        """Get specific variant by pressure level"""
        return self.variants.get(pressure_level.lower())
    
    def get_random_variant(self, seed_offset: int = None) -> EventVariant:
        """Get random variant with optional seed support"""
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
                required_fields = ["category", "name", "variants"]
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
                    name=event_data["name"],  # 读取name字段如GC_E1
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
    
    def __init__(self, task_set_name: str, global_event_probability: float = 0.3, seed: int = None, 
                 control_category: str = None, control_intensity: str = None, 
                 show_preview: bool = True, max_tasks: int = 14):
        self.task_set_name = task_set_name
        self.global_event_probability = global_event_probability
        self.seed = seed
        self.control_category = control_category
        self.control_intensity = control_intensity
        
        if seed is not None:
            random.seed(seed)  # 设置全局随机种子
        self.loader = VariantEventLoader()
        self._load_event_sets()
        
        # 🆕 集成的EVENT序列预览
        if show_preview:
            self._print_event_sequence_preview(max_tasks)
    
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

    
    def _print_event_sequence_preview(self, max_tasks: int):
        """打印EVENT序列预览，应用全局控制参数"""
        print(f"🎲 Event Seed: {self.seed if self.seed is not None else 'Random'}")
        
        # 显示控制信息
        if self.control_category or self.control_intensity:
            control_info = []
            if self.control_category:
                control_info.append(f"Category: {self.control_category}")
            if self.control_intensity:
                control_info.append(f"Intensity: {self.control_intensity}")
            print(f"🎯 Global Control Active: {', '.join(control_info)}")
        
        print("📋 EVENT SEQUENCE PREVIEW:")
        print("=" * 60)
        
        # 创建独立的随机状态来预览（不影响主系统）
        import random
        preview_random = random.Random(self.seed)
        
        for task_num in range(1, max_tasks + 1):
            # 模拟事件触发概率
            should_trigger = preview_random.random() < self.global_event_probability
            
            if should_trigger:
                # 模拟三层随机数生成
                random_category_idx = preview_random.randint(0, len(self.category_index) - 1)
                phase = self.get_phase_for_task(task_num)
                phase_events = self.phase_events[phase]
                random_event_idx = preview_random.randint(0, len(phase_events) - 1)
                random_pressure_idx = preview_random.randint(0, 3)
                
                # 应用控制逻辑
                categories_list = list(self.category_index.keys())
                
                if self.control_category is not None:
                    final_category = self.control_category
                else:
                    final_category = categories_list[random_category_idx]
                
                # 选择事件
                if final_category in self.category_index and phase in self.category_index[final_category]:
                    category_events = self.category_index[final_category][phase]
                    if category_events:
                        event_idx_in_category = random_event_idx % len(category_events)
                        selected_event = category_events[event_idx_in_category]
                    else:
                        selected_event = phase_events[random_event_idx]
                else:
                    selected_event = phase_events[random_event_idx]
                
                # 选择pressure
                pressure_levels = ['low', 'medium', 'high', 'critical']
                if self.control_intensity is not None:
                    final_pressure = self.control_intensity.lower()
                else:
                    final_pressure = pressure_levels[random_pressure_idx]
                
                phase_indicator = "PH1" if task_num <= 7 else "PH2"
                print(f"  Task {task_num:2d} ({phase_indicator}): {selected_event.name:15s} {final_pressure.upper():8s} - {selected_event.category}")
            else:
                print(f"  Task {task_num:2d}: NO_EVENT")
        
        print("=" * 60)
        print()
    
    def get_phase_for_task(self, task_sequence_num: int) -> EventPhase:
        """Determine which phase a given task sequence number belongs to - 动态读取JSON配置"""
        # 从JSON配置读取阶段范围，不再硬编码7
        phases_data = self.event_set_data.get('phases', {})
        
        for phase_key, phase_data in phases_data.items():
            if 'task_start' in phase_data and 'task_end' in phase_data:
                if phase_data['task_start'] <= task_sequence_num <= phase_data['task_end']:
                    if phase_key == "phase_1":
                        return EventPhase.PHASE_1
                    elif phase_key == "phase_2":
                        return EventPhase.PHASE_2
        
        # 回退到默认逻辑
        if task_sequence_num <= 7:
            return EventPhase.PHASE_1
        else:
            return EventPhase.PHASE_2
    
    def should_trigger_event(self, task_num: int = None) -> bool:
        """Determine if an event should be triggered based on probability with seed support"""
        return random.random() < self.global_event_probability
    
    def sample_event_by_category(self, phase: EventPhase, category: str, task_num: int = None) -> Optional[DeceptiveEvent]:
        """Sample event by specific category and phase with seed support"""
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
                                  pressure_preference: Optional[str] = None,
                                  task_num: int = None) -> Optional[DeceptiveEvent]:
        """
        Sample event based on attributes (category + pressure preference)
        
        Args:
            phase: Which phase to sample from
            category: Specific category to filter by (optional)
            pressure_preference: Preferred pressure level (optional)
            task_num: Task number for seed-based selection
        """
        if category:
            # Sample from specific category
            event = self.sample_event_by_category(phase, category, task_num)
        else:
            # Sample from any category in phase
            event = self.sample_event(phase, task_num)
        
        return event
    
    def sample_event(self, phase: EventPhase, task_num: int = None) -> DeceptiveEvent:
        """Sample a random event from the specified phase event set with seed support"""
        if phase not in self.phase_events:
            raise ValueError(f"No events loaded for phase: {phase}")
        
        events = self.phase_events[phase]
        if not events:
            raise ValueError(f"No events available for phase: {phase}")
        
        return random.choice(events)
    
    def get_event_for_task(self, task_sequence_num: int, 
                         control_category: Optional[str] = None,
                         control_intensity: Optional[str] = None) -> Optional[DeceptiveEvent]:
        """
        Main interface: Get an event with optional control parameters
        
        Args:
            task_sequence_num: Task sequence number
            control_category: 指定category (e.g., "GOAL_CONFLICT"), None为随机
            control_intensity: 指定intensity (e.g., "high"), None为随机
            
        Returns:
            DeceptiveEvent or None if no event should be triggered
            
        Control模式:
        1. 都不指定: 完全随机选择
        2. 只指定category: 从该category随机选event，随机选variant
        3. 只指定intensity: 随机选event，强制选指定intensity的variant
        4. 都指定: 从指定category选event，强制选指定intensity的variant
        """
        if not self.should_trigger_event(task_sequence_num):
            return None
        
        phase = self.get_phase_for_task(task_sequence_num)
        
        # 根据control参数选择事件
        if control_category is not None:
            # 指定了category，从该category中选择
            selected_event = self.sample_event_by_category(phase, control_category, task_sequence_num)
            if selected_event is None:
                # 指定的category在当前phase不存在，回退到随机选择
                selected_event = self.sample_event(phase, task_sequence_num)
        else:
            # 没有指定category，随机选择
            selected_event = self.sample_event(phase, task_sequence_num)
        
        # 如果指定了intensity，需要选择对应的variant
        if control_intensity is not None:
            # 检查该event是否有指定的intensity variant
            if control_intensity.lower() in selected_event.variants:
                # 直接使用指定的variant
                pass  # 在get_variant时会处理
            else:
                # 指定的intensity不存在，回退到随机选择
                pass  # 在get_variant时会随机选择
        
        return selected_event
    
    def get_event_and_variant_for_task(self, task_sequence_num: int, 
                                     control_category: Optional[str] = None,
                                     control_intensity: Optional[str] = None) -> tuple[Optional[DeceptiveEvent], Optional[EventVariant]]:
        """
        获取事件和variant，使用三层独立随机但保持状态一致的算法
        
        核心算法：总是生成3个随机数，控制时选择性使用结果
        
        Args:
            task_sequence_num: 任务序列号
            control_category: 控制category (None=使用系统级控制)
            control_intensity: 控制intensity (None=使用系统级控制)
            
        Returns:
            (selected_event, selected_variant) or (None, None) if no event triggered
        """
        # 优先使用系统级控制参数，如果方法参数为None
        effective_control_category = control_category if control_category is not None else self.control_category
        effective_control_intensity = control_intensity if control_intensity is not None else self.control_intensity
        # 第1步：检查是否应该触发事件
        if not self.should_trigger_event(task_sequence_num):
            return None, None
        
        # 第2步：确定phase
        phase = self.get_phase_for_task(task_sequence_num)
        phase_events = self.phase_events[phase]
        
        # 第3步：**总是生成3个随机数，保证状态消耗一致**
        # 这3个随机数的消耗顺序必须在所有控制模式下保持一致
        random_category_idx = random.randint(0, len(self.category_index) - 1)  # 第1个随机数
        random_event_idx = random.randint(0, len(phase_events) - 1)            # 第2个随机数  
        random_pressure_idx = random.randint(0, 3)                             # 第3个随机数 (4个pressure levels)
        
        # 第4步：根据有效控制参数决定使用随机值还是固定值
        categories_list = list(self.category_index.keys())
        
        if effective_control_category is not None:
            # Category被控制，使用指定的category
            if effective_control_category in categories_list:
                final_category = effective_control_category
            else:
                # 指定的category不存在，fallback到随机
                final_category = categories_list[random_category_idx]
        else:
            # Category不被控制，使用随机索引
            final_category = categories_list[random_category_idx]
        
        # 第5步：根据最终category选择event
        category_events = self.category_index[final_category][phase]
        if not category_events:
            # 该category在此phase没有事件，fallback到全部事件
            selected_event = phase_events[random_event_idx]
        else:
            # 使用event随机索引选择该category下的事件
            event_idx_in_category = random_event_idx % len(category_events)
            selected_event = category_events[event_idx_in_category]
        
        # 第6步：根据有效控制参数选择pressure level
        pressure_levels = ['low', 'medium', 'high', 'critical']
        
        if effective_control_intensity is not None:
            # Pressure被控制，使用指定的intensity
            final_pressure = effective_control_intensity.lower()
        else:
            # Pressure不被控制，使用随机索引
            final_pressure = pressure_levels[random_pressure_idx]
        
        # 第7步：获取最终variant
        selected_variant = selected_event.get_variant(final_pressure)
        if selected_variant is None:
            # 指定的pressure不存在，使用随机pressure
            final_pressure = pressure_levels[random_pressure_idx]
            selected_variant = selected_event.get_variant(final_pressure)
        
        return selected_event, selected_variant
    
    def get_variant_content(self, event: DeceptiveEvent, pressure_level: str, task_num: int = None) -> str:
        """Get specific variant content from an event with seed support"""
        variant = event.get_variant(pressure_level)
        if variant:
            return variant.content
        else:
            # Fallback to random variant if requested level not found
            variant = event.get_random_variant()
            return variant.content

    
    def get_controlled_variant(self, event: DeceptiveEvent, control_intensity: str = None, task_num: int = None) -> EventVariant:
        """
        Get variant with optional intensity control
        
        Args:
            event: The selected event
            control_intensity: 指定intensity level (e.g., "high"), None为随机
            task_num: Task number for seed support
            
        Returns:
            Selected EventVariant
        """
        if control_intensity is not None:
            # 指定了intensity，尝试获取对应variant
            variant = event.get_variant(control_intensity)
            if variant:
                return variant
            else:
                # 指定的intensity不存在，回退到随机选择
                print(f"Warning: intensity '{control_intensity}' not found for event {event.name}, falling back to random")
        
        # 随机选择variant
        return event.get_random_variant()
    
    def create_enhanced_prompt(self, base_prompt: str, event: Optional[DeceptiveEvent], 
                              control_intensity: str = None, task_num: int = None) -> str:
        """
        Create the final prompt by concatenating event variant to base prompt
        
        Args:
            base_prompt: Original task prompt
            event: Selected event (can be None)
            control_intensity: 指定intensity level (可选)
            task_num: Task number for seed support
        """
        if event is None:
            return base_prompt
        
        # Get variant content
        if control_intensity:
            content = self.get_variant_content(event, control_intensity, task_num)
        else:
            # Use random variant
            variant = event.get_random_variant()
            content = variant.content
        
        # Natural concatenation
        enhanced_prompt = f"{base_prompt}\n\n{content}"
        return enhanced_prompt
    
    def get_event_info_for_manager(self, event: Optional[DeceptiveEvent], 
                                  variant_used: Optional[EventVariant] = None,
                                  control_info: Dict = None) -> Dict:
        """
        Create event info dictionary for manager context with control information
        """
        if event is None:
            return {}
        
        info = {
            'name': event.name,  # 使用event的name字段
            'category': event.category,
            'triggered': True
        }
        
        if variant_used:
            info.update({
                'pressure_level': variant_used.pressure_level,
                'content_preview': variant_used.content[:100] + "..." if len(variant_used.content) > 100 else variant_used.content
            })
        
        # 添加control信息
        if control_info:
            info.update({
                'control_mode': control_info.get('mode', 'random'),
                'controlled_category': control_info.get('category'),
                'controlled_intensity': control_info.get('intensity')
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
def get_variant_event_system(task_set_name: str, global_event_probability: float = 0.3, seed: int = None,
                            control_category: str = None, control_intensity: str = None,
                            show_preview: bool = True, max_tasks: int = 14) -> VariantEventSystem:
    """Factory function to create variant event system for a task set with control support"""
    return VariantEventSystem(task_set_name, global_event_probability, seed, 
                            control_category, control_intensity, show_preview, max_tasks)

# For backwards compatibility - maps to new system with control support
def get_event_system(task_set_name: str, global_event_probability: float = 0.3, seed: int = None,
                   control_category: str = None, control_intensity: str = None,
                   show_preview: bool = True, max_tasks: int = 14) -> VariantEventSystem:
    """Backwards compatible factory function with control mechanism support"""
    return get_variant_event_system(task_set_name, global_event_probability, seed,
                                  control_category, control_intensity, show_preview, max_tasks)
