## Manager 机制学术支持（按论文组织）

仅列出“论文如何具体支持我们的实现”，不讨论设计哲学。

### Reflexion: Language Agents with Verbal Reinforcement Learning (Shinn et al., 2023) — `https://arxiv.org/abs/2303.11366`
- 支持点：两阶段“评估→反馈”的语言反思循环；反思写入情景记忆缓冲区；无需参数更新。
- 对应：我们每轮先做评估推理、更新内部状态，再基于评估推理生成反馈，复用同一轮的LLM上下文。

### MemoryBank: Enhancing Large Language Models with Long-Term Memory (Zhong et al., 2023) — `https://arxiv.org/abs/2305.10250`
- 支持点：长期记忆通过“条目级独立摘要 + 更新/遗忘”维护；短期窗口内保留细节，远期以压缩表征保留可用性。
- 对应：K-window保留最近K轮完整交互；溢出时对最早一轮做“单轮独立摘要”并移入长期摘要列表；评估期组合“近期原始JSON + 早期摘要”。

### Generative Agents: Interactive Simulacra of Human Behavior (Park et al., 2023) — `https://arxiv.org/abs/2304.03442`
- 支持点：内部记忆/反思驱动行为，但不直接暴露；记忆检索遵循重要性/新近性/相关性。
- 对应：内部状态变量不对外，只输出反馈；内存上下文只在Manager私域使用。

### Augmenting Language Models with Long-Term Memory (LongMem) (Wang et al., 2023) — `https://arxiv.org/abs/2306.07174`
- 支持点：短期上下文与长期记忆解耦，通过检索/压缩组合使用以降低上下文负担。
- 对应：我们将“最近K轮原文 + 更早摘要”在评估时合并使用，保持可达性并防溢出。

### Self-Refine: Iterative Refinement with Feedback (Shinn et al., 2023) — `https://arxiv.org/abs/2303.17651`
- 支持点：利用迭代反馈进行自我修正，提升结构化输出的一致性。
- 对应：评估与反馈均由解析器强制格式；失败时追加格式提醒并重试（最多3次）。

### RecallM: An Adaptable Memory Mechanism with Temporal Understanding (Kynoch et al., 2023) — `https://arxiv.org/abs/2307.02738`
- 支持点：带时间理解的可适应记忆更新；强调记忆随着交互演化。
- 对应：我们对溢出轮做摘要并追加到长期记忆，保持跨轮时间线索。

### LaMemo: Language Modeling with Look-Ahead Memory (Ji et al., 2022) — `https://arxiv.org/abs/2204.07341`
- 支持点：前瞻记忆与当前上下文的动态交互，提升长文本一致性。
- 对应：近期原文与早期摘要共同参与评估推理，提供“当下 + 远期压缩”的联合上下文。

### Enhancing Large Language Model with Self-Controlled Memory Framework (Wang et al., 2023) — `https://arxiv.org/abs/2304.13343`
- 支持点：记忆流与记忆控制器决定何时/如何读写与利用记忆。
- 对应：Manager决定何时生成摘要、如何把记忆注入评估，而不直接暴露给工作LLM。

### MemLong: Memory-Augmented Retrieval for Long-Text Modeling (2024, method family)
- 参考：技术评述 `https://www.51cto.com/aigc/2126.html`
- 支持点：外部检索 + 可控注意力，提升长上下文处理能力。
- 对应：我们在评估期同时检索“近期原文 + 远期摘要”，等价于在短/长记忆层进行信息聚合。

### Relational Recurrent Neural Networks (Santoro et al., 2018) — `https://arxiv.org/abs/1806.01822`
- 支持点：关系记忆核心（RMC）展示显式记忆模块可增强长期依赖与关系推理。
- 对应：从理论上支持“显式记忆结构 + 读取/写入策略”能稳定长期信息利用。

### Learning to Remember More with Less Memorization (Rae et al., 2019) — `https://arxiv.org/abs/1901.01347`
- 支持点：统一写入/减少冗余的思想，强调选择性持久化关键内容。
- 对应：我们以摘要形式压缩并只保留关键信息，减少冗余上下文。

### MemOS: A Memory OS for AI System（立场/综述类资料）
- 参考：`https://cloud.tencent.com/developer/article/2540464`
- 支持点：把记忆视为可治理的系统资源（生命周期、权限、结构抽象）。
- 对应：与我们“短期窗口 + 长期摘要 + 私域使用”的治理思路一致。

### From Human Memory to AI Memory: A Survey（综述）
- 参考：`https://www.themoonlight.io/zh/review/from-human-memory-to-ai-memory-a-survey-on-memory-mechanisms-in-the-era-of-llms`
- 支持点：对AI记忆的分类与实践汇总，背书K-window与摘要压缩是主流路线之一。
- 对应：为我们的K-window + 摘要提供综述层面的背景支持。

### Structured Memory Mechanisms for Stable Context Representation（评述）
- 参考：`https://www.themoonlight.io/zh/review/structured-memory-mechanisms-for-stable-context-representation-in-large-language-models`
- 支持点：显式记忆单元、门控写入、基于注意力的读取等结构化机制。
- 对应：与我们的“显式持久摘要 + 读取时组合”一致。

### MemEngine: A Unified and Modular Memory Library（工程评述）
- 参考：`https://www.themoonlight.io/zh/review/memengine-a-unified-and-modular-library-for-developing-advanced-memory-of-llm-based-agents`
- 支持点：模块化记忆操作（写入/更新/检索）的工程化总结。
- 对应：从工程角度背书我们把“生成摘要/读取记忆/组合上下文”拆分为清晰步骤。




