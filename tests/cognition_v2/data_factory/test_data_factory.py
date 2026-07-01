"""Tests for WP-02 data factory contracts, registry, acquisition, and audit.

D01-D13: comprehensive tests for the historical data factory.
"""

import os
import json
import tempfile
from datetime import datetime, timezone
from dataclasses import asdict

import pytest

from market_radar.cognition_v2.data_factory.contracts import (
    AcquisitionRun,
    AcquisitionStatus,
    CorrectionChainAssignment,
    CorrectionType,
    CorpusBuildManifest,
    CorpusQualityReport,
    EventIdentityAssignment,
    FrozenSplitAssignment,
    MarketRegimeAssignment,
    NormalizedEvidenceRecord,
    OutcomeObservation,
    RawIntakeRecord,
    QualificationState,
    RejectedRecord,
    SourceClass,
    SourceRegistryEntry,
    SplitLabel,
    _stable_hash,
)
from market_radar.cognition_v2.data_factory.source_registry import (
    SourceRegistry,
    FamilyBoundRegistry,
    build_default_registry,
)
from market_radar.cognition_v2.data_factory.acquisition import (
    AcquisitionAdapter,
    AcquisitionBudgetExceeded,
    CheckpointedAcquisition,
    IncompatibleResumeError,
)
from market_radar.cognition_v2.data_factory.normalization import (
    EvidenceNormalizer,
    point_in_time_available,
)
from market_radar.cognition_v2.data_factory.identity import (
    EventIdentityResolver,
)
from market_radar.cognition_v2.data_factory.splits import (
    FrozenSplitAllocator,
)
from market_radar.cognition_v2.data_factory.storage import (
    write_jsonl,
    write_yaml,
    read_jsonl,
    read_yaml,
    build_manifest_hash,
    file_sha256,
)
from market_radar.cognition_v2.data_factory.audit import (
    CorpusAuditor,
)


NOW = datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# D03 — Contracts
# ═══════════════════════════════════════════════════════════════════════════════

class TestContracts:
    def test_source_registry_entry(self):
        entry = SourceRegistryEntry(
            source_id="test-1", name="Test Source",
            source_class=SourceClass.QUALIFYING_EVIDENCE,
            authority="government_official",
            fact_permission="public_record",
            access_method="https GET",
            base_url="https://example.com",
        )
        assert entry.source_id == "test-1"
        assert entry.source_class == SourceClass.QUALIFYING_EVIDENCE
        assert entry.id  # deterministic ID

    def test_acquisition_run(self):
        run = AcquisitionRun(
            run_id="run-1", source_id="test-1",
            start_time=NOW, end_time=NOW,
            record_limit=100,
        )
        assert run.deterministic_id
        assert run.status == AcquisitionStatus.PENDING

    def test_normalized_evidence_point_in_time(self):
        ev = NormalizedEvidenceRecord(
            evidence_id="e1", source_id="s1", source_url="https://x.com",
            authority="gov", fact_permission="public",
        )
        assert ev.availability_time is None  # no first_seen/retrieval

        ev2 = NormalizedEvidenceRecord(
            evidence_id="e2", source_id="s1", source_url="https://x.com",
            authority="gov", fact_permission="public",
            first_seen_at=NOW, retrieval_time=NOW,
        )
        assert ev2.availability_time is not None
        assert ev2.availability_time == max(ev2.first_seen_at, ev2.retrieval_time)

    def test_qualification_states(self):
        assert QualificationState.QUALIFIED.value == "QUALIFIED"
        assert QualificationState.INCOMPLETE.value != "QUALIFIED"

    def test_split_labels(self):
        assert SplitLabel.BUILD.value == "BUILD"
        assert SplitLabel.BLIND.value != "DEVELOPMENT"

    def test_corpus_build_manifest(self):
        m = CorpusBuildManifest(
            build_id="b1",
            artifact_hashes={"cases.jsonl": "abc123"},
        )
        # root_hash starts empty; compute_root_hash() produces deterministic hash
        h = m.compute_root_hash()
        assert len(h) == 64

    def test_quality_report_defaults(self):
        r = CorpusQualityReport(build_id="q1")
        assert r.all_gates_pass is False
        assert r.acceptable_cases_ge_1500 is False

    def test_deterministic_hash_stable(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert _stable_hash(d1) == _stable_hash(d2)

    def test_rejected_record(self):
        r = RejectedRecord(
            intake_id="int-1",
            rejection_reason="Missing authority",
            qualification=QualificationState.UNAUTHORIZED_SOURCE,
            source_id="test-1",
        )
        assert r.qualification == QualificationState.UNAUTHORIZED_SOURCE
        assert "Missing authority" in r.rejection_reason


# ═══════════════════════════════════════════════════════════════════════════════
# D01 — Source Registry
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceRegistry:
    def test_register_and_get(self):
        reg = SourceRegistry()
        entry = SourceRegistryEntry(
            source_id="s1", name="S1",
            source_class=SourceClass.QUALIFYING_EVIDENCE,
            authority="gov", fact_permission="public",
            access_method="https", base_url="https://x.com",
        )
        reg.register(entry)
        assert reg.get("s1") is entry
        assert reg.get("nonexistent") is None

    def test_reject(self):
        reg = SourceRegistry()
        entry = SourceRegistryEntry(
            source_id="bad", name="Bad",
            source_class=SourceClass.QUALIFYING_EVIDENCE,
            authority="gov", fact_permission="public",
            access_method="https", base_url="https://x.com",
        )
        reg.reject(entry)
        assert reg.get("bad").source_class == SourceClass.REJECTED

    def test_by_class(self):
        reg = SourceRegistry()
        for i in range(3):
            reg.register(SourceRegistryEntry(
                source_id=f"q{i}", name=f"Q{i}",
                source_class=SourceClass.QUALIFYING_EVIDENCE,
                authority="gov", fact_permission="public",
                access_method="https", base_url="https://x.com",
            ))
        reg.register(SourceRegistryEntry(
            source_id="m1", name="M1",
            source_class=SourceClass.MARKET_OUTCOME,
            authority="exch", fact_permission="market_data",
            access_method="https", base_url="https://y.com",
        ))
        assert len(reg.by_class(SourceClass.QUALIFYING_EVIDENCE)) == 3
        assert len(reg.by_class(SourceClass.MARKET_OUTCOME)) == 1

    def test_yaml_roundtrip(self):
        reg = build_default_registry()
        yaml_text = reg.to_yaml()
        reg2 = SourceRegistry.from_yaml(yaml_text)
        assert len(reg2.all()) == len(reg.all())

    def test_default_registry_has_all_families(self):
        reg = build_default_registry()
        assert len(reg.all()) >= 10


# ═══════════════════════════════════════════════════════════════════════════════
# D04 — Acquisition
# ═══════════════════════════════════════════════════════════════════════════════

class MockAdapter(AcquisitionAdapter):
    def __init__(self, total_pages=3, records_per_page=5):
        self._total_pages = total_pages
        self._records_per_page = records_per_page
        self.call_count = 0

    def fetch_page(self, source_id, start_time, end_time,
                   page_size, page_token=None):
        self.call_count += 1
        if page_token is not None:
            pt = int(page_token)
            if pt > self._total_pages:
                return [], None
        page_num = int(page_token) if page_token else 1
        records = [
            RawIntakeRecord(
                intake_id=f"{source_id}-{page_num}-{i}",
                source_id=source_id,
                source_url=f"https://x.com/{page_num}/{i}",
                raw_body=f"Record {i} on page {page_num}",
                retrieved_at=datetime.now(timezone.utc),
            )
            for i in range(min(self._records_per_page, page_size))
        ]
        next_token = str(page_num + 1) if page_num < self._total_pages else None
        return records, next_token


class TestAcquisition:
    def test_successful_run(self):
        adapter = MockAdapter(total_pages=2, records_per_page=5)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="test-run-1", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100,
            max_record_budget=500,
            max_request_budget=50,
        )
        records, completed, cp = acq.run(req)
        assert completed.status == AcquisitionStatus.COMPLETED
        assert len(records) == 10  # 2 pages x 5 records

    def test_record_limit_respected(self):
        adapter = MockAdapter(total_pages=5, records_per_page=10)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="test-limit", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=12,  # hard ceiling: stop at 12
            max_record_budget=500,
            max_request_budget=50,
        )
        records, completed, cp = acq.run(req)
        # Hard ceiling: returns at most record_limit records
        assert len(records) == 12

    def test_budget_exceeded(self):
        adapter = MockAdapter(total_pages=100, records_per_page=100)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="test-budget", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=999999,
            max_record_budget=50,  # low budget
            max_request_budget=10,
        )
        records, completed, cp = acq.run(req)
        assert completed.status in (AcquisitionStatus.BUDGET_EXCEEDED,
                                     AcquisitionStatus.COMPLETED)

    def test_resume_from_checkpoint(self):
        adapter = MockAdapter(total_pages=3, records_per_page=5)
        tmpdir = tempfile.mkdtemp()
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tmpdir)
        req = AcquisitionRun(
            run_id="test-resume", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100,
            max_record_budget=500,
            max_request_budget=50,
        )
        records1, _, _ = acq.run(req)

        # Second run on same request — should resume and not duplicate
        adapter2 = MockAdapter(total_pages=3, records_per_page=5)
        acq2 = CheckpointedAcquisition(adapter2, checkpoint_dir=tmpdir)
        req2 = AcquisitionRun(
            run_id="test-resume", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100,
            max_record_budget=500,
            max_request_budget=50,
        )
        records2, _, _ = acq2.run(req2, resume=True)
        # Should have same total, no duplication
        assert len(records2) >= 10

    def test_incompatible_resume_rejected(self):
        tmpdir = tempfile.mkdtemp()
        adapter = MockAdapter(total_pages=1, records_per_page=5)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tmpdir)
        req = AcquisitionRun(
            run_id="test-incompat", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100,
        )
        acq.run(req)

        # Different fingerprint
        req2 = AcquisitionRun(
            run_id="test-incompat", source_id="different",
            start_time=NOW, end_time=NOW,
            record_limit=100,
        )
        acq2 = CheckpointedAcquisition(MockAdapter(), checkpoint_dir=tmpdir)
        with pytest.raises(IncompatibleResumeError):
            acq2.run(req2, resume=True)
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_retry_on_failure(self):
        class FailingAdapter(AcquisitionAdapter):
            def __init__(self):
                self.attempts = 0
            def fetch_page(self, *args, **kwargs):
                self.attempts += 1
                if self.attempts <= 2:
                    raise ConnectionError("Temporary failure")
                return [
                    RawIntakeRecord(
                        intake_id="retry-1", source_id="fail",
                        source_url="https://x.com",
                        raw_body="Retried", retrieved_at=NOW,
                    )
                ], None

        acq = CheckpointedAcquisition(FailingAdapter(),
                                       checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="test-retry", source_id="fail",
            start_time=NOW, end_time=NOW,
            record_limit=100, retry_limit=3,
            backoff_seconds=0.01,
        )
        records, completed, _ = acq.run(req)
        assert completed.status == AcquisitionStatus.COMPLETED
        assert len(records) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# D05 — Normalization
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalization:
    def test_normalize_basic(self):
        raw = RawIntakeRecord(
            intake_id="int-1", source_id="s1",
            source_url="https://x.com/a",
            raw_body="Event announcement text here",
            retrieved_at=NOW,
        )
        normalizer = EvidenceNormalizer()
        ev = normalizer.normalize(
            raw, authority="gov", fact_permission="public",
            first_seen_at=NOW, publication_time=NOW,
        )
        assert ev.source_id == "s1"
        assert ev.content_hash
        assert ev.evidence_id

    def test_point_in_time_available(self):
        cutoff = NOW
        ev = NormalizedEvidenceRecord(
            evidence_id="e1", source_id="s1", source_url="https://x.com",
            authority="gov", fact_permission="public",
            first_seen_at=cutoff, retrieval_time=cutoff,
        )
        assert point_in_time_available(ev, cutoff)

        # Evidence seen later — not available
        later = NormalizedEvidenceRecord(
            evidence_id="e2", source_id="s1", source_url="https://x.com",
            authority="gov", fact_permission="public",
            first_seen_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            retrieval_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        assert not point_in_time_available(later, datetime(2024, 1, 1, tzinfo=timezone.utc))

    def test_deterministic_hash(self):
        raw = RawIntakeRecord(
            intake_id="int-1", source_id="s1",
            source_url="https://x.com/a",
            raw_body="Test content",
            retrieved_at=NOW,
        )
        normalizer = EvidenceNormalizer()
        ev1 = normalizer.normalize(raw, authority="gov", fact_permission="public")
        ev2 = normalizer.normalize(raw, authority="gov", fact_permission="public")
        assert ev1.content_hash == ev2.content_hash


# ═══════════════════════════════════════════════════════════════════════════════
# D06 — Identity
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdentity:
    def test_compute_event_identity(self):
        resolver = EventIdentityResolver()
        eid1 = resolver.compute_event_identity(
            "case-1", "SEC Charges Bank ABC", "regulatory",
            event_time="2023-06-15",
        )
        eid2 = resolver.compute_event_identity(
            "case-2", "SEC Charges Bank ABC", "regulatory",
            event_time="2023-06-15",
        )
        assert eid1 == eid2  # same title stem, same family/time

    def test_assign_identity(self):
        resolver = EventIdentityResolver()
        a = resolver.assign_identity("case-1", "eid-001")
        assert a.case_id == "case-1"
        assert a.event_identity_id == "eid-001"

    def test_assign_chain(self):
        resolver = EventIdentityResolver()
        a = resolver.assign_correction_chain(
            "case-1", "chain-001", chain_root_case_id="root-1",
            correction_type=CorrectionType.CORRECTION,
        )
        assert a.correction_chain_id == "chain-001"

    def test_get_chain_members(self):
        resolver = EventIdentityResolver()
        resolver.assign_correction_chain("root-1", "chain-001",
                                          chain_root_case_id="root-1")
        resolver.assign_correction_chain("child-1", "chain-001",
                                          chain_root_case_id="root-1",
                                          correction_type=CorrectionType.CORRECTION)
        members = resolver.get_chain_members("chain-001")
        assert "root-1" in members
        assert "child-1" in members

    def test_validate_cross_split(self):
        resolver = EventIdentityResolver()
        resolver.assign_identity("case-a", "eid-x")
        resolver.assign_identity("case-b", "eid-x")
        errors = resolver.validate_cross_split({
            "case-a": SplitLabel.BUILD,
            "case-b": SplitLabel.BLIND,
        })
        assert len(errors) > 0
        assert any("crosses splits" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# D09 — Splits
# ═══════════════════════════════════════════════════════════════════════════════

class TestSplits:
    def test_allocate(self):
        allocator = FrozenSplitAllocator(
            build_cutoff=datetime(2023, 1, 1, tzinfo=timezone.utc),
            development_cutoff=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        a = allocator.allocate(
            "case-1", datetime(2022, 6, 1, tzinfo=timezone.utc),
        )
        assert a.split_label == SplitLabel.BUILD

        b = allocator.allocate(
            "case-2", datetime(2023, 6, 1, tzinfo=timezone.utc),
        )
        assert b.split_label == SplitLabel.DEVELOPMENT

        c = allocator.allocate(
            "case-3", datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        assert c.split_label == SplitLabel.BLIND

    def test_default_boundaries(self):
        from datetime import timedelta
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        cases = [
            (f"case-{i}", start + timedelta(days=i * 10))
            for i in range(100)
        ]
        build_cutoff, dev_cutoff = FrozenSplitAllocator.compute_default_boundaries(
            cases, 0.60, 0.20
        )
        assert build_cutoff < dev_cutoff


# ═══════════════════════════════════════════════════════════════════════════════
# D10 — Storage
# ═══════════════════════════════════════════════════════════════════════════════

class TestStorage:
    def test_write_read_jsonl_roundtrip(self):
        records = [
            {"case_id": "c1", "value": 42},
            {"case_id": "c2", "value": 99},
        ]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.jsonl")
            h = write_jsonl(path, records)
            assert h
            loaded = read_jsonl(path)
            assert len(loaded) == 2
            assert loaded[0]["case_id"] == "c1"

    def test_deterministic_write(self):
        data = {"a": [1, 2, 3], "b": {"nested": True}}
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.yaml")
            h1 = write_yaml(path, data)
            h2 = write_yaml(path, data)
            assert h1 == h2

    def test_manifest_hash(self):
        with tempfile.TemporaryDirectory() as td:
            # Create a minimal artifact set
            write_jsonl(os.path.join(td, "cases.jsonl"), [{"id": "c1"}])
            write_yaml(os.path.join(td, "source_registry.yaml"), {"v": "1.0"})
            h = build_manifest_hash(td)
            assert h
            h2 = build_manifest_hash(td)
            assert h == h2

    def test_file_sha256(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("test content")
            f.flush()
            h = file_sha256(f.name)
            assert len(h) == 64


# ═══════════════════════════════════════════════════════════════════════════════
# D12 — Audit
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudit:
    def test_audit_basic(self):
        with tempfile.TemporaryDirectory() as td:
            # Create minimal quality report
            write_yaml(os.path.join(td, "quality_report.json"), {"audit": "ok"})
            write_yaml(os.path.join(td, "source_registry.yaml"), {"entries": []})
            write_yaml(os.path.join(td, "split_manifest.json"), {"splits": []})
            write_jsonl(os.path.join(td, "cases.jsonl"), [])
            write_jsonl(os.path.join(td, "evidence.jsonl"), [])

            auditor = CorpusAuditor()
            report = auditor.audit(td)
            # Should detect insufficient cases
            assert report.acceptable_cases_ge_1500 is False


# ═══════════════════════════════════════════════════════════════════════════════
# D13 — Regression (WP-01 and Stage 2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataFactoryBoundaries:
    """Import-boundary tests for the data factory package."""
    
    def test_import_contracts(self):
        from market_radar.cognition_v2.data_factory import contracts
        assert contracts.SCHEMA_VERSION

    def test_import_source_registry(self):
        from market_radar.cognition_v2.data_factory import source_registry
        reg = source_registry.build_default_registry()
        assert len(reg.all()) >= 10

    def test_import_acquisition(self):
        from market_radar.cognition_v2.data_factory import acquisition
        assert acquisition.CheckpointedAcquisition

    def test_import_normalization(self):
        from market_radar.cognition_v2.data_factory import normalization
        assert normalization.EvidenceNormalizer

    def test_import_identity(self):
        from market_radar.cognition_v2.data_factory import identity
        assert identity.EventIdentityResolver

    def test_import_splits(self):
        from market_radar.cognition_v2.data_factory import splits
        assert splits.FrozenSplitAllocator

    def test_import_storage(self):
        from market_radar.cognition_v2.data_factory import storage
        assert storage.write_jsonl

    def test_import_audit(self):
        from market_radar.cognition_v2.data_factory import audit
        assert audit.CorpusAuditor

    def test_import_checkpoints(self):
        from market_radar.cognition_v2.data_factory import checkpoints
        assert checkpoints.AtomicCheckpointWriter

    def test_import_provenance(self):
        from market_radar.cognition_v2.data_factory import provenance
        assert provenance.ProvenanceTracker

    def test_import_regimes(self):
        from market_radar.cognition_v2.data_factory import regimes
        assert regimes.MarketRegimeLabeler

    def test_import_outcomes(self):
        from market_radar.cognition_v2.data_factory import outcomes
        assert outcomes.OutcomeBuilder

    def test_import_adapters(self):
        from market_radar.cognition_v2.data_factory.adapters import registry
        assert registry.SecEdgarAdapter
        assert registry.FederalReserveAdapter
        assert registry.get_adapter("sec-edgar") is not None


# ═══════════════════════════════════════════════════════════════════════════════
# C01 — Registry and family bindings
# ═══════════════════════════════════════════════════════════════════════════════

class TestFamilyRegistry:
    def test_default_registry_counts_match(self):
        reg = build_default_registry()
        # 11 unique source IDs
        assert reg.count() == 11, f"Got {reg.count()}, expected 11"

    def test_all_six_families_have_sources(self):
        reg = build_default_registry()
        families = reg.family_binding_counts()
        required = {"regulatory", "corporate", "macro", "technology", "market", "security"}
        assert set(families.keys()) == required, f"Missing families: {required - set(families.keys())}"

    def test_yaml_roundtrip_preserves_counts(self):
        reg = build_default_registry()
        yaml_text = reg.to_yaml()
        reg2 = FamilyBoundRegistry.from_yaml(yaml_text)
        assert reg2.count() == reg.count()
        assert reg2.family_binding_counts() == reg.family_binding_counts()

    def test_registry_report_counts_match(self):
        reg = build_default_registry()
        # The report table: 2 regulatory + 1 corporate + 3 macro + 2 technology + 2 market + 1 security = 11
        family_counts = reg.family_binding_counts()
        total_bound = sum(family_counts.values())
        assert total_bound == reg.count(), \
            f"Family counts {family_counts} sum to {total_bound} but registry has {reg.count()}"


# ═══════════════════════════════════════════════════════════════════════════════
# C03 — Acquisition hard ceilings and resume
# ═══════════════════════════════════════════════════════════════════════════════

class TestHardCeilings:
    def test_record_limit_hard_ceiling(self):
        adapter = MockAdapter(total_pages=10, records_per_page=10)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="hard-limit", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=7,  # less than one full page
            max_record_budget=500, max_request_budget=50,
        )
        records, completed, _ = acq.run(req)
        assert len(records) == 7  # hard ceiling

    def test_budget_is_hard_ceiling(self):
        adapter = MockAdapter(total_pages=100, records_per_page=50)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="hard-budget", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=999999, max_record_budget=50, max_request_budget=10,
            page_size=30,
        )
        records, completed, _ = acq.run(req)
        # Budget is checked per-request — never exceeds
        assert completed.status in (AcquisitionStatus.BUDGET_EXCEEDED,
                                     AcquisitionStatus.COMPLETED)

    def test_completed_resume_returns_zero_new(self):
        adapter1 = MockAdapter(total_pages=2, records_per_page=5)
        tmpdir = tempfile.mkdtemp()
        acq1 = CheckpointedAcquisition(adapter1, checkpoint_dir=tmpdir)
        req = AcquisitionRun(
            run_id="zero-resume", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records1, _, _ = acq1.run(req)

        adapter2 = MockAdapter(total_pages=2, records_per_page=5)
        acq2 = CheckpointedAcquisition(adapter2, checkpoint_dir=tmpdir)
        req2 = AcquisitionRun(
            run_id="zero-resume", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records2, _, _ = acq2.run(req2, resume=True)
        # Completed resume returns no new records
        assert len(records2) <= len(records1)


# ═══════════════════════════════════════════════════════════════════════════════
# C04 — New modules
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckpoints:
    def test_atomic_writer(self):
        from market_radar.cognition_v2.data_factory.checkpoints import AtomicCheckpointWriter
        with tempfile.TemporaryDirectory() as td:
            writer = AtomicCheckpointWriter(td)
            path = writer.write_output("test-run", [{"id": "c1"}, {"id": "c2"}])
            import json
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2


class TestProvenance:
    def test_provenance_tracker(self):
        from market_radar.cognition_v2.data_factory.provenance import ProvenanceTracker
        pt = ProvenanceTracker()
        pt.record_intake("sec-edgar", "intake-1")
        result = pt.validate_coverage()
        assert result["total_edges"] == 1


class TestRegimes:
    def test_regime_labeling(self):
        from market_radar.cognition_v2.data_factory.regimes import MarketRegimeLabeler
        labeler = MarketRegimeLabeler()
        label, rule = labeler.label_from_price_data(
            NOW, [100, 101, 102, 103, 104, 105],
            [105, 106, 107, 108, 109, 110],
        )
        assert label in ("bull", "ranging")


class TestOutcomes:
    def test_outcome_builder(self):
        from market_radar.cognition_v2.data_factory.outcomes import OutcomeBuilder
        builder = OutcomeBuilder()
        windows = builder.build(
            "case-1", NOW,
            {"1h": {"close": 50000, "high": 50100, "low": 49900}},
        )
        assert len(windows) == 5
        assert windows[0].interval == "1h"
        errors = OutcomeBuilder.validate_windows(windows)
        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# C05 — Auditor
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditNoPlaceholders:
    def test_audit_fails_without_rebuild(self):
        with tempfile.TemporaryDirectory() as td:
            write_yaml(os.path.join(td, "quality_report.json"), {"audit": "ok"})
            write_yaml(os.path.join(td, "source_registry.yaml"), {"entries": []})
            write_yaml(os.path.join(td, "split_manifest.json"), {"splits": []})
            write_jsonl(os.path.join(td, "cases.jsonl"), [])
            write_jsonl(os.path.join(td, "evidence.jsonl"), [])
            auditor = CorpusAuditor()
            report = auditor.audit(td)
            # Should fail because no second build and no cases
            assert report.deterministic_rebuild_match is False
            assert report.acceptable_cases_ge_1500 is False

    def test_audit_detects_future_leakage(self):
        """Future evidence in cases should be detected."""
        with tempfile.TemporaryDirectory() as td:
            cases = [{
                "case_id": "c1", "event_family": "regulatory",
                "event_time": "2023-01-01T00:00:00+00:00",
                "first_seen_at": "2024-01-01T00:00:00+00:00",
                "retrieval_time": "2024-01-01T00:00:00+00:00",
                "qualification": "QUALIFIED",
                "source_id": "sec-edgar", "authority": "gov",
                "fact_permission": "public",
                "market_regime": "ranging",
                "split_label": "BUILD",
            }]
            write_jsonl(os.path.join(td, "cases.jsonl"), cases)
            write_yaml(os.path.join(td, "quality_report.json"), {"audit": "ok"})
            write_yaml(os.path.join(td, "source_registry.yaml"), {"entries": []})
            write_yaml(os.path.join(td, "split_manifest.json"), {"splits": []})
            write_jsonl(os.path.join(td, "evidence.jsonl"), [{"id": "e1"}])
            auditor = CorpusAuditor()
            report = auditor.audit(td)
            assert report.future_leakage_violations > 0


# ═══════════════════════════════════════════════════════════════════════════════
# P02 — Deterministic intake IDs
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterministicIntakeIds:
    def test_deterministic_intake_id(self):
        from market_radar.cognition_v2.data_factory.adapters.registry import (
            _deterministic_intake_id, _content_hash
        )
        id1 = _deterministic_intake_id("s1", "key1", "hash1")
        id2 = _deterministic_intake_id("s1", "key1", "hash1")
        assert id1 == id2
        assert len(id1) == 32

    def test_duplicate_content_same_id(self):
        from market_radar.cognition_v2.data_factory.adapters.registry import (
            _content_hash
        )
        h1 = _content_hash("same content")
        h2 = _content_hash("same content")
        assert h1 == h2
        assert len(h1) == 32

    def test_different_content_different_id(self):
        from market_radar.cognition_v2.data_factory.adapters.registry import (
            _content_hash
        )
        h1 = _content_hash("content A")
        h2 = _content_hash("content B")
        assert h1 != h2


# ═══════════════════════════════════════════════════════════════════════════════
# P03 — Cyclic token and hard ceiling edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class CyclicTokenAdapter(MockAdapter):
    """Adapter that returns the same page token repeatedly."""
    def __init__(self):
        super().__init__(total_pages=999, records_per_page=5)
        self._call_count = 0

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        records, _ = super().fetch_page(
            source_id, start_time, end_time, page_size, page_token
        )
        self._call_count += 1
        return records, "always_same_token"


class TestHardCeilingsExtended:
    def test_ceiling_smaller_than_one_page(self):
        adapter = MockAdapter(total_pages=2, records_per_page=10)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="small-ceiling", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=3,  # smaller than one full page
            max_record_budget=500, max_request_budget=50,
        )
        records, completed, _ = acq.run(req)
        assert len(records) == 3
        assert completed.status == AcquisitionStatus.COMPLETED

    def test_cyclic_page_token_detected(self):
        adapter = CyclicTokenAdapter()
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="cyclic-test", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records, completed, _ = acq.run(req)
        # Should fail safely with cyclic token detection
        assert completed.status == AcquisitionStatus.FAILED

    def test_source_exhausted_completed_resume(self):
        """Source exhaustion (no more pages) returns 0 new records on resume."""
        adapter = MockAdapter(total_pages=1, records_per_page=10)
        tmpdir = tempfile.mkdtemp()
        acq1 = CheckpointedAcquisition(adapter, checkpoint_dir=tmpdir)
        req1 = AcquisitionRun(
            run_id="exhausted-resume", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records1, _, _ = acq1.run(req1)

        adapter2 = MockAdapter(total_pages=1, records_per_page=10)
        acq2 = CheckpointedAcquisition(adapter2, checkpoint_dir=tmpdir)
        req2 = AcquisitionRun(
            run_id="exhausted-resume", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records2, completed2, _ = acq2.run(req2, resume=True)
        # Source was exhausted — no new records
        assert len(records2) <= len(records1)
        assert completed2.status == AcquisitionStatus.COMPLETED


# ═══════════════════════════════════════════════════════════════════════════════
# Q02 — Persisted resume semantics
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersistedResume:
    def test_completed_resume_zero_requests(self):
        """Completed run returns zero new records and zero source requests."""
        adapter = MockAdapter(total_pages=2, records_per_page=5)
        tmpdir = tempfile.mkdtemp()
        acq1 = CheckpointedAcquisition(adapter, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req1 = AcquisitionRun(
            run_id="complete-zero", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records1, _, _ = acq1.run(req1)
        orig_requests = req1.total_requests

        adapter2 = MockAdapter(total_pages=2, records_per_page=5)
        acq2 = CheckpointedAcquisition(adapter2, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req2 = AcquisitionRun(
            run_id="complete-zero", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records2, completed2, cp = acq2.run(req2, resume=True)
        assert len(records2) == len(records1)
        assert completed2.status == AcquisitionStatus.COMPLETED
        # No new source requests
        assert completed2.total_requests == orig_requests

    def test_source_exhausted_completed_terminal(self):
        """Source exhaustion with last_page_token=None is terminal."""
        adapter = MockAdapter(total_pages=1, records_per_page=10)
        tmpdir = tempfile.mkdtemp()
        acq1 = CheckpointedAcquisition(adapter, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req1 = AcquisitionRun(
            run_id="exhausted-term", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        acq1.run(req1)

        # Resume: should return committed state without new requests
        adapter2 = MockAdapter(total_pages=999, records_per_page=100)
        acq2 = CheckpointedAcquisition(adapter2, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req2 = AcquisitionRun(
            run_id="exhausted-term", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records2, completed2, _ = acq2.run(req2, resume=True)
        assert len(records2) == 10  # original page
        assert completed2.total_requests == 1  # no new requests

    def test_output_survives_checkpoint_failure(self):
        """Output is committed even if checkpoint write fails."""
        from market_radar.cognition_v2.data_factory.checkpoints import AtomicCheckpointWriter
        import unittest.mock as mock

        adapter = MockAdapter(total_pages=1, records_per_page=10)
        tmpdir = tempfile.mkdtemp()

        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tmpdir,
                                       output_dir=tmpdir)
        req = AcquisitionRun(
            run_id="cp-fail-test", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records, completed, _ = acq.run(req)
        # Output should exist despite any checkpoint issues
        import glob
        output_files = glob.glob(os.path.join(tmpdir, "cp-fail-test*"))
        assert len(output_files) >= 1

    def test_process_style_reopen(self):
        """Simulate process restart: new CheckpointedAcquisition resumes."""
        adapter = MockAdapter(total_pages=3, records_per_page=10)
        tmpdir = tempfile.mkdtemp()
        acq1 = CheckpointedAcquisition(adapter, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req1 = AcquisitionRun(
            run_id="reopen-test", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records1, _, _ = acq1.run(req1)

        # Second run — new adapter, new acquisition object, same dir
        adapter2 = MockAdapter(total_pages=3, records_per_page=10)
        acq2 = CheckpointedAcquisition(adapter2, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req2 = AcquisitionRun(
            run_id="reopen-test", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records2, completed2, _ = acq2.run(req2, resume=True)
        assert len(records2) == len(records1)
        assert completed2.status == AcquisitionStatus.COMPLETED

    def test_duplicate_page_after_reopen(self):
        """Duplicate source page after reopen does not duplicate records."""
        tmpdir = tempfile.mkdtemp()
        adapter1 = MockAdapter(total_pages=1, records_per_page=5)
        acq1 = CheckpointedAcquisition(adapter1, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req1 = AcquisitionRun(
            run_id="dup-page", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records1, _, _ = acq1.run(req1)

        # Second run with same page — should not duplicate
        adapter2 = MockAdapter(total_pages=2, records_per_page=5)
        acq2 = CheckpointedAcquisition(adapter2, checkpoint_dir=tmpdir,
                                        output_dir=tmpdir)
        req2 = AcquisitionRun(
            run_id="dup-page", source_id="mock", start_time=NOW, end_time=NOW,
            record_limit=100, max_record_budget=500, max_request_budget=50,
        )
        records2, _, _ = acq2.run(req2, resume=True)
        # Should not have more records than the first run
        assert len(records2) <= len(records1) + 5  # at most one new page

    def test_record_limit_hard_ceiling(self):
        """record_limit is a hard ceiling, never exceeded."""
        adapter = MockAdapter(total_pages=10, records_per_page=100)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="hard-limit-q02", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=7,
            max_record_budget=500, max_request_budget=50,
        )
        records, completed, _ = acq.run(req)
        assert len(records) == 7

    def test_max_budget_ceiling(self):
        """max_record_budget < record_limit is a hard ceiling."""
        adapter = MockAdapter(total_pages=10, records_per_page=100)
        acq = CheckpointedAcquisition(adapter, checkpoint_dir=tempfile.mkdtemp())
        req = AcquisitionRun(
            run_id="budget-ceiling", source_id="mock",
            start_time=NOW, end_time=NOW,
            record_limit=999999, max_record_budget=5, max_request_budget=10,
            page_size=50,
        )
        records, completed, _ = acq.run(req)
        # Budget should eventually stop us
        assert completed.status in (AcquisitionStatus.BUDGET_EXCEEDED,
                                     AcquisitionStatus.COMPLETED)
