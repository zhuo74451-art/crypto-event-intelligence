import argparse
import hashlib
import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query Claude via OpenRouter using docs/CLAUDE_NEXT_PROMPT.md. API key is read only from OPENROUTER_API_KEY."
    )
    parser.add_argument("--prompt", default=str(ROOT / "docs" / "CLAUDE_NEXT_PROMPT.md"))
    parser.add_argument("--output", default="")
    parser.add_argument("--model", default="anthropic/claude-sonnet-4.5")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=5000)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--no-refresh", action="store_true", help="Do not re-index Claude responses or refresh Project OS after success.")
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def default_output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ROOT / "results" / f"claude_next_response_{stamp}.md"


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    model_l = str(model or "").lower()
    if "haiku" in model_l:
        input_per_m = 0.25
        output_per_m = 1.25
    elif "sonnet" in model_l:
        input_per_m = 3.0
        output_per_m = 15.0
    elif "opus" in model_l:
        input_per_m = 15.0
        output_per_m = 75.0
    else:
        input_per_m = 3.0
        output_per_m = 15.0
    return round((prompt_tokens / 1_000_000) * input_per_m + (completion_tokens / 1_000_000) * output_per_m, 6)


def append_llm_usage(row: dict) -> None:
    path = ROOT / "data" / "llm_usage_ledger.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "created_at",
        "provider",
        "model",
        "task_type",
        "prompt_path",
        "output_path",
        "prompt_sha256_16",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "status",
        "error",
    ]
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def extract_response_content(payload: dict) -> str:
    choices = payload.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def run_refresh_steps() -> None:
    steps = [
        ["scripts/check_local_environment.py"],
        ["scripts/audit_v043_selection_against_v06.py"],
        ["scripts/index_claude_responses.py"],
        ["scripts/build_claude_decision_review_queue.py"],
        ["scripts/build_command_registry.py"],
        ["scripts/build_backtest_readiness_report.py"],
        ["scripts/refresh_project_state.py"],
        ["scripts/render_project_dashboard.py"],
        ["scripts/build_project_review_actions.py"],
        ["scripts/build_artifact_manifest.py"],
        ["scripts/render_project_dashboard.py"],
        ["scripts/validate_project_os.py"],
        ["scripts/refresh_project_state.py"],
        ["scripts/render_project_dashboard.py"],
        ["scripts/generate_cursor_prompt.py"],
        ["scripts/generate_claude_question_prompt.py", "--force"],
    ]
    for step in steps:
        subprocess.run([sys.executable, *step], cwd=ROOT, check=True)


def mark_backlog_asked(output_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/mark_claude_backlog_asked.py",
            "--response",
            str(output_path),
            "--batch-id",
            output_path.stem.replace("claude_next_response_", ""),
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("OPENROUTER_API_KEY is missing in environment. No request was sent.")
        return 1

    prompt_path = normalize_path(args.prompt)
    output_path = normalize_path(args.output) if args.output else default_output_path()
    if not prompt_path.exists():
        print(f"prompt not found: {prompt_path}")
        return 1

    prompt = prompt_path.read_text(encoding="utf-8", errors="replace")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:16]
    payload = {
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = None
    for attempt in range(1, max(1, args.retries) + 1):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=args.timeout,
            )
            if response.status_code < 500:
                break
        except requests.RequestException as exc:
            if attempt == args.retries:
                print(f"request failed after {attempt} attempts: {exc}")
                return 4
        time.sleep(min(2 * attempt, 8))

    if response is None:
        print("request failed: no response")
        return 4
    if response.status_code >= 300:
        print(f"request failed: http_status={response.status_code}; body={response.text[:500]}")
        append_llm_usage(
            {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC+8"),
                "provider": "openrouter",
                "model": args.model,
                "task_type": "claude_consultation",
                "prompt_path": str(prompt_path.relative_to(ROOT)),
                "output_path": str(output_path.relative_to(ROOT)),
                "prompt_sha256_16": prompt_hash,
                "status": "fail",
                "error": f"http_status={response.status_code}",
            }
        )
        return 2

    data = response.json()
    content = extract_response_content(data)
    if not content.strip():
        print("request returned no response content")
        append_llm_usage(
            {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC+8"),
                "provider": "openrouter",
                "model": args.model,
                "task_type": "claude_consultation",
                "prompt_path": str(prompt_path.relative_to(ROOT)),
                "output_path": str(output_path.relative_to(ROOT)),
                "prompt_sha256_16": prompt_hash,
                "status": "fail",
                "error": "empty_response",
            }
        )
        return 3

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "\n".join(
        [
            "# Claude Response",
            "",
            f"- generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
            f"- model: {args.model}",
            f"- prompt: {prompt_path.relative_to(ROOT)}",
            f"- prompt_sha256_16: {prompt_hash}",
            "",
            content.strip(),
            "",
        ]
    )
    output_path.write_text(rendered, encoding="utf-8")
    usage = data.get("usage", {}) if isinstance(data.get("usage", {}), dict) else {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    append_llm_usage(
        {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC+8"),
            "provider": "openrouter",
            "model": args.model,
            "task_type": "claude_consultation",
            "prompt_path": str(prompt_path.relative_to(ROOT)),
            "output_path": str(output_path.relative_to(ROOT)),
            "prompt_sha256_16": prompt_hash,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimate_cost_usd(args.model, prompt_tokens, completion_tokens),
            "status": "ok",
            "error": "",
        }
    )
    print(f"wrote Claude response to {output_path}")
    mark_backlog_asked(output_path)
    if not args.no_refresh:
        run_refresh_steps()
        print("refreshed Claude index, Project State, Dashboard, Cursor prompt, and Claude prompt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
