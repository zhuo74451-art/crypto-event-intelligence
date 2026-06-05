"""PnL consistency regression tests for static position cards."""
import sys

def validate(side, entry, mark, pnl):
    """Returns (passes, reason)."""
    if side == "多单":
        if mark > entry and pnl < 0:
            return False, "pnl_sign_conflict: long profit expected but pnl negative"
        if mark < entry and pnl > 0:
            return False, "pnl_sign_conflict: long loss expected but pnl positive"
    elif side == "空单":
        if mark > entry and pnl > 0:
            return False, "pnl_sign_conflict: short loss expected but pnl positive"
        if mark < entry and pnl < 0:
            return False, "pnl_sign_conflict: short profit expected but pnl negative"
    return True, "ok"

def test_cases():
    cases = [
        ("多单盈利", "多单", 10, 12, 100, True),
        ("多单亏损", "多单", 10, 8, -100, True),
        ("空单盈利", "空单", 10, 8, 100, True),
        ("空单亏损", "空单", 10, 12, -100, True),
        ("空单涨但pnl正-应拦截", "空单", 10, 12, 100, False),
        ("多单涨但pnl负-应拦截", "多单", 10, 12, -100, False),
    ]
    passed = 0; failed = 0
    for name, side, entry, mark, pnl, expect_pass in cases:
        ok, reason = validate(side, entry, mark, pnl)
        if ok == expect_pass:
            passed += 1; status = "PASS"
        else:
            failed += 1; status = "FAIL"
        print(f"  [{status}] {name}: {reason}")
    print(f"\nResults: {passed}/{len(cases)} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    ok = test_cases()
    sys.exit(0 if ok else 1)
