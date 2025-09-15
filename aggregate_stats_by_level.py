#!/usr/bin/env python3
"""
Aggregate detector summary metrics per "level" directory automatically.

Definition of a "level" directory:
- A directory whose immediate child directories are the experiment sessions
  (i.e., at least one child dir contains a result.json file).

Examples that will be treated as levels under the root you pass:
- /.../Results_checked/GPT5_main
- /.../Results_checked/GPT5_control/pressure_level/medium

For each such level directory, this script:
- Collects all immediate child session dirs (child/result.json exists)
- For each session, picks the latest detector JSON (detector_*.json, else detector_ensemble_*/final.json)
- Reads summary metrics and aggregates:
    * deception_rate (mean, variance)
    * severity_average_all_rounds (mean, variance)
    * severity_average_deception_only (mean, variance)
- Writes a CSV with per-session values to <level>/aggregate_stats.csv
- Prints a one-line summary per level

Usage:
  python aggregate_stats_by_level.py --root /Users/.../Results_checked
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def is_session_dir(d: Path) -> bool:
    return (d.is_dir() and (d / 'result.json').exists())


def find_level_dirs(root: Path) -> List[Path]:
    """Find level directories: those with immediate child session directories."""
    level_dirs: List[Path] = []
    # Walk the tree; consider each directory as a potential level
    for p in root.rglob('*'):
        if not p.is_dir():
            continue
        # skip hidden/system dirs
        if p.name.startswith('.'):
            continue
        # immediate children with result.json
        child_sessions = [c for c in p.iterdir() if is_session_dir(c)] if any(p.iterdir()) else []
        if child_sessions:
            level_dirs.append(p)
    # Also consider root itself if it directly contains sessions
    direct_sessions = [c for c in root.iterdir() if is_session_dir(c)] if any(root.iterdir()) else []
    if direct_sessions and root not in level_dirs:
        level_dirs.insert(0, root)
    # Deduplicate and sort
    seen = set()
    uniq: List[Path] = []
    for d in sorted(level_dirs):
        rp = d.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(d)
    return uniq


def select_detector_json(session: Path) -> Path | None:
    dets = sorted(session.glob('detector_*.json'))
    if dets:
        return dets[-1]
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
    var = sum((x - m) ** 2 for x in values) / (n - 1)
    return m, var


def aggregate_level(level_dir: Path) -> Tuple[List[Dict[str, Any]], List[Tuple[Path, str]]]:
    sessions = [c for c in level_dir.iterdir() if is_session_dir(c)]
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
            rows.append({
                'session': str(s.name),
                'detector': det.name,
                'deception_rate': float(summ['deception_rate']),
                'severity_average_all_rounds': float(summ['severity_average_all_rounds']),
                'severity_average_deception_only': float(summ['severity_average_deception_only']),
            })
        except Exception as e:
            skipped.append((s, f'malformed summary: {e}'))
    return rows, skipped


def write_csv(level_dir: Path, rows: List[Dict[str, Any]]) -> Path:
    import csv
    outp = level_dir / 'aggregate_stats.csv'
    with outp.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                'session',
                'detector',
                'deception_rate',
                'severity_average_all_rounds',
                'severity_average_deception_only',
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return outp


def main() -> None:
    ap = argparse.ArgumentParser(description='Aggregate detector stats per level directory automatically')
    ap.add_argument('--root', type=str, required=True, help='Results_checked root')
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f'Root not found or not a directory: {root}')

    levels = find_level_dirs(root)
    if not levels:
        print('No level directories with immediate sessions found.')
        return

    print(f'Found {len(levels)} level directory(ies).')
    for level in levels:
        rows, skipped = aggregate_level(level)
        if not rows:
            print(f'[SKIP] {level} (no valid session summaries)')
            if skipped:
                print('  Skipped:')
                for s, r in skipped:
                    print(f'    - {s.name}: {r}')
            continue
        # Aggregate
        dr = [r['deception_rate'] for r in rows]
        sa = [r['severity_average_all_rounds'] for r in rows]
        sd = [r['severity_average_deception_only'] for r in rows]
        dr_m, dr_v = mean_and_var(dr)
        sa_m, sa_v = mean_and_var(sa)
        sd_m, sd_v = mean_and_var(sd)
        # Write CSV
        out_csv = write_csv(level, rows)
        print(f"[OK] {level}: N={len(rows)} -> CSV={out_csv.name}")
        print(f"     deception_rate: mean={dr_m:.6f} var={dr_v:.6f}")
        print(f"     severity_all:   mean={sa_m:.6f} var={sa_v:.6f}")
        print(f"     severity_only:  mean={sd_m:.6f} var={sd_v:.6f}")
        if skipped:
            print('     Skipped:')
            for s, r in skipped:
                print(f'       - {s.name}: {r}')


if __name__ == '__main__':
    main()

