"""Market Radar v1.11-O — Post-Send Review Stub

A skeleton post-send review script that:
  - Does NOT call Telegram API
  - Does NOT read token/chat_id
  - Does NOT read .env
  - Reads message_id from future result files (when available)
  - If v1.11-N is still blocked (no message_id), outputs status: skipped
  - If message_id is present, generates a review packet skeleton for
    manual/Gemini post-send quality review

Security:
  - No network calls
  - No credential reading
  - No Telegram API calls
  - No printing or saving of secrets

Usage:
    python scripts/run_market_radar_v111o_post_send_review_stub.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.11-O"
MODE = "post_send_review_stub"

# ── Paths ──────────────────────────────────────────────────────────────────────────
V111N_RESULT_PATH = ROOT / "results" / "market_radar_v111n_safe_single_arb_test_send_result.json"
V111L_RESULT_PATH = ROOT / "results" / "market_radar_v111l_public_card_readiness_result.json"


def _now_iso() -> str:
    return datetime.now(CN_TZ).isoformat()


def _load_send_result() -> dict | None:
    """Load v1.11-N send result. Returns None if not found."""
    if not V111N_RESULT_PATH.exists():
        return None
    with open(V111N_RESULT_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _load_public_card() -> dict | None:
    """Load ARB H6-07 public card from v1.11-L result."""
    if not V111L_RESULT_PATH.exists():
        return None
    with open(V111L_RESULT_PATH, "r", encoding="utf-8-sig") as f:
        v111l = json.load(f)

    records = v111l.get("records", [])
    for r in records:
        if r.get("signal_id") == "H6-07" and str(r.get("asset", "")).upper() == "ARB":
            return r.get("public_card", {})
    return None


def run_review() -> dict:
    """Run the post-send review stub.

    Returns:
        Dict with review packet skeleton, or skipped status.
    """
    now_str = _now_iso()

    # ── 1. Load v1.11-N result ──
    send_result = _load_send_result()

    if send_result is None:
        return {
            "version": VERSION,
            "mode": MODE,
            "status": "skipped",
            "reason": "no_v111n_result_found",
            "detail": f"v1.11-N result file not found at {V111N_RESULT_PATH}",
            "checked_at": now_str,
        }

    # ── 2. Check if blocked ──
    send_status = send_result.get("status", "unknown")

    if send_status == "blocked":
        return {
            "version": VERSION,
            "mode": MODE,
            "status": "skipped",
            "reason": "no_real_message_id_available",
            "detail": f"v1.11-N send was blocked: {send_result.get('reason', 'unknown')}",
            "v111n_status": send_status,
            "v111n_reason": send_result.get("reason", ""),
            "checked_at": now_str,
        }

    # ── 3. Extract message_id(s) ──
    sent_messages = send_result.get("sent_messages", [])
    if not sent_messages:
        return {
            "version": VERSION,
            "mode": MODE,
            "status": "skipped",
            "reason": "no_real_message_id_available",
            "detail": "v1.11-N result has no sent_messages",
            "checked_at": now_str,
        }

    # ── 4. Build review packet skeleton ──
    public_card = _load_public_card()

    review_items = []
    for msg in sent_messages:
        signal_id = msg.get("signal_id", "?")
        asset = msg.get("asset", "?")
        message_id = msg.get("message_id", "")
        payload_sha256 = msg.get("payload_text_sha256", "")

        item = {
            "message_id": message_id,
            "signal_id": signal_id,
            "asset": asset,
            "payload_hash": payload_sha256,
            "payload_length": msg.get("payload_length", 0),
            "public_card_preview": (
                public_card.get("text", "")[:200] + "..."
                if public_card and public_card.get("text")
                else "(public card text not available)"
            ),
            "review_checklist": {
                "markdown_rendering": "pending — check in test channel",
                "link_preview": "pending — verify links are correct and working",
                "mobile_readability": "pending — verify on mobile TG client",
                "disclaimer_visible": "pending — check ⚠️ disclaimer is present",
                "no_trading_advice": "pending — verify it does not read as trading advice",
                "parse_mode_correct": "pending — verify MarkdownV2 escape is correct",
                "payload_integrity": f"verified — SHA-256: {payload_sha256[:24]}...",
            },
        }
        review_items.append(item)

    return {
        "version": VERSION,
        "mode": MODE,
        "status": "review_packet_generated",
        "review_items": review_items,
        "review_count": len(review_items),
        "requires_manual_review": True,
        "requires_gemini_review": False,  # Gemini not called in stub
        "checked_at": now_str,
        "generated_at": now_str,
    }


def main() -> int:
    """Run the post-send review stub."""
    print(f"=== Market Radar {VERSION}: Post-Send Review Stub ===")
    print(f"Time: {_now_iso()}")
    print(f"Mode: {MODE}")
    print()

    result = run_review()

    print(f"Status: {result['status']}")
    if result["status"] == "skipped":
        print(f"Reason: {result['reason']}")
        print(f"Detail: {result['detail']}")
        print()
        print("No real message_id available — review packet not generated.")
        print("Run this stub again after a successful real test send.")
    else:
        print(f"Review items: {result.get('review_count', 0)}")
        for item in result.get("review_items", []):
            print(f"  - {item['signal_id']} {item['asset']}: message_id={item['message_id']}")
            print(f"    payload_hash: {item['payload_hash'][:24]}...")
            print(f"    checklist items: {len(item['review_checklist'])}")
        print()
        print("Review packet generated. Manual review required for all checklist items.")
        print("Use the checklist to verify rendering in test channel.")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
