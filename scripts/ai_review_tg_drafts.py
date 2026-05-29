import argparse
import csv
import json
import os
import re
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


REVIEW_FIELDS = [
    "reviewer_decision",
    "reviewer_usefulness",
    "reviewer_issue_type",
    "reviewer_notes",
]


SYSTEM_PROMPT = """You are a senior Web3 event-intelligence editor.

Review Telegram-style crypto intelligence drafts.

Goal:
- Decide whether each draft is useful enough for a private intelligence feed.
- Do not provide trading advice.
- Do not generate buy/sell/long/short recommendations.
- Be strict about noisy, stale, vague, generic, or non-actionable items.

Return JSON only.

Allowed reviewer_decision:
- approve: useful enough as a private intelligence draft
- edit: potentially useful but needs asset/time/tone/factual cleanup
- reject: too noisy, stale, vague, generic, or not relevant enough

Allowed reviewer_usefulness:
- useful
- interesting
- noise

Allowed reviewer_issue_type:
- none
- factual_issue
- asset_issue
- time_issue
- tone_issue
- not_price_relevant
- too_generic
- duplicate_or_stale

Important:
- "Useful" means useful as market/event intelligence, not a trade signal.
- A draft can be useful even if the asset lacks Binance support, if it is relevant to Web3.
- Pure price recaps, generic macro noise, ads, career content, and vague KOL takes should usually be rejected.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-review local TG draft queue through OpenRouter.")
    parser.add_argument("--input", default=str(ROOT / "data" / "tg_drafts_v06_private_pilot.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_drafts_v06_private_pilot_ai_reviewed.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_draft_ai_review_summary.csv"))
    parser.add_argument("--model", default="anthropic/claude-sonnet-4.5")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--apply", action="store_true", help="Also overwrite --input with reviewed rows.")
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compact_draft(row: dict) -> dict:
    return {
        "draft_id": row.get("draft_id", ""),
        "candidate_id": row.get("candidate_id", ""),
        "published_at_china": row.get("published_at_china", ""),
        "asset_symbol": row.get("asset_symbol", ""),
        "event_type": row.get("event_type", ""),
        "event_scope": row.get("event_scope", ""),
        "channel_route": row.get("channel_route", ""),
        "confidence_label": row.get("confidence_label", ""),
        "title": row.get("title", ""),
        "draft_text": row.get("draft_text", ""),
    }


def build_user_prompt(rows: list[dict]) -> str:
    payload = [compact_draft(row) for row in rows]
    return (
        "Review these drafts and return a JSON object with key 'reviews'. "
        "Each review must include draft_id, reviewer_decision, reviewer_usefulness, "
        "reviewer_issue_type, reviewer_notes. reviewer_notes should be short Chinese.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def call_openrouter(prompt: str, model: str, timeout: int, retries: int) -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing in environment.")

    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 5000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_error = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            if response.status_code < 300:
                content = response.json()["choices"][0]["message"]["content"]
                return extract_json(content)
            last_error = f"http_status={response.status_code}; body={response.text[:300]}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(min(2 * attempt, 8))
    raise RuntimeError(f"OpenRouter request failed: {last_error}")


def apply_reviews(rows: list[dict], reviews: list[dict]) -> tuple[list[dict], dict]:
    by_id = {str(item.get("draft_id", "")).strip(): item for item in reviews}
    counts = {
        "matched_reviews": 0,
        "approve_count": 0,
        "edit_count": 0,
        "reject_count": 0,
        "useful_count": 0,
        "interesting_count": 0,
        "noise_count": 0,
    }
    for row in rows:
        review = by_id.get(str(row.get("draft_id", "")).strip())
        if not review:
            continue
        counts["matched_reviews"] += 1
        for field in REVIEW_FIELDS:
            row[field] = str(review.get(field, "") or "").strip()
        decision = row["reviewer_decision"].lower()
        usefulness = row["reviewer_usefulness"].lower()
        if decision in {"approve", "approved"}:
            row["draft_status"] = "approved"
            counts["approve_count"] += 1
        elif decision in {"edit", "needs_edit", "fix"}:
            row["draft_status"] = "needs_edit"
            counts["edit_count"] += 1
        elif decision in {"reject", "rejected", "discard"}:
            row["draft_status"] = "rejected"
            counts["reject_count"] += 1
        if usefulness in {"useful", "interesting", "noise"}:
            counts[f"{usefulness}_count"] += 1
    return rows, counts


def write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    rows = read_rows(input_path)
    target_rows = rows[: args.limit] if args.limit else rows
    result = call_openrouter(build_user_prompt(target_rows), args.model, args.timeout, args.retries)
    reviews = result.get("reviews", [])
    if not isinstance(reviews, list):
        raise RuntimeError("AI response JSON does not contain reviews list.")

    reviewed_rows, counts = apply_reviews(rows, reviews)
    fieldnames = list(reviewed_rows[0].keys()) if reviewed_rows else []
    write_rows(output_path, reviewed_rows, fieldnames)
    if args.apply:
        write_rows(input_path, reviewed_rows, fieldnames)

    summary = {
        "input_rows": len(rows),
        "requested_review_rows": len(target_rows),
        "returned_reviews": len(reviews),
        **counts,
        "model": args.model,
        "applied_to_input": "yes" if args.apply else "no",
        "status": "pass" if counts["matched_reviews"] == len(target_rows) else "warning",
    }
    write_summary(normalize_path(args.summary), summary)
    print(f"input_rows={len(rows)}")
    print(f"requested_review_rows={len(target_rows)}")
    print(f"returned_reviews={len(reviews)}")
    print(f"matched_reviews={counts['matched_reviews']}")
    print(f"approve_count={counts['approve_count']}")
    print(f"edit_count={counts['edit_count']}")
    print(f"reject_count={counts['reject_count']}")
    print(f"wrote_output={output_path}")
    print(f"wrote_summary={normalize_path(args.summary)}")
    return 0 if summary["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
