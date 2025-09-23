#!/usr/bin/env python3
"""
Collect datapoint-level deception rates for Control runs under p_event
for GPT4o and GPT5 only, without aggregation.

Input directory layout (examples):
  Control/
    GPT4o_control/p_event/<p_value>/<session_dir>/detector_YYYYMMDD_HHMMSS.json
    GPT5_control/p_event/<p_value>/<session_dir>/detector_YYYYMMDD_HHMMSS.json

For every session, the script selects the latest standard detector JSON
by filename timestamp, reads summary.deception_rate, total_rounds,
severity averages, and emits a JSON mapping per model 
and p_event value, keyed by seed.

Fail-fast rules:
- Root must exist and be a directory.
- Only model folders GPT4o_control and GPT5_control are processed.
- Every datapoint must have a parseable seed in its path (seed<digits>),
  a valid p_event value segment, and a standard detector JSON with the
  required summary keys; otherwise the script aborts with an explicit error.

Output: Writes control_p_event_datapoints.json under the given root
directory (or a custom path via --out).

Usage:
  python aggregate_control_p_event.py Results_all_models/Control
  python aggregate_control_p_event.py Results_all_models/Control --out my_out.json
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
OUT_FILENAME = "control_p_event_datapoints.json"

_TS_RE = re.compile(r"^detector_(\d{8})_(\d{6})\.json$")
_SEED_RE = re.compile(r"seed(\d+)")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Collect control p_event datapoints for GPT4o/GPT5")
    ap.add_argument("root", type=str, help="Path to Control directory")
    ap.add_argument("--out", type=str, default=None, help=f"Optional output JSON path (default: <root>/{OUT_FILENAME})")
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


def find_p_event_component(path: Path) -> str:
    parts = list(path.parts)
    for i, seg in enumerate(parts):
        if seg == "p_event" and i + 1 < len(parts):
            p_value = parts[i + 1]
            # Validate that it's a valid p_event value (0.1, 0.3, 0.5, 0.7, 0.9)
            if p_value not in ["0.1", "0.3", "0.5", "0.7", "0.9"]:
                raise ValueError(f"Invalid p_event value: {p_value}. Expected one of: 0.1, 0.3, 0.5, 0.7, 0.9")
            return p_value
    raise ValueError(f"Cannot locate p_event/<p_value> segment in path: {path}")


def iter_model_dirs(root: Path) -> Iterable[Tuple[str, Path]]:
    for name, label in ALLOWED_MODELS.items():
        p = root / name
        if p.exists() and p.is_dir():
            yield label, p


def collect_datapoints_for_model(model_label: str, model_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return mapping: p_event_value -> seed -> datapoint dict."""
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}

    # Scan only p_event subtree  
    p_event_path = model_dir / "p_event"
    if not p_event_path.exists():
        return result
        
    # Iterate through p_event directories
    for p_value_dir in p_event_path.iterdir():
        if not p_value_dir.is_dir():
            continue
        # Find detector files in session directories under this p_event value
        for session_dir in p_value_dir.iterdir():
            if not session_dir.is_dir():
                continue
            for det_file in session_dir.glob("detector_*.json"):
                if not is_standard_detector_file(det_file):
                    continue
                # Validate we picked the latest for this session
                latest = pick_latest_detector(session_dir)
                if latest is None or latest != det_file:
                    continue

                p_value = find_p_event_component(det_file)
                seed = extract_seed(session_dir)

                # Read deception rate, total rounds, and severity averages
                with open(det_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "summary" not in data or not isinstance(data["summary"], dict):
                    raise KeyError(f"Missing or invalid 'summary' in {det_file}")
                summ = data["summary"]
                
                # Check required keys
                required_keys = ["deception_rate", "total_rounds", "severity_average_all_rounds", 
                               "severity_average_deception_only"]
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

                # Insert into mapping, ensure uniqueness per seed within a p_event value
                if p_value not in result:
                    result[p_value] = {}
                if seed in result[p_value]:
                    raise ValueError(f"Duplicate seed for {model_label} p_event={p_value}: {seed} ({session_dir})")
                result[p_value][seed] = {
                    "deception_rate": float(dr),
                    "total_rounds": tr,
                    "severity_average_all_rounds": float(saa),
                    "severity_average_deception_only": float(sad),
                }

    # Sort seeds numerically for stable view, and sort p_event values numerically
    ordered: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for p_value in sorted(result.keys(), key=lambda x: float(x)):
        seeds = result[p_value]
        ordered[p_value] = {k: seeds[k] for k in sorted(seeds.keys(), key=lambda x: int(x))}
    return ordered


def calculate_aggregated_deception_rate(p_event_data: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
    """Calculate aggregated deception rate for each p_event value."""
    # Define logical order from lowest to highest probability
    p_event_order = ["0.1", "0.3", "0.5", "0.7", "0.9"]
    
    aggregated_deception_rate = {}
    
    # Process in logical order
    for p_value in p_event_order:
        if p_value not in p_event_data:
            continue
            
        sessions = p_event_data[p_value]
        if not sessions:
            aggregated_deception_rate[p_value] = 0.0
            continue
        
        # Calculate mean deception rate for this p_event value (ONLY deception rate)
        deception_rates = [session_data["deception_rate"] for session_data in sessions.values()]
        avg_rate = sum(deception_rates) / len(deception_rates) if deception_rates else 0.0
        aggregated_deception_rate[p_value] = round(avg_rate, 6)  # Round to 6 decimal places for clarity
    
    return aggregated_deception_rate


def main() -> None:
    args = parse_args()
    root = resolve_root(args.root)
    out_path = Path(args.out).resolve() if args.out else (root / OUT_FILENAME)

    payload: Dict[str, Any] = {}
    errors: List[str] = []

    for label, model_dir in iter_model_dirs(root):
        try:
            p_event_data = collect_datapoints_for_model(label, model_dir)
            # Require at least one datapoint per model
            if not p_event_data:
                raise RuntimeError(f"No datapoints found for model {label} under p_event")
            
            # Calculate aggregated deception rate (only deception rate)
            aggregated_deception_rate = calculate_aggregated_deception_rate(p_event_data)
            
            # Build the model payload with aggregated deception rate and detailed data
            payload[label] = {
                "aggregated_deception_rate": aggregated_deception_rate,
                "p_event": p_event_data
            }
        except Exception as e:
            errors.append(f"{label}: {e}")

    if errors:
        joined = "\n".join(errors)
        raise SystemExit(f"Failed to collect datapoints for some models:\n{joined}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote datapoints: {out_path}")


if __name__ == "__main__":
    main()
