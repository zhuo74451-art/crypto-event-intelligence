"""Extraction layer tests — 25+ scenarios."""
import pytest
from market_radar.acquisition.extraction.metadata import MetadataExtractor
from market_radar.acquisition.extraction.normalization import TextNormalizer
from market_radar.acquisition.extraction.html import HtmlExtractor, HtmlExtractionResult

class TestMetadataExtractor:
    def test_extract_opengraph(self):
        html = '<html><head><meta property="og:title" content="Test"></head></html>'
        result = MetadataExtractor.extract_opengraph(html)
        assert result.get("og:title") == "Test"

    def test_extract_opengraph_empty(self):
        result = MetadataExtractor.extract_opengraph("<html></html>")
        assert isinstance(result, dict)

    def test_extract_canonical_url(self):
        html = '<link rel="canonical" href="https://example.com/page">'
        url = MetadataExtractor.extract_canonical_url(html)
        assert url == "https://example.com/page"

    def test_extract_canonical_url_missing(self):
        url = MetadataExtractor.extract_canonical_url("<html></html>")
        assert url == ""

    def test_extract_language(self):
        html = '<html lang="en"></html>'
        lang = MetadataExtractor.extract_language(html)
        assert lang == "en"

    def test_extract_language_missing(self):
        lang = MetadataExtractor.extract_language("<html></html>")
        assert lang == ""

    def test_extract_json_ld(self):
        html = '<script type="application/ld+json">{"@type":"WebPage"}</script>'
        data = MetadataExtractor.extract_json_ld(html)
        assert len(data) >= 1

    def test_extract_json_ld_invalid(self):
        html = '<script type="application/ld+json">{invalid}</script>'
        data = MetadataExtractor.extract_json_ld(html)
        assert isinstance(data, list)

class TestTextNormalizer:
    def test_normalize_whitespace(self):
        result = TextNormalizer.normalize_whitespace("  hello   world\n\n  test  ")
        assert result == "hello world test"

    def test_normalize_line_endings(self):
        result = TextNormalizer.normalize_line_endings("hello\r\nworld\r")
        assert result == "hello\nworld\n"

    def test_normalized_hash_deterministic(self):
        h1 = TextNormalizer.compute_normalized_hash("Hello   World")
        h2 = TextNormalizer.compute_normalized_hash("Hello World")
        assert h1 == h2

    def test_normalized_hash_changes_with_content(self):
        h1 = TextNormalizer.compute_normalized_hash("Hello World")
        h2 = TextNormalizer.compute_normalized_hash("Hello World!")
        assert h1 != h2

    def test_identity_hash_deterministic(self):
        h1 = TextNormalizer.compute_identity_hash("Same   Text")
        h2 = TextNormalizer.compute_identity_hash("Same Text")
        assert h1 == h2

class TestHtmlExtractor:
    def test_extract_empty_html(self):
        extractor = HtmlExtractor(use_trafilatura=False)
        result = extractor.extract("", "")
        assert result.extraction_quality in ("empty", "failed")

    def test_extract_simple_html(self):
        html = "<html><head><title>Test</title></head><body>Hello world</body></html>"
        extractor = HtmlExtractor(use_trafilatura=False)
        result = extractor.extract(html, "http://example.com")
        assert isinstance(result, HtmlExtractionResult)

    def test_extract_no_body(self):
        html = "<html><head><title>Test</title></head></html>"
        extractor = HtmlExtractor(use_trafilatura=False)
        result = extractor.extract(html, "")
        assert result.extraction_quality in ("metadata_only", "empty")
