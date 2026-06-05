"""Market Radar TG Formatting v1.10-A R2 — 卡片产品化格式化工具。

提供：
- humanize_number / humanize_money / humanize_percent / humanize_token_amount
- safe_value（None / nan / inf → "--"）
- mask_address（0x082d...ca88 脱敏）
- normalize_symbol（统一大写）
- escape_markdown_v2（Telegram MarkdownV2 特殊字符转义）
- build_public_links / render_source_links
"""

from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import urlparse


# ── 安全值处理 ──────────────────────────────────────────────────────────────

def safe_value(value: Any, fallback: str = "--") -> str:
    """将 None / nan / inf 转换为安全字符串，避免进入卡片。"""
    if value is None:
        return fallback
    if isinstance(value, float):
        if math.isnan(value):
            return fallback
        if math.isinf(value):
            return fallback
    if isinstance(value, str) and value.strip() == "":
        return fallback
    # Only Python None, float nan/inf are converted. String values like "none" are kept.
    return str(value)
    return str(value)


# ── 数字人性化 ──────────────────────────────────────────────────────────────

def humanize_number(value: Any, decimals: int = 2) -> str:
    """人性化大数字：1000000 → 1.00M。"""
    v = _to_float(value)
    if v is None:
        return "--"
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    if abs_v >= 1_000_000_000:
        return f"{sign}{abs_v / 1_000_000_000:.{decimals}f}B"
    if abs_v >= 1_000_000:
        return f"{sign}{abs_v / 1_000_000:.{decimals}f}M"
    if abs_v >= 1_000:
        return f"{sign}{abs_v / 1_000:.{decimals}f}K"
    return f"{sign}{abs_v:.{decimals}f}"


def humanize_money(value: Any) -> str:
    """人性化金额：45000000 → $45.00M。"""
    v = _to_float(value)
    if v is None:
        return "--"
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    if abs_v >= 1_000_000_000:
        return f"{sign}${abs_v / 1_000_000_000:.2f}B"
    if abs_v >= 1_000_000:
        return f"{sign}${abs_v / 1_000_000:.2f}M"
    if abs_v >= 1_000:
        return f"{sign}${abs_v / 1_000:.2f}K"
    return f"{sign}${abs_v:.2f}"


def humanize_percent(value: Any) -> str:
    """人性化百分比：12.5 → +12.50%。"""
    v = _to_float(value)
    if v is None:
        return "--"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def humanize_token_amount(value: Any, symbol: str = "") -> str:
    """人性化代币数量：1380000 → 1.38M HYPE。"""
    v = _to_float(value)
    if v is None:
        return "--"
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    suffix = f" {symbol.upper()}" if symbol else ""
    if abs_v >= 1_000_000_000:
        return f"{sign}{abs_v / 1_000_000_000:.2f}B{suffix}"
    if abs_v >= 1_000_000:
        return f"{sign}{abs_v / 1_000_000:.2f}M{suffix}"
    if abs_v >= 1_000:
        return f"{sign}{abs_v / 1_000:.2f}K{suffix}"
    if abs_v >= 1:
        return f"{sign}{abs_v:.4f}{suffix}"
    return f"{sign}{abs_v:.8f}{suffix}"


# ── 地址脱敏 ────────────────────────────────────────────────────────────────

def mask_address(address: Any) -> str:
    """脱敏地址：显示前 6 位 + ... + 后 4 位 → 0x082d...8e9f。"""
    if address is None:
        return "--"
    addr = str(address).strip()
    if not addr or len(addr) <= 12:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


# ── 符号规范化 ──────────────────────────────────────────────────────────────

def normalize_symbol(symbol: Any) -> str:
    """统一符号为大写，去除空白。"""
    return str(symbol or "").strip().upper()


# ── MarkdownV2 转义 ─────────────────────────────────────────────────────────

# Telegram MarkdownV2 需要转义的特殊字符
_MDV2_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"

def escape_markdown_v2(text: str) -> str:
    """对 Telegram MarkdownV2 特殊字符进行转义。

    不转义已经转义的字符（避免双重转义）。
    规则：在特殊字符前加反斜杠。
    """
    if not text:
        return text
    # 用正则替换所有需要转义的字符
    # 注意：只转义前面没有反斜杠的字符
    result = []
    for ch in text:
        if ch in _MDV2_ESCAPE_CHARS:
            result.append("\\" + ch)
        else:
            result.append(ch)
    return "".join(result)


# ── 公开外链 ─────────────────────────────────────────────────────────────────

# 常见币种的公开行情链接
_PUBLIC_LINK_TEMPLATES = {
    "coingecko": "https://www.coingecko.com/en/coins/{slug}",
    "dexscreener": "https://dexscreener.com/search?q={symbol}",
    "coinmarketcap": "https://coinmarketcap.com/currencies/{slug}/",
}

# 常见币种的 CoinGecko slug
_COINGECKO_SLUGS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "HYPE": "hyperliquid", "ARB": "arbitrum", "SUI": "sui",
    "XRP": "ripple", "DOGE": "dogecoin", "AVAX": "avalanche-2",
    "DOT": "polkadot", "LINK": "chainlink", "UNI": "uniswap",
    "MATIC": "matic-network", "POL": "polygon-ecosystem-token",
}


def build_public_links(asset: str) -> list[dict]:
    """根据资产符号构建公开行情链接列表。

    返回 list of {label, url}。
    """
    symbol = normalize_symbol(asset)
    slug = _COINGECKO_SLUGS.get(symbol, symbol.lower())
    links = [
        {"label": "CoinGecko", "url": f"https://www.coingecko.com/en/coins/{slug}"},
        {"label": "DexScreener", "url": f"https://dexscreener.com/search?q={symbol}"},
    ]
    return links


def render_source_links(source_url: str = "", asset: str = "", source_name: str = "") -> list[str]:
    """渲染来源链接行（含公开行情外链）。

    返回链接文本行列表，可直接插入卡片。
    """
    lines: list[str] = []

    # 公开行情链接
    if asset:
        pub_links = build_public_links(asset)
        link_parts = []
        for pl in pub_links:
            link_parts.append(f"[{pl['label']}]({pl['url']})")
        if link_parts:
            lines.append(f"🔗 行情查看：{' / '.join(link_parts)}")

    # 原始来源链接
    if source_url:
        domain = _extract_domain(source_url)
        lines.append(f"📎 原始来源：[{domain}]({source_url})")

    return lines


# ── TG 安全渲染（MarkdownV2 异常自动降级为纯文本）───────────────────────────

def render_tg_safe_text(text: str, prefer_markdown: bool = True) -> dict:
    """安全渲染 TG 文本，MarkdownV2 异常时自动降级为纯文本。

    返回格式：
    {
        "text": "...",
        "parse_mode": "MarkdownV2" 或 None,
        "fallback_used": True/False,
        "warnings": [...]
    }

    策略：
    1. 正常情况下返回 parse_mode="MarkdownV2"，text 已转义
    2. 遇到转义/格式化异常时返回 parse_mode=None，text 为纯文本
    3. fallback 文本不得包含 traceback / HTTPError / KeyError
    4. 不允许因为 MarkdownV2 异常导致整张卡片丢失
    """
    warnings: list[str] = []

    if not prefer_markdown:
        # 调用方明确要求纯文本，直接返回
        return {
            "text": text,
            "parse_mode": None,
            "fallback_used": False,
            "warnings": ["parse_mode explicitly set to plain text"],
        }

    # 尝试 MarkdownV2 转义
    try:
        escaped = escape_markdown_v2(text)
        # 二次确认：转义后的文本不能包含异常信息
        if _contains_exception_markers(escaped):
            raise ValueError("escaped text contains exception markers")

        # 正常路径
        return {
            "text": escaped,
            "parse_mode": "MarkdownV2",
            "fallback_used": False,
            "warnings": warnings,
        }
    except Exception as exc:
        # MarkdownV2 转义异常 → 纯文本兜底
        error_msg = str(exc)
        # 截断异常信息，避免泄露内部细节
        short_err = error_msg[:100] + ("..." if len(error_msg) > 100 else "")
        warnings.append(f"MarkdownV2 escape failed: {short_err}")

        # 清理文本中的异常信息
        clean_text = _strip_exception_text(text)

        return {
            "text": clean_text,
            "parse_mode": None,
            "fallback_used": True,
            "warnings": warnings,
        }


def _contains_exception_markers(text: str) -> bool:
    """检查文本是否包含异常/错误标记。"""
    markers = [
        "traceback", "Traceback",
        "HTTPError", "http_error",
        "KeyError", "key_error",
        "TypeError", "ValueError",
        "Exception", "exception",
    ]
    text_lower = text.lower()
    return any(m.lower() in text_lower for m in markers)


def _strip_exception_text(text: str) -> str:
    """清理文本中的异常/错误信息，保留纯文本内容。"""
    import re

    # 移除 traceback 行（以 "  File " 或 "Traceback" 开头的行）
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # 跳过 traceback 栈帧行
        if stripped.startswith("File ") or stripped.startswith("Traceback"):
            clean_lines.append("[内容已清洗]")
            continue
        # 跳过纯异常类型行
        if re.match(r'^[A-Z][a-zA-Z]*(Error|Exception)', stripped):
            clean_lines.append("[内容已清洗]")
            continue
        # 跳过异常消息中包含技术路径的行
        if any(marker in stripped for marker in [
            "site-packages", "__pycache__", ".py\"", ".py'",
        ]):
            clean_lines.append("[内容已清洗]")
            continue
        clean_lines.append(line)

    result = "\n".join(clean_lines)
    # 如果清洗后文本为空，返回兜底内容
    if not result.strip():
        result = "[系统提示：卡片内容生成异常，已降级为纯文本占位]"

    return result


# ── 内部工具 ─────────────────────────────────────────────────────────────────

def _to_float(value: Any) -> float | None:
    """安全转换为 float，None / nan / inf 返回 None。0 是有效值。"""
    if value is None:
        return None
    try:
        v = float(str(value).strip())
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def _extract_domain(url: str) -> str:
    """从 URL 提取域名/产品名标签。"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if "hyperliquid" in hostname:
            return "Hyperliquid"
        if "etherscan" in hostname:
            return "Etherscan"
        if "coindesk" in hostname:
            return "CoinDesk"
        if "cointelegraph" in hostname:
            return "CoinTelegraph"
        if "coingecko" in hostname:
            return "CoinGecko"
        if "dexscreener" in hostname:
            return "DexScreener"
        return hostname.split(".")[-2] if hostname.count(".") >= 1 else hostname
    except Exception:
        return "来源"
