"""Adapter-owned CCXT import resolver.

Hyperliquid SDK ships a ``hyperliquid.ccxt`` sub-package (a partial adaptation,
not the real CCXT) and its ``__init__.py`` deliberately overwrites
``sys.modules['ccxt']`` with this fake module:

    import hyperliquid.ccxt as ccxt_module
    sys.modules['ccxt'] = ccxt_module

This breaks any code that ``import ccxt`` after importing hyperliquid.

This resolver provides ``resolve_real_ccxt()`` which:

1. Attempts a normal ``import ccxt``.
2. Verifies the result is the *real* third-party CCXT (checks ``__name__``,
   ``__file__``, ``hasattr(..., 'binance')``, and distribution version).
3. If the loaded module turns out to be ``hyperliquid.ccxt``, it uses
   ``importlib.metadata`` and ``importlib.util`` to locate and load the
   genuine CCXT distribution directly — without requiring the caller to
   manipulate ``sys.modules`` or adjust import order.
4. The resolved module is cached so repeated calls are idempotent.
5. On failure, raises ``CcxtResolutionError`` (a subclass of ``ImportError``).
"""
from __future__ import annotations

import sys
import types
from typing import Optional

from market_radar.external_adapters.adapter_models import AdapterError


# ── Sentinel: reference to the real ccxt once resolved ──

_real_ccxt: Optional[types.ModuleType] = None
_resolved: bool = False


class CcxtResolutionError(ImportError):
    """Raised when the real CCXT cannot be located or loaded."""


def _is_real_ccxt(mod: types.ModuleType) -> bool:
    """Check whether *mod* is the genuine third-party CCXT.

    Rejects ``hyperliquid.ccxt`` by checking several independent signals.
    """
    # 1. __name__ must be "ccxt", not "hyperliquid.ccxt"
    if getattr(mod, "__name__", "") != "ccxt":
        return False

    # 2. __file__ must not be inside hyperliquid site-package
    file_path = getattr(mod, "__file__", "") or ""
    if "hyperliquid" in file_path.replace("\\", "/").split("/"):
        return False

    # 3. Must have at least one allowlisted exchange class
    if not hasattr(mod, "binance"):
        return False

    # 4. Version must be readable
    try:
        from importlib.metadata import version
        ver = version("ccxt")
        if not ver:
            return False
    except Exception:
        return False

    return True


def _clear_ccxt_shadow() -> None:
    """Remove any ``hyperliquid.ccxt`` entries from ``sys.modules``.

    When hyperliquid shadows ``sys.modules['ccxt']`` it also prevents
    the real CCXT's sub-modules (``ccxt.base``, ``ccxt.base.errors``,
    etc.) from loading correctly.  We clear all ``ccxt.*`` keys from
    ``sys.modules`` so a fresh import finds the real package.
    """
    shadowed_keys = [
        k for k in sys.modules
        if k == "ccxt" or k.startswith("ccxt.")
    ]
    for k in shadowed_keys:
        del sys.modules[k]


def _load_real_ccxt_via_metadata() -> types.ModuleType:
    """Locate and load the real CCXT using distribution metadata.

    This is the primary fallback when ``hyperliquid.ccxt`` has shadowed
    ``sys.modules['ccxt']``.

    Strategy: clear the shadowed ``sys.modules['ccxt']`` entries, then
    do a fresh ``import ccxt`` which will find the real package on
    ``sys.path``.
    """
    # Clear any hyperliquid.ccxt shadow entries from sys.modules
    _clear_ccxt_shadow()

    # Fresh import — sys.path search should now find the real ccxt
    try:
        import ccxt as _real
    except ImportError as e:
        raise CcxtResolutionError(
            f"fresh import ccxt failed after clearing shadow: {e}")

    if _is_real_ccxt(_real):
        return _real

    # If still not real, fall through to metadata-based loading
    import importlib.metadata
    import importlib.util
    import pathlib

    # Find the ccxt distribution
    try:
        dist = importlib.metadata.distribution("ccxt")
    except importlib.metadata.PackageNotFoundError:
        raise CcxtResolutionError("ccxt distribution not found via importlib.metadata")

    if dist is None:
        raise CcxtResolutionError("ccxt distribution lookup returned None")

    # Get the top-level package path from the distribution
    try:
        init_path = dist.locate_file(pathlib.Path("ccxt") / "__init__.py")
    except Exception:
        raise CcxtResolutionError("cannot locate real ccxt __init__.py via dist metadata")

    if not init_path or not init_path.exists():
        raise CcxtResolutionError(f"real ccxt not found at {init_path}")

    # Load the real ccxt module from the found path
    spec = importlib.util.spec_from_file_location(
        "ccxt", str(init_path),
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise CcxtResolutionError(f"cannot create module spec for ccxt at {init_path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules["ccxt"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        sys.modules.pop("ccxt", None)
        raise CcxtResolutionError(f"failed to exec real ccxt module: {e}")

    if not _is_real_ccxt(mod):
        sys.modules.pop("ccxt", None)
        raise CcxtResolutionError(
            f"loaded module at {init_path} does not appear to be real ccxt")

    return mod


def resolve_real_ccxt() -> types.ModuleType:
    """Return the genuine third-party ``ccxt`` module.

    Idempotent — the resolved module is cached after the first call.

    Returns:
        The real ``ccxt`` module (guaranteed to be the third-party package).

    Raises:
        CcxtResolutionError: if the real CCXT cannot be found or loaded.
    """
    global _real_ccxt, _resolved

    if _resolved and _real_ccxt is not None:
        return _real_ccxt

    # Strategy 1: check existing sys.modules
    existing = sys.modules.get("ccxt")
    if existing is not None and _is_real_ccxt(existing):
        _real_ccxt = existing
        _resolved = True
        return _real_ccxt

    # Strategy 2: try a fresh import
    try:
        import ccxt as _fresh
        if _is_real_ccxt(_fresh):
            _real_ccxt = _fresh
            _resolved = True
            return _real_ccxt
    except Exception:
        pass

    # Strategy 3: load via distribution metadata (works after hyperliquid shadow)
    mod = _load_real_ccxt_via_metadata()
    _real_ccxt = mod
    _resolved = True
    return _real_ccxt


def is_real_ccxt_available() -> bool:
    """Check whether real CCXT is available without raising."""
    try:
        resolve_real_ccxt()
        return True
    except CcxtResolutionError:
        return False


def ccxt_resolution_error() -> AdapterError:
    """Return a structured AdapterError describing CCXT resolution failure."""
    return AdapterError(
        code="ccxt_import_resolution_failed",
        message="real CCXT package not found or shadowed by hyperliquid.ccxt. "
                "Install ccxt via pip and ensure it is not shadowed.",
        source="import_resolver",
    )
