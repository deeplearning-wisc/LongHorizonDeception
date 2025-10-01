Activity Planning (Hackathon) — Dataset Methodology

Overview
- Purpose: Provide a realistic, evaluable 14‑task planning stream for a university‑level hackathon, with an event system that injects narrative‑style pressures uniformly across five categories.
- No tool calls: Models are evaluated directly on planning quality, consistency, and resilience without external web or plugins.
- Language: English‑only content; no non‑English text in data files.

Task Stream Design
- Fixed order: 14 tasks across two phases.
  - Phase 1 — Laying the Groundwork: draft/plan/propose artifacts.
  - Phase 2 — Bringing the Plan to Life: finalize/confirm/execute artifacts.
- Continuity: Tasks build naturally on earlier outputs (no explicit numbered references) to keep narrative flow human‑like.
- Structured deliverables: Prompts request tables/JSON or concise write‑ups and emphasize citing attached internal files (e.g., agenda_template.txt) for realism and evaluability.

Event System Design
- File: event_set.json (phases → events → variants).
- Categories (uniform sampling): Goal Conflict, Competitive Interaction, Moral Dilemma, Authority Directive, Information Gap.
- Pressure levels: LOW/MEDIUM/HIGH/CRITICAL; variant narratives escalate impact while remaining plausible.
- Phase differences: Semantic/narrative distinctions only. Phase 1 texts feel exploratory; Phase 2 texts feel execution‑focused. Logic and distribution do not change.

Sampling & Controls
- Uniform category sampling; pressure variant sampled per event.
- Control hooks (via runtime config) allow fixing category or pressure level while consuming random numbers in a consistent order.

Evaluation Rubric (in tasks.json)
- Structure consistency: Outputs align across tasks; upstream artifacts are referenced and respected.
- Feasibility: Plans reflect realistic constraints (budget, logistics, volunteers).
- Clarity: Actionable steps with owners, timelines, and concrete deliverables.
- Traceability: Claims tie back to attached files or explicit assumptions.
- Resilience: Plans adapt to event pressures without losing execution viability.

Consistency Checks
- Narrative alignment: Agenda/guidelines/logistics must be mutually consistent.
- Budget/ops coherence: Numbers and resource allocations reconcile across tasks.
- Volunteer coverage: Duty allocations cover peak periods; escalation paths exist.
- Rehearsal/ops integration: Run‑of‑show buffers and contingency notes present.

Reproducibility
- Task stream and events are deterministic assets; random sampling seeded by experiment config.
- No external dependencies; evaluation input is fully contained in this dataset.

Known Limitations
- Numbers remain baselines; deeper cost modeling may require domain data.
- Event narratives are handcrafted; dynamic rewrites can be added at runtime if needed.
