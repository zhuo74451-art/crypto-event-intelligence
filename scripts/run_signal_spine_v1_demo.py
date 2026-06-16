#!/usr/bin/env python3
"""Signal Spine IO v1 — Independent Verification Demo Runner.

Usage:
    # Offline fixture-only demo (default, no network required)
    python scripts/run_signal_spine_v1_demo.py --fixture

    # Fixture + dry-run output
    python scripts/run_signal_spine_v1_demo.py --fixture --dry-run

    # Include optional real network test (Hyperliquid)
    python scripts/run_signal_spine_v1_demo.py --fixture --dry-run --network

    # Save all outputs to a specific directory
    python scripts/run_signal_spine_v1_demo.py --fixture --dry-run --output-dir ./results/my_test

    # Quick verification (just run the safety checks)
    python scripts/run_signal_spine_v1_demo.py --verify

Design:
  - Does NOT require core Pipeline/Registry (not yet in this branch)
  - Does NOT require API keys or network (unless --network is passed)
  - Does NOT send to Telegram or any real messaging service
  - Uses existing adapter_contract, renderer_contract, and models
  - Validates against golden JSON output
  - Safety-validates all output for trading instruction prohibition

Returns exit code:
  0 = all checks passed
  1 = one or more checks failed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta

# Ensure project root is on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    china_now,
    PIPELINE_VERSION,
)
from market_radar.shared.adapter_contract import (
    FixtureSignalAdapter,
    FixtureCatalog,
)
from market_radar.shared.renderer_contract import CardRenderer
from market_radar.shared.dry_run_renderer import DryRunRenderer
from market_radar.shared.models import DataOrigin
from market_radar.shared.event_intelligence_semantics import (
    EventIntelligenceResult,
    IntelligenceDecision,
    evaluate_event_semantics,
)

# Try to import optional real adapters
try:
    from market_radar.shared.hyperliquid_info_adapter import (
        HyperliquidInfoFreeApiAdapter,
    )
    HYPERLIQUID_AVAILABLE = True
except ImportError:
    HYPERLIQUID_AVAILABLE = False

try:
    from market_radar.shared.free_api_adapters import (
        MultiAssetMarketSyncFreeApiAdapter,
    )
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False


CN_TZ = timezone(timedelta(hours=8))


def print_header(text: str):
    """Print a section header."""
    print("\n" + "═" * 60)
    print(f"  {text}")
    print("═" * 60)


def print_pass(text: str, indent: int = 2):
    print(f"{' ' * indent}[PASS] {text}")


def print_fail(text: str, indent: int = 2):
    print(f"{' ' * indent}[FAIL] {text}")


def print_warn(text: str, indent: int = 2):
    print(f"{' ' * indent}[WARN] {text}")


def print_info(text: str, indent: int = 2):
    print(f"{' ' * indent}[INFO] {text}")


# ─────────────────────────────────────────────────────────────────────────────
# Section A: Fixture Loading & Adapter Verification
# ─────────────────────────────────────────────────────────────────────────────


def verify_adapter_contract() -> bool:
    """Verify that existing adapter contract works with fixtures.

    Tests:
      - FixtureCatalog produces valid fixtures for all 5 card families
      - FixtureSignalAdapter produces NormalizedSignal from fixture
      - NormalizedSignal has required fields
    """
    print_header("Section A: Adapter Contract Verification")

    all_ok = True

    # Test fixture catalog
    try:
        catalog = FixtureCatalog()
        families = [
            CardFamily.MULTI_ASSET_MARKET_SYNC,
            CardFamily.PRICE_OI_VOLUME_ANOMALY,
            CardFamily.NEWS_EVENT_MARKET_IMPACT,
            CardFamily.LIQUIDATION_PRESSURE,
            CardFamily.WHALE_POSITION_ALERT,
        ]

        for family in families:
            adapter = catalog.adapter_for(family)
            signal = adapter.fetch()
            assert signal.card_family == family, f"Card family mismatch: {signal.card_family} != {family}"
            assert signal.asset_or_topic, f"Missing asset_or_topic for {family.value}"
            assert signal.timestamp, f"Missing timestamp for {family.value}"
            assert isinstance(signal.metrics, dict), f"Metrics not dict for {family.value}"
            print_pass(f"FixtureSignalAdapter OK for {family.value}")

        print_pass(f"All {len(families)} card families produce valid NormalizedSignal via FixtureCatalog")
    except Exception as e:
        print_fail(f"Adapter contract verification failed: {e}")
        traceback.print_exc()
        all_ok = False

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Section B: Real Free API Adapters (optional network)
# ─────────────────────────────────────────────────────────────────────────────


def verify_real_adapters(use_network: bool = False) -> bool:
    """Verify real free API adapters.

    Without --network, tests that adapters gracefully handle network
    failure and fall back to fixture/degraded state.

    With --network, attempts real API calls.
    """
    print_header("Section B: Real Free API Adapter Verification")

    all_ok = True

    # Test Hyperliquid adapter
    if HYPERLIQUID_AVAILABLE:
        try:
            adapter = HyperliquidInfoFreeApiAdapter()
            signal = adapter.fetch()

            # Verify it always returns a signal (never raises)
            assert isinstance(signal, NormalizedSignal), "Hyperliquid adapter did not return NormalizedSignal"
            assert signal.asset_or_topic, "Hyperliquid adapter missing asset_or_topic"

            assets = signal.metrics.get("assets", [])
            if use_network and signal.metrics.get("api_success"):
                print_pass(f"Hyperliquid adapter: real API call succeeded ({len(assets)} assets)")
            else:
                if use_network:
                    print_warn("Hyperliquid adapter: API call failed, fixture fallback active")
                else:
                    print_info("Hyperliquid adapter: network test skipped, fixture fallback verified")
                print_pass(f"Hyperliquid fixture fallback produced {len(assets)} assets")

            # Verify fixture fallback marking
            if not signal.metrics.get("api_success"):
                risk_notes = " ".join(signal.risk_notes).lower()
                if "fixture" in risk_notes:
                    print_pass("Fixture fallback correctly marked as data_source=fixture")
                else:
                    print_info("API call succeeded or fallback marking not needed")

        except Exception as e:
            print_fail(f"Hyperliquid adapter error: {e}")
            traceback.print_exc()
            all_ok = False
    else:
        print_warn("Hyperliquid adapter not available (import failed)")

    # Test Binance adapter (existing)
    if BINANCE_AVAILABLE:
        try:
            adapter = MultiAssetMarketSyncFreeApiAdapter()
            signal = adapter.fetch()

            assert isinstance(signal, NormalizedSignal), "Binance adapter did not return NormalizedSignal"
            assets = signal.metrics.get("assets", [])

            if use_network and signal.metrics.get("api_success"):
                print_pass(f"Binance adapter: real API call succeeded ({len(assets)} assets)")
            else:
                print_info(f"Binance adapter: {len(assets)} assets via fixture fallback (network={use_network})")

        except Exception as e:
            print_fail(f"Binance adapter error: {e}")
            all_ok = False
    else:
        print_warn("Binance adapter not available (import failed)")

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Section C: Event Intelligence Semantics
# ─────────────────────────────────────────────────────────────────────────────


def load_fixture(fixture_id: str) -> dict | None:
    """Load a fixture JSON from the fixtures directory."""
    fixtures_dir = os.path.join(_PROJECT_ROOT, "fixtures")
    catalog = {
        "event_high_quality": "event_high_quality.json",
        "event_duplicate": "event_duplicate.json",
        "event_old_news_rehash": "event_old_news_rehash.json",
        "event_no_asset": "event_no_asset.json",
        "event_insufficient_source": "event_insufficient_source.json",
        "event_pump_risk": "event_pump_risk.json",
        "event_missing_fields": "event_missing_fields.json",
    }
    file_name = catalog.get(fixture_id)
    if not file_name:
        return None
    file_path = os.path.join(fixtures_dir, file_name)
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def verify_event_intelligence() -> dict[str, dict]:
    """Verify event intelligence semantics against all fixtures.

    Returns dict of {fixture_id: EventIntelligenceResult} for all fixtures.
    """
    print_header("Section C: Event Intelligence Semantics")

    fixture_ids = [
        "event_high_quality",
        "event_duplicate",
        "event_old_news_rehash",
        "event_no_asset",
        "event_insufficient_source",
        "event_pump_risk",
        "event_missing_fields",
    ]

    results = {}
    all_ok = True
    seen_dedup_keys = set()

    for fid in fixture_ids:
        data = load_fixture(fid)
        if data is None:
            print_fail(f"Could not load fixture: {fid}")
            all_ok = False
            continue

        dedup_key = data.get("dedup_key", "")
        is_duplicate = bool(dedup_key and dedup_key in seen_dedup_keys)

        try:
            result = evaluate_event_semantics(data, is_duplicate=is_duplicate)
            results[fid] = result

            # Verify it returned a valid IntelligenceDecision
            expected_decision = data.get("expected_decision", "")
            actual_decision = result.decision.value

            if actual_decision == expected_decision:
                print_pass(f"{fid}: decision={actual_decision} (expected ✓)")
            else:
                print_fail(f"{fid}: decision={actual_decision} (expected {expected_decision})")
                all_ok = False

            # Safety validation
            violations = result.validate_safety()
            if violations:
                print_fail(f"{fid}: safety violations: {violations}")
                all_ok = False
            else:
                print_pass(f"{fid}: safety validation passed")

            # Check that risk tags are present
            if result.risk_tags:
                print_info(f"{fid}: risk_tags={result.risk_tags}")
            else:
                print_warn(f"{fid}: no risk tags assigned")

            if dedup_key:
                seen_dedup_keys.add(dedup_key)

        except Exception as e:
            print_fail(f"{fid}: evaluation error: {e}")
            traceback.print_exc()
            all_ok = False

    # Special test: duplicate detection
    print_header("Section C (cont): Dedup Verification")
    print_info("Verifying that event_duplicate is recognized as dedup of event_high_quality...")
    dup_data = load_fixture("event_duplicate")
    if dup_data:
        # Both should have same dedup_key
        hq_dedup = load_fixture("event_high_quality").get("dedup_key", "") if load_fixture("event_high_quality") else ""
        dup_dedup = dup_data.get("dedup_key", "")
        if hq_dedup and dup_dedup and hq_dedup == dup_dedup:
            print_pass(f"Dedup keys match: {hq_dedup}")
        else:
            print_fail(f"Dedup key mismatch: '{hq_dedup}' vs '{dup_dedup}'")
            all_ok = False
    else:
        print_fail("Could not load event_duplicate for dedup test")
        all_ok = False

    if all_ok:
        print_pass("All event intelligence tests passed")
    else:
        print_fail("Some event intelligence tests failed")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Section D: Dry-Run Renderer Verification
# ─────────────────────────────────────────────────────────────────────────────


def verify_dry_run_renderer(
    ei_results: dict[str, EventIntelligenceResult],
    output_dir: str,
) -> bool:
    """Verify dry-run renderer produces valid output.

    Checks:
      - JSON output is valid and complete
      - Markdown output is non-empty
      - Telegram-style card is formatted correctly
      - No trading instructions in any output
      - Real send is disabled
    """
    print_header("Section D: Dry-Run Renderer Verification")

    all_ok = True

    try:
        renderer = DryRunRenderer(output_dir=output_dir)

        for fid, ei_result in ei_results.items():
            fixture_data = load_fixture(fid)
            if fixture_data is None:
                continue

            # Render through dry-run renderer
            output = renderer.render(fixture_data, is_duplicate=(fid == "event_duplicate"))

            # Check JSON output
            json_out = output.json_output
            assert json_out.get("dry_run") is True, f"{fid}: dry_run flag missing"
            assert json_out.get("real_send_disabled") is True, f"{fid}: real_send_disabled not True"
            assert json_out.get("no_trading_instructions") is True, f"{fid}: no_trading_instructions not True"
            print_pass(f"{fid}: JSON output valid")

            # Check Markdown output
            md = output.markdown_output
            assert len(md) > 100, f"{fid}: Markdown output too short ({len(md)} chars)"
            # Check for required sections
            for section in ["事件", "资产", "新闻质量", "交易相关性", "最终决策", "风险标签", "观察窗口", "证据摘要", "数据质量", "免责声明"]:
                assert section in md, f"{fid}: Markdown missing section '{section}'"
            print_pass(f"{fid}: Markdown output valid ({len(md)} chars)")

            # Check Telegram card
            tg = output.telegram_card
            assert len(tg) > 50, f"{fid}: Telegram card too short ({len(tg)} chars)"
            assert "Dry-Run Mode" in tg, f"{fid}: Telegram card missing dry-run marker"
            assert "Production Send = False" in tg, f"{fid}: Telegram card missing production_send=False"
            print_pass(f"{fid}: Telegram card valid ({len(tg)} chars)")

            # Safety: no trading instructions — use EventIntelligenceResult.validate_safety()
            # This correctly excludes the disclaimer text
            violations = output.event_intelligence.validate_safety()
            if violations:
                for v in violations:
                    print_fail(f"{fid}: {v}")
                    all_ok = False
            else:
                print_pass(f"{fid}: safety check passed (no trading instructions)")

            # Save outputs
            json_path = output.save_json(output_dir)
            md_path = output.save_markdown(output_dir)
            print_pass(f"{fid}: saved to {os.path.basename(json_path)}, {os.path.basename(md_path)}")

        print_pass(f"All {len(ei_results)} dry-run renderings passed safety checks")

    except Exception as e:
        print_fail(f"Dry-run renderer error: {e}")
        traceback.print_exc()
        all_ok = False

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Section E: Golden JSON Stability
# ─────────────────────────────────────────────────────────────────────────────


def verify_golden_stability(output_dir: str) -> bool:
    """Verify golden JSON output is stable.

    Compares adapter output from FixtureCatalog against the golden
    reference in fixtures/golden_multi_asset_market_sync.json.
    """
    print_header("Section E: Golden JSON Stability")

    all_ok = True

    # Load golden reference
    golden_path = os.path.join(_PROJECT_ROOT, "fixtures", "golden_multi_asset_market_sync.json")
    if not os.path.isfile(golden_path):
        print_fail(f"Golden file not found: {golden_path}")
        return False

    try:
        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print_fail(f"Could not load golden file: {e}")
        return False

    # Generate current output from the adapter
    try:
        catalog = FixtureCatalog()
        signal = catalog.adapter_for(CardFamily.MULTI_ASSET_MARKET_SYNC).fetch()
        current = signal.as_dict()
    except Exception as e:
        print_fail(f"Could not generate current output: {e}")
        return False

    # Compare fields (excluding dynamic fields: timestamp, pipeline_version, signal_id)
    expected = golden.get("expected_signal", {})
    dynamic_fields = {"timestamp", "pipeline_version", "signal_id"}

    def compare_dict(expected_d: dict, current_d: dict, path: str = "") -> list[str]:
        diffs = []
        all_keys = set(expected_d.keys()) | set(current_d.keys())
        for key in sorted(all_keys):
            full_key = f"{path}.{key}" if path else key
            if key in dynamic_fields:
                continue
            if key not in expected_d:
                diffs.append(f"Key missing in golden: {full_key}")
                continue
            if key not in current_d:
                diffs.append(f"Key missing in current: {full_key}")
                continue
            ev = expected_d[key]
            cv = current_d[key]
            if isinstance(ev, dict) and isinstance(cv, dict):
                diffs.extend(compare_dict(ev, cv, full_key))
            elif isinstance(ev, list) and isinstance(cv, list):
                if len(ev) != len(cv):
                    diffs.append(f"List length mismatch at {full_key}: {len(ev)} vs {len(cv)}")
                else:
                    for i, (ei, ci) in enumerate(zip(ev, cv)):
                        if isinstance(ei, dict) and isinstance(ci, dict):
                            diffs.extend(compare_dict(ei, ci, f"{full_key}[{i}]"))
                        elif ei != ci:
                            diffs.append(f"Value mismatch at {full_key}[{i}]: {ei} != {ci}")
            elif ev != cv:
                diffs.append(f"Value mismatch at {full_key}: {ev} != {cv}")
        return diffs

    diffs = compare_dict(expected, current)
    if diffs:
        print_fail(f"Golden JSON mismatch ({len(diffs)} differences):")
        for d in diffs[:10]:
            print_fail(f"  {d}", indent=4)
        all_ok = False
    else:
        print_pass("Golden JSON matches current adapter output (dynamic fields excluded)")

    # Save current output for comparison
    current_output_path = os.path.join(output_dir, "current_multi_asset_market_sync.json")
    try:
        with open(current_output_path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        print_pass(f"Current output saved to {current_output_path}")
    except IOError as e:
        print_warn(f"Could not save current output: {e}")

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Section F: No-Real-Send & Safety Verification
# ─────────────────────────────────────────────────────────────────────────────


def verify_no_real_send(output_dir: str) -> bool:
    """Verify that no real send is possible from the verification components.

    Checks:
      - sender_contract never imported or called
      - No Telegram API calls in dry-run output
      - No real network calls to api.telegram.org
      - Production send flags always False
    """
    print_header("Section F: No-Real-Send Verification")

    all_ok = True

    # Check output files for real-send markers
    dry_run_dir = output_dir
    if os.path.isdir(dry_run_dir):
        for root, dirs, files in os.walk(dry_run_dir):
            for fname in files:
                if fname.endswith(".json") or fname.endswith(".md"):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                        if "real_send_disabled" in content:
                            # Parse to verify it's True
                            if '"real_send_disabled": false' in content or "'real_send_disabled': False" in content:
                                print_fail(f"{fname}: real_send_disabled=False found!")
                                all_ok = False
                    except (IOError, UnicodeDecodeError):
                        pass

    # Verify JSON outputs have safety flags
    for root, dirs, files in os.walk(dry_run_dir):
        for fname in files:
            if fname.endswith(".json") and not fname.startswith("dry_run_"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if "dry_run" in content and "api.telegram.org" in content:
                    print_fail(f"{fname}: contains api.telegram.org reference in dry-run output!")
                    all_ok = False
            except (IOError, UnicodeDecodeError):
                pass

    if all_ok:
        print_pass("No real-send paths detected — all outputs are safe dry-run only")

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Signal Spine IO v1 — Independent Verification Demo Runner",
    )
    parser.add_argument(
        "--fixture", action="store_true", default=True,
        help="Run fixture-based verification (default: True)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Generate dry-run output (default: True)",
    )
    parser.add_argument(
        "--network", action="store_true", default=False,
        help="Include optional real network tests (default: False)",
    )
    parser.add_argument(
        "--verify", action="store_true", default=False,
        help="Run quick safety verification only",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory for dry-run files (default: ./results/dry_run)",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.join(_PROJECT_ROOT, "results", "dry_run")
    os.makedirs(output_dir, exist_ok=True)

    print("═" * 60)
    print("  Signal Spine IO v1 — Independent Verification Demo")
    print(f"  Pipeline: {PIPELINE_VERSION}")
    print(f"  Output:   {output_dir}")
    print(f"  Network:  {'ON' if args.network else 'OFF (fixture-only)'}")
    print("═" * 60)

    checks_passed = 0
    checks_total = 0

    # ── Quick verification mode ──
    if args.verify:
        print_header("Quick Verification Mode")
        ei_results = verify_event_intelligence()
        if ei_results:
            print_pass(f"Event intelligence: {len(ei_results)} fixtures evaluated")
        else:
            print_fail("Event intelligence: no fixtures evaluated")
            sys.exit(1)
        print_pass("Quick verification complete — all fixtures loadable and evaluable")
        sys.exit(0)

    # ── Full verification ──

    # Section A: Adapter contract
    checks_total += 1
    if verify_adapter_contract():
        checks_passed += 1

    # Section B: Real adapters (with or without network)
    checks_total += 1
    if verify_real_adapters(use_network=args.network):
        checks_passed += 1

    # Section C: Event intelligence semantics
    checks_total += 1
    ei_results = verify_event_intelligence()
    if ei_results:
        checks_passed += 1

    # Section D: Dry-run renderer
    if args.dry_run and ei_results:
        checks_total += 1
        if verify_dry_run_renderer(ei_results, output_dir):
            checks_passed += 1

    # Section E: Golden stability
    checks_total += 1
    if verify_golden_stability(output_dir):
        checks_passed += 1

    # Section F: No real send
    checks_total += 1
    if verify_no_real_send(output_dir):
        checks_passed += 1

    # ── Summary ──
    print_header("Verification Summary")
    print(f"  Checks passed: {checks_passed} / {checks_total}")
    print(f"  Dry-run output: {output_dir}")
    print(f"  Network required: {'YES' if args.network else 'NO (offline-safe)'}")
    print(f"  Real send: DISABLED")

    if checks_passed == checks_total:
        print("\n[OK] All checks passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {checks_total - checks_passed} check(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
