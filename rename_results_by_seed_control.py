#!/usr/bin/env python3
"""
Rename result session folders by appending seed/control suffixes based on stream_info.txt.

Rules (per user spec):
- Always read two lines from each session's stream_info.txt:
    Event Seed: 390185437
    Control Parameters: Category=UNCONTROL, Pressure_Level=UNCONTROL
- If both Category and Pressure_Level are UNCONTROL → append only "_seed{SEED}".
- Otherwise append non-UNCONTROL dimensions as suffixes:
    - If Category != UNCONTROL and != NONE → append "_category_{CATEGORY}"
    - If Pressure_Level != UNCONTROL and != NONE → append "_pressure_{PRESSURE}"
  Always include "_seed{SEED}" at the end. Examples:
    name → name_category_GOAL_CONFLICT_seed390185437
    name → name_pressure_HIGH_seed390185437
    name → name_category_MD_pressure_CRITICAL_seed390185437

Usage:
  python rename_results_by_seed_control.py --root results [--dry-run]

Notes:
- Only directories containing a stream_info.txt are processed.
- Idempotent-ish: if the folder name already ends with the exact target suffix, it will be skipped.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional, Tuple

STREAM_INFO_FILENAME = "stream_info.txt"


def parse_stream_info(info_path: Path) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Extract (seed, category, pressure) from a stream_info.txt file.

    Returns None for fields that cannot be found.
    """
    seed: Optional[int] = None
    category: Optional[str] = None
    pressure: Optional[str] = None

    seed_re = re.compile(r"^\s*Event Seed:\s*(\d+)\s*$", re.IGNORECASE)
    ctrl_re = re.compile(r"^\s*Control Parameters:\s*(.*)$", re.IGNORECASE)
    cat_re = re.compile(r"Category=([^,]+)")
    pres_re = re.compile(r"Pressure_Level=([^,]+)")

    try:
        with info_path.open("r", encoding="utf-8") as f:
            for line in f:
                if seed is None:
                    m = seed_re.match(line)
                    if m:
                        try:
                            seed = int(m.group(1))
                        except ValueError:
                            seed = None
                        continue
                m = ctrl_re.match(line)
                if m:
                    payload = m.group(1).strip()
                    if payload.lower() != "none":
                        cm = cat_re.search(payload)
                        pm = pres_re.search(payload)
                        if cm:
                            category = cm.group(1).strip()
                        if pm:
                            pressure = pm.group(1).strip()
                    else:
                        category = None
                        pressure = None
    except FileNotFoundError:
        return None, None, None

    return seed, category, pressure


def build_suffix(seed: int, category: Optional[str], pressure: Optional[str]) -> str:
    """Build the rename suffix according to the rules."""
    parts = []
    cat_upper = (category or "").upper()
    pres_upper = (pressure or "").upper()

    # Append anything that is controlled (including NONE). Only skip UNCONTROL.
    if cat_upper and cat_upper != "UNCONTROL":
        parts.append(f"_category_{cat_upper}")
    if pres_upper and pres_upper != "UNCONTROL":
        parts.append(f"_pressure_{pres_upper}")

    # seed always appended
    parts.append(f"_seed{seed}")
    return "".join(parts)


def rename_session_dir(session_dir: Path, dry_run: bool = False) -> Optional[Tuple[str, str]]:
    """Rename a single session directory if applicable.

    Returns mapping (old_name, new_name) if renamed, None otherwise.
    """
    info_path = session_dir / STREAM_INFO_FILENAME
    seed, category, pressure = parse_stream_info(info_path)
    if seed is None:
        print(f"[SKIP] No seed found in {info_path}")
        return None

    suffix = build_suffix(seed, category, pressure)
    if not suffix:
        print(f"[SKIP] No suffix to apply for {session_dir.name}")
        return None

    old_name = session_dir.name
    if old_name.endswith(suffix):
        print(f"[SKIP] Already has suffix: {old_name}")
        return None

    new_name = old_name + suffix
    new_path = session_dir.parent / new_name

    if new_path.exists():
        print(f"[WARN] Target exists, skip: {new_name}")
        return None

    if dry_run:
        print(f"[DRY-RUN] {old_name} -> {new_name}")
        return (old_name, new_name)

    session_dir.rename(new_path)
    print(f"[RENAMED] {old_name} -> {new_name}")
    return (old_name, new_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rename results folders with seed/control suffixes")
    parser.add_argument("--root", type=str, default="results", help="Results root directory")
    parser.add_argument("--dry-run", action="store_true", help="Show planned renames without applying")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root directory not found or not a directory: {root}")

    renamed = 0
    skipped = 0
    processed = set()
    # Recursively search for stream_info.txt
    for info_file in sorted(root.rglob(STREAM_INFO_FILENAME)):
        session_dir = info_file.parent
        key = str(session_dir.resolve())
        if key in processed:
            continue
        processed.add(key)
        res = rename_session_dir(session_dir, dry_run=args.dry_run)
        if res is None:
            skipped += 1
        else:
            renamed += 1

    print(f"Done. Renamed={renamed}, Skipped={skipped}")


if __name__ == "__main__":
    main()
