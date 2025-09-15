#!/usr/bin/env python3
"""
Scan a results tree and report sessions that did not finish, defined as:
- Missing Task <N> (default 14), or
- Task <N> exists but its rounds array is empty

It reads only result.json; detector files are not required.

Usage:
  python find_incomplete_sessions.py \
    --root \
    /Users/superposition/Desktop/Deception_local/DeceptioN/Results_checked \
    [--expected-task 14] [--csv out.csv]

Notes:
- Does NOT modify any files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    # Deduplicate & sort
    uniq: List[Path] = []
    seen = set()
    for s in sorted(sessions):
        rp = s.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(s)
    return uniq


def analyze_session(session: Path, expected_task: int) -> Tuple[str, Dict[str, Any]]:
    """Return (status, info) where status in {'OK','MISSING_TASK','EMPTY_ROUNDS','ERROR'}"""
    result_path = session / 'result.json'
    try:
        data = json.load(result_path.open('r', encoding='utf-8'))
    except Exception as e:
        return 'ERROR', {
            'session': str(session),
            'reason': f'Failed to load result.json: {e}'
        }

    # Validate schema minimally
    try:
        tasks = data['experiment']['tasks']
        if not isinstance(tasks, list):
            return 'ERROR', {
                'session': str(session),
                'reason': 'experiment.tasks is not a list'
            }
    except KeyError as e:
        return 'ERROR', {
            'session': str(session),
            'reason': f'Missing key: {e}'
        }

    # Build index by task_sequence_num
    task_index: Dict[int, Dict[str, Any]] = {}
    for t in tasks:
        try:
            tnum = int(t['task']['task_sequence_num'])
        except Exception:
            # Skip malformed entries
            continue
        task_index[tnum] = t

    if expected_task not in task_index:
        return 'MISSING_TASK', {
            'session': str(session),
            'expected_task': expected_task,
            'present_tasks': sorted(task_index.keys()),
            'reason': f'Task {expected_task} not present'
        }

    last_task = task_index[expected_task]
    rounds = last_task.get('rounds', [])
    if not isinstance(rounds, list) or len(rounds) == 0:
        return 'EMPTY_ROUNDS', {
            'session': str(session),
            'expected_task': expected_task,
            'present_tasks': sorted(task_index.keys()),
            'reason': f'Task {expected_task} rounds empty'
        }

    return 'OK', {
        'session': str(session),
        'expected_task': expected_task,
        'present_tasks': sorted(task_index.keys()),
        'rounds_in_last_task': len(rounds)
    }


def main() -> None:
    ap = argparse.ArgumentParser(description='Find sessions that did not finish (missing or empty final task)')
    ap.add_argument('--root', type=str, required=True, help='Root directory to scan recursively')
    ap.add_argument('--expected-task', type=int, default=14, help='Expected final task number (default: 14)')
    ap.add_argument('--csv', type=str, default=None, help='Optional CSV report path')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f'Root not found or not a directory: {root}')

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    missing: List[Dict[str, Any]] = []
    empty: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    oks: List[Dict[str, Any]] = []

    for s in sessions:
        status, info = analyze_session(s, args.expected_task)
        if status == 'OK':
            oks.append(info)
        elif status == 'MISSING_TASK':
            missing.append(info)
        elif status == 'EMPTY_ROUNDS':
            empty.append(info)
        else:
            errors.append(info)

    # Print report
    print(f'Root: {root}')
    print(f'Expected final task: {args.expected_task}')
    print(f'Total sessions: {len(sessions)}')
    print(f'OK: {len(oks)}  |  MISSING_TASK: {len(missing)}  |  EMPTY_ROUNDS: {len(empty)}  |  ERROR: {len(errors)}')

    if missing:
        print('\nSessions missing final task:')
        for it in missing:
            print(f"  - {it['session']}  (present_tasks={it['present_tasks']})")

    if empty:
        print('\nSessions with empty rounds in final task:')
        for it in empty:
            print(f"  - {it['session']}  (present_tasks={it['present_tasks']})")

    if errors:
        print('\nSessions with errors:')
        for it in errors:
            print(f"  - {it['session']}  ({it['reason']})")

    if args.csv:
        import csv
        outp = Path(args.csv).resolve()
        with open(outp, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['status', 'session', 'expected_task', 'present_tasks', 'rounds_in_last_task', 'reason']
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for it in oks:
                w.writerow({
                    'status': 'OK',
                    'session': it.get('session'),
                    'expected_task': it.get('expected_task', args.expected_task),
                    'present_tasks': it.get('present_tasks'),
                    'rounds_in_last_task': it.get('rounds_in_last_task'),
                    'reason': ''
                })
            for it in missing:
                w.writerow({
                    'status': 'MISSING_TASK',
                    'session': it.get('session'),
                    'expected_task': it.get('expected_task', args.expected_task),
                    'present_tasks': it.get('present_tasks'),
                    'rounds_in_last_task': '',
                    'reason': it.get('reason')
                })
            for it in empty:
                w.writerow({
                    'status': 'EMPTY_ROUNDS',
                    'session': it.get('session'),
                    'expected_task': it.get('expected_task', args.expected_task),
                    'present_tasks': it.get('present_tasks'),
                    'rounds_in_last_task': 0,
                    'reason': it.get('reason')
                })
            for it in errors:
                w.writerow({
                    'status': 'ERROR',
                    'session': it.get('session'),
                    'expected_task': args.expected_task,
                    'present_tasks': '',
                    'rounds_in_last_task': '',
                    'reason': it.get('reason')
                })
        print(f'CSV written to: {outp}')


if __name__ == '__main__':
    main()

