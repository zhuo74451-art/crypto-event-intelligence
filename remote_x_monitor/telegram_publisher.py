from __future__ import annotations

import argparse
import html
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from env_bootstrap import load_env
from newsflash_adapter import build_newsflash_draft_payload
from publish_suggestions import parse_hermes_suggestion


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "data" / "tweets.db"
DEFAULT_STATE_PATH = PROJECT_DIR / "data" / "telegram_publish_state.json"
DEFAULT_BACKEND_PUBLISH_CONFIG_PATH = PROJECT_DIR / "newsflash_publish_config.json"
_BACKEND_PUBLISH_CONFIG_CACHE: dict[str, Any] | None = None

DEFAULT_CONFIG: dict[str, Any] = {
    "chat_ids": [],
    "poll_seconds": 10,
    "max_batch": 5,
    "lookback_minutes": 240,
    "start_from_now": True,
    "default_category": "市场",
    "max_title_chars": 120,
    "max_body_chars": 700,
    "include_body": True,
    "include_time": False,
    "include_source": False,
    "allowed_categories": [],
    "blocked_categories": [],
    "blocked_sources": [],
    "trading_filter_enabled": False,
    "trading_block_categories": ["AI界"],
    "trading_block_content_types": ["exchange_announcement"],
    "trading_force_allow_content_types": [
        "prediction_market"
    ],
    "trading_force_allow_sources": [
        "news:odaily_exchange_gap",
        "news:coinglass"
    ],
    "trading_keywords": [
        "btc", "eth", "bitcoin", "ethereum", "usdt", "usdc", "sol", "bnb",
        "比特币", "以太坊", "稳定币", "山寨币", "加密货币", "加密资产",
        "币价", "现货", "合约", "永续", "期货", "杠杆", "爆仓", "清算",
        "资金费率", "持仓", "未平仓", "open interest", "oi",
        "交易所", "上线", "下架", "充提", "充币", "提币", "交易对",
        "etf", "sec", "链上", "巨鲸", "地址", "转账", "增持", "减持",
        "买入", "卖出", "突破", "跌破", "上涨", "下跌", "暴涨", "暴跌",
        "反弹", "回落", "涨幅", "跌幅", "价格", "行情", "市场",
        "美联储", "降息", "加息", "利率", "cpi", "通胀", "美元",
        "黄金", "原油", "外汇"
    ],
    "source_weights": {
        "news:jin10": 90,
        "tg:HyperInsight": 80,
        "tg:OneMillion_AI": 80,
    },
}

LEADING_NOISE_PREFIXES = (
    "币界网消息，",
    "币界网消息,",
    "币界网快讯，",
    "币界网快讯,",
)
MARKET_DATA_SOURCES = {"news:odaily_exchange_gap", "news:coinglass"}
MARKET_DATA_ATTR_RE = re.compile(
    r"^\s*(?:据\s*)?(?:odaily[_\-\s]*exchange[_\-\s]*gap|coinglass)"
    r"(?:\s*(?:数据)?(?:显示|报道))?\s*[，,：:]?\s*",
    re.IGNORECASE,
)
GATE_DATA_ATTR_RE = re.compile(
    r"^\s*据\s*Gate\s*数据\s*[，,：:]?\s*",
    re.IGNORECASE,
)


def _log(message: str) -> None:
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def load_config(path: str | None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if path:
        config.update(_load_json_file(Path(path)))

    env_chat_ids = (os.getenv("TELEGRAM_PUBLISH_CHAT_IDS") or "").strip()
    if env_chat_ids:
        config["chat_ids"] = [
            part.strip() for part in env_chat_ids.split(",") if part.strip()
        ]

    for key, env_name in (
        ("poll_seconds", "TELEGRAM_PUBLISH_POLL_SECONDS"),
        ("max_batch", "TELEGRAM_PUBLISH_MAX_BATCH"),
        ("lookback_minutes", "TELEGRAM_PUBLISH_LOOKBACK_MINUTES"),
    ):
        raw = (os.getenv(env_name) or "").strip()
        if raw:
            try:
                config[key] = int(raw)
            except ValueError:
                _log(f"[config] ignore invalid {env_name}={raw!r}")

    return config


def load_backend_publish_config() -> dict[str, Any]:
    global _BACKEND_PUBLISH_CONFIG_CACHE
    if _BACKEND_PUBLISH_CONFIG_CACHE is not None:
        return _BACKEND_PUBLISH_CONFIG_CACHE
    path = Path(os.getenv("TELEGRAM_BACKEND_PUBLISH_CONFIG_PATH") or DEFAULT_BACKEND_PUBLISH_CONFIG_PATH)
    data = _load_json_file(path)
    if not data:
        data = {
            "sourceId": 4,
            "language": "cn",
            "terminalStatusList": [],
            "publishLanguageList": ["cn", "tn", "en"],
        }
    _BACKEND_PUBLISH_CONFIG_CACHE = data
    return data


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def ensure_outbox() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_publications (
                tweet_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                telegram_message_id INTEGER,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                message_text TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sent_at TEXT,
                PRIMARY KEY (tweet_id, chat_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_telegram_publications_status
            ON telegram_publications(status, updated_at)
            """
        )
        conn.commit()


def _load_state(path: Path, *, start_from_now: bool) -> dict[str, Any]:
    state = _load_json_file(path)
    if state:
        return state
    first_started_at = _now_iso() if start_from_now else "1970-01-01T00:00:00+00:00"
    state = {"first_started_at": first_started_at}
    _save_state(path, state)
    return state


def _save_state(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _parse_category(value: Any, default_category: str) -> str:
    cats = _parse_categories(value)
    cats = [c for c in cats if c and c != "重要"]
    if not cats:
        return default_category
    return cats[0]


def _parse_categories(value: Any) -> list[str]:
    cats: list[str] = []
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except Exception:
            parsed = value
    else:
        parsed = value

    if isinstance(parsed, list):
        cats = [str(x).strip() for x in parsed if str(x).strip()]
    elif isinstance(parsed, str) and parsed.strip():
        cats = [parsed.strip()]

    return [c for c in cats if c]


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    changed = True
    while changed:
        changed = False
        for prefix in LEADING_NOISE_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix) :].lstrip()
                changed = True
    return " ".join(text.split())


def _clean_body_text(value: Any, source: Any) -> str:
    text = _clean_text(value)
    source_key = str(source or "").strip().lower()
    probe = text.lower()
    if (
        source_key in MARKET_DATA_SOURCES
        or "odaily_exchange_gap" in probe
        or "coinglass" in probe
    ):
        normalized = MARKET_DATA_ATTR_RE.sub("据币界网数据显示，", text, count=1)
        if normalized == text:
            normalized = GATE_DATA_ATTR_RE.sub("据币界网数据显示，", text, count=1)
        text = normalized
    return text


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _row_get(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if hasattr(row, "get"):
        return row.get(key, default)  # type: ignore[attr-defined]
    try:
        return row[key]
    except Exception:
        return default


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


def _adapter_title_content(row: Mapping[str, Any]) -> tuple[str | None, str | None]:
    candidate = _row_to_dict(row)
    if not candidate:
        return None, None
    hermes = _load_json_obj(candidate.get("hermes_result_json"))
    suggestion = parse_hermes_suggestion(hermes.get("suggestion"))
    gate = build_newsflash_draft_payload(
        candidate,
        load_backend_publish_config(),
        suggestion,
    )
    if not isinstance(gate, Mapping) or gate.get("ready_to_publish") is not True:
        return None, None
    draft = gate.get("draft_payload")
    if not isinstance(draft, Mapping):
        return None, None
    title = _first_nonempty(
        draft.get("shortTitle"),
        draft.get("subTitle"),
        draft.get("title"),
    )
    content = _first_nonempty(draft.get("content"))
    return title, content


def _load_json_obj(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        data = json.loads(value)
    except Exception:
        return {}
    return dict(data) if isinstance(data, Mapping) else {}


def _first_nonempty(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_message(row: Mapping[str, Any], config: Mapping[str, Any]) -> str:
    default_category = str(config.get("default_category") or "快讯")
    try:
        adapter_title, adapter_content = _adapter_title_content(row)
    except Exception as e:
        _log(f"[adapter-fallback] tweet_id={_row_get(row, 'tweet_id')} err={e!r}")
        adapter_title, adapter_content = None, None

    title = _clean_text(
        adapter_title
        or _row_get(row, "zh_short_title")
        or _row_get(row, "zh_title")
        or _row_get(row, "title")
        or _row_get(row, "draft")
    )
    body = _clean_body_text(
        adapter_content
        or _row_get(row, "zh_body")
        or _row_get(row, "extracted_text")
        or _row_get(row, "text"),
        _row_get(row, "source"),
    )
    category = _classify_display_category(
        row,
        config,
        title=title,
        body=body,
        default_category=default_category,
    )

    max_title_chars = int(config.get("max_title_chars") or 120)
    max_body_chars = int(config.get("max_body_chars") or 700)
    title = _truncate(title, max_title_chars)

    if not title:
        title = "重要消息"

    lines = [f"<b>{html.escape(f'【{category}】{title}')}</b>"]
    if config.get("include_body", True):
        body = _truncate(body, max_body_chars)
        if body and body != title:
            lines.extend(["", html.escape(body)])
    if config.get("include_time", False):
        published_at = str(
            _row_get(row, "published_at") or _row_get(row, "received_at") or ""
        ).strip()
        if published_at:
            lines.extend(["", html.escape(f"时间：{published_at}")])
    return "\n".join(lines).strip()


def _classify_display_category(
    row: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    title: str,
    body: str,
    default_category: str,
) -> str:
    category = _parse_category(_row_get(row, "hermes_category"), "")
    if category and category != "快讯":
        return category

    source = str(_row_get(row, "source") or "").strip().lower()
    content_type = str(_row_get(row, "content_type") or "").strip()
    text = f"{title} {body} {_row_get(row, 'title') or ''} {_row_get(row, 'zh_title') or ''}".lower()

    if content_type == "prediction_market" or any(k in text for k in ("kalshi", "polymarket", "预测市场", "cftc")):
        return "预测市场"
    if any(k in text for k in ("攻击", "被盗", "漏洞", "冻结", "损失", "exploit", "hack", "安全")):
        return "风险"
    if any(k in text for k in ("链上", "巨鲸", "地址", "钱包", "转账", "提取", "存入", "onchain", "whale")):
        return "链上"
    if any(k in text for k in ("爆仓", "清算", "空单", "多单", "持仓", "资金费率", "未平仓", "合约", "杠杆")):
        return "合约"
    if any(k in text for k in ("突破", "跌破", "上涨", "下跌", "暴涨", "暴跌", "反弹", "回落", "涨幅", "跌幅", "价格", "现报")):
        return "行情"
    if any(k in text for k in ("etf", "sec", "监管", "诉讼", "批准", "调查", "cftc")):
        return "监管"
    if any(k in text for k in ("美联储", "降息", "加息", "利率", "美元", "cpi", "通胀", "国债", "央行")):
        return "宏观"
    if any(k in text for k in ("上线", "下架", "交易对", "充提", "交易所")) or source.endswith("_ann"):
        return "交易所"
    if any(k in text for k in ("融资", "收购", "合作", "推出", "发布", "主网", "测试网")):
        return "项目"
    return default_category or "市场"


def _list_config_values(config: Mapping[str, Any], key: str) -> list[str]:
    raw = config.get(key)
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [str(raw).strip()]


def _trading_filter_skip_reason(row: Mapping[str, Any], config: Mapping[str, Any]) -> str | None:
    if not config.get("trading_filter_enabled", False):
        return None

    categories = set(_parse_categories(_row_get(row, "hermes_category")))
    blocked_categories = set(_list_config_values(config, "trading_block_categories"))
    blocked_hit = sorted(c for c in categories if c in blocked_categories)
    if blocked_hit:
        return f"trading_category_blocked:{','.join(blocked_hit)}"

    content_type = str(_row_get(row, "content_type") or "").strip()
    source = str(_row_get(row, "source") or "").strip()
    blocked_types = set(_list_config_values(config, "trading_block_content_types"))
    if blocked_types and content_type in blocked_types:
        return f"trading_content_type_blocked:{content_type}"

    force_types = set(_list_config_values(config, "trading_force_allow_content_types"))
    force_sources = set(_list_config_values(config, "trading_force_allow_sources"))
    if content_type in force_types or source in force_sources:
        return None

    try:
        adapter_title, adapter_content = _adapter_title_content(row)
    except Exception:
        adapter_title, adapter_content = None, None

    probe = " ".join(
        str(x or "")
        for x in (
            adapter_title,
            adapter_content,
            _row_get(row, "zh_short_title"),
            _row_get(row, "zh_title"),
            _row_get(row, "zh_body"),
            _row_get(row, "title"),
            _row_get(row, "extracted_text"),
            _row_get(row, "text"),
        )
    ).lower()
    keywords = [kw.lower() for kw in _list_config_values(config, "trading_keywords")]
    if any(kw and kw in probe for kw in keywords):
        return None

    return "not_trading_related"


def _should_skip(row: Mapping[str, Any], config: Mapping[str, Any]) -> str | None:
    default_category = str(config.get("default_category") or "快讯")
    category = _parse_category(_row_get(row, "hermes_category"), default_category)
    allowed = set(_list_config_values(config, "allowed_categories"))
    blocked = set(_list_config_values(config, "blocked_categories"))
    blocked_sources = set(_list_config_values(config, "blocked_sources"))
    source = str(_row_get(row, "source") or "").strip()

    if allowed and category not in allowed:
        return f"category_not_allowed:{category}"
    if blocked and category in blocked:
        return f"category_blocked:{category}"
    if blocked_sources and source in blocked_sources:
        return f"source_blocked:{source}"
    trading_skip = _trading_filter_skip_reason(row, config)
    if trading_skip:
        return trading_skip
    return None


def _source_weight_expr(config: Mapping[str, Any]) -> str:
    weights = config.get("source_weights")
    if not isinstance(weights, Mapping) or not weights:
        return "0"
    parts = ["CASE"]
    for source, weight in weights.items():
        try:
            int_weight = int(weight)
        except Exception:
            continue
        escaped = str(source).replace("'", "''")
        parts.append(f"WHEN source = '{escaped}' THEN {int_weight}")
    parts.append("ELSE 0 END")
    return " ".join(parts)


def pick_candidates(config: Mapping[str, Any], state: Mapping[str, Any]) -> list[sqlite3.Row]:
    lookback = max(1, int(config.get("lookback_minutes") or 240))
    max_batch = max(1, int(config.get("max_batch") or 5))
    first_started_at = str(state.get("first_started_at") or "1970-01-01T00:00:00+00:00")
    source_weight = _source_weight_expr(config)

    with get_conn() as conn:
        return conn.execute(
            f"""
            SELECT t.*
            FROM tweets t
            WHERE (t.backend_upload_status = 'published' OR t.pipeline_stage = 'published')
              AND t.received_at IS NOT NULL
              AND datetime(t.received_at) >= datetime(?)
              AND datetime(t.received_at) >= datetime('now', ?)
              AND NOT EXISTS (
                  SELECT 1 FROM telegram_publications p
                  WHERE p.tweet_id = t.tweet_id
                    AND p.status IN ('sent', 'skipped', 'pending')
              )
            ORDER BY {source_weight} DESC,
                     datetime(COALESCE(NULLIF(t.published_at_backend, ''), t.received_at)) ASC,
                     t.rowid ASC
            LIMIT ?
            """,
            (first_started_at, f"-{lookback} minutes", max_batch),
        ).fetchall()


def send_telegram_message(
    *,
    bot_token: str,
    chat_id: str,
    text: str,
    disable_web_page_preview: bool = True,
) -> int:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true" if disable_web_page_preview else "false",
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"telegram_http_{e.code}:{raw[:500]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"telegram_request_failed:{e}") from e

    if not payload.get("ok"):
        raise RuntimeError(f"telegram_not_ok:{payload}")
    result = payload.get("result") or {}
    message_id = result.get("message_id")
    return int(message_id) if message_id is not None else 0


def record_publication(
    *,
    tweet_id: str,
    chat_id: str,
    status: str,
    message_text: str,
    telegram_message_id: int | None = None,
    last_error: str | None = None,
) -> None:
    now = _now_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO telegram_publications (
                tweet_id, chat_id, status, telegram_message_id, retry_count,
                last_error, message_text, created_at, updated_at, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tweet_id, chat_id) DO UPDATE SET
                status = excluded.status,
                telegram_message_id = excluded.telegram_message_id,
                retry_count = telegram_publications.retry_count + CASE
                    WHEN excluded.status = 'failed' THEN 1 ELSE 0 END,
                last_error = excluded.last_error,
                message_text = excluded.message_text,
                updated_at = excluded.updated_at,
                sent_at = excluded.sent_at
            """,
            (
                tweet_id,
                chat_id,
                status,
                telegram_message_id,
                1 if status == "failed" else 0,
                last_error,
                message_text,
                now,
                now,
                now if status == "sent" else None,
            ),
        )
        conn.commit()


def run_once(
    *,
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    bot_token: str,
    dry_run: bool = False,
) -> dict[str, int]:
    stats = {"picked": 0, "sent": 0, "skipped": 0, "failed": 0}
    chat_ids = _list_config_values(config, "chat_ids")
    if not chat_ids:
        _log("[publisher] no chat_ids configured")
        return stats

    rows = pick_candidates(config, state)
    stats["picked"] = len(rows)
    for row in rows:
        tweet_id = str(row["tweet_id"])
        skip_reason = _should_skip(row, config)
        message = build_message(row, config)

        if skip_reason:
            for chat_id in chat_ids:
                record_publication(
                    tweet_id=tweet_id,
                    chat_id=chat_id,
                    status="skipped",
                    message_text=message,
                    last_error=skip_reason,
                )
            stats["skipped"] += 1
            _log(f"[skip] {tweet_id} {skip_reason}")
            continue

        for chat_id in chat_ids:
            if dry_run:
                _log(f"[dry-run] chat={chat_id} tweet_id={tweet_id}\n{message}")
                stats["skipped"] += 1
                continue
            try:
                message_id = send_telegram_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    text=message,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                err = str(e)
                record_publication(
                    tweet_id=tweet_id,
                    chat_id=chat_id,
                    status="failed",
                    message_text=message,
                    last_error=err[:1000],
                )
                stats["failed"] += 1
                _log(f"[failed] chat={chat_id} tweet_id={tweet_id} err={err[:300]}")
                continue

            record_publication(
                tweet_id=tweet_id,
                chat_id=chat_id,
                status="sent",
                message_text=message,
                telegram_message_id=message_id,
            )
            stats["sent"] += 1
            _log(f"[sent] chat={chat_id} tweet_id={tweet_id} message_id={message_id}")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.getenv("TELEGRAM_PUBLISH_CONFIG_PATH"))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    enabled = (os.getenv("TELEGRAM_PUBLISH_ENABLED") or "false").strip().lower()
    if enabled not in ("1", "true", "yes", "on") and not args.dry_run:
        _log("[publisher] disabled by TELEGRAM_PUBLISH_ENABLED")
        return 0

    config = load_config(args.config)
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not bot_token and not args.dry_run:
        _log("[publisher] missing TELEGRAM_BOT_TOKEN")
        return 2

    ensure_outbox()
    state_path = DEFAULT_STATE_PATH
    state = _load_state(
        state_path,
        start_from_now=bool(config.get("start_from_now", True)),
    )

    poll_seconds = max(3, int(config.get("poll_seconds") or 10))
    while True:
        stats = run_once(
            config=config,
            state=state,
            bot_token=bot_token,
            dry_run=bool(args.dry_run),
        )
        if stats["picked"] or stats["failed"]:
            _log(f"[stats] {stats}")
        if args.once:
            return 0 if stats["failed"] == 0 else 1
        time.sleep(poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
