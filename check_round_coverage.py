#!/usr/bin/env python3
"""
Check per-round coverage for detector and analyzer across a results tree.

For each session (directory containing result.json), this tool reports:
- expected_rounds: all global_round values present in result.json (experiment data)
- detector_covered_rounds: union of rounds in all detector_*.json (and detector_ensemble_*/final.json)
- missing_in_detector: expected_rounds minus detector_covered_rounds
- analyzer_ran: whether any analysis_* folder exists
- missing_in_analyzer: equals expected_rounds if analyzer didn't run; otherwise same as missing_in_detector

This script is read-only. It does not modify any experiment files.

Usage:
  python check_round_coverage.py --root Results_checked [--csv coverage.csv]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    # Deduplicate + sort
    uniq: List[Path] = []
    seen = set()
    for s in sorted(sessions):
        rp = s.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(s)
    return uniq


def load_experiment_rounds(session: Path) -> List[int]:
    result_path = session / 'result.json'
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    rounds: List[int] = []
    for task in data.get('experiment', {}).get('tasks', []):
        for r in task.get('rounds', []):
            gr = r.get('global_round')
            if isinstance(gr, int):
                rounds.append(gr)
    rounds = sorted(set(rounds))
    return rounds


def collect_detector_rounds(session: Path) -> Set[int]:
    covered: Set[int] = set()
    # detector_*.json files
    for det_file in sorted(session.glob('detector_*.json')):
        try:
            with open(det_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for det in data.get('round_detections', []):
                gr = det.get('global_round')
                if isinstance(gr, int):
                    covered.add(gr)
        except Exception:
            continue
    # detector_ensemble_*/final.json (optional)
    for final in sorted(session.glob('detector_ensemble_*/final.json')):
        try:
            with open(final, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for det in data.get('round_detections', []):
                gr = det.get('global_round')
                if isinstance(gr, int):
                    covered.add(gr)
        except Exception:
            continue
    return covered


def analyzer_ran(session: Path) -> bool:
    # Consider analyzer ran if any analysis_* directory exists
    return any(p.is_dir() and p.name.startswith('analysis_') for p in session.iterdir())


def main() -> None:
    ap = argparse.ArgumentParser(description='Check per-round coverage for detector and analyzer')
    ap.add_argument('--root', type=str, required=True, help='Root directory to scan recursively')
    ap.add_argument('--csv', type=str, default=None, help='Optional CSV output path')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f'Root not found or not a directory: {root}')

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    rows: List[Dict[str, Any]] = []
    total_missing_detector = 0
    total_sessions = 0
    total_missing_analyzer_sessions = 0

    for s in sessions:
        total_sessions += 1
        try:
            exp_rounds = load_experiment_rounds(s)
        except Exception as e:
            print(f'[ERROR] {s}: failed to load experiment rounds: {e}')
            continue

        det_rounds = collect_detector_rounds(s)
        missing_in_detector = sorted(r for r in exp_rounds if r not in det_rounds)
        total_missing_detector += 1 if missing_in_detector else 0

        ran = analyzer_ran(s)
        if not ran:
            missing_in_analyzer = exp_rounds[:]  # analyzer not run
            total_missing_analyzer_sessions += 1
        else:
            missing_in_analyzer = missing_in_detector[:]  # analyzer relies on detector coverage

        rows.append({
            'session': str(s),
            'rounds_total': len(exp_rounds),
            'detector_covered': len(det_rounds),
            'detector_missing_count': len(missing_in_detector),
            'detector_missing_rounds': missing_in_detector,
            'analyzer_ran': ran,
            'analyzer_missing_count': len(missing_in_analyzer),
            'analyzer_missing_rounds': missing_in_analyzer,
        })

    # Print summary
    print(f'Root: {root}')
    print(f'Sessions scanned: {total_sessions}')
    print(f'Sessions with detector missing rounds: {sum(1 for r in rows if r["detector_missing_count"]>0)}')
    print(f'Sessions where analyzer did not run: {sum(1 for r in rows if not r["analyzer_ran"]) }')

    # Detailed listing
    for r in rows:
        print('\nSession:', r['session'])
        print(f"  rounds_total={r['rounds_total']}  detector_covered={r['detector_covered']}  analyzer_ran={r['analyzer_ran']}")
        if r['detector_missing_count']:
            print(f"  detector_missing ({r['detector_missing_count']}): {r['detector_missing_rounds']}")
        if r['analyzer_missing_count']:
            print(f"  analyzer_missing ({r['analyzer_missing_count']}): {r['analyzer_missing_rounds']}")

    if args.csv:
        import csv
        outp = Path(args.csv).resolve()
        with open(outp, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['session','rounds_total','detector_covered','detector_missing_count','analyzer_ran','analyzer_missing_count','detector_missing_rounds','analyzer_missing_rounds']
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f'CSV written to: {outp}')


if __name__ == '__main__':
    main()

