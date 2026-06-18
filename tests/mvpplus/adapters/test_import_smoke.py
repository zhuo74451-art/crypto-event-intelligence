"""Import smoke test — verify all adapter modules load without error."""
import unittest


class TestImportSmoke(unittest.TestCase):
    def test_httpx_transport_imports(self):
        from market_radar.external_adapters.httpx_transport import HttpxTransport, TransportResult, TransportError
        self.assertIsNotNone(HttpxTransport)

    def test_adapter_models_imports(self):
        from market_radar.external_adapters.adapter_models import AdapterResult, AdapterError, AdapterProvenance, AdapterHealth
        self.assertIsNotNone(AdapterResult)

    def test_hyperliquid_adapter_imports(self):
        from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
        self.assertIsNotNone(HyperliquidPublicAdapter)

    def test_ccxt_adapter_imports(self):
        from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
        self.assertIsNotNone(CcxtPublicMarketAdapter)

    def test_no_l1_l6_imports(self):
        """Verify adapter code does not import from forbidden lane modules."""
        import ast, os
        # __file__ = tests/mvpplus/adapters/test_import_smoke.py -> go up 3 levels = project root
        test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        basedir = os.path.join(test_dir, "market_radar", "external_adapters")
        forbidden_prefixes = ("market_radar.l1_", "market_radar.l2_", "market_radar.l3_",
                              "market_radar.l4_", "market_radar.l5_", "market_radar.l6_",
                              "market_radar.shared")
        for fname in os.listdir(basedir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(basedir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=fpath)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for prefix in forbidden_prefixes:
                            self.assertNotIn(prefix, alias.name, f"{fname} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for prefix in forbidden_prefixes:
                            self.assertNotIn(prefix, node.module, f"{fname} imports from {node.module}")


if __name__ == "__main__":
    unittest.main()
