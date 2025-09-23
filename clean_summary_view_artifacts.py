#!/usr/bin/env python3
"""
Clean summary-view artifacts under a given results subtree.

Removes recursively the following files:
- log_view.html
- summary_view_run.log
- summary.json

Safety:
- Default is DRY-RUN (prints what would be removed). Use --apply to actually delete.

Usage:
  python clean_summary_view_artifacts.py /path/to/session_or_root
  python clean_summary_view_artifacts.py /path/to/session_or_root --apply
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List


TARGET_FILENAMES = {"log_view.html", "summary_view_run.log", "summary.json"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Remove summary-view artifacts recursively")
    ap.add_argument("root", type=str, help="Root directory to clean under")
    ap.add_argument("--apply", action="store_true", help="Actually perform deletions (default: dry-run)")
    return ap.parse_args()


def resolve_root(root_str: str) -> Path:
    root = Path(root_str).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Root not found or not a directory: {root}")
    return root


def plan_targets(root: Path) -> List[Path]:
    files: List[Path] = []
    for name in TARGET_FILENAMES:
        for p in root.rglob(name):
            if p.is_file():
                files.append(p)
    # Dedup while preserving order
    seen = set()
    uniq: List[Path] = []
    for p in files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def main() -> None:
    args = parse_args()
    root = resolve_root(args.root)
    files = plan_targets(root)

    print(f"Root: {root}")
    print("Mode: APPLY" if args.apply else "Mode: DRY-RUN")
    print(f"Planned file deletions: {len(files)}")
    for p in files:
        print(f"  - {p}")

    if not args.apply:
        print("\nNothing deleted (dry-run). Re-run with --apply to execute.")
        return

    errors: List[str] = []
    for p in files:
        try:
            p.unlink(missing_ok=True)
        except Exception as e:
            errors.append(f"{p}: {e}")

    if errors:
        print("\nCompleted with errors:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\nDeletion completed successfully.")


if __name__ == "__main__":
    main()

