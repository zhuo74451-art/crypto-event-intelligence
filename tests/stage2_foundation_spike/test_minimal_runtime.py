"""Test minimal runtime — basic smoke tests."""
import os
import tempfile
from experiments.stage2_foundation_spike.minimal_runtime_spike import (
    MinimalReviewRuntime, MinimalReviewRuntime, DuplicateIdempotencyKeyError
)


def test_module_importable():
    assert MinimalReviewRuntime is not None


def test_runtime_creates_and_restores():
    """Test basic persist and checkpoint recovery."""
    import tempfile
    td = tempfile.mkdtemp()
    try:
        cp = os.path.join(td, "cp.json")
        rt = MinimalReviewRuntime(checkpoint_path=cp)
        r = rt.persist_review(review_id="r1", idempotency_key="ik1")
        assert r.idempotency_key == "ik1"
        rt.close()
        rt2 = MinimalReviewRuntime(checkpoint_path=cp)
        r2 = rt2.get_review("r1")
        assert r2 is not None
        assert r2.idempotency_key == "ik1"
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
