# Manager Design: Two-Stage Architecture with ManagerMemory Integration

This document describes the current Manager implementation in core/manager.py, focusing on the two-stage evaluation architecture and ManagerMemory integration.

## Current Architecture Overview

The Manager class implements a clean two-stage design with integrated ManagerMemory system:

### Stage 1: Evaluation
- Creates fresh LLM for each round (short lifecycle)
- Processes LLM response with task/event context and memory history
- Updates three-dimensional internal state
- Generates detailed evaluation reasoning

### Stage 2: Feedback  
- Same LLM continues conversation (context preservation)
- Generates feedback response for the LLM
- Uses evaluation results to guide feedback generation

## Core Components

### Three-Dimensional State System
```python
self.state = {
    'trust_level': float,           # Long-term, deception-focused (-1.0 to 1.0)
    'work_satisfaction': float,     # Short-term, task quality-focused (-1.0 to 1.0)
    'relational_comfort': float     # Long-term, personal connection-focused (-1.0 to 1.0)
}
```

**State Evolution**:
- States update after **every round**, not per task
- Previous state preserved for logging and comparison
- State updates occur before returning results to ensure next evaluation uses updated context

### ManagerMemory Integration
```python
self.memory = ManagerMemory(
    k_window=memory_k_window,              # Recent rounds kept in full detail
    memory_llm_config=manager_api_config,  # LLM for generating summaries
    memory_prompt=manager_memory_prompt    # Prompt for summarization
)
```

**Memory Lifecycle**:
- K-window recent rounds stored in full detail
- Overflow rounds automatically summarized and moved to long-term memory
- Memory context injected into every evaluation
- Complete round data preservation (no truncation)

## Implementation Details

### Manager.__init__()
**Purpose**: Initialize Manager with clean architecture and ManagerMemory system
- Stores configuration and prompts
- Initializes three-dimensional state with initial values
- Creates ManagerMemory instance with K-window configuration
- Formats evaluation prompt with completion threshold and max rounds

### Manager.evaluate()
**Purpose**: Main evaluation method implementing two-stage processing

**Input**: 
- `llm_response`: Complete LLM response text
- `task_event`: Unified task and event information
- `current_round`: Current round number within task

**Output**: Complete state transition information for result_saver

**Process Flow**:
1. Extract task and event from unified object
2. Store previous state for comparison
3. Create fresh LLM for this round
4. Stage 1: Evaluation with memory context
5. Stage 2: Feedback generation (same LLM)
6. **Critical**: Update internal state before returning
7. Add complete round data to memory
8. Return structured results

### Two-Stage Processing Details

#### Stage 1: _stage1_evaluation()
- Retrieves memory context from ManagerMemory
- Builds comprehensive evaluation context with task info, event info, LLM response, current state, and memory
- Uses retry mechanism (max 3 attempts) with format reminders
- Returns parsed evaluation results with state updates

#### Stage 2: _stage2_feedback() 
- Continues same LLM conversation (context preserved)
- Generates feedback based on evaluation results
- Uses retry mechanism for robust parsing
- Returns structured feedback results

### Memory Management Integration

#### _add_to_memory()
**Purpose**: Add complete round data to ManagerMemory system
- Preserves complete task information (no truncation)
- Stores full LLM response (complete preservation)
- Records evaluation and feedback results
- Includes previous and new state information

**Data Structure**:
```python
round_data = {
    'task': {
        'title': task.title,
        'base_prompt': task.base_prompt,  # Complete preservation
        'files': [complete file data]    # All file content preserved
    },
    'event': event_info,                  # Complete event information
    'llm_response': llm_response,         # Complete preservation - no truncation
    'manager_evaluation': {               # Complete evaluation record
        'evaluation_reasoning': str,
        'state_updates': {...},
        'feedback_reasoning': str,
        'feedback_response': str,
        'task_complete': bool
    }
}
```

## Academic Foundations

### Reflexion: Language Agents with Verbal Reinforcement Learning (Shinn et al., 2023)
**Implementation Mapping**:
- Two-stage "evaluation→feedback" matches verbal reinforcement learning
- Internal state updates correspond to agent self-reflection
- Memory integration enables cross-temporal learning

### MemoryBank: Enhancing Large Language Models with Long-Term Memory (Zhong et al., 2023)  
**Implementation Mapping**:
- K-window mechanism preserves recent detailed context
- Automatic summarization compresses older interactions
- Combined context (recent + summarized) provides comprehensive memory

### Generative Agents: Interactive Simulacra of Human Behavior (Park et al., 2023)
**Implementation Mapping**:
- Internal state evolution drives behavior changes
- Memory system enables pattern recognition across interactions
- Private memory context not exposed to evaluated LLM

## Error Handling and Scientific Standards

### Fail-Fast Principle
- All parsing failures result in RuntimeError after retry exhaustion
- No silent failures or default values
- Complete error context preservation for debugging

### Scientific Data Integrity
- Complete data preservation (no truncation of LLM responses or task content)
- Strict key checking (no .get() with defaults)
- Atomic memory operations
- Comprehensive logging of all state transitions

## Key Differences from Legacy Implementation

### Removed Components
- **ManagerHistory class**: Replaced by ManagerMemory
- **summary_level configuration**: Replaced by K-window mechanism
- **truncation parameters**: Completely removed for scientific integrity

### Enhanced Components  
- **Two-stage evaluation**: Single LLM context across evaluation and feedback
- **Memory summarization**: Automatic LLM-powered compression of overflow rounds
- **State persistence**: Three-dimensional state with explicit lifecycle management
- **Error resilience**: Retry mechanisms with format guidance

## Current Status
- **Implementation**: Complete and functional
- **Integration**: Fully integrated with main.py experiment flow
- **Testing**: Verified with scientific coding standards compliance
- **Memory**: K-window=3 default, configurable per experiment