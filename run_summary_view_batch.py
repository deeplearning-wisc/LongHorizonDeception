#!/usr/bin/env python3
"""
Batch-run strict summarizer + viewer for all sessions under a root directory.

For each session (a directory containing result.json):
  - Run summarizer (strict). If it fails, mark FAIL and skip viewer.
  - If summarizer succeeds, run chat viewer (strict) to produce log_view.html.

Concurrency: up to N sessions in parallel (default: 4). Each session is treated
as an atomic unit: summarizer then viewer, with a single per-session log file.

Usage:
  python run_summary_view_batch.py \
    --root Results_checked/test \
    --concurrency 4 \
    --workers 2

Notes:
  - This script is read/write only to per-session artifacts: summary.json and
    log_view.html, plus a per-session log file summary_view_run.log.
  - It does not modify experiment data (result.json, detector outputs).
"""

from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res in root.rglob('result.json'):
        sessions.append(res.parent)
    # Deduplicate and sort by path
    seen = set()
    uniq: List[Path] = []
    for s in sorted(sessions):
        rp = s.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(s)
    return uniq


def select_detector(session: Path) -> Path:
    # Prefer latest detector_*.json; else try detector_ensemble_*/final.json
    det_files = sorted(session.glob('detector_*.json'))
    if det_files:
        return det_files[-1]
    ensemble_finals = sorted(session.glob('detector_ensemble_*/final.json'))
    if ensemble_finals:
        return ensemble_finals[-1]
    raise FileNotFoundError(f"No detector JSON found under {session}")


def run_session(session: Path, workers: int = 2, no_summary: bool = False) -> Tuple[Path, bool, str]:
    """Run summarizer then viewer for one session. Returns (session, ok, reason)."""
    result_json = session / 'result.json'
    if not result_json.exists():
        return session, False, 'result.json not found'
    log_path = session / 'summary_view_run.log'
    log_fh = log_path.open('a', encoding='utf-8')
    try:
        # Summarizer (strict) - skip if --no-summary
        if not no_summary:
            sum_cmd = [
                sys.executable,
                str(Path(__file__).parent / 'visualization' / 'summarizer.py'),
                '--run', str(session),
                '--workers', str(workers),
            ]
            log_fh.write(f"[RUN] {' '.join(sum_cmd)}\n")
            ret = subprocess.run(sum_cmd, stdout=log_fh, stderr=subprocess.STDOUT)
            if ret.returncode != 0:
                return session, False, f'summarizer failed (exit={ret.returncode})'
        else:
            log_fh.write("[SKIP] Summarizer skipped due to --no-summary flag\n")

        # Viewer (with --no-summary if requested)
        try:
            det_path = select_detector(session)
        except Exception as e:
            return session, False, f'detector not found: {e}'
        out_html = session / 'log_view.html'
        view_cmd = [
            sys.executable,
            str(Path(__file__).parent / 'visualization' / 'chat_dialog_viewer.py'),
            '--run', str(session),
            '--detector', str(det_path),
            '--out', str(out_html),
        ]
        if no_summary:
            view_cmd.append('--no-summary')
        log_fh.write(f"[RUN] {' '.join(view_cmd)}\n")
        ret2 = subprocess.run(view_cmd, stdout=log_fh, stderr=subprocess.STDOUT)
        if ret2.returncode != 0:
            return session, False, f'viewer failed (exit={ret2.returncode})'
        return session, True, ''
    finally:
        try:
            log_fh.close()
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser(description='Batch-run strict summarizer + viewer over a results tree')
    ap.add_argument('--root', type=str, default=str(Path('Results_checked') / 'test'), help='Root directory to scan')
    ap.add_argument('--concurrency', type=int, default=4, help='Max concurrent sessions (default 4)')
    ap.add_argument('--workers', type=int, default=2, help='Summarizer workers per session (default 2)')
    ap.add_argument('--no-summary', action='store_true', help='Skip summarizer and run viewer without summaries')
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a directory: {root}")

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    print(f"Found {len(sessions)} session(s) under {root}")

    # Concurrency via ThreadPool; each task runs summarizer then viewer synchronously (atomic per session)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    try:
        from tqdm.auto import tqdm  # type: ignore
    except Exception:  # pragma: no cover
        tqdm = None

    completed = 0
    failed = 0
    failures: List[Tuple[Path, str]] = []

    def task_fn(sess: Path) -> Tuple[Path, bool, str]:
        return run_session(sess, workers=args.workers, no_summary=args.no_summary)

    try:
        with ThreadPoolExecutor(max_workers=max(1, int(args.concurrency))) as ex:
            futures = {ex.submit(task_fn, s): s for s in sessions}
            iterator = as_completed(futures)
            if tqdm is not None:
                iterator = tqdm(iterator, total=len(futures), desc='Sessions', unit='sess')
            for fut in iterator:
                try:
                    sess, ok, reason = fut.result()
                except Exception as e:
                    # defensive: catch unexpected thread exceptions
                    sess = futures[fut]
                    ok = False
                    reason = f'unhandled error: {e}'
                print(f"[OK] {sess}" if ok else f"[FAIL] {sess} :: {reason}")
                if ok:
                    completed += 1
                else:
                    failed += 1
                    failures.append((sess, reason))
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Aborting batch run by user.")

    print(f"\nDone. Completed={completed}, Failed={failed}")
    if failures:
        print("Failed sessions:")
        for s, r in failures:
            print(f"  - {s} :: {r}")


if __name__ == '__main__':
    main()
