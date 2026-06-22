"""Structured metadata extraction from HTML."""

import json
import re
from typing import Any


class MetadataExtractor:
    """Extract structured metadata from HTML using JSON-LD, OpenGraph, meta tags, etc."""

    @staticmethod
    def extract_json_ld(html: str) -> list[dict]:
        """Parse JSON-LD script tags from HTML and return list of parsed dicts."""
        results: list[dict] = []
        if not html:
            return results
        # Find <script type="application/ld+json">...</script>
        pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(html):
            raw = match.group(1).strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
            except json.JSONDecodeError:
                # Graceful — skip malformed blocks
                pass
        return results

    @staticmethod
    def extract_opengraph(html: str) -> dict:
        """Find meta[property^=og:] tags and return dict of og:property -> content."""
        result: dict[str, str] = {}
        if not html:
            return result
        # <meta property="og:..." content="..." />
        pattern = re.compile(
            r'<meta[^>]+property=["\'](og:[^"\']+)["\'][^>]*content=["\']([^"\']*)["\']',
            re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            prop = match.group(1).strip()
            content = match.group(2).strip()
            if prop:
                result[prop] = content
        return result

    @staticmethod
    def extract_meta_tags(html: str) -> dict:
        """Find meta[name] tags and return dict of name -> content."""
        result: dict[str, str] = {}
        if not html:
            return result
        # <meta name="..." content="..." />
        pattern = re.compile(
            r'<meta[^>]+name=["\']([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']',
            re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            name = match.group(1).strip()
            content = match.group(2).strip()
            if name:
                result[name] = content
        return result

    @staticmethod
    def extract_time_tags(html: str) -> list[dict]:
        """Find <time> tags, extract datetime attribute and text content."""
        results: list[dict[str, str]] = []
        if not html:
            return results
        pattern = re.compile(
            r'<time[^>]*datetime=["\']([^"\']*)["\']>([^<]*)</time>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(html):
            results.append(
                {
                    "datetime": match.group(1).strip(),
                    "text": match.group(2).strip(),
                }
            )
        return results

    @staticmethod
    def extract_canonical_url(html: str) -> str:
        """Find link[rel=canonical] and return href or empty string."""
        if not html:
            return ""
        pattern = re.compile(
            r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match:
            return match.group(1).strip()
        # Also try reversed attribute order
        pattern2 = re.compile(
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']',
            re.IGNORECASE,
        )
        match2 = pattern2.search(html)
        return match2.group(1).strip() if match2 else ""

    @staticmethod
    @staticmethod
    def extract_title(html: str) -> str:
        """Extract the <title> tag content from HTML."""
        import re
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ""


    def extract_language(html: str) -> str:
        """Extract language from html[lang] attribute."""
        if not html:
            return ""
        pattern = re.compile(r'<html[^>]*lang=["\']([^"\']+)["\']', re.IGNORECASE)
        match = pattern.search(html)
        if match:
            return match.group(1).strip()
        return ""
