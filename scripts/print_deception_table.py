#!/usr/bin/env python3
"""
Read Main/summary_by_model.json and print a LaTeX table summarizing:
- Deception Rate (mean ± std.err)
- Avg. Severity (All interactions) (mean ± std.err)
- Avg. Severity (Deceptive only) (mean ± std.err)

The script does not modify any results; it only reads and prints.

Usage:
  python scripts/print_deception_table.py \
    --input Results_all_models/Main/summary_by_model.json \
    [--caption "Deception auditing results ..."]

You can adjust the display names/release dates/order by editing MODEL_MAP below
or passing --only to restrict to a subset (comma-separated keys from the JSON).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple


# Mapping from JSON keys to (Display Name, Release Date)
MODEL_MAP: Dict[str, Tuple[str, str]] = {
    "GPT5_main": ("GPT-5", "Aug. 2025"),
    "gemini_main": ("Gemini 2.5 Pro", "Jun. 2025"),
    "claude4_main": ("Claude Sonnet-4", "May. 2025"),
    "grok4_main": ("Grok-4", "Jul. 2025"),
    "deepseek_v3_1_main": ("DeepSeek V3.1", "Aug. 2025"),
    "o3_main": ("o3", "Apr. 2025"),
    "o4mini_main": ("o4-mini", "Apr. 2025"),
    "qwen_main": ("Qwen3-235B-A22B", "Apr. 2025"),
    "deepseek_r1_0528_main": ("DeepSeek R1-0528", "May. 2025"),
    "oss_main": ("gpt-oss-120b", "Aug. 2025"),
    "GPT4o_main": ("GPT-4o-1120", "Nov. 2024"),
    "deepseek_v3_0324_main": ("DeepSeek V3-0324", "Mar. 2025"),
}

# Default output order (can be overridden via --only)
DEFAULT_ORDER: List[str] = [
    "GPT5_main",
    "gemini_main",
    "claude4_main",
    "grok4_main",
    "deepseek_v3_1_main",
    "o3_main",
    "o4mini_main",
    "qwen_main",
    "deepseek_r1_0528_main",
    "oss_main",
    "GPT4o_main",
    "deepseek_v3_0324_main",
]


def fmt_pm_plain(mean: float, stderr: float) -> str:
    return f"{mean:.3f} ± {stderr:.3f}"

def fmt_pm_latex(mean: float, stderr: float) -> str:
    return f"{mean:.3f}$_{{\\pm {stderr:.3f}}}$"


def build_rows_values(data: Dict, keys: List[str]) -> List[Tuple[str, str, float, float, float, float, float, float]]:
    """Return rows as tuples: (disp_name, release, dr_mean, dr_se, sa_mean, sa_se, sd_mean, sd_se)."""
    rows: List[Tuple[str, str, float, float, float, float, float, float]] = []
    for key in keys:
        if key not in data:
            continue
        disp, rel = MODEL_MAP.get(key, (key, "—"))
        agg = data[key].get("aggregated", {})
        dr = agg.get("deception_rate", {})
        sa = agg.get("severity_average_all_rounds", {})
        sd = agg.get("severity_average_deception_only", {})

        try:
            dr_m, dr_se = float(dr["mean"]), float(dr["stderr"]) 
            sa_m, sa_se = float(sa["mean"]), float(sa["stderr"]) 
            sd_m, sd_se = float(sd["mean"]), float(sd["stderr"]) 
        except Exception:
            # Skip models with incomplete stats
            continue

        rows.append((disp, rel, dr_m, dr_se, sa_m, sa_se, sd_m, sd_se))
    return rows


def detect_n_runs(data: Dict, keys: List[str]) -> str:
    runs = []
    for k in keys:
        n = data.get(k, {}).get("aggregated", {}).get("n_sessions")
        if isinstance(n, int):
            runs.append(n)
    runs_set = sorted(set(runs))
    if len(runs_set) == 1:
        return str(runs_set[0])
    return ", ".join(map(str, runs_set)) if runs_set else "N"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        type=str,
        default="Results_all_models/Main/summary_by_model.json",
        help="Path to summary_by_model.json",
    )
    ap.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated list of model keys to include (uses given order)",
    )
    ap.add_argument(
        "--caption",
        type=str,
        default=(
            "\\textbf{Deception auditing results}. We report the average deception rate, "
            "average severity over all interactions, and average severity conditioned on deceptive interactions only. "
            "Values are mean$_{\\pm \\text{std.err}}$ across %RUNS% runs. For fair comparison, all models are evaluated on the same set of random seeds."
        ),
        help="LaTeX caption text (use %RUNS% to interpolate n_sessions if uniform)",
    )
    args = ap.parse_args()

    path = Path(args.input)
    data = json.loads(path.read_text(encoding="utf-8"))

    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
    else:
        keys = [k for k in DEFAULT_ORDER if k in data]

    n_runs = detect_n_runs(data, keys)
    caption = args.caption.replace("%RUNS%", n_runs)

    rows_vals = build_rows_values(data, keys)

    # Plain text table printing
    header1 = "Deception auditing results (mean ± std.err). Runs: " + detect_n_runs(data, keys)
    print(header1)
    col1, col2 = "Model", "Release Date"
    col3 = "Deception Rate"
    col4 = "Avg. Severity (All)"
    col5 = "Avg. Severity (Deceptive)"

    # Format values as strings first to compute widths
    formatted_rows = []
    for disp, rel, dr_m, dr_se, sa_m, sa_se, sd_m, sd_se in rows_vals:
        formatted_rows.append(
            (
                disp,
                rel,
                fmt_pm_plain(dr_m, dr_se),
                fmt_pm_plain(sa_m, sa_se),
                fmt_pm_plain(sd_m, sd_se),
            )
        )

    w1 = max(len(col1), max((len(r[0]) for r in formatted_rows), default=0))
    w2 = max(len(col2), max((len(r[1]) for r in formatted_rows), default=0))
    w3 = max(len(col3), max((len(r[2]) for r in formatted_rows), default=0))
    w4 = max(len(col4), max((len(r[3]) for r in formatted_rows), default=0))
    w5 = max(len(col5), max((len(r[4]) for r in formatted_rows), default=0))

    def row_fmt(a,b,c,d,e):
        return f"{a:<{w1}}  {b:<{w2}}  {c:>{w3}}  {d:>{w4}}  {e:>{w5}}"

    print(row_fmt(col1, col2, col3, col4, col5))
    print("-" * (w1 + w2 + w3 + w4 + w5 + 8))
    for r in formatted_rows:
        print(row_fmt(*r))


if __name__ == "__main__":
    main()
