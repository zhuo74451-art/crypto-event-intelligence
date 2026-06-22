"""HTML extraction with Trafilatura fallback."""

import re
import datetime
from dataclasses import dataclass, field
from ..contracts.timestamps import utc_now
from typing import Any, Optional

from .metadata import MetadataExtractor
from .normalization import TextNormalizer


@dataclass
class HtmlExtractionResult:
    """Result of HTML content extraction."""

    title: str = ""
    body_text: str = ""
    author: str = ""
    published_at: str = ""
    updated_at: str = ""
    canonical_url: str = ""
    language: str = ""
    extraction_quality: str = "empty"  # complete / partial / metadata_only / empty / failed
    structured_data: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    extracted_at: str = ""


class HtmlExtractor:
    """Extract structured content from HTML using Trafilatura or fallback regex."""

    def __init__(self, use_trafilatura: bool = True):
        self.trafilatura_available = False
        self.trafilatura_module: Any = None
        if use_trafilatura:
            try:
                import trafilatura  # type: ignore[import-untyped]
                self.trafilatura_module = trafilatura
                self.trafilatura_available = True
            except ImportError:
                self.trafilatura_available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def _detect_language_heuristic(self, text: str) -> str:
        """Simple language detection heuristic."""
        if not text:
            return ""
        text_lower = text.lower()
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        if chinese_chars > len(text) * 0.1:
            return "zh"
        if any(word in text_lower for word in ['the', 'and', 'for', 'that', 'this', 'with']):
            return "en"
        return "en"

    def _extract_fallback(self, html_content: str) -> dict:
        """Basic fallback extraction without trafilatura."""
        result = {"title": "", "body_text": "", "author": "",
                  "published_at": "", "updated_at": "",
                  "canonical_url": "", "language": "",
                  "extraction_quality": "metadata_only",
                  "structured_data": {}, "extracted_at": utc_now().isoformat()}
        warnings = []
        try:
            from market_radar.acquisition.extraction.metadata import MetadataExtractor
            from market_radar.acquisition.extraction.normalization import TextNormalizer

            # Extract title
            canonical_url = MetadataExtractor.extract_canonical_url(html_content)
            title = MetadataExtractor.extract_title(html_content)
            result["canonical_url"] = canonical_url
            result["title"] = title

            lang = MetadataExtractor.extract_language(html_content)
            result["language"] = lang

            # Try to extract body text via simple tag stripping
            import re
            body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
            if body_match:
                body_html = body_match.group(1)
                text = re.sub(r'<[^>]+>', ' ', body_html)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    result["body_text"] = TextNormalizer.normalize_whitespace(text)
                    result["extraction_quality"] = "partial"

            opengraph = MetadataExtractor.extract_opengraph(html_content)
            if opengraph:
                result["structured_data"]["opengraph"] = opengraph
                if not result["title"] and opengraph.get("og:title"):
                    result["title"] = opengraph["og:title"]

            jsonld = MetadataExtractor.extract_json_ld(html_content)
            if jsonld:
                result["structured_data"]["json_ld"] = jsonld

        except Exception as e:
            result["extraction_quality"] = "failed"
            warnings.append(f"Fallback extraction: {e}")

        result["warnings"] = warnings
        return result

    def extract(self, html_content: str, url: str = "") -> HtmlExtractionResult:
        """Extract structured data from raw HTML content.

        Parameters
        ----------
        html_content : str
            The raw HTML string to process.
        url : str, optional
            The source URL (used for better relative URL resolution if needed).

        Returns
        -------
        HtmlExtractionResult
        """
        extracted_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        warnings: list[str] = []
        structured_data: dict[str, Any] = {}
        title = author = published_at = updated_at = canonical_url = language = ""
        body_text = ""
        extraction_quality = "empty"

        if not html_content or not html_content.strip():
            warnings.append("Empty HTML content provided.")
            return HtmlExtractionResult(
                extraction_quality="empty",
                warnings=warnings,
                extracted_at=extracted_at,
            )

        # ----- Try Trafilatura first -----
        if self.trafilatura_available:
            try:
                result = self._extract_with_trafilatura(html_content)
                title = result.get("title", "")
                body_text = result.get("body_text", "")
                author = result.get("author", "")
                published_at = result.get("published_at", "")
                updated_at = result.get("updated_at", "")
                canonical_url = result.get("canonical_url", "")
                language = result.get("language", "")
                structured_data = result.get("structured_data", {})
                warnings.extend(result.get("warnings", []))
            except Exception as exc:
                warnings.append(f"Trafilatura extraction failed: {exc}")
                # Fall through to fallback

        # ----- Fallback: regex-based extraction -----
        if not body_text:
            try:
                fallback = self._extract_fallback(html_content)
                if not title:
                    title = fallback.get("title", "")
                if not body_text:
                    body_text = fallback.get("body_text", "")
                if not author:
                    author = fallback.get("author", "")
                if not published_at:
                    published_at = fallback.get("published_at", "")
                if not updated_at:
                    updated_at = fallback.get("updated_at", "")
                if not canonical_url:
                    canonical_url = fallback.get("canonical_url", "")
                if not language:
                    language = fallback.get("language", "")
                if not structured_data:
                    structured_data = fallback.get("structured_data", {})
                warnings.extend(fallback.get("warnings", []))
            except Exception as exc:
                warnings.append(f"Fallback extraction failed: {exc}")

        # ----- Normalize body text -----
        if body_text:
            body_text = TextNormalizer.normalize_line_endings(body_text)
            body_text = TextNormalizer.normalize_whitespace(body_text)
            body_text = TextNormalizer.strip_noise_elements(body_text)

        # ----- Determine quality -----
        if body_text and len(body_text) > 50:
            extraction_quality = "complete"
        elif body_text and len(body_text) > 0:
            extraction_quality = "partial"
        elif title or author or published_at or canonical_url:
            extraction_quality = "metadata_only"
        else:
            extraction_quality = "failed"

        # ----- Detect language from HTML if not already set -----
        if not language:
            language = MetadataExtractor.extract_language(html_content)
            if not language:
                # Simple heuristic: check for common language indicators in body
                lang_hint = self._detect_language_heuristic(body_text or title)
                if lang_hint:
                    language = lang_hint

        return HtmlExtractionResult(
            title=title,
            body_text=body_text,
            author=author,
            published_at=published_at,
            updated_at=updated_at,
            canonical_url=canonical_url,
            language=language,
            extraction_quality=extraction_quality,
            structured_data=structured_data,
            warnings=warnings,
            extracted_at=extracted_at,
        )

    # ------------------------------------------------------------------
    # Trafilatura extraction
    # ------------------------------------------------------------------
    def _extract_with_trafilatura(self, html_content: str) -> dict:
        """Use trafilatura to extract body text and metadata."""
        result: dict[str, Any] = {
            "title": "",
            "body_text": "",
            "author": "",
            "published_at": "",
            "updated_at": "",
            "canonical_url": "",
            "language": "",
            "structured_data": {},
            "warnings": [],
        }
        t = self.trafilatura_module

        # Body text
        try:
            extracted = t.extract(html_content, output_format="txt", include_tables=False)
            if extracted:
                result["body_text"] = extracted
        except Exception as exc:
            result["warnings"].append(f"trafilatura.extract failed: {exc}")

        # Metadata
        try:
            meta = t.bare_extraction(
                html_content,
                include_links=False,
                include_images=False,
                include_tables=False,
                output_format="python",
            )
            if meta and isinstance(meta, dict):
                result["title"] = meta.get("title") or ""
                result["author"] = meta.get("author") or ""
                result["published_at"] = meta.get("date") or ""
                result["canonical_url"] = meta.get("url") or ""
                result["language"] = meta.get("hostname") or ""
        except Exception as exc:
            result["warnings"].append(f"trafilatura.bare_extraction failed: {exc}")

        # Structured data via MetadataExtractor
        try:
            jsonld = MetadataExtractor.extract_json_ld(html_content)
            if jsonld:
                result["structured_data"]["json_ld"] = jsonld
            opengraph = MetadataExtractor.extract_opengraph(html_content)
            if opengraph:
                result["structured_data"]["opengraph"] = opengraph
            meta_tags = M
            meta_tags = MetadataExtractor.extract_meta_tags(html_content)
            if meta_tags:
                result["structured_data"]["meta_tags"] = meta_tags

        except Exception as e:
            warnings.append(f"Structured data extraction failed: {e}")

        return HtmlExtractionResult(
            title=result.get("title", ""),
            body_text=result.get("body_text", ""),
            author=result.get("author", ""),
            published_at=result.get("published_at", ""),
            updated_at=result.get("updated_at", ""),
            canonical_url=result.get("canonical_url", ""),
            language=result.get("language", ""),
            extraction_quality=result.get("extraction_quality", "failed"),
            structured_data=result.get("structured_data", {}),
            warnings=tuple(warnings),
            extracted_at=result.get("extracted_at", ""),
        )
