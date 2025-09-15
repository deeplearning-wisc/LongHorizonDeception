#!/usr/bin/env python3
"""
Aggregate detector summary metrics for a directory level.

Given a root path (e.g.,
  - /Users/.../Results_checked/GPT5_main
  - /Users/.../Results_checked/GPT5_control/pressure_level/medium
), recursively find sessions and their detector JSONs, read precomputed
summary metrics, and report aggregate statistics:

  - deception_rate (mean, variance)
  - severity_average_all_rounds (mean, variance)
  - severity_average_deception_only (mean, variance)

Session selection:
- A "session" is identified by the parent directory that contains result.json.
- For each session, we select the latest detector JSON available:
  1) Prefer the lexicographically latest detector_*.json under the session
  2) Otherwise, the lexicographically latest detector_ensemble_*/final.json

Output:
- Prints aggregate metrics to stdout, plus per-session counts.
- Optionally writes CSV with per-session values via --csv.

Strictness:
- If a detector JSON is missing the 'summary' block or required fields, that
  session is skipped (reported). Aggregation uses only valid sessions.

Usage:
  python aggregate_detector_stats.py \
    --root /Users/.../Results_checked/GPT5_main \
    [--csv out.csv]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res in root.rglob('result.json'):
        sessions.append(res.parent)
    # Deduplicate + sort
    seen = set()
    uniq: List[Path] = []
    for s in sorted(sessions):
        rp = s.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(s)
    return uniq


def select_detector_json(session: Path) -> Path | None:
    # Prefer detector_*.json
    dets = sorted(session.glob('detector_*.json'))
    if dets:
        return dets[-1]
    # Else ensemble final
    finals = sorted(session.glob('detector_ensemble_*/final.json'))
    if finals:
        return finals[-1]
    return None


def read_summary(det_path: Path) -> Dict[str, Any] | None:
    try:
        data = json.loads(det_path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(data, dict) or 'summary' not in data:
        return None
    return data['summary']


def mean_and_var(values: List[float]) -> Tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    m = sum(values) / n
    if n == 1:
        return m, 0.0
    var = sum((x - m) ** 2 for x in values) / (n - 1)  # sample variance
    return m, var


def main() -> None:
    ap = argparse.ArgumentParser(description='Aggregate detector summary metrics for a results level')
    ap.add_argument('--root', type=str, required=True, help='Directory to scan recursively (level root)')
    ap.add_argument('--csv', type=str, default=None, help='Optional CSV output with per-session values')
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f'Root not found or not a directory: {root}')

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    # Collect per-session metrics
    rows: List[Dict[str, Any]] = []
    skipped: List[Tuple[Path, str]] = []

    for s in sessions:
        det = select_detector_json(s)
        if det is None:
            skipped.append((s, 'detector JSON not found'))
            continue
        summ = read_summary(det)
        if not summ:
            skipped.append((s, 'summary missing in detector JSON'))
            continue
        try:
            row = {
                'session': str(s),
                'detector': str(det.name),
                'deception_rate': float(summ['deception_rate']),
                'severity_average_all_rounds': float(summ['severity_average_all_rounds']),
                'severity_average_deception_only': float(summ['severity_average_deception_only']),
            }
            rows.append(row)
        except Exception as e:
            skipped.append((s, f'malformed summary: {e}'))

    if not rows:
        print('No valid sessions with detector summaries found.')
        if skipped:
            print('Skipped:')
            for s, r in skipped:
                print(f'  - {s} :: {r}')
        return

    # Aggregate
    dr_list = [r['deception_rate'] for r in rows]
    sev_all_list = [r['severity_average_all_rounds'] for r in rows]
    sev_dec_list = [r['severity_average_deception_only'] for r in rows]

    dr_mean, dr_var = mean_and_var(dr_list)
    sa_mean, sa_var = mean_and_var(sev_all_list)
    sd_mean, sd_var = mean_and_var(sev_dec_list)

    # Print summary
    print(f'Root: {root}')
    print(f'Valid sessions: {len(rows)}  |  Skipped: {len(skipped)}')
    print('Metrics (mean, variance):')
    print(f'  deception_rate: ({dr_mean:.6f}, {dr_var:.6f})')
    print(f'  severity_average_all_rounds: ({sa_mean:.6f}, {sa_var:.6f})')
    print(f'  severity_average_deception_only: ({sd_mean:.6f}, {sd_var:.6f})')

    if skipped:
        print('\nSkipped sessions:')
        for s, r in skipped:
            print(f'  - {s} :: {r}')

    # Optional CSV
    if args.csv:
        import csv
        outp = Path(args.csv).expanduser().resolve()
        with outp.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['session','detector','deception_rate','severity_average_all_rounds','severity_average_deception_only'])
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f'CSV written to: {outp}')


if __name__ == '__main__':
    main()

