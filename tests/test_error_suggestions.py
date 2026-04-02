#!/usr/bin/env python3
"""Unit tests for _lookup_schema_field_info and _format_suggestions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.archcompiler import _lookup_schema_field_info, _format_suggestions


SCHEMA = {
    "properties": {
        "nfr": {
            "properties": {
                "rpo_minutes": {"type": "integer", "minimum": 0},
                "security": {
                    "properties": {
                        "auth": {
                            "type": "string",
                            "enum": ["oauth2_oidc", "api_key", "jwt", "mtls", "saml", "password", "n/a"]
                        },
                        "tenant_isolation": {
                            "type": "string",
                            "enum": ["shared-db-row-level", "schema-per-tenant", "per-tenant-db", "n/a", "unknown"]
                        },
                        "audit_logging": {"type": "boolean"},
                    }
                },
                "availability": {
                    "properties": {
                        "target": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                },
            }
        },
        "constraints": {
            "properties": {
                "cloud": {
                    "type": "string",
                    "enum": ["agnostic", "aws", "azure", "gcp", "on-prem"]
                }
            }
        }
    }
}


def test_enum_field_returns_pipe_joined_values():
    result = _lookup_schema_field_info(SCHEMA, "/nfr/security/auth")
    assert result == "oauth2_oidc | api_key | jwt | mtls | saml | password | n/a"


def test_integer_field_with_minimum():
    result = _lookup_schema_field_info(SCHEMA, "/nfr/rpo_minutes")
    assert result == "integer (min: 0)"


def test_number_field_with_min_and_max():
    result = _lookup_schema_field_info(SCHEMA, "/nfr/availability/target")
    assert result == "number (0–1)"


def test_boolean_field():
    result = _lookup_schema_field_info(SCHEMA, "/nfr/security/audit_logging")
    assert result == "boolean"


def test_unknown_path_returns_unknown():
    result = _lookup_schema_field_info(SCHEMA, "/nfr/nonexistent/field")
    assert result == "unknown"


def test_empty_schema_returns_unknown():
    result = _lookup_schema_field_info({}, "/nfr/security/auth")
    assert result == "unknown"


def test_constraints_enum_field():
    result = _lookup_schema_field_info(SCHEMA, "/constraints/cloud")
    assert result == "agnostic | aws | azure | gcp | on-prem"


def test_anyof_nullable_enum_returns_enum_options():
    # Fields using anyOf: [{type: string, enum: [...]}, {type: null}] should return the enum
    schema_with_anyof = {
        "properties": {
            "features": {
                "properties": {
                    "delivery": {
                        "anyOf": [
                            {"type": "string", "enum": ["at-most-once", "at-least-once", "exactly-once"]},
                            {"type": "null"},
                        ]
                    }
                }
            }
        }
    }
    result = _lookup_schema_field_info(schema_with_anyof, "/features/delivery")
    assert result == "at-most-once | at-least-once | exactly-once"


def test_format_suggestions_single_pattern_enum_gate():
    violations = [{"pid": "sec-auth-api-key", "path": "/nfr/rpo_minutes",
                   "op": ">=", "value": 5, "reason": "r"}]
    honored = {
        "sec-auth-api-key": {
            "nfr": [{"path": "/nfr/security/auth", "op": "==", "value": "api_key"}],
            "constraints": [],
        }
    }
    result = _format_suggestions(violations, honored, SCHEMA)
    assert "💡" in result
    assert "sec-auth-api-key" in result
    assert "/nfr/security/auth" in result
    assert '"api_key"' in result
    assert "oauth2_oidc" in result  # enum shown


def test_format_suggestions_two_patterns():
    violations = [
        {"pid": "p1", "path": "/nfr/rpo_minutes", "op": ">=", "value": 1, "reason": "r"},
        {"pid": "p2", "path": "/nfr/rpo_minutes", "op": ">=", "value": 5, "reason": "r"},
    ]
    honored = {
        "p1": {"nfr": [{"path": "/nfr/security/tenant_isolation", "op": "==", "value": "per-tenant-db"}], "constraints": []},
        "p2": {"nfr": [{"path": "/nfr/security/auth", "op": "==", "value": "api_key"}], "constraints": []},
    }
    result = _format_suggestions(violations, honored, SCHEMA)
    assert "p1" in result
    assert "p2" in result
    assert "per-tenant-db" in result
    assert "api_key" in result


def test_format_suggestions_nfr_threshold_shown():
    # NFR threshold rules (<=, >=) are activation gates — they SHOULD appear in suggestions
    # so the user knows what spec value triggered the pattern.
    violations = [{"pid": "p1", "path": "/nfr/rpo_minutes", "op": ">=", "value": 1, "reason": "r"}]
    honored = {
        "p1": {"nfr": [{"path": "/nfr/availability/target", "op": "<=", "value": 0.999}], "constraints": []}
    }
    result = _format_suggestions(violations, honored, SCHEMA)
    assert "p1 activated by:" in result
    assert "/nfr/availability/target" in result
    assert "threshold: <=" in result


def test_format_suggestions_nfr_gte_threshold_shown():
    # caching-required-high-read-throughput scenario: NFR >= activates, constraint fails
    violations = [{"pid": "caching-req", "path": "/constraints/features/caching", "op": "==", "value": True, "reason": "r"}]
    honored = {
        "caching-req": {
            "nfr": [{"path": "/nfr/throughput/peak_query_per_second_read", "op": ">=", "value": 200}],
            "constraints": [],
        }
    }
    result = _format_suggestions(violations, honored, {})
    assert "caching-req activated by:" in result
    assert "/nfr/throughput/peak_query_per_second_read" in result
    assert "threshold: >=" in result


def test_format_suggestions_deduplicates_pids():
    # Same pid appears twice in violations (two failing rules) → one suggestion block
    violations = [
        {"pid": "p1", "path": "/nfr/rpo_minutes", "op": ">=", "value": 1, "reason": "r"},
        {"pid": "p1", "path": "/nfr/rto_minutes", "op": ">=", "value": 5, "reason": "r"},
    ]
    honored = {
        "p1": {"nfr": [{"path": "/nfr/security/auth", "op": "==", "value": "api_key"}], "constraints": []}
    }
    result = _format_suggestions(violations, honored, SCHEMA)
    assert result.count("p1 activated by") == 1  # deduplicated


def test_format_suggestions_unknown_schema_path():
    violations = [{"pid": "p1", "path": "/nfr/rpo_minutes", "op": ">=", "value": 1, "reason": "r"}]
    honored = {
        "p1": {"nfr": [{"path": "/nfr/security/auth", "op": "==", "value": "api_key"}], "constraints": []}
    }
    result = _format_suggestions(violations, honored, {})  # empty schema
    # Gate path is still shown; "Available: unknown" is suppressed (unhelpful)
    assert "/nfr/security/auth" in result
    assert "Available: unknown" not in result


def test_format_suggestions_boolean_gate_no_available_line():
    # Boolean == gates must NOT show "Available: boolean" (redundant, unhelpful)
    violations = [{"pid": "p1", "path": "/nfr/rpo_minutes", "op": ">=", "value": 1, "reason": "r"}]
    honored = {
        "p1": {"nfr": [{"path": "/nfr/security/audit_logging", "op": "==", "value": True}], "constraints": []}
    }
    result = _format_suggestions(violations, honored, SCHEMA)
    assert "/nfr/security/audit_logging" in result
    assert "Available: boolean" not in result


def test_format_suggestions_pid_not_in_honored_rules_returns_empty():
    # pid in violations but absent from honored_rules → silent skip → empty
    violations = [{"pid": "p1", "path": "/nfr/rpo_minutes", "op": ">=", "value": 1, "reason": "r"}]
    honored = {}  # p1 not present at all
    result = _format_suggestions(violations, honored, SCHEMA)
    assert result == ""
