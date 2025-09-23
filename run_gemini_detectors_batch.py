#!/usr/bin/env python3
"""
Batch-run the Gemini-based detector over all sessions in a results tree.

Uses core/bidirectional_detector_gemini.py (hardcoded to 'gemini_2_5_pro' in
configs/api_profiles.yaml). For each directory that contains a result.json,
launches one detector process unless detector output already exists (override
with --force). Stdout/stderr go to <session_dir>/detector_run.log.

Usage examples:
  python run_gemini_detectors_batch.py \
    --root Results_all_models/Main/GPT5_main_d_gemini --concurrency 6 --detector-workers 4
  python run_gemini_detectors_batch.py --root <path> --force
"""

from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


def find_session_dirs(root: Path) -> List[Path]:
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


def already_has_detector_output(session_dir: Path) -> bool:
    return any(session_dir.glob('detector_*.json')) or any(session_dir.glob('detector_ensemble_*/final.json'))


def main() -> None:
    ap = argparse.ArgumentParser(description='Batch-run Gemini detector over results tree')
    ap.add_argument('--root', type=str, default='Results_all_models/Main/GPT5_main_d_gemini', help='Root directory to scan')
    ap.add_argument('--concurrency', type=int, default=6, help='Max concurrent detector processes (default 6)')
    ap.add_argument('--detector-workers', type=int, default=4, help='Max parallel rounds per session (passed as --max_parallel)')
    ap.add_argument('--force', action='store_true', help='Run even if detector output already exists in session')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a directory: {root}")

    script_path = Path(__file__).parent / 'core' / 'bidirectional_detector_gemini.py'
    if not script_path.exists():
        raise SystemExit(f"Gemini detector script not found: {script_path}")

    sessions = find_session_dirs(root)
    if not sessions:
        print('No result.json found under root; nothing to do.')
        return

    queue: List[Path] = []
    for s in sessions:
        if not args.force and already_has_detector_output(s):
            print(f"[SKIP] Existing detector output in {s}")
            continue
        queue.append(s)

    print(f"Found {len(sessions)} session(s); queued {len(queue)} (concurrency={args.concurrency}, workers={args.detector_workers})")
    print(f"Detector: {script_path} (hardcoded gemini_2_5_pro)")

    running: List[Tuple[subprocess.Popen, Path]] = []
    completed = 0
    failed = 0
    idx = 0

    def spawn(session_dir: Path) -> Tuple[subprocess.Popen, Path]:
        log_file = session_dir / 'detector_run.log'
        log_fh = open(log_file, 'a', encoding='utf-8')
        cmd = [sys.executable, str(script_path), '--result_name', str(session_dir), '--max_parallel', str(args.detector_workers)]
        print(f"[LAUNCH] {session_dir} -> {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
        return proc, session_dir

    while idx < len(queue) or running:
        # fill
        while idx < len(queue) and len(running) < args.concurrency:
            proc, sdir = spawn(queue[idx])
            running.append((proc, sdir))
            idx += 1

        # poll
        still: List[Tuple[subprocess.Popen, Path]] = []
        for proc, sdir in running:
            ret = proc.poll()
            if ret is None:
                still.append((proc, sdir))
                continue
            if ret == 0:
                print(f"[OK] {sdir}")
                completed += 1
            else:
                print(f"[FAIL] {sdir} (exit={ret})")
                failed += 1
        running = still

    print(f"Done. Completed={completed}, Failed={failed}, Skipped={len(sessions)-len(queue)}")


if __name__ == '__main__':
    main()

