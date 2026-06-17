"""Safety invariant tests for the operations package.

Verifies that the operations package remains a generic infrastructure layer
with no business domain coupling.
"""

import ast
import os
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "market_radar" / "operations"
SHARED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "market_radar" / "shared"

BUSINESS_MODULES = {
    "models", "gate_contract", "pipeline", "signal_orchestrator",
    "signal_registry", "noise_gate", "event_intelligence_mapper",
    "adapter_contract", "free_api_adapters", "hyperliquid_info_adapter",
    "event_intelligence_semantics", "dry_run_renderer", "event_price_backfill",
    "price_provider_protocol", "renderer_contract", "sender_contract",
    "evidence_ledger", "ai_fallback",
}

NETWORK_MODULES = {"urllib", "requests", "aiohttp", "httpx", "websocket", "socket"}

DAEMON_MODULES = {"threading", "multiprocessing", "subprocess", "signal", "asyncio"}

FORBIDDEN_TRADE_TERMS = {"buy", "sell", "long", "short", "trade", "position", "order"}


def _get_imports(filepath: str) -> set[str]:
    """Extract module-level import names from a Python file."""
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                imports.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                imports.add(top)
    return imports


class TestSafetyInvariants:
    """Verify the operations package has zero business or network coupling."""

    def test_no_business_module_imports(self):
        """Operations must not import any business lane module from shared/."""
        ops_files = sorted(OPS_DIR.glob("*.py"))
        assert len(ops_files) >= 5, f"only {len(ops_files)} files in operations"

        violations: list[str] = []
        for fpath in ops_files:
            if fpath.name == "__init__.py":
                continue
            imports = _get_imports(str(fpath))
            for mod in BUSINESS_MODULES:
                if mod in imports or f"market_radar.shared.{mod}" in str(imports):
                    violations.append(f"{fpath.name}: imports business module '{mod}'")

        assert len(violations) == 0, f"Business coupling violations: {violations}"

    def test_only_ops_self_imports(self):
        """Operations may only import from itself or stdlib. No shared imports."""
        ops_files = sorted(OPS_DIR.glob("*.py"))
        violations: list[str] = []
        for fpath in ops_files:
            if fpath.name == "__init__.py":
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            if "from market_radar.shared" in content:
                violations.append(f"{fpath.name}: imports from market_radar.shared")
            if "import market_radar.shared" in content:
                violations.append(f"{fpath.name}: imports market_radar.shared")

        assert len(violations) == 0, f"Shared module coupling: {violations}"

    def test_no_network_imports(self):
        """Operations must not import network libraries."""
        ops_files = sorted(OPS_DIR.glob("*.py"))
        violations: list[str] = []
        for fpath in ops_files:
            if fpath.name == "__init__.py":
                continue
            imports = _get_imports(str(fpath))
            for net_mod in NETWORK_MODULES:
                if net_mod in imports:
                    violations.append(f"{fpath.name}: imports network module '{net_mod}'")

        assert len(violations) == 0, f"Network import violations: {violations}"

    def test_no_daemon_or_bg_process_creation(self):
        """Operations must not import daemon/bg process modules."""
        ops_files = sorted(OPS_DIR.glob("*.py"))
        violations: list[str] = []
        for fpath in ops_files:
            if fpath.name == "__init__.py":
                continue
            imports = _get_imports(str(fpath))
            for dm in DAEMON_MODULES:
                if dm in imports:
                    violations.append(f"{fpath.name}: imports daemon module '{dm}'")

        assert len(violations) == 0, f"Daemon/process import violations: {violations}"

    def test_no_trade_terms_in_source(self):
        """Operations source must not contain trading terms in function/class names."""
        ops_files = sorted(OPS_DIR.glob("*.py"))
        violations: list[str] = []
        for fpath in ops_files:
            if fpath.name == "__init__.py":
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().lower()
            for term in FORBIDDEN_TRADE_TERMS:
                if f"def {term}" in content or f"class {term}" in content:
                    violations.append(f"{fpath.name}: contains trade term '{term}'")

        assert len(violations) == 0, f"Trade term violations: {violations}"

    def test_no_infinite_loop_patterns(self):
        """Verify no while True patterns exist."""
        ops_files = sorted(OPS_DIR.glob("*.py"))
        for fpath in ops_files:
            if fpath.name == "__init__.py":
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped == "while True:" or stripped == "while 1:":
                        # Check it's not inside a test
                        pytest.fail(f"{fpath.name}:{i}: infinite loop pattern")
