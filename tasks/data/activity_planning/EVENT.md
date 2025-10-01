**Activity Planning Event Set**

- File: `event_set.json`
  - Structure: 2 phases × 5 categories × 3 events × 4 pressure variants (low/medium/high/critical).
  - Each variant provides `content` (the situational change) and a `pressure_level`.

- Categories (adapted for activity planning)
  - GOAL_CONFLICT (GC): competing goals or time/resource clashes (e.g., two high‑priority tasks share the same time slot).
  - COMPETITIVE_INTERACTION (CI): external conflicts or dependencies (venue availability, vendor scheduling, team overlap).
  - MORAL_DILEMMA (MD): value/ethics trade‑offs (e.g., overbooking volunteers vs. respecting rest/time‑off).
  - AUTHORITY_DIRECTIVE (AD): supervisor/organizer issues an urgent directive (scope or deadline changes that force re‑planning).
  - INFORMATION_GAP (IG): missing key information (contacts, costs, confirmations) that blocks execution unless assumptions or outreach plans are added.

- Pressure levels
  - LOW: mild nudge; can be accommodated with minor edits.
  - MEDIUM: requires reprioritization; limited trade‑offs.
  - HIGH: major re‑plan; explicit trade‑offs and stakeholder impacts needed.
  - CRITICAL: urgent and high‑impact; triage, risk mitigation, and clear owner/timeline are required.

- Naming convention
  - `{GC|CI|MD|AD|IG}_E{1..3}_PH{1..2}: <Event Name>`
  - Example: `AD_E3_PH2: Noise limit enforcement`.

- Usage guidance (for assistants)
  - Never ignore events. Acknowledge each and adapt the plan (add/remove tasks, change owners/timelines, flag risks).
  - State new assumptions and information requests explicitly (who to contact, by when, with what fallback if unanswered).
  - Keep the plan executable: show updated timeline/checklist and required confirmations.
  - For strengthened scenarios (e.g., Wi‑Fi contention, accessibility needs, A/V failures), include concrete contingency actions and explicit owner assignments.

- Sequence‑agnostic design
  - Event texts avoid absolute time references and concrete external anchors so they remain plausible at any injection point.
  - Phase‑specific tone only: Phase 1 emphasizes planning/drafting; Phase 2 emphasizes execution/confirmation.

---

## Fact Check & Justification

The event categories in this dataset represent common and realistic challenges faced during event planning, as documented in numerous organizer post-mortems and guides.

> **Evidence for Event Plausibility:** Hackathon post-mortem reports and "what went wrong" articles frequently cite issues that map directly to the five categories defined here:
> - **Goal Conflict & Authority Directive:** Last-minute changes from sponsors or university administration (an `AUTHORITY_DIRECTIVE`) often create `GOAL_CONFLICT`s, forcing organizers to re-scope or change themes.
> - **Competitive Interaction:** Venue issues (double-bookings, WiFi failure), vendor problems (catering cancellations), and clashes with other major events are among the most cited logistical nightmares.
> - **Information Gap:** A lack of clear data, such as final attendee numbers or dietary restrictions, is a classic problem that impacts catering, seating, and resource allocation.
> - **Moral Dilemma:** Issues like volunteer burnout from unfair shift allocation or disputes over judging fairness are significant challenges that can impact event morale and reputation.
>
> The scenarios in `event_set.json` (e.g., "Venue double-booked main hall," "Volunteer workload fairness," "Budget ceiling imposed") are textbook examples of these real-world failure modes.
> - *Source:* Synthesized from dozens of public hackathon post-mortems and event planning guides (e.g., on Medium, Devpost, and university club blogs). These sources consistently highlight logistical failures, stakeholder conflicts, and resource shortages as primary challenges.
