#!/usr/bin/env python3
"""
Append model suffix to result session folders based on the copied config filename.

Logic:
- In each session directory under --root (default: results), detect the copied config YAML
  (e.g., our_config_4o.yaml or our_config_5.yaml) saved by ResultSaver.
- If config filename starts with our_config_4o → append "_model_gpt4o" to the folder name.
- If config filename starts with our_config_5  → append "_model_gpt5" to the folder name.
- If neither pattern matches, skip the folder.

Idempotent behavior:
- If the folder name already ends with the exact target suffix, skip.
- If target folder name already exists, skip with a warning.

Usage:
  python append_model_suffix.py --root results [--dry-run]
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional


def detect_model_suffix(session_dir: Path) -> Optional[str]:
    """Detect model suffix by scanning for our_config_*.yaml in the session dir.

    Returns the suffix string (e.g., "_model_gpt4o") or None if not determinable.
    """
    # Prefer files starting with our_config_*
    candidates = sorted(session_dir.glob("our_config_*.yaml"))
    if not candidates:
        # Fallback: any single yaml in top-level
        candidates = sorted([p for p in session_dir.glob("*.yaml")])
    if not candidates:
        return None

    cfg_name = candidates[0].name  # pick the first match deterministically
    if cfg_name.startswith("our_config_4o"):
        return "_model_gpt4o"
    if cfg_name.startswith("our_config_5"):
        return "_model_gpt5"
    return None


def append_suffix(session_dir: Path, suffix: str, dry_run: bool = False) -> Optional[str]:
    old_name = session_dir.name
    if old_name.endswith(suffix):
        print(f"[SKIP] Already has model suffix: {old_name}")
        return None
    new_name = old_name + suffix
    new_path = session_dir.parent / new_name
    if new_path.exists():
        print(f"[WARN] Target exists, skip: {new_name}")
        return None
    if dry_run:
        print(f"[DRY-RUN] {old_name} -> {new_name}")
        return new_name
    session_dir.rename(new_path)
    print(f"[RENAMED] {old_name} -> {new_name}")
    return new_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Append model suffix to result folders")
    parser.add_argument("--root", type=str, default="results", help="Results root directory")
    parser.add_argument("--dry-run", action="store_true", help="Show renames without applying")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root directory not found or not a directory: {root}")

    renamed = 0
    skipped = 0
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        # Only process session dirs containing at least one YAML config copy
        has_yaml = any(entry.glob("*.yaml"))
        if not has_yaml:
            continue
        suffix = detect_model_suffix(entry)
        if not suffix:
            print(f"[SKIP] Could not determine model for {entry.name}")
            skipped += 1
            continue
        res = append_suffix(entry, suffix, dry_run=args.dry_run)
        if res is None:
            skipped += 1
        else:
            renamed += 1

    print(f"Done. Renamed={renamed}, Skipped={skipped}")


if __name__ == "__main__":
    main()

