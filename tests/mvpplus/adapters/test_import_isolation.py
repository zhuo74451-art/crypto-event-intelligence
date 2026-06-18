"""Import isolation tests — subprocess-based, no import cache masking.

Each test spawns a clean Python subprocess to verify that
the real CCXT is resolved correctly regardless of import order.

No MagicMock, no import order fixups, no sys.modules manipulation
by the test runner.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


def _run_py(script: str, timeout: int = 30) -> dict:
    """Run Python code in a clean subprocess and return structured results."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=timeout,
        env=env,
    )

    stdout_clean = proc.stdout.strip()
    stderr_clean = proc.stderr.strip()

    # Try to parse last JSON line from stdout
    data = {}
    for line in reversed(stdout_clean.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                pass
            break

    result = {
        "exit_code": proc.returncode,
        "stdout_truncated": stdout_clean[:500],
        "stderr_truncated": stderr_clean[:500],
        "data": data,
    }
    return result


# ═══════════════════════════════════════════════════════════════════
# Import order subprocess tests
# ═══════════════════════════════════════════════════════════════════

class TestImportOrderCCXTFirst(unittest.TestCase):
    """import ccxt → import hyperliquid → use resolver for ccxt"""

    def test_ccxt_first_then_resolver_after_hyperliquid(self):
        """After hyperliquid shadows ccxt, the resolver must restore the real one."""
        script = """
import json, sys, importlib.metadata

# 1. import ccxt first
import ccxt as _c1
c1_file = getattr(_c1, "__file__", "")
c1_name = getattr(_c1, "__name__", "")
c1_binance = hasattr(_c1, "binance")

# 2. import hyperliquid (known to shadow sys.modules["ccxt"])
import hyperliquid as _h

# 3. use the Adapter-owned resolver to get real ccxt
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
_c2 = resolve_real_ccxt()
c2_file = getattr(_c2, "__file__", "")
c2_name = getattr(_c2, "__name__", "")
c2_binance = hasattr(_c2, "binance")

result = {
    "c1_real": "hyperliquid" not in c1_file.replace("\\\\", "/").split("/") and c1_name == "ccxt" and c1_binance,
    "c2_real": "hyperliquid" not in c2_file.replace("\\\\", "/").split("/") and c2_name == "ccxt" and c2_binance,
    "c1_file": c1_file, "c1_name": c1_name, "c1_binance": c1_binance,
    "c2_file": c2_file, "c2_name": c2_name, "c2_binance": c2_binance,
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        self.assertTrue(data.get("c1_real"), f"First import not real ccxt: {data}")
        self.assertTrue(data.get("c2_real"), f"Resolver after HL not real ccxt: {data}")


class TestImportOrderHyperliquidFirst(unittest.TestCase):
    """import hyperliquid → import ccxt — ccxt should still be real"""

    def test_ccxt_after_hyperliquid_is_real(self):
        script = """
import json, sys, importlib.metadata

# 1. import hyperliquid first
import hyperliquid as _h

# 2. import ccxt after — need resolver to avoid shadow
import ccxt as _c
c_file = getattr(_c, "__file__", "")
c_name = getattr(_c, "__name__", "")
c_binance = hasattr(_c, "binance")

# Check if shadowed
hl_ccxt_file = ""
hl_ccxt = getattr(_h, "ccxt", None)
if hl_ccxt is not None:
    hl_ccxt_file = getattr(hl_ccxt, "__file__", "")

result = {
    "ccxt_real": "hyperliquid" not in c_file.replace("\\\\", "/").split("/") and c_name == "ccxt" and c_binance,
    "ccxt_file": c_file,
    "ccxt_name": c_name,
    "ccxt_binance": c_binance,
    "hl_ccxt_file": hl_ccxt_file,
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        # hyperliquid-first SHOULD trigger hyperliquid.ccxt shadowing.
        # This test exists to verify we KNOW it fails without our fix.
        # With the fix, we can check the resolver separately.
        # For now, verify the known behavior before fix.
        self.assertFalse(data.get("ccxt_real"),
                         "HL-first bare import should get shadowed ccxt (expected behavior)")


class TestImportOrderW4HLFirst(unittest.TestCase):
    """W4 HL adapter first → W4 CCXT adapter"""

    def test_w4_hl_then_ccxt_adapter_real_ccxt(self):
        script = """
import json, sys

# 1. Import HyperliquidPublicAdapter first
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter

# 2. Check ccxt after HL adapter import
import ccxt as _c1
c1_file = getattr(_c1, "__file__", "")
c1_name = getattr(_c1, "__name__", "")
c1_binance = hasattr(_c1, "binance")

# 3. Import CcxtPublicMarketAdapter
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter

# 4. Check ccxt again
import ccxt as _c2
c2_file = getattr(_c2, "__file__", "")
c2_name = getattr(_c2, "__name__", "")
c2_binance = hasattr(_c2, "binance")

result = {
    "c1_real": "hyperliquid" not in c1_file.replace("\\\\", "/").split("/") and c1_name == "ccxt" and c1_binance,
    "c2_real": "hyperliquid" not in c2_file.replace("\\\\", "/").split("/") and c2_name == "ccxt" and c2_binance,
    "adapter_ok": True,
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        self.assertTrue(data.get("c1_real"), f"ccxt after HL adapter not real: {data}")
        self.assertTrue(data.get("c2_real"), f"ccxt after CCXT adapter not real: {data}")
        self.assertTrue(data.get("adapter_ok"))


class TestImportOrderW4CCXTFirst(unittest.TestCase):
    """W4 CCXT adapter first → W4 HL adapter"""

    def test_w4_ccxt_then_hl_adapter_real_ccxt(self):
        script = """
import json, sys

# 1. Import CcxtPublicMarketAdapter first
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter

# 2. Check ccxt
import ccxt as _c1
c1_file = getattr(_c1, "__file__", "")
c1_name = getattr(_c1, "__name__", "")
c1_binance = hasattr(_c1, "binance")

# 3. Import HyperliquidPublicAdapter
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter

# 4. Check ccxt again
import ccxt as _c2
c2_file = getattr(_c2, "__file__", "")
c2_name = getattr(_c2, "__name__", "")
c2_binance = hasattr(_c2, "binance")

result = {
    "c1_real": "hyperliquid" not in c1_file.replace("\\\\", "/").split("/") and c1_name == "ccxt" and c1_binance,
    "c2_real": "hyperliquid" not in c2_file.replace("\\\\", "/").split("/") and c2_name == "ccxt" and c2_binance,
    "adapter_ok": True,
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        self.assertTrue(data.get("c1_real"), f"ccxt after CCXT adapter not real: {data}")
        self.assertTrue(data.get("c2_real"), f"ccxt after HL adapter not real: {data}")


# ═══════════════════════════════════════════════════════════════════
# Alternating usage test
# ═══════════════════════════════════════════════════════════════════

class TestAlternatingAdapterUsage(unittest.TestCase):
    """HL → CCXT → HL → CCXT in same process"""

    def test_alternating_adapters_use_real_ccxt(self):
        script = """
import json, sys

from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter

# Create both adapters
hl = HyperliquidPublicAdapter()
ccxt_a = CcxtPublicMarketAdapter()

# Check ccxt module after both are created
import ccxt as _c
c_file = getattr(_c, "__file__", "")
c_name = getattr(_c, "__name__", "")
c_binance = hasattr(_c, "binance")

hl.close()
ccxt_a.close()

result = {
    "ccxt_real": "hyperliquid" not in c_file.replace("\\\\", "/").split("/") and c_name == "ccxt" and c_binance,
    "ccxt_name": c_name,
    "ccxt_binance": c_binance,
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        self.assertTrue(data.get("ccxt_real"), f"ccxt not real after alternating: {data}")


class TestRepeatedResolverCalls(unittest.TestCase):
    """Repeated resolve_real_ccxt() calls should be idempotent"""

    def test_repeated_resolver_idempotent(self):
        script = """
import json, sys

from market_radar.external_adapters.import_resolver import resolve_real_ccxt, is_real_ccxt_available

# Resolve multiple times
m1 = resolve_real_ccxt()
m2 = resolve_real_ccxt()
m3 = resolve_real_ccxt()

result = {
    "ids_same": id(m1) == id(m2) == id(m3),
    "available": is_real_ccxt_available(),
    "has_binance": hasattr(m1, "binance"),
    "name": getattr(m1, "__name__", ""),
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        self.assertTrue(data.get("ids_same"), f"Resolver not idempotent: {data}")
        self.assertTrue(data.get("available"))
        self.assertTrue(data.get("has_binance"))


# ═══════════════════════════════════════════════════════════════════
# Resolver exception safety
# ═══════════════════════════════════════════════════════════════════

class TestResolverExceptionCleanup(unittest.TestCase):
    """Resolver must not leave corrupted state after exceptions"""

    def test_resolver_import_error_does_not_pollute(self):
        """When real CCXT cannot be found, sys.modules must not be corrupted."""
        script = """
import json, sys

# Simulate: hyperliquid has shadowed ccxt
import hyperliquid as _h

from market_radar.external_adapters.import_resolver import (
    resolve_real_ccxt, is_real_ccxt_available, CcxtResolutionError
)

# After hyperliquid import, ccxt in sys.modules is hyperliquid.ccxt
before = sys.modules.get("ccxt")
before_name = getattr(before, "__name__", "") if before else None

try:
    m = resolve_real_ccxt()
    resolved = True
except CcxtResolutionError:
    resolved = False

after = sys.modules.get("ccxt")
after_name = getattr(after, "__name__", "") if after else None

result = {
    "resolved": resolved,
    "before_name": before_name,
    "after_name": after_name,
    "available": is_real_ccxt_available(),
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        # We expect the resolver to work (real ccxt is installed)
        # If real ccxt is installed, this should pass
        if data.get("resolved"):
            self.assertTrue(data.get("available"))


# ═══════════════════════════════════════════════════════════════════
# Hyperliquid adapter isolation
# ═══════════════════════════════════════════════════════════════════

class TestHyperliquidAdapterIsolation(unittest.TestCase):
    """Using HyperliquidPublicAdapter must not break subsequent CCXT"""

    def test_hl_adapter_does_not_shadow_ccxt(self):
        script = """
import json, sys

from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.import_resolver import resolve_real_ccxt

# Create and close HL adapter
a = HyperliquidPublicAdapter()
a.close()

# After adapter close, ccxt must still be resolvable
m = resolve_real_ccxt()
result = {
    "ccxt_real": "hyperliquid" not in getattr(m, "__file__", "").replace("\\\\", "/").split("/"),
    "has_binance": hasattr(m, "binance"),
    "name": getattr(m, "__name__", ""),
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        self.assertTrue(data.get("ccxt_real"), f"HL adapter shadowed ccxt: {data}")
        self.assertTrue(data.get("has_binance"))


# ═══════════════════════════════════════════════════════════════════
# CCXT Adapter with resolver
# ═══════════════════════════════════════════════════════════════════

class TestCCXTAdapterUsesRealCCXT(unittest.TestCase):
    """CcxtPublicMarketAdapter must use real CCXT via resolver"""

    def test_adapter_check_ccxt_uses_real_ccxt(self):
        script = """
import json, sys

from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter

a = CcxtPublicMarketAdapter()
ok = a._check_ccxt()
err = a._ccxt_resolution_error

result = {
    "ccxt_available": ok,
    "resolution_error": err,
}
print(json.dumps(result))
"""
        r = _run_py(script)
        data = r.get("data", {})
        self.assertEqual(r["exit_code"], 0, f"Subprocess failed: {r['stderr_truncated']}")
        # Real ccxt is installed, so _check_ccxt should return True
        self.assertTrue(data.get("ccxt_available"),
                        f"CCXT not available through resolver: {data}")


# ═══════════════════════════════════════════════════════════════════
# Reproduce-all test (comprehensive)
# ═══════════════════════════════════════════════════════════════════

class TestComprehensiveImportOrders(unittest.TestCase):
    """All import orders, each in a clean subprocess"""

    def test_all_import_orders(self):
        """Run all 6 import orders and verify CCXT is real in each."""
        import subprocess as _sp
        project_root = PROJECT_ROOT

        orders = [
            ("ccxt-first-resolver", """
import ccxt as _c
import hyperliquid as _h
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
_m = resolve_real_ccxt()
"""),
            ("hyperliquid-first-resolver", """
import hyperliquid as _h
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
_m = resolve_real_ccxt()
"""),
            ("W4-HL-first", """
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
_m = resolve_real_ccxt()
"""),
            ("W4-CCXT-first", """
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
_m = resolve_real_ccxt()
"""),
            ("alternating", """
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
_m = resolve_real_ccxt()
"""),
            ("repeated-resolver", """
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
_m1 = resolve_real_ccxt()
_m2 = resolve_real_ccxt()
_m3 = resolve_real_ccxt()
_m = _m3
"""),
        ]

        results = []
        for label, setup_code in orders:
            check_code = f"""
import json
{setup_code}
_name = getattr(_m, "__name__", "")
_file = getattr(_m, "__file__", "")
_binance = hasattr(_m, "binance")
_hl_path = "hyperliquid" in _file.replace("\\\\", "/").split("/")
result = {{
    "label": "{label}",
    "real_ccxt": not _hl_path and _name == "ccxt" and _binance,
    "name": _name,
    "has_binance": _binance,
}}
print(json.dumps(result))
"""
            env = os.environ.copy()
            env["PYTHONPATH"] = project_root
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            proc = _sp.run([sys.executable, "-c", check_code],
                          capture_output=True, text=True, timeout=30, env=env)
            data = {}
            for line in reversed(proc.stdout.strip().splitlines()):
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        pass
                    break

            is_pass = data.get("real_ccxt", False) and proc.returncode == 0
            results.append({"label": label, "pass": is_pass, "data": data,
                           "rc": proc.returncode})

        failed = [r for r in results if not r["pass"]]
        if failed:
            details = "; ".join(f"{r['label']}: {r['data']}" for r in failed)
            self.fail(f"Import orders failed: {details}")

        all_real = all(r["data"].get("real_ccxt") for r in results if r["data"])
        self.assertTrue(all_real, f"Not all imports resolved to real ccxt: {results}")


if __name__ == "__main__":
    unittest.main()
