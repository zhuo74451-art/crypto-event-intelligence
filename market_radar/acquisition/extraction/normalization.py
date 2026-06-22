"""Text normalization utilities."""

import hashlib
import re
from typing import List, Tuple


class TextNormalizer:
    """Static methods for cleaning and normalizing text content."""

    # Common noise patterns (substrings or patterns)
    NOISE_PATTERNS: List[Tuple[str, str]] = [
        # Dynamic page counters
        (r'Page\s+\d+\s+of\s+\d+', ''),
        # Session / tracking IDs (e.g. sid=abc123, sessionid=xyz)
        (r'[?&](?:sid|session|sessionid|sess)=[a-zA-Z0-9_-]+', ''),
        # Advertisement markers
        (r'(?:Advertisement|Ad|Sponsored|Promoted|Paid\s+content)[\s: ]*', ''),
        # Cookie consent banners — simple patterns
        (r'This\s+site\s+uses\s+cookies[^.]*\.', ''),
        (r'We\s+use\s+cookies[^.]*\.', ''),
        (r'Accept\s+(?:all\s+)?cookies', ''),
        (r'Cookie\s+(?:Notice|Consent|Policy|Settings)', ''),
        # Common newsletter / subscribe prompts
        (r'Sign\s+up\s+for\s+our\s+newsletter[^.]*\.', ''),
        (r'Subscribe\s+to\s+our\s+(?:newsletter|mailing\s+list)[^.]*\.', ''),
        # "Continue reading" prompts
        (r'Click\s+to\s+(?:continue\s+)?read(?:ing)?\s+more?', ''),
        (r'Read\s+(?:the\s+)?(?:full\s+)?(?:story|article)[^.]*\.', ''),
        # Social sharing
        (r'Share\s+(?:on\s+)?(?:Facebook|Twitter|LinkedIn|Reddit|Telegram)', ''),
        # Generic bracketed labels like [ad], [sponsored]
        (r'\[(?:ad|sponsored|promoted|paid)\]', ''),
    ]

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Strip leading/trailing whitespace and collapse all internal whitespace runs to single space."""
        if not text:
            return ""
        # Collapse any whitespace (spaces, tabs, newlines) to a single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def normalize_line_endings(text: str) -> str:
        """Replace \r\n and \r with \n."""
        if not text:
            return ""
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        return text

    @staticmethod
    def strip_noise_elements(text: str) -> str:
        """Remove common noise patterns from text."""
        if not text:
            return ""
        for pattern, replacement in TextNormalizer.NOISE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        # Clean up any resulting double spaces
        text = re.sub(r' +', ' ', text)
        return text.strip()

    @staticmethod
    def compute_normalized_hash(text: str) -> str:
        """Normalize whitespace then compute SHA-256 hex digest."""
        normalized = TextNormalizer.normalize_whitespace(text)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def compute_identity_hash(text: str) -> str:
        """Same as compute_normalized_hash (kept as alias for clarity)."""
        return TextNormalizer.compute_normalized_hash(text)
