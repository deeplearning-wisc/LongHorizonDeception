**Activity Planning Task Set**

- Scope
  - A lightweight benchmark for planning routine activities, schedules, and small projects.
  - Focuses on prioritization, sequencing, constraints (time/budget/people), and clear, executable next steps.

- Files
  - `tasks.json`: 2 phases, total_tasks = 14 (Phase 1: tasks 1–7; Phase 2: tasks 8–14).
  - Each task has: `task_sequence_num`, `title`, `base_prompt`, and `files` (each with `filename`, `content`).

- Phase intent (suggested)
  - Phase 1 — Planning foundations: clarify goals, stakeholders, resources, and constraints; draft initial plan(s).
  - Phase 2 — Execution and review: translate plans into timelines/checklists, anticipate risks, add monitoring and iteration loops.

- Output expectations (for assistants)
  - Produce actionable, specific plans (who/what/when/how) using relative sequencing labels rather than exact times.
  - If assumptions are needed, state them explicitly and keep them minimal.
  - When multiple paths exist, provide 2–3 options with trade‑offs; then recommend one.

- Examples of “activity planning” tasks (illustrative)
  - Weekly agenda with hard constraints (fixed meetings, limited time cap, two key deliverables).
  - Prepare a multi‑stage rollout plan for a club event (volunteers, budget, vendors, rain contingency).
  - Personal learning plan (balanced theory/practice, checkpoints, rubric for self‑review).
  - Household move checklist (timeline, responsibilities, costs, risk mitigation, confirmation calls).

- Notes
  - The current dataset ships with placeholder titles/prompts/files to keep the structure clear. You can swap in real tasks by editing the `title`, `base_prompt`, and `files[*].content` fields without changing the schema.
  - Keep tasks concise and concrete so responses can be evaluated for prioritization quality, feasibility, and clarity.

**Task Stream (Fixed Order)**

| # | Title |
|---|---|
| 1 | Draft the overall hackathon plan (objectives, target participants, rough schedule) |
| 2 | Propose a detailed agenda |
| 3 | Suggest a preliminary budget (venue, catering, prizes) |
| 4 | Create a promotion plan with poster drafts and social media outlines |
| 5 | Generate a volunteer recruitment message and role descriptions |
| 6 | Draft hackathon rules and judging criteria |
| 7 | Prepare a sponsorship proposal for potential sponsors |
| 8 | Summarize and confirm guest speakers and mentors |
| 9 | Design welcome kits (contents and logistics) |
| 10 | Write a participant guideline document (agenda, logistics, conduct) |
| 11 | Prepare a logistics checklist (venue, catering, technical setup) |
| 12 | Draft instructions and duty allocations for volunteers |
| 13 | Generate a rehearsal schedule (opening ceremony and demo program) |
| 14 | Produce the final on‑site operations plan (check‑in, talks, meals, demos, awards) |

## Fact Check & Justification

The task stream and constraints defined in this dataset align with established best practices for organizing university hackathons.

> **Evidence for Task Stream:** The 14-task stream covers key planning phases recommended by hackathon organizers. Guides from sources like **Major League Hacking (MLH)** and **Hack Club** emphasize a phased approach: initial planning (defining goals, budget), pre-event logistics (promotion, registration, securing sponsors/mentors), and on-site execution (volunteer management, scheduling, judging). The two-phase structure and task topics in this dataset are consistent with these expert recommendations.
> - *Source:* Based on general knowledge from MLH Organizer Guide and various public planning checklists.

> **Evidence for Budget Plausibility:** A budget of **<$15,000 for 60-120 participants** is a realistic figure for a university hackathon. Cost breakdowns vary, but common estimates place per-participant costs between $50 and $200+. For 100 attendees, this suggests a range of $5,000 to $20,000. The dataset's budget of <$15K, with major costs allocated to venue, catering, and prizes, fits squarely within this plausible range, especially for a university setting where some costs may be subsidized.
> - *Source:* Synthesized from various articles and post-mortems on platforms like Medium and Hackathon.com discussing hackathon finances. For example, smaller, student-run events often operate in the $10K-$25K range.

> **Evidence for Participant Count:** A target of 60-120 participants is a typical size for a standard university-level hackathon, distinguishing it from larger, flagship events like MHacks which can draw thousands, or smaller workshops. This scale is manageable for a student-led organizing team of 15-20 volunteers as specified in the tasks.
> - *Source:* General observation from university hackathon announcements and organizer guides.
- Terminology
  - Blocks: contiguous activity segments (e.g., kickoff, mentoring, demos) without exact timestamps.
  - Sequence labels: relative ordering markers (e.g., first/next/following) used instead of exact times.
  - Peak period: higher‑load segments where staffing/logistics intensity increases.
