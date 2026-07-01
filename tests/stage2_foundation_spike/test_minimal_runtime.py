"""Test minimal durable runtime — SQLAlchemy-based with controlled clock."""

import os
import tempfile
import threading
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from experiments.stage2_foundation_spike.minimal_runtime_spike import (
    MinimalDurableRuntime,
    ReviewNotFoundError,
    ReviewNotClaimableError,
    DuplicateIdempotencyKeyError,
    RetryExhaustedError,
    ReviewIntent,
)


NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
PAST = NOW - timedelta(hours=2)
FUTURE = NOW + timedelta(hours=2)


@pytest.fixture
def runtime():
    td = tempfile.mkdtemp()
    db_path = os.path.join(td, "test.db")
    rt = MinimalDurableRuntime(db_path=db_path, max_retries=3)
    yield rt
    rt.close()
    try:
        os.unlink(db_path)
        os.rmdir(td)
    except Exception:
        pass



class TestPersistAndClaim:
    def test_persist_creates_review(self, runtime):
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik1", due_at=PAST)
        assert rid is not None

    def test_claim_due_atomically(self, runtime):
        runtime.persist_review(thesis_id="t1", idempotency_key="ik1", due_at=PAST)
        claimed = runtime.claim_due(NOW)
        assert claimed is not None
        assert claimed.status == "CLAIMED"

    def test_duplicate_idempotency_key_rejected(self, runtime):
        runtime.persist_review(thesis_id="t1", idempotency_key="unique", due_at=PAST)
        with pytest.raises(DuplicateIdempotencyKeyError):
            runtime.persist_review(thesis_id="t2", idempotency_key="unique", due_at=PAST)

    def test_future_due_not_claimed(self, runtime):
        runtime.persist_review(thesis_id="t1", idempotency_key="future", due_at=FUTURE)
        claimed = runtime.claim_due(NOW)
        assert claimed is None


class TestCheckpointAndRecovery:
    def test_checkpoint_persisted(self, runtime):
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_cp", due_at=PAST)
        runtime.claim_due(NOW)
        runtime.write_checkpoint(rid, step=3, retry_count=1)
        step, retry, err = runtime.resume_checkpoint(rid)
        assert step == 3
        assert retry == 1

    def test_close_and_reopen_resumes(self, runtime):
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_reopen", due_at=PAST)
        runtime.claim_due(NOW)
        runtime.write_checkpoint(rid, step=2, retry_count=0)
        runtime.close_and_reopen()
        step, retry, err = runtime.resume_checkpoint(rid)
        assert step == 2


class TestFailure:
    def test_inject_failure_increments_retry(self, runtime):
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_fail", due_at=PAST)
        runtime.claim_due(NOW)
        runtime.simulate_failure(rid)
        _, retry, err = runtime.resume_checkpoint(rid)
        assert retry == 1

    def test_retry_exhaustion(self, runtime):
        """3 retries max — 3rd call raises RetryExhaustedError."""
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_ex", due_at=PAST)
        runtime.claim_due(NOW)
        runtime.simulate_failure(rid)  # retry 1
        runtime.simulate_failure(rid)  # retry 2
        with pytest.raises(RetryExhaustedError):  # retry 3 = max
            runtime.simulate_failure(rid)


class TestCancelAndResume:
    def test_cancel_review(self, runtime):
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_cancel", due_at=PAST)
        runtime.cancel_review(rid)
        r = runtime.get_review(rid)
        assert r.status == "CANCELLED"

    def test_resume_cancelled(self, runtime):
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_resume", due_at=PAST)
        runtime.cancel_review(rid)
        runtime.resume_review(rid)
        r = runtime.get_review(rid)
        assert r.status == "PENDING"

    def test_cancel_nonexistent_raises(self, runtime):
        with pytest.raises(ReviewNotFoundError):
            runtime.cancel_review("nonexistent")


class TestDuplicatePrevention:
    def test_has_idempotency_key(self, runtime):
        assert runtime.has_idempotency_key("missing") is False
        runtime.persist_review(thesis_id="t1", idempotency_key="exists", due_at=NOW)
        assert runtime.has_idempotency_key("exists") is True


# ════════════════════════════════════════════════════════
# R12 — Additional correctness tests
# ════════════════════════════════════════════════════════


class TestTwoClaimerRace:
    """Synchronized claim race via threading.Barrier — exactly one wins."""

    N_REPEATS = 10

    def test_two_claimers_synchronized_race(self):
        """Two threads, separate runtimes, same database, Barrier-synchronized, exactly one claims.

        Repeats N_REPEATS times to prove the result is not a scheduling accident.
        """
        for iteration in range(self.N_REPEATS):
            td = tempfile.mkdtemp()
            db_path = os.path.join(td, f"test_race_{iteration}.db")

            # Persist one PENDING review before starting threads
            rt0 = MinimalDurableRuntime(db_path=db_path)
            rt0.persist_review(
                thesis_id=f"t_race_{iteration}",
                idempotency_key=f"ik_race_{iteration}",
                due_at=PAST,
            )
            rt0.close()

            results = {}
            barrier = threading.Barrier(2)

            def _claim(claimer_id: int):
                rt = MinimalDurableRuntime(db_path=db_path)
                barrier.wait()  # both threads start here simultaneously
                claimed = rt.claim_due(NOW)
                rt.close()
                results[claimer_id] = claimed

            t1 = threading.Thread(target=_claim, args=(1,))
            t2 = threading.Thread(target=_claim, args=(2,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # Exactly one claimer must succeed
            claimed_count = sum(1 for v in results.values() if v is not None)
            assert claimed_count == 1, (
                f"Iteration {iteration}: expected exactly 1 claimer, got {claimed_count}"
            )
            for cid, review in results.items():
                if review is not None:
                    assert review.status == "CLAIMED", (
                        f"Iteration {iteration}: claimer {cid} got status {review.status}"
                    )

            # Exactly one DB row with CLAIMED status
            claimed_review = next(v for v in results.values() if v is not None)
            rt_check = MinimalDurableRuntime(db_path=db_path)
            review = rt_check.get_review(claimed_review.id)
            rt_check.close()
            assert review is not None
            assert review.status == "CLAIMED"

            # Cleanup
            try:
                os.unlink(db_path)
                os.rmdir(td)
            except Exception:
                pass


class TestCheckpointPreservedOnResume:
    def test_resume_preserves_checkpoint(self, runtime):
        """resume_review() must preserve the last committed checkpoint and retry count."""
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_cp_resume", due_at=PAST)
        runtime.claim_due(NOW)
        runtime.write_checkpoint(rid, step=5, retry_count=2)
        runtime.cancel_review(rid)
        runtime.resume_review(rid)
        r = runtime.get_review(rid)
        assert r.status == "PENDING"
        # Checkpoint and retry are preserved (not reset)
        assert r.checkpoint_step == 5
        assert r.retry_count == 2


class TestFailedStatePersisted:
    def test_retry_exhaustion_persists_failed_state(self, runtime):
        """After retry exhaustion, FAILED state must persist even after close/reopen."""
        rid = runtime.persist_review(thesis_id="t1", idempotency_key="ik_fail_state", due_at=PAST)
        runtime.claim_due(NOW)
        try:
            runtime.simulate_failure(rid)
            runtime.simulate_failure(rid)
            runtime.simulate_failure(rid)
        except RetryExhaustedError:
            pass
        # Verify FAILED state persisted
        r = runtime.get_review(rid)
        assert r.status == "FAILED"
        assert r.retry_count == 3
        # Close and reopen — FAILED state must survive
        runtime.close_and_reopen()
        r2 = runtime.get_review(rid)
        assert r2.status == "FAILED"
        assert r2.retry_count == 3
