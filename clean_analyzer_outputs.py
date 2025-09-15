#!/usr/bin/env python3
"""
Clean ONLY analyzer-generated artifacts under a results tree.

Deletes per-session:
- Directories: analysis_*
- Files: analyzer_run.log, state_evolution.png, state_evolution_detector_*.png

Keeps experiment data intact (result.json, detector_*.json, detector_ensemble_*/ ... are NOT touched).

Usage:
  # Preview (no deletion):
  python clean_analyzer_outputs.py --root Results_checked

  # Actually delete:
  python clean_analyzer_outputs.py --root Results_checked --force
"""

from __future__ import annotations

import argparse
import shutil
import os
from pathlib import Path
from typing import List, Tuple, Dict


def find_sessions(root: Path) -> List[Path]:
    sessions: List[Path] = []
    for res_file in root.rglob('result.json'):
        sessions.append(res_file.parent)
    # dedupe + sort
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


def _human(nbytes: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    v = float(nbytes)
    for u in units:
        if v < 1024.0:
            return f"{v:.1f}{u}"
        v /= 1024.0
    return f"{v:.1f}PB"


def _dir_size(path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def delete_targets(del_dirs: List[Path], del_files: List[Path]) -> None:
    for d in del_dirs:
        shutil.rmtree(d, ignore_errors=True)
    for f in del_files:
        try:
            f.unlink(missing_ok=True)
        except TypeError:
            if f.exists():
                f.unlink()


def main() -> None:
    ap = argparse.ArgumentParser(description='Clean analyzer artifacts under results tree')
    ap.add_argument('--root', type=str, default='Results_checked', help='Root directory to scan recursively')
    ap.add_argument('--force', action='store_true', help='Actually delete files (default: preview only)')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root not found or not a directory: {root}")

    sessions = find_sessions(root)
    if not sessions:
        print('No sessions found (no result.json).')
        return

    plan: List[Tuple[Path, List[Path], List[Path]]] = []
    totals: Dict[str, int] = {
        'sessions': 0,
        'dirs': 0,
        'files': 0,
        'bytes': 0,
    }

    per_session_sizes: List[Tuple[Path, int, int, int]] = []  # (session, dir_count, file_count, bytes)

    for s in sessions:
        ddirs, dfiles = collect_targets(s)
        if not ddirs and not dfiles:
            continue
        plan.append((s, ddirs, dfiles))

        # Compute size footprint
        sz = 0
        for d in ddirs:
            sz += _dir_size(d)
        for f in dfiles:
            sz += _file_size(f)

        per_session_sizes.append((s, len(ddirs), len(dfiles), sz))
        totals['sessions'] += 1
        totals['dirs'] += len(ddirs)
        totals['files'] += len(dfiles)
        totals['bytes'] += sz

    print(f"Found {len(sessions)} session(s) under {root}")
    print(f"Sessions with analyzer artifacts: {totals['sessions']}")
    print(f"Targets to delete: {totals['dirs']} directories, {totals['files']} files, approx {_human(totals['bytes'])}")

    if not args.force:
        print('\nPreview (use --force to actually delete):')
        # Sort sessions by size desc to highlight big wins
        per_session_sizes.sort(key=lambda t: t[3], reverse=True)
        for s, dcnt, fcnt, sz in per_session_sizes:
            print(f"\nSession: {s}")
            print(f"  Summary: {dcnt} dir(s), {fcnt} file(s), approx {_human(sz)}")
            # List individual targets with sizes
            for d in sorted([p for p in (p for p in (x for x in plan if x[0]==s).__next__()[1])], key=lambda p: p.name):
                print(f"  [DIR]  {d}  (approx {_human(_dir_size(d))})")
            for f in sorted([p for p in (p for p in (x for x in plan if x[0]==s).__next__()[2])], key=lambda p: p.name):
                print(f"  [FILE] {f}  ({_human(_file_size(f))})")
        print('\nNo changes made.')
        return

    for s, ddirs, dfiles in plan:
        print(f"[CLEAN] {s} ({len(ddirs)} dirs, {len(dfiles)} files)")
        delete_targets(ddirs, dfiles)

    print('Done.')


if __name__ == '__main__':
    main()
