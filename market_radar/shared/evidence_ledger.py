"""Market Radar v117 — Evidence Ledger (Shared Pipeline).

Redacted evidence records for the shared pipeline.

Requirements:
  - proof is sha256-like (redacted fingerprint)
  - No raw token/chat_id/message_id stored
  - Records card_family, pipeline_version, timestamp, production_send=false, proof
  - Supports JSONL output
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from market_radar.shared.models import (
    CardFamily,
    EvidenceRecord,
    TGTestSendResult,
    china_now,
    PIPELINE_VERSION,
    sha256_short,
)


class EvidenceLedger:
    """Records redacted evidence entries for each pipeline run.

    All sensitive data is replaced with SHA-256 fingerprints.
    No raw token/chat_id/message_id is ever written.
    """

    def __init__(self, ledger_version: str = PIPELINE_VERSION):
        self._version = ledger_version
        self._entries: list[EvidenceRecord] = []

    def record(
        self,
        card_family: CardFamily,
        asset_or_topic: str,
        quality_gate_allow: Optional[bool] = None,
        send_readiness_allow: Optional[bool] = None,
        tg_result: Optional[TGTestSendResult] = None,
        event_id: Optional[str] = None,
    ) -> EvidenceRecord:
        """Create and store a redacted evidence entry.

        The proof is a SHA-256 hash of key pipeline metadata — never raw credentials.
        """
        # Build proof from redacted metadata only
        proof_parts = [
            str(card_family.value),
            self._version,
            china_now(),
            str(quality_gate_allow) if quality_gate_allow is not None else "None",
            str(send_readiness_allow) if send_readiness_allow is not None else "None",
        ]
        proof = sha256_short("|".join(proof_parts))

        # If TG was attempted, include redacted proofs
        if tg_result:
            if tg_result.message_id_proof:
                proof = tg_result.message_id_proof  # Use the TG-level proof
            elif tg_result.token_proof:
                proof = sha256_short(proof + (tg_result.token_proof or ""))

        entry = EvidenceRecord(
            card_family=card_family,
            pipeline_version=self._version,
            timestamp=china_now(),
            production_send=False,
            proof=proof,
            event_id=event_id,
            asset_or_topic=asset_or_topic,
            quality_gate_allow=quality_gate_allow,
            send_readiness_allow=send_readiness_allow,
            tg_test_sent=tg_result.success if tg_result else None,
            tg_status=tg_result.status if tg_result else None,
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[EvidenceRecord]:
        """Return all recorded entries."""
        return list(self._entries)

    def write_jsonl(self, path: str | Path) -> Path:
        """Write all entries to a JSONL file.

        Returns the path written.
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in self._entries:
                f.write(json.dumps(entry.as_dict(), ensure_ascii=False) + "\n")
        return output_path

    def write_json(self, path: str | Path) -> Path:
        """Write all entries as a JSON array."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [e.as_dict() for e in self._entries],
                f,
                ensure_ascii=False,
                indent=2,
            )
        return output_path

    def verify_no_raw_secrets(self) -> tuple[bool, list[str]]:
        """Verify that no entry contains raw token/chat_id/message_id patterns.

        Returns (clean: bool, violations: list[str]).
        """
        violations: list[str] = []
        for i, entry in enumerate(self._entries):
            d = json.dumps(entry.as_dict(), ensure_ascii=False)

            # Check for raw token pattern (digits:alphanumeric)
            import re
            raw_token_pat = re.compile(r'\b\d{8,10}:[A-Za-z0-9_-]{20,}\b')
            raw_chat_pat = re.compile(r'(?<!_)chat_id["\']?\s*:\s*["\']-?\d{5,}["\']')

            if raw_token_pat.search(d):
                violations.append(f"Entry {i}: potential raw token pattern detected")
            if raw_chat_pat.search(d):
                violations.append(f"Entry {i}: potential raw chat_id pattern detected")

            # Verify proof is hashed, not a raw number
            proof = entry.proof or ""
            if proof.startswith("sha256:"):
                continue  # Good — redacted
            if proof.isdigit():
                violations.append(f"Entry {i}: proof is a raw number (not redacted)")

        return len(violations) == 0, violations


def create_evidence_ledger() -> EvidenceLedger:
    """Factory: create the evidence ledger."""
    return EvidenceLedger()
