#!/usr/bin/env python3
"""
Flatten OpenRouter-style model subdirectories by merging parent and child names.

Context
- Some runs saved as parent/child where parent is a generic model holder (e.g.,
  "model_deepseek") and the child is the specific OpenRouter model ID
  (e.g., "deepseek-chat-v3.1"), producing an extra layer like:

    .../model_deepseek/deepseek-chat-v3.1/result.json

Goal
- Flatten to a single directory by concatenating names with an underscore and
  moving child contents up one level:

    .../model_deepseek_deepseek-chat-v3.1/result.json

Rules (fail-fast)
- Only operate on directories named like "model_*" that contain exactly one
  non-hidden child directory, and that child must contain a result.json.
- Parent must not contain any non-hidden files (avoid collisions).
- If the target merged directory already exists, the script fails for that
  case (no silent overwrite).

Usage
  cd /Users/superposition/Desktop/Deception_local/DeceptioN/Results_new_models
  python ../flatten_openrouter_subdir.py              # dry-run (default)
  python ../flatten_openrouter_subdir.py --apply      # perform changes

Options
- --root <path>: root to scan (default: current working directory)
- --apply: actually perform the rename/move (otherwise dry-run)
"""

from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


RESULT_FILE = "result.json"


@dataclass(frozen=True)
class Candidate:
    parent: Path
    child: Path


def resolve_root(root_str: str) -> Path:
    root = Path(root_str).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Root not found or not a directory: {root}")
    return root


def is_hidden(p: Path) -> bool:
    return p.name.startswith('.')


def find_single_child(parent: Path) -> Optional[Path]:
    """Return the single non-hidden child directory if exactly one exists, else None."""
    subdirs: List[Path] = [d for d in parent.iterdir() if d.is_dir() and not is_hidden(d)]
    files: List[Path] = [f for f in parent.iterdir() if f.is_file() and not is_hidden(f)]
    if files:
        return None
    if len(subdirs) != 1:
        return None
    return subdirs[0]


def detect_candidates(root: Path) -> List[Candidate]:
    """Find flattenable parent/child pairs under root (deepest-first order).

    Heuristic:
    - Parent has exactly one non-hidden child directory and NO non-hidden files.
    - That child contains a result.json (marks an experiment session directory).
    This targets structures like: <parent>/<child>/result.json.
    """
    candidates: List[Candidate] = []
    # Consider all directories under root; deepest-first limits re-traversal impact
    parents = [p for p in root.rglob('*') if p.is_dir()]
    parents.sort(key=lambda p: len(p.parts), reverse=True)

    for parent in parents:
        child = find_single_child(parent)
        if child is None:
            continue
        # Require a sentinel file to ensure it's a session dir
        if not (child / RESULT_FILE).exists():
            continue
        candidates.append(Candidate(parent=parent, child=child))
    return candidates


def flatten_one(parent: Path, child: Path, apply: bool) -> Tuple[Path, Path]:
    """Flatten a single parent/child pair.

    Returns (old_parent, new_parent) for logging.
    """
    grand = parent.parent
    merged_name = f"{parent.name}_{child.name}"
    target_parent = grand / merged_name

    if target_parent.exists():
        raise FileExistsError(
            f"Target directory already exists, won't overwrite: {target_parent}"
        )

    print(f"[PLAN] {parent} + {child.name} -> {target_parent}")
    if not apply:
        return parent, target_parent

    # 1) Rename parent to merged target directory
    parent.rename(target_parent)

    # 2) Move child contents up and remove child dir
    child_in_target = target_parent / child.name
    if not child_in_target.exists() or not child_in_target.is_dir():
        raise FileNotFoundError(
            f"Post-rename child directory not found: {child_in_target}"
        )

    for entry in child_in_target.iterdir():
        dest = target_parent / entry.name
        if dest.exists():
            raise FileExistsError(
                f"Conflict when moving {entry} -> {dest}; aborting to avoid data loss"
            )
        shutil.move(str(entry), str(dest))

    # Remove now-empty child directory
    try:
        child_in_target.rmdir()
    except OSError:
        # If some hidden files remain, remove forcefully
        shutil.rmtree(child_in_target)

    print(f"[OK] Flattened to: {target_parent}")
    return parent, target_parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Flatten OpenRouter model subdirectories (parent_child)")
    ap.add_argument("--root", type=str, default=".", help="Root directory to scan (default: .)")
    ap.add_argument("--apply", action="store_true", help="Actually perform changes (default: dry-run)")
    args = ap.parse_args()

    root = resolve_root(args.root)
    print(f"Root: {root}")
    print("Mode: APPLY" if args.apply else "Mode: DRY-RUN")

    candidates = detect_candidates(root)
    if not candidates:
        print("No flattenable directories found.")
        return

    print(f"Found {len(candidates)} candidate(s):")
    for c in candidates:
        print(f" - {c.parent} -> {c.parent.name}_{c.child.name}")

    # Execute in deepest-first order (already sorted)
    for c in candidates:
        flatten_one(c.parent, c.child, apply=args.apply)

    if not args.apply:
        print("\nThis was a dry-run. Re-run with --apply to make changes.")


if __name__ == "__main__":
    main()
