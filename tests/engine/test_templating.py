"""Tests for template engine."""

import os
import pytest
from unittest.mock import patch

from engine.templating import TemplateEngine


class TestTemplateEngine:
    """Tests for TemplateEngine."""

    def test_no_variables(self):
        """Test string with no variables passes through unchanged."""
        engine = TemplateEngine()
        result = engine.substitute("https://example.com/api")
        assert result == "https://example.com/api"

    def test_uuid_variable(self):
        """Test {{uuid}} generates a UUID."""
        engine = TemplateEngine()
        result = engine.substitute("https://example.com/{{uuid}}")
        # UUID has format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert len(result) == len("https://example.com/") + 36
        assert "-" in result

    def test_timestamp_variable(self):
        """Test {{timestamp}} generates ISO timestamp."""
        engine = TemplateEngine()
        result = engine.substitute("{{timestamp}}")
        # ISO timestamp contains T separator
        assert "T" in result

    def test_request_number_variable(self):
        """Test {{request_number}} substitutes correctly."""
        engine = TemplateEngine()
        result = engine.substitute("Request #{{request_number}}", request_number=42)
        assert result == "Request #42"

    def test_custom_variables(self):
        """Test custom variables are substituted."""
        engine = TemplateEngine(variables={"api_key": "secret123"})
        result = engine.substitute("Key: {{api_key}}")
        assert result == "Key: secret123"

    def test_extra_vars_override(self):
        """Test extra_vars override base variables."""
        engine = TemplateEngine(variables={"key": "base"})
        result = engine.substitute("{{key}}", extra_vars={"key": "override"})
        assert result == "override"

    def test_env_variable(self):
        """Test {{env:VAR}} reads environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "env_value"}):
            engine = TemplateEngine()
            result = engine.substitute("{{env:TEST_VAR}}")
            assert result == "env_value"

    def test_env_variable_missing(self):
        """Test missing env variable keeps placeholder."""
        engine = TemplateEngine()
        result = engine.substitute("{{env:NONEXISTENT_VAR_12345}}")
        assert result == "{{env:NONEXISTENT_VAR_12345}}"

    def test_target_variable(self):
        """Test {{target:NAME}} reads TARGET_NAME env var."""
        with patch.dict(os.environ, {"TARGET_API": "https://api.test.com"}):
            engine = TemplateEngine()
            result = engine.substitute("{{target:api}}")
            assert result == "https://api.test.com"

    def test_substitute_dict(self):
        """Test substitution in dictionaries."""
        engine = TemplateEngine(variables={"id": "123"})
        result = engine.substitute_dict({
            "url": "https://example.com/{{id}}",
            "headers": {"X-ID": "{{id}}"},
        })
        assert result["url"] == "https://example.com/123"
        assert result["headers"]["X-ID"] == "123"

    def test_substitute_nested_dict(self):
        """Test substitution in nested dictionaries."""
        engine = TemplateEngine(variables={"val": "test"})
        result = engine.substitute_dict({
            "outer": {
                "inner": "{{val}}",
            }
        })
        assert result["outer"]["inner"] == "test"

    def test_substitute_list_in_dict(self):
        """Test substitution in lists within dictionaries."""
        engine = TemplateEngine(variables={"item": "value"})
        result = engine.substitute_dict({
            "items": ["{{item}}", "static", "{{item}}"],
        })
        assert result["items"] == ["value", "static", "value"]

    def test_unknown_variable_unchanged(self):
        """Test unknown variables remain unchanged."""
        engine = TemplateEngine()
        result = engine.substitute("{{unknown_var}}")
        assert result == "{{unknown_var}}"
