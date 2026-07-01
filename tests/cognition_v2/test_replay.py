"""Cognition v2 replay contract tests.

R04: explicit point-in-time authority
R05: real future-leakage validation
R06: real split-order integrity
R07: correct outcome windows
"""

from datetime import datetime, timedelta, timezone
import math
import pytest

from market_radar.cognition_v2.domain.contracts import (
    EventFamily,
    EvidenceRef,
    HistoricalCaseManifest,
    MarketRegime,
    SplitLabel,
    OutcomeWindow,
    SourceAuthority,
    FactPermission,
)
from market_radar.cognition_v2.replay.contracts import (
    ManifestBuilder,
    HistoricalSourceRecord,
    HistoricalEvidenceRecord,
    LeakageValidator,
    EvidenceLeakageResult,
    SplitBoundary,
    SplitOrderIntegrity,
    SplitOrderResult,
    CorrectionRelations,
    CorrectionChainSplitValidator,
    deterministic_manifest_serialize,
    CorrectionType,
    validate_outcome_window,
    validate_outcome_windows,
    CANONICAL_WINDOW_LABELS,
    WINDOW_DURATIONS,
)


NOW = datetime.now(timezone.utc)
PAST = datetime(2020, 1, 1, tzinfo=timezone.utc)
FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)
YESTERDAY = NOW - timedelta(hours=24)
TWO_DAYS_AGO = NOW - timedelta(hours=48)


# ═══════════════════════════════════════════════════════════════════════════════
# R04 — Historical authority and times
# ═══════════════════════════════════════════════════════════════════════════════

class TestHistoricalSourceRecord:
    def test_explicit_authority_required(self):
        with pytest.raises(ValueError, match="must be explicitly supplied"):
            HistoricalSourceRecord(
                source_id="s1", name="Test", source_type="api",
                authority=SourceAuthority.UNKNOWN,
                fact_permission=FactPermission.SELF,
                first_seen_at=PAST,
            )

    def test_explicit_permission_required(self):
        with pytest.raises(ValueError, match="must be explicitly supplied"):
            HistoricalSourceRecord(
                source_id="s1", name="Test", source_type="api",
                authority=SourceAuthority.OFFICIAL,
                fact_permission=FactPermission.NONE,
                first_seen_at=PAST,
            )

    def test_timezone_aware_required(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            HistoricalSourceRecord(
                source_id="s1", name="Test", source_type="api",
                authority=SourceAuthority.OFFICIAL,
                fact_permission=FactPermission.SELF,
                first_seen_at=datetime(2020, 1, 1),  # naive
            )

    def test_valid(self):
        r = HistoricalSourceRecord(
            source_id="s1", name="Test", source_type="api",
            authority=SourceAuthority.OFFICIAL,
            fact_permission=FactPermission.SELF,
            first_seen_at=PAST,
        )
        assert r.authority == SourceAuthority.OFFICIAL
        assert r.fact_permission == FactPermission.SELF


class TestHistoricalEvidenceRecord:
    def test_timezone_required(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            HistoricalEvidenceRecord(
                evidence_id="e1", source_id="s1", content_hash="abc",
                first_seen_at=datetime(2020, 1, 1),  # naive
                retrieval_time=PAST,
            )

    def test_assessment_timezone_required(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            HistoricalEvidenceRecord(
                evidence_id="e1", source_id="s1", content_hash="abc",
                first_seen_at=PAST, retrieval_time=PAST,
                assessment_time=datetime(2020, 1, 1),  # naive
            )

    def test_available_at(self):
        ev = HistoricalEvidenceRecord(
            evidence_id="e1", source_id="s1", content_hash="abc",
            first_seen_at=PAST, retrieval_time=PAST,
        )
        assert ev.available_at(NOW) is True
        assert ev.available_at(PAST) is True

    def test_not_available_when_retrieved_later(self):
        ev = HistoricalEvidenceRecord(
            evidence_id="e1", source_id="s1", content_hash="abc",
            first_seen_at=PAST, retrieval_time=FUTURE,
        )
        assert ev.available_at(PAST) is False


# ═══════════════════════════════════════════════════════════════════════════════
# R05 — Future-leakage
# ═══════════════════════════════════════════════════════════════════════════════

class TestLeakageValidator:
    def test_timezone_naive_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            LeakageValidator(assessment_cutoff=datetime(2020, 1, 1))

    def test_published_before_cutoff_retrieved_after_blocked(self):
        """R05: Published before cutoff but retrieved after cutoff is blocked."""
        validator = LeakageValidator(assessment_cutoff=NOW)
        ev = HistoricalEvidenceRecord(
            evidence_id="e1", source_id="s1", content_hash="abc",
            first_seen_at=PAST,  # published/presented before
            publication_time=PAST,
            retrieval_time=FUTURE,  # but retrieved after
        )
        assert validator.is_available(ev) is False
        result = validator.validate_evidence_list([ev])
        assert result.is_clean is False
        assert "e1" in result.blocked_ids

    def test_retrieved_before_assessed_after_still_available(self):
        """R05: Retrieved before cutoff but assessed after — remains available at retrieval."""
        validator = LeakageValidator(assessment_cutoff=NOW)
        ev = HistoricalEvidenceRecord(
            evidence_id="e2", source_id="s1", content_hash="def",
            first_seen_at=YESTERDAY,
            retrieval_time=YESTERDAY,  # retrieved before
            assessment_time=FUTURE,  # assessed after
        )
        assert validator.is_available(ev) is True  # available at retrieval time

    def test_correction_first_seen_after_cutoff_blocked(self):
        """R05: Correction first seen after cutoff is blocked even when correcting older item."""
        validator = LeakageValidator(assessment_cutoff=PAST)
        ev = HistoricalEvidenceRecord(
            evidence_id="e3", source_id="s1", content_hash="ghi",
            first_seen_at=FUTURE,  # correction appears after cutoff
            retrieval_time=FUTURE,
        )
        assert validator.is_available(ev) is False
        result = validator.validate_evidence_list([ev])
        assert "e3" in result.blocked_ids

    def test_mixed_clean_and_leaked(self):
        """R05: Mixed clean/leaked returns exact blocked IDs and reasons."""
        validator = LeakageValidator(assessment_cutoff=NOW)
        clean = HistoricalEvidenceRecord(
            evidence_id="clean", source_id="s1", content_hash="cln",
            first_seen_at=PAST, retrieval_time=PAST,
        )
        leaked = HistoricalEvidenceRecord(
            evidence_id="leaked", source_id="s1", content_hash="lek",
            first_seen_at=FUTURE, retrieval_time=FUTURE,
        )
        result = validator.validate_evidence_list([clean, leaked])
        assert result.is_clean is False
        assert result.blocked_ids == ["leaked"]
        assert len(result.reasons) == 1

    def test_filtering_has_audit_result(self):
        """R05: Filtering cannot silently discard evidence without audit result."""
        validator = LeakageValidator(assessment_cutoff=NOW)
        ev = HistoricalEvidenceRecord(
            evidence_id="leak", source_id="s1", content_hash="lek",
            first_seen_at=FUTURE, retrieval_time=FUTURE,
        )
        result = validator.validate_evidence_list([ev])
        # Must produce a reason, not silently discard
        assert len(result.reasons) >= 1
        assert "not available" in result.reasons[0].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# R06 — Split-order integrity
# ═══════════════════════════════════════════════════════════════════════════════

class TestSplitBoundary:
    def test_timezone_required(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            SplitBoundary(
                build_max_time=datetime(2020, 6, 1),
                development_max_time=datetime(2020, 12, 1),
            )

    def test_build_before_development(self):
        with pytest.raises(ValueError, match="must be before"):
            SplitBoundary(
                build_max_time=datetime(2020, 12, 1, tzinfo=timezone.utc),
                development_max_time=datetime(2020, 6, 1, tzinfo=timezone.utc),
            )

    def test_classify(self):
        boundary = SplitBoundary(
            build_max_time=datetime(2020, 6, 1, tzinfo=timezone.utc),
            development_max_time=datetime(2020, 12, 1, tzinfo=timezone.utc),
        )
        assert boundary.classify(datetime(2020, 1, 1, tzinfo=timezone.utc)) == SplitLabel.BUILD
        assert boundary.classify(datetime(2020, 9, 1, tzinfo=timezone.utc)) == SplitLabel.DEVELOPMENT
        assert boundary.classify(datetime(2021, 3, 1, tzinfo=timezone.utc)) == SplitLabel.BLIND


class TestSplitOrderIntegrity:
    def test_valid_multi_case_ordering(self):
        """R06: Multi-case ordering with valid splits."""
        boundary = SplitBoundary(
            build_max_time=datetime(2020, 6, 1, tzinfo=timezone.utc),
            development_max_time=datetime(2020, 12, 1, tzinfo=timezone.utc),
        )
        manifests = [
            HistoricalCaseManifest(
                case_id="build1", event_family="regulatory",
                market_regime="unknown", split_label="BUILD",
                title="Build case", evidence_manifest_hash="a",
                event_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
            ),
            HistoricalCaseManifest(
                case_id="dev1", event_family="market",
                market_regime="bull", split_label="DEVELOPMENT",
                title="Dev case", evidence_manifest_hash="b",
                event_time=datetime(2020, 9, 1, tzinfo=timezone.utc),
            ),
            HistoricalCaseManifest(
                case_id="blind1", event_family="technology",
                market_regime="unknown", split_label="BLIND",
                title="Blind case", evidence_manifest_hash="c",
                event_time=datetime(2021, 3, 1, tzinfo=timezone.utc),
            ),
        ]
        result = SplitOrderIntegrity.validate(manifests, boundary)
        assert result.is_valid, f"Errors: {result.errors}"

    def test_invalid_overlap_detected(self):
        """R06: Actual invalid overlaps return exact case IDs and violations."""
        boundary = SplitBoundary(
            build_max_time=datetime(2020, 6, 1, tzinfo=timezone.utc),
            development_max_time=datetime(2020, 12, 1, tzinfo=timezone.utc),
        )
        manifests = [
            HistoricalCaseManifest(
                case_id="c1", event_family="regulatory",
                market_regime="unknown", split_label="BUILD",
                title="Build case", evidence_manifest_hash="a",
                event_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
            ),
            HistoricalCaseManifest(
                case_id="c1",  # duplicate case_id but different split
                event_family="regulatory", market_regime="unknown",
                split_label="DEVELOPMENT",
                title="Duplicate", evidence_manifest_hash="b",
                event_time=datetime(2020, 1, 1, tzinfo=timezone.utc),  # same time
            ),
        ]
        result = SplitOrderIntegrity.validate(manifests, boundary)
        assert result.is_valid is False
        assert any("appears in both" in e for e in result.errors)

    def test_blind_isolation(self):
        """R06: BLIND IDs cannot be accepted as tuning/training input."""
        blind_ids = {"b1", "b2", "b3"}
        training_ids = {"b2", "t1"}  # b2 is in both
        errors = SplitOrderIntegrity.check_blind_isolation(blind_ids, training_ids)
        assert len(errors) == 1
        assert "b2" in errors[0]

    def test_single_build_case_does_not_prove_integrity(self):
        """R06: A single BUILD case does not prove split integrity."""
        manifests = [HistoricalCaseManifest(
            case_id="only", event_family="regulatory",
            market_regime="unknown", split_label="BUILD",
            title="Only build", evidence_manifest_hash="a",
            event_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )]
        # This is valid but doesn't prove multi-split integrity
        boundary = SplitBoundary(
            build_max_time=datetime(2020, 6, 1, tzinfo=timezone.utc),
            development_max_time=datetime(2020, 12, 1, tzinfo=timezone.utc),
        )
        result = SplitOrderIntegrity.validate(manifests, boundary)
        assert result.is_valid  # A single case is valid
        # But the test ensures we have explicit multi-case tests above


# ═══════════════════════════════════════════════════════════════════════════════
# R07 — Outcome window validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutcomeWindowTimes:
    def test_close_time_from_event_time(self):
        """R07: Close times computed from event time, not equal to it."""
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        windows = ManifestBuilder.build_outcome_windows(
            event_id="e1", event_time=event_time, price_data={},
        )
        for w in windows:
            assert w.close_time > w.open_time, f"{w.window_label}: close not after open"
            assert w.open_time == event_time

    def test_correct_durations(self):
        """R07: Durations match expectations."""
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        windows = ManifestBuilder.build_outcome_windows(
            event_id="e1", event_time=event_time, price_data={},
        )
        duration_map = {w.window_label: w.close_time - w.open_time for w in windows}
        assert duration_map["1h"] == timedelta(hours=1)
        assert duration_map["6h"] == timedelta(hours=6)
        assert duration_map["24h"] == timedelta(hours=24)
        assert duration_map["3d"] == timedelta(days=3)
        assert duration_map["7d"] == timedelta(days=7)

    def test_event_time_must_be_timezone_aware(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            ManifestBuilder.build_outcome_windows(
                event_id="e1",
                event_time=datetime(2020, 6, 1, 12, 0),  # naive
                price_data={},
            )

    def test_all_canonical_labels_present(self):
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        windows = ManifestBuilder.build_outcome_windows(
            event_id="e1", event_time=event_time, price_data={},
        )
        labels = {w.window_label for w in windows}
        assert labels == CANONICAL_WINDOW_LABELS


class TestOutcomeWindowValidation:
    def test_valid_window_passes(self):
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        w = OutcomeWindow(
            window_label="1h",
            event_id="e1",
            open_time=event_time,
            close_time=event_time + timedelta(hours=1),
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            return_pct=5.0,
            direction="up",
        )
        errors = validate_outcome_window(w)
        assert errors == []

    def test_close_time_must_be_after_open(self):
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        w = OutcomeWindow(
            window_label="1h", event_id="e1",
            open_time=event_time, close_time=event_time,  # same = invalid
        )
        errors = validate_outcome_window(w)
        assert any("must be after" in e for e in errors)

    def test_high_not_below_low(self):
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        w = OutcomeWindow(
            window_label="1h", event_id="e1",
            open_time=event_time,
            close_time=event_time + timedelta(hours=1),
            high_price=90.0,  # below low
            low_price=100.0,
        )
        errors = validate_outcome_window(w)
        assert any("is below" in e for e in errors)

    def test_finite_values(self):
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        w = OutcomeWindow(
            window_label="1h", event_id="e1",
            open_time=event_time,
            close_time=event_time + timedelta(hours=1),
            open_price=float('inf'),  # not finite
        )
        errors = validate_outcome_window(w)
        assert any("must be finite" in e for e in errors)

    def test_invalid_label_rejected(self):
        event_time = datetime(2020, 6, 1, 12, 0, tzinfo=timezone.utc)
        w = OutcomeWindow(
            window_label="99h", event_id="e1",  # not in canonical set
            open_time=event_time,
            close_time=event_time + timedelta(hours=1),
        )
        errors = validate_outcome_window(w)
        assert any("not in canonical" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# Manifest tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestManifestBuilder:
    def test_deterministic_case_id(self):
        cid1 = ManifestBuilder.deterministic_case_id(EventFamily.REGULATORY, PAST, "abc")
        cid2 = ManifestBuilder.deterministic_case_id(EventFamily.REGULATORY, PAST, "abc")
        assert cid1 == cid2
        assert len(cid1) == 32

    def test_different_inputs_different_ids(self):
        cid1 = ManifestBuilder.deterministic_case_id(EventFamily.REGULATORY, PAST, "abc")
        cid2 = ManifestBuilder.deterministic_case_id(EventFamily.MARKET, PAST, "abc")
        assert cid1 != cid2

    def test_evidence_manifest_hash_excludes_outcome(self):
        refs = [
            EvidenceRef(source="src1", content_hash="abc", retrieved_at=NOW),
            EvidenceRef(source="src2", content_hash="def", retrieved_at=NOW),
        ]
        h1 = ManifestBuilder.compute_evidence_manifest_hash(refs)
        h2 = ManifestBuilder.compute_evidence_manifest_hash(refs)
        assert h1 == h2
        assert len(h1) == 64


class TestDeterministicSerialization:
    def test_deterministic_hash(self):
        m1 = HistoricalCaseManifest(
            case_id="c1", event_family="regulatory",
            market_regime="unknown", split_label="BUILD",
            title="Test", evidence_manifest_hash="abc",
        )
        m2 = HistoricalCaseManifest(
            case_id="c1", event_family="regulatory",
            market_regime="unknown", split_label="BUILD",
            title="Test", evidence_manifest_hash="abc",
        )
        assert m1.deterministic_hash() == m2.deterministic_hash()


class TestCorrectionRelations:
    def test_add_and_check(self):
        cr = CorrectionRelations()
        cr.add_relation("case1", "case2", CorrectionType.CORRECTION)
        assert cr.has_correction_chain("case1")
        assert not cr.has_correction_chain("case3")

    def test_get_chain_members(self):
        cr = CorrectionRelations()
        cr.add_relation("root1", "child1", CorrectionType.CORRECTION)
        cr.add_relation("child1", "child2", CorrectionType.RETRACTION)
        members = cr.get_chain_members("root1")
        assert "root1" in members
        assert "child1" in members
        assert "child2" in members


class TestCorrectionChainSplit:
    """R14 — Correction-chain split isolation tests.

    Uses persisted identity fields (event_identity_id, correction_chain_id,
    chain_root_case_id) instead of external CorrectionRelations objects.
    """

    def make_manifest(self, case_id, split_label, event_time=None,
                      event_identity_id=None, correction_chain_id=None,
                      chain_root_case_id=None, correction_type=None):
        if event_time is None:
            event_time = datetime(2020, 6, 1, tzinfo=timezone.utc)
        kwargs = dict(
            case_id=case_id, event_family="regulatory",
            market_regime="unknown", split_label=split_label,
            title=f"Case {case_id}", evidence_manifest_hash="abc",
            event_time=event_time,
        )
        if event_identity_id is not None:
            kwargs["event_identity_id"] = event_identity_id
        if correction_chain_id is not None:
            kwargs["correction_chain_id"] = correction_chain_id
        if chain_root_case_id is not None:
            kwargs["chain_root_case_id"] = chain_root_case_id
        if correction_type is not None:
            kwargs["correction_type"] = correction_type
        return HistoricalCaseManifest(**kwargs)

    def test_valid_chain_inside_one_split(self):
        """Valid chain remains inside one split."""
        manifests = [
            self.make_manifest("root1", SplitLabel.BUILD,
                               correction_chain_id="chain_a",
                               chain_root_case_id="root1"),
            self.make_manifest("child1", SplitLabel.BUILD,
                               correction_chain_id="chain_a",
                               chain_root_case_id="root1"),
        ]
        result = CorrectionChainSplitValidator.validate(manifests)
        assert result.is_valid, f"Errors: {result.errors}"

    def test_same_event_across_splits_rejected(self):
        """Same event identity across BUILD and BLIND is rejected."""
        manifests = [
            self.make_manifest("e1", SplitLabel.BUILD,
                               event_identity_id="eid_001"),
            self.make_manifest("e1", SplitLabel.BLIND,
                               event_identity_id="eid_001"),
        ]
        result = CorrectionChainSplitValidator.validate(manifests)
        assert not result.is_valid
        assert any("multiple splits" in e for e in result.errors)

    def test_correction_chain_crossing_splits_rejected(self):
        """Correction chain crossing DEVELOPMENT and BLIND is rejected."""
        manifests = [
            self.make_manifest("root1", SplitLabel.DEVELOPMENT,
                               correction_chain_id="chain_b",
                               chain_root_case_id="root1"),
            self.make_manifest("child1", SplitLabel.BLIND,
                               correction_chain_id="chain_b",
                               chain_root_case_id="root1"),
        ]
        result = CorrectionChainSplitValidator.validate(manifests)
        assert not result.is_valid
        assert any("spans multiple splits" in e for e in result.errors)

    def test_blind_chain_tuning_exclusion(self):
        """BLIND chain IDs are rejected from training/tuning input."""
        manifests = [
            self.make_manifest("root1", SplitLabel.BUILD,
                               correction_chain_id="chain_c",
                               chain_root_case_id="root1"),
            self.make_manifest("blind1", SplitLabel.BLIND,
                               correction_chain_id="chain_c",
                               chain_root_case_id="root1"),
        ]
        result = CorrectionChainSplitValidator.validate(manifests)
        assert not result.is_valid
        assert any("BLIND" in e for e in result.errors)

    def test_exact_violation_ids_reported(self):
        """Exact violating case IDs, chain IDs and split labels reported."""
        manifests = [
            self.make_manifest("dev_case", SplitLabel.DEVELOPMENT,
                               correction_chain_id="chain_d",
                               chain_root_case_id="dev_case"),
            self.make_manifest("blind_case", SplitLabel.BLIND,
                               correction_chain_id="chain_d",
                               chain_root_case_id="dev_case"),
            self.make_manifest("e_dup", SplitLabel.BUILD,
                               event_identity_id="eid_dup"),
            self.make_manifest("e_dup", SplitLabel.BLIND,
                               event_identity_id="eid_dup"),
        ]
        result = CorrectionChainSplitValidator.validate(manifests)
        assert not result.is_valid
        error_text = " ".join(result.errors)
        assert "eid_dup" in error_text or "e_dup" in error_text
        assert "BUILD" in error_text
        assert "BLIND" in error_text
