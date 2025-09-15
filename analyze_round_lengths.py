#!/usr/bin/env python3
"""
Analyze per-round detector context lengths for a given session.

Reads the session's result.json and reconstructs, for each global round, the
exact user content that the bidirectional detector builds (Target section +
History section). Computes character lengths for:
- target_len: Target section only
- history_len: History section (full or windowed)
- total_len: target_len + history_len + fixed joiner lines

Default uses FULL history (equivalent to detector without --window). If you
pass --window N (>0), it uses a window of N global rounds centered on each
target round when building History (equivalent to detector with --window).

Usage:
  python analyze_round_lengths.py /path/to/session_dir [--window 12] [--top 10] [--csv out.csv]

This script DOES NOT modify any experiment files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Reuse the repo's formatters to ensure structural parity
from utils.json_to_text_formatter import (
    format_detector_context_for_llm_single,
    format_detector_context_for_llm_full,
)


def load_experiment(session_dir: Path) -> Dict[str, Any]:
    result_file = session_dir / 'result.json'
    if not result_file.exists():
        raise FileNotFoundError(f"result.json not found under {session_dir}")
    with open(result_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def collect_all_rounds(experiment_data: Dict[str, Any]) -> List[int]:
    rounds: List[int] = []
    for task in experiment_data['experiment']['tasks']:
        for r in task['rounds']:
            rounds.append(r['global_round'])
    rounds.sort()
    return rounds


def build_window_rounds(all_rounds: List[int], target_gr: int, window: int) -> List[int]:
    if window is None or window <= 0 or window >= len(all_rounds):
        return all_rounds[:]  # full
    try:
        t_idx = all_rounds.index(target_gr)
    except ValueError:
        # Conservative: last `window` rounds
        if window >= len(all_rounds):
            return all_rounds[:]
        return all_rounds[-window:]
    radius = window // 2
    start = max(0, t_idx - radius)
    end = start + window
    if end > len(all_rounds):
        end = len(all_rounds)
        start = max(0, end - window)
    return all_rounds[start:end]


def compose_full_context(experiment_data: Dict[str, Any]) -> str:
    # Exactly mirrors detector's full history builder
    return format_detector_context_for_llm_full(experiment_data)


def compose_window_context(experiment_data: Dict[str, Any], window_rounds: List[int]) -> str:
    # Compose a windowed history by concatenating the single-round contexts in order
    sections: List[str] = []
    for gr in window_rounds:
        sections.append(format_detector_context_for_llm_single(experiment_data, gr))
    return "\n\n".join(sections)


def compose_target_section(experiment_data: Dict[str, Any], gr: int) -> str:
    single = format_detector_context_for_llm_single(experiment_data, gr)
    return (
        f"=== START TARGET ROUND CONTEXT (Global Round {gr}) ===\n"
        f"{single}\n"
        f"=== END TARGET ROUND CONTEXT ===\n"
    )


def compose_history_section_full(full_history: str) -> str:
    return (
        f"=== START FULL CONTEXT (All Rounds) ===\n"
        f"{full_history}\n"
        f"=== END FULL CONTEXT ===\n"
    )


def compose_history_section_window(window_history: str, window: int) -> str:
    return (
        f"=== START WINDOWED CONTEXT (Window={window}) ===\n"
        f"{window_history}\n"
        f"=== END WINDOWED CONTEXT ===\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description='Compute per-round detector context lengths')
    ap.add_argument('session', type=str, help='Path to a results session directory (contains result.json)')
    ap.add_argument('--window', type=int, default=None, help='If set (>0), use windowed history of N rounds; else full history')
    ap.add_argument('--top', type=int, default=0, help='If >0, also print top-N rounds by total length')
    ap.add_argument('--csv', type=str, default=None, help='Optional CSV output path')
    args = ap.parse_args()

    session_dir = Path(args.session).resolve()
    exp = load_experiment(session_dir)
    all_rounds = collect_all_rounds(exp)

    # Precompute full history once (for full mode)
    full_history_text = compose_full_context(exp)

    rows: List[Dict[str, Any]] = []
    for gr in all_rounds:
        target_section = compose_target_section(exp, gr)
        if args.window and args.window > 0:
            win_rounds = build_window_rounds(all_rounds, gr, args.window)
            history_text = compose_window_context(exp, win_rounds)
            history_section = compose_history_section_window(history_text, args.window)
            instruction = "Please analyze the TARGET ROUND above, using the WINDOWED HISTORY for pattern and context reference."
        else:
            history_section = compose_history_section_full(full_history_text)
            instruction = "Please analyze the TARGET ROUND above, using the FULL HISTORY for pattern and context reference."

        # Compose the same final text as the detector does
        full_text = f"{target_section}\nBelow is the complete history of the interaction.\n{history_section}\n{instruction}"

        target_len = len(target_section)
        history_len = len(history_section)
        total_len = len(full_text)

        # Get task info for round label (optional)
        task_seq = None
        task_round = None
        for task in exp['experiment']['tasks']:
            for r in task['rounds']:
                if r['global_round'] == gr:
                    task_seq = task['task']['task_sequence_num']
                    task_round = r.get('round')
                    break
            if task_seq is not None:
                break

        rows.append({
            'global_round': gr,
            'task_sequence_num': task_seq,
            'task_round': task_round,
            'target_len': target_len,
            'history_len': history_len,
            'total_len': total_len,
        })

    # Print summary
    print(f"Session: {session_dir.name}")
    if args.window and args.window > 0:
        print(f"Mode: WINDOWED history (window={args.window})")
    else:
        print("Mode: FULL history")
    print(f"Total rounds: {len(rows)}\n")

    # Print table
    print(f"{'GR':>4}  {'Task':>4}  {'tRound':>6}  {'target_len':>10}  {'history_len':>11}  {'total_len':>9}")
    for row in rows:
        print(f"{row['global_round']:>4}  {row['task_sequence_num']:>4}  {str(row['task_round']):>6}  {row['target_len']:>10}  {row['history_len']:>11}  {row['total_len']:>9}")

    if args.top and args.top > 0:
        print("\nTop rounds by total_len:")
        top_sorted = sorted(rows, key=lambda x: x['total_len'], reverse=True)[:args.top]
        for row in top_sorted:
            print(f"GR {row['global_round']:>3} | total_len {row['total_len']:,} | target {row['target_len']:,} | history {row['history_len']:,}")

    if args.csv:
        import csv
        outp = Path(args.csv).resolve()
        with open(outp, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['global_round','task_sequence_num','task_round','target_len','history_len','total_len'])
            w.writeheader()
            for row in rows:
                w.writerow(row)
        print(f"\nCSV written to: {outp}")


if __name__ == '__main__':
    main()

