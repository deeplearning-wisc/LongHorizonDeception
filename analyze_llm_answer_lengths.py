#!/usr/bin/env python3
"""
Analyze character lengths of every LLM answer in a session result.

Given a path to a session directory, this script finds the session's
result.json, iterates through all tasks and rounds, extracts the LLM answer
text, and reports per-round character counts.

Fail-fast rules:
- The provided path must either directly contain `result.json`, or contain
  exactly one immediate child directory that contains `result.json`.
- Required keys must exist (no silent defaults). If structure differs, the
  script raises with a clear message.

Usage:
  python analyze_llm_answer_lengths.py /path/to/session_dir [--csv out.csv]

Example:
  python analyze_llm_answer_lengths.py \
    Results_new_models/oss_main/startup_consulting_20250916_055205_seed3179177405_model_openai/gpt-oss-120b \
    --csv answer_lengths.csv
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Constants
RESULT_FILENAME: str = "result.json"


@dataclass(frozen=True)
class AnswerLengthRow:
    global_round: int
    task_sequence_num: int
    task_round: int
    char_len: int


def resolve_session_dir(path_str: str) -> Path:
    """Resolve a directory that contains result.json.

    Accepts either the exact session directory (with result.json) or a parent
    directory that has exactly one immediate child directory with result.json.
    Raises ValueError if none or multiple candidates are found.
    """
    p = Path(path_str).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")
    if p.is_file():
        raise ValueError(f"Expected a directory, got a file: {p}")

    direct = p / RESULT_FILENAME
    if direct.exists():
        return p

    # Search only immediate children to avoid surprising matches
    candidates: List[Path] = []
    for child in p.iterdir():
        if child.is_dir() and (child / RESULT_FILENAME).exists():
            candidates.append(child)

    if not candidates:
        raise FileNotFoundError(
            f"No {RESULT_FILENAME} found under {p}. Provide a session directory."
        )
    if len(candidates) > 1:
        names = ", ".join(c.name for c in candidates)
        raise ValueError(
            f"Multiple child directories contain {RESULT_FILENAME}: {names}. "
            f"Please specify the exact session directory."
        )
    return candidates[0]


def load_experiment(session_dir: Path) -> Dict[str, Any]:
    """Load and validate the experiment JSON structure."""
    result_path = session_dir / RESULT_FILENAME
    with open(result_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    if "experiment" not in data:
        raise KeyError("Missing required key 'experiment' at top level")
    exp = data["experiment"]
    if "tasks" not in exp:
        raise KeyError("Missing required key 'tasks' in 'experiment'")
    if not isinstance(exp["tasks"], list):
        raise TypeError("'experiment.tasks' must be a list")
    return data


def extract_answer_text(llm_response: Any) -> str:
    """Extract plain text answer from llm_response field.

    - If `llm_response` is a string, return it directly.
    - If it is a dict, require a 'content' key and return it.
    - Otherwise, raise a descriptive error.
    """
    if isinstance(llm_response, str):
        return llm_response
    if isinstance(llm_response, dict):
        if "content" not in llm_response:
            raise KeyError(
                "'llm_response' is an object but missing required key 'content'"
            )
        content = llm_response["content"]
        if not isinstance(content, str):
            raise TypeError("'llm_response.content' must be a string")
        return content
    raise TypeError(
        f"Unsupported llm_response type: {type(llm_response).__name__}"
    )


def collect_answer_lengths(exp_data: Dict[str, Any]) -> List[AnswerLengthRow]:
    """Walk the experiment structure and collect per-round answer lengths."""
    rows: List[AnswerLengthRow] = []
    exp = exp_data["experiment"]
    tasks: List[Dict[str, Any]] = exp["tasks"]

    for task in tasks:
        # Required nested structure checks
        if "task" not in task or not isinstance(task["task"], dict):
            raise KeyError("Each item in 'tasks' must contain dict key 'task'")
        if "rounds" not in task or not isinstance(task["rounds"], list):
            raise KeyError("Each item in 'tasks' must contain list key 'rounds'")
        if "task_sequence_num" not in task["task"]:
            raise KeyError("Missing required key 'task_sequence_num' in task.task")
        task_seq = task["task"]["task_sequence_num"]
        if not isinstance(task_seq, int):
            raise TypeError("'task_sequence_num' must be an int")

        for r in task["rounds"]:
            if not isinstance(r, dict):
                raise TypeError("Each round must be a dict")
            for k in ("round", "global_round", "llm_response"):
                if k not in r:
                    raise KeyError(f"Missing required key '{k}' in round")
            task_round = r["round"]
            global_round = r["global_round"]
            if not isinstance(task_round, int) or not isinstance(global_round, int):
                raise TypeError("'round' and 'global_round' must be ints")

            content = extract_answer_text(r["llm_response"])
            char_len = len(content)

            rows.append(
                AnswerLengthRow(
                    global_round=global_round,
                    task_sequence_num=task_seq,
                    task_round=task_round,
                    char_len=char_len,
                )
            )
    # Sort by global_round for stable output
    rows.sort(key=lambda x: x.global_round)
    return rows


def print_table(rows: List[AnswerLengthRow]) -> None:
    """Print a compact table of per-round character lengths."""
    print(f"{'GR':>4}  {'Task':>4}  {'tRound':>6}  {'chars':>7}")
    for row in rows:
        print(
            f"{row.global_round:>4}  {row.task_sequence_num:>4}  {row.task_round:>6}  {row.char_len:>7}"
        )


def write_csv(rows: List[AnswerLengthRow], out_path: Path) -> None:
    """Write results to CSV with deterministic ordering."""
    import csv

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["global_round", "task_sequence_num", "task_round", "char_len"])
        for r in rows:
            w.writerow([r.global_round, r.task_sequence_num, r.task_round, r.char_len])
    print(f"\nCSV written to: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute character lengths of every LLM answer in a session"
    )
    parser.add_argument(
        "session",
        type=str,
        help="Path to a session directory (or its parent) containing result.json",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional CSV output filepath",
    )
    args = parser.parse_args()

    session_dir = resolve_session_dir(args.session)
    print(f"Session dir: {session_dir}")

    exp = load_experiment(session_dir)
    rows = collect_answer_lengths(exp)

    print_table(rows)

    if args.csv is not None:
        write_csv(rows, Path(args.csv).resolve())


if __name__ == "__main__":
    main()
