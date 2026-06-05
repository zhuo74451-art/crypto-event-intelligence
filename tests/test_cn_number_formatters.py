"""Chinese number formatter regression tests. No abs() on PnL."""
import sys, re

def usd_abs(v):
    a = abs(v)
    if a >= 100_000_000: return f"{a/100_000_000:.2f}亿美元"
    if a >= 10_000_000: return f"{a/10_000:.0f}万美元"
    if a >= 1_000_000: return f"{a/10_000:.1f}万美元"
    return f"{a:.0f}美元"

def usd_signed(v):
    a = abs(v); s = "+" if v > 0 else "-" if v < 0 else ""
    if a >= 100_000_000: return f"{s}{a/100_000_000:.2f}亿美元"
    if a >= 10_000_000: return f"{s}{a/10_000:.0f}万美元"
    if a >= 1_000_000: return f"{s}{a/10_000:.1f}万美元"
    return f"{s}{a:.0f}美元"

def test():
    cases = [
        ("usd_abs position", usd_abs(52140000), "5214万美元"),
        ("usd_signed neg PnL", usd_signed(-19650759), "-1965万美元"),
        ("usd_signed pos PnL", usd_signed(47414726) == "+4741万美元" or usd_signed(47414726).startswith("+"), True),
        ("usd_abs no neg sign", "-" not in usd_abs(-19650759), True),
        ("no $ symbol", "$" not in usd_abs(52140000), True),
        ("no M symbol", "M" not in usd_abs(1000000), True),
        ("no K symbol", "K" not in usd_abs(1000), True),
    ]
    passed = 0; failed = 0
    for name, actual, expected in cases:
        ok = actual == expected
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else: failed += 1
        print(f"  [{status}] {name}: got={actual if not isinstance(actual, bool) else ''}")

    # Critical: PnL must NOT lose sign
    pnl_check = usd_signed(-19650759)
    ok = "-" in pnl_check
    print(f"  [{'PASS' if ok else 'FAIL'}] PnL retains negative sign")
    if ok: passed += 1
    else: failed += 1
    print(f"\nResults: {passed}/{len(cases)} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    ok = test()
    sys.exit(0 if ok else 1)
