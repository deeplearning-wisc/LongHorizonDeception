"""
Generate per-round summaries (LLM response, Manager feedback, Manager eval reasoning)
and write them to <run_dir>/summary.json.

Usage:
  python visualization/summarizer.py --run results/<run_dir>

Notes:
  - Uses Azure GPT‑5 profile from configs/api_profiles.yaml (key: gpt5_azure).
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

import yaml
from openai.lib.azure import AzureOpenAI
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


def _sub_env(s: str) -> str:
    """Substitute ${VAR} using environment variables."""
    out = ""
    i = 0
    while i < len(s):
        if s[i] == '$' and i + 1 < len(s) and s[i + 1] == '{':
            j = s.find('}', i + 2)
            if j == -1:
                out += s[i]
                i += 1
                continue
            var = s[i + 2:j]
            val = os.environ.get(var)
            if val is None:
                raise ValueError(f"Environment variable '{var}' not found for substitution")
            out += val
            i = j + 1
        else:
            out += s[i]
            i += 1
    return out


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


def load_gpt5_azure_profile(repo_root: Path) -> Dict[str, Any]:
    cfg_path = repo_root / 'configs' / 'api_profiles.yaml'
    if not cfg_path.exists():
        raise FileNotFoundError(f"api_profiles.yaml not found at {cfg_path}")
    data = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or 'api_profiles' not in data:
        raise ValueError("Invalid api_profiles.yaml structure (missing api_profiles)")
    profiles = data['api_profiles']
    if 'gpt5_azure' not in profiles:
        raise ValueError("Profile 'gpt5_azure' not found in api_profiles.yaml")
    prof = profiles['gpt5_azure']
    # env substitution for strings
    resolved: Dict[str, Any] = {}
    for k, v in prof.items():
        if isinstance(v, str):
            resolved[k] = _sub_env(v) if '${' in v else v
        else:
            resolved[k] = v
    required = ['azure_api_key', 'azure_endpoint', 'azure_deployment', 'azure_api_version']
    for k in required:
        if k not in resolved or not resolved[k]:
            raise ValueError(f"gpt5_azure missing required key: {k}")
    return resolved


def build_client(profile: Dict[str, Any]) -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=profile['azure_endpoint'],
        azure_deployment=profile['azure_deployment'],
        api_version=profile['azure_api_version'],
        api_key=profile['azure_api_key'],
    )


def call_summary_via_handler(profile: Dict[str, Any], title: str, body: str, kind: str) -> str:
    if not body:
        return ""
    sys = (
        "You are a precise summarizer for audits.\n"
        "Summarize ONLY the provided content. Do not use any prior or external context.\n"
        "Keep to 5–7 concise bullets (or a short paragraph if better).\n"
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
    title = it.get('task_title', f"Round {gr}")
    llm = it.get('llm_response') or ''
    mfb = it.get('manager_feedback') or ''
    mev = it.get('manager_eval_reasoning') or ''
    su = it.get('state_updates') or {}
    llm_sum = call_summary_via_handler(profile, title, llm, 'LLM response') if llm else ''
    mfb_sum = call_summary_via_handler(profile, title, mfb, 'manager feedback') if mfb else ''
    mev_sum = call_summary_via_handler(profile, title, mev, 'manager evaluation reasoning') if mev else ''
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
    ex = data['experiment']
    rounds: List[Dict[str, Any]] = []
    for t in ex['tasks']:
        title = t['task']['title']
        for r in t['rounds']:
            rounds.append({
                'global_round': r['global_round'],
                'task_title': title,
                'llm_response': r.get('llm_response', ''),
                'manager_feedback': r.get('manager_evaluation', {}).get('feedback_response', ''),
                'manager_eval_reasoning': r.get('manager_evaluation', {}).get('evaluation_reasoning', ''),
                'state_updates': r.get('manager_evaluation', {}).get('state_updates', {}),
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

    out: Dict[str, Dict[str, str]] = {}
    progress = None
    if show_progress and tqdm is not None:
        progress = tqdm(total=len(items), desc='Summarizing rounds', unit='round')

    # Use processes for concurrency; wait for all results to finish (no per-item timeout).
    with ProcessPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futures = {ex.submit(_summarize_worker, profile, it): it for it in items}
        for fut in as_completed(futures):
            try:
                res = fut.result()
                out[res['gr']] = res['data']
            except Exception as e:
                it = futures[fut]
                gr = str(it['global_round'])
                out[gr] = {
                    'llm_summary': f'[summary_error] {e}',
                    'manager_feedback_summary': f'[summary_error] {e}',
                    'manager_eval_summary': f'[summary_error] {e}',
                }
            finally:
                if progress is not None:
                    progress.update(1)
        if progress is not None:
            progress.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description='Generate summary.json for a run directory')
    ap.add_argument('--run', required=True, help='Path to run directory containing result.json')
    ap.add_argument('--no-progress', action='store_true', help='Disable tqdm progress bar')
    ap.add_argument('--workers', type=int, default=2, help='Max concurrent workers (default: 2)')
    args = ap.parse_args()
    run_dir = Path(args.run).expanduser().resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        raise NotADirectoryError(f"Run directory not found: {run_dir}")
    summaries = summarize_run(run_dir, show_progress=not args.no_progress, workers=args.workers)
    out_path = run_dir / 'summary.json'
    out_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote summaries: {out_path}")


if __name__ == '__main__':
    main()
