#!/usr/bin/env python3
"""
Aggregate detector metrics by model from a Main directory.

Input: Path to a Main directory whose immediate subdirectories are model groups
(e.g., gemini_main, grok4_main, ...). For each model directory, recursively
find experiment sessions that contain standard detector result files named like
"detector_YYYYMMDD_HHMMSS.json" (explicitly excluding any windowed variants
such as "detector_window_*").

For each model, collect the three metrics from each selected detector file:
  - summary.deception_rate
  - summary.severity_average_all_rounds
  - summary.severity_average_deception_only

Then compute the mean and standard error (stderr = sample_std / sqrt(n), using
ddof=1). If n < 2, stderr is null. If any model directory has zero detector
results, the script fails (as requested) with a clear error message.

Output: Writes a JSON file named "summary_by_model.json" into the provided
Main directory by default (can override with --out).

Usage:
  python aggregate_models_main.py Results_all_models/Main
  python aggregate_models_main.py Results_all_models/Main --out summary_by_model.json
  python aggregate_models_main.py Results_all_models/Main --precision 3
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Constants
DETECTOR_PREFIX: str = "detector_"
WINDOW_TAG: str = "detector_window_"
SUMMARY_FILENAME: str = "summary_by_model.json"


@dataclass(frozen=True)
class DetectorPick:
    session_dir: Path
    detector_file: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate detector metrics by model from a Main directory"
    )
    parser.add_argument(
        "main_dir",
        type=str,
        help="Path to Main directory (contains model subdirectories)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional output JSON path; defaults to <main_dir>/summary_by_model.json",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=3,
        help="Decimal places for formatted mean ± stderr (default: 3; range 0-6)",
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip model directories that fail aggregation (default: fail-fast)",
    )
    return parser.parse_args()


def resolve_main_dir(p: str) -> Path:
    main = Path(p).resolve()
    if not main.exists() or not main.is_dir():
        raise FileNotFoundError(f"Main directory not found or not a directory: {main}")
    return main


def iter_model_dirs(main_dir: Path) -> Iterable[Path]:
    for child in main_dir.iterdir():
        if child.is_dir():
            yield child


_TS_RE = re.compile(r"^detector_(\d{8})_(\d{6})\.json$")


def is_standard_detector_file(p: Path) -> bool:
    name = p.name
    if not name.startswith(DETECTOR_PREFIX):
        return False
    if name.startswith(WINDOW_TAG):
        return False
    return _TS_RE.match(name) is not None


def pick_latest_detector(session_dir: Path) -> Optional[Path]:
    """Pick the latest standard detector_*.json in a session directory.

    Returns the Path or None if none found.
    """
    candidates = [p for p in session_dir.glob("detector_*.json") if is_standard_detector_file(p)]
    if not candidates:
        return None
    # Sort by timestamp embedded in filename; if equal, fall back to mtime
    def key(p: Path) -> Tuple[str, str, float]:
        m = _TS_RE.match(p.name)
        assert m is not None
        return (m.group(1), m.group(2), p.stat().st_mtime)

    candidates.sort(key=key, reverse=True)
    return candidates[0]


# Seed parsing: must find seed<digits> in path; otherwise error
_SEED_RE = re.compile(r"seed(\d+)")


def extract_seed_from_path(p: Path) -> str:
    """Extract numeric seed string from path. Fail if not found."""
    m = _SEED_RE.search(str(p))
    if not m:
        raise ValueError(f"Failed to parse seed from path: {p}")
    return m.group(1)


def load_analysis_metrics(session_dir: Path) -> Tuple[float, float, float]:
    """Load final_trust, final_relational_comfort, average_work_satisfaction from latest analysis.

    Strict: must read from analysis_*/analysis_results.json; no fallback allowed.
    """
    analysis_dirs = [d for d in session_dir.glob("analysis_*") if d.is_dir()]
    if not analysis_dirs:
        raise FileNotFoundError(f"No analysis_* directory found in {session_dir}. Run analyzer.py first.")
    # Prefer lexicographically latest by name (timestamped)
    latest = max(analysis_dirs, key=lambda d: d.name)
    analysis_file = latest / "analysis_results.json"
    if not analysis_file.exists():
        raise FileNotFoundError(f"analysis_results.json not found in {latest}")
    with open(analysis_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    ft = data["final_trust_level"]
    rc = data["final_relational_comfort"]
    aws = data["average_work_satisfaction"]
    if not isinstance(ft, (int, float)):
        raise TypeError(f"final_trust_level must be numeric in {analysis_file}")
    if not isinstance(rc, (int, float)):
        raise TypeError(f"final_relational_comfort must be numeric in {analysis_file}")
    if not isinstance(aws, (int, float)):
        raise TypeError(f"average_work_satisfaction must be numeric in {analysis_file}")
    # Preserve floating-point resolution; casting to int here truncates values in (-1,1) to 0.
    return float(ft), float(rc), float(aws)


def collect_session_picks(model_dir: Path) -> List[DetectorPick]:
    """Find all session directories under model_dir and pick one detector per session.

    A session directory is any directory that directly contains at least one
    standard detector_*.json (windowed variants excluded).
    """
    picks: List[DetectorPick] = []
    for detector_file in model_dir.rglob("detector_*.json"):
        if not is_standard_detector_file(detector_file):
            continue
        session_dir = detector_file.parent
        # Ensure we only add the latest per session
        latest = pick_latest_detector(session_dir)
        if latest is None:
            continue
        if latest != detector_file:
            continue  # not the latest in this session
        picks.append(DetectorPick(session_dir=session_dir, detector_file=latest))

    # Deduplicate in case of overlapping rglob matches
    unique: Dict[Path, DetectorPick] = {}
    for p in picks:
        unique[p.session_dir] = p
    return list(unique.values())


def load_required_metrics(detector_file: Path) -> Tuple[float, float, float, int]:
    with open(detector_file, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    if "summary" not in data:
        raise KeyError(f"Missing required key 'summary' in {detector_file}")
    summary = data["summary"]
    if not isinstance(summary, dict):
        raise TypeError(f"'summary' must be an object in {detector_file}")

    # Strict access: validate presence and type
    if "deception_rate" not in summary:
        raise KeyError(f"Missing 'summary.deception_rate' in {detector_file}")
    if "severity_average_all_rounds" not in summary:
        raise KeyError(f"Missing 'summary.severity_average_all_rounds' in {detector_file}")
    if "severity_average_deception_only" not in summary:
        raise KeyError(f"Missing 'summary.severity_average_deception_only' in {detector_file}")
    if "total_rounds" not in summary:
        raise KeyError(f"Missing 'summary.total_rounds' in {detector_file}")

    dr = summary["deception_rate"]
    saa = summary["severity_average_all_rounds"]
    sad = summary["severity_average_deception_only"]
    tr = summary["total_rounds"]
    for v, k in ((dr, "deception_rate"), (saa, "severity_average_all_rounds"), (sad, "severity_average_deception_only")):
        if not isinstance(v, (int, float)):
            raise TypeError(f"summary.{k} must be numeric in {detector_file}")
    if not isinstance(tr, int):
        raise TypeError(f"summary.total_rounds must be an int in {detector_file}")

    return float(dr), float(saa), float(sad), tr


def mean(values: List[float]) -> float:
    if not values:
        raise ValueError("mean() of empty list")
    return sum(values) / float(len(values))


def stderr(values: List[float]) -> Optional[float]:
    n = len(values)
    if n < 2:
        return None
    mu = mean(values)
    var = sum((x - mu) ** 2 for x in values) / (n - 1)
    sd = math.sqrt(var)
    return sd / math.sqrt(n)


def _format_mean_stderr(mu: float, se: Optional[float], precision: int) -> str:
    if se is None:
        return f"{mu:.{precision}f} ± n/a"
    return f"{mu:.{precision}f} ± {se:.{precision}f}"


def aggregate_model(model_dir: Path, precision: int) -> Tuple[Dict[str, Any], Dict[str, Any], List[float], List[float], List[float]]:
    picks = collect_session_picks(model_dir)
    if not picks:
        raise RuntimeError(f"FATAL: No standard detector files found under model directory: {model_dir}")

    drs: List[float] = []
    saas: List[float] = []
    sads: List[float] = []
    interaction_lengths: List[int] = []
    per_seed: Dict[str, Any] = {}
    # Per-model cumulative type counts
    model_type_counts: Dict[str, int] = {"FALSIFICATION": 0, "CONCEALMENT": 0, "EQUIVOCATION": 0}

    for pick in picks:
        dr, saa, sad, tr = load_required_metrics(pick.detector_file)
        # Strict seed and analysis requirements
        seed = extract_seed_from_path(pick.session_dir)
        ft, rc, aws = load_analysis_metrics(pick.session_dir)

        # Open detector summary to fetch type_counts
        with open(pick.detector_file, "r", encoding="utf-8") as f:
            det_data = json.load(f)
        summary = det_data["summary"]
        tc = summary.get("type_counts")
        if not isinstance(tc, dict):
            raise TypeError(f"summary.type_counts must be an object in {pick.detector_file}")
        # Accumulate per-model totals
        for k in ("FALSIFICATION", "CONCEALMENT", "EQUIVOCATION"):
            if k in tc:
                model_type_counts[k] += int(tc[k])

        if seed in per_seed:
            raise ValueError(f"Duplicate seed within model {model_dir.name}: {seed}")
        per_seed[seed] = {
            "final_trust_level": ft,
            "final_relational_comfort": rc,
            "average_work_satisfaction": aws,
            "interaction_len": tr,
            "deception_rate": dr,
            "severity_average_all_rounds": saa,
            "severity_average_deception_only": sad,
            "type_counts": tc,
        }

        drs.append(dr)
        saas.append(saa)
        sads.append(sad)
        interaction_lengths.append(tr)

    mu_dr, se_dr = mean(drs), stderr(drs)
    mu_saa, se_saa = mean(saas), stderr(saas)
    mu_sad, se_sad = mean(sads), stderr(sads)

    # Compute internal composition percentages for type counts
    total_types = sum(int(model_type_counts.get(k, 0)) for k in ("FALSIFICATION", "CONCEALMENT", "EQUIVOCATION"))
    if total_types > 0:
        type_percentages_total = {
            "FALSIFICATION": model_type_counts.get("FALSIFICATION", 0) / total_types,
            "CONCEALMENT": model_type_counts.get("CONCEALMENT", 0) / total_types,
            "EQUIVOCATION": model_type_counts.get("EQUIVOCATION", 0) / total_types,
        }
    else:
        type_percentages_total = {"FALSIFICATION": 0.0, "CONCEALMENT": 0.0, "EQUIVOCATION": 0.0}

    result = {
        "n_sessions": len(picks),
        "deception_rate": {
            "mean": mu_dr,
            "stderr": se_dr,
            "formatted": _format_mean_stderr(mu_dr, se_dr, precision),
        },
        "severity_average_all_rounds": {
            "mean": mu_saa,
            "stderr": se_saa,
            "formatted": _format_mean_stderr(mu_saa, se_saa, precision),
        },
        "severity_average_deception_only": {
            "mean": mu_sad,
            "stderr": se_sad,
            "formatted": _format_mean_stderr(mu_sad, se_sad, precision),
        },
        "type_counts_total": model_type_counts,
        "type_percentages_total": type_percentages_total,
    }
    return result, per_seed, drs, saas, sads


def main() -> None:
    args = parse_args()
    main_dir = resolve_main_dir(args.main_dir)
    out_path = Path(args.out).resolve() if args.out else (main_dir / SUMMARY_FILENAME)
    # Validate precision
    if not (0 <= args.precision <= 6):
        raise SystemExit("--precision must be between 0 and 6")

    models: Dict[str, Any] = {}
    errors: List[str] = []

    for model_dir in iter_model_dirs(main_dir):
        try:
            agg, per_seed, _drs, _saas, _sads = aggregate_model(model_dir, precision=args.precision)
            # Order seeds numerically for stable viewing
            ordered: Dict[str, Any] = {}
            for seed in sorted(per_seed.keys(), key=lambda x: int(x)):
                ordered[seed] = per_seed[seed]
            # Nest structure per model
            models[model_dir.name] = {
                "aggregated": agg,
                "datapoint_level": ordered,
            }
        except Exception as e:
            errors.append(f"{model_dir.name}: {e}")

    if errors:
        joined = "\n".join(errors)
        if not args.skip_missing:
            # Fail-fast if any model directory lacks detector results or errors out
            raise SystemExit(f"One or more model directories failed to aggregate:\n{joined}")
        else:
            print("[WARN] Skipping the following model directories due to errors:")
            print(joined)

    payload = models
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote summary: {out_path}")


if __name__ == "__main__":
    main()
