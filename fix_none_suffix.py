#!/usr/bin/env python3
"""
Recursively fix session folder names that should include NONE control suffixes.

Context: Prior renames mostly succeeded, but cases where Control Parameters contain
NONE (Category=NONE and/or Pressure_Level=NONE) were not appended. This script
adds ONLY the missing NONE suffixes and does not change anything else.

Rules:
- Look for stream_info.txt under the provided root (recursively).
- Read:
    Event Seed: 390185437
    Control Parameters: Category=UNCONTROL, Pressure_Level=NONE
- If Category=NONE and folder name does not contain "_category_NONE", add it.
- If Pressure_Level=NONE and folder name does not contain "_pressure_NONE", add it.
- Preserve existing suffixes and always keep the seed suffix at the end if present.
  That is, if the name ends with "_seed<SEED>", insert NONE suffixes just before the seed.
- If the seed suffix is not present, append NONE suffixes at the end.
- Do NOT add any non-NONE suffixes; ignore UNCONTROL and any other values.

Usage:
  python fix_none_suffix.py --root Results_checked [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional, Tuple, List

STREAM_INFO_FILENAME = "stream_info.txt"


def parse_stream_info(info_path: Path) -> Tuple[Optional[int], Optional[str], Optional[str]]:
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


def compute_new_name(name: str, seed: Optional[int], need_cat: bool, need_pres: bool) -> Optional[str]:
    if not (need_cat or need_pres):
        return None

    # Determine seed suffix positioning
    seed_suffix = f"_seed{seed}" if seed is not None else None
    parts_to_insert: List[str] = []
    if need_cat:
        parts_to_insert.append("_category_NONE")
    if need_pres:
        parts_to_insert.append("_pressure_NONE")

    if seed_suffix and name.endswith(seed_suffix):
        base = name[:-len(seed_suffix)]
        return base + "".join(parts_to_insert) + seed_suffix
    else:
        return name + "".join(parts_to_insert)


def main() -> None:
    parser = argparse.ArgumentParser(description="Append missing NONE control suffixes to session folders")
    parser.add_argument("--root", type=str, default="Results_checked", help="Root directory to search recursively")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without renaming")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root directory not found or not a directory: {root}")

    renamed = 0
    skipped = 0
    for info_file in sorted(root.rglob(STREAM_INFO_FILENAME)):
        session_dir = info_file.parent
        seed, category, pressure = parse_stream_info(info_file)
        if seed is None and category is None and pressure is None:
            skipped += 1
            continue
        name = session_dir.name
        # Determine if NONE suffixes are needed (and not already present)
        need_cat = (category or "").upper() == "NONE" and ("_category_NONE" not in name)
        need_pres = (pressure or "").upper() == "NONE" and ("_pressure_NONE" not in name)
        if not (need_cat or need_pres):
            skipped += 1
            continue

        new_name = compute_new_name(name, seed, need_cat, need_pres)
        if not new_name or new_name == name:
            skipped += 1
            continue

        new_path = session_dir.parent / new_name
        if new_path.exists():
            print(f"[WARN] Target exists, skip: {session_dir.name} -> {new_name}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"[DRY-RUN] {session_dir.name} -> {new_name}")
            renamed += 1
            continue

        session_dir.rename(new_path)
        print(f"[RENAMED] {session_dir.name} -> {new_name}")
        renamed += 1

    print(f"Done. Renamed={renamed}, Skipped={skipped}")


if __name__ == "__main__":
    main()

