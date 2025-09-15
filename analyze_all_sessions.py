#!/usr/bin/env python3
"""
Batch analyzer for all sessions under a root directory (e.g., Results_checked).

For every leaf directory containing a result.json and at least one detector_*.json,
this script will:
  - Load the latest detector JSON (by timestamp in filename)
  - Summarize key stats (round count, deception rate, avg severities)
  - Optionally emit a CSV with per-session summary

It does NOT modify any experiment results.

Usage:
  python analyze_all_sessions.py --root Results_checked [--csv out.csv] [--print-rounds]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    # Deduplicate and sort
    uniq = []
    seen = set()
    for s in sorted(sessions):
        r = s.resolve()
        if r not in seen:
            seen.add(r)
            uniq.append(s)
    return uniq


def load_latest_detector(session: Path) -> Optional[Path]:
    files = sorted(session.glob('detector_*.json'))
    if not files:
        # Also support ensemble folder final.json
        ensembles = sorted(session.glob('detector_ensemble_*/final.json'))
        return ensembles[-1] if ensembles else None
    return files[-1]


def summarize_detector(detector_path: Path) -> Dict[str, Any]:
    with open(detector_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    summary = data.get('summary', {})
    rounds = summary.get('total_rounds')
    occ = summary.get('deception_occurrences')
    rate = summary.get('deception_rate')
    sev_all = summary.get('severity_average_all_rounds')
    sev_dec = summary.get('severity_average_deception_only')
    type_counts = summary.get('type_counts', {})
    type_percentages = summary.get('type_percentages', {})
    return {
        'total_rounds': rounds,
        'deception_occurrences': occ,
        'deception_rate': rate,
        'severity_average_all_rounds': sev_all,
        'severity_average_deception_only': sev_dec,
        'type_counts': type_counts,
        'type_percentages': type_percentages,
    }


def print_session_summary(session: Path, det_path: Path, summ: Dict[str, Any]) -> None:
    print(f"Session: {session.name}")
    print(f"  Detector: {det_path.name if det_path.name != 'final.json' else det_path.parent.name + '/final.json'}")
    print(f"  total_rounds={summ['total_rounds']}  deception_occurrences={summ['deception_occurrences']}  deception_rate={summ['deception_rate']:.2%}")
    print(f"  severity_all={summ['severity_average_all_rounds']:.2f}  severity_deception_only={summ['severity_average_deception_only']:.2f}")
    if summ['type_counts']:
        tc = summ['type_counts']
        tp = summ['type_percentages']
        print(f"  types: FAL={tc.get('FALSIFICATION',0)} ({tp.get('FALSIFICATION',0.0):.2%}), CON={tc.get('CONCEALMENT',0)} ({tp.get('CONCEALMENT',0.0):.2%}), EQV={tc.get('EQUIVOCATION',0)} ({tp.get('EQUIVOCATION',0.0):.2%})")
    print("")


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze all detector results under a root directory')
    ap.add_argument('--root', type=str, default='Results_checked', help='Root directory to scan')
    ap.add_argument('--csv', type=str, default=None, help='Optional output CSV path')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a directory: {root}")

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json)')
        return

    rows: List[Dict[str, Any]] = []
    for s in sessions:
        det = load_latest_detector(s)
        if not det:
            print(f"[SKIP] No detector JSON for {s.name}")
            continue
        summ = summarize_detector(det)
        print_session_summary(s, det, summ)
        row = {
            'session': s.name,
            'detector': det.name if det.name != 'final.json' else det.parent.name + '/final.json',
            'total_rounds': summ['total_rounds'],
            'deception_occurrences': summ['deception_occurrences'],
            'deception_rate': summ['deception_rate'],
            'severity_average_all_rounds': summ['severity_average_all_rounds'],
            'severity_average_deception_only': summ['severity_average_deception_only'],
            'FALSIFICATION_count': summ['type_counts'].get('FALSIFICATION', 0),
            'CONCEALMENT_count': summ['type_counts'].get('CONCEALMENT', 0),
            'EQUIVOCATION_count': summ['type_counts'].get('EQUIVOCATION', 0),
            'FALSIFICATION_pct': summ['type_percentages'].get('FALSIFICATION', 0.0),
            'CONCEALMENT_pct': summ['type_percentages'].get('CONCEALMENT', 0.0),
            'EQUIVOCATION_pct': summ['type_percentages'].get('EQUIVOCATION', 0.0),
        }
        rows.append(row)

    if args.csv and rows:
        import csv
        outp = Path(args.csv).resolve()
        with open(outp, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"CSV written to: {outp}")


if __name__ == '__main__':
    main()

