#!/usr/bin/env python3
"""Static scan: verify adapter code contains no prohibited trading/private capability."""
import ast, os, sys

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                    "market_radar", "external_adapters")

PROHIBITED_PATTERNS = [
    "create_order", "cancel_order", "cancel_all_orders", "fetch_my_trades",
    "fetch_order", "fetch_open_orders", "fetch_closed_orders", "fetch_balance",
    "withdraw", "transfer", "set_leverage", "set_margin_mode",
    "apiKey", "api_key", "apiSecret", "api_secret", "private_key",
    "sign(", "sign_payload", "sign_message",
    "wallet", "Exchange(", "exchange_class", "TradingClient",
]

def scan_file(path):
    violations = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for pattern in PROHIBITED_PATTERNS:
        if pattern in content:
            violations.append(pattern)
    return violations

def main():
    total_violations = 0
    for root, dirs, files in os.walk(BASE):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            violations = scan_file(fpath)
            if violations:
                print(f"[FAIL] {os.path.relpath(fpath, BASE)}: {violations}")
                total_violations += len(violations)
    if total_violations == 0:
        print("[PASS] No prohibited trading/private capabilities found")
        return 0
    else:
        print(f"[FAIL] {total_violations} prohibited pattern(s) found")
        return 1

if __name__ == "__main__":
    sys.exit(main())
