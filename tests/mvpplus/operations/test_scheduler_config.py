"""Tests for scheduler_config."""

from market_radar.operations.scheduler_config import SchedulerConfig, check_apscheduler_available


class TestSchedulerConfig:
    def test_disabled_by_default(self):
        cfg = SchedulerConfig()
        assert cfg.enabled is False

    def test_default_config_valid(self):
        cfg = SchedulerConfig()
        v = cfg.validate()
        assert len(v) == 0, f"default config should be valid: {v}"

    def test_enabled_triggers_violation(self):
        cfg = SchedulerConfig(enabled=True)
        v = cfg.validate()
        assert len(v) >= 1
        assert any("disabled" in vi for vi in v)

    def test_max_instances_must_be_1(self):
        cfg = SchedulerConfig(max_instances=3)
        v = cfg.validate()
        assert any("max_instances" in vi for vi in v)

    def test_coalesce_enforced(self):
        cfg = SchedulerConfig(coalesce=False)
        v = cfg.validate()
        assert any("coalesce" in vi for vi in v)

    def test_misfire_grace_time_non_negative(self):
        cfg = SchedulerConfig(misfire_grace_time=-1)
        v = cfg.validate()
        assert any("misfire_grace_time" in vi for vi in v)

    def test_check_apscheduler_available(self):
        # Should return False in clean test environment
        result = check_apscheduler_available()
        assert isinstance(result, bool)
