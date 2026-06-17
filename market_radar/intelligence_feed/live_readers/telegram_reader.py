"""TelegramReader — reads Telegram-sourced items from injected SQLite DB.

Contract (VERIFIED from local_news_flow_tg_sent_state.sqlite + telegram_publisher.py):
    SQLite schema:
      sent: content_hash, sent_at, chat_id, msg_id, status, error

    The reader can also read from a generic messages table if present.

Design:
  - URI read-only mode (sqlite3.connect(uri, uri=True) with ?mode=ro)
  - No INSERT, UPDATE, DELETE, VACUUM, or schema migration
  - Single synchronous read_once() call
  - No daemon, no thread, no scheduler
  - chat_id + msg_id used for stable identity
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.intelligence_feed.live_readers.protocol import (
    ReaderProtocol, ReaderBatchResult, ReaderStatus, _utc_now, _now_ms,
)
from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, make_feed_id, make_freshness,
)


# Default SQL query for the sent-state table
_SENT_SQL = """
SELECT content_hash, sent_at, chat_id, msg_id, status, error
FROM sent
ORDER BY sent_at DESC
"""

# Generic messages table query (if present)
_MESSAGES_SQL = """
SELECT message_id, chat_id, text, date, title
FROM messages
ORDER BY date DESC
"""


class TelegramReader(ReaderProtocol):
    """Read Telegram feed items from an injected SQLite database (read-only).

    Args:
        db_path: Path to SQLite file.
        source_label: Override label (defaults to filename stem).
        limit: Max items to return (0 = no limit).
        reference_time: Deterministic time for freshness computation.
        query: Optional custom SQL SELECT (must return usable columns).
        table: 'sent' or 'messages' — selects built-in query for known schemas.
    """

    def __init__(
        self,
        db_path: str,
        source_label: Optional[str] = None,
        limit: int = 0,
        reference_time: Optional[datetime] = None,
        query: Optional[str] = None,
        table: str = "sent",
    ):
        self._db_path = db_path
        self._label = source_label or os.path.splitext(os.path.basename(db_path))[0]
        self._limit = limit
        self._reference_time = reference_time
        self._query = query
        self._table = table

    @property
    def source_type(self) -> FeedSourceType:
        return FeedSourceType.TELEGRAM

    @property
    def source_name(self) -> str:
        return f"telegram:{self._label}"

    def read_once(self) -> ReaderBatchResult:
        started_at = _utc_now()
        start_ms = _now_ms()
        errors: list[str] = []

        if not os.path.isfile(self._db_path):
            return ReaderBatchResult(
                source_name=self.source_name,
                source_type=FeedSourceType.TELEGRAM,
                status=ReaderStatus.UNAVAILABLE,
                errors=[f"Database not found: {self._db_path}"],
                started_at=started_at,
                finished_at=_utc_now(),
            )

        try:
            rows = self._query_db()
        except sqlite3.DatabaseError as e:
            return ReaderBatchResult(
                source_name=self.source_name,
                source_type=FeedSourceType.TELEGRAM,
                status=ReaderStatus.DEGRADED,
                errors=[f"SQLite error: {e}"],
                started_at=started_at,
                finished_at=_utc_now(),
            )

        items: list[FeedItem] = []
        seen = 0
        rejected = 0

        for row in rows:
            seen += 1
            item = self._row_to_item(row)
            if item is None:
                rejected += 1
                continue
            items.append(item)
            if self._limit > 0 and len(items) >= self._limit:
                break

        latency = _now_ms() - start_ms

        status = ReaderStatus.OK if items else ReaderStatus.DEGRADED
        return ReaderBatchResult(
            source_name=self.source_name,
            source_type=FeedSourceType.TELEGRAM,
            status=status,
            items=items,
            records_seen=seen,
            records_accepted=len(items),
            records_rejected=rejected,
            errors=errors,
            provenance=f"injected_sqlite_ro:{self._db_path}",
            started_at=started_at,
            finished_at=_utc_now(),
            data_mode=FeedDataMode.LIVE,
        )

    def _query_db(self) -> list[sqlite3.Row]:
        """Execute the configured query in read-only mode.

        Uses URI mode with ?mode=ro to prevent any writes.
        """
        uri = f"file:{os.path.abspath(self._db_path)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("PRAGMA query_only = 1")
            # Verify read-only: try an INSERT (should fail silently or raise)
            try:
                conn.execute("CREATE TABLE _ro_test (x int)")
                conn.execute("DROP TABLE _ro_test")
                # If we get here, read-only mode is NOT working — abort
                return []
            except sqlite3.OperationalError:
                pass  # Expected — read-only mode is active

            if self._query:
                sql = self._query
            elif self._table == "messages":
                sql = _MESSAGES_SQL
            else:
                sql = _SENT_SQL

            try:
                cur = conn.execute(sql)
                return cur.fetchall()
            except sqlite3.OperationalError as e:
                # Table not found or query error
                return []
        finally:
            conn.close()

    def _row_to_item(self, row: sqlite3.Row) -> Optional[FeedItem]:
        """Convert a SQLite row to FeedItem based on the table schema."""
        keys = row.keys()

        if self._table == "messages" or "message_id" in keys:
            return self._row_to_message_item(row)
        return self._row_to_sent_item(row)

    def _row_to_sent_item(self, row: sqlite3.Row) -> Optional[FeedItem]:
        """Convert a 'sent' table row to FeedItem."""
        content_hash = row["content_hash"]
        sent_at = row["sent_at"]
        chat_id = str(row["chat_id"])
        msg_id = str(row["msg_id"])
        status = row["status"]
        error_msg = row["error"]

        title = f"TG Message {msg_id}"
        body = f"Chat: {chat_id} | Status: {status}"
        if error_msg:
            body += f" | Error: {error_msg}"

        # Stable identity from chat_id + msg_id
        id_content = f"{chat_id}:{msg_id}"
        feed_id = make_feed_id(id_content, self._label)
        freshness = make_freshness(sent_at, reference_time=self._reference_time)

        return FeedItem(
            feed_id=feed_id,
            source_type=FeedSourceType.TELEGRAM,
            source_label=self._label,
            data_mode=FeedDataMode.LIVE,
            title=title,
            body=body,
            published_at=sent_at,
            freshness=freshness,
            original_id=f"{chat_id}:{msg_id}",
        )

    def _row_to_message_item(self, row: sqlite3.Row) -> Optional[FeedItem]:
        """Convert a 'messages' table row to FeedItem."""
        message_id = str(row["message_id"])
        chat_id = str(row["chat_id"])
        text = row["text"] if row["text"] else None
        date_raw = row["date"]
        title = row["title"] if row["title"] else None

        # published_at: convert unix timestamp to ISO if integer
        published_at: Optional[str] = None
        if date_raw is not None:
            try:
                ts = int(date_raw)
                published_at = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, OSError):
                published_at = str(date_raw)

        if not title and not text:
            title = f"TG Message {message_id}"

        id_content = f"{chat_id}:{message_id}"
        feed_id = make_feed_id(id_content, self._label)
        freshness = make_freshness(published_at, reference_time=self._reference_time)

        return FeedItem(
            feed_id=feed_id,
            source_type=FeedSourceType.TELEGRAM,
            source_label=self._label,
            data_mode=FeedDataMode.LIVE,
            title=title or f"TG Message {message_id}",
            body=str(text).strip() if text else None,
            assets=[],
            published_at=published_at,
            freshness=freshness,
            original_id=f"{chat_id}:{message_id}",
        )


def _verify_read_only(db_path: str) -> bool:
    """Verify a SQLite connection is truly read-only.

    Returns True if write operations are blocked.
    """
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("PRAGMA query_only = 1")
        try:
            conn.execute("CREATE TABLE _tg_ro_verify (x int)")
            conn.execute("DROP TABLE _tg_ro_verify")
            conn.close()
            return False  # Writes succeeded — NOT read-only
        except sqlite3.OperationalError:
            conn.close()
            return True  # Writes blocked — read-only confirmed
    except sqlite3.Error:
        return False
