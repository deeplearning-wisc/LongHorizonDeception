#!/usr/bin/env python3
"""
Clean detector outputs under a given results subtree.

Removes detector artifacts recursively:
- Files: detector_*.json (includes windowed variants)
- Directories: detector_ensemble_* (entire directory)
- Logs: detector_run.log (deleted by default; use --keep-logs to preserve)

Safety:
- Default is DRY-RUN (no deletions). Use --apply to actually delete.
- Prints a clear plan of what would be removed.

Usage examples:
  python clean_detector_results.py /path/to/results
  python clean_detector_results.py /path/to/results --apply
  python clean_detector_results.py /path/to/results --keep-logs --apply
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import List, Tuple


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Remove detector outputs (detector_*.json, detector_ensemble_*) recursively")
    ap.add_argument("root", type=str, help="Root directory to clean under")
    ap.add_argument("--keep-logs", action="store_true", help="Preserve detector_run.log files (default deletes them)")
    ap.add_argument("--apply", action="store_true", help="Actually perform deletions (default: dry-run)")
    return ap.parse_args()


def resolve_root(root_str: str) -> Path:
    root = Path(root_str).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Root not found or not a directory: {root}")
    return root


def plan_deletions(root: Path, keep_logs: bool) -> Tuple[List[Path], List[Path]]:
    files: List[Path] = []
    dirs: List[Path] = []

    # detector JSONs
    for p in root.rglob("detector_*.json"):
        files.append(p)

    # detector ensembles
    for d in root.rglob("detector_ensemble_*"):
        if d.is_dir():
            dirs.append(d)

    # logs (deleted by default)
    if not keep_logs:
        for p in root.rglob("detector_run.log"):
            files.append(p)

    # De-duplicate while preserving order
    def dedup(paths: List[Path]) -> List[Path]:
        seen = set()
        out: List[Path] = []
        for x in paths:
            rp = x.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(x)
        return out

    return dedup(files), dedup(dirs)


def main() -> None:
    args = parse_args()
    root = resolve_root(args.root)

    files, dirs = plan_deletions(root, args.keep_logs)
    print(f"Root: {root}")
    print("Mode: APPLY" if args.apply else "Mode: DRY-RUN")
    print(f"Planned removals: files={len(files)}, dirs={len(dirs)}")

    if files:
        print("\nFiles:")
        for p in files:
            print(f"  - {p}")

    if dirs:
        print("\nDirectories:")
        for d in dirs:
            print(f"  - {d}")

    if not args.apply:
        print("\nNothing deleted (dry-run). Re-run with --apply to execute.")
        return

    # Perform deletions
    errors: List[str] = []
    for p in files:
        try:
            p.unlink(missing_ok=True)
        except Exception as e:
            errors.append(f"file {p}: {e}")
    for d in dirs:
        try:
            shutil.rmtree(d, ignore_errors=False)
        except Exception as e:
            errors.append(f"dir {d}: {e}")

    if errors:
        print("\nCompleted with errors:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\nDeletion completed successfully.")


if __name__ == "__main__":
    main()
