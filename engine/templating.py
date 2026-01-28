"""Template variable substitution for test specs."""

import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any


class TemplateEngine:
    """Handles variable substitution in test specs.

    Supports built-in variables:
    - {{uuid}} - Random UUID
    - {{timestamp}} - ISO timestamp
    - {{timestamp_unix}} - Unix timestamp
    - {{request_number}} - Current request number (1-indexed)
    - {{random_int}} - Random integer 0-999999

    Also supports:
    - Custom variables from spec.variables
    - Environment variables via {{env:VAR_NAME}}
    - TARGET_* environment variables via {{target:NAME}} (maps to TARGET_NAME)
    """

    PATTERN = re.compile(r"\{\{(\w+(?::\w+)?)\}\}")

    def __init__(self, variables: dict[str, str] | None = None):
        """Initialize with optional custom variables.

        Args:
            variables: Custom variables to use for substitution
        """
        self.variables = variables or {}

    def _get_builtin_value(self, name: str, request_number: int = 0) -> str | None:
        """Get value for a built-in variable.

        Args:
            name: Variable name
            request_number: Current request number for {{request_number}}

        Returns:
            Variable value or None if not a built-in
        """
        if name == "uuid":
            return str(uuid.uuid4())
        elif name == "timestamp":
            return datetime.now(UTC).isoformat()
        elif name == "timestamp_unix":
            return str(int(datetime.now(UTC).timestamp()))
        elif name == "request_number":
            return str(request_number)
        elif name == "random_int":
            return str(uuid.uuid4().int % 1000000)
        return None

    def _get_env_value(self, var_name: str) -> str | None:
        """Get value from environment variable.

        Args:
            var_name: Environment variable name

        Returns:
            Environment variable value or None if not set
        """
        return os.environ.get(var_name)

    def _get_target_value(self, name: str) -> str | None:
        """Get value from TARGET_* environment variable.

        Args:
            name: Target name (without TARGET_ prefix)

        Returns:
            TARGET_{name} environment variable value or None
        """
        return os.environ.get(f"TARGET_{name.upper()}")

    def substitute(
        self,
        template: str,
        request_number: int = 0,
        extra_vars: dict[str, str] | None = None,
    ) -> str:
        """Substitute variables in a template string.

        Args:
            template: String containing {{variable}} placeholders
            request_number: Current request number for {{request_number}}
            extra_vars: Additional variables for this substitution

        Returns:
            String with variables substituted
        """
        merged_vars = {**self.variables, **(extra_vars or {})}

        def replace_match(match: re.Match) -> str:
            key = match.group(1)

            # Handle prefixed variables (env:VAR, target:NAME)
            if ":" in key:
                prefix, name = key.split(":", 1)
                if prefix == "env":
                    value = self._get_env_value(name)
                    return value if value is not None else match.group(0)
                elif prefix == "target":
                    value = self._get_target_value(name)
                    return value if value is not None else match.group(0)

            # Check custom variables first
            if key in merged_vars:
                return str(merged_vars[key])

            # Check built-in variables
            builtin = self._get_builtin_value(key, request_number)
            if builtin is not None:
                return builtin

            # Return original if no match
            return match.group(0)

        return self.PATTERN.sub(replace_match, template)

    def substitute_dict(
        self,
        data: dict[str, Any],
        request_number: int = 0,
        extra_vars: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Recursively substitute variables in a dictionary.

        Args:
            data: Dictionary potentially containing template strings
            request_number: Current request number
            extra_vars: Additional variables

        Returns:
            New dictionary with substituted values
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.substitute(value, request_number, extra_vars)
            elif isinstance(value, dict):
                result[key] = self.substitute_dict(value, request_number, extra_vars)
            elif isinstance(value, list):
                result[key] = self._substitute_list(value, request_number, extra_vars)
            else:
                result[key] = value
        return result

    def _substitute_list(
        self,
        data: list[Any],
        request_number: int = 0,
        extra_vars: dict[str, str] | None = None,
    ) -> list[Any]:
        """Recursively substitute variables in a list."""
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(self.substitute(item, request_number, extra_vars))
            elif isinstance(item, dict):
                result.append(self.substitute_dict(item, request_number, extra_vars))
            elif isinstance(item, list):
                result.append(self._substitute_list(item, request_number, extra_vars))
            else:
                result.append(item)
        return result
