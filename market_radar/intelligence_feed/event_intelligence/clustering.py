"""Cross-source event clustering — groups FeedItems into IntelligenceEvents.

Uses deterministic rules: asset overlap, entity overlap, topic overlap,
title token similarity, URL domain, time window.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from market_radar.intelligence_feed.models import FeedItem, FeedSourceType
from .models import (
    IntelligenceEvent, EventStatus, EventClusterConfig, Entity, Asset, Topic,
    ExtractionResult, SourceIndependence, SourceGroup, TimelineEntry,
    DuplicateResult,
)
from .extraction import ExtractionEngine
from .timeline import TimelineBuilder


_NONWORD = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _tokenize(text: str) -> set[str]:
    t = _NONWORD.sub(" ", text.lower())
    t = _WHITESPACE.sub(" ", t).strip()
    return set(w for w in t.split() if len(w) > 2)


def _title_overlap(t1: str, t2: str) -> float:
    tok1 = _tokenize(t1)
    tok2 = _tokenize(t2)
    if not tok1 or not tok2:
        return 0.0
    inter = tok1 & tok2
    return len(inter) / max(len(tok1), len(tok2))


def _make_event_id(items: list[FeedItem], cfg: EventClusterConfig) -> str:
    """Deterministic event ID from canonical items."""
    raw = ":".join(sorted(i.feed_id for i in items[:5]))
    return "ev_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class ClusteringEngine:
    """Groups deduplicated FeedItems into IntelligenceEvents.

    Args:
        config: EventClusterConfig with thresholds and weights.
        extractor: ExtractionEngine for asset/entity/topic extraction.
    """

    def __init__(self, config: Optional[EventClusterConfig] = None,
                 extractor: Optional[ExtractionEngine] = None):
        self._config = config or EventClusterConfig()
        self._extractor = extractor or ExtractionEngine()
        self._source_domains: dict[str, str] = {}  # url -> domain

    def cluster(self, items: list[FeedItem],
                dup_result: Optional[DuplicateResult] = None) -> list[IntelligenceEvent]:
        """Cluster deduplicated FeedItems into events.

        Args:
            items: Deduplicated FeedItems.
            dup_result: Optional DuplicateResult for copy info.

        Returns:
            List of IntelligenceEvents.
        """
        if not items:
            return []

        events: list[IntelligenceEvent] = []
        assigned: set[str] = set()

        # Sort by published_at ascending for stable order
        sorted_items = sorted(
            items,
            key=lambda x: x.published_at or "9999",
        )

        for item in sorted_items:
            if item.feed_id in assigned:
                continue

            # Extract features
            extr = self._extractor.extract(
                title=item.title, body=item.body or "",
                source_label=item.source_label,
            )

            # Find best matching event
            best_event_idx = self._find_best_event(item, extr, events, assigned)
            if best_event_idx is not None:
                event = events[best_event_idx]
                self._add_to_event(event, item, extr)
                assigned.add(item.feed_id)
            else:
                # Create new event
                event = self._create_event(item, extr)
                events.append(event)
                assigned.add(item.feed_id)

        # Post-process: set statuses, merge small events
        for event in events:
            self._finalize_event(event)

        return events

    def _find_best_event(self, item: FeedItem, extr: ExtractionResult,
                         events: list[IntelligenceEvent],
                         assigned: set[str]) -> Optional[int]:
        """Find best existing event for this item. Returns index or None."""
        best_idx: Optional[int] = None
        best_score = 0.0

        for idx, event in enumerate(events):
            score = self._cluster_score(item, extr, event)
            # Boost if same source group
            if event.items:
                event_sources = {i.source_label for i in event.items}
                item_groups = self._compute_source_groups([item.source_label])
                event_groups = self._compute_source_groups(list(event_sources))
                shared_groups = set(g.group_label for g in item_groups) & set(g.group_label for g in event_groups)
                if shared_groups:
                    score += 15.0  # Same source group boost
            # Require at least one of these overlaps for clustering
            item_tokens = _tokenize(item.title)
            event_tokens = _tokenize(event.canonical_title)
            title_overlap = (len(item_tokens & event_tokens) / max(len(item_tokens | event_tokens), 1)
                             if item_tokens and event_tokens else 0.0)
            has_content_overlap = bool(
                title_overlap > 0.3
                or (extr.assets and event.assets and
                    {a.symbol for a in extr.assets} & {a.symbol for a in event.assets})
                or (extr.topics and event.topics and
                    {t.topic for t in extr.topics} & {t.topic for t in event.topics})
                or (extr.entities and event.entities and
                    {e.name.lower() for e in extr.entities} & {e.name.lower() for e in event.entities})
            )
            if score > 25.0 and score > best_score and has_content_overlap:
                best_score = score
                best_idx = idx

        return best_idx

    def _cluster_score(self, item: FeedItem, extr: ExtractionResult,
                       event: IntelligenceEvent) -> float:
        """Compute clustering score between item and existing event."""
        score = 0.0

        # Asset overlap (0-30)
        item_assets = {a.symbol for a in extr.assets}
        event_assets = {a.symbol for a in event.assets}
        if item_assets and event_assets:
            overlap = item_assets & event_assets
            score += 30.0 * (len(overlap) / max(len(item_assets | event_assets), 1))

        # Topic overlap (0-20)
        item_topics = {t.topic for t in extr.topics}
        event_topics = {t.topic for t in event.topics}
        if item_topics and event_topics:
            overlap = item_topics & event_topics
            score += 20.0 * (len(overlap) / max(len(item_topics | event_topics), 1))

        # Title overlap (0-25)
        title_sim = _title_overlap(item.title, event.canonical_title)
        score += 25.0 * title_sim

        # Time proximity (0-15)
        item_ts = _parse_ts(item.published_at)
        event_ts = _parse_ts(event.latest_at or event.started_at)
        if item_ts and event_ts:
            hours_diff = abs((item_ts - event_ts).total_seconds()) / 3600
            if hours_diff <= self._config.time_window_hours:
                score += 15.0 * (1.0 - hours_diff / self._config.time_window_hours)

        # Entity overlap (0-10)
        item_entities = {e.name.lower() for e in extr.entities}
        event_entities = {e.name.lower() for e in event.entities}
        if item_entities and event_entities:
            overlap = item_entities & event_entities
            score += 10.0 * (len(overlap) / max(len(item_entities | event_entities), 1))

        return score

    def _create_event(self, item: FeedItem, extr: ExtractionResult) -> IntelligenceEvent:
        """Create a new IntelligenceEvent from a single item."""
        event_id = _make_event_id([item], self._config)
        event_type = self._infer_event_type(extr)

        now = _parse_ts(item.published_at)
        started = item.published_at or item.ingested_at

        return IntelligenceEvent(
            event_id=event_id,
            event_type=event_type,
            canonical_title=item.title,
            summary=(item.body or "")[:200],
            started_at=started,
            latest_at=started,
            status=EventStatus.NEW,
            entities=extr.entities,
            assets=extr.assets,
            topics=extr.topics,
            items=[item],
            source_count=1,
            source_diversity=1,
            evidence_count=1 if item.body else 0,
            timeline=[TimelineEntry(
                timestamp=started or "",
                item_id=item.feed_id,
                source_label=item.source_label,
                event_type="first_report",
                summary=item.title[:120],
            )],
            source_independence=SourceIndependence(
                raw_source_count=1,
                independent_source_count=1,
                primary_source_candidates=[item.source_label],
            ),
        )

    def _add_to_event(self, event: IntelligenceEvent, item: FeedItem,
                      extr: ExtractionResult):
        """Add an item to an existing event."""
        # Update assets/topics/entities
        seen_assets = {a.symbol for a in event.assets}
        for a in extr.assets:
            if a.symbol not in seen_assets:
                event.assets.append(a)
                seen_assets.add(a.symbol)

        seen_topics = {t.topic for t in event.topics}
        for t in extr.topics:
            if t.topic not in seen_topics:
                event.topics.append(t)
                seen_topics.add(t.topic)

        seen_entities = {e.name.lower() for e in event.entities}
        for e in extr.entities:
            if e.name.lower() not in seen_entities:
                event.entities.append(e)
                seen_entities.add(e.name.lower())

        # Update timeline
        item_ts = item.published_at or item.ingested_at or ""
        event.items.append(item)
        event.evidence_count += 1 if item.body else 0

        # Source tracking
        source_labels = {i.source_label for i in event.items}
        event.source_count = len(source_labels)
        event.source_diversity = self._estimate_diversity(list(source_labels))

        # Update time boundaries
        if item.published_at:
            if not event.started_at or item.published_at < event.started_at:
                event.started_at = item.published_at
            if not event.latest_at or item.published_at > event.latest_at:
                event.latest_at = item.published_at

        # Check for conflicting claims
        existing_titles = {i.title for i in event.items[:-1]}
        title_sim = max(_title_overlap(item.title, t) for t in existing_titles) if existing_titles else 0
        if title_sim < 0.3 and len(event.items) > 1:
            event.conflicting_claims.append(f"'{item.title[:60]}' differs from existing reports")

        # Timeline entry
        event_type = "update"
        if event.conflicting_claims:
            event_type = "conflict"
            event.status = EventStatus.CONFLICTING
        elif event.status == EventStatus.NEW:
            event.status = EventStatus.DEVELOPING

        event.timeline.append(TimelineEntry(
            timestamp=item_ts,
            item_id=item.feed_id,
            source_label=item.source_label,
            event_type=event_type,
            summary=item.title[:120],
        ))

    def _finalize_event(self, event: IntelligenceEvent):
        """Post-process event: compute source groups, set status."""
        source_labels = [i.source_label for i in event.items]
        unique = list(set(source_labels))
        groups = self._compute_source_groups(unique)
        event.source_independence = SourceIndependence(
            raw_source_count=len(source_labels),
            independent_source_count=len(groups),
            source_groups=groups,
            primary_source_candidates=unique[:3],
            mirrored_count=max(0, len(source_labels) - len(groups)),
        )

        # Source diversity heuristic
        if event.source_independence.independent_source_count >= 3:
            if event.status != EventStatus.CONFLICTING:
                event.status = EventStatus.CONFIRMED
        elif event.source_independence.independent_source_count >= 2:
            if event.status == EventStatus.NEW:
                event.status = EventStatus.DEVELOPING

    @staticmethod
    def _compute_source_groups(sources: list[str]) -> list[SourceGroup]:
        """Group sources by likely affiliation."""
        groups: dict[str, list[str]] = {}
        for src in sources:
            s = src.lower().strip()
            if any(domain in s for domain in ["coindesk", "theblock", "cointelegraph", "decrypt"]):
                key = "crypto_media"
            elif "binance" in s or "okx" in s or "bybit" in s or "coinbase" in s:
                key = "exchange"
            elif "telegram" in s or "tg" in s:
                key = "telegram"
            elif "twitter" in s or "x.com" in s:
                key = "social"
            elif "research" in s or "report" in s:
                key = "research"
            else:
                key = "other"
            groups.setdefault(key, []).append(src)
        result = []
        for group_label, sources_list in groups.items():
            result.append(SourceGroup(
                group_label=group_label,
                sources=sources_list,
                is_independent=group_label not in ("telegram", "social"),
            ))
        return result

    @staticmethod
    def _estimate_diversity(sources: list[str]) -> int:
        """Estimate independent source count."""
        if len(sources) <= 1:
            return len(sources)
        # Simple heuristic: each unique domain ≈ independent
        domains = set()
        for s in sources:
            s_lower = s.lower().strip()
            if "coindesk" in s_lower or "theblock" in s_lower:
                domains.add("media")
            elif "binance" in s_lower or "exchange" in s_lower:
                domains.add("exchange")
            elif "telegram" in s_lower:
                domains.add("telegram")
            elif "twitter" in s_lower or "x.com" in s_lower:
                domains.add("social")
            else:
                domains.add(s_lower)
        return max(1, len(domains))

    @staticmethod
    def _infer_event_type(extr: ExtractionResult) -> str:
        """Infer event type from extracted topics."""
        for t in extr.topics:
            if t.topic in ("exploit", "security", "liquidation", "regulation",
                           "listing", "delisting", "etf", "macro", "whale",
                           "partnership", "funding", "governance", "outage",
                           "stablecoin", "token_unlock", "product_launch", "derivatives"):
                return t.topic
        return "general"
