#!/usr/bin/env python3
"""
Aggregate detector metrics for a single model directory, similar to the
structure under Results_all_models/Main/summary_by_model.json (per model).

Input: a model directory (e.g., Results_all_models/GPT5_main_d_gemini)
containing many session subfolders, each with detector_*.json (standard, not
window) and analysis_*/analysis_results.json produced by analyzer.py.

Output: Writes <model_dir>/summary.json with this structure:
{
  "aggregated": {
    "n_sessions": N,
    "deception_rate": {"mean": x, "stderr": y, "formatted": "x.xxx ± y.yyy"},
    "severity_average_all_rounds": {...},
    "severity_average_deception_only": {...},
    "type_counts_total": {"FALSIFICATION": a, "CONCEALMENT": b, "EQUIVOCATION": c},
    "type_percentages_total": {...}
  },
  "datapoint_level": {
     "<seed>": {
        "final_trust_level": ..., "final_relational_comfort": ...,
        "average_work_satisfaction": ..., "interaction_len": ...,
        "deception_rate": ..., "severity_average_all_rounds": ...,
        "severity_average_deception_only": ..., "type_counts": {...}
     },
     ...
  }
}

Fail-fast rules:
- Each session must contain a standard detector_*.json (latest picked per session)
- Each session must have analysis_*/analysis_results.json
- Seeds are extracted from session path (seed<digits>); missing seed → error

Usage:
  python aggregate_single_model.py <model_dir> [--precision 3]
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DETECTOR_PREFIX = "detector_"
WINDOW_TAG = "detector_window_"

_TS_RE = re.compile(r"^detector_(\d{8})_(\d{6})\.json$")
_SEED_RE = re.compile(r"seed(\d+)")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Aggregate metrics for a single model directory")
    ap.add_argument("model_dir", type=str, help="Path to a model directory (contains session subfolders)")
    ap.add_argument("--precision", type=int, default=3, help="Decimal places for formatted mean ± stderr")
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


def extract_seed(session_dir: Path) -> str:
    m = _SEED_RE.search(str(session_dir))
    if not m:
        raise ValueError(f"Failed to parse seed from path: {session_dir}")
    return m.group(1)


def load_detector_summary(det_file: Path) -> Dict[str, Any]:
    data = json.loads(det_file.read_text(encoding="utf-8"))
    if "summary" not in data or not isinstance(data["summary"], dict):
        raise KeyError(f"Missing/invalid 'summary' in {det_file}")
    s = data["summary"]
    required = [
        "deception_rate",
        "severity_average_all_rounds",
        "severity_average_deception_only",
        "total_rounds",
    ]
    for k in required:
        if k not in s:
            raise KeyError(f"Missing summary.{k} in {det_file}")
    if not isinstance(s["total_rounds"], int):
        raise TypeError(f"summary.total_rounds must be int in {det_file}")
    return s


def load_analysis_metrics(session_dir: Path) -> Tuple[float, float, float]:
    # Find latest analysis_*/analysis_results.json (by mtime)
    analysis_dirs = sorted([d for d in session_dir.glob("analysis_*") if d.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    if not analysis_dirs:
        raise FileNotFoundError(f"No analysis_* under {session_dir}")
    ar = analysis_dirs[0] / "analysis_results.json"
    if not ar.exists():
        raise FileNotFoundError(f"analysis_results.json not found: {ar}")
    a = json.loads(ar.read_text(encoding="utf-8"))
    for k in ("final_trust_level", "final_relational_comfort", "average_work_satisfaction"):
        if k not in a:
            raise KeyError(f"Missing {k} in {ar}")
    return float(a["final_trust_level"]), float(a["final_relational_comfort"]), float(a["average_work_satisfaction"])


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else 0.0


def stderr(xs: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mu = mean(xs)
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)
    return math.sqrt(var) / math.sqrt(n)


def fmt(mu: float, se: Optional[float], p: int) -> str:
    return f"{mu:.{p}f} ± {se:.{p}f}" if se is not None else f"{mu:.{p}f} ± n/a"


def aggregate(model_dir: Path, precision: int) -> Dict[str, Any]:
    # Map latest detector per session
    picks: List[Tuple[Path, Path]] = []  # (session_dir, det_file)
    for det_file in model_dir.rglob("detector_*.json"):
        if not is_standard_detector_file(det_file):
            continue
        sdir = det_file.parent
        latest = pick_latest_detector(sdir)
        if latest and latest == det_file:
            picks.append((sdir, det_file))

    # Deduplicate by session_dir
    uniq: Dict[Path, Path] = {}
    for sdir, df in picks:
        uniq[sdir] = df
    picks2 = list(uniq.items())
    if not picks2:
        raise SystemExit(f"No sessions with detector_*.json under {model_dir}")

    drs: List[float] = []
    saas: List[float] = []
    sads: List[float] = []
    type_total = {"FALSIFICATION": 0, "CONCEALMENT": 0, "EQUIVOCATION": 0}
    per_seed: Dict[str, Any] = {}

    for sdir, df in picks2:
        seed = extract_seed(sdir)
        summ = load_detector_summary(df)
        ft, rc, aws = load_analysis_metrics(sdir)

        dr = float(summ["deception_rate"])  # deception_rate
        saa = float(summ["severity_average_all_rounds"])  # avg severity (all)
        sad = float(summ["severity_average_deception_only"])  # avg severity (deception only)
        tr = int(summ["total_rounds"])  # interaction_len
        tcounts = summ.get("type_counts", {})
        if not isinstance(tcounts, dict):
            tcounts = {}
        # aggregate type counts
        for k in type_total:
            type_total[k] += int(tcounts.get(k, 0))

        if seed in per_seed:
            raise ValueError(f"Duplicate seed in {model_dir.name}: {seed}")
        per_seed[seed] = {
            "final_trust_level": ft,
            "final_relational_comfort": rc,
            "average_work_satisfaction": aws,
            "interaction_len": tr,
            "deception_rate": dr,
            "severity_average_all_rounds": saa,
            "severity_average_deception_only": sad,
            "type_counts": {k: int(tcounts.get(k, 0)) for k in type_total},
        }

        drs.append(dr)
        saas.append(saa)
        sads.append(sad)

    # aggregated
    mu_dr, se_dr = mean(drs), stderr(drs)
    mu_saa, se_saa = mean(saas), stderr(saas)
    mu_sad, se_sad = mean(sads), stderr(sads)
    total_types = sum(type_total.values())
    type_pct = {k: (type_total[k] / total_types) if total_types else 0.0 for k in type_total}

    out = {
        "aggregated": {
            "n_sessions": len(per_seed),
            "deception_rate": {"mean": mu_dr, "stderr": se_dr, "formatted": fmt(mu_dr, se_dr, precision)},
            "severity_average_all_rounds": {"mean": mu_saa, "stderr": se_saa, "formatted": fmt(mu_saa, se_saa, precision)},
            "severity_average_deception_only": {"mean": mu_sad, "stderr": se_sad, "formatted": fmt(mu_sad, se_sad, precision)},
            "type_counts_total": type_total,
            "type_percentages_total": type_pct,
        },
        "datapoint_level": {k: per_seed[k] for k in sorted(per_seed.keys(), key=lambda x: int(x))},
    }
    return out


def main() -> None:
    args = parse_args()
    model_dir = resolve_dir(args.model_dir)
    if not (0 <= args.precision <= 6):
        raise SystemExit("--precision must be 0..6")
    out = aggregate(model_dir, precision=args.precision)
    outp = model_dir / "summary.json"
    outp.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote summary: {outp}")


if __name__ == "__main__":
    main()

