#!/usr/bin/env python3
"""
Batch-run the built-in analyzer.py across all sessions under a root directory.

For each directory containing a result.json, invoke:
  python analyzer.py --result_name <session_dir>

Options:
  --root DIR      Root directory to scan recursively (default: Results_checked)
  --no-plot       Pass through to analyzer to skip plot generation
  --concurrency N Run up to N analyzers in parallel (default: 4)

This script reads results and writes analysis outputs into each session's
analysis_<timestamp>/ subfolder (as analyzer.py already does). It does not
modify experiment data beyond analyzer outputs.
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
    # Deduplicate preserve order
    uniq: List[Path] = []
    seen = set()
    for s in sorted(sessions):
        rp = s.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(s)
    return uniq


def main() -> None:
    ap = argparse.ArgumentParser(description='Batch run analyzer.py over results tree')
    ap.add_argument('--root', type=str, default='Results_checked', help='Root directory to scan')
    ap.add_argument('--no-plot', action='store_true', help='Disable plot generation for all runs')
    ap.add_argument('--concurrency', type=int, default=4, help='Max concurrent analyzer processes (default 4)')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a directory: {root}")

    analyzer_path = Path(__file__).parent / 'analyzer.py'
    if not analyzer_path.exists():
        raise SystemExit(f"analyzer.py not found at {analyzer_path}")

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    print(f"Found {len(sessions)} session(s) under {root}")

    queue = sessions[:]
    running: List[Tuple[subprocess.Popen, Path]] = []
    idx = 0
    completed = 0
    failed = 0
    ok_sessions: List[Path] = []
    failed_sessions: List[Path] = []

    def spawn(session_dir: Path) -> Tuple[subprocess.Popen, Path]:
        cmd = [sys.executable, str(analyzer_path), '--result_name', str(session_dir)]
        if args.no_plot:
            cmd.append('--no-plot')
        log_file = session_dir / 'analyzer_run.log'
        log_fh = open(log_file, 'a', encoding='utf-8')
        print(f"[LAUNCH] {session_dir.name} -> {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
        return proc, session_dir

    while idx < len(queue) or running:
        # Fill slots
        while idx < len(queue) and len(running) < args.concurrency:
            proc, sdir = spawn(queue[idx])
            running.append((proc, sdir))
            idx += 1

        # Poll
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

    print(f"Done. Completed={completed}, Failed={failed}")
    if failed_sessions:
        print("\nFailed sessions:")
        for s in failed_sessions:
            print(f"  - {s}")


if __name__ == '__main__':
    main()
