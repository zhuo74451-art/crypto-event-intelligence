import argparse
import os
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query Claude via OpenRouter using local manual-reduction prompt.")
    parser.add_argument("--prompt", default=str(ROOT / "docs" / "CLAUDE_MANUAL_REDUCTION_PROMPT.md"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v06_claude_manual_reduction_response.md"))
    parser.add_argument("--model", default="anthropic/claude-3.7-sonnet")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=3)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("OPENROUTER_API_KEY is missing in environment.")
        return 1

    prompt_path = normalize_path(args.prompt)
    output_path = normalize_path(args.output)
    if not prompt_path.exists():
        print(f"prompt not found: {prompt_path}")
        return 1

    prompt = prompt_path.read_text(encoding="utf-8", errors="replace")
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = None
    last_error = ""
    for attempt in range(1, max(1, args.retries) + 1):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=args.timeout,
            )
            break
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt == args.retries:
                print(f"request failed after {attempt} attempts: {last_error}")
                return 4
            time.sleep(min(2 * attempt, 6))

    if resp is None:
        print(f"request failed: {last_error}")
        return 4
    if resp.status_code >= 300:
        print(f"request failed: {resp.status_code} {resp.text[:500]}")
        return 2

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        print("no choices returned")
        return 3
    content = choices[0].get("message", {}).get("content", "")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(content), encoding="utf-8")
    print(f"wrote Claude response to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
