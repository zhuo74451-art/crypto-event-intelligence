"""Multi-layer deterministic dedup engine — FeedItem deduplication.

Priority layers:
  1. source + original_id/tweet_id
  2. Canonical URL (normalized)
  3. Explicit content fingerprint (SHA256 of body)
  4. Normalized title fingerprint
  5. Near-duplicate text fingerprint (normalized tokens)

All deterministic — no LLM, no vectors.
"""
from __future__ import annotations
import hashlib
import re
import unicodedata
from urllib.parse import urlparse, urlunparse
from typing import Optional

from market_radar.intelligence_feed.models import FeedItem
from .models import DuplicateInfo, DuplicateType, DuplicateResult


_URL_CLEAN = re.compile(r"^(?:https?://)?(?:www\.)?", re.IGNORECASE)
_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                    "utm_content", "ref", "source", "fbclid", "gclid", "mc_cid"}
_NONWORD = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def normalize_url(raw: Optional[str]) -> Optional[str]:
    """Normalize URL: lowercase, strip tracking params, sort query."""
    if not raw:
        return None
    try:
        parsed = urlparse(raw.lower().strip())
        # Keep only scheme + netloc + path, strip fragments
        clean = parsed._replace(fragment="")
        # Remove tracking query params
        if parsed.query:
            params = sorted(
                p for p in parsed.query.split("&") if p.split("=")[0] not in _TRACKING_PARAMS
            )
            clean = clean._replace(query="&".join(params))
        return urlunparse(clean)
    except Exception:
        return None


def _fingerprint(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    normalized = unicodedata.normalize("NFKC", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _title_fingerprint(title: Optional[str]) -> Optional[str]:
    if not title:
        return None
    # Remove punctuation, collapse whitespace, lowercase
    t = _NONWORD.sub(" ", title.lower())
    t = _WHITESPACE.sub(" ", t).strip()
    tokens = [w for w in t.split() if len(w) > 1]
    return hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()


def _near_dup_fingerprint(title: Optional[str], body: Optional[str]) -> Optional[str]:
    """Create a fuzzy fingerprint from normalized tokens."""
    text = (title or "") + " " + (body or "")
    t = _NONWORD.sub(" ", text.lower())
    t = _WHITESPACE.sub(" ", t).strip()
    tokens = sorted(set(w for w in t.split() if len(w) > 2))
    return hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()


class DedupEngine:
    """Multi-layer deterministic dedup engine.

    Args:
        same_source_only: If True, only dedup within same source_label.
    """

    def __init__(self, same_source_only: bool = False):
        self._same_source = same_source_only

    def dedup(self, items: list[FeedItem]) -> DuplicateResult:
        """Deduplicate items. Returns canonical items and duplicate map."""
        canonical: dict[str, FeedItem] = {}
        dup_map: dict[str, DuplicateInfo] = {}
        seen_urls: dict[str, str] = {}
        seen_content: dict[str, str] = {}
        seen_titles: dict[str, str] = {}
        seen_near: dict[str, str] = {}
        removed: set[str] = set()

        for item in items:
            fid = item.feed_id
            if fid in removed:
                continue

            # Layer 1: source + original_id
            if item.original_id:
                key = f"{item.source_label}:{item.original_id}"
                if key in canonical:
                    existing = canonical[key]
                    dup_map[fid] = DuplicateInfo(
                        duplicate_of=existing.feed_id,
                        duplicate_reason=DuplicateType.EXACT,
                        duplicate_confidence=1.0,
                        canonical_item_id=key,
                        source_copies=[fid],
                    )
                    removed.add(fid)
                    continue
                else:
                    canonical[key] = item
                    continue

            # Layer 2: Canonical URL
            url = normalize_url(item.url)
            if url:
                if url in seen_urls:
                    ex_id = seen_urls[url]
                    dup_map[fid] = DuplicateInfo(
                        duplicate_of=ex_id, duplicate_reason=DuplicateType.MIRRORED,
                        duplicate_confidence=0.95, canonical_item_id=url,
                    )
                    removed.add(fid)
                    continue
                seen_urls[url] = fid

            # Layer 3: Content fingerprint
            cf = _fingerprint(item.body)
            if cf and cf in seen_content:
                ex_id = seen_content[cf]
                dup_map[fid] = DuplicateInfo(
                    duplicate_of=ex_id, duplicate_reason=DuplicateType.EXACT,
                    duplicate_confidence=1.0, canonical_item_id=cf,
                )
                removed.add(fid)
                continue
            if cf:
                seen_content[cf] = fid

            # Layer 4: Title fingerprint
            tf = _title_fingerprint(item.title)
            if tf and tf in seen_titles:
                ex_id = seen_titles[tf]
                # Check if body differs → updated version
                ex_item = next((i for i in items if i.feed_id == ex_id), None)
                ex_body_fp = _fingerprint(ex_item.body) if ex_item else None
                cur_body_fp = _fingerprint(item.body)
                if ex_body_fp and cur_body_fp and ex_body_fp != cur_body_fp:
                    dr = DuplicateType.UPDATED
                    dc = 0.8
                else:
                    dr = DuplicateType.RELATED
                    dc = 0.7
                dup_map[fid] = DuplicateInfo(
                    duplicate_of=ex_id, duplicate_reason=dr,
                    duplicate_confidence=dc, canonical_item_id=tf,
                )
                removed.add(fid)
                continue
            seen_titles[tf] = fid

            # Layer 5: Near-dup fingerprint
            nf = _near_dup_fingerprint(item.title, item.body)
            if nf and nf in seen_near:
                ex_id = seen_near[nf]
                dup_map[fid] = DuplicateInfo(
                    duplicate_of=ex_id, duplicate_reason=DuplicateType.RELATED,
                    duplicate_confidence=0.6, canonical_item_id=nf,
                )
                removed.add(fid)
                continue
            if nf:
                seen_near[nf] = fid

        canonical_items = [i for i in items if i.feed_id not in removed]
        return DuplicateResult(
            canonical_items=canonical_items,
            removed_count=len(removed),
            duplicate_map=dup_map,
        )
