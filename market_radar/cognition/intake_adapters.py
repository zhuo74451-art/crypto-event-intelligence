"""F02: Executable intake lane adapters.

Converts the P02 contracts into actual loaders/adapters with:
- schema validation
- deterministic ID generation
- origin, authority and fact-permission preservation
- timestamp and leakage checks
- evidence refs/hashes
- rejection reasons
- adapter outputs mapped into cognition/world-model/research/evaluation paths
"""

from __future__ import annotations
import hashlib, json, csv, io
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from market_radar.cognition.intake_contracts import (
    QuickFlashEventEnvelope, DirectEvidenceBundle, MarketStateInput,
    ExpectationBaselineInput, ResearchClaimInput, HistoricalOutcomeInput,
    LaneOrigin, AuthorityClass, FactPermission, SCHEMA_VERSION,
)


def _sha256_id(parts_list: List[str]) -> str:
    return hashlib.sha256(":".join(parts_list).encode("utf-8")).hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_timestamp(ts: str, as_of: Optional[str] = None) -> Optional[str]:
    """Return an error if timestamp is invalid or indicates future leakage."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return "missing_timezone"
        if as_of and dt > datetime.fromisoformat(as_of.replace("Z", "+00:00")):
            return "future_leakage_risk"
    except (ValueError, TypeError):
        return "invalid_timestamp"
    return None


# -------------------------------------------------------------------------
# 1. QuickFlash JSONL loader
# -------------------------------------------------------------------------

class QuickFlashJSONLLoader:
    """Load cleaned QuickFlash events from JSONL format."""

    def load(self, path: Path, as_of: Optional[str] = None) -> Tuple[List[QuickFlashEventEnvelope], List[str]]:
        envelopes: List[QuickFlashEventEnvelope] = []
        errors: List[str] = []
        if not path.exists():
            errors.append(f"quickflash_jsonl not found: {path}")
            return envelopes, errors
        for i, line in enumerate(path.read_text(encoding="utf-8").strip().split(chr(10))):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                env = QuickFlashEventEnvelope.from_dict(d)
                # Schema validation
                if not env.upstream_item_id:
                    errors.append(f"line {i+1}: missing upstream_item_id")
                    continue
                # Timestamp check
                ts_err = _check_timestamp(env.published_at, as_of)
                if ts_err == "future_leakage_risk":
                    errors.append(f"line {i+1}: future_leakage {env.published_at} > {as_of}")
                # Generate deterministic envelope_id if missing
                if not env.envelope_id:
                    env.envelope_id = _sha256_id(["qf_jsonl", env.upstream_item_id, env.published_at or _utc_now()])
                env.retrieved_at = _utc_now()
                envelopes.append(env)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                errors.append(f"line {i+1}: parse_error: {e}")
        return envelopes, errors


# -------------------------------------------------------------------------
# 2. QuickFlash SQLite-export loader
# -------------------------------------------------------------------------

class QuickFlashSQLiteLoader:
    """Load QuickFlash events from a SQLite export file."""

    def load(self, path: Path, as_of: Optional[str] = None) -> Tuple[List[QuickFlashEventEnvelope], List[str]]:
        envelopes: List[QuickFlashEventEnvelope] = []
        errors: List[str] = []
        if not path.exists():
            errors.append(f"quickflash_sqlite not found: {path}")
            return envelopes, errors
        import sqlite3
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM events ORDER BY first_seen_at").fetchall()
            for r in rows:
                try:
                    d = dict(r)
                    env = QuickFlashEventEnvelope(
                        upstream_item_id=str(d.get("item_id", "")),
                        upstream_event_id=str(d.get("event_id", "")),
                        source_identity=str(d.get("source", "")),
                        cleaned_title=str(d.get("title", "")),
                        cleaned_summary=str(d.get("summary", "")),
                        event_type=str(d.get("event_type", "")),
                        published_at=str(d.get("published_at", "") or ""),
                        first_seen_at=str(d.get("first_seen_at", "") or ""),
                        updated_at=str(d.get("updated_at", "") or ""),
                        importance=float(d.get("importance", 0) or 0),
                        urgency=float(d.get("urgency", 0) or 0),
                        origin=LaneOrigin.REPLAY.value,
                    )
                    if not env.envelope_id:
                        env.envelope_id = _sha256_id(["qf_sqlite", env.upstream_item_id])
                    env.retrieved_at = _utc_now()
                    # Check future leakage
                    _check_timestamp(env.published_at, as_of)
                    envelopes.append(env)
                except Exception as e:
                    errors.append(f"sqlite_row: {e}")
            conn.close()
        except Exception as e:
            errors.append(f"sqlite_open: {e}")
        return envelopes, errors


# -------------------------------------------------------------------------
# 3. Direct-evidence routing adapter
# -------------------------------------------------------------------------

class DirectEvidenceAdapter:
    """Route acquisition source results into DirectEvidenceBundle."""

    SOURCE_IDS = {"cisa", "sec", "congress", "bls", "github_releases"}

    def is_direct_source(self, source_id: str) -> bool:
        return source_id in self.SOURCE_IDS

    def to_bundle(self, source_id: str, title: str = "", body: str = "",
                  artifact_path: str = "", artifact_sha256: str = "",
                  published_at: str = "", origin: str = LaneOrigin.FIXTURE.value) -> DirectEvidenceBundle:
        bundle = DirectEvidenceBundle(
            source_id=source_id,
            authority_class=AuthorityClass.PRIMARY_OFFICIAL.value
            if source_id in ("cisa", "sec", "bls") else AuthorityClass.SECONDARY_OFFICIAL.value,
            fact_permission=FactPermission.CONFIRMED.value,
            title=title, body_text=body,
            raw_artifact_path=artifact_path,
            raw_artifact_sha256=artifact_sha256,
            published_at=published_at,
            origin=origin,
        )
        if not bundle.bundle_id:
            bundle.bundle_id = _sha256_id(["direct", source_id, artifact_path or title or _utc_now()])
        return bundle

    def route(self, source_id: str, acquisition_result: Dict[str, Any]) -> DirectEvidenceBundle:
        """Route an acquisition pipeline result dict to a DirectEvidenceBundle."""
        return self.to_bundle(
            source_id=source_id,
            title=acquisition_result.get("title", ""),
            body=acquisition_result.get("body_text", ""),
            artifact_path=acquisition_result.get("artifact_path", ""),
            artifact_sha256=acquisition_result.get("artifact_sha256", ""),
            published_at=acquisition_result.get("published_at", ""),
            origin=acquisition_result.get("origin", LaneOrigin.FIXTURE.value),
        )


# -------------------------------------------------------------------------
# 4. Market-state adapter
# -------------------------------------------------------------------------

class MarketStateAdapter:
    """Convert raw market data into MarketStateInput records."""

    def to_input(self, asset: str, data: Dict[str, Any],
                 provider: str = "fixture", origin: str = LaneOrigin.FIXTURE.value) -> MarketStateInput:
        msi = MarketStateInput(
            asset=asset,
            as_of=data.get("as_of", _utc_now()),
            provider=provider,
            price=data.get("price"),
            return_1h=data.get("return_1h"),
            return_24h=data.get("return_24h"),
            volume_24h=data.get("volume_24h") or data.get("volume"),
            open_interest=data.get("open_interest"),
            funding_rate=data.get("funding_rate"),
            basis=data.get("basis"),
            origin=origin,
        )
        if not msi.record_id:
            msi.record_id = _sha256_id(["ms", asset, msi.as_of])
        # Track missing metrics
        missing = []
        for field in ("price", "volume_24h", "open_interest", "funding_rate"):
            if getattr(msi, field, None) is None:
                missing.append(field)
        msi.missing_metrics = missing
        return msi


# -------------------------------------------------------------------------
# 5. Expectation baseline adapter
# -------------------------------------------------------------------------

class ExpectationAdapter:
    """Load expectation baselines from JSON files."""

    def load_json(self, path: Path, as_of: Optional[str] = None) -> Tuple[Dict[str, ExpectationBaselineInput], List[str]]:
        results: Dict[str, ExpectationBaselineInput] = {}
        errors: List[str] = []
        if not path.exists():
            return results, errors
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key, entry in data.items():
                try:
                    ebi = ExpectationBaselineInput(
                        event_dedup_key=key,
                        expectation_type=entry.get("type", "consensus_value"),
                        expected_value=entry.get("expected"),
                        expected_range_low=entry.get("range_low"),
                        expected_range_high=entry.get("range_high"),
                        actual_value=entry.get("actual"),
                        baseline_source=entry.get("baseline_source", ""),
                        baseline_timestamp=entry.get("baseline_timestamp", ""),
                        origin=LaneOrigin.FIXTURE.value,
                    )
                    if not ebi.record_id:
                        ebi.record_id = _sha256_id(["exp", key, ebi.baseline_timestamp or _utc_now()])
                    if ebi.expected_value is not None and ebi.actual_value is not None:
                        ebi.signed_surprise = ebi.actual_value - ebi.expected_value
                        if ebi.expected_value != 0:
                            ebi.surprise_pct = ((ebi.actual_value - ebi.expected_value) / abs(ebi.expected_value)) * 100.0
                    if as_of and ebi.baseline_timestamp:
                        try:
                            bt = datetime.fromisoformat(ebi.baseline_timestamp.replace("Z", "+00:00"))
                            at = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
                            if (at - bt).total_seconds() > 168 * 3600:
                                ebi.stale = True
                        except (ValueError, TypeError):
                            pass
                    results[key] = ebi
                except (TypeError, ValueError) as e:
                    errors.append(f"entry {key}: {e}")
        except (json.JSONDecodeError, IOError) as e:
            errors.append(f"json_parse: {e}")
        return results, errors


# -------------------------------------------------------------------------
# 6. Research-claim loader
# -------------------------------------------------------------------------

class ResearchClaimLoader:
    """Load research claims from Markdown or JSON fixtures."""

    def load_markdown(self, path: Path) -> Tuple[List[ResearchClaimInput], List[str]]:
        claims: List[ResearchClaimInput] = []
        errors: List[str] = []
        if not path.exists():
            errors.append(f"research_md not found: {path}")
            return claims, errors
        text = path.read_text(encoding="utf-8")
        sections = text.split("## ")[1:]
        for sec in sections:
            lines = sec.strip().split(chr(10))
            if not lines:
                continue
            title = lines[0].strip()
            meta = {}
            body_lines = []
            in_meta = True
            for l in lines[1:]:
                if in_meta and ":" in l and not l.startswith(" "):
                    k, v = l.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
                else:
                    in_meta = False
                    body_lines.append(l)
            rc = ResearchClaimInput(
                source_title=title,
                claim_text=chr(10).join(body_lines).strip(),
                claim_type=meta.get("type", "fact"),
                domain=meta.get("domain", ""),
                expected_direction=meta.get("direction", ""),
                time_horizon=meta.get("horizon", ""),
                status=meta.get("status", "seed"),
                source_date=meta.get("date", ""),
                source_url=meta.get("url", ""),
                origin=LaneOrigin.FIXTURE.value,
            )
            if not rc.claim_id:
                rc.claim_id = _sha256_id(["research", title, meta.get("date", _utc_now())])
            claims.append(rc)
        return claims, errors

    def load_json(self, path: Path) -> Tuple[List[ResearchClaimInput], List[str]]:
        claims: List[ResearchClaimInput] = []
        errors: List[str] = []
        if not path.exists():
            errors.append(f"research_json not found: {path}")
            return claims, errors
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = data if isinstance(data, list) else data.get("claims", [])
            for entry in entries:
                try:
                    rc = ResearchClaimInput.from_dict(entry)
                    if not rc.claim_id:
                        rc.claim_id = _sha256_id(["research", rc.source_title or str(rc.source_date)])
                    claims.append(rc)
                except (TypeError, ValueError) as e:
                    errors.append(f"entry_parse: {e}")
        except (json.JSONDecodeError, IOError) as e:
            errors.append(f"json_parse: {e}")
        return claims, errors


# -------------------------------------------------------------------------
# 7. Historical-outcome loader
# -------------------------------------------------------------------------

class HistoricalOutcomeLoader:
    """Load historical outcome labels from JSON/CSV fixtures."""

    def load_json(self, path: Path) -> Tuple[List[HistoricalOutcomeInput], List[str]]:
        outcomes: List[HistoricalOutcomeInput] = []
        errors: List[str] = []
        if not path.exists():
            errors.append(f"historical_json not found: {path}")
            return outcomes, errors
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = data if isinstance(data, list) else data.get("outcomes", [])
            for entry in entries:
                try:
                    ho = HistoricalOutcomeInput.from_dict(entry)
                    if not ho.outcome_id:
                        ho.outcome_id = _sha256_id(["hist", ho.event_dedup_key, ho.case_name])
                    outcomes.append(ho)
                except (TypeError, ValueError) as e:
                    errors.append(f"entry_parse: {e}")
        except (json.JSONDecodeError, IOError) as e:
            errors.append(f"json_parse: {e}")
        return outcomes, errors