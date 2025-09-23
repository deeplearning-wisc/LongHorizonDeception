#!/usr/bin/env python3
"""
Aggregate only the three detector metrics for a single model directory:
  - deception_rate (mean)
  - severity_average_all_rounds (mean)
  - severity_average_deception_only (mean)

Scans the directory recursively, picks the latest standard detector_*.json per
session (excludes window variants), and computes means across sessions. Writes a
compact JSON with just these three fields.

Usage:
  python aggregate_single_model_min.py <model_dir> [--out summary_min.json]
Example:
  python aggregate_single_model_min.py \
    "/Users/superposition/Desktop/Deception_local/DeceptioN/Results_all_models/GPT5_main_d_gemini"
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DETECTOR_PREFIX = "detector_"
WINDOW_TAG = "detector_window_"
_TS_RE = re.compile(r"^detector_(\d{8})_(\d{6})\.json$")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Aggregate minimal detector metrics for a single model directory")
    ap.add_argument("model_dir", type=str, help="Path to model directory (contains many sessions)")
    ap.add_argument("--out", type=str, default=None, help="Output JSON path (default: <model_dir>/summary_min.json)")
    return ap.parse_args()


def resolve_dir(p: str) -> Path:
    d = Path(p).resolve()
    if not d.exists() or not d.is_dir():
        raise SystemExit(f"Not a directory: {d}")
    return d


def is_standard_detector_file(p: Path) -> bool:
    name = p.name
    if not name.startswith(DETECTOR_PREFIX):
        return False
    if name.startswith(WINDOW_TAG):
        return False
    return _TS_RE.match(name) is not None


def pick_latest_detector(session_dir: Path) -> Optional[Path]:
    cands = [p for p in session_dir.glob("detector_*.json") if is_standard_detector_file(p)]
    if not cands:
        return None
    def key(p: Path) -> Tuple[str, str, float]:
        m = _TS_RE.match(p.name)
        assert m is not None
        return (m.group(1), m.group(2), p.stat().st_mtime)
    cands.sort(key=key, reverse=True)
    return cands[0]


def load_required_three(det_file: Path) -> Tuple[float, float, float]:
    data = json.loads(det_file.read_text(encoding="utf-8"))
    if "summary" not in data or not isinstance(data["summary"], dict):
        raise KeyError(f"Missing/invalid 'summary' in {det_file}")
    s = data["summary"]
    required = [
        "deception_rate",
        "severity_average_all_rounds",
        "severity_average_deception_only",
    ]
    for k in required:
        if k not in s:
            raise KeyError(f"Missing summary.{k} in {det_file}")
        if not isinstance(s[k], (int, float)):
            raise TypeError(f"summary.{k} must be numeric in {det_file}")
    return float(s["deception_rate"]), float(s["severity_average_all_rounds"]), float(s["severity_average_deception_only"])


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else 0.0


def aggregate_min(model_dir: Path) -> Dict[str, float]:
    # latest detector per session
    latest: Dict[Path, Path] = {}
    for det in model_dir.rglob("detector_*.json"):
        if not is_standard_detector_file(det):
            continue
        sdir = det.parent
        latest_det = pick_latest_detector(sdir)
        if latest_det and latest_det == det:
            latest[sdir] = det
    if not latest:
        raise SystemExit(f"No sessions with detector_*.json under {model_dir}")

    drs: List[float] = []
    saas: List[float] = []
    sads: List[float] = []
    for sdir, det_file in latest.items():
        dr, saa, sad = load_required_three(det_file)
        drs.append(dr)
        saas.append(saa)
        sads.append(sad)

    return {
        "deception_rate": mean(drs),
        "severity_average_all_rounds": mean(saas),
        "severity_average_deception_only": mean(sads),
    }


def main() -> None:
    args = parse_args()
    model_dir = resolve_dir(args.model_dir)
    outp = Path(args.out).resolve() if args.out else (model_dir / "summary_min.json")
    out = aggregate_min(model_dir)
    outp.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote minimal summary: {outp}")


if __name__ == "__main__":
    main()

