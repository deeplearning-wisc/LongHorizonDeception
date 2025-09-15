
\subsection{Data Persistence and Reproducibility}

\textbf{Atomic Write Operations.} All experimental data uses atomic JSON serialization to prevent corruption during concurrent operations. Each session generates timestamped directories with complete interaction logs, configuration snapshots, and detector analyses.

\textbf{Configuration Management.} The system supports hierarchical YAML configuration with environment variable substitution. Configuration validation ensures all required parameters are specified before experiment execution, with automatic backup to result directories for reproducibility.

\textbf{Multi-Provider LLM Integration.} The Universal LLM Handler abstracts provider differences (Azure OpenAI, OpenRouter) while supporting model-specific parameters (reasoning\_effort, temperature, max\_tokens). Automatic continuation handles output truncation, while input truncation manages context length limits through middle-out sampling strategies.