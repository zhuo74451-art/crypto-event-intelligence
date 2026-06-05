"""Market Radar v1.16-J — News Event Market Impact Real Free Public Source TG Test Send Tests

Validates all v116J outputs meet the acceptance criteria defined in the task spec.

Tests cover:
  - All v116J output files exist
  - card_family == news_event_market_impact
  - real_public_source_called == true
  - real_external_api_called == true (unless source blocked)
  - fixture_only == false
  - api_key_required == false
  - Raw source records have source/title/url/published_at/fetched_at
  - No news full text saved
  - result is one of the 5 allowed audit_result values
  - production_send_ready == false
  - prod_state_write == false
  - ai_model_called == false
  - daemon_or_loop_started == false
  - files_deleted == false
  - secret_preflight_run == true
  - Cards contain attribution risk disclaimer
  - No token/key/cookie/password/chat_id plaintext in any output
  - TG success → redacted proof present
  - TG blocked → real blocked reason present
  - Gate not passed → no TG send
  - Cards do not claim false causality
  - No investment advice in cards
  - News full text not saved in any output

Usage:
    python scripts/test_market_radar_v116j_news_event_market_impact_real_free_public_source_tg_test_send_one_shot.py
"""

import json
import re
import sys
import unittest
from pathlib import Path


# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]

SEND_RESULT_JSON = ROOT / "results" / "market_radar_v116j_news_event_market_impact_tg_test_send_result.json"
RAW_SOURCES_JSON = ROOT / "results" / "market_radar_v116j_news_event_market_impact_raw_sources.json"
EVENT_RECORDS_JSONL = ROOT / "results" / "market_radar_v116j_news_event_market_impact_event_records.jsonl"
MARKET_SNAPSHOTS_JSON = ROOT / "results" / "market_radar_v116j_news_event_market_impact_market_snapshots.json"
CARD_RECORDS_JSONL = ROOT / "results" / "market_radar_v116j_news_event_market_impact_card_records.jsonl"
QUALITY_GATE_JSONL = ROOT / "results" / "market_radar_v116j_news_event_market_impact_quality_gate_records.jsonl"
SEND_READINESS_JSONL = ROOT / "results" / "market_radar_v116j_news_event_market_impact_send_readiness_records.jsonl"
TG_SEND_ATTEMPTS_JSONL = ROOT / "results" / "market_radar_v116j_news_event_market_impact_tg_send_attempts.jsonl"
SEND_REPORT_MD = ROOT / "runs" / "market_radar" / "v116j_news_event_market_impact_tg_test_send_report.md"
HANDOFF_MD = ROOT / "runs" / "market_radar" / "v116j_news_event_market_impact_local_only_handoff.md"
CARD_PREVIEW_MD = ROOT / "runs" / "market_radar" / "v116j_news_event_market_impact_card_preview.md"

ALLOWED_AUDIT_RESULTS = [
    "real_free_public_source_tg_test_sent",
    "real_public_source_card_ready_tg_blocked_missing_sender",
    "blocked_public_source_unavailable",
    "blocked_market_snapshot_unavailable",
    "blocked_gate_not_passed",
]

FORBIDDEN_PATTERNS = [
    r'\b[0-9]{8,10}:[A-Za-z0-9_-]{35,}\b',
    r'bot[0-9]{8,10}:',
    r'api_key\s*[:=]\s*["\'][A-Za-z0-9_-]{20,}',
    r'chat_id\s*[:=]\s*["\']-?[0-9]{5,}',
    r'password\s*[:=]\s*["\'][^"\']+["\']',
    r'secret\s*[:=]\s*["\'][A-Za-z0-9_-]{10,}',
    r'cookie\s*[:=]\s*["\'][^"\']+["\']',
]

RAW_TOKEN_PATTERN = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
RAW_CHAT_ID_PATTERN = re.compile(r'chat_id["\']?\s*:\s*["\']-?[0-9]{5,}["\']')

REQUIRED_SOURCE_FIELDS = ["source_name", "title", "url", "published_at", "fetched_at"]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def check_no_forbidden_patterns(text: str) -> list[str]:
    violations = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"Pattern matched: {pattern[:60]}...")
    return violations


def check_no_raw_token(text: str) -> bool:
    return not bool(RAW_TOKEN_PATTERN.search(text))


def check_no_raw_chat_id_assignment(text: str) -> bool:
    return not bool(RAW_CHAT_ID_PATTERN.search(text))


def has_attribution_disclaimer(text: str) -> bool:
    """Check if text contains attribution risk disclaimer."""
    disclaimers = [
        "事件影响观察", "不构成因果证明", "不构成投资建议",
        "不构成任何投资建议", "not constitute",
    ]
    return any(d in text for d in disclaimers)


def has_false_causality(text: str) -> bool:
    """Check if text claims false causality."""
    false_claims = ["导致暴涨", "导致暴跌", "必然上涨", "必然下跌"]
    for claim in false_claims:
        if claim in text:
            idx = text.find(claim)
            context_start = max(0, idx - 15)
            context = text[context_start:idx + len(claim) + 5]
            if "不" not in context and "不能" not in context and "非" not in context:
                return True
    return False


# ── Test Case ────────────────────────────────────────────────────────────

class TestV116JNewsEventMarketImpactRealFreePublicSourceTgTestSend(unittest.TestCase):
    """Tests for v116J News Event Market Impact Real Free Public Source TG Test Send."""

    @classmethod
    def setUpClass(cls):
        cls.send_result = None
        cls.raw_sources = None
        cls.event_records = []
        cls.market_snapshot = None
        cls.card_records = []
        cls.quality_gates = []
        cls.send_readiness = []
        cls.tg_attempts = []
        cls.report_text = ""
        cls.handoff_text = ""
        cls.preview_text = ""

        if SEND_RESULT_JSON.exists():
            with open(SEND_RESULT_JSON, "r", encoding="utf-8") as f:
                cls.send_result = json.load(f)

        if RAW_SOURCES_JSON.exists():
            with open(RAW_SOURCES_JSON, "r", encoding="utf-8") as f:
                cls.raw_sources = json.load(f)

        if EVENT_RECORDS_JSONL.exists():
            cls.event_records = load_jsonl(EVENT_RECORDS_JSONL)

        if MARKET_SNAPSHOTS_JSON.exists():
            with open(MARKET_SNAPSHOTS_JSON, "r", encoding="utf-8") as f:
                cls.market_snapshot = json.load(f)

        if CARD_RECORDS_JSONL.exists():
            cls.card_records = load_jsonl(CARD_RECORDS_JSONL)

        if QUALITY_GATE_JSONL.exists():
            cls.quality_gates = load_jsonl(QUALITY_GATE_JSONL)

        if SEND_READINESS_JSONL.exists():
            cls.send_readiness = load_jsonl(SEND_READINESS_JSONL)

        if TG_SEND_ATTEMPTS_JSONL.exists():
            cls.tg_attempts = load_jsonl(TG_SEND_ATTEMPTS_JSONL)

        if SEND_REPORT_MD.exists():
            with open(SEND_REPORT_MD, "r", encoding="utf-8") as f:
                cls.report_text = f.read()

        if HANDOFF_MD.exists():
            with open(HANDOFF_MD, "r", encoding="utf-8") as f:
                cls.handoff_text = f.read()

        if CARD_PREVIEW_MD.exists():
            with open(CARD_PREVIEW_MD, "r", encoding="utf-8") as f:
                cls.preview_text = f.read()

    # ══════════════════════════════════════════════════════════════════════
    # File existence tests
    # ══════════════════════════════════════════════════════════════════════

    def test_01_send_result_json_exists(self):
        self.assertTrue(SEND_RESULT_JSON.exists(), f"Missing: {SEND_RESULT_JSON}")

    def test_02_send_report_md_exists(self):
        self.assertTrue(SEND_REPORT_MD.exists(), f"Missing: {SEND_REPORT_MD}")

    def test_03_handoff_md_exists(self):
        self.assertTrue(HANDOFF_MD.exists(), f"Missing: {HANDOFF_MD}")

    def test_04_raw_sources_json_exists(self):
        self.assertTrue(RAW_SOURCES_JSON.exists(), f"Missing: {RAW_SOURCES_JSON}")

    def test_05_event_records_jsonl_exists(self):
        self.assertTrue(EVENT_RECORDS_JSONL.exists(), f"Missing: {EVENT_RECORDS_JSONL}")

    def test_06_market_snapshots_json_exists(self):
        self.assertTrue(MARKET_SNAPSHOTS_JSON.exists(), f"Missing: {MARKET_SNAPSHOTS_JSON}")

    def test_07_card_records_jsonl_exists(self):
        self.assertTrue(CARD_RECORDS_JSONL.exists(), f"Missing: {CARD_RECORDS_JSONL}")

    def test_08_quality_gate_jsonl_exists(self):
        self.assertTrue(QUALITY_GATE_JSONL.exists(), f"Missing: {QUALITY_GATE_JSONL}")

    def test_09_send_readiness_jsonl_exists(self):
        self.assertTrue(SEND_READINESS_JSONL.exists(), f"Missing: {SEND_READINESS_JSONL}")

    def test_10_tg_send_attempts_jsonl_exists(self):
        self.assertTrue(TG_SEND_ATTEMPTS_JSONL.exists(), f"Missing: {TG_SEND_ATTEMPTS_JSONL}")

    def test_11_card_preview_md_exists(self):
        self.assertTrue(CARD_PREVIEW_MD.exists(), f"Missing: {CARD_PREVIEW_MD}")

    # ══════════════════════════════════════════════════════════════════════
    # Core field tests
    # ══════════════════════════════════════════════════════════════════════

    def test_12_card_family_correct(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertEqual(self.send_result.get("card_family"), "news_event_market_impact")

    def test_13_real_public_source_called(self):
        """real_public_source_called must be true (unless ALL sources unreachable)."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        real_source = self.send_result.get("real_public_source_called", False)
        if not real_source:
            audit = self.send_result.get("audit_result", "")
            self.assertEqual(audit, "blocked_public_source_unavailable",
                           f"real_public_source_called=false but audit_result={audit}, expected blocked_public_source_unavailable")

    def test_14_fixture_only_is_false(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("fixture_only", True))

    def test_15_api_key_required_is_false(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("api_key_required", True))

    def test_16_production_send_ready_is_false(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("production_send_ready", True))

    def test_17_prod_state_write_is_false(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("prod_state_write", True))

    def test_18_ai_model_called_is_false(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("ai_model_called", True))

    def test_19_daemon_or_loop_started_is_false(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("daemon_or_loop_started", True))

    def test_20_files_deleted_is_false(self):
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        self.assertFalse(self.send_result.get("files_deleted", True))

    # ══════════════════════════════════════════════════════════════════════
    # Raw source record tests
    # ══════════════════════════════════════════════════════════════════════

    def test_21_raw_sources_has_articles(self):
        """Raw sources must have articles list (can be empty if all blocked)."""
        self.assertIsNotNone(self.raw_sources, "Raw sources JSON not loaded")
        self.assertIn("articles", self.raw_sources, "Raw sources missing 'articles' field")
        self.assertIsInstance(self.raw_sources["articles"], list,
                            "articles must be a list")

    def test_22_raw_sources_have_required_fields(self):
        """Each article in raw sources must have source/title/url/published_at/fetched_at."""
        articles = self.raw_sources.get("articles", []) if self.raw_sources else []
        for article in articles:
            for field in REQUIRED_SOURCE_FIELDS:
                self.assertIn(field, article,
                            f"Article '{article.get('title', '?')[:60]}' missing field: {field}")

    def test_23_no_full_text_in_raw_sources(self):
        """Raw sources must NOT contain article body/full text."""
        articles = self.raw_sources.get("articles", []) if self.raw_sources else []
        for article in articles:
            # Check no body field (full text)
            if "body" in article:
                body = article.get("body", "")
                self.assertEqual(len(body), 0,
                               f"Article has non-empty body (full text): {article.get('title', '')[:60]}")
            # Check summary_snippet max 280 chars
            snippet = article.get("summary_snippet", "")
            self.assertLessEqual(len(snippet), 280,
                               f"summary_snippet exceeds 280 chars: {len(snippet)} chars")

    def test_24_raw_sources_has_metadata(self):
        """Raw sources must have source metadata."""
        self.assertIsNotNone(self.raw_sources, "Raw sources JSON not loaded")
        self.assertIn("source_results", self.raw_sources)
        self.assertIn("sources_attempted", self.raw_sources)
        self.assertIn("sources_succeeded", self.raw_sources)
        self.assertIn("total_articles", self.raw_sources)
        self.assertIn("api_key_required", self.raw_sources)
        self.assertIn("news_full_text_saved", self.raw_sources)

    # ══════════════════════════════════════════════════════════════════════
    # Event record tests
    # ══════════════════════════════════════════════════════════════════════

    def test_25_event_records_have_required_fields(self):
        """Event records must have required fields."""
        required = [
            "card_family", "source_name", "title", "url",
            "assets", "event_type", "intensity", "attribution_risk",
        ]
        for ev in self.event_records:
            for field in required:
                self.assertIn(field, ev,
                            f"Event '{ev.get('title', '?')[:60]}' missing field: {field}")

    def test_26_event_card_family_correct(self):
        """All events must have card_family == news_event_market_impact."""
        for ev in self.event_records:
            self.assertEqual(ev.get("card_family"), "news_event_market_impact",
                           f"Wrong card_family in event: {ev.get('title', '')[:60]}")

    def test_27_event_ai_model_called_false(self):
        """Events must have ai_model_called == false."""
        for ev in self.event_records:
            self.assertFalse(ev.get("ai_model_called", True),
                           f"Event has ai_model_called=true: {ev.get('title', '')[:60]}")

    def test_28_event_api_key_required_false(self):
        """Events must have api_key_required == false."""
        for ev in self.event_records:
            self.assertFalse(ev.get("api_key_required", True),
                           f"Event has api_key_required=true: {ev.get('title', '')[:60]}")

    def test_29_event_is_fixture_false(self):
        """Events must have is_fixture == false."""
        for ev in self.event_records:
            self.assertFalse(ev.get("is_fixture", True),
                           f"Event has is_fixture=true: {ev.get('title', '')[:60]}")

    def test_30_event_has_valid_intensity(self):
        """Event intensity must be high/medium/low."""
        valid = {"high", "medium", "low"}
        for ev in self.event_records:
            intensity = ev.get("intensity", "")
            self.assertIn(intensity, valid,
                        f"Event '{ev.get('title', '')[:60]}' has invalid intensity: {intensity}")

    def test_31_event_has_valid_attribution(self):
        """Event attribution_risk must be direct/indirect (unsafe should be filtered)."""
        valid = {"direct", "indirect"}
        for ev in self.event_records:
            attr = ev.get("attribution_risk", "")
            self.assertIn(attr, valid,
                        f"Event '{ev.get('title', '')[:60]}' has unsafe attribution: {attr}")

    def test_32_event_has_valid_event_type(self):
        """Event type must be one of the known types or 'other'."""
        known_types = {
            "ETF", "regulatory", "lawsuit", "approval", "hack", "exploit",
            "listing", "delisting", "unlock", "partnership", "outage",
            "macro", "whale", "funding", "airdrop", "mainnet", "upgrade", "other",
        }
        for ev in self.event_records:
            etype = ev.get("event_type", "")
            self.assertIn(etype, known_types,
                        f"Event '{ev.get('title', '')[:60]}' has unknown event_type: {etype}")

    def test_33_event_has_extraction_method(self):
        """Events must indicate extraction_method."""
        for ev in self.event_records:
            self.assertIn("extraction_method", ev,
                        f"Event missing extraction_method: {ev.get('title', '')[:60]}")
            method = ev.get("extraction_method", "")
            self.assertIn("rule", method.lower(),
                        f"Event extraction_method should be rule-based: {method}")

    def test_34_event_news_full_text_not_saved(self):
        """Events must have news_full_text_saved == false."""
        for ev in self.event_records:
            self.assertFalse(ev.get("news_full_text_saved", True))

    # ══════════════════════════════════════════════════════════════════════
    # Market snapshot tests
    # ══════════════════════════════════════════════════════════════════════

    def test_35_market_snapshot_has_metadata(self):
        """Market snapshot must have metadata fields."""
        self.assertIsNotNone(self.market_snapshot, "Market snapshot not loaded")
        self.assertIn("api_key_required", self.market_snapshot)
        self.assertIn("real_external_api_called", self.market_snapshot)
        self.assertFalse(self.market_snapshot.get("api_key_required", True))

    # ══════════════════════════════════════════════════════════════════════
    # audit_result test
    # ══════════════════════════════════════════════════════════════════════

    def test_36_audit_result_is_allowed_value(self):
        """audit_result must be one of the 5 allowed values."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        audit = self.send_result.get("audit_result", "")
        self.assertIn(audit, ALLOWED_AUDIT_RESULTS,
                      f"audit_result '{audit}' not in allowed: {ALLOWED_AUDIT_RESULTS}")

    # ══════════════════════════════════════════════════════════════════════
    # News-specific: attribution risk disclaimer tests
    # ══════════════════════════════════════════════════════════════════════

    def _is_real_card(self, card_text: str) -> bool:
        """Check if this is a real rendered card (not a [BLOCKED] stub)."""
        return not card_text.startswith("[BLOCKED]")

    def test_37_cards_have_attribution_disclaimer(self):
        """Real (non-blocked) cards must contain attribution risk disclaimer."""
        for card in self.card_records:
            card_text = card.get("card_text", "")
            if not self._is_real_card(card_text):
                continue  # Blocked stub cards don't need full disclaimer
            self.assertTrue(has_attribution_disclaimer(card_text),
                          f"Card '{card.get('title', '?')[:60]}' missing attribution disclaimer")

    def test_38_cards_no_false_causality(self):
        """Cards must NOT claim false causality."""
        for card in self.card_records:
            card_text = card.get("card_text", "")
            self.assertFalse(has_false_causality(card_text),
                           f"Card '{card.get('title', '?')[:60]}' claims false causality")

    def test_39_cards_no_investment_advice(self):
        """Cards must not contain investment advice (with context-awareness for disclaimers)."""
        bad_phrases_standalone = [
            "买入", "卖出", "做多", "做空", "all in", "满仓", "清仓",
            "梭哈", "暴富", "翻倍",
        ]
        bad_phrases_contextual = [
            "开空", "开多", "必涨", "必跌", "稳赚", "抄底",
        ]
        negations = ["不包含", "不含", "不构成", "不得", "不能",
                    "不涉及", "不提供", "禁止", "避免", "严禁"]
        for card in self.card_records:
            card_text = card.get("card_text", "")
            card_lower = card_text.lower()
            for phrase in bad_phrases_standalone:
                self.assertNotIn(phrase, card_text,
                               f"Card '{card.get('title', '?')[:60]}' contains '{phrase}'")
            for phrase in bad_phrases_contextual:
                if phrase in card_lower:
                    idx = card_lower.find(phrase)
                    context_before = card_lower[max(0, idx-50):idx]
                    is_negated = any(neg in context_before for neg in negations)
                    if not is_negated:
                        self.fail(
                            f"Card '{card.get('title', '?')[:60]}' contains '{phrase}' "
                            f"outside of disclaimer context"
                        )

    def test_40_cards_mention_risk_warning(self):
        """Real (non-blocked) cards must mention risk/conservative stance."""
        risk_keywords = ["风险", "观察", "不构成", "谨慎", "免责", "disclaimer"]
        for card in self.card_records:
            card_text = card.get("card_text", "")
            if not self._is_real_card(card_text):
                continue  # Blocked stub cards don't need full risk warning
            has_any = any(kw in card_text for kw in risk_keywords)
            self.assertTrue(has_any,
                          f"Card '{card.get('title', '?')[:60]}' missing risk warning")

    # ══════════════════════════════════════════════════════════════════════
    # Secret preflight tests
    # ══════════════════════════════════════════════════════════════════════

    def test_41_secret_preflight_run(self):
        """secret_preflight_run must be true."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        preflight_run = self.send_result.get("secret_preflight_run", False)
        self.assertTrue(preflight_run, "v116J requires secret_preflight_run == true")

    def test_42_preflight_boolean_flags_present(self):
        """Send result must have boolean flags for token/chat_id presence."""
        self.assertIsNotNone(self.send_result, "Send result JSON not loaded")
        bot_present = self.send_result.get("telegram_bot_token_present")
        chat_present = self.send_result.get("telegram_chat_id_present")
        self.assertIsInstance(bot_present, bool, "telegram_bot_token_present must be bool")
        self.assertIsInstance(chat_present, bool, "telegram_chat_id_present must be bool")

    # ══════════════════════════════════════════════════════════════════════
    # TG send / blocked reason tests
    # ══════════════════════════════════════════════════════════════════════

    def test_43_tg_attempt_has_required_fields(self):
        """TG send attempts must have attempted, target_type, one_shot fields."""
        for rec in self.tg_attempts:
            self.assertIn("attempted", rec)
            if rec.get("attempted", False):
                self.assertIn("target_type", rec)
                self.assertEqual(rec.get("target_type"), "test_group")
                self.assertTrue(rec.get("one_shot", False))

    def test_44_tg_success_has_redacted_proof(self):
        """If TG sent successfully, must have redacted message proof."""
        for rec in self.tg_attempts:
            if rec.get("success", False):
                self.assertTrue(rec.get("message_id_present", False))
                self.assertIsNotNone(rec.get("message_id_redacted"))
                redacted = rec.get("message_id_redacted", "")
                self.assertTrue(redacted.startswith("sha256:"),
                              f"message_id_redacted must be sha256 hashed, got: {redacted[:30]}")

    def test_45_tg_blocked_has_real_reason(self):
        """If TG blocked, must have a real blocked_reason."""
        for rec in self.tg_attempts:
            if not rec.get("success", False) and rec.get("attempted", False):
                self.assertIn("blocked_reason", rec)
                self.assertIsNotNone(rec.get("blocked_reason"))

    def test_46_tg_blocked_not_masquerading_as_success(self):
        """TG blocked must have success: false."""
        for rec in self.tg_attempts:
            if rec.get("blocked_reason"):
                self.assertFalse(rec.get("success", True))

    def test_47_gate_not_passed_no_tg_send(self):
        """If quality gate is not passed, TG must not be sent."""
        for i, qg in enumerate(self.quality_gates):
            if not qg.get("quality_gate_passed", True):
                if i < len(self.tg_attempts):
                    ta = self.tg_attempts[i]
                    self.assertFalse(ta.get("success", True),
                                   f"QG not passed but TG success=true for entry {i}")
                    self.assertFalse(ta.get("attempted", False),
                                   f"QG not passed but TG attempted=true for entry {i}")

    # ══════════════════════════════════════════════════════════════════════
    # Secret leak prevention tests
    # ══════════════════════════════════════════════════════════════════════

    def test_50_no_forbidden_patterns_in_send_result(self):
        """Send result JSON must not contain token/key/password patterns."""
        if self.send_result:
            result_str = json.dumps(self.send_result, ensure_ascii=False)
            violations = check_no_forbidden_patterns(result_str)
            self.assertEqual(len(violations), 0,
                           f"Send result contains forbidden patterns: {violations}")

    def test_51_no_forbidden_patterns_in_report(self):
        """Report must not contain forbidden patterns."""
        violations = check_no_forbidden_patterns(self.report_text)
        self.assertEqual(len(violations), 0,
                       f"Report contains forbidden patterns: {violations}")

    def test_52_no_forbidden_patterns_in_handoff(self):
        """Handoff must not contain forbidden patterns."""
        violations = check_no_forbidden_patterns(self.handoff_text)
        self.assertEqual(len(violations), 0,
                       f"Handoff contains forbidden patterns: {violations}")

    def test_53_no_raw_token_in_send_result(self):
        """Send result must not contain raw TELEGRAM_BOT_TOKEN pattern."""
        if self.send_result:
            result_str = json.dumps(self.send_result, ensure_ascii=False)
            self.assertTrue(check_no_raw_token(result_str),
                           "Send result contains raw TELEGRAM_BOT_TOKEN pattern")

    def test_54_no_raw_chat_id_in_send_result(self):
        """Send result must not contain raw chat_id."""
        if self.send_result:
            result_str = json.dumps(self.send_result, ensure_ascii=False)
            self.assertTrue(check_no_raw_chat_id_assignment(result_str),
                           "Send result contains raw chat_id")

    def test_55_no_raw_token_in_report(self):
        """Report must not contain raw token pattern."""
        self.assertTrue(check_no_raw_token(self.report_text))

    def test_56_no_raw_chat_id_in_report(self):
        """Report must not contain raw chat_id."""
        self.assertTrue(check_no_raw_chat_id_assignment(self.report_text))

    def test_57_no_raw_token_in_handoff(self):
        """Handoff must not contain raw token pattern."""
        self.assertTrue(check_no_raw_token(self.handoff_text))

    def test_58_no_raw_chat_id_in_handoff(self):
        """Handoff must not contain raw chat_id."""
        self.assertTrue(check_no_raw_chat_id_assignment(self.handoff_text))

    def test_59_all_outputs_clean(self):
        """All JSONL/JSON outputs must not contain forbidden patterns."""
        for path in [
            RAW_SOURCES_JSON, EVENT_RECORDS_JSONL, MARKET_SNAPSHOTS_JSON,
            CARD_RECORDS_JSONL, QUALITY_GATE_JSONL, SEND_READINESS_JSONL,
            TG_SEND_ATTEMPTS_JSONL,
        ]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                violations = check_no_forbidden_patterns(content)
                self.assertEqual(len(violations), 0,
                               f"{path.name} contains forbidden patterns: {violations}")

    def test_60_no_full_text_in_event_records(self):
        """Event records must not contain news full text / body."""
        for ev in self.event_records:
            if "body" in ev:
                body = ev.get("body", "")
                self.assertEqual(len(body or ""), 0,
                               f"Event has non-empty body (full text): {ev.get('title', '')[:60]}")

    # ══════════════════════════════════════════════════════════════════════
    # Safety flag tests
    # ══════════════════════════════════════════════════════════════════════

    def test_61_report_mentions_preflight(self):
        """Report must mention safe secret preflight or safety."""
        combined = (self.report_text + self.handoff_text).lower()
        has_safety = ("preflight" in combined or "safety" in combined or
                      "PASS" in self.handoff_text)
        self.assertTrue(has_safety, "Report/handoff must mention safety")

    def test_62_report_mentions_test_group(self):
        """Report must indicate test group (not production)."""
        has_test = ("test_group" in self.report_text.lower() or
                    "test group" in self.report_text.lower() or
                    "测试群" in self.report_text)
        self.assertTrue(has_test, "Report must mention test group context")

    def test_63_report_mentions_one_shot(self):
        """Report must mention one-shot execution."""
        combined = (self.report_text + self.handoff_text).lower()
        has_oneshot = ("one-shot" in combined or "one_shot" in combined or "oneshot" in combined)
        self.assertTrue(has_oneshot, "Must mention one-shot execution")

    def test_64_audit_result_in_report(self):
        """Report must contain the audit_result value."""
        if self.send_result:
            audit = self.send_result.get("audit_result", "")
            if audit:
                self.assertTrue(audit.lower() in self.report_text.lower(),
                              f"Report must contain audit_result '{audit}'")

    def test_65_no_fixture_only_true(self):
        """No output should claim fixture_only: true."""
        for path in [SEND_RESULT_JSON]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                matches = re.findall(r'"fixture_only"\s*:\s*true', content, re.IGNORECASE)
                self.assertEqual(len(matches), 0, f"{path.name} contains fixture_only: true")

    def test_66_no_production_send_ready_true(self):
        """No output should claim production_send_ready: true."""
        for path in [SEND_RESULT_JSON, SEND_READINESS_JSONL]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                matches = re.findall(r'"production_send_ready"\s*:\s*true', content, re.IGNORECASE)
                self.assertEqual(len(matches), 0,
                               f"{path.name} contains production_send_ready: true")

    def test_67_no_prod_state_write_true(self):
        """No output should claim prod_state_write: true."""
        if SEND_RESULT_JSON.exists():
            with open(SEND_RESULT_JSON, "r", encoding="utf-8") as f:
                content = f.read()
            matches = re.findall(r'"prod_state_write"\s*:\s*true', content, re.IGNORECASE)
            self.assertEqual(len(matches), 0)

    def test_68_news_full_text_saved_false(self):
        """Send result must have news_full_text_saved == false."""
        self.assertIsNotNone(self.send_result, "Send result not loaded")
        self.assertFalse(self.send_result.get("news_full_text_saved", True))

    def test_69_raw_sources_reports_sources_attempted(self):
        """Raw sources must report how many sources were attempted."""
        self.assertIsNotNone(self.raw_sources, "Raw sources not loaded")
        attempted = self.raw_sources.get("sources_attempted", 0)
        self.assertGreater(attempted, 0, "At least 1 source must be attempted")

    def test_70_no_full_article_in_raw_sources(self):
        """Raw sources must not have full article content."""
        articles = self.raw_sources.get("articles", []) if self.raw_sources else []
        full_text_fields = ["content", "full_text", "body", "article_body", "html"]
        for article in articles:
            for field in full_text_fields:
                if field in article:
                    val = article.get(field, "")
                    if isinstance(val, str):
                        self.assertLess(len(val), 300,
                                      f"Article has {field} with {len(val)} chars (potential full text)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
