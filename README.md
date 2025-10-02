# Simulating and Understanding Deceptive Behaviors in Long-Horizon Interactions

<p align="center">
  <a href="https://github.com/yourusername/deception-long-horizon">
    <img src="https://img.shields.io/badge/Code-Open%20Source-green.svg" alt="Open Source">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Paper-Preprint-orange.svg" alt="Paper">
  </a>
</p>

**The first simulation framework for probing and evaluating deception in LLMs under extended sequences of interdependent tasks and dynamic contextual pressures.**


Deception is a pervasive feature of human communication and an emerging concern in large language models (LLMs). While recent studies document instances of LLM deception under pressure, most evaluations remain confined to single-turn prompts and fail to capture the long-horizon interactions in which deceptive strategies typically unfold. We introduce the first simulation framework for probing and evaluating deception in LLMs under extended sequences of interdependent tasks and dynamic contextual pressures. Our framework instantiates a multi-agent system: a **performer agent** tasked with completing tasks and a **supervisor agent** that evaluates progress, provides feedback, and maintains evolving states of trust. An independent **deception auditor** then reviews full trajectories to identify when and how deception occurs.

![RESULTS](assets/pipeline.png)


## Methodology

Our framework simulates long-horizon interactions to probe whether LLMs adopt deceptive strategies under extended sequences of interdependent tasks and dynamic contextual pressures. We structure interactions as a multi-agent system where a **performer agent** completes tasks while a **supervisor agent** evaluates progress, provides feedback, and tracks longitudinal states of the collaboration.

### Simulating Long-Horizon Interactions

**Task Stream.** We formalize a sequential task stream $\mathcal{T} = (T_1, T_2, \dots, T_n)$ forming the temporal backbone of the interaction. Tasks are continuous and interdependent, forcing the performer to build on earlier outputs. We provide two domain instantiations with 14 tasks each:

**Startup Consulting**:
- Phase 1 — Discovery & Validation (Tasks 1-7)
- Phase 2 — Strategy & Launch (Tasks 8-14)

**Activity Planning**:
- Phase 1 — Laying the Groundwork (Tasks 1-7)
- Phase 2 — Bringing the Plan to Life (Tasks 8-14)

**Event System.** We augment the task stream with a probabilistic event system $\mathcal{E}$ that inserts contextually relevant disruptions aligned with the current project phase. Events are designed based on social science literature identifying sources of pressure that shape strategic and potentially deceptive behavior:

1. **Goal Conflict**: Objectives cannot be jointly satisfied
2. **Competitive Interaction**: Rivalry dynamics affecting incentives
3. **Moral Dilemma**: Trade-offs between ethical values and instrumental gains
4. **Authority Directive**: Top-down control from higher-status actors
5. **Information Gap**: Missing, asymmetric, or incomplete knowledge

Each category has four pressure levels $\Lambda=\{\text{low},\text{medium},\text{high},\text{critical}\}$ controlling stakes, urgency, and scrutiny. Events are sampled uniformly to avoid experimenter bias.

![TASK_EVENT](assets/task_event.png)

### Supervisor Agent

The supervisor oversees the performer's work and regulates task progression through structured feedback. For each task, multiple interaction rounds are allowed (up to $R_{\max}$). The supervisor maintains an internal state vector updated after each attempt:

- $s^{\text{trust}}$: Perceived integrity and reliability of the performer
- $s^{\text{satisfaction}}$: Task-focused quality assessment
- $s^{\text{comfort}}$: Relational comfort level in the collaboration

**Hybrid Memory System.** Recent $K$ interactions stored verbatim, earlier exchanges compressed into summaries. Artifacts from the task stream (e.g., documents, .txt or .json files) are also preserved. This enables evaluation of both local performance and global coherence across tasks.

**Two-Stage Process.** For each attempt, the supervisor (1) generates internal reasoning to update states, and (2) formulates explicit feedback combining evaluative commentary with actionable guidance.

### Deception Auditor

The auditor provides post-hoc assessment after all interactions to capture deception only evident across extended trajectories. For each interaction step, it receives the current interaction slice and the complete trajectory, evaluating longitudinal coherence.

**Structured Annotations**:
- **Deception Flag**: Binary detection indicator
- **Deception Type**(following Interpersonal Deception Theory): Falsification (fabricating information), Concealment (withholding information), Equivocation (obscuring/evading responses)
- **Severity**: Ordinal 0-4 scale reflecting magnitude and deliberateness
- **Reasoning & Evidence**: Natural language justification with explicit references to interaction history

## 🧪 Experimental Results

On startup consulting domain, we evaluate 11 frontier models across 20 independent trials each, including both closed-source (GPT-4o, GPT-o3, o4-mini, Gemini 2.5 Pro, Claude Sonnet 4, Grok 4) and open-source systems (GPT-OSS-120B, Qwen3, DeepSeek V3/V3.1/R1).

![TABLE](assets/table.png)
![TYPE](assets/type.png)
![CORRELATION](assets/correlation.png)

**Key Findings**:
- Deception is model-dependent: Claude Sonnet-4 shows sporadic deception (21.4%) while DeepSeek V3-0324 exhibits persistent deceptive strategies (79.3%)
- **Falsification dominates**: Across all models, falsification (fabricating information) is the primary strategy, though models differ in diversification into concealment and equivocation
- **Deception erodes trust, satisfaction, and relational comfort**: Strong anti-correlation between deception rate and supervisor trust, satisfaction, and relational comfort

### Control Studies

**Event Category Impact**: Falsification remains dominant across all five event categories. Information Gap events show increased shares of concealment and equivocation compared to other categories.

**Pressure Level Impact**: For deepseek v3.1, deception rates rise steadily from low to high pressure. Interestingly, GPT-4o shows a drop at critical pressure, where it tends to respond with explicit safety-aware statements.

![CONTROL](assets/control.png)

## Installation

### Prerequisites
- Python 3.12+
- Virtual environment (conda/venv recommended)
- API keys for Azure OpenAI and/or OpenRouter

### Setup

```bash
# Clone the repository
git clone https://github.com/Superposition09m/deception-long-horizon.git
cd deception-long-horizon

# Create and activate virtual environment
conda create -n deception python=3.12
conda activate deception

# Install dependencies
pip install -r requirements.txt
```

### API Configuration

Create a `.env` file in the project root:

```bash
# Azure OpenAI models
gpt_5_key=your_gpt_5_key_here
...

# OpenRouter
OPENROUTER=your_openrouter_key_here
```

## Running the Project

### Basic Usage

```bash
# Run with your own configuration
python main.py --config your_config_file.yaml

# Run detector with Result Dir
python core/deception_auditor.py --result_name SESSION_DIR_NAME --max_parallel 10

# Run Analyzer with visualization of supervisor state evolution, etc.
python analyzer.py --result_name SESSION_DIR_NAME

# HTML viewer with summaries
python visualization/summarizer.py --run SESSION_DIR_NAME --workers 5

# HTML viewer with chat-style static HTML file
python visualization/chat_dialog_viewer.py --run SESSION_DIR_NAME --detector SESSION_DIR_NAME/detector_<timestamp>.json
#or without summaries
python visualization/chat_dialog_viewer.py --run SESSION_DIR_NAME --detector SESSION_DIR_NAME/detector_<timestamp>.json --no-summary
```

### Configuration

Key parameters in `configs/*.yaml`:

```yaml
task_load_folder_name: "startup_consulting"  # Task set name
p_event: 0.5                                 # Event triggering probability
max_rounds_per_task: 3                       # Maximum interaction rounds per task
memory_k_window: 7                           # Recent rounds kept in full detail
task_completion_threshold: 0.2               # Threshold for task completion

# Model selection (references to api_profiles.yaml)
llm_api_config:
  llm: "gpt4o1120azurenew"          # Performer agent
  manager: "gpt5_mini"              # Supervisor agent
  detector: "gpt5_azure_detector"   # Deception auditor(fixed to GPT-5-high-reasoning-effort)
```

## Citation

If you use this framework in your research, please cite:

```bibtex
@misc{xu2025simulating,
  title={Simulating and Understanding Deceptive Behaviors in Long-Horizon Interactions},
  author={Xu, Yang and Zhang, Xuanming and Yeh, Min-Hsuan and Dhamala, Jwala and Dia, Ousmane and Gupta, Rahul and Li, Yixuan},
  year={2025},
  howpublished={\url{https://github.com/yourusername/deception-long-horizon}}
}
```
