#!/usr/bin/env python3
"""
List sessions under a results tree where detector/analyzer did NOT finish.

Criteria:
- DETECTOR_NOT_RUN: no detector_*.json and no detector_ensemble_*/final.json
- DETECTOR_INCOMPLETE: expected rounds from result.json are not fully covered by detector round_detections
- ANALYZER_NOT_RUN: no analysis_* directory present
- ANALYZER_FAILED: analyzer_run.log exists and contains a traceback or fatal marker

Notes:
- Read-only. Does not modify any files.
- "Expected rounds" are global_round values present in result.json (across all tasks/rounds).

Usage:
  python list_unfinished_detector_analyzer.py --root Results_checked [--csv report.csv]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Set


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    uniq: List[Path] = []
    seen = set()
    for s in sorted(sessions):
        rs = s.resolve()
        if rs not in seen:
            seen.add(rs)
            uniq.append(s)
    return uniq


def expected_rounds(session: Path) -> List[int]:
    rs = session / 'result.json'
    data = json.load(rs.open('r', encoding='utf-8'))
    rounds: Set[int] = set()
    for task in data.get('experiment', {}).get('tasks', []):
        for r in task.get('rounds', []):
            gr = r.get('global_round')
            if isinstance(gr, int):
                rounds.add(gr)
    return sorted(rounds)


def detector_rounds(session: Path) -> Set[int]:
    covered: Set[int] = set()
    # detector_*.json
    for det in sorted(session.glob('detector_*.json')):
        try:
            data = json.load(det.open('r', encoding='utf-8'))
            for rd in data.get('round_detections', []):
                gr = rd.get('global_round')
                if isinstance(gr, int):
                    covered.add(gr)
        except Exception:
            pass
    # ensemble final
    for fin in sorted(session.glob('detector_ensemble_*/final.json')):
        try:
            data = json.load(fin.open('r', encoding='utf-8'))
            for rd in data.get('round_detections', []):
                gr = rd.get('global_round')
                if isinstance(gr, int):
                    covered.add(gr)
        except Exception:
            pass
    return covered


def analyzer_status(session: Path) -> str:
    # NOT_RUN if no analysis_* dir
    has_analysis = any(p.is_dir() and p.name.startswith('analysis_') for p in session.iterdir())
    if not has_analysis:
        return 'NOT_RUN'
    # FAILED if analyzer_run.log contains traceback/fatal
    log = session / 'analyzer_run.log'
    if log.exists():
        try:
            txt = log.read_text(encoding='utf-8', errors='ignore')
            lowered = txt.lower()
            if 'traceback' in lowered or 'fatal' in lowered or 'indexerror' in lowered:
                return 'FAILED'
        except Exception:
            pass
    return 'OK'


def main() -> None:
    ap = argparse.ArgumentParser(description='List sessions with unfinished detector/analyzer')
    ap.add_argument('--root', type=str, required=True, help='Root directory to scan recursively')
    ap.add_argument('--csv', type=str, default=None, help='Optional CSV output')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f'Root not found or not a directory: {root}')

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    unfinished: List[Dict[str, Any]] = []

    for s in sessions:
        exp = expected_rounds(s)
        det_files = list(s.glob('detector_*.json')) + list(s.glob('detector_ensemble_*/final.json'))
        det_cov = detector_rounds(s)
        det_not_run = len(det_files) == 0
        det_missing = sorted(r for r in exp if r not in det_cov)
        an_stat = analyzer_status(s)

        row = {
            'session': str(s),
            'expected_rounds': len(exp),
            'detector_files': len(det_files),
            'detector_covered_rounds': len(det_cov),
            'detector_missing_rounds': det_missing,
            'analyzer_status': an_stat,
        }

        # Consider unfinished if any of these:
        if det_not_run or det_missing or an_stat != 'OK':
            unfinished.append(row)

    # Print only unfinished
    print(f'Root: {root}')
    print(f'Unfinished sessions: {len(unfinished)}')
    for r in unfinished:
        print('\nSession:', r['session'])
        print(f"  expected_rounds={r['expected_rounds']}  detector_files={r['detector_files']}  detector_covered={r['detector_covered_rounds']}")
        if r['detector_files'] == 0:
            print('  DETECTOR_NOT_RUN')
        if r['detector_missing_rounds']:
            print(f"  DETECTOR_INCOMPLETE (missing {len(r['detector_missing_rounds'])}): {r['detector_missing_rounds']}")
        print(f"  ANALYZER_STATUS: {r['analyzer_status']}")

    if args.csv and unfinished:
        import csv
        outp = Path(args.csv).resolve()
        with open(outp, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['session','expected_rounds','detector_files','detector_covered_rounds','detector_missing_rounds','analyzer_status']
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in unfinished:
                w.writerow(r)
        print(f'CSV written to: {outp}')


if __name__ == '__main__':
    main()

