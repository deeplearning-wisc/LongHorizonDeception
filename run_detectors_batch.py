#!/usr/bin/env python3
"""
Batch runner for detectors: runs up to N detectors in parallel over all leaf
result directories under a given root (default: Results_checked).

Behavior:
- Recursively find every directory that contains a result.json (an experiment session).
- Launch core/bidirectional_detector.py for each directory with --result_name=<dir>.
- Run at most --concurrency processes at the same time (default: 10).
- Each run writes its stdout/stderr to <session_dir>/detector_run.log.
- Skips a session if it already has a detector_*.json file (unless --force).

Usage examples:
  python run_detectors_batch.py --root Results_checked --concurrency 10
  python run_detectors_batch.py --root results --concurrency 8 --detector-workers 4
  python run_detectors_batch.py --root Results_checked --force
"""

from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


def find_session_dirs(root: Path) -> List[Path]:
    """Find all directories containing a result.json (recursively)."""
    sessions = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for d in sorted(sessions):
        rp = d.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(d)
    return unique


def already_has_detector_output(session_dir: Path) -> bool:
    """Heuristic: consider the session processed if any detector_*.json exists."""
    return any(session_dir.glob('detector_*.json')) or any(session_dir.glob('detector_ensemble_*/final.json'))


def main() -> None:
    parser = argparse.ArgumentParser(description='Batch-run detectors concurrently over result directories')
    parser.add_argument('--root', type=str, default='Results_checked', help='Root directory to scan recursively')
    parser.add_argument('--concurrency', type=int, default=10, help='Max concurrent detector processes (default: 10)')
    parser.add_argument('--detector-workers', type=int, default=4, help='--max_parallel for each detector process')
    parser.add_argument('--force', action='store_true', help='Run even if detector output already exists')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root directory not found or not a directory: {root}")

    script_path = Path(__file__).parent / 'core' / 'bidirectional_detector.py'
    if not script_path.exists():
        raise SystemExit(f"Detector script not found: {script_path}")

    sessions = find_session_dirs(root)
    if not sessions:
        print('No result.json found under root; nothing to do.')
        return

    print(f"Found {len(sessions)} session(s) under {root}")

    queue: List[Path] = []
    for s in sessions:
        if not args.force and already_has_detector_output(s):
            print(f"[SKIP] Existing detector output in {s.name}")
            continue
        queue.append(s)

    print(f"Queued {len(queue)} session(s) for detector runs (concurrency={args.concurrency})")

    # Process queue with concurrency limit
    running: List[Tuple[subprocess.Popen, Path]] = []
    completed = 0
    failed = 0

    def launch(session_dir: Path) -> subprocess.Popen:
        log_file = session_dir / 'detector_run.log'
        log_fh = open(log_file, 'a', encoding='utf-8')
        cmd = [sys.executable, str(script_path), '--result_name', str(session_dir), '--max_parallel', str(args.detector-workers if hasattr(args, 'detector-workers') else args.detector_workers)]
        # The above line cannot reference a hyphenated attr; patch below to avoid confusion
        return None  # placeholder

    # Build correct command without hyphenated attribute access
    detector_workers = args.detector_workers

    def spawn(session_dir: Path) -> Tuple[subprocess.Popen, Path]:
        log_file = session_dir / 'detector_run.log'
        log_fh = open(log_file, 'a', encoding='utf-8')
        cmd = [sys.executable, str(script_path), '--result_name', str(session_dir), '--max_parallel', str(detector_workers)]
        print(f"[LAUNCH] {session_dir.name} -> {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
        return proc, session_dir

    # Start initial batch
    idx = 0
    while idx < len(queue) or running:
        # Fill up to concurrency
        while idx < len(queue) and len(running) < args.concurrency:
            proc, sdir = spawn(queue[idx])
            running.append((proc, sdir))
            idx += 1

        # Poll running processes and reap finished
        still_running: List[Tuple[subprocess.Popen, Path]] = []
        for proc, sdir in running:
            ret = proc.poll()
            if ret is None:
                still_running.append((proc, sdir))
                continue
            if ret == 0:
                print(f"[OK] {sdir.name}")
                completed += 1
            else:
                print(f"[FAIL] {sdir.name} (exit={ret})")
                failed += 1
        running = still_running

    print(f"Done. Completed={completed}, Failed={failed}, Skipped={len(sessions)-len(queue)}")


if __name__ == '__main__':
    main()

