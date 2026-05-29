import argparse
import os
from datetime import timedelta
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        ETHERSCAN_V2_URL,
        address_key,
        dt_to_utc_iso,
        estimate_usd,
        json_dumps,
        load_symbol_map,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        redact_secret,
        request_json,
        safe_float,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        ETHERSCAN_V2_URL,
        address_key,
        dt_to_utc_iso,
        estimate_usd,
        json_dumps,
        load_symbol_map,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        redact_secret,
        request_json,
        safe_float,
        token_amount,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )


ROOT = Path(__file__).resolve().parents[1]
AAVE_V3_ETH_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
LIQUIDATION_CALL_TOPIC0 = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
SECONDS_PER_ETH_BLOCK = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch Aave V3 Ethereum LiquidationCall events.")
    parser.add_argument("--market-map", default=str(ROOT / "data" / "liquidation_market_map.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_lending_liquidations.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_lending_liquidation_watcher_summary.csv"))
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--min-usd", type=float, default=1_000_000)
    parser.add_argument("--max-logs", type=int, default=100)
    parser.add_argument("--chain-id", default="1")
    parser.add_argument("--pool-address", default=AAVE_V3_ETH_POOL)
    parser.add_argument("--api-key-env", default="ETHERSCAN_API_KEY")
    parser.add_argument("--sample-if-no-key", default="true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_market_map(path: Path) -> dict[str, dict]:
    rows = read_csv_rows(path)
    output = {}
    for row in rows:
        if str(row.get("enabled", "")).strip().lower() not in {"1", "true", "yes", "y"}:
            continue
        token = address_key(row.get("token_address"))
        if token:
            output[token] = row
    return output


def current_block(api_key: str, chain_id: str) -> int:
    payload = request_json(
        ETHERSCAN_V2_URL,
        params={
            "chainid": chain_id,
            "module": "proxy",
            "action": "eth_blockNumber",
            "apikey": api_key,
        },
    )
    if not isinstance(payload, dict) or not payload.get("result"):
        raise RuntimeError(f"unexpected current block response: {payload}")
    return int(str(payload["result"]), 16)


def get_logs(api_key: str, chain_id: str, pool_address: str, from_block: int, to_block: int) -> list[dict]:
    payload = request_json(
        ETHERSCAN_V2_URL,
        params={
            "chainid": chain_id,
            "module": "logs",
            "action": "getLogs",
            "fromBlock": from_block,
            "toBlock": to_block,
            "address": pool_address,
            "topic0": LIQUIDATION_CALL_TOPIC0,
            "apikey": api_key,
        },
        timeout=20,
        retries=3,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("unexpected Etherscan logs response")
    result = payload.get("result", [])
    message = str(payload.get("message", ""))
    status = str(payload.get("status", ""))
    if status == "0" and isinstance(result, str):
        if "No records found" in result or "No transactions found" in result:
            return []
        raise RuntimeError(f"Etherscan logs error: {message}; {result}")
    if not isinstance(result, list):
        raise RuntimeError(f"unexpected Etherscan logs result: {result}")
    return result


def topic_to_address(topic: str) -> str:
    raw = str(topic or "").strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) < 40:
        return ""
    return "0x" + raw[-40:]


def split_words(data: str) -> list[str]:
    raw = str(data or "").strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    return [raw[index : index + 64] for index in range(0, len(raw), 64) if len(raw[index : index + 64]) == 64]


def word_to_int(word: str) -> int:
    try:
        return int(str(word or "0"), 16)
    except Exception:
        return 0


def word_to_address(word: str) -> str:
    raw = str(word or "")
    if len(raw) < 40:
        return ""
    return "0x" + raw[-40:]


def display_symbol(row: dict | None) -> str:
    if not row:
        return ""
    symbol = str(row.get("price_symbol") or row.get("asset_symbol") or "").strip().upper()
    if symbol == "WETH":
        return "ETH"
    if symbol == "WBTC":
        return "BTC"
    return symbol


def sample_alerts() -> list[dict]:
    observed = dt_to_utc_iso(now_utc())
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("sample_aave_v3_liquidation", observed),
            "observed_at_utc": observed,
            "observed_at_china": utc_iso_to_china(observed),
            "source_type": "first_hand",
            "watcher_source": "etherscan_v2_aave_v3_liquidations",
            "blockchain": "ethereum",
            "block_number": "sample",
            "tx_hash": "sample_tx_aave_v3_liquidation",
            "log_index": "0",
            "primary_entity": "Aave V3",
            "primary_address": AAVE_V3_ETH_POOL,
            "counterparty_entity": "liquidated_user",
            "counterparty_address": "sample_user",
            "asset_symbol": "ETH",
            "token_address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "amount_native": "2500000",
            "amount_usd": "2500000.00",
            "metric_type": "lending_liquidation",
            "metric_value": "2500000.00",
            "metric_change_pct": "",
            "event_type_l1": "liquidation",
            "event_type_l2": "aave_v3_liquidation",
            "risk_category": "lending_liquidation",
            "confidence": "sample",
            "relevance_score": "0.78",
            "threshold_rule": "sample_debt_covered_usd>=1000000",
            "dedupe_key": make_dedupe_key("sample_aave_v3_liquidation", observed[:13]),
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "sample",
            "raw_json": json_dumps({"sample": True}),
        }
    )
    return [alert]


def build_alert(log: dict, market_map: dict[str, dict], symbol_map: dict[str, dict], min_usd: float) -> tuple[dict | None, str]:
    topics = log.get("topics", [])
    if not isinstance(topics, list) or len(topics) < 4:
        return None, "bad_topics"
    collateral_address = address_key(topic_to_address(topics[1]))
    debt_address = address_key(topic_to_address(topics[2]))
    user_address = topic_to_address(topics[3])
    collateral = market_map.get(collateral_address)
    debt = market_map.get(debt_address)
    if not debt:
        return None, "unknown_debt_asset"
    words = split_words(str(log.get("data", "")))
    if len(words) < 4:
        return None, "bad_data"

    debt_symbol = display_symbol(debt)
    collateral_symbol = display_symbol(collateral) or debt_symbol
    debt_raw = word_to_int(words[0])
    collateral_raw = word_to_int(words[1])
    liquidator = word_to_address(words[2])
    debt_amount = token_amount(str(debt_raw), debt.get("decimals", "18"))
    collateral_amount = token_amount(str(collateral_raw), collateral.get("decimals", "18") if collateral else "18")
    amount_usd, price = estimate_usd(debt_symbol, debt_amount, symbol_map)
    if amount_usd <= 0 and debt_symbol in {"USDT", "USDC", "DAI"}:
        amount_usd = debt_amount
        price = 1.0
    if amount_usd < min_usd:
        return None, "below_threshold"

    block_number = str(log.get("blockNumber", ""))
    tx_hash = str(log.get("transactionHash") or log.get("transactionHash".lower()) or "")
    log_index = str(log.get("logIndex", ""))
    observed = dt_to_utc_iso(now_utc())
    amount_native_display = collateral_amount if collateral_symbol not in {"USDT", "USDC", "DAI"} else debt_amount
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("aave_v3_liquidation", tx_hash, log_index, debt_symbol, collateral_symbol),
            "observed_at_utc": observed,
            "observed_at_china": utc_iso_to_china(observed),
            "source_type": "first_hand",
            "watcher_source": "etherscan_v2_aave_v3_liquidations",
            "blockchain": "ethereum",
            "block_number": block_number,
            "tx_hash": tx_hash,
            "log_index": log_index,
            "primary_entity": "Aave V3",
            "primary_address": AAVE_V3_ETH_POOL,
            "counterparty_entity": "liquidated_user",
            "counterparty_address": user_address,
            "asset_symbol": collateral_symbol,
            "token_address": collateral_address,
            "amount_native": f"{amount_native_display:.12g}",
            "amount_usd": f"{amount_usd:.2f}",
            "metric_type": "lending_liquidation",
            "metric_value": f"{amount_usd:.2f}",
            "metric_change_pct": "",
            "event_type_l1": "liquidation",
            "event_type_l2": "aave_v3_liquidation",
            "risk_category": "lending_liquidation",
            "confidence": "medium",
            "relevance_score": "0.90" if amount_usd >= 5_000_000 else "0.78",
            "threshold_rule": f"debt_covered_usd>={min_usd:.0f};debt_asset={debt_symbol};collateral_asset={collateral_symbol};debt_amount={debt_amount:.12g};collateral_amount={collateral_amount:.12g};price={price:.8g};liquidator={liquidator}",
            "dedupe_key": make_dedupe_key("aave_v3_liquidation", tx_hash, log_index),
            "needs_model_review": "true" if amount_usd >= 5_000_000 else "false",
            "model_review_reason": "large_lending_liquidation" if amount_usd >= 5_000_000 else "",
            "publish_route": "review",
            "status": "ok",
            "raw_json": json_dumps(log),
        }
    )
    return alert, ""


def main() -> int:
    args = parse_args()
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    api_key = os.environ.get(args.api_key_env, "").strip()

    if not api_key and truthy(args.sample_if_no_key):
        rows = sample_alerts()
        write_csv_rows(output_path, rows, ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "lending_liquidations",
                "mode": "sample_no_api_key",
                "raw_log_rows": 0,
                "alert_rows": len(rows),
                "status": "sample",
            },
        )
        print(f"{args.api_key_env} missing; wrote sample lending liquidation alerts to {output_path}")
        return 0

    if not api_key:
        write_csv_rows(output_path, [], ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "lending_liquidations",
                "mode": "live",
                "raw_log_rows": 0,
                "alert_rows": 0,
                "status": "missing_api_key",
            },
        )
        print(f"{args.api_key_env} missing; no live lending liquidation request sent")
        return 0

    market_map = load_market_map(normalize_path(args.market_map))
    symbol_map = load_symbol_map(normalize_path(args.symbol_map))
    skipped: dict[str, int] = {}
    alerts = []
    raw_logs = []
    request_failed = ""
    from_block = 0
    to_block = 0

    try:
        to_block = current_block(api_key, args.chain_id)
        block_span = int((args.hours * 3600) / SECONDS_PER_ETH_BLOCK) + 50
        from_block = max(0, to_block - block_span)
        raw_logs = get_logs(api_key, args.chain_id, args.pool_address, from_block, to_block)
    except Exception as exc:
        request_failed = redact_secret(exc)
        print(f"request_failed={request_failed}")

    for log in raw_logs[: args.max_logs]:
        alert, reason = build_alert(log, market_map, symbol_map, args.min_usd)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        if alert:
            alerts.append(alert)

    write_csv_rows(output_path, alerts, ALERT_COLUMNS)
    top_skip = max(skipped, key=skipped.get) if skipped else ""
    write_summary(
        summary_path,
        {
            "watcher": "lending_liquidations",
            "mode": "live",
            "chain_id": args.chain_id,
            "pool_address": args.pool_address,
            "from_block": from_block,
            "to_block": to_block,
            "hours": args.hours,
            "raw_log_rows": len(raw_logs),
            "alert_rows": len(alerts),
            "skipped_rows": sum(skipped.values()),
            "top_skip_reason": top_skip,
            "top_skip_count": skipped.get(top_skip, 0) if top_skip else 0,
            "request_failed": request_failed,
            "min_usd": args.min_usd,
            "status": "pass" if not request_failed else "request_failed",
        },
    )
    print(f"lending_liquidation_alert_rows={len(alerts)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
