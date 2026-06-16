"""MVP+ L6 — Safety Patterns & Third-Party Reuse Manifest.

Implements:
  - URL scheme allowlist
  - HTML escaping (output context)
  - Path traversal protection
  - Atomic writes utility
  - Request parameter validation
  - Third-party reuse manifest generation

Does NOT implement:
  - Authentication (not needed — read-only public APIs)
  - Encryption (not needed — local-only)
  - Input sanitization from user (no user input)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

# ── URL Scheme Allowlist ──────────────────────────────────────────────────────

ALLOWED_URL_SCHEMES = {"https", "http"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
ALLOWED_URL_PATTERNS = {
    r"^https://api\.binance\.com/",
    r"^https://api\.hyperliquid\.xyz/",
    r"^https://fapi\.binance\.com/",
    r"^https://testnet\.binancefuture\.com/",
}


class URLValidationError(ValueError):
    """Raised when URL fails safety validation."""


def validate_request_url(url: str) -> str:
    """Validate URL for outgoing requests.

    Checks:
      1. Scheme is HTTPS or HTTP (only for known safe endpoints)
      2. Not a blocked host (localhost, etc.)
      3. Matches at least one allowed URL pattern

    Raises URLValidationError if invalid.
    Returns the URL if valid.
    """
    import urllib.parse
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        raise URLValidationError(f"URL scheme '{parsed.scheme}' not allowed")

    hostname = parsed.hostname or ""
    if hostname in BLOCKED_HOSTS:
        raise URLValidationError(f"Host '{hostname}' is blocked")

    allowed = any(re.match(p, url) for p in ALLOWED_URL_PATTERNS)
    if not allowed:
        raise URLValidationError(f"URL '{url}' does not match any allowed pattern")

    return url


# ── HTML Escaping ─────────────────────────────────────────────────────────────

_HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
}


def escape_html(text: str) -> str:
    """Escape text for safe HTML output. Prevents XSS in workbench HTML."""
    return "".join(_HTML_ESCAPE_TABLE.get(c, c) for c in text)


def escape_html_attr(text: str) -> str:
    """Escape text for HTML attribute context."""
    escaped = escape_html(text)
    return escaped.replace('"', "&quot;").replace("'", "&#x27;")


# ── Path Traversal Protection ─────────────────────────────────────────────────

class PathTraversalError(ValueError):
    """Raised when path traversal is detected."""


def safe_resolve_path(base_dir: str, user_path: str) -> str:
    """Resolve a path relative to base_dir, preventing traversal above base_dir.

    Raises PathTraversalError if the resolved path escapes base_dir.
    """
    resolved = os.path.normpath(os.path.join(base_dir, user_path))
    if not resolved.startswith(os.path.normpath(base_dir)):
        raise PathTraversalError(f"Path '{user_path}' escapes base directory")
    return resolved


# ── Atomic File Write ─────────────────────────────────────────────────────────

def atomic_write(filepath: str, data: str, encoding: str = "utf-8"):
    """Write data to file atomically using temporary file + rename.

    On failure, the target file is not corrupted.
    """
    tmp = filepath + ".tmp." + os.urandom(4).hex()
    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(data)
        os.replace(tmp, filepath)
    except Exception:
        # Clean up temp file on failure
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(filepath: str, data: Any):
    """Write JSON data atomically."""
    content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    atomic_write(filepath, content)


# ── Shell Interpolation Guard ─────────────────────────────────────────────────

def safe_shell_arg(arg: str) -> str:
    """Basic guard: reject shell metacharacters in arguments."""
    if re.search(r'[;&|`$(){}[\]!#~*?\\\n]', arg):
        raise ValueError(f"Shell metacharacters rejected in argument: {arg[:50]}")
    return arg


# ── Third-Party Reuse Manifest ────────────────────────────────────────────────

THIRD_PARTY_MANIFEST = {
    "meta": {
        "generated_at": "",
        "project": "Crypto Signal Intelligence MVP+",
        "version": "mvp+v1.0",
    },
    "dependencies": [
        {
            "name": "hyperliquid-python-sdk",
            "version": "inferred (public Info API)",
            "source_url": "https://github.com/hyperliquid-dex/hyperliquid-python-sdk",
            "usage": "API pattern reference for POST JSON to Hyperliquid Info endpoint",
            "license": "MIT (inferred from GitHub repo)",
            "provenance": "Adapted — uses same Info API endpoint, no SDK dependency",
            "original_code_reused": False,
            "api_pattern_reused": True,
        },
        {
            "name": "ccxt",
            "version": "inferred (Binance public REST API)",
            "source_url": "https://github.com/ccxt/ccxt",
            "usage": "API pattern reference for Binance public ticker endpoint",
            "license": "MIT",
            "provenance": "Adapted — uses raw HTTP to Binance, no ccxt dependency",
            "original_code_reused": False,
            "api_pattern_reused": True,
        },
        {
            "name": "httpx / urllib",
            "version": "stdlib (urllib)",
            "source_url": "https://docs.python.org/3/library/urllib.request.html",
            "usage": "HTTP requests to public APIs",
            "license": "Python Software Foundation License",
            "provenance": "Standard library — no external dependency",
            "original_code_reused": False,
            "api_pattern_reused": False,
        },
        {
            "name": "kittycapital/hyperliquid-whales",
            "version": "reference only",
            "source_url": "https://github.com/kittycapital/hyperliquid-whales",
            "usage": "Concept reference for whale position tracking patterns",
            "license": "MIT",
            "provenance": "Concept reference only — no code copied. Uses same public Info API.",
            "original_code_reused": False,
            "api_pattern_reused": True,
        },
    ],
    "dependency_pinning": {
        "method": "None — all dependencies are stdlib (json, sqlite3, urllib, csv, os, etc.)",
        "notes": "No pip packages required beyond pandas and requests (existing project deps). "
                 "MVP+ workbench runs entirely on Python standard library.",
    },
    "license_compliance": {
        "status": "All dependencies are MIT or PSF-licensed. No copyleft dependencies.",
        "risk": "None identified — all public APIs are free and read-only.",
    },
}


def generate_third_party_manifest(output_path: str) -> str:
    """Generate and save the third-party reuse manifest."""
    import copy
    manifest = copy.deepcopy(THIRD_PARTY_MANIFEST)
    from datetime import datetime, timezone
    manifest["meta"]["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    atomic_write_json(output_path, manifest)
    return output_path
