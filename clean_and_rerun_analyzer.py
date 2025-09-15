#!/usr/bin/env python3
"""
Clean analyzer outputs and re-run analyzer for all sessions under a root.

WHAT IT REMOVES (per session dir):
- Directories: analysis_* (all timestamps)
- Files: analyzer_run.log, state_evolution.png, state_evolution_detector_*.png (if present)

WHAT IT KEEPS:
- result.json, detector_*.json, detector_ensemble_*/ (detector outputs)
- Any other experiment artifacts are preserved.

Usage:
  # Show what would be deleted, do not delete, do not rerun
  python clean_and_rerun_analyzer.py --root Results_checked

  # Actually delete and re-run analyzer (4-way parallel)
  python clean_and_rerun_analyzer.py --root Results_checked --force --concurrency 4

  # Skip plots to speed up
  python clean_and_rerun_analyzer.py --root Results_checked --force --no-plot

Notes:
- This script does NOT modify experiment data (result.json, detector outputs).
"""

from __future__ import annotations

import argparse
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    # Deduplicate, preserve order
    uniq: List[Path] = []
    seen = set()
    for s in sorted(sessions):
        rp = s.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(s)
    return uniq


def collect_targets(session_dir: Path) -> Tuple[List[Path], List[Path]]:
    del_dirs: List[Path] = []
    del_files: List[Path] = []

    for child in session_dir.iterdir():
        if child.is_dir() and child.name.startswith('analysis_'):
            del_dirs.append(child)
        elif child.is_file():
            if child.name == 'analyzer_run.log':
                del_files.append(child)
            elif child.name == 'state_evolution.png':
                del_files.append(child)
            elif child.name.startswith('state_evolution_detector_') and child.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
                del_files.append(child)
    return del_dirs, del_files


def delete_targets(del_dirs: List[Path], del_files: List[Path]) -> None:
    for d in del_dirs:
        shutil.rmtree(d, ignore_errors=True)
    for f in del_files:
        try:
            f.unlink(missing_ok=True)
        except TypeError:
            # Python <3.8 compatibility
            if f.exists():
                f.unlink()


def spawn_analyzer(session_dir: Path) -> subprocess.Popen:
    analyzer_path = Path(__file__).parent / 'analyzer.py'
    if not analyzer_path.exists():
        raise SystemExit(f"analyzer.py not found at {analyzer_path}")
    cmd = [sys.executable, str(analyzer_path), '--result_name', str(session_dir)]
    log_file = session_dir / 'analyzer_run.log'
    log_fh = open(log_file, 'a', encoding='utf-8')
    print(f"[LAUNCH] {session_dir} -> {' '.join(cmd)}")
    return subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)


def main() -> None:
    ap = argparse.ArgumentParser(description='Clean analyzer outputs and re-run analyzer for all sessions')
    ap.add_argument('--root', type=str, default='Results_checked', help='Root directory to scan recursively')
    ap.add_argument('--force', action='store_true', help='Actually delete targets (without this, only lists)')
    # no --no-plot; always generate plots to align with strict requirements
    ap.add_argument('--concurrency', type=int, default=4, help='Max concurrent analyzer processes (default 4)')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a directory: {root}")

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    # Collect targets
    total_dirs = 0
    total_files = 0
    plan: List[Tuple[Path, List[Path], List[Path]]] = []
    for s in sessions:
        del_dirs, del_files = collect_targets(s)
        total_dirs += len(del_dirs)
        total_files += len(del_files)
        plan.append((s, del_dirs, del_files))

    print(f"Found {len(sessions)} session(s) under {root}")
    print(f"Planned deletions: {total_dirs} directories, {total_files} files")

    # List targets if not forced
    if not args.force:
        print("\nPreview of deletions (use --force to apply):")
        for s, ddirs, dfiles in plan:
            if not ddirs and not dfiles:
                continue
            print(f"\nSession: {s}")
            for d in ddirs:
                print(f"  [DIR]  {d}")
            for f in dfiles:
                print(f"  [FILE] {f}")
        print("\nNo changes made. Re-run with --force to delete, then I will re-run analyzer.")
        return

    # Delete targets
    for s, ddirs, dfiles in plan:
        if ddirs or dfiles:
            print(f"[CLEAN] {s} ({len(ddirs)} dirs, {len(dfiles)} files)")
            delete_targets(ddirs, dfiles)

    # Re-run analyzer with concurrency
    running: List[Tuple[subprocess.Popen, Path]] = []
    idx = 0
    completed = 0
    failed = 0
    ok_sessions: List[Path] = []
    failed_sessions: List[Path] = []

    def fill_slots():
        nonlocal idx
        while idx < len(sessions) and len(running) < args.concurrency:
            proc = spawn_analyzer(sessions[idx])
            running.append((proc, sessions[idx]))
            idx += 1

    fill_slots()
    while idx < len(sessions) or running:
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
                ok_sessions.append(sdir)
            else:
                print(f"[FAIL] {sdir} (exit={ret})")
                failed += 1
                failed_sessions.append(sdir)
        running = still
        fill_slots()

    print(f"\nDone. Completed={completed}, Failed={failed}")
    if failed_sessions:
        print("Failed sessions:")
        for s in failed_sessions:
            print(f"  - {s}")


if __name__ == '__main__':
    main()
