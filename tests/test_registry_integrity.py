"""
Registry integrity tests.

Two categories:

1. Pattern rule path validity
   Every rule path in every pattern file must reference a valid JSON pointer
   into canonical-schema.yaml.  This catches typos and schema drift before
   they cause silent runtime bugs in the compiler.

2. Schema-defaults completeness
   Every user-settable leaf field in canonical-schema.yaml must have an
   explicit entry in config/defaults.yaml (even if the value is null).
   This catches fields added to the schema that were never given defaults,
   which would cause the compiler to treat them as missing rather than optional.

Both tests are derived entirely from the schema and pattern files — no manual
maintenance is needed.  When schema or patterns change, these tests adapt.
"""
import glob
import json
import os
from typing import Any

import pytest
import yaml

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "canonical-schema.yaml")
_DEFAULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "defaults.yaml")
_PATTERNS_DIR = os.path.join(os.path.dirname(__file__), "..", "patterns")

_RULE_FIELDS = [
    "supports_constraints", "supports_nfr",
    "requires_constraints", "requires_nfr",
    "warn_constraints", "warn_nfr",
]


# ---------------------------------------------------------------------------
# Schema path extractors
# ---------------------------------------------------------------------------

def _extract_all_valid_paths(schema_node: dict, current_path: str = "") -> set:
    """
    Return the set of all valid JSON pointer paths in the schema subtree,
    including object paths, array paths (for contains-any rules), and leaves.
    """
    if not isinstance(schema_node, dict):
        return set()

    paths = set()
    node_type = schema_node.get("type")

    if node_type == "object" and "properties" in schema_node:
        paths.add(current_path)
        for key, sub_schema in schema_node["properties"].items():
            child_path = f"{current_path}/{key}"
            paths.add(child_path)
            paths |= _extract_all_valid_paths(sub_schema, child_path)

    elif node_type == "array":
        paths.add(current_path)   # array path (used with contains-any operator)

    elif node_type in ("boolean", "string", "number", "integer"):
        paths.add(current_path)

    elif isinstance(node_type, list):
        paths.add(current_path)

    elif "anyOf" in schema_node or "oneOf" in schema_node:
        paths.add(current_path)

    elif "enum" in schema_node:
        paths.add(current_path)

    return paths


def _extract_leaf_paths_with_defaults(schema_node: dict, defaults_node: Any,
                                      current_path: str = ""):
    """
    Recursively yield (json_pointer_path, defaults_node_value) for every
    user-settable leaf field (arrays skipped, project/functional/assumptions
    sections handled by caller).
    """
    if not isinstance(schema_node, dict):
        return

    node_type = schema_node.get("type")

    if node_type == "object" and "properties" in schema_node:
        for key, sub_schema in schema_node["properties"].items():
            child_path = f"{current_path}/{key}"
            child_default = (
                defaults_node.get(key) if isinstance(defaults_node, dict) else None
            )
            yield from _extract_leaf_paths_with_defaults(
                sub_schema, child_default, child_path
            )

    elif node_type == "array":
        return   # arrays are not individually settable leaf fields

    elif node_type in ("boolean", "string", "number", "integer") or "enum" in schema_node:
        yield (current_path, defaults_node)

    elif isinstance(node_type, list):
        actual = next((t for t in node_type if t not in ("null", "array")), None)
        if actual:
            yield (current_path, defaults_node)

    elif "anyOf" in schema_node:
        non_null = [s for s in schema_node["anyOf"] if s.get("type") != "null"]
        if non_null:
            yield (current_path, defaults_node)

    elif "oneOf" in schema_node:
        non_null = [s for s in schema_node["oneOf"] if s.get("type") != "null"]
        if non_null:
            yield (current_path, defaults_node)


def _path_exists_in_dict(d: dict, pointer: str) -> bool:
    """Return True if the JSON pointer path exists as a key in d (value may be null)."""
    parts = [p for p in pointer.lstrip("/").split("/") if p]
    node = d
    for part in parts:
        if isinstance(node, dict):
            if part not in node:
                return False
            node = node[part]
        else:
            return False
    return True


# ---------------------------------------------------------------------------
# Fixtures: load schema, defaults, and patterns once
# ---------------------------------------------------------------------------

def _load_schema_and_defaults():
    with open(_SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)
    with open(_DEFAULTS_PATH) as f:
        defaults = yaml.safe_load(f)
    return schema, defaults


def _load_all_patterns():
    for fname in sorted(glob.glob(os.path.join(_PATTERNS_DIR, "*.json"))):
        yield json.load(open(fname))


# ---------------------------------------------------------------------------
# Test 1: every pattern rule path is valid
# ---------------------------------------------------------------------------

def test_pattern_rule_paths_are_valid():
    """
    Every rule path in every pattern file must reference a valid path in
    canonical-schema.yaml.

    Covers: supports_constraints, supports_nfr, requires_constraints,
            requires_nfr, warn_constraints, warn_nfr.

    If this fails, either a pattern has a typo in a rule path, or the schema
    was changed and the patterns were not updated accordingly.
    """
    schema, _ = _load_schema_and_defaults()

    # Build the set of all valid paths from the sections that rules reference
    valid_paths: set = set()
    for section in ("constraints", "nfr", "operating_model", "cost"):
        if section in schema.get("properties", {}):
            sub = schema["properties"][section]
            valid_paths |= _extract_all_valid_paths(sub, f"/{section}")

    invalid: list = []
    for pattern in _load_all_patterns():
        pid = pattern.get("id", "unknown")
        for field in _RULE_FIELDS:
            for rule in pattern.get(field, []) or []:
                path = rule.get("path", "")
                if path and path not in valid_paths:
                    invalid.append(f"{pid}.{field}: {path!r}")

    assert not invalid, (
        f"Pattern rules reference {len(invalid)} invalid path(s):\n"
        + "\n".join(f"  {e}" for e in invalid[:30])
        + (f"\n  ... and {len(invalid) - 30} more" if len(invalid) > 30 else "")
        + "\n\nEither fix the typo in the pattern or update the schema."
    )


# ---------------------------------------------------------------------------
# Test 2: every schema leaf has a default in defaults.yaml
# ---------------------------------------------------------------------------

def test_schema_leaf_has_default():
    """
    Every user-settable leaf in canonical-schema.yaml must have an explicit
    entry in config/defaults.yaml (the value may be null, but the key must
    be present).

    If this fails, add the missing field to config/defaults.yaml.

    Sections skipped (not defaulted by the compiler):
      /project, /functional, /assumptions, /patterns
    """
    schema, defaults = _load_schema_and_defaults()

    _SKIP_PREFIXES = ("/project", "/functional", "/assumptions", "/patterns")

    missing: list = []
    for path, _ in _extract_leaf_paths_with_defaults(schema, defaults):
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            continue
        if not _path_exists_in_dict(defaults, path):
            missing.append(path)

    assert not missing, (
        f"{len(missing)} schema leaf path(s) have no entry in config/defaults.yaml:\n"
        + "\n".join(f"  {p}" for p in missing)
        + "\n\nAdd defaults for these paths to config/defaults.yaml.\n"
        "The value may be null if the field is optional — the key must still be present."
    )


# ---------------------------------------------------------------------------
# Test 3: capability names use canonical vocabulary (no known aliases)
# ---------------------------------------------------------------------------

_VOCAB_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "capability-vocabulary.yaml")


def _load_alias_map():
    """
    Return a dict mapping every known alias → canonical name.
    Built from capability-vocabulary.yaml aliases lists.
    """
    with open(_VOCAB_PATH) as f:
        vocab = yaml.safe_load(f)

    alias_map = {}
    for canonical, entry in (vocab.get("capabilities") or {}).items():
        for alias in (entry.get("aliases") or []):
            alias_map[alias] = canonical
    return alias_map


def test_capability_names_use_canonical_forms():
    """
    No pattern's requires or provides may use a known alias string when a
    canonical form exists in schemas/capability-vocabulary.yaml.

    If this fails, rename the capability in the pattern to its canonical form.
    To add a new synonym pair, update capability-vocabulary.yaml first.
    """
    alias_map = _load_alias_map()
    if not alias_map:
        return  # vocabulary has no aliases yet — nothing to check

    violations: list = []
    for pattern in _load_all_patterns():
        pid = pattern.get("id", "unknown")

        for item in pattern.get("provides", []):
            cap = item.get("capability", "")
            if cap in alias_map:
                violations.append(
                    f"{pid} provides: '{cap}' — use canonical name '{alias_map[cap]}'"
                )

        for item in pattern.get("requires", []):
            cap = item.get("capability", "")
            if cap in alias_map:
                violations.append(
                    f"{pid} requires: '{cap}' — use canonical name '{alias_map[cap]}'"
                )

    assert not violations, (
        f"{len(violations)} capability name(s) use known aliases instead of canonical forms:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\n\nRename each capability to its canonical form."
        " To register a new synonym, update schemas/capability-vocabulary.yaml."
    )
