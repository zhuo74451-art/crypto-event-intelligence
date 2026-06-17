# Adapter Import Isolation Migration Guide

## Root Cause

The `hyperliquid` SDK (v0.4.66) contains a `ccxt` sub-package at
`hyperliquid/ccxt/__init__.py`. Its top-level `__init__.py` overwrites
`sys.modules['ccxt']` with this internal shim:

```python
import hyperliquid.ccxt as ccxt_module
sys.modules['ccxt'] = ccxt_module
```

This means **any** `import ccxt` after `import hyperliquid` loads
`hyperliquid.ccxt` instead of the real third-party CCXT package.
The shim does not expose exchange classes like `binance`, `okx`, or `bybit`,
causing `CcxtPublicMarketAdapter` to fail with `AttributeError` or
`could not initialize`.

## W4 Fix: Adapter-Owned Import Resolver

All import isolation logic is encapsulated in:

```
market_radar/external_adapters/import_resolver.py
```

Key API:

| Function | Purpose |
|---|---|
| `resolve_real_ccxt()` | Return the real CCXT module (raises `CcxtResolutionError` on failure) |
| `is_real_ccxt_available()` | Check availability without raising |
| `ccxt_resolution_error()` | Return structured `AdapterError` for response envelopes |

The resolver uses a three-strategy cascade:

1. Check existing `sys.modules['ccxt']` — if it's the real CCXT, use it.
2. Try a fresh `import ccxt` — works if hyperliquid hasn't shadowed it.
3. Clear shadowed `ccxt.*` from `sys.modules`, then re-import — works
   even after hyperliquid import has shadowed the namespace.

## HyperliquidPublicAdapter Changes

`HyperliquidPublicAdapter._check_sdk()` and `_get_info()` now save and
restore `sys.modules['ccxt']` around hyperliquid imports. This prevents
the adapter from permanently shadowing CCXT for subsequent callers.

## CcxtPublicMarketAdapter Changes

- `_check_ccxt()` uses `resolve_real_ccxt()` instead of bare `import ccxt`.
- `_get_exchange()` uses `resolve_real_ccxt()` instead of bare `import ccxt`.
- Resolution failure returns `ccxt_import_resolution_failed` error code
  with structured `AdapterError`, not a cryptic `AttributeError`.

## Integration Workarounds Eligible for Deletion

The following workarounds in the integration layer can be removed once
W6 QA has verified the W4 import isolation fix:

### File: `market_radar/integration/one_shot.py`

**Lines 17-28** — Pre-import + sys.modules restore:
```python
import ccxt as _real_ccxt
_CCXT_ID = id(_real_ccxt)
...
import sys as _sys
if id(_sys.modules.get("ccxt")) != _CCXT_ID:
    _sys.modules["ccxt"] = _real_ccxt
```

**Function `_ensure_real_ccxt()` (lines 60-63)**:
```python
def _ensure_real_ccxt() -> None:
    if id(_sys.modules.get("ccxt")) != _CCXT_ID:
        _sys.modules["ccxt"] = _real_ccxt
```

**Removal impact**: After W4 import isolation, the integration module can
simply `from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter`
without any pre-import or sys.modules manipulation. These lines can be
safely deleted.

**W6 verification required**:
1. Verify `CcxtPublicMarketAdapter._check_ccxt()` returns True without
   any pre-import of ccxt.
2. Run integration tests after removing the workaround.
3. Verify all 5 live probes pass (HL → CCXT → HL → CCXT → CCXT).

## Verifying the Fix

### Test command (subprocess isolation):

```bash
python -X utf8 -m pytest tests/mvpplus/adapters/test_import_isolation.py -v
```

Expected: 10 passed.

### Live probe command:

```bash
python -c "
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
# Alternating usage should work without errors
hl = HyperliquidPublicAdapter()
print('HL:', hl.fetch_all_mids().ok)
ccxt_a = CcxtPublicMarketAdapter()
print('CCXT BTC:', ccxt_a.fetch('binance', 'ticker', 'BTC/USDT').ok)
print('HL meta:', hl.fetch_meta().ok)
print('CCXT ETH:', ccxt_a.fetch('binance', 'ticker', 'ETH/USDT').ok)
print('CCXT SOL:', ccxt_a.fetch('binance', 'ticker', 'SOL/USDT').ok)
hl.close()
ccxt_a.close()
"
```

## Remaining Upstream Risk

The `hyperliquid.ccxt` shadowing is intentional SDK behavior, not a bug.
The SDK team may change or remove this in future versions. If they do,
the resolver will detect the real CCXT directly on `sys.modules` and
skip the shadow-clearing strategy entirely — no migration needed.

If the SDK adds additional shadowing mechanisms (e.g., custom import
hooks), the resolver may need updates. Current collision surfaces:

| SDK Action | W4 Mitigation |
|---|---|
| `sys.modules['ccxt'] = hyperliquid.ccxt` | `_clear_ccxt_shadow()` + re-import |
| Additional ccxt sub-module keys | Automatic via `ccxt.*` key clearing |
| pkg_resources / namespace packages | Not observed; no action needed |
| Custom import hooks | Not observed; no action needed |

## Modified Files

- `market_radar/external_adapters/import_resolver.py` (NEW)
- `market_radar/external_adapters/ccxt_public_market_adapter.py`
- `market_radar/external_adapters/hyperliquid_public_adapter.py`
- `tests/mvpplus/adapters/test_import_isolation.py` (NEW)
