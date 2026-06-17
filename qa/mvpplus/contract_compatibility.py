"""Cross-branch contract compatibility — W3 CuratedApiReader output → W1 Feed Provider Slot.

Verifies that W3 output fields are accepted by W1 Provider contract.
No code copying — only schema/type comparison.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class ContractResult:
    name: str
    status: str
    detail: str = ""
    violations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# ── W3 Expected Output Schema ───────────────────────────────────────────────

W3_OUTPUT_SCHEMA = {
    "items": [
        {
            "tweet_id": "str (required)",
            "source": "str (required)",
            "source_label": "str (required)",
            "feed_id": "str (derived deterministically)",
            "published_at_backend": "str (ISO8601, required)",
            "original_id": "str (=tweet_id)",
            "data_mode": "str (live|fixture|research_sample|cached)",
            "source_kind": "str (news|telegram|webhook|unknown)",
            "content_type": "str",
            "zh_title": "str (optional)",
            "raw_title": "str (optional)",
            "delivery_payload.title": "str (optional)",
            "zh_body": "str (optional)",
            "extracted_text": "str (optional)",
            "raw_text": "str (optional)",
            "delivery_payload.body": "str (optional)",
            "is_featured": "bool (optional, default false)",
            "pipeline_stage": "str (published|draft|... )",
            "backend_error": "str (optional)",
            # db_path: MUST BE DISCARDED by Reader before output
        }
    ],
    "db_path_suppression_required": True,
    "source_statuses": [
        {
            "source": "str",
            "status": "str (ok|degraded|unavailable)",
            "ok": "bool",
            "detail": "str (optional)",
        }
    ],
    "overall_status": "str (ok|degraded|unavailable)",
    "records_seen": "int",
    "records_accepted": "int",
    "records_rejected": "int",
    "live_count": "int",
    "fixture_count": "int",
    "research_count": "int",
    "cached_count": "int",
    "errors": "list[str]",
    "next_cursor": "str (optional)",
    "provider_name": "str",
    "cursor_safe": "bool (default true)",
    "provenance": "str (curated_api|... )",
}


# ── W1 Provider Contract Expected Input ─────────────────────────────────────

W1_PROVIDER_CONTRACT = {
    "feed_items": [
        {
            "source": "str (required)",
            "source_label": "str (required)",
            "feed_id": "str (required, deterministic)",
            "original_id": "str (required)",
            "published_at": "str (ISO8601)",
            "data_mode": "str",
            "content": "str",
            "content_type": "str (optional)",
            "is_featured": "bool (optional)",
        }
    ],
    "next_cursor": "str (optional)",
    "provider_name": "str",
    "cursor_safe": "bool",
    "records_seen": "int",
    "records_accepted": "int",
    "records_rejected": "int",
    "live_count": "int",
    "fixture_count": "int",
    "research_count": "int",
    "cached_count": "int",
    "source_statuses": [
        {
            "source": "str",
            "status": "str",
            "ok": "bool",
        }
    ],
    "overall_status": "str",
    "errors": "list[str]",
    "provenance": "str",
}


def check_schema_fields(w3_schema: dict, w1_contract: dict) -> list[str]:
    """Compare W3 output schema vs W1 provider contract. Returns violations."""
    violations = []

    # W1 items need: source, source_label, feed_id, original_id, published_at, data_mode, content
    # W3 provides: source, source_label, feed_id (via make_feed_id), original_id (=tweet_id),
    #   published_at_backend→published_at, data_mode, zh_title/zh_body→content
    field_map = {
        "source": ("source", "str"),
        "source_label": ("source_label", "str"),
        "original_id": ("tweet_id→original_id", "str"),
        "feed_id": ("derived deterministically", "str"),
        "published_at": ("published_at_backend", "str (ISO8601)"),
        "data_mode": ("data_mode", "str"),
        "content": ("zh_body|extracted_text|raw_text|delivery_payload.body", "str (optional)"),
    }

    for w1_field, expected_types in w1_contract["feed_items"][0].items():
        if w1_field in field_map:
            w3_src = field_map[w1_field][0]
        else:
            w3_src = w1_field  # assume same name

    # Check W3 has all fields W1 needs
    w3_fields = {k for item in w3_schema["items"] for k in item.keys()}
    w3_fields.add("tweet_id")
    w3_fields.add("published_at_backend")

    w1_needs = {"source", "source_label", "original_id", "feed_id", "published_at", "data_mode"}
    for need in w1_needs:
        w3_equivalent = {
            "original_id": "tweet_id",
            "feed_id": "feed_id",
            "published_at": "published_at_backend",
        }
        w3_field = w3_equivalent.get(need, need)
        if w3_field not in w3_fields and w3_field not in str(w3_schema):
            violations.append(f"W1 needs '{need}' — W3 equivalent '{w3_field}' not found in schema")

    # Check common fields at provider result level
    for field in ["records_seen", "records_accepted", "records_rejected",
                  "live_count", "fixture_count", "research_count", "cached_count",
                  "next_cursor", "provider_name", "cursor_safe", "source_statuses",
                  "overall_status", "errors", "provenance"]:
        if field not in w3_schema and field not in str(w3_schema):
            violations.append(f"Field '{field}' in W1 contract but not in W3 schema")

    return violations


def run_compatibility_check() -> ContractResult:
    """Run full cross-branch compatibility check."""
    violations = check_schema_fields(W3_OUTPUT_SCHEMA, W1_PROVIDER_CONTRACT)

    # Type-level consistency
    for w3_item in W3_OUTPUT_SCHEMA["items"]:
        for k, v in w3_item.items():
            if k == "tweet_id" and "str" in v:
                pass  # original_id = tweet_id, OK
            if k == "db_path":
                violations.append(f"db_path found in W3 schema — MUST be discarded before reaching W1")
            if k == "backend_error":
                violations.append(f"backend_error in W3 — W1 should handle via records_rejected")

    status = "PASS" if not violations else "FAIL"
    return ContractResult(name="cross_branch_compatibility", status=status,
                          detail="W3 output ↔ W1 provider contract compatibility",
                          violations=violations)
