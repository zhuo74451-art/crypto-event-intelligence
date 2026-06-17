"""Tests for config_validator."""

from market_radar.operations.config_validator import validate_config


class TestConfigValidator:
    def test_valid_config(self):
        v = validate_config({"a": 1, "b": "x"}, required=["a"])
        assert v == []

    def test_missing_required(self):
        v = validate_config({"a": 1}, required=["a", "b"])
        assert len(v) == 1
        assert "missing" in v[0] and "b" in v[0]

    def test_allowed_fields(self):
        v = validate_config({"a": 1, "extra": 2}, allowed=["a"])
        assert len(v) == 1
        assert "extra" in v[0]

    def test_type_check_pass(self):
        v = validate_config({"age": 30}, types={"age": int})
        assert v == []

    def test_type_check_fail(self):
        v = validate_config({"age": "30"}, types={"age": int})
        assert len(v) == 1
        assert "int" in v[0] and "str" in v[0]

    def test_none_required_fails(self):
        v = validate_config({"a": None}, required=["a"])
        assert len(v) == 1

    def test_empty_config_valid(self):
        v = validate_config({}, required=[])
        assert v == []
