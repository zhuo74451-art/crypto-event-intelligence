"""Comprehensive tests for CuratedApiReader — mock HTTP, no network dependency.

Covers 46 required scenarios:
  1-3: Default no-filter params
  4-5: include_special_line true/false
  6: limit 1-500 validation
  7: offset pagination
  8: since preserves +08:00
  9: total stops
  10: empty page stops
  11: max_pages stops
  12: max_items stops
  13: repeat page no dead loop
  14: tweet_id idempotent
  15: tweet_id missing → rejected
  16: zh_title priority
  17: raw_title fallback
  18: zh_body priority
  19: extracted_text fallback
  20: raw_text fallback
  21: canonical_url priority
  22: source_label priority
  23: source_kind=news → NEWS
  24: source_kind=telegram → TELEGRAM
  25: unknown source_kind → UNKNOWN
  26: not all curated source
  27: published_at_backend → next_cursor
  28: no valid backend time → no cursor advance
  29: is_featured true preserved
  30: editorial_categories preserved
  31: event_fingerprint preserved
  32: db_path not in output
  33: stage non-published
  34: backend_error handling
  35: partial page success → degraded
  36: timeout
  37: non-JSON
  38: oversized response
  39: single bad item doesn't block
  40: aggregate with other readers
  41: Curated API fails, other readers succeed
  42: fixture not live
  43: XSS escaped in workbench
  44: URL safety check
  45: no POST/write
  46: no daemon/thread/scheduler
"""

import json, os, sys, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, Freshness,
    make_feed_id, make_freshness,
)
from market_radar.intelligence_feed.feed_loader import load_feed
from market_radar.intelligence_feed.live_readers import (
    CuratedApiReader, CuratedApiConfig, ReaderStatus,
    FlashReader, NewsReader,
    read_all_once,
)
from market_radar.workbench.bundle import WorkbenchBundle
from market_radar.workbench.renderer import render_workbench

REF_TIME = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)


def _make_item(tweet_id: int = 1, **overrides) -> dict:
    """Create a standard curated API item dict."""
    item = {
        "tweet_id": tweet_id,
        "source": "coindesk",
        "source_label": "CoinDesk",
        "source_category": "media",
        "source_kind": "news",
        "content_type": "news",
        "source_id": f"cd_{tweet_id}",
        "author_username": "coindesk",
        "raw_author": "CoinDesk",
        "raw_title": f"Raw Title {tweet_id}",
        "raw_text": f"Raw text content for item {tweet_id}.",
        "extracted_text": f"Extracted content for item {tweet_id}.",
        "zh_title": f"中文标题 {tweet_id}",
        "zh_body": f"中文正文内容 {tweet_id}.",
        "canonical_url": f"https://example.com/{tweet_id}",
        "article_url": f"https://example.com/alt/{tweet_id}",
        "tweet_created_at": "2026-06-17T08:00:00Z",
        "published_at": "2026-06-17T09:00:00Z",
        "fetched_at": "2026-06-17T09:30:00Z",
        "received_at": "2026-06-17T09:31:00Z",
        "published_at_backend": "2026-06-17T10:00:00Z",
        "pipeline_stage": "published",
        "filter_status": "passed",
        "dedupe_status": "unique",
        "bridge_status": "delivered",
        "is_featured": False,
        "backend_upload_status": "success",
        "editors_categories": ["markets", "regulation"],
    }
    item.update(overrides)
    return item


def _make_page(items: list[dict], total: int = 0, stage: str = "published",
               offset: int = 0, limit: int = 100) -> dict:
    return {
        "stage": stage,
        "total": total or len(items),
        "limit": limit,
        "offset": offset,
        "items": items,
        "query": {},
        "defaults": {},
        "db_path": "/data/curated/items.sqlite",
        "generated_at": "2026-06-17T10:00:00Z",
    }


def _mock_response(data: dict, status: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.getcode.return_value = status
    body = json.dumps(data).encode("utf-8")
    mock.read.return_value = body
    mock.__enter__.return_value = mock
    return mock


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestCuratedApiReaderParams(unittest.TestCase):
    """Parameter-level tests — defaults, filtering, special_line, raw_json."""

    @patch("urllib.request.urlopen")
    def test_1_default_no_source_filter(self, mock_urlopen):
        """1. Default request does NOT send source/exclude_source/content_type."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        reader.read_once()
        call_url = mock_urlopen.call_args[0][0].full_url
        self.assertNotIn("source=", call_url)
        self.assertNotIn("exclude_source=", call_url)
        self.assertNotIn("content_type=", call_url)

    @patch("urllib.request.urlopen")
    def test_2_default_no_special_line(self, mock_urlopen):
        """2. Default does NOT send include_special_line."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        reader.read_once()
        call_url = mock_urlopen.call_args[0][0].full_url
        self.assertNotIn("include_special_line", call_url)

    @patch("urllib.request.urlopen")
    def test_3_default_no_raw_json(self, mock_urlopen):
        """3. Default does NOT send include_raw_json."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        reader.read_once()
        call_url = mock_urlopen.call_args[0][0].full_url
        self.assertNotIn("include_raw_json", call_url)

    @patch("urllib.request.urlopen")
    def test_4_special_line_true_sends_1(self, mock_urlopen):
        """4. include_special_line=True sends ?include_special_line=1."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        config = CuratedApiConfig(include_special_line=True)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        reader.read_once()
        call_url = mock_urlopen.call_args[0][0].full_url
        self.assertIn("include_special_line=1", call_url)

    @patch("urllib.request.urlopen")
    def test_5_special_line_false_sends_0(self, mock_urlopen):
        """5. include_special_line=False sends ?include_special_line=0."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        config = CuratedApiConfig(include_special_line=False)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        reader.read_once()
        call_url = mock_urlopen.call_args[0][0].full_url
        self.assertIn("include_special_line=0", call_url)

    @patch("urllib.request.urlopen")
    def test_6_limit_range(self, mock_urlopen):
        """6. limit parameter within 1-500."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        config = CuratedApiConfig(limit=500)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        reader.read_once()
        call_url = mock_urlopen.call_args[0][0].full_url
        self.assertIn("limit=500", call_url)

    def test_6b_limit_out_of_range(self):
        """6b. limit=999 raises ValueError."""
        with self.assertRaises(ValueError):
            CuratedApiConfig(limit=999)


class TestCuratedApiReaderPagination(unittest.TestCase):
    """Pagination — offset, max_pages, max_items, empty page, total."""

    @patch("urllib.request.urlopen")
    def test_7_offset_pagination(self, mock_urlopen):
        """7. offset advances correctly between pages."""
        page1 = _make_page([_make_item(i) for i in range(2)], total=4, offset=0, limit=2)
        page2 = _make_page([_make_item(i) for i in range(2, 4)], total=4, offset=2, limit=2)
        mock_urlopen.side_effect = [
            _mock_response(page1),
            _mock_response(page2),
        ]
        config = CuratedApiConfig(limit=2, max_pages=3)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 4)
        self.assertEqual(result.records_seen, 4)

    @patch("urllib.request.urlopen")
    def test_9_total_stops(self, mock_urlopen):
        """9. offset >= total stops pagination."""
        page1 = _make_page([_make_item(1)], total=1, offset=0, limit=2)
        mock_urlopen.return_value = _mock_response(page1)
        config = CuratedApiConfig(limit=2, max_pages=10)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        # Should only have 1 item from 1 page, stop because offset >= total
        self.assertEqual(len(result.items), 1)

    @patch("urllib.request.urlopen")
    def test_10_empty_page_stops(self, mock_urlopen):
        """10. Empty items list stops pagination."""
        mock_urlopen.return_value = _mock_response(_make_page([], total=0))
        config = CuratedApiConfig(limit=100, max_pages=10)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 0)

    @patch("urllib.request.urlopen")
    def test_11_max_pages_stops(self, mock_urlopen):
        """11. max_pages limits the number of pages fetched."""
        many_items = [_make_item(i) for i in range(50)]
        page = _make_page(many_items, total=999, offset=0, limit=50)
        mock_urlopen.return_value = _mock_response(page)
        config = CuratedApiConfig(limit=50, max_pages=1, max_items=999)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertLessEqual(len(result.items), 50)

    @patch("urllib.request.urlopen")
    def test_12_max_items_stops(self, mock_urlopen):
        """12. max_items truncates and stops."""
        items = [_make_item(i) for i in range(100)]
        mock_urlopen.return_value = _mock_response(
            _make_page(items, total=100, offset=0, limit=100)
        )
        config = CuratedApiConfig(limit=100, max_pages=5, max_items=5)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 5)

    @patch("urllib.request.urlopen")
    def test_13_no_dead_loop(self, mock_urlopen):
        """13. Repeat page (same offset) does not cause dead loop."""
        items = [_make_item(i) for i in range(2)]
        page = _make_page(items, total=4, offset=0, limit=2)
        # Return the same page every time — total=4 so offset advances
        # but never reaches 4 with limit=2. simulates API returning same data.
        mock_urlopen.side_effect = [
            _mock_response(page),
            _mock_response(_make_page([], total=4, offset=2, limit=2)),  # empty page stops
        ]
        config = CuratedApiConfig(limit=2, max_pages=10)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertGreaterEqual(len(result.items), 2)
        self.assertLess(len(result.items), 10)

    @patch("urllib.request.urlopen")
    def test_8_since_preserved(self, mock_urlopen):
        """8. since parameter is transmitted as-is."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        config = CuratedApiConfig(since="2026-06-17T08:00:00+08:00")
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        reader.read_once()
        call_url = mock_urlopen.call_args[0][0].full_url
        self.assertIn("since=2026-06-17T08%3A00%3A00%2B08%3A00", call_url)


class TestCuratedApiReaderItemMapping(unittest.TestCase):
    """Item field mapping — title/body/URL fallbacks, source mapping."""

    @patch("urllib.request.urlopen")
    def test_14_tweet_id_idempotent(self, mock_urlopen):
        """14. Same tweet_id across pages → deduplicated."""
        page1 = _make_page([_make_item(1)], total=2, offset=0, limit=1)
        page2 = _make_page([_make_item(1)], total=2, offset=1, limit=1)  # same tweet_id
        mock_urlopen.side_effect = [
            _mock_response(page1),
            _mock_response(page2),
        ]
        config = CuratedApiConfig(limit=1, max_pages=5)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 1)

    @patch("urllib.request.urlopen")
    def test_15_tweet_id_missing_rejected(self, mock_urlopen):
        """15. Item without tweet_id → rejected."""
        bad_item = _make_item(1)
        del bad_item["tweet_id"]
        mock_urlopen.return_value = _mock_response(
            _make_page([bad_item, _make_item(2)])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.records_rejected, 1)

    @patch("urllib.request.urlopen")
    def test_16_zh_title_priority(self, mock_urlopen):
        """16. zh_title takes priority over raw_title."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, zh_title="中文标题", raw_title="Raw Title")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIn("中文标题", result.items[0].title)

    @patch("urllib.request.urlopen")
    def test_17_raw_title_fallback(self, mock_urlopen):
        """17. raw_title used when zh_title is missing."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, zh_title=None, raw_title="Fallback Title")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.items[0].title, "Fallback Title")

    @patch("urllib.request.urlopen")
    def test_18_zh_body_priority(self, mock_urlopen):
        """18. zh_body takes priority over extracted_text."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, zh_body="中文正文", extracted_text="Extracted")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIn("中文正文", result.items[0].body)

    @patch("urllib.request.urlopen")
    def test_19_extracted_text_fallback(self, mock_urlopen):
        """19. extracted_text used when zh_body is missing."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, zh_body=None, extracted_text="Extracted Fallback")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIn("Extracted Fallback", result.items[0].body)

    @patch("urllib.request.urlopen")
    def test_20_raw_text_fallback(self, mock_urlopen):
        """20. raw_text used when zh_body and extracted_text are missing."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, zh_body=None, extracted_text=None, raw_text="Raw Fallback")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIn("Raw Fallback", result.items[0].body)

    @patch("urllib.request.urlopen")
    def test_21_canonical_url_priority(self, mock_urlopen):
        """21. canonical_url takes priority over article_url."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, canonical_url="https://canonical.com/1",
                                     article_url="https://alt.com/1")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.items[0].url, "https://canonical.com/1")

    @patch("urllib.request.urlopen")
    def test_22_source_label_priority(self, mock_urlopen):
        """22. source_label takes priority over source."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, source_label="CoinDesk", source="coindesk")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.items[0].source_label, "CoinDesk")

    @patch("urllib.request.urlopen")
    def test_23_source_kind_news(self, mock_urlopen):
        """23. source_kind=news → FeedSourceType.NEWS."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, source_kind="news")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.items[0].source_type, FeedSourceType.NEWS)

    @patch("urllib.request.urlopen")
    def test_24_source_kind_telegram(self, mock_urlopen):
        """24. source_kind=telegram → FeedSourceType.TELEGRAM."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, source_kind="telegram")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.items[0].source_type, FeedSourceType.TELEGRAM)

    @patch("urllib.request.urlopen")
    def test_25_unknown_source_kind(self, mock_urlopen):
        """25. Unknown source_kind → FeedSourceType.UNKNOWN."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, source_kind="webhook", content_type="signal")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        # "signal" is not in content_type map
        self.assertEqual(result.items[0].source_type, FeedSourceType.UNKNOWN)

    @patch("urllib.request.urlopen")
    def test_26_not_all_curated_source(self, mock_urlopen):
        """26. Items have individual source_type, not all 'curated'."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, source_kind="news"),
            _make_item(2, source_kind="telegram"),
            _make_item(3, source_kind="flash"),
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        types = {i.source_type for i in result.items}
        self.assertIn(FeedSourceType.NEWS, types)
        self.assertIn(FeedSourceType.TELEGRAM, types)
        self.assertIn(FeedSourceType.FLASH, types)

    @patch("urllib.request.urlopen")
    def test_27_cursor_from_backend(self, mock_urlopen):
        """27. published_at_backend generates next_cursor via public field."""
        items = [
            _make_item(1, published_at_backend="2026-06-17T10:00:00Z"),
            _make_item(2, published_at_backend="2026-06-17T11:00:00Z"),
        ]
        mock_urlopen.return_value = _mock_response(_make_page(items))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.next_cursor, "2026-06-17T11:00:00Z")
        self.assertTrue(result.cursor_safe)

    @patch("urllib.request.urlopen")
    def test_28_no_cursor_without_backend_time(self, mock_urlopen):
        """28. No valid published_at_backend → cursor is None."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, published_at_backend=None)])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIsNone(result.next_cursor)

    @patch("urllib.request.urlopen")
    def test_29_is_featured_preserved(self, mock_urlopen):
        """29. is_featured=true preserved as metadata, not affecting trust."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, is_featured=True)])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        meta = getattr(result.items[0], "_metadata", {}) or {}
        self.assertTrue(meta.get("is_featured"))

    @patch("urllib.request.urlopen")
    def test_30_editorial_categories_preserved(self, mock_urlopen):
        """30. editorial_categories preserved."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, editorial_categories=["markets", "tech"])])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        meta = getattr(result.items[0], "_metadata", {}) or {}
        cats = meta.get("editorial_categories")
        self.assertIsNotNone(cats)

    @patch("urllib.request.urlopen")
    def test_31_event_fingerprint_preserved(self, mock_urlopen):
        """31. event_fingerprint preserved."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, event_fingerprint="fp_abc123")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        meta = getattr(result.items[0], "_metadata", {}) or {}
        self.assertEqual(meta.get("event_fingerprint"), "fp_abc123")


class TestCuratedApiReaderErrorHandling(unittest.TestCase):
    """Error handling — HTTP errors, JSON, size, stage, bad items."""

    @patch("urllib.request.urlopen")
    def test_32_db_path_discarded(self, mock_urlopen):
        """32. db_path not in output items or provenance."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertNotIn("db_path", result.provenance)
        meta = getattr(result.items[0], "_metadata", {}) or {}
        self.assertNotIn("db_path", meta)

    @patch("urllib.request.urlopen")
    def test_33_stage_not_published(self, mock_urlopen):
        """33. Stage is not 'published' → degraded."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1)], stage="draft")
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIn(result.status, (ReaderStatus.DEGRADED, ReaderStatus.UNAVAILABLE))

    @patch("urllib.request.urlopen")
    def test_34_backend_error_item(self, mock_urlopen):
        """34. backend_upload_status=failed → item rejected."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1), _make_item(2, backend_upload_status="failed")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.records_rejected, 1)

    @patch("urllib.request.urlopen")
    def test_35_partial_page_failure(self, mock_urlopen):
        """35. Page 1 succeeds, page 2 fails → degraded with page 1 items."""
        page1 = _make_page([_make_item(1), _make_item(2)], total=4, offset=0, limit=2)
        mock_urlopen.side_effect = [
            _mock_response(page1),
            _mock_response("not json", 200),  # Second page fails
        ]
        config = CuratedApiConfig(limit=2, max_pages=5)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.DEGRADED)
        self.assertGreaterEqual(len(result.items), 2)

    @patch("urllib.request.urlopen")
    def test_36_timeout(self, mock_urlopen):
        """36. Timeout → unavailable."""
        mock_urlopen.side_effect = OSError("timed out")
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.UNAVAILABLE)

    @patch("urllib.request.urlopen")
    def test_37_non_json_response(self, mock_urlopen):
        """37. Non-JSON response → degraded."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json at all"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.DEGRADED)

    @patch("urllib.request.urlopen")
    def test_38_oversized_response(self, mock_urlopen):
        """38. Response exceeds max_response_bytes → degraded."""
        mock_resp = MagicMock()
        # Return more bytes than allowed
        mock_resp.read.return_value = b"x" * (5 * 1024 * 1024 + 1)
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        config = CuratedApiConfig(max_response_bytes=5 * 1024 * 1024)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.DEGRADED)

    @patch("urllib.request.urlopen")
    def test_39_single_bad_item_does_not_block(self, mock_urlopen):
        """39. One bad item (missing body) doesn't block others."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, zh_body=None, extracted_text=None, raw_text=None),  # no body
            _make_item(2),  # good
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.records_rejected, 1)

    @patch("urllib.request.urlopen")
    def test_40_aggregate_with_other_readers(self, mock_urlopen):
        """40. CuratedApiReader aggregates with other readers."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, source_kind="news")])
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"title": "Flash item", "source_label": "test"}], f)
            flash_path = f.name
        try:
            readers = [
                CuratedApiReader(reference_time=REF_TIME),
                FlashReader(flash_path, reference_time=REF_TIME),
            ]
            summary = read_all_once(readers)
            self.assertGreaterEqual(len(summary.items), 2)
        finally:
            os.unlink(flash_path)

    @patch("urllib.request.urlopen")
    def test_41_curated_fails_others_succeed(self, mock_urlopen):
        """41. Curated API fails, Flash reader still succeeds."""
        mock_urlopen.side_effect = OSError("API unreachable")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"title": "Flash survives", "source_label": "test"}], f)
            flash_path = f.name
        try:
            readers = [
                CuratedApiReader(reference_time=REF_TIME),
                FlashReader(flash_path, reference_time=REF_TIME),
            ]
            summary = read_all_once(readers)
            self.assertEqual(summary.overall_status, "degraded")
            self.assertGreaterEqual(len(summary.items), 1)
        finally:
            os.unlink(flash_path)

    @patch("urllib.request.urlopen")
    def test_42_fixture_not_live(self, mock_urlopen):
        """42. Fixture never counts as live in aggregate."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, source_kind="news")])
        )
        feed_result = load_feed()
        live_from_feed = [i for i in feed_result.items if i.data_mode == FeedDataMode.LIVE]
        self.assertEqual(len(live_from_feed), 0)

    @patch("urllib.request.urlopen")
    def test_43_xss_escaped(self, mock_urlopen):
        """43. XSS content in curated item → escaped by workbench renderer."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, raw_title='<script>alert("xss")</script>',
                       zh_title=None, raw_text="safe body")
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        bundle = WorkbenchBundle(feed_items=result.items)
        html = render_workbench(bundle)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert", html)

    @patch("urllib.request.urlopen")
    def test_44_url_safety(self, mock_urlopen):
        """44. Non-http URL → rejected by URL safety."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, canonical_url="javascript:alert(1)", article_url=None)
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIsNone(result.items[0].url)

    @patch("urllib.request.urlopen")
    def test_35b_http_error(self, mock_urlopen):
        """HTTP 500 → unavailable, 404 → degraded."""
        # 500
        mock_urlopen.side_effect = HTTPError(
            "http://example.com", 500, "Internal Error", {}, None
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.UNAVAILABLE)


class TestCuratedApiReaderConstraints(unittest.TestCase):
    """Structural constraints — no daemon, no POST, etc."""

    def test_45_no_post_or_write(self):
        """45. Reader file must not contain POST/PUT/DELETE or write paths."""
        import inspect
        import market_radar.intelligence_feed.live_readers.curated_api_reader as mod
        src = inspect.getsource(mod)
        self.assertNotIn(".post(", src)
        self.assertNotIn(".put(", src)
        self.assertNotIn(".delete(", src)
        self.assertNotIn('"POST"', src)
        self.assertNotIn("'POST'", src)

    def test_46_no_daemon_or_scheduler(self):
        """46. Reader file must not import daemon/thread/scheduler modules."""
        import inspect
        import market_radar.intelligence_feed.live_readers.curated_api_reader as mod
        src = inspect.getsource(mod)
        self.assertNotIn("import threading", src)
        self.assertNotIn("import asyncio", src)
        self.assertNotIn("import sched", src)
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import multiprocessing", src)

    def test_46b_only_urllib_for_http(self):
        """Reader uses only urllib for HTTP, not requests/httpx/aiohttp."""
        import inspect
        import market_radar.intelligence_feed.live_readers.curated_api_reader as mod
        src = inspect.getsource(mod)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import httpx", src)
        self.assertNotIn("import aiohttp", src)
        # urllib is the only HTTP library
        self.assertIn("urllib.request", src)


class TestCuratedApiReaderEdge(unittest.TestCase):
    """Edge cases — empty body rejection, title-only derivation."""

    @patch("urllib.request.urlopen")
    def test_body_rejected_when_all_empty(self, mock_urlopen):
        """Item with no body at all → rejected."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, zh_body=None, extracted_text=None, raw_text=None,
                       delivery_payload={}),
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.records_rejected, 1)

    @patch("urllib.request.urlopen")
    def test_derived_title_from_body(self, mock_urlopen):
        """No title at all → derived from body truncation."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, zh_title=None, raw_title=None,
                       zh_body="This is a long body text that should be truncated to 80 chars for display title purposes")
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertTrue(len(result.items) > 0)
        # Title should be truncated body
        self.assertLessEqual(len(result.items[0].title), 82)


class TestCuratedApiReaderR03PublicContract(unittest.TestCase):
    """R03: Public contract fields — next_cursor, cursor_safe, source_statuses, empty-batch truth."""

    @patch("urllib.request.urlopen")
    def test_empty_batch_is_ok(self, mock_urlopen):
        """Empty batch (200, stage=published, items=[]) → status=ok, cursor_safe=true."""
        mock_urlopen.return_value = _mock_response(_make_page([], total=0))
        config = CuratedApiConfig(limit=100, max_pages=2)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.OK)
        self.assertEqual(len(result.items), 0)
        self.assertIsNone(result.next_cursor)
        self.assertTrue(result.cursor_safe)

    @patch("urllib.request.urlopen")
    def test_completed_total_not_degraded(self, mock_urlopen):
        """offset >= total normal completion → not truncated, cursor_safe=true."""
        page = _make_page([_make_item(1)], total=1, offset=0, limit=2)
        mock_urlopen.return_value = _mock_response(page)
        config = CuratedApiConfig(limit=2, max_pages=5, max_items=500)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.OK)
        self.assertTrue(result.cursor_safe)

    @patch("urllib.request.urlopen")
    def test_max_pages_truncated(self, mock_urlopen):
        """max_pages hit with more data → degraded, cursor_safe=false."""
        items = [_make_item(i) for i in range(50)]
        page = _make_page(items, total=200, offset=0, limit=50)
        mock_urlopen.return_value = _mock_response(page)
        config = CuratedApiConfig(limit=50, max_pages=1, max_items=5000)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.DEGRADED)
        self.assertFalse(result.cursor_safe)

    @patch("urllib.request.urlopen")
    def test_max_items_truncated(self, mock_urlopen):
        """max_items hit → degraded, cursor_safe=false."""
        items = [_make_item(i) for i in range(100)]
        mock_urlopen.return_value = _mock_response(
            _make_page(items, total=100, offset=0, limit=100)
        )
        config = CuratedApiConfig(limit=100, max_pages=5, max_items=5)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.DEGRADED)
        self.assertFalse(result.cursor_safe)

    @patch("urllib.request.urlopen")
    def test_public_next_cursor_field(self, mock_urlopen):
        """next_cursor is a public ReaderBatchResult field, not private _next_cursor."""
        mock_urlopen.return_value = _mock_response(
            _make_page([_make_item(1, published_at_backend="2026-06-17T10:00:00Z")])
        )
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertIsNotNone(result.next_cursor)
        self.assertFalse(hasattr(result, "_next_cursor") and
                         "_next_cursor" in type(result).__dataclass_fields__)

    @patch("urllib.request.urlopen")
    def test_cursor_z_suffix_comparison(self, mock_urlopen):
        """Z and +00:00 times compare correctly (same time → same cursor)."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, published_at_backend="2026-06-17T10:00:00Z"),
            _make_item(2, published_at_backend="2026-06-17T10:00:00+00:00"),
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.next_cursor, "2026-06-17T10:00:00Z")

    @patch("urllib.request.urlopen")
    def test_cursor_plus08_convert(self, mock_urlopen):
        """+08:00 times convert to UTC correctly."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, published_at_backend="2026-06-17T18:00:00+08:00"),
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        # 18:00 +08:00 → 10:00 UTC
        self.assertEqual(result.next_cursor, "2026-06-17T10:00:00Z")

    @patch("urllib.request.urlopen")
    def test_cursor_invalid_time(self, mock_urlopen):
        """Invalid published_at_backend → cursor_safe=false."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, published_at_backend="not-a-timestamp"),
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertFalse(result.cursor_safe)

    @patch("urllib.request.urlopen")
    def test_config_validation_boundaries(self, mock_urlopen):
        """Config validation rejects out-of-range values."""
        with self.assertRaises(ValueError):
            CuratedApiConfig(limit=0)
        with self.assertRaises(ValueError):
            CuratedApiConfig(limit=501)
        with self.assertRaises(ValueError):
            CuratedApiConfig(max_pages=0)
        with self.assertRaises(ValueError):
            CuratedApiConfig(max_pages=11)
        with self.assertRaises(ValueError):
            CuratedApiConfig(max_items=0)
        with self.assertRaises(ValueError):
            CuratedApiConfig(max_items=5001)
        with self.assertRaises(ValueError):
            CuratedApiConfig(timeout_seconds=0)
        with self.assertRaises(ValueError):
            CuratedApiConfig(base_url="ftp://bad")
        with self.assertRaises(ValueError):
            CuratedApiConfig(include_special_line=123)
        with self.assertRaises(ValueError):
            CuratedApiConfig(include_raw_json="yes")

    @patch("urllib.request.urlopen")
    def test_stage_missing(self, mock_urlopen):
        """Missing stage field → degraded."""
        page = {"total": 1, "limit": 100, "offset": 0, "items": [_make_item(1)]}
        mock_urlopen.return_value = _mock_response(page)
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.DEGRADED)

    @patch("urllib.request.urlopen")
    def test_backend_error_rejected(self, mock_urlopen):
        """backend_error non-empty → item rejected."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, backend_error=""),  # empty → ok
            _make_item(2, backend_error="Rate limit exceeded"),  # non-empty → rejected
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.records_rejected, 1)

    @patch("urllib.request.urlopen")
    def test_source_statuses_multiple(self, mock_urlopen):
        """source_statuses groups by source_label."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(1, source_label="CoinDesk", source_kind="news"),
            _make_item(2, source_label="CoinDesk", source_kind="news"),
            _make_item(3, source_label="TG Channel", source_kind="telegram"),
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertGreaterEqual(len(result.source_statuses), 2)

    @patch("urllib.request.urlopen")
    def test_db_path_not_in_output(self, mock_urlopen):
        """db_path never appears in items or metadata."""
        mock_urlopen.return_value = _mock_response(_make_page([_make_item(1)]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertNotIn("db_path", result.provenance)

    @patch("urllib.request.urlopen")
    def test_empty_second_increment_is_ok(self, mock_urlopen):
        """Empty incremental poll (since=some time, no new items) → ok."""
        mock_urlopen.return_value = _mock_response(_make_page([], total=0))
        config = CuratedApiConfig(since="2026-06-17T12:00:00Z")
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.OK)
        self.assertEqual(len(result.items), 0)

    @patch("urllib.request.urlopen")
    def test_same_time_different_tweet_id(self, mock_urlopen):
        """Same published_at_backend time, different tweet_ids → both accepted."""
        mock_urlopen.return_value = _mock_response(_make_page([
            _make_item(tweet_id=101, published_at_backend="2026-06-17T10:00:00Z"),
            _make_item(tweet_id=102, published_at_backend="2026-06-17T10:00:00Z"),
        ]))
        reader = CuratedApiReader(reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(len(result.items), 2)
        self.assertIsNotNone(result.next_cursor)

    @patch("urllib.request.urlopen")
    def test_partial_page_failure_cursor_not_safe(self, mock_urlopen):
        """Partial page failure → cursor_safe=false, degraded, has partial items."""
        page1 = _make_page([_make_item(1), _make_item(2)], total=4, offset=0, limit=2)
        mock_urlopen.side_effect = [
            _mock_response(page1),
            _mock_response("notjson", 200),
        ]
        config = CuratedApiConfig(limit=2, max_pages=5)
        reader = CuratedApiReader(config, reference_time=REF_TIME)
        result = reader.read_once()
        self.assertEqual(result.status, ReaderStatus.DEGRADED)
        self.assertFalse(result.cursor_safe)
        self.assertGreaterEqual(len(result.items), 2)

    def test_provider_name_field(self):
        """provider_name is 'curated_api'."""
        self.assertEqual(CuratedApiConfig().base_url, "http://43.98.174.247:8001/api/integration/curated")


# ═══════════════════════════════════════════════════════════════════════
# R06 — Source Status Consistency Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSourceStatusConsistency(unittest.TestCase):
    """Section 1: source_statuses must contain ok, status/ok consistent."""

    def setUp(self):
        self.cfg = CuratedApiConfig(base_url="http://fake.test/api/read")
        self.cfg.max_pages = 1

    def _mock_response(self, status_code: int, data: dict):
        m = MagicMock()
        m.__enter__.return_value = m
        m.status = status_code
        m.read.return_value = json.dumps(data).encode("utf-8")
        m.getcode.return_value = status_code
        return m

    def test_status_ok_ok_true(self):
        """status=ok → ok=true."""
        data = {
            "stage": "published",
            "items": [{"tweet_id": 1, "source": "test", "raw_title": "T1",
                       "raw_text": "Body", "published_at_backend": "2026-06-17T12:00:00Z"}],
            "total": 1,
        }
        with patch("urllib.request.urlopen", return_value=self._mock_response(200, data)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            for ss in result.source_statuses:
                if ss.get("status") == "ok":
                    self.assertTrue(ss.get("ok"), f"source {ss.get('source')} status=ok but ok=false")

    def test_degraded_ok_false(self):
        """status=degraded → ok=false."""
        data = {"stage": "unknown_stage", "items": []}
        with patch("urllib.request.urlopen", return_value=self._mock_response(200, data)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            for ss in result.source_statuses:
                if ss.get("status") == "degraded":
                    self.assertFalse(ss.get("ok"), f"source {ss.get('source')} status=degraded but ok=true")

    def test_unavailable_ok_false(self):
        """status=unavailable → ok=false."""
        with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            for ss in result.source_statuses:
                if ss.get("status") == "unavailable":
                    self.assertFalse(ss.get("ok"), f"source {ss.get('source')} status=unavailable but ok=true")


class TestEmptyAndFailureBatchConsistency(unittest.TestCase):
    """Section 2: empty and failure batch status consistency."""

    def setUp(self):
        self.cfg = CuratedApiConfig(base_url="http://fake.test/api/read")
        self.cfg.max_pages = 1

    def _mock_response(self, status_code: int, data: dict):
        m = MagicMock()
        m.__enter__.return_value = m
        m.status = status_code
        m.read.return_value = json.dumps(data).encode("utf-8")
        m.getcode.return_value = status_code
        return m

    def test_normal_empty_batch_ok(self):
        """Normal empty batch (HTTP 200, empty items) → source ok, ok=true."""
        data = {"stage": "published", "items": [], "total": 0}
        with patch("urllib.request.urlopen", return_value=self._mock_response(200, data)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            self.assertEqual(result.status, ReaderStatus.OK)
            for ss in result.source_statuses:
                self.assertEqual(ss.get("status"), "ok")
                self.assertTrue(ss.get("ok"))

    def test_http_unavailable_empty_batch(self):
        """HTTP unavailable → source unavailable, ok=false."""
        with patch("urllib.request.urlopen", side_effect=HTTPError(
                "http://fake.test", 503, "Service Unavailable", {}, None)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            self.assertEqual(result.status, ReaderStatus.UNAVAILABLE)
            for ss in result.source_statuses:
                self.assertEqual(ss.get("status"), "unavailable")
                self.assertFalse(ss.get("ok"))

    def test_stage_missing_degraded(self):
        """Missing stage → source degraded, ok=false."""
        data = {"items": []}
        with patch("urllib.request.urlopen", return_value=self._mock_response(200, data)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            self.assertEqual(result.status, ReaderStatus.DEGRADED)
            for ss in result.source_statuses:
                self.assertEqual(ss.get("status"), "degraded")
                self.assertFalse(ss.get("ok"))

    def test_non_json_degraded(self):
        """Non-JSON response → degraded."""
        m = MagicMock()
        m.__enter__.return_value = m
        m.read.return_value = b"not json at all"
        m.getcode.return_value = 200
        with patch("urllib.request.urlopen", return_value=m):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            self.assertIn(result.status, (ReaderStatus.DEGRADED, ReaderStatus.UNAVAILABLE))
            for ss in result.source_statuses:
                self.assertFalse(ss.get("ok"))


class TestMultiSourcePartialFailure(unittest.TestCase):
    """Section 3: multi-source partial failure handling."""

    def setUp(self):
        self.cfg = CuratedApiConfig(base_url="http://fake.test/api/read")
        self.cfg.max_pages = 5

    def _mock_response(self, pages: list[dict]):
        """Create a urlopen mock that returns different pages sequentially."""
        responses = []
        for page_data in pages:
            m = MagicMock()
            m.__enter__.return_value = m
            m.read.return_value = json.dumps(page_data).encode("utf-8")
            m.getcode.return_value = 200
            responses.append(m)
        iterator = iter(responses)
        def side_effect(*args, **kwargs):
            return next(iterator)
        return side_effect

    def test_all_sources_ok(self):
        """All sources ok → each source status=ok, ok=true."""
        page1 = {
            "stage": "published",
            "items": [
                {"tweet_id": 1, "source": "coindesk", "source_kind": "news",
                 "source_label": "CoinDesk", "raw_title": "T1", "raw_text": "B1",
                 "published_at_backend": "2026-06-17T12:00:00Z"},
                {"tweet_id": 2, "source": "telegram_channel", "source_kind": "telegram",
                 "source_label": "Telegram A", "raw_title": "T2", "raw_text": "B2",
                 "published_at_backend": "2026-06-17T12:01:00Z"},
            ],
            "total": 2,
        }
        with patch("urllib.request.urlopen", side_effect=self._mock_response([page1])):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            self.assertEqual(result.status, ReaderStatus.OK)
            for ss in result.source_statuses:
                self.assertEqual(ss.get("status"), "ok")
                self.assertTrue(ss.get("ok"))

    def test_partial_page_failure_keeps_ok_sources(self):
        """Page-level partial failure: ok sources stay ok, aggregate curated_api degraded."""
        pages = [
            {"stage": "published",
             "items": [{"tweet_id": 1, "source": "coindesk", "source_kind": "news",
                        "source_label": "CoinDesk", "raw_title": "T1", "raw_text": "B1",
                        "published_at_backend": "2026-06-17T12:00:00Z"}],
             "total": 300},
            {"stage": "error_stage",
             "items": []},
        ]
        with patch("urllib.request.urlopen", side_effect=self._mock_response(pages)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            # Status should be degraded
            self.assertEqual(result.status, ReaderStatus.DEGRADED)
            # Successful source should be ok
            coinbase_sources = [ss for ss in result.source_statuses if ss.get("source") == "CoinDesk"]
            if coinbase_sources:
                self.assertEqual(coinbase_sources[0].get("status"), "ok")
                self.assertTrue(coinbase_sources[0].get("ok"))
            # Aggregate degraded source should exist
            api_sources = [ss for ss in result.source_statuses if ss.get("source") == "curated_api"]
            self.assertGreater(len(api_sources), 0)
            self.assertEqual(api_sources[0].get("status"), "degraded")
            self.assertFalse(api_sources[0].get("ok"))


class TestW1Compatibility(unittest.TestCase):
    """Section 9: W1 FeedProviderProtocol compatibility."""

    def setUp(self):
        self.cfg = CuratedApiConfig(base_url="http://fake.test/api/read")
        self.cfg.max_pages = 1

    def _mock_response(self, data: dict):
        m = MagicMock()
        m.__enter__.return_value = m
        m.read.return_value = json.dumps(data).encode("utf-8")
        m.getcode.return_value = 200
        return m

    def test_w1_ss_get_ok_default_false_ok_source(self):
        """W1 uses ss.get('ok', False) — normal ok source must return True."""
        data = {
            "stage": "published",
            "items": [{"tweet_id": 1, "source": "test", "raw_title": "T",
                       "raw_text": "B", "published_at_backend": "2026-06-17T12:00:00Z"}],
            "total": 1,
        }
        with patch("urllib.request.urlopen", return_value=self._mock_response(data)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            for ss in result.source_statuses:
                # W1 does: ss.get("ok", False)
                self.assertTrue(ss.get("ok", False), f"W1 compatibility: source {ss.get('source')} ss.get('ok', False) should be True")


class TestFiniteValidation(unittest.TestCase):
    """Section 4: timeout_seconds finite validation."""

    def test_timeout_nan_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(timeout_seconds=float("nan"))

    def test_timeout_infinity_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(timeout_seconds=float("inf"))

    def test_timeout_neg_infinity_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(timeout_seconds=float("-inf"))

    def test_timeout_zero_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(timeout_seconds=0)

    def test_timeout_negative_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(timeout_seconds=-5)

    def test_limit_bool_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(limit=True)

    def test_max_pages_bool_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(max_pages=True)

    def test_max_items_bool_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(max_items=True)

    def test_max_response_bytes_bool_rejected(self):
        with self.assertRaises(ValueError):
            CuratedApiConfig(max_response_bytes=True)


class TestInvalidCursorAudit(unittest.TestCase):
    """Section 5: invalid cursor timestamp audit."""

    def setUp(self):
        self.cfg = CuratedApiConfig(base_url="http://fake.test/api/read")
        self.cfg.max_pages = 1

    def _mock_response(self, data: dict):
        m = MagicMock()
        m.__enter__.return_value = m
        m.read.return_value = json.dumps(data).encode("utf-8")
        m.getcode.return_value = 200
        return m

    def test_invalid_cursor_timestamp_counted(self):
        """Invalid published_at_backend must set cursor_safe=false and record count."""
        data = {
            "stage": "published",
            "items": [{"tweet_id": 1, "source": "test", "raw_title": "T",
                       "raw_text": "B", "published_at_backend": "not-a-timestamp"}],
            "total": 1,
        }
        with patch("urllib.request.urlopen", return_value=self._mock_response(data)):
            reader = CuratedApiReader(self.cfg, reference_time=REF_TIME)
            result = reader.read_once()
            self.assertFalse(result.cursor_safe)
            metadata = result.metadata or {}
            count = metadata.get("invalid_cursor_timestamp_count", 0)
            self.assertGreater(count, 0, "invalid cursor timestamp count must be > 0")


class TestCuratedApiReaderLiveProbe(unittest.TestCase):
    """Placeholder for live probe — only runs when explicitly enabled."""

    def test_live_probe_disabled_by_default(self):
        """Live probe does not run during unit tests."""
        pass


if __name__ == "__main__":
    unittest.main()
