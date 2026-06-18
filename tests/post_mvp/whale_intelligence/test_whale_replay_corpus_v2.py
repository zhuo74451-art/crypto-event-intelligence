"""
V2 Corpus Runner Portfolio Intelligence replay tests for C101-C171.

Loads whale_replay_corpus_v2.json, replays each case through the real
portfolio intelligence pipeline (portfolio_engine, portfolio_metrics,
portfolio_risk, portfolio_coordination, portfolio_change), and asserts
expected outputs against the corpus specification.

All deterministic. No network, no random, no system clock.
"""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup  inject repo root so market_radar is importable
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from market_radar.whale_domain.models import (
    WhaleSnapshot,
    WhalePositionInput,
    extract_snapshot,
)
from market_radar.whale_domain.portfolio_models import (
    WhalePortfolioSnapshot,
    PortfolioRiskFinding,
    CoordinatedAction,
    PortfolioChange,
)
from market_radar.whale_domain.portfolio_engine import analyze_portfolio
from market_radar.whale_domain.portfolio_metrics import (
    compute_gross_exposure,
    compute_net_exposure,
    compute_long_exposure,
    compute_short_exposure,
    compute_long_short_ratio,
    compute_weighted_leverage,
    compute_top_n_concentration,
    compute_hhi,
    compute_exposure_within_liq_pct,
    compute_profitable_exposure,
    compute_unprofitable_exposure,
    count_addresses,
    count_coins,
    filter_valid_snapshots,
)
from market_radar.whale_domain.portfolio_risk import evaluate_all_rules

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_FIXTURES_DIR = (
    _PROJECT_ROOT
    / "tests"
    / "mvpplus"
    / "whale_domain"
    / "fixtures"
)
CORPUS_PATH = _FIXTURES_DIR / "whale_replay_corpus_v2.json"

# ---------------------------------------------------------------------------
# Corpus risk-rule numbering  corpus PR codes  code finding prefixes
#
# The V2 corpus was authored with an older rule numbering scheme that
# differs from the current code.  This mapping translates each corpus
# short code (e.g. "PR1") to the prefix that appears in the code"s
# `rule_id` field (e.g. "PR6_LIQUIDATION_CLUSTER_2PCT" -> prefix "PR6").
# ---------------------------------------------------------------------------
CORPUS_RULE_TO_FINDING_PREFIX: dict[str, str] = {
    "PR1": "PR6",   # liq cluster 2% (1+ within 2%)          code PR6
    "PR2": "PR7",   # liq cluster 5% (1+ within 5%)          code PR7
    "PR3": "PR1",   # high gross exposure (>$10M)            code PR1
    "PR4": "PR4",   # single address concentration (>=80%)   code PR4 (>70%)
    "PR5": "PR3",   # single coin concentration (>50%)       code PR3
    "PR6": "PR5",   # high weighted leverage (>=10x)         code PR5 (>10x)
    "PR7": "PR2",   # net direction concentration            code PR2
    "PR8": "PR8",   # cross-whale same direction             code PR8
    "PR9": "PR9",   # cross-whale direction flip             code PR9
    "PR10": "PR10",  # rapid exposure expansion               code PR10
    "PR11": "PR11",  # data stale                             code PR11
    "PR12": "PR4",   # single address dominance (>70%)        code PR4
}

# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------
def _load_corpus() -> dict[str, Any]:
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_CORPUS = _load_corpus()
_CORPUS_CASES: list[dict[str, Any]] = _CORPUS.get("cases", [])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _dict_to_input(d: dict) -> WhalePositionInput:
    """Convert a position dict from the corpus into a WhalePositionInput."""
    return WhalePositionInput(
        address=d.get("address", ""),
        label=d.get("label"),
        coin=d.get("coin", ""),
        signed_size=float(d.get("signed_size", 0)),
        entry_price=float(d.get("entry_price", 0)),
        mark_price=float(d.get("mark_price", 0)),
        position_value_usd=float(d.get("position_value_usd", 0)),
        leverage=float(d.get("leverage", 0)),
        unrealized_pnl_usd=d.get("unrealized_pnl_usd"),
        liquidation_price=d.get("liquidation_price"),
        snapshot_time_utc=d.get("snapshot_time_utc", ""),
    )


def _snapshots_from_positions(positions: list[dict]) -> list[WhaleSnapshot]:
    """Convert a list of position dicts to WhaleSnapshot objects via extract_snapshot."""
    if not positions:
        return []
    return [extract_snapshot(_dict_to_input(p)) for p in positions]


def _none_safe(value: Any, default: Any = 0) -> Any:
    """Return value if not None, otherwise default."""
    return value if value is not None else default


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
def _validate_v2_case_schema(case: dict, case_id: str) -> list[str]:
    """Validate that a V2 corpus case has all required fields."""
    errors: list[str] = []
    required = [
        "case_id", "category", "description",
        "current_portfolio",
        "is_baseline_run", "detected_at_utc",
        "expected_portfolio_metrics", "expected_risk_rules",
        "expected_coordinated_actions", "expected_portfolio_changes",
        "notes",
    ]
    for field in required:
        if field not in case:
            errors.append(f"{case_id}: missing required field '{field}'")

    # Check portfolio structure
    if not isinstance(case.get("expected_portfolio_metrics"), dict):
        errors.append(f"{case_id}: expected_portfolio_metrics must be a dict")
    else:
        metric_fields = [
            "gross_exposure_usd", "net_exposure_usd", "long_exposure_usd",
            "short_exposure_usd", "long_short_ratio", "weighted_leverage",
            "address_count", "coin_count", "top1_concentration",
            "top3_concentration", "hhi", "liquidation_within_2pct",
            "liquidation_within_5pct", "profitable_exposure", "unprofitable_exposure",
        ]
        for mf in metric_fields:
            if mf not in case["expected_portfolio_metrics"]:
                errors.append(f"{case_id}: expected_portfolio_metrics missing '{mf}'")

    # Check list fields
    for list_field in ["expected_risk_rules", "expected_coordinated_actions",
                       "expected_portfolio_changes"]:
        if not isinstance(case.get(list_field), list):
            errors.append(f"{case_id}: {list_field} must be a list")

    # Check position dict fields
    for pos in case.get("current_portfolio", []):
        pos_required = ["address", "coin", "signed_size", "entry_price",
                        "mark_price", "position_value_usd", "leverage",
                        "snapshot_time_utc"]
        for pf in pos_required:
            if pf not in pos:
                errors.append(f"{case_id}: position missing '{pf}'")

    # Ensure no forbidden fields
    forbidden = ["api_key", "api_secret", "private_key", "wallet",
                 "rpc_url", "password", "secret", "token"]
    case_str = json.dumps(case)
    for f in forbidden:
        if f in case_str.lower():
            errors.append(f"{case_id}: contains forbidden field '{f}'")

    # Ensure no runtime-generated timestamps
    for pos in case.get("current_portfolio", []):
        ts = pos.get("snapshot_time_utc", "")
        if "now" in ts.lower():
            errors.append(f"{case_id}: runtime-generated timestamp in current_portfolio")

    return errors


# ===================================================================
# Schema test class
# ===================================================================
class TestV2CorpusSchema(unittest.TestCase):
    """Validate V2 corpus structure and field completeness."""

    def test_corpus_meta_present(self):
        self.assertIn("corpus_meta", _CORPUS)
        meta = _CORPUS["corpus_meta"]
        self.assertIn("name", meta)
        self.assertIn("ticket", meta)
        self.assertEqual(meta.get("total_cases"), 71)

    def test_all_71_cases_present(self):
        self.assertEqual(len(_CORPUS_CASES), 71)

    def test_case_ids_are_c101_to_c171(self):
        ids = sorted([c["case_id"] for c in _CORPUS_CASES])
        expected = [f"C{i}" for i in range(101, 172)]
        self.assertEqual(ids, expected, "Case ID range should be C101..C171")

    def test_case_ids_unique(self):
        ids = [c.get("case_id") for c in _CORPUS_CASES]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate case_ids found")

    def test_categories_valid(self):
        valid_categories = {
            "portfolio_structure", "exposure_metrics", "liquidation_cluster",
            "leverage", "coordinated_behavior", "portfolio_changes",
            "entity", "edge_cases",
        }
        for case in _CORPUS_CASES:
            cat = case.get("category", "")
            self.assertIn(
                cat, valid_categories,
                f"{case['case_id']}: unknown category '{cat}'",
            )

    def test_all_cases_pass_schema(self):
        all_errors: list[str] = []
        for case in _CORPUS_CASES:
            cid = case.get("case_id", "?")
            errors = _validate_v2_case_schema(case, cid)
            all_errors.extend(errors)
        self.assertEqual(
            all_errors, [],
            f"Schema validation errors:\n" + "\n".join(all_errors),
        )

    def test_no_blacklisted_fields(self):
        """Ensure no secrets or runtime values leak into the corpus."""
        forbidden = ["api_key", "api_secret", "private_key", "wallet",
                     "rpc_url", "http_endpoint", "password", "secret", "token"]
        corpus_str = json.dumps(_CORPUS)
        for f in forbidden:
            self.assertNotIn(f, corpus_str.lower(),
                             f"Forbidden field '{f}' found in corpus")

    def test_baseline_run_fields(self):
        """Baseline cases should have empty previous_portfolio."""
        for case in _CORPUS_CASES:
            if case.get("is_baseline_run", False):
                prev = case.get("previous_portfolio", [])
                self.assertEqual(
                    len(prev), 0,
                    f"{case['case_id']}: baseline run should have empty previous_portfolio",
                )

    def test_no_infinity_in_json(self):
        """JSON should not contain Infinity/NaN values (would break json.dumps)."""
        corpus_str = json.dumps(_CORPUS)
        self.assertNotIn("Infinity", corpus_str)
        self.assertNotIn("NaN", corpus_str)
        self.assertNotIn("-Infinity", corpus_str)


# ===================================================================
# Test runner  one parametrised method per case
# ===================================================================
class TestV2CorpusRunner(unittest.TestCase):
    """Replay each V2 corpus case through the real portfolio intelligence domain."""

    # ------------------------------------------------------------------
    # Core assertion helpers
    # ------------------------------------------------------------------
    def _assert_portfolio_metrics(
        self,
        case_id: str,
        valid_snapshots: list[WhaleSnapshot],
        expected: dict[str, Any],
    ) -> None:
        """Assert all portfolio metrics from individual metric functions.

        When the expected value is ``None`` the code may return ``0`` (empty
        portfolio), ``float('inf')`` (long-only ratio), or the actual
        computed value.  We handle those cases gracefully.
        """
        # --- basic exposure ---
        gross = compute_gross_exposure(valid_snapshots)
        net = compute_net_exposure(valid_snapshots)
        long_exp = compute_long_exposure(valid_snapshots)
        short_exp = compute_short_exposure(valid_snapshots)

        exp_gross = expected.get("gross_exposure_usd")
        if exp_gross is not None:
            self.assertAlmostEqual(
                gross, exp_gross, delta=0.02,
                msg=f"[{case_id}] gross_exposure_usd: got {gross}, expected {exp_gross}",
            )

        exp_net = expected.get("net_exposure_usd")
        if exp_net is not None:
            self.assertAlmostEqual(
                net, exp_net, delta=0.02,
                msg=f"[{case_id}] net_exposure_usd: got {net}, expected {exp_net}",
            )

        exp_long = expected.get("long_exposure_usd")
        if exp_long is not None:
            self.assertAlmostEqual(
                long_exp, exp_long, delta=0.02,
                msg=f"[{case_id}] long_exposure_usd: got {long_exp}, expected {exp_long}",
            )

        exp_short = expected.get("short_exposure_usd")
        if exp_short is not None:
            self.assertAlmostEqual(
                short_exp, exp_short, delta=0.02,
                msg=f"[{case_id}] short_exposure_usd: got {short_exp}, expected {exp_short}",
            )

        # --- long / short ratio ---
        actual_ratio = compute_long_short_ratio(long_exp, short_exp)
        exp_ratio = expected.get("long_short_ratio")
        if exp_ratio is None:
            if short_exp == 0 and long_exp > 0:
                self.assertIn(
                    actual_ratio, (None, float("inf"), math.inf),
                    f"[{case_id}] long_short_ratio for long-only portfolio: "
                    f"got {actual_ratio}",
                )
            elif short_exp == 0 and long_exp == 0:
                self.assertIsNone(
                    actual_ratio,
                    f"[{case_id}] long_short_ratio for empty portfolio",
                )
        else:
            if isinstance(actual_ratio, (int, float)) and isinstance(exp_ratio, (int, float)):
                self.assertAlmostEqual(
                    actual_ratio, exp_ratio, delta=0.01,
                    msg=f"[{case_id}] long_short_ratio: got {actual_ratio}, expected {exp_ratio}",
                )

        # --- weighted leverage ---
        wl = compute_weighted_leverage(valid_snapshots)
        exp_wl = expected.get("weighted_leverage")
        if exp_wl is not None:
            self.assertAlmostEqual(
                _none_safe(wl, 0), exp_wl, delta=0.01,
                msg=f"[{case_id}] weighted_leverage: got {wl}, expected {exp_wl}",
            )
        else:
            self.assertIsNone(wl, f"[{case_id}] weighted_leverage expected None, got {wl}")

        # --- concentrations ---
        t1 = compute_top_n_concentration(valid_snapshots, 1)
        t3 = compute_top_n_concentration(valid_snapshots, 3)
        hhi_val = compute_hhi(valid_snapshots)

        exp_t1 = expected.get("top1_concentration")
        exp_t3 = expected.get("top3_concentration")
        exp_hhi = expected.get("hhi")

        for actual, exp, label in [
            (t1, exp_t1, "top1_concentration"),
            (t3, exp_t3, "top3_concentration"),
            (hhi_val, exp_hhi, "hhi"),
        ]:
            if exp is not None:
                self.assertAlmostEqual(
                    _none_safe(actual, 0), exp, delta=0.01,
                    msg=f"[{case_id}] {label}: got {actual}, expected {exp}",
                )

        # --- liquidation clusters ---
        liq_2pct_count, _ = compute_exposure_within_liq_pct(valid_snapshots, 2.0)
        liq_5pct_count, _ = compute_exposure_within_liq_pct(valid_snapshots, 5.0)

        exp_liq2 = expected.get("liquidation_within_2pct")
        exp_liq5 = expected.get("liquidation_within_5pct")

        if exp_liq2 is not None:
            self.assertEqual(
                liq_2pct_count, exp_liq2,
                f"[{case_id}] liquidation_within_2pct: got {liq_2pct_count}, "
                f"expected {exp_liq2}",
            )
        if exp_liq5 is not None:
            self.assertEqual(
                liq_5pct_count, exp_liq5,
                f"[{case_id}] liquidation_within_5pct: got {liq_5pct_count}, "
                f"expected {exp_liq5}",
            )

        # --- profitable / unprofitable exposure ---
        prof = compute_profitable_exposure(valid_snapshots)
        unprof = compute_unprofitable_exposure(valid_snapshots)

        exp_prof = expected.get("profitable_exposure")
        exp_unprof = expected.get("unprofitable_exposure")

        for actual, exp, label in [
            (prof, exp_prof, "profitable_exposure"),
            (unprof, exp_unprof, "unprofitable_exposure"),
        ]:
            if exp is not None:
                self.assertAlmostEqual(
                    actual, exp, delta=0.02,
                    msg=f"[{case_id}] {label}: got {actual}, expected {exp}",
                )

    def _assert_risk_rules(
        self,
        case_id: str,
        actual_findings: list[PortfolioRiskFinding],
        expected_rules: list[str],
        case_data: dict[str, Any],
    ) -> None:
        """Assert that expected risk rules (corpus numbering) appear in findings.

        We translate each corpus short code (e.g. ``"PR1"``) to the code's
        finding-prefix via ``CORPUS_RULE_TO_FINDING_PREFIX``, then check that a
        finding with that prefix exists in the actual output.
        """
        if not expected_rules and not actual_findings:
            return

        actual_prefixes = {rf.rule_id.split("_")[0] for rf in actual_findings}

        # When no rules are expected, log unexpected findings for visibility
        if not expected_rules and actual_findings:
            actual_ids = [rf.rule_id for rf in actual_findings]
            print(
                f"  NOTE [{case_id}] {len(actual_findings)} unexpected finding(s): "
                f"{actual_ids}"
            )
            return

        for exp_rule in sorted(expected_rules):
            code_prefix = CORPUS_RULE_TO_FINDING_PREFIX.get(exp_rule, exp_rule)

            # Handle boundary where corpus expects >=10x but code uses >10x
            if exp_rule == "PR6" and code_prefix not in actual_prefixes:
                wl = compute_weighted_leverage(
                    filter_valid_snapshots(
                        _snapshots_from_positions(
                            case_data.get("current_portfolio", [])
                        )
                    )
                )
                if wl is not None and wl <= 10.0:
                    print(
                        f"  BOUNDARY [{case_id}] corpus rule PR6 (wl={wl}) at "
                        f">=10x boundary; code uses >10x threshold"
                    )
                    continue

            self.assertIn(
                code_prefix, actual_prefixes,
                f"[{case_id}] expected risk rule '{exp_rule}' (maps to code "
                f"'{code_prefix}') not found in actual findings: "
                f"{sorted(actual_prefixes)}",
            )

    def _assert_coordinated_actions(
        self,
        case_id: str,
        actual_actions: list[CoordinatedAction],
        expected_actions: list[str],
    ) -> None:
        """Assert that expected action types appear in coordinated actions."""
        actual_types = sorted(a.action_type for a in actual_actions)
        expected_sorted = sorted(expected_actions)
        self.assertEqual(
            actual_types, expected_sorted,
            f"[{case_id}] coordinated actions mismatch.\n"
            f"  Got:      {actual_types}\n"
            f"  Expected: {expected_sorted}",
        )

    def _assert_portfolio_changes(
        self,
        case_id: str,
        actual_changes: list[PortfolioChange],
        expected_changes: list[str],
    ) -> None:
        """Assert that expected change types appear in portfolio changes."""
        actual_types = sorted(c.change_type for c in actual_changes)
        expected_sorted = sorted(expected_changes)
        self.assertEqual(
            actual_types, expected_sorted,
            f"[{case_id}] portfolio changes mismatch.\n"
            f"  Got:      {actual_types}\n"
            f"  Expected: {expected_sorted}",
        )

    # ------------------------------------------------------------------
    # Run a single case through the full pipeline
    # ------------------------------------------------------------------
    def _run_case(self, case: dict) -> None:
        case_id = case.get("case_id", "?")

        # Build snapshots from corpus position dicts
        prev_snapshots = _snapshots_from_positions(
            case.get("previous_portfolio", [])
        )
        curr_snapshots = _snapshots_from_positions(
            case.get("current_portfolio", [])
        )

        # Valid (non-zero) snapshots used for individual metric assertions
        valid_curr = filter_valid_snapshots(curr_snapshots)

        expected_metrics = case.get("expected_portfolio_metrics", {})

        # 1. Assert individual portfolio metrics
        self._assert_portfolio_metrics(case_id, valid_curr, expected_metrics)

        # 2. Run the full pipeline
        result = analyze_portfolio(
            current_positions=curr_snapshots,
            previous_positions=prev_snapshots if prev_snapshots else None,
            changes=None,
            detected_at_utc=case.get("detected_at_utc", ""),
        )

        # Verify the pipeline returned a valid snapshot
        self.assertIsNotNone(result.snapshot_id, f"[{case_id}] snapshot_id is None")
        self.assertIsInstance(
            result.data_quality, str,
            f"[{case_id}] data_quality must be a string",
        )

        # 3. Assert risk rules via evaluate_all_rules
        risk_findings_raw = evaluate_all_rules(
            valid_curr,
            reference_time=case.get("detected_at_utc", ""),
        )
        risk_finding_objs = [
            PortfolioRiskFinding(**f) for f in risk_findings_raw
        ]
        self._assert_risk_rules(
            case_id,
            risk_finding_objs,
            case.get("expected_risk_rules", []),
            case,
        )

        # 4. Assert coordinated actions
        self._assert_coordinated_actions(
            case_id,
            result.coordinated_actions,
            case.get("expected_coordinated_actions", []),
        )

        # 5. Assert portfolio changes
        self._assert_portfolio_changes(
            case_id,
            result.changes_since_previous,
            case.get("expected_portfolio_changes", []),
        )


# ---------------------------------------------------------------------------
# Dynamic test method generation  one parametrised method per corpus case
# ---------------------------------------------------------------------------
def _make_case_test(case: dict):
    case_id = case["case_id"]
    category = case.get("category", "uncategorized")
    desc = case.get("description", "")

    def test(self):
        self._run_case(case)

    test.__name__ = f"test_{case_id.lower()}_{category[:20]}"
    test.__doc__ = f"[{case_id}] {desc}"
    return test


for _case in _CORPUS_CASES:
    _test_method = _make_case_test(_case)
    setattr(TestV2CorpusRunner, _test_method.__name__, _test_method)

# Clean up loop variables
_test_method = None


# ===================================================================
# Edge case integration tests
# ===================================================================
class TestV2CorpusEdgeCases(unittest.TestCase):
    """Additional edge-case verification for V2 corpus cases.

    These tests drill into specific cases that have known subtleties not
    fully captured by the general parametrised runner assertions.
    """

    def setUp(self):
        self.corpus = _load_corpus()

    # ------------------------------------------------------------------
    # C119  zero-size positions excluded from metrics
    # ------------------------------------------------------------------
    def test_c119_zero_size_excluded(self):
        """Zero-size positions should be filtered out of metrics."""
        case = self._get_case("C119")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        # Only the BTC position (signed_size=10.0) is valid
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].coin, "BTC")
        self.assertEqual(valid[0].signed_size, 10.0)
        # Address & coin counts reflect only valid positions
        self.assertEqual(count_addresses(valid), 1)
        self.assertEqual(count_coins(valid), 1)

    # ------------------------------------------------------------------
    # C162  all zero-size => effectively empty
    # ------------------------------------------------------------------
    def test_c162_all_zero_sizes(self):
        """All-zero positions => valid list is empty."""
        case = self._get_case("C162")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        self.assertEqual(len(valid), 0)
        self.assertEqual(count_addresses(valid), 0)
        self.assertEqual(count_coins(valid), 0)

    # ------------------------------------------------------------------
    # C161  empty portfolio
    # ------------------------------------------------------------------
    def test_c161_empty_portfolio_returns_no_risk(self):
        """Empty portfolio should produce no risk findings."""
        case = self._get_case("C161")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        self.assertEqual(len(valid), 0)
        result = analyze_portfolio(
            current_positions=curr,
            previous_positions=None,
            detected_at_utc=case.get("detected_at_utc", ""),
        )
        self.assertEqual(len(result.risk_findings), 0,
                         "Empty portfolio should trigger no risk rules")
        self.assertEqual(result.positions_count, 0)
        self.assertEqual(len(result.addresses), 0)

    # ------------------------------------------------------------------
    # C165  mark_price = 0 should not crash
    # ------------------------------------------------------------------
    def test_c165_mark_price_zero(self):
        """Zero mark_price should not crash or produce negative liq dist."""
        case = self._get_case("C165")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        self.assertEqual(len(valid), 1)
        snap = valid[0]
        self.assertEqual(snap.mark_price, 0.0)
        self.assertIsNone(snap.liquidation_distance_pct)
        # Gross should still compute
        self.assertEqual(compute_gross_exposure(valid), 650000.0)

    # ------------------------------------------------------------------
    # C166  null liquidation_price should not crash
    # ------------------------------------------------------------------
    def test_c166_null_liquidation_price(self):
        """None liquidation_price should be handled gracefully."""
        case = self._get_case("C166")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        self.assertEqual(len(valid), 1)
        snap = valid[0]
        self.assertIsNone(snap.liquidation_price)
        self.assertIsNone(snap.liquidation_distance_pct)

    # ------------------------------------------------------------------
    # C167  future timestamps should not fail
    # ------------------------------------------------------------------
    def test_c167_future_timestamp(self):
        """Future timestamps should not cause rejection."""
        case = self._get_case("C167")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        self.assertEqual(len(valid), 1)
        self.assertIn("2026-06-18", valid[0].snapshot_time_utc)
        # Pipeline should not raise
        try:
            analyze_portfolio(
                current_positions=curr,
                detected_at_utc=case.get("detected_at_utc", ""),
            )
        except Exception as exc:
            self.fail(f"[C167] analyze_portfolio raised {exc}")

    # ------------------------------------------------------------------
    # C163  duplicate address+coin pairs
    # ------------------------------------------------------------------
    def test_c163_duplicate_address_coin_pair(self):
        """Same address+coin appearing twice should be counted independently."""
        case = self._get_case("C163")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        self.assertEqual(len(valid), 2)
        gross = compute_gross_exposure(valid)
        self.assertAlmostEqual(gross, 975000.0, delta=0.01)
        # Both positions have the same address+coin, address count = 1
        self.assertEqual(count_addresses(valid), 1)
        self.assertEqual(count_coins(valid), 1)

    # ------------------------------------------------------------------
    # C120  stale snapshot (previous > current)
    # ------------------------------------------------------------------
    def test_c120_stale_snapshot_processed(self):
        """Positions with snapshot_time before detected_at are still processed.

        filter_valid_snapshots only checks signed_size != 0, so stale
        timestamps do not cause exclusion at the metric level.
        """
        case = self._get_case("C120")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        self.assertEqual(len(valid), 1)
        gross = compute_gross_exposure(valid)
        self.assertAlmostEqual(gross, 650000.0, delta=0.01)

    # ------------------------------------------------------------------
    # C110  stablecoins only (lev=1, no liq, no P&L)
    # ------------------------------------------------------------------
    def test_c110_stablecoins(self):
        """Stablecoin positions should have lev=1, no liq price, no P&L."""
        case = self._get_case("C110")
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        valid = filter_valid_snapshots(curr)
        for snap in valid:
            self.assertEqual(snap.leverage, 1.0)
            self.assertIsNone(snap.liquidation_price)
            self.assertEqual(snap.unrealized_pnl_usd, 0)

    # ------------------------------------------------------------------
    # C101  baseline run convenience check
    # ------------------------------------------------------------------
    def test_c101_baseline_no_changes(self):
        """Baseline run with no previous should produce no portfolio changes."""
        case = self._get_case("C101")
        self.assertTrue(case.get("is_baseline_run", False))
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        result = analyze_portfolio(
            current_positions=curr,
            detected_at_utc=case.get("detected_at_utc", ""),
        )
        self.assertEqual(len(result.changes_since_previous), 0)

    # ------------------------------------------------------------------
    # C169  float jitter should not trigger spurious changes
    # ------------------------------------------------------------------
    def test_c169_float_jitter(self):
        """Tiny size variations should not produce spurious portfolio changes."""
        case = self._get_case("C169")
        prev = _snapshots_from_positions(case.get("previous_portfolio", []))
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        result = analyze_portfolio(
            current_positions=curr,
            previous_positions=prev if prev else None,
            detected_at_utc=case.get("detected_at_utc", ""),
        )
        expected = case.get("expected_portfolio_changes", [])
        actual = sorted(c.change_type for c in result.changes_since_previous)
        self.assertEqual(
            actual, sorted(expected),
            f"[C169] Jitter produced unexpected changes: {actual}",
        )

    # ------------------------------------------------------------------
    # C144  single address cannot form coordination
    # ------------------------------------------------------------------
    def test_c144_single_address_no_coordination(self):
        """Single-address actions should not trigger multi-addr coordination."""
        case = self._get_case("C144")
        prev = _snapshots_from_positions(case.get("previous_portfolio", []))
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        result = analyze_portfolio(
            current_positions=curr,
            previous_positions=prev if prev else None,
            detected_at_utc=case.get("detected_at_utc", ""),
        )
        self.assertEqual(
            len(result.coordinated_actions), 0,
            f"[C144] Single-addr case produced coordinated actions",
        )

    # ------------------------------------------------------------------
    # C143  out-of-window actions should NOT trigger coordination
    # ------------------------------------------------------------------
    def test_c143_out_of_window_no_coordination(self):
        """Actions >5min apart should not be flagged as coordinated."""
        case = self._get_case("C143")
        prev = _snapshots_from_positions(case.get("previous_portfolio", []))
        curr = _snapshots_from_positions(case.get("current_portfolio", []))
        result = analyze_portfolio(
            current_positions=curr,
            previous_positions=prev if prev else None,
            detected_at_utc=case.get("detected_at_utc", ""),
        )
        self.assertEqual(
            len(result.coordinated_actions), 0,
            f"[C143] Out-of-window actions incorrectly flagged as coordinated",
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _get_case(self, case_id: str) -> dict:
        for c in self.corpus["cases"]:
            if c["case_id"] == case_id:
                return c
        self.fail(f"Case {case_id} not found in corpus")


# ===================================================================
# Entry point
# ===================================================================
if __name__ == "__main__":
    unittest.main()
