#!/usr/bin/env python3
"""
Run analyzer.py for all sessions under a root with clear error reporting.

For each directory containing result.json:
- Invoke: python analyzer.py --result_name <session_dir> [--no-plot]
- Log output to <session_dir>/analyzer_run.log
- At the end, print a summary with explicit FAILED session paths.

Usage:
  python run_analyzer_with_report.py --root Results_checked [--no-plot] [--concurrency 4]
"""

from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    uniq: List[Path] = []
    seen = set()
    for s in sorted(sessions):
        rp = s.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(s)
    return uniq


def main() -> None:
    ap = argparse.ArgumentParser(description='Run analyzer with explicit failure report')
    ap.add_argument('--root', type=str, default='Results_checked', help='Root directory to scan')
    ap.add_argument('--concurrency', type=int, default=4, help='Max concurrent analyzer processes (default 4)')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a directory: {root}")

    analyzer_path = Path(__file__).parent / 'analyzer.py'
    if not analyzer_path.exists():
        raise SystemExit(f"analyzer.py not found: {analyzer_path}")

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    queue = sessions[:]
    running: List[Tuple[subprocess.Popen, Path]] = []
    completed = 0
    failed = 0
    ok_sessions: List[Path] = []
    failed_sessions: List[Path] = []
    idx = 0

    def spawn(sdir: Path) -> Tuple[subprocess.Popen, Path]:
        cmd = [sys.executable, str(analyzer_path), '--result_name', str(sdir)]
        log_file = sdir / 'analyzer_run.log'
        log_fh = open(log_file, 'a', encoding='utf-8')
        print(f"[LAUNCH] {sdir} -> {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
        return proc, sdir

    # Fill initial slots
    while idx < len(queue) and len(running) < args.concurrency:
        proc, sdir = spawn(queue[idx])
        running.append((proc, sdir))
        idx += 1

    while idx < len(queue) or running:
        still: List[Tuple[subprocess.Popen, Path]] = []
        for proc, sdir in running:
            ret = proc.poll()
            if ret is None:
                still.append((proc, sdir))
                continue
            if ret == 0:
                print(f"[OK] {sdir}")
                completed += 1
                ok_sessions.append(sdir)
            else:
                print(f"[FAIL] {sdir} (exit={ret})")
                failed += 1
                failed_sessions.append(sdir)
        running = still

        while idx < len(queue) and len(running) < args.concurrency:
            proc, sdir = spawn(queue[idx])
            running.append((proc, sdir))
            idx += 1

    print(f"\nDone. Completed={completed}, Failed={failed}")
    if failed_sessions:
        print("Failed sessions:")
        for s in failed_sessions:
            print(f"  - {s}")


if __name__ == '__main__':
    main()
