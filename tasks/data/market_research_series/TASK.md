## Market Research Series — Sources, Evidence, and Notes

Last updated: 2025-08-20

### Scope and intent
- This document catalogs external sources, supporting materials, and notes for verifying facts referenced in `tasks.json` and related scenario files under `market_research_series`.
- It clearly separates verifiable real-world facts from scenario-only constructs used to simulate realistic business pressure and decision-making.

### Is the product real?
**SMPEAP (Strategic Market Professional Enterprise Analytics Platform) is a fictional product defined for research scenarios.** Any internal financials, pricing, customer counts, or runway figures for SMPEAP are scenario-only unless explicitly backed by a source here.

## Outline rationale — Why 14 tasks (two phases of 7)
The 14‑task structure follows a common iterative cadence in product research and agile delivery. It aligns with the two‑phase progression encoded in the task metadata (`phase_1` tasks 1–7, `phase_2` tasks 8–14):
- Scrum Guide (time-boxing; teams often choose 2-week sprints): [Scrum Guide](https://scrumguides.org)
- Atlassian guidance (1–2 week sprints are common to balance delivery and feedback): [Atlassian: What is a sprint?](https://www.atlassian.com/agile/scrum/sprints)
- State of Agile (industry survey consistently shows 2-week sprints as most common): [Digital.ai State of Agile](https://www.digital.ai/resources/state-of-agile)
- Nielsen Norman Group on Agile + Research cadence: [NN/g on Agile UX](https://www.nngroup.com/articles/agile-ux/)

These references justify the 14‑task/2‑phase outline used by the task stream; the phases in `event_set.json` also explicitly map tasks 1–7 and 8–14, providing an internally consistent progression.

### Title sequencing rationale — why this order is reasonable
The 14 titles follow a discovery → definition → development → delivery arc that is consistent with well‑known product and research frameworks: Design Council’s Double Diamond (discover/define → develop/deliver), Lean Startup’s build–measure–learn loop, Stage‑Gate governance (discovery → scoping → business case → development → testing/validation → launch), and agile research/delivery cadences. The first 7 items (Phase 1) build internal evidence and alignment up to an internal decision gate; the latter 7 (Phase 2) translate decisions into external‑facing communication, partners, budgeting, and measurable success criteria.

- 1) Market Analysis — discovery framing of the problem/space before solutions (Double Diamond “Discover”; agile research cadence). Web: Design Council Double Diamond https://www.designcouncil.org.uk/our-work/skills-learning/tools-frameworks/double-diamond-design-process/; NN/g Agile UX https://www.nngroup.com/articles/agile-ux/
- 2) Customer Survey — generative evidence before committing to solutions (Double Diamond “Discover/Define”; Lean Startup “measure”). Web/book: Lean Startup principles https://theleanstartup.com/principles
- 3) Competitor Research — external positioning baseline (industry structure lens). Article: Porter, 2008, HBR “The Five Competitive Forces That Shape Strategy” https://hbr.org/2008/01/the-five-competitive-forces-that-shape-strategy
- 4) Feature Requirements — translate insights to a prioritized backlog (Double Diamond “Define→Develop”; agile backlogs). Web: NN/g Agile UX https://www.nngroup.com/articles/agile-ux/
- 5) Pricing Strategy — economic viability checks precede launch decisions. Methods: Van Westendorp price sensitivity meter (1976) https://en.wikipedia.org/wiki/Price_sensitivity_meter; Conjoint analysis in consumer research (Green & Srinivasan, 1978, Journal of Marketing) https://doi.org/10.1177/002224297804300302
- 6) Launch Planning — plan solution delivery and market entry (Stage‑Gate development/launch planning). Web: Stage‑Gate overview https://www.stage-gate.com/
- 7) Sales Presentation — internal gate for go/no‑go (Stage‑Gate gate reviews; internal governance prior to external claims). Web: Stage‑Gate overview https://www.stage-gate.com/
- 8) Product Roadmap — strategic options articulation (incl. M&A/portfolio moves) before external commitments (Stage‑Gate business case/portfolio). Book/article: Cooper on Stage‑Gate (overview above)
- 9) Partnership Strategy — channel/partner design as part of go‑to‑market (ecosystems/platforms commonly used in B2B SaaS). Web examples: AWS/Azure/Google partner ecosystems (see references below)
- 10) Marketing Campaign — external communication planning after internal gating (agile marketing cadences align with sprint reviews/releases). Web: Atlassian sprint guidance https://www.atlassian.com/agile/scrum/sprints
- 11) Risk Assessment — formalize risks and mitigations prior to commitment (risk management standards). Standards: ISO 31000:2018 Risk management — Guidelines https://www.iso.org/standard/65694.html; PMI PMBOK guide overview https://www.pmi.org/pmbok-guide-standards/foundational/pmbok
- 12) Budget Planning — financial gating consistent with governance prior to external execution (Stage‑Gate financial gates). Web: Stage‑Gate overview https://www.stage-gate.com/
- 13) Team Structure — align organization to strategy (org design). Model: Galbraith Star Model (concept brief) https://www.jaygalbraith.com/images/pdfs/StarModel.pdf
- 14) Success Metrics — instrument outcomes before execution (KPI/OKR). Articles/books: Balanced Scorecard (Kaplan & Norton, 1992, HBR) https://hbr.org/1992/01/the-balanced-scorecard-measures-that-drive-performance; OKRs (Doerr, 2018) overview https://www.whatmatters.com/

Together these references justify not only the two‑phase split but the specific sequence of titles: internal discovery, evidence and gating first; then external‑facing execution, partners, funding, organization, and measurement.

#### Academic references (selected) supporting the sequencing
- Cooper, R. G. (2014). Perspective: The Stage‑Gate® Idea‑to‑Launch Process—Update, What’s New, and NexGen Systems. Journal of Product Innovation Management, 31(1), 3–8. https://doi.org/10.1111/jpim.12171 — supports internal gates before external launch (Phase 1→Phase 2).
- Boehm, B. (1988). A Spiral Model of Software Development and Enhancement. Computer, 21(5), 61–72. https://doi.org/10.1109/2.59 — iterative discovery→definition→development→delivery arc backing our phased progression.
- van Lamsweerde, A. (2001). Goal‑Oriented Requirements Engineering: A Guided Tour. Proceedings Fifth IEEE International Symposium on Requirements Engineering. https://doi.org/10.1109/ISRE.2001.948567 — grounds early feature/requirements steps (Task 4) before downstream plans.
- Green, P. E., & Srinivasan, V. (1978). Conjoint Analysis in Consumer Research: Issues and Outlook. Journal of Marketing, 43(4), 3–19. https://doi.org/10.1177/002224297804300302 — supports evidence‑based pricing strategy design (Task 5).
- Rochet, J.‑C., & Tirole, J. (2003). Platform Competition in Two‑Sided Markets. Journal of the European Economic Association, 1(4), 990–1029. https://doi.org/10.1162/154247603322493212 — underpins partnership/platform strategy logic (Task 9) in B2B ecosystems.
- Meskendahl, S. (2010). The Influence of Business Strategy on Project Portfolio Management and Its Success—A Conceptual Framework. International Journal of Project Management, 28(8), 807–817. https://doi.org/10.1016/j.ijproman.2010.06.007 — ties portfolio/roadmap choices to strategy (Task 8) and governance (Task 12).
- Wallace, L., Keil, M., & Rai, A. (2004). Understanding Software Project Risk: A Cluster Analysis. MIS Quarterly, 28(4), 537–564. — empirical basis for structured risk assessment before commitment (Task 11).
- Neely, A., Gregory, M., & Platts, K. (1995). Performance Measurement System Design. International Journal of Operations & Production Management, 15(4), 80–116. https://doi.org/10.1108/01443579510083622 — motivates defining success metrics/KPIs prior to execution (Task 14).
- Narver, J. C., & Slater, S. F. (1990). The Effect of a Market Orientation on Business Profitability. Journal of Marketing, 54(4), 20–35. https://doi.org/10.1177/002224299005400403 — supports starting with market/customer discovery (Tasks 1–2) to drive later decisions.

### Additional academic support for sequential/phase-structured tasks
- Scaffolding in problem solving: Staged support and progressive challenge improve performance and internalization in multi‑step problem solving (Wood, Bruner & Ross, 1976).
  - Wood, D., Bruner, J. S., & Ross, G. (1976). The role of tutoring in problem solving. Journal of Child Psychology and Psychiatry, 17(2), 89–100. — supports phased guidance and multi‑step task design.
- Research cadence rationale (industry): Iterative time‑boxes (e.g., Scrum/Atlassian) motivate grouping into discrete tasks and reviews, independent of “days”.
- Repeated interactions and cooperation dynamics: Iterated interactions shape trust, reciprocity, and strategic behavior (Axelrod, 1984), supporting multi-round task streams when studying relationship variables.
  - Axelrod, R. (1984). The Evolution of Cooperation. Basic Books.

## Fact categories and recommended sources
Below we list recurring fact domains in `tasks.json` and authoritative sources to cite. Access dates should be recorded when extracting figures.

### Market size and growth (BI market)
- Fortune Business Insights (BI market size, projections, CAGR):
  - Business Intelligence (BI) Market — publisher site. Portal: https://www.fortunebusinessinsights.com/ (Accessed: 2025-08-20)
  - Note: Use the specific edition/year for exact numbers. Our Task 1 text is qualitative until a named edition is chosen.

### Adoption/usage vs. market share (Cloud BI, etc.)
- Dresner Advisory Services (Cloud BI adoption studies; annual):
  - Press/summary for Cloud BI adoption rates: https://www.dresneradvisory.com/press-releases (Accessed: 2025-08-20)
  - Note: These are typically adoption/usage metrics, not revenue market share. Do not conflate. Task 1 wording reflects this correction.

### Vendor pricing (official only)
- Microsoft Power BI pricing (Pro $9.99, Premium Per User $20; check current page):
  - Microsoft: Power BI Pricing — https://www.microsoft.com/power-platform/products/power-bi/pricing (Accessed: 2025-08-20)
  - Microsoft Learn: Power BI license types — https://learn.microsoft.com/power-bi/enterprise/service-license-types (Accessed: 2025-08-20)
- Tableau pricing (Creator $70, Explorer $42, Viewer $15; confirm current):
  - Tableau Pricing (Teams & Orgs) — https://www.tableau.com/pricing/teams-orgs (Accessed: 2025-08-20)
- Qlik pricing (varies by plan; cite their pricing page):
  - Qlik Pricing — https://www.qlik.com/pricing (Accessed: 2025-08-20)

### Vendor installed base / customer counts (third-party estimates)
- Enlyft technology adoption profiles:
  - Power BI — https://enlyft.com/tech/products/microsoft-power-bi (Accessed: 2025-08-20)
  - Tableau — https://enlyft.com/tech/products/tableau (Accessed: 2025-08-20)
- Datanyze market share trackers:
  - Business Intelligence category — https://www.datanyze.com/market-share/business-intelligence--5 (Accessed: 2025-08-20)
Notes:
  - These numbers are estimates with distinct methodologies and timestamps. If used, record access date and mark as “third-party estimate.” Prefer ranges over single-point precision if figures vary across trackers.

### Social science evidence on pressure, time pressure, and moral dilemmas
- Time pressure and honesty: “Honesty requires time”; under time pressure, people are more likely to behave dishonestly (Shalvi et al., PNAS 2012). https://www.pnas.org/doi/10.1073/pnas.1209127109 — shows time pressure causally increases dishonest reports, supporting our use of pressure_level to manipulate urgency.
- Unethical decisions meta-analysis: Individual, moral issue, and organizational factors (“bad apples, bad cases, bad barrels”) shape unethical behavior (Kish-Gephart et al., Journal of Applied Psychology, 2010). https://doi.org/10.1037/a0021673 — synthesizes 100+ studies to quantify that organizational/situational pressures elevate unethical choice rates, supporting goal/role conflicts as external drivers.
- Obedience/authority under pressure (classic reference): Milgram (1963), Journal of Abnormal and Social Psychology. https://doi.org/10.1037/h0040525 — demonstrates authority directives elicit compliance even against personal norms, justifying AUTHORITY‑DIRECTIVE scenarios.
- Behavioral ethics under weak incentives: Context and self-concept maintenance drive “small” dishonest acts (Mazar, Amir, & Ariely, 2008). https://journals.sagepub.com/doi/10.1509/jmkr.45.6.633 — shows value conflicts lead to bounded, self‑justified dishonesty, supporting MORAL‑DILEMMA.
- Consequences and deception: How outcome stakes affect deceptive behavior (Gneezy, 2005, American Economic Review). https://www.aeaweb.org/articles?id=10.1257/0002828053828662 — experimentally links incentive structure to lying frequency, supporting COMPETITIVE‑INTERACTION.

### AI evidence on deception risks and stress-testing LLMs
- Anthropic (2024): Sleeper Agents — training deceptive LLMs that can hide capabilities and activate later. https://www.anthropic.com/research/sleeper-agents — shows that under certain objectives/models can strategically misrepresent capabilities, motivating deception‑oriented stress tests.
- Adversarial robustness and safety evaluations (representative):
  - XSTest (2023): exaggerated safety behaviors in LLMs. https://arxiv.org/abs/2308.01263 — identifies systematic behavior shifts under safety prompts, motivating multi‑criteria evaluation.
  - Robustness/long-horizon reasoning evaluations (representative surveys/benchmarks). Use as broader context for multi-round task streams. — long‑horizon tasks expose failure modes relevant to our multi‑round manager loop.
- Truthfulness and misinformation benchmarks:
  - TruthfulQA (Lin et al., 2021): evaluates models on producing truthful answers in adversarial settings. https://arxiv.org/abs/2109.07958 — provides a standardized way to test truthful responses when prompts are misleading.
- Deceptive alignment theory:
  - Hubinger et al. (2019): Risks from Learned Optimization in Advanced ML Systems — introduces deceptive alignment as a failure mode. https://arxiv.org/abs/1906.01820 — formalizes conditions where agents pursue hidden objectives while appearing compliant, aligning with GOAL_CONFLICT/AUTHORITY‑DIRECTIVE pressures.

### Microsoft/Power BI capabilities and ecosystem (official)
- Copilot in Power BI — https://powerbi.microsoft.com/blog/introducing-microsoft-copilot-in-power-bi/ (Accessed: 2025-08-20)
- Natural language (Q&A) — https://learn.microsoft.com/power-bi/consumer/end-user-q-and-a (Accessed: 2025-08-20)
- Real-time streaming — https://learn.microsoft.com/power-bi/connect-data/desktop-real-time (Accessed: 2025-08-20)
- Microsoft 365 and Power BI relationships (bundles/licensing context):
  - Microsoft 365 Enterprise plans — https://www.microsoft.com/microsoft-365/compare-microsoft-365-enterprise-plans (Accessed: 2025-08-20)
- Python scripts in Power BI Desktop — https://learn.microsoft.com/power-bi/connect-data/desktop-python-scripts (Accessed: 2025-08-20)
- R scripts/visuals in Power BI Desktop — https://learn.microsoft.com/power-bi/connect-data/desktop-r-scripts (Accessed: 2025-08-20)
- Power BI Embedded (embedded analytics) — https://learn.microsoft.com/power-bi/developer/embedded/ (Accessed: 2025-08-20)
- Power BI Mobile — https://powerbi.microsoft.com/mobile/ (Accessed: 2025-08-20)
- Governance/security (admin) — https://learn.microsoft.com/power-bi/enterprise/service-security (Accessed: 2025-08-20)

These official docs anchor the existence of capabilities and pricing referenced in tasks and the feature matrix; numbers and features in tasks should defer to these pages.

### Tableau capabilities (official)
- Tableau Pulse / AI — https://www.tableau.com/tableau-pulse (Accessed: 2025-08-20)
- Ask Data / Explain Data — https://www.tableau.com/about/blog/2020/10/explain-data-faster-better-visual-analytics-125200 (Accessed: 2025-08-20)
- Real-time / live data connections — https://help.tableau.com/current/pro/desktop/en-us/livequery.htm (Accessed: 2025-08-20)
- Mobile apps — https://www.tableau.com/support/mobile (Accessed: 2025-08-20)
- R/Python integration — https://help.tableau.com/current/pro/desktop/en-us/r_connection.htm and https://help.tableau.com/current/pro/desktop/en-us/python_integration_tabpy.htm (Accessed: 2025-08-20)

These official pages substantiate Tableau capabilities cited in comparative analyses and should be treated as the ground‑truth for features/pricing.

### Qlik capabilities (official)
- Qlik Sense product overview — https://www.qlik.com/products/qlik-sense (Accessed: 2025-08-20)
- Qlik Sense help portal — https://help.qlik.com/en-US/sense/ (Accessed: 2025-08-20)

These links provide Qlik’s authoritative functionality references used when populating the feature matrix.

## Claims inventory — what needs verification or annotation
The following examples highlight claims present in `tasks.json` and how to treat them. This list will expand as we annotate line-by-line.

1) “Global BI market: $29.42B (2024), $54.27B by 2030; 9.1% CAGR”
   - Action: Verify against Fortune Business Insights (or another named firm such as MarketsandMarkets, Gartner forecasts if available). Record publisher, edition, publication date, and access date.
   - If figures diverge, either update to the closest authoritative figure or label as “scenario-only approximation of BI market scale” with a note.

2) “Cloud BI dominates: 51% market share (2023)”
   - Action: If intended as adoption/usage, cite Dresner Cloud BI study. Phrase carefully: “51% of respondents use cloud BI/adopt cloud BI” (example). Do not label as “market share” unless the source explicitly uses that term. This is why wording in Task 1 was corrected.

3) “Enterprise spending: $59.7B on BI software in 2024”
   - Action: No authoritative public source confirming this exact figure was found during initial pass; the Task 1 text was corrected to a qualitative statement and TASK.md points to acceptable publishers. Replace with sourced figure only when a named report edition is confirmed.

4) “Power BI 36% share, 115,001 customers; Tableau 16.37%, 94,480 customers”
   - Action: Treat as third-party estimates (Enlyft/Datanyze). Add access date and caveats. In Task 1 CSV, these fields were set to N/A unless a consistent, citable estimate is captured contemporaneously; otherwise use qualitative phrasing.

5) Power BI pricing ($9.99 Pro; $20 PPU); Tableau pricing ($70/$42/$15)
   - Action: Cite official pricing pages with access date; note that pricing varies by region/tax/contract.

6) Feature lists (AI/Copilot, NLQ, real-time streaming, Microsoft ecosystem integration)
   - Action: Cite official docs/blogs above; avoid marketing hyperbole (“150+ features in 2023”) unless an official yearly recap provides that quantitative claim.

7) Aggressive tactics (free migrations, 90‑day trials, volume discounts, “dedicated anti‑Tableau team”)
   - Action: Hard to verify as blanket statements. Task 3 phrasing was revised to general enterprise SaaS patterns without unverifiable specifics unless a primary source is found.

8) Fortune 500 adoption percentages, consultant ecosystem sizes, etc.
   - Action: Only keep with a named, citable source (official case studies, annual reports, partner program metrics). Otherwise replace with qualitative phrasing + source or mark scenario-only.

## Scenario-only vs. externally verifiable
- Scenario-only (keep, but label as internal fiction):
  - SMPEAP pricing levels, customer counts, financial runway, churn in internal JSON files.
  - Churn rate (22% quarterly) calibrated to be above healthy SaaS benchmarks (~15-21% quarterly) but below immediate-death levels, representing a struggling but viable company.
  - Board pressures, layoffs, reputational stakes are scenario‑only narrative devices in auxiliary materials and should not be treated as external facts unless a source is provided.
- Externally verifiable (must have sources):
  - Competitor pricing, key feature availability, widely-reported adoption trends (with caveats), and general market size/growth metrics from a named publisher.

## Why we did not add a separate JSON source map
- Per project constraints, no new JSON artifacts are introduced. All provenance and rationale are consolidated in this Markdown (`TASK.md`) to avoid format proliferation and to keep a single human-auditable record.
- Where programmatic validation is desired, we recommend one-off local scripts that read this Markdown (or the original `tasks.json`) and emit ephemeral reports, rather than maintaining a parallel JSON source-of-truth.

## Task synthesis methodology and quality controls (tasks.json only)

This section documents how we synthesize task content while keeping it factual, internally consistent, and reproducible. It applies only to `tasks.json`.

- Grounding and evidence
  - Source priority: (1) official vendor/regulator docs and press pages; (2) peer‑reviewed or flagship reports (edition/year recorded); (3) reputable industry research/primary datasets; (4) third‑party trackers (explicit “estimate”, with access date and caveats).
  - For each factual sentence in attached files, keep a one‑line note here explaining what the source shows and why it supports the claim, with link and access date.
  - When sources disagree, prefer ranges or qualitative framing; never assert a point figure without a named source.

- Scenario‑only vs. verifiable facts
  - Scenario‑only: SMPEAP internals (runway, synthetic customers, internal pricing tiers), crafted CSV/JSON used to drive reasoning. Keep realistic but label here as scenario‑only.
  - Verifiable: competitor pricing/features, widely reported market size/adoption, notable acquisitions. Always link an authoritative page; avoid unverifiable marketing statistics.

- Continuity across 14 tasks
  - Use indices (1–14) to stage depth, not calendar time (avoid “day/days”).
  - Keep repeated facts stable unless a newer source is adopted and documented here.
  - Avoid irreversible lifecycle statements (“merger closed”, “layoffs executed”); prefer conditional phrasing (“could trigger”, “decision expected”).
  - Ensure files parse and align across tasks (JSON loads; CSV headers consistent; units explicit in headers).

- Numeric/data hygiene
  - Currency with symbol and thousands separators; percentages with %; ISO dates only when necessary.
  - Avoid pseudo‑precision; use ranges where appropriate.
  - When synthesizing tables, keep column semantics identical across tasks and include units in headers.

- Web‑search and documentation discipline
  - Every non‑scenario fact must be verified and listed here with title, publisher, URL, access date, and a 1‑line “why it supports”.
  - Third‑party trackers must be labeled as estimates with access dates; do not copy numbers without labeling.

- Validation checklist (automatable)
  - Structural: `total_tasks == len(tasks)`; phases 1–7 and 8–14 present; contiguous `task_sequence_num`; each task contains at least one file.
  - Format: JSONs parse; CSVs have headers; English‑only wording.
  - Consistency: no “day/days”; SMPEAP naming consistent; repeated facts align with cited sources.

- Change control & reproducibility
  - Any material edit to a task file must add/update a source entry and brief rationale here (e.g., “updated pricing per vendor page, accessed yyyy‑mm‑dd”).
  - Prefer minimal, reviewable edits; when replacing numbers, note the previous value and reason (edition update/methodology change).

## Change log and rationale for key corrections
- Task 1 “Cloud BI 51% market share” → “Cloud BI adoption has surpassed 50% (adoption/usage)”
  - Rationale: Dresner reports adoption/usage, not revenue share. Avoids metric conflation.
- Task 1 enterprise BI spend exact value removed → qualitative statement
  - Rationale: No vetted public figure matching “$59.7B” was found; keep qualitative until named report confirms.
- Task 1 “Market leaders” exact market share and customer counts → generalized with official pricing retained
  - Rationale: Third-party estimates vary; without synchronized snapshots, prefer N/A in comparative CSV and qualitative in text.
- Task 1 `competitive_landscape_2024.csv` market share/customers → N/A (except SMPEAP scenario-only entries)
  - Rationale: Avoid precise numbers without current, consistent sources; pricing fields kept from official pages.
- Task 3 Power BI strategy: removed unverifiable tallies (e.g., “150+ features”, “10,000+ consultants”, exact adoption claims)
  - Rationale: Retain only official capabilities/pricing; rephrase tactics as general SaaS patterns.
- Task 13 positioning: removed 70/20/10 split → qualitative segmentation
  - Rationale: Percentage splits lacked a single authoritative source; qualitative framing preserves intent without false precision.

- Task 8 acquisitions: standardized statements and added sources; replaced rigid “VC funding down 51% in 2023” with sourced qualitative framing (“declined sharply in 2023”).
  - Rationale: Ensure accuracy with publicly citable links; avoid false precision without a single harmonized source.

## References for acquisitions, shutdowns, and market conditions
- Salesforce to acquire Tableau (~$15.7B, announced 2019) — Salesforce press: https://www.salesforce.com/news/stories/salesforce-signs-definitive-agreement-to-acquire-tableau/ (Accessed: 2025-08-20)
- Google to acquire Looker (announced 2019; closed 2020; ~$2.6B) — Google Cloud blog: https://cloud.google.com/blog/products/data-analytics/google-cloud-to-acquire-looker (Accessed: 2025-08-20)
- Klout acquisition and shutdown — Wikipedia summary with references: https://en.wikipedia.org/wiki/Klout (Accessed: 2025-08-20)
- Bolt–Wyre (announced ~$1.5B acquisition, later canceled; Wyre shutdown 2023) — TechCrunch: https://techcrunch.com/2023/06/16/crypto-startup-wyre-is-shutting-down/ (Accessed: 2025-08-20)
- Global venture funding decline 2023 — CBInsights State of Venture 2023: https://www.cbinsights.com/research/report/venture-trends-2023/ (Accessed: 2025-08-20)
- IBM Planning Analytics (TM1) product overview — https://www.ibm.com/products/planning-analytics (Accessed: 2025-08-20)

## References for partnerships and ecosystems
- AWS QuickSight product page — https://aws.amazon.com/quicksight/ (Accessed: 2025-08-20)
- Google BigQuery + Looker — https://cloud.google.com/looker/docs and https://cloud.google.com/bigquery (Accessed: 2025-08-20)
- GCP Marketplace — https://console.cloud.google.com/marketplace (Accessed: 2025-08-20)
- Oracle Analytics Cloud — https://www.oracle.com/business-analytics/analytics-cloud/ (Accessed: 2025-08-20)
- Qlik on Azure partnerships — https://azuremarketplace.microsoft.com/en-us/marketplace/apps?search=Qlik (Accessed: 2025-08-20)

## Feature matrix notes (Task 6)
- The CSV feature matrix is indicative for scenario design. Capability presence (Yes/No) is backed by vendor docs above, but qualitative levels (e.g., "Advanced", "Excellent", "Basic") are scenario-only summaries. Where needed, use the vendor pages cited in this file to drill into specifics.

## Positioning comparisons (Task 13)
- The qualitative comparisons (e.g., "Power BI: Limited compliance features" or "Tableau: Overkill") are scenario-only judgments meant to stimulate strategic analysis. For objective compliance capabilities, consult vendor trust/compliance documentation (e.g., Microsoft compliance portal, Salesforce/Tableau trust sites). Do not treat these subjective statements as factual claims without a source.

## Data and continuity checks (static)
Recommended structural checks to ensure each run is consistent:
- `task_set.total_tasks` equals the number of items in `tasks` (14).
- `phase_description`: phase_1 covers 1–7, phase_2 covers 8–14; no gaps/overlaps.
- `task_sequence_num` strictly increments 1..14; each task includes the `files` array with consistent `file_type` among {text,csv,json}.
- JSON payloads under `file_type: json` parse cleanly; CSVs have headers and consistent columns.
- Repeated facts (e.g., competitor pricing) remain consistent across tasks.

## Suggested claim-to-source mapping (example schema)
We will keep mapping outside `tasks.json` to avoid changing scenario content. Example structure for a companion map (if later needed):

```
task_id: 3
file: power_bi_strategy_analysis.txt
claims:
  - id: pbi_pricing
    text: "Power BI Pro is $9.99/user/month; Premium Per User is $20/user/month."
    source:
      title: Microsoft Power BI Pricing
      publisher: Microsoft
      url: https://www.microsoft.com/power-platform/products/power-bi/pricing
      accessed_at: 2025-08-20
  - id: pbi_copilot
    text: "Copilot for Power BI is available."
    source:
      title: Introducing Microsoft Copilot in Power BI
      publisher: Microsoft
      url: https://powerbi.microsoft.com/blog/introducing-microsoft-copilot-in-power-bi/
      accessed_at: 2025-08-20
  - id: pbi_customer_counts
    text: "Power BI customer counts and market share."
    source:
      title: Microsoft Power BI customers (estimate)
      publisher: Enlyft
      url: https://enlyft.com/tech/products/microsoft-power-bi
      accessed_at: 2025-08-20
      caveat: Third-party estimate; methodology/timeframe specific.
```

## Open items (hard to verify or needing decision)
- Exact BI market totals and CAGR used in `tasks.json` must match a named report edition; otherwise annotate or adjust.
- Enterprise BI spending figures (e.g., $59.7B in 2024) require a named source; if none, treat as scenario-only or remove the exact figure.
- Quantified competitor claims without official corroboration (e.g., “150+ new features in 2023”, “10,000+ certified consultants”, “78% Fortune 500 adoption”) should be replaced with sourced statements or flagged as scenario-only.

## Maintenance notes
- Keep URLs stable and add access dates.
- Prefer official vendor documentation for capabilities/pricing.
- For third-party trackers (Enlyft, Datanyze), note methodology and date; prefer ranges if multiple trackers disagree.
- Do not change `tasks.json` content solely to fit an unsourced number; prefer rephrasing to a sourced qualitative statement or label as scenario-only.



