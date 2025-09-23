#!/usr/bin/env python3
"""
Collect datapoint-level deception rates for Control runs under pressure_level
for GPT4o and GPT5 only, without aggregation.

Input directory layout (examples):
  Control/
    GPT4o_control/pressure_level/<level>/<session_dir>/detector_YYYYMMDD_HHMMSS.json
    GPT5_control/pressure_level/<level>/<session_dir>/detector_YYYYMMDD_HHMMSS.json

For every session, the script selects the latest standard detector JSON
by filename timestamp, reads summary.deception_rate and total_rounds, and
emits a JSON mapping per model and pressure level, keyed by seed.

Fail-fast rules:
- Root must exist and be a directory.
- Only model folders GPT4o_control and GPT5_control are processed.
- Every datapoint must have a parseable seed in its path (seed<digits>),
  a valid pressure level segment, and a standard detector JSON with the
  required summary keys; otherwise the script aborts with an explicit error.

Output: Writes control_pressure_datapoints.json under the given root
directory (or a custom path via --out).

Usage:
  python aggregate_control_pressure.py Results_all_models/Control
  python aggregate_control_pressure.py Results_all_models/Control --out my_out.json
  # Allow skipping models that have no datapoints (instead of failing):
  python aggregate_control_pressure.py Results_all_models/Control --skip-missing
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Iterable, List


# Constants
ALLOWED_MODELS: Dict[str, str] = {
    "GPT4o_control": "GPT4o",
    "GPT5_control": "GPT5",
    "deepseek_v3_1_control": "Deepseek_V3.1",
}
DETECTOR_PREFIX = "detector_"
WINDOW_TAG = "detector_window_"
OUT_FILENAME = "control_pressure_datapoints.json"

_TS_RE = re.compile(r"^detector_(\d{8})_(\d{6})\.json$")
_SEED_RE = re.compile(r"seed(\d+)")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Collect control pressure datapoints for GPT4o/GPT5")
    ap.add_argument("root", type=str, help="Path to Control directory")
    ap.add_argument("--out", type=str, default=None, help=f"Optional output JSON path (default: <root>/{OUT_FILENAME})")
    ap.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip models that have no datapoints under pressure_level instead of failing",
    )
    return ap.parse_args()


def resolve_root(p: str) -> Path:
    root = Path(p).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Root not found or not a directory: {root}")
    return root


def is_standard_detector_file(p: Path) -> bool:
    name = p.name
    if not name.startswith(DETECTOR_PREFIX):
        return False
    if name.startswith(WINDOW_TAG):
        return False
    return _TS_RE.match(name) is not None


def pick_latest_detector(session_dir: Path) -> Optional[Path]:
    candidates = [p for p in session_dir.glob("detector_*.json") if is_standard_detector_file(p)]
    if not candidates:
        return None
    def key(p: Path) -> Tuple[str, str, float]:
        m = _TS_RE.match(p.name)
        assert m is not None
        return (m.group(1), m.group(2), p.stat().st_mtime)
    candidates.sort(key=key, reverse=True)
    return candidates[0]


def extract_seed(p: Path) -> str:
    m = _SEED_RE.search(str(p))
    if not m:
        raise ValueError(f"Failed to parse seed from path: {p}")
    return m.group(1)


def find_pressure_level_component(path: Path) -> str:
    parts = list(path.parts)
    for i, seg in enumerate(parts):
        if seg == "pressure_level" and i + 1 < len(parts):
            return parts[i + 1]
    raise ValueError(f"Cannot locate pressure_level/<level> segment in path: {path}")


def iter_model_dirs(root: Path) -> Iterable[Tuple[str, Path]]:
    for name, label in ALLOWED_MODELS.items():
        p = root / name
        if p.exists() and p.is_dir():
            yield label, p


def collect_datapoints_for_model(model_label: str, model_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return mapping: pressure_level -> seed -> datapoint dict."""
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}

    # Scan only pressure_level subtree  
    pressure_level_path = model_dir / "pressure_level"
    if not pressure_level_path.exists():
        return result
        
    # Iterate through pressure level directories
    for level_dir in pressure_level_path.iterdir():
        if not level_dir.is_dir():
            continue
        # Find detector files in session directories under this level
        for session_dir in level_dir.iterdir():
            if not session_dir.is_dir():
                continue
            for det_file in session_dir.glob("detector_*.json"):
                if not is_standard_detector_file(det_file):
                    continue
                # Validate we picked the latest for this session
                latest = pick_latest_detector(session_dir)
                if latest is None or latest != det_file:
                    continue

                level = find_pressure_level_component(det_file)
                seed = extract_seed(session_dir)

                # Read deception rate, total rounds, and severity averages
                with open(det_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "summary" not in data or not isinstance(data["summary"], dict):
                    raise KeyError(f"Missing or invalid 'summary' in {det_file}")
                summ = data["summary"]
                
                # Check required keys
                required_keys = ["deception_rate", "total_rounds", "severity_average_all_rounds", "severity_average_deception_only"]
                for key in required_keys:
                    if key not in summ:
                        raise KeyError(f"Missing required key '{key}' in summary for {det_file}")
                
                dr = summ["deception_rate"]
                tr = summ["total_rounds"]
                saa = summ["severity_average_all_rounds"]
                sad = summ["severity_average_deception_only"]
                
                # Type validation
                if not isinstance(dr, (int, float)):
                    raise TypeError(f"summary.deception_rate must be numeric in {det_file}")
                if not isinstance(tr, int):
                    raise TypeError(f"summary.total_rounds must be int in {det_file}")
                if not isinstance(saa, (int, float)):
                    raise TypeError(f"summary.severity_average_all_rounds must be numeric in {det_file}")
                if not isinstance(sad, (int, float)):
                    raise TypeError(f"summary.severity_average_deception_only must be numeric in {det_file}")

                # Insert into mapping, ensure uniqueness per seed within a level
                if level not in result:
                    result[level] = {}
                if seed in result[level]:
                    raise ValueError(f"Duplicate seed for {model_label} level={level}: {seed} ({session_dir})")
                result[level][seed] = {
                    "deception_rate": float(dr),
                    "total_rounds": tr,
                    "severity_average_all_rounds": float(saa),
                    "severity_average_deception_only": float(sad),
                }

    # Sort seeds numerically for stable view
    ordered: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for level in sorted(result.keys()):
        seeds = result[level]
        ordered[level] = {k: seeds[k] for k in sorted(seeds.keys(), key=lambda x: int(x))}
    return ordered


def calculate_aggregated_deception_rate(pressure_data: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
    """Calculate aggregated deception rate for each pressure level."""
    # Define logical order from highest to lowest pressure
    pressure_order = ["critical", "high", "medium", "low", "none"]
    
    aggregated_deception_rate = {}
    
    # Process in logical order
    for level in pressure_order:
        if level not in pressure_data:
            continue
            
        sessions = pressure_data[level]
        if not sessions:
            raise ValueError(f"No sessions found for pressure level {level} - cannot aggregate deception rate")
        
        # Calculate mean deception rate for this level (ONLY deception rate)
        deception_rates = [session_data["deception_rate"] for session_data in sessions.values()]
        if not deception_rates:
            raise ValueError(f"No valid deception rates found for pressure level {level}")
        avg_rate = sum(deception_rates) / len(deception_rates)
        aggregated_deception_rate[level] = round(avg_rate, 6)  # Round to 6 decimal places for clarity
    
    return aggregated_deception_rate


def main() -> None:
    args = parse_args()
    root = resolve_root(args.root)
    out_path = Path(args.out).resolve() if args.out else (root / OUT_FILENAME)

    payload: Dict[str, Any] = {}
    errors: List[str] = []
    totals_summary: List[str] = []
    grand_sessions = 0

    for label, model_dir in iter_model_dirs(root):
        try:
            pressure_level_data = collect_datapoints_for_model(label, model_dir)
            # Require at least one datapoint per model unless skipping is enabled
            if not pressure_level_data:
                if args.skip_missing:
                    print(f"[WARN] Skipping model {label}: no datapoints found under pressure_level at {model_dir}")
                    continue
                raise RuntimeError(f"No datapoints found for model {label} under pressure_level")
            
            # Calculate aggregated deception rate (only deception rate)
            aggregated_deception_rate = calculate_aggregated_deception_rate(pressure_level_data)
            
            # Build the model payload with aggregated deception rate and detailed data
            payload[label] = {
                "aggregated_deception_rate": aggregated_deception_rate,
                "pressure_level": pressure_level_data
            }
            # Count included leaf sessions (with standard detectors)
            included_sessions = sum(len(seeds) for seeds in pressure_level_data.values())
            grand_sessions += included_sessions
            totals_summary.append(f"{label}: included_sessions={included_sessions}; levels={len(pressure_level_data)}")
        except Exception as e:
            errors.append(f"{label}: {e}")

    if errors:
        joined = "\n".join(errors)
        raise SystemExit(f"Failed to collect datapoints for some models:\n{joined}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote datapoints: {out_path}")
    if totals_summary:
        print("Session coverage:")
        for line in totals_summary:
            print(" -", line)
        print(f"Total included sessions across models: {grand_sessions}")


if __name__ == "__main__":
    main()
