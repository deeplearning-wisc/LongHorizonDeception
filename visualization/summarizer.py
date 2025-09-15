"""
Generate per-round summaries (LLM response, Manager feedback, Manager eval reasoning)
and write them to <run_dir>/summary.json.

Usage:
  python visualization/summarizer.py --run results/<run_dir>

Notes:
  - Uses Azure GPT-5 profile from configs/api_profiles.yaml (key: gpt5_azure).
  - Requires .env with gpt_5_key set (referenced by api_profiles.yaml).
  - Fail-fast on missing keys; no silent fallbacks.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from utils.config_handler import ConfigHandler  # type: ignore
from core.Universal_LLM_Handler import UniversalLLMHandler  # type: ignore
try:
    from tqdm.auto import tqdm  # type: ignore
except Exception:  # pragma: no cover
    tqdm = None  # fallback: no progress bar


RESULT_FILENAME = "result.json"



def _load_env(repo_root: Path) -> None:
    """Load .env from repo root into os.environ (override=True)."""
    env_path = repo_root / '.env'
    if not env_path.exists():
        # don't fail here; caller may have env set by shell
        return
    # Try python-dotenv first
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=str(env_path), override=True)
        return
    except Exception:
        pass
    # Fallback: simple parser KEY=VALUE, strip quotes
    try:
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value
    except Exception:
        # Ignore, let downstream substitution raise clear error if missing
        return



def call_summary_via_handler(profile: Dict[str, Any], title: str, body: str, kind: str) -> str:
    if not isinstance(body, str) or not body.strip():
        raise ValueError(f"Empty content for summarization: {kind}")
    sys = (
        "You are a precise summarizer for audits.\n"
        "Summarize ONLY the provided content. Do not use any prior or external context.\n"
        "Keep to 5-7 concise bullets (or a short paragraph if better).\n"
        "Preserve key facts, caveats, risks, and explicit next actions.\n"
        "Do not invent facts; if uncertain, be explicit."
    )
    usr = (
        f"Summarize this {kind}.\n"
        f"Title: {title}\n\n"
        f"Content:\n{body}"
    )
    handler = UniversalLLMHandler(provider='azure', config=profile, verbose_print=False)
    handler.set_system_prompt(sys)
    handler.add_user_message(usr)
    try:
        return handler.generate_response(max_iterations=1, retry=2)
    except Exception as e:
        return f"[summary_error] {e}"


def _summarize_worker(profile: Dict[str, Any], it: Dict[str, Any]) -> Dict[str, Any]:
    """Process-safe worker to summarize a single round."""
    gr = str(it['global_round'])
    # Strict: required fields must exist and be non-empty strings / proper objects
    if 'task_title' not in it or not isinstance(it['task_title'], str) or not it['task_title'].strip():
        raise KeyError(f"Missing or empty task_title for round {gr}")
    title = it['task_title']
    if 'llm_response' not in it or not isinstance(it['llm_response'], str) or not it['llm_response'].strip():
        raise KeyError(f"Missing or empty llm_response for round {gr}")
    if 'manager_feedback' not in it or not isinstance(it['manager_feedback'], str) or not it['manager_feedback'].strip():
        raise KeyError(f"Missing or empty manager_feedback for round {gr}")
    if 'manager_eval_reasoning' not in it or not isinstance(it['manager_eval_reasoning'], str) or not it['manager_eval_reasoning'].strip():
        raise KeyError(f"Missing or empty manager_eval_reasoning for round {gr}")
    if 'state_updates' not in it or not isinstance(it['state_updates'], dict):
        raise KeyError(f"Missing or invalid state_updates for round {gr}")

    llm = it['llm_response']
    mfb = it['manager_feedback']
    mev = it['manager_eval_reasoning']
    su = it['state_updates']

    llm_sum = call_summary_via_handler(profile, title, llm, 'LLM response')
    mfb_sum = call_summary_via_handler(profile, title, mfb, 'manager feedback')
    mev_sum = call_summary_via_handler(profile, title, mev, 'manager evaluation reasoning')
    return {
        'gr': gr,
        'data': {
            'llm_summary': llm_sum,
            'manager_feedback_summary': mfb_sum,
            'manager_eval_summary': mev_sum,
        }
    }


def parse_rounds(result_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(result_path.read_text(encoding='utf-8'))
    # Strict schema checks (no defaults)
    if 'experiment' not in data or not isinstance(data['experiment'], dict):
        raise KeyError("result.json missing 'experiment' object")
    ex = data['experiment']
    if 'tasks' not in ex or not isinstance(ex['tasks'], list):
        raise KeyError("result.json 'experiment.tasks' must be a list")
    rounds: List[Dict[str, Any]] = []
    for ti, t in enumerate(ex['tasks']):
        if 'task' not in t or 'rounds' not in t:
            raise KeyError(f"task entry {ti} missing 'task' or 'rounds'")
        task_obj = t['task']
        rounds_list = t['rounds']
        if not isinstance(task_obj, dict) or not isinstance(rounds_list, list):
            raise TypeError(f"task entry {ti} has invalid types for 'task' or 'rounds'")
        if 'title' not in task_obj or not isinstance(task_obj['title'], str) or not task_obj['title'].strip():
            raise KeyError(f"task entry {ti} missing or empty title")
        title = task_obj['title']
        for ri, r in enumerate(rounds_list):
            if not isinstance(r, dict):
                raise TypeError(f"round {ri} in task {ti} must be an object")
            required_r_keys = ('global_round', 'llm_response', 'manager_evaluation')
            for k in required_r_keys:
                if k not in r:
                    raise KeyError(f"round {ri} in task {ti} missing '{k}'")
            if not isinstance(r['global_round'], int):
                raise TypeError(f"round {ri} in task {ti} has non-integer global_round")
            if not isinstance(r['llm_response'], str) or not r['llm_response'].strip():
                raise ValueError(f"round {ri} in task {ti} has empty llm_response")
            me = r['manager_evaluation']
            if not isinstance(me, dict):
                raise TypeError(f"round {ri} in task {ti} has invalid manager_evaluation")
            for mk in ('feedback_response', 'evaluation_reasoning', 'state_updates'):
                if mk not in me:
                    raise KeyError(f"round {ri} in task {ti} manager_evaluation missing '{mk}'")
            if not isinstance(me['feedback_response'], str) or not me['feedback_response'].strip():
                raise ValueError(f"round {ri} in task {ti} has empty manager feedback")
            if not isinstance(me['evaluation_reasoning'], str) or not me['evaluation_reasoning'].strip():
                raise ValueError(f"round {ri} in task {ti} has empty manager evaluation reasoning")
            if not isinstance(me['state_updates'], dict):
                raise TypeError(f"round {ri} in task {ti} has invalid state_updates")
            rounds.append({
                'global_round': r['global_round'],
                'task_title': title,
                'llm_response': r['llm_response'],
                'manager_feedback': me['feedback_response'],
                'manager_eval_reasoning': me['evaluation_reasoning'],
                'state_updates': me['state_updates'],
            })
    rounds.sort(key=lambda x: x['global_round'])
    return rounds


def summarize_run(run_dir: Path, show_progress: bool = True, workers: int = 2) -> Dict[str, Dict[str, str]]:
    repo_root = Path(__file__).resolve().parent.parent
    # Ensure .env is loaded so ${gpt_5_key} resolves
    _load_env(repo_root)
    # Reuse repo handler to resolve api profiles and env
    ch = ConfigHandler()
    api_profiles = ch._load_api_profiles()
    profile = api_profiles['api_profiles']['gpt5_azure']

    result_path = run_dir / RESULT_FILENAME
    if not result_path.exists():
        raise FileNotFoundError(f"result.json not found at {result_path}")
    items = parse_rounds(result_path)
    if not items:
        raise RuntimeError("No rounds found in result.json; cannot generate summaries")

    out: Dict[str, Dict[str, str]] = {}
    progress = None
    if show_progress and tqdm is not None:
        progress = tqdm(total=len(items), desc='Summarizing rounds', unit='round')

    # Use processes for concurrency; wait for all results to finish (no per-item timeout).
    with ProcessPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futures = {ex.submit(_summarize_worker, profile, it): it for it in items}
        for fut in as_completed(futures):
            res = fut.result()  # propagate worker exceptions (strict)
            out[res['gr']] = res['data']
            if progress is not None:
                progress.update(1)
        if progress is not None:
            progress.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description='Generate summary.json for a run directory')
    ap.add_argument('--run', required=True, help='Path to run directory containing result.json')
    ap.add_argument('--no-progress', action='store_true', help='Disable tqdm progress bar')
    ap.add_argument('--workers', type=int, default=5, help='Max concurrent workers (default: 2)')
    args = ap.parse_args()
    run_dir = Path(args.run).expanduser().resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        raise NotADirectoryError(f"Run directory not found: {run_dir}")
    summaries = summarize_run(run_dir, show_progress=not args.no_progress, workers=args.workers)
    # strict validation: ensure every round has non-empty summaries
    required = ('llm_summary', 'manager_feedback_summary', 'manager_eval_summary')
    missing = []
    for gr, data in summaries.items():
        if not isinstance(data, dict):
            missing.append((gr, 'object'))
            continue
        for k in required:
            v = data.get(k, None)
            if not isinstance(v, str) or not v.strip():
                missing.append((gr, k))
    if missing:
        raise SystemExit(f"Summary generation incomplete; missing fields: {missing}")
    out_path = run_dir / 'summary.json'
    out_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote summaries: {out_path}")


if __name__ == '__main__':
    main()
