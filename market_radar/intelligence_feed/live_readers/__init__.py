"""Live feed readers — read-once, synchronous, no daemon/thread/scheduler.

Exports:
    ReaderProtocol, ReaderBatchResult, ReaderHealth
    FlashReader, NewsReader, TelegramReader
    read_all_once, FeedReadSummary
"""
from .protocol import ReaderProtocol, ReaderBatchResult, ReaderHealth, ReaderStatus
from .flash_reader import FlashReader
from .news_reader import NewsReader
from .telegram_reader import TelegramReader
from .aggregate import read_all_once, FeedReadSummary

__all__ = [
    "ReaderProtocol", "ReaderBatchResult", "ReaderHealth",
    "FlashReader", "NewsReader", "TelegramReader",
    "read_all_once", "FeedReadSummary",
]
