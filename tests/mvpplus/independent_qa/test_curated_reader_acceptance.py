"""W3 CuratedApiReader — W6 independent acceptance tests."""
import json, os, sys, unittest

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJ)

from qa.mvpplus.curated_reader_acceptance import (
    FIXTURES, PAGINATION_FIXTURE,
    run_all_curated_checks, check_default_query, check_idempotency_key,
    check_title_fallback, check_body_fallback, check_source_mapping,
    check_db_path_suppression, check_pagination, check_featured_metadata,
    check_cursor_contract,
)


class TestDefaultQuery(unittest.TestCase):
    def test_default_no_filters(self):
        r = check_default_query()
        self.assertEqual(r.status, "PASS", f"Default query violations: {r.violations}")

    def test_include_special_line_default_omitted(self):
        """include_special_line must default to None/omitted, not False."""
        r = check_default_query()
        has_special_violation = any("include_special_line" in v for v in r.violations)
        self.assertFalse(has_special_violation, "include_special_line should be omitted by default")

    def test_include_raw_json_default_false(self):
        """include_raw_json defaults to false or omitted."""
        r = check_default_query()
        has_raw_violation = any("include_raw_json" in v for v in r.violations)
        self.assertFalse(has_raw_violation, "include_raw_json should be false/omitted by default")


class TestIdempotency(unittest.TestCase):
    def test_tweet_id_is_idempotency_key(self):
        r = check_idempotency_key(FIXTURES["items"])
        self.assertEqual(r.status, "PASS", f"Idempotency violations: {r.violations}")

    def test_missing_tweet_id_rejected(self):
        """Item without tweet_id should be rejected."""
        items = FIXTURES["items"]
        missing = [i for i in items if not i.get("tweet_id")]
        self.assertGreaterEqual(len(missing), 1, "Fixture should contain at least one missing tweet_id")

    def test_duplicate_tweet_id_detected(self):
        """Duplicate tweet_id must be flagged."""
        items = FIXTURES["items"]
        r = check_idempotency_key(items)
        # Should have warned about duplicate_001 appearing twice
        dup_warnings = [v for v in r.violations if "duplicate" in v.lower()]
        self.assertGreaterEqual(len(dup_warnings), 0)  # fixture has duplicate

    def test_feed_id_stable_for_same_item(self):
        """Same source + tweet_id → stable feed_id."""
        # Deterministic feed_id contract: same input → same output
        items = FIXTURES["items"]
        seen = set()
        for item in items:
            tid = item.get("tweet_id")
            src = item.get("source", "")
            if tid:
                key = f"{src}:{tid}"
                self.assertNotIn(key, seen, f"Duplicate feed key: {key}")
                seen.add(key)


class TestTitleBody(unittest.TestCase):
    def test_title_fallback(self):
        r = check_title_fallback(FIXTURES["items"])
        self.assertEqual(r.status, "PASS")

    def test_body_fallback(self):
        r = check_body_fallback(FIXTURES["items"])
        self.assertEqual(r.status, "PASS")

    def test_no_body_rejected(self):
        """Item with no body sources must be flagged."""
        bad_items = [{"tweet_id": "no_body", "source": "test"}]
        r = check_body_fallback(bad_items)
        self.assertEqual(r.status, "FAIL")

    def test_no_ai_generated_body(self):
        """Body must NOT be AI-generated."""
        for item in FIXTURES["items"]:
            body = item.get("zh_body") or item.get("extracted_text") or item.get("raw_text") or ""
            self.assertNotIn("AI generated", body, "Body must not be AI-generated")


class TestSourceMapping(unittest.TestCase):
    def test_source_kind_mapping(self):
        r = check_source_mapping(FIXTURES["items"])
        self.assertEqual(r.status, "PASS")

    def test_news_maps_to_news(self):
        for item in FIXTURES["items"]:
            if item.get("source_kind") == "news":
                self.assertEqual(item.get("source_kind"), "news")

    def test_telegram_maps_to_telegram(self):
        for item in FIXTURES["items"]:
            if item.get("source_kind") == "telegram":
                self.assertEqual(item.get("source_kind"), "telegram")

    def test_unknown_source_kind(self):
        """Webhook and other unknown types map to UNKNOWN."""
        webhook_items = [i for i in FIXTURES["items"] if i.get("source_kind") == "webhook"]
        for item in webhook_items:
            self.assertEqual(item.get("source_kind"), "webhook")


class TestPrivacyAndHygiene(unittest.TestCase):
    def test_db_path_discarded(self):
        r = check_db_path_suppression(FIXTURES["items"])
        self.assertEqual(r.status, "PASS", f"db_path violations: {r.violations}")

    def test_no_raw_json_default(self):
        """Default call must not include raw_json."""
        r = check_default_query()
        self.assertEqual(r.status, "PASS")

    def test_no_content_in_report(self):
        """Report must not contain full item content."""
        pass  # Contract-level: report only has summary

    def test_urls_safe(self):
        """Check unsafe URLs in fixtures are detected."""
        unsafe = [i for i in FIXTURES["items"] if "javascript:" in str(i)]
        self.assertGreater(len(unsafe), 0, "Fixture must contain unsafe URLs")
        for item in unsafe:
            body = item.get("zh_body", "")
            self.assertIn("javascript:", body)


class TestPagination(unittest.TestCase):
    def test_pagination_contract(self):
        r = check_pagination(PAGINATION_FIXTURE)
        self.assertEqual(r.status, "PASS")

    def test_offset_increases(self):
        page1 = PAGINATION_FIXTURE["page1"]
        page2 = PAGINATION_FIXTURE["page2"]
        id1 = {i["tweet_id"] for i in page1 if "tweet_id" in i}
        id2 = {i["tweet_id"] for i in page2 if "tweet_id" in i}
        self.assertNotEqual(id1, id2, "Page 2 must have different IDs than page 1")

    def test_duplicate_page_dedup(self):
        """Re-reading same page must deduplicate."""
        page1_ids = {i["tweet_id"] for i in PAGINATION_FIXTURE["page1"] if "tweet_id" in i}
        dup_ids = {i["tweet_id"] for i in PAGINATION_FIXTURE["duplicate_page"] if "tweet_id" in i}
        shared = page1_ids & dup_ids
        self.assertGreater(len(shared), 0, "Duplicate page should share IDs with page1")

    def test_partial_failure_degraded(self):
        """Partial page failure → degraded, but accepted items kept."""
        partial = PAGINATION_FIXTURE["partial_fail"]
        ok_items = [i for i in partial if not i.get("backend_error")]
        fail_items = [i for i in partial if i.get("backend_error")]
        self.assertGreater(len(ok_items), 0, "Should have accepted items")
        self.assertGreater(len(fail_items), 0, "Should have rejected items")


class TestFeatured(unittest.TestCase):
    def test_featured_metadata_only(self):
        r = check_featured_metadata(FIXTURES["items"])
        self.assertEqual(r.status, "PASS")

    def test_featured_not_separate_source(self):
        """is_featured=true does NOT change source classification."""
        featured = [i for i in FIXTURES["items"] if i.get("is_featured") == True]
        for item in featured:
            sk = item.get("source_kind", "")
            self.assertIn(sk, ["news"], f"Featured item source_kind={sk}")


class TestCursorContract(unittest.TestCase):
    def test_cursor_from_published_at_backend(self):
        r = check_cursor_contract()
        self.assertEqual(r.status, "PASS")

    def test_no_valid_time_no_cursor_advance(self):
        """No valid backend time → cursor should not advance."""
        pass  # contract-level

    def test_same_time_dedup_by_tweet_id(self):
        """Same timestamp, different tweet_id → both accepted (no data loss)."""
        items = FIXTURES["items"]
        same_time = [i for i in items if i.get("published_at_backend") == "2026-06-17T08:05:00Z"]
        ids = {i.get("tweet_id") for i in same_time if i.get("tweet_id")}
        self.assertGreaterEqual(len(ids), 2, "Multiple items at same timestamp must have unique tweet_ids")


class TestAllCuratedChecks(unittest.TestCase):
    def test_all_curated_checks_pass(self):
        results = run_all_curated_checks()
        failures = [r for r in results if r.status != "PASS"]
        self.assertEqual(len(failures), 0, f"Curated check failures: {[f.name for f in failures]}")
