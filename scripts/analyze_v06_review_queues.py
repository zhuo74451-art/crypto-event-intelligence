import argparse
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

TOKEN_RE = re.compile(r"\$?[A-Z][A-Z0-9]{1,10}\b")
HANDLE_RE = re.compile(r"@[A-Za-z0-9_]{2,32}")

NOISE_TOKENS = {
    "JUST",
    "NEW",
    "IN",
    "THE",
    "AND",
    "FOR",
    "WITH",
    "FROM",
    "THIS",
    "THAT",
    "USD",
    "USDT",
    "USDC",
    "HTTP",
    "HTTPS",
    "AI",
    "CEO",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
}

KNOWN_SYMBOLS = {
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "XRP",
    "DOGE",
    "ADA",
    "LINK",
    "AVAX",
    "HYPE",
    "WLD",
    "ONDO",
    "TON",
    "ZEC",
    "TRX",
    "BCH",
    "XMR",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze v0.6 review queues for recurring rule improvements.")
    parser.add_argument(
        "--scored",
        default=str(ROOT / "data" / "event_candidates_v06_relevance_scored.csv"),
    )
    parser.add_argument(
        "--publish-review",
        default=str(ROOT / "data" / "event_candidates_v06_publish_review_queue.csv"),
    )
    parser.add_argument(
        "--other-review",
        default=str(ROOT / "data" / "event_candidates_v06_other_review_queue.csv"),
    )
    parser.add_argument(
        "--discard-audit",
        default=str(ROOT / "data" / "event_candidates_v06_discard_audit_sample.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "v062_review_queue_rule_suggestions.md"),
    )
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype=str).fillna("")


def extract_tokens(text: str) -> list[str]:
    tokens = []
    for raw in TOKEN_RE.findall(text):
        token = raw.upper().lstrip("$")
        if token not in NOISE_TOKENS and len(token) >= 2:
            tokens.append(token)
    return tokens


def extract_handles(text: str) -> list[str]:
    return [handle.lower() for handle in HANDLE_RE.findall(text)]


def top_counter(counter: Counter, n: int = 30) -> list[tuple[str, int]]:
    return [(key, count) for key, count in counter.most_common(n) if count > 1]


def markdown_table(rows: list[dict] | pd.DataFrame, columns: list[str], max_rows: int = 30) -> str:
    if isinstance(rows, pd.DataFrame):
        df = rows.head(max_rows)
        records = df.to_dict("records")
    else:
        records = rows[:max_rows]
    if not records:
        return "_No rows._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in records:
        cells = []
        for col in columns:
            value = row.get(col, "")
            cells.append(str(value).replace("\n", " ")[:160])
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def counter_table(counter: Counter, columns: tuple[str, str], n: int = 30) -> str:
    rows = [{columns[0]: key, columns[1]: count} for key, count in top_counter(counter, n)]
    return markdown_table(rows, [columns[0], columns[1]], n)


def likely_false_positive_publish(df: pd.DataFrame) -> pd.DataFrame:
    title = df.get("title", pd.Series("", index=df.index)).astype(str)
    reasons = []
    masks = []

    masks.append(title.str.contains(r"GPT|Gemini|OpenAI|Cursor|Meta|AI云|Colossus|SWE-Bench", case=False, regex=True))
    reasons.append("ai_or_non_crypto_tech")

    masks.append(title.str.contains(r"突破|跌幅|涨幅|price slips|price drops|price rises|24H", case=False, regex=True))
    reasons.append("pure_price_recap")

    masks.append(title.str.contains(r"夜盘主力|原油|REITs|总统|伊朗|乌克兰|战争|wildfire|football", case=False, regex=True))
    reasons.append("macro_or_non_crypto_noise")

    output = []
    for mask, reason in zip(masks, reasons):
        part = df[mask].copy()
        if part.empty:
            continue
        part["suspected_issue"] = reason
        output.append(part)
    if not output:
        return pd.DataFrame()
    result = pd.concat(output).drop_duplicates(subset=["candidate_id"])
    return result.sort_values("relevance_score_realtime", ascending=False)


def possible_missed_crypto(df: pd.DataFrame) -> pd.DataFrame:
    title = df.get("title", pd.Series("", index=df.index)).astype(str)
    mask = title.str.contains(
        r"crypto|blockchain|token|wallet|exchange|Revolut|Polygon|Machi|Hyperliquid|PhoenixTrade|链上|加密|钱包|交易所|代币",
        case=False,
        regex=True,
    )
    return df[mask].copy()


def build_report(scored: pd.DataFrame, publish: pd.DataFrame, other: pd.DataFrame, discard: pd.DataFrame) -> str:
    token_counter = Counter()
    handle_counter = Counter()
    for _, row in pd.concat([other, discard]).iterrows():
        text = f"{row.get('title', '')} {row.get('content', '')}"
        token_counter.update(extract_tokens(text))
        handle_counter.update(extract_handles(text))

    unknown_tokens = Counter({k: v for k, v in token_counter.items() if k not in KNOWN_SYMBOLS})
    publish_fp = likely_false_positive_publish(publish)
    missed_other = possible_missed_crypto(other)
    missed_discard = possible_missed_crypto(discard)

    lines = [
        "# v0.6.2 Review Queue Rule Suggestions",
        "",
        "This report suggests rule/dictionary improvements. It does not change publishing decisions by itself.",
        "",
        "## Queue Sizes",
        f"- scored rows: {len(scored)}",
        f"- publish review rows: {len(publish)}",
        f"- other review rows: {len(other)}",
        f"- discard audit rows: {len(discard)}",
        "",
        "## Suspected False Positives In Publish Review",
        markdown_table(
            publish_fp,
            ["candidate_id", "title", "primary_asset_symbol", "event_type_l1", "publish_decision", "relevance_score_realtime", "suspected_issue"],
            40,
        ),
        "",
        "## Possible Missed Crypto Rows In Other Review",
        markdown_table(
            missed_other,
            ["candidate_id", "title", "detected_entity_names", "discard_reason"],
            40,
        ),
        "",
        "## Possible Missed Crypto Rows In Discard Audit",
        markdown_table(
            missed_discard,
            ["candidate_id", "title", "detected_entity_names", "discard_reason"],
            40,
        ),
        "",
        "## Recurring Unknown Ticker-Like Tokens",
        counter_table(unknown_tokens, ("token", "count"), 40),
        "",
        "## Recurring Handles",
        counter_table(handle_counter, ("handle", "count"), 40),
        "",
        "## Suggested Next Edits",
        "- Add recurring project tokens only after manual confirmation that they are relevant assets, not webpage footer noise.",
        "- Add deny rules for AI-only / non-crypto tech news that only mention crypto in scraped footer text.",
        "- Add a pure price recap deny rule for rows that only report price movement without a new catalyst.",
        "- Add specific L1/L2 rules for crypto payment/card stories if the product wants payment adoption events.",
        "- Review `Machi`, `Hyperliquid`, `PhoenixTrade`, `Polygon`, `Revolut` rows manually before changing rules.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    scored = read_csv(normalize_path(args.scored))
    publish = read_csv(normalize_path(args.publish_review))
    other = read_csv(normalize_path(args.other_review))
    discard = read_csv(normalize_path(args.discard_audit))
    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_report(scored, publish, other, discard), encoding="utf-8")
    logging.info("wrote rule suggestion report to %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
