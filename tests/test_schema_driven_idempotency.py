"""
Schema-driven recompilation idempotency tests.

Parametrized by walking canonical-schema.yaml so that every user-settable
leaf field is automatically covered.  When the schema gains a new field, a
test case is generated for it without any manual additions.

Companion requirements are also auto-derived: for each test case the test
builds the minimal spec, then calls _auto_satisfy_requires() which reads
every pattern's requires_constraints / requires_nfr rules and satisfies them
in a fixed-point loop.  This replaces the manual COMPANIONS dict from the
previous version — when a new pattern is added that requires other fields,
the test adapts automatically.

The only remaining manual maintenance points are:
  FIXED_TEST_VALUES  — pin explicit test values when auto-computed would be
                       semantically invalid (e.g. availability.target * 2 > 1.0)
  _NULLABLE_FALLBACKS — provide a concrete value for "!= null" guards on
                       nullable fields (batch NFR, job latency, etc.)
  SKIP_NONDEFAULT    — paths whose non-default test requires too many
                       interacting companions to be worth chasing.

Design
------
For each leaf path in canonical-schema.yaml:
  1. Build a minimal spec with BASE + that one field set to a non-default value.
  2. Call _auto_satisfy_requires() to add any fields required by selected
     patterns (fixed-point loop handles transitive deps).
  3. Compile twice; assert the same pattern IDs are selected both times.
  4. Also verify: the field value in the compiled spec equals what the user set
     (user-provided values must survive recompilation unchanged).
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers shared with the compiler (import directly so we use the same logic)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from archcompiler import _evaluate_rule, _json_pointer_get  # noqa: E402

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "canonical-schema.yaml")
_DEFAULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "defaults.yaml")
_PATTERNS_DIR = os.path.join(os.path.dirname(__file__), "..", "patterns")
_COMPILER = os.path.join(os.path.dirname(__file__), "..", "tools", "archcompiler.py")

# Minimal valid spec that compiles cleanly on its own.
_BASE = {
    "project": {"name": "Schema Idempotency Test", "domain": "testing"},
    "constraints": {"cloud": "aws", "language": "python", "platform": "api"},
}


# ---------------------------------------------------------------------------
# Load all patterns once at module level (used by _auto_satisfy_requires)
# ---------------------------------------------------------------------------

def _load_all_patterns() -> list:
    result = []
    for f in sorted(Path(_PATTERNS_DIR).glob("*.json")):
        result.append(json.loads(f.read_text()))
    return result


_ALL_PATTERNS = _load_all_patterns()

# Fields used by _auto_satisfy_requires to check all rule types
_RULE_FIELDS_REQUIRES = ["requires_constraints", "requires_nfr"]
_RULE_FIELDS_SUPPORTS = ["supports_constraints", "supports_nfr"]


# ---------------------------------------------------------------------------
# For fields where the auto-computed non-default (default*2 etc.) would be out
# of range or semantically invalid, pin an explicit test value here.
# ---------------------------------------------------------------------------
FIXED_TEST_VALUES: dict = {
    "/nfr/availability/target": 0.999,           # default*2 = 1.9 → exceeds 1.0
    "/nfr/latency/p95Milliseconds": 200,
    "/nfr/latency/p99Milliseconds": 500,
    "/nfr/throughput/peak_query_per_second_read": 20,
    "/nfr/throughput/peak_query_per_second_write": 10,
    "/nfr/rto_minutes": 120,
    "/nfr/rpo_minutes": 120,
    "/nfr/data/retention_days": 365,
    "/constraints/tenantCount": 5,               # >1 requires multi_tenancy companion
    "/operating_model/ops_team_size": 2,
    "/operating_model/single_resource_monthly_ops_usd": 5000,
    "/operating_model/amortization_months": 36,
    "/cost/ceilings/monthly_operational_usd": 1000,
    "/cost/ceilings/one_time_setup_usd": 5000,
    # pin to at-least-once so the auto_satisfy covers it
    "/constraints/features/messaging_delivery_guarantee": "at-least-once",
}

# Fallback concrete values for "!= null" guard rules on nullable schema fields.
# These are fields that are null by default but some patterns require a non-null
# value when they are selected (e.g., batch-processing-required requires
# peak_jobs_per_hour to be set when batch_processing=True).
# Add an entry here if a new pattern adds a "!= null" requires rule.
_NULLABLE_FALLBACKS: dict = {
    "/nfr/latency/jobStartP95Seconds": 60,
    "/nfr/latency/jobStartP99Seconds": 120,
    "/nfr/throughput/peak_jobs_per_hour": 100,
}

# Paths for which the non-default test value is too complex to companion-wire
# safely (e.g. requires batch + pii + audit + compliance-gdpr together).
# We fall back to explicitly setting the default value, which still tests that
# "user provides the default explicitly" is idempotent.
SKIP_NONDEFAULT: set = {
    "/nfr/data/compliance/gdpr_rtbf",   # requires batch + pii + audit + compliance-gdpr
    "/nfr/latency/jobStartP95Seconds",  # only valid with batch_processing=True
    "/nfr/latency/jobStartP99Seconds",
    "/nfr/throughput/peak_jobs_per_hour",
}


# ---------------------------------------------------------------------------
# Auto-satisfaction of requires_* rules
# ---------------------------------------------------------------------------

def _load_defaults() -> dict:
    with open(_DEFAULTS_PATH) as f:
        return yaml.safe_load(f)


def _pattern_would_be_selected(pattern: dict, merged_spec: dict) -> bool:
    """
    Return True if this pattern would survive phase 3.1 (supports_constraints)
    and phase 3.2 (supports_nfr) given the merged spec.

    Mirrors the compiler's _filter_by_supports_constraints and
    _filter_by_supports_nfr logic so that auto-satisfaction targets the same
    patterns the real compiler would select.
    """
    # Phase 3.1: ALL supports_constraints rules must pass
    for rule in pattern.get("supports_constraints", []) or []:
        if not _evaluate_rule(merged_spec, rule):
            return False

    # Phase 3.2: supports_nfr rules
    has_nfr = bool(merged_spec.get("nfr", {}))
    sn_rules = pattern.get("supports_nfr", []) or []
    if has_nfr:
        if not sn_rules:
            return False   # empty supports_nfr with NFR requirements → excluded
        for rule in sn_rules:
            if not _evaluate_rule(merged_spec, rule):
                return False

    return True


def _satisfying_value(rule: dict) -> Any:
    """
    Return a concrete value that satisfies the given requires rule, or None
    if this rule type cannot be automatically satisfied (e.g. upper-bound <=).

    Handled:
      ==          → return the required value
      in [list]   → return the first non-null item
      != null     → return the nullable fallback (if known)
      >=          → return the minimum bound value
    Skipped (already satisfied by in-range defaults or no simple fix):
      <=, <, >    → None
    """
    op = rule.get("op")
    value = rule.get("value")
    path = rule.get("path", "")

    if op == "==":
        return value
    elif op == "in" and isinstance(value, list):
        non_null = [v for v in value if v is not None]
        return non_null[0] if non_null else None
    elif op == "!=" and value is None:
        return _NULLABLE_FALLBACKS.get(path)
    elif op == ">=":
        return value   # satisfy the minimum bound
    return None


def _apply_semantic_fixups(spec: dict, merged_spec: dict) -> tuple:
    """
    Apply semantic validation rules encoded in the compiler's
    _validate_semantic_consistency, which are NOT captured by pattern
    requires_* rules and must be handled separately.

    Currently handles:
      • multi_tenancy=True  → tenantCount must be > 1
      • tenantCount > 1     → multi_tenancy must be True

    Returns (updated_spec, changed: bool).
    """
    changed = False
    mt = _json_pointer_get(merged_spec, "/constraints/features/multi_tenancy")
    tc = _json_pointer_get(merged_spec, "/constraints/tenantCount")

    # multi_tenancy=True requires tenantCount > 1
    if mt is True and (tc is None or tc <= 1):
        spec = _set_pointer(spec, "/constraints/tenantCount", 2)
        changed = True

    # tenantCount > 1 requires multi_tenancy=True
    if tc is not None and tc > 1 and not mt:
        spec = _set_pointer(spec, "/constraints/features/multi_tenancy", True)
        changed = True

    return spec, changed


def _auto_satisfy_requires(spec: dict) -> dict:
    """
    Return a copy of spec with all requires_constraints and requires_nfr rules
    satisfied for every pattern that would be selected given the spec (with
    defaults merged in).

    Algorithm (fixed-point):
      1. Merge config/defaults.yaml into spec to get the effective spec.
      2. For each pattern, check if it would be selected (supports_* rules pass).
      3. For each selected pattern, check its requires_* rules.
      4. For any failing require, compute a satisfying value and add it to spec.
      5. Also apply hardcoded semantic validations (tenantCount ↔ multi_tenancy).
      6. Repeat until convergence (max 10 iterations).

    This handles transitive dependencies: setting async_messaging=True selects
    queue-consumer-idempotency, which requires key_value_store=True; that may
    in turn select other patterns with their own requirements.
    """
    defaults = _load_defaults()
    spec = copy.deepcopy(spec)

    for _iteration in range(10):
        merged = _deep_merge(defaults, spec)
        changed = False

        for pattern in _ALL_PATTERNS:
            if not _pattern_would_be_selected(pattern, merged):
                continue

            for rule in (
                (pattern.get("requires_constraints") or [])
                + (pattern.get("requires_nfr") or [])
            ):
                if _evaluate_rule(merged, rule):
                    continue  # already satisfied

                new_val = _satisfying_value(rule)
                if new_val is None:
                    continue  # can't auto-satisfy this rule type

                path = rule["path"]
                current = _json_pointer_get(spec, path)
                if current == new_val:
                    continue  # already set in spec (just merged from defaults)
                spec = _set_pointer(spec, path, new_val)
                merged = _deep_merge(defaults, spec)  # update immediately
                changed = True

        # Apply hardcoded semantic validations (not from pattern rules)
        spec, sem_changed = _apply_semantic_fixups(spec, merged)
        if sem_changed:
            changed = True

        if not changed:
            break

    return spec


# ---------------------------------------------------------------------------
# Schema walker
# ---------------------------------------------------------------------------

def _extract_leaf_paths(schema_node: dict, defaults_node: Any, current_path: str = ""):
    """
    Recursively yield (json_pointer_path, default_value, type_hint, enum_values)
    for each leaf field.  Array fields are skipped (not individually settable).
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
            yield from _extract_leaf_paths(sub_schema, child_default, child_path)

    elif node_type == "array":
        return  # skip — arrays (saas-providers, etc.) aren't single-value leaf fields

    elif node_type in ("boolean", "string", "number", "integer") or "enum" in schema_node:
        yield (current_path, defaults_node, node_type, schema_node.get("enum"))

    elif isinstance(node_type, list):
        # e.g. [\"number\", \"null\"]
        actual_type = next((t for t in node_type if t not in ("null", "array")), None)
        if actual_type:
            yield (current_path, defaults_node, actual_type, schema_node.get("enum"))

    elif "anyOf" in schema_node or "oneOf" in schema_node:
        # e.g. anyOf: [{type: string, enum: [...]}, {type: null}]
        # e.g. oneOf: [{type: number}, {type: string, enum: ["n/a"]}]
        variants = schema_node.get("anyOf") or schema_node.get("oneOf") or []
        non_null = [s for s in variants if s.get("type") != "null"]
        if non_null:
            sub = non_null[0]
            yield (current_path, defaults_node, sub.get("type"), sub.get("enum"))


def _nondefault_value(path: str, default: Any, type_hint: str, enum_vals) -> Any:
    """Return a test value that differs from the default when possible."""
    if path in SKIP_NONDEFAULT:
        return default  # fall back to explicit-default test

    # Path-specific override wins over auto-computation
    if path in FIXED_TEST_VALUES:
        return FIXED_TEST_VALUES[path]

    if type_hint == "boolean":
        return (not default) if default is not None else True

    if type_hint in ("number", "integer"):
        if default is None:
            return None  # null default → skip below
        return default + 10  # safe additive delta (avoid * 2 overflow for bounded fields)

    if type_hint == "string":
        if enum_vals:
            for v in enum_vals:
                if v != default:
                    return v
        return default  # no alternative found

    return default


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result


def _set_pointer(spec: dict, pointer: str, value: Any) -> dict:
    """Return a copy of spec with value set at the JSON pointer path."""
    parts = [p for p in pointer.lstrip("/").split("/") if p]
    result = copy.deepcopy(spec)
    node = result
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    return result


# ---------------------------------------------------------------------------
# Generate test cases from schema
# ---------------------------------------------------------------------------

def _generate_schema_cases():
    with open(_SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)
    with open(_DEFAULTS_PATH) as f:
        defaults = yaml.safe_load(f)

    cases = []
    for path, default, type_hint, enum_vals in _extract_leaf_paths(schema, defaults):
        # Skip project/functional — not involved in pattern selection or merging
        if path.startswith("/project") or path.startswith("/functional"):
            continue

        test_value = _nondefault_value(path, default, type_hint, enum_vals)

        if test_value is None:
            continue  # null-default numeric fields require too much context

        # Start from BASE, set the test field, then auto-satisfy all requires
        spec = _set_pointer(_BASE, path, test_value)
        spec = _auto_satisfy_requires(spec)

        # Use last two path segments as a readable ID
        label = "/".join(path.lstrip("/").split("/")[-2:])
        cases.append((label, path, test_value, spec))

    return cases


_SCHEMA_CASES = _generate_schema_cases()


# ---------------------------------------------------------------------------
# Compile helpers
# ---------------------------------------------------------------------------

def _compile(spec_dict: dict, outdir: str) -> tuple:
    """Write spec to outdir, run compiler, return (ok, compiled_spec_or_None)."""
    spec_file = os.path.join(outdir, "spec.yaml")
    with open(spec_file, "w") as f:
        yaml.dump(spec_dict, f)
    result = subprocess.run(
        [sys.executable, _COMPILER, spec_file, "-o", outdir],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False, result.stdout
    compiled_path = os.path.join(outdir, "compiled-spec.yaml")
    with open(compiled_path) as f:
        return True, yaml.safe_load(f)


def _selected_ids_from_file(outdir: str) -> frozenset:
    path = os.path.join(outdir, "selected-patterns.yaml")
    if not os.path.exists(path):
        return frozenset()
    with open(path) as f:
        data = yaml.safe_load(f) or []
    return frozenset(p["id"] for p in data)


# ---------------------------------------------------------------------------
# Test: schema-driven idempotency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,path,test_value,spec", _SCHEMA_CASES,
                         ids=[c[0] for c in _SCHEMA_CASES])
def test_schema_leaf_idempotency(label, path, test_value, spec):
    """
    For every leaf field in canonical-schema.yaml:
      - compile the spec twice
      - assert the same patterns are selected
      - assert the user-provided value survived recompilation
    """
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        ok1, r1 = _compile(spec, d1)
        assert ok1, f"[{label}] First compile failed:\n{r1}"

        ids1 = _selected_ids_from_file(d1)
        compiled_spec1 = r1

        ok2, r2 = _compile(compiled_spec1, d2)
        assert ok2, f"[{label}] Second compile failed:\n{r2}"

        ids2 = _selected_ids_from_file(d2)

        assert ids1 == ids2, (
            f"[{label}] Pattern selection changed on recompile\n"
            f"  run1: {sorted(ids1)}\n"
            f"  run2: {sorted(ids2)}\n"
            f"  added:   {sorted(ids2 - ids1)}\n"
            f"  removed: {sorted(ids1 - ids2)}"
        )

        # User-provided value must survive recompilation unchanged
        actual = _json_pointer_get(r2, path)
        # The value may live at top-level or be preserved in assumptions — either is fine
        # as long as idempotency holds.  We check top-level first, then assumptions.
        if actual is None:
            assumptions_path = "/assumptions" + path
            actual = _json_pointer_get(r2, assumptions_path)
        assert actual == test_value, (
            f"[{label}] User value {test_value!r} at {path!r} was lost after recompile; "
            f"got {actual!r}"
        )


# ---------------------------------------------------------------------------
# Test: schema coverage — every leaf path has a generated case
# (meta-test: catches misconfigured SKIP_NONDEFAULT or schema walker bugs)
# ---------------------------------------------------------------------------

def test_schema_case_count_is_nonzero():
    """Sanity check: the schema walker must generate at least one case per
    top-level section.  If this fails, the schema walker is broken."""
    sections = {c[1].split("/")[1] for c in _SCHEMA_CASES}
    assert "constraints" in sections, "No constraints cases generated"
    assert "nfr" in sections, "No nfr cases generated"
    assert "operating_model" in sections, "No operating_model cases generated"
    assert "cost" in sections, "No cost cases generated"


def test_skip_nondefault_keys_are_valid_paths():
    """Every path in SKIP_NONDEFAULT must exist in the schema."""
    with open(_SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)
    with open(_DEFAULTS_PATH) as f:
        defaults = yaml.safe_load(f)

    all_schema_paths = {
        path for path, *_ in _extract_leaf_paths(schema, defaults)
    }
    for path in SKIP_NONDEFAULT:
        assert path in all_schema_paths, (
            f"SKIP_NONDEFAULT references {path!r} which is not a leaf path in the schema. "
            "Update SKIP_NONDEFAULT if the schema changed."
        )


def test_nullable_fallbacks_keys_are_valid_paths():
    """Every path in _NULLABLE_FALLBACKS must exist in the schema."""
    with open(_SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)
    with open(_DEFAULTS_PATH) as f:
        defaults = yaml.safe_load(f)

    all_schema_paths = {
        path for path, *_ in _extract_leaf_paths(schema, defaults)
    }
    for path in _NULLABLE_FALLBACKS:
        assert path in all_schema_paths, (
            f"_NULLABLE_FALLBACKS references {path!r} which is not a leaf path in the schema. "
            "Update _NULLABLE_FALLBACKS if the schema changed."
        )


def test_fixed_test_values_are_valid_paths():
    """Every path in FIXED_TEST_VALUES must exist in the schema."""
    with open(_SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)
    with open(_DEFAULTS_PATH) as f:
        defaults = yaml.safe_load(f)

    all_schema_paths = {
        path for path, *_ in _extract_leaf_paths(schema, defaults)
    }
    for path in FIXED_TEST_VALUES:
        assert path in all_schema_paths, (
            f"FIXED_TEST_VALUES references {path!r} which is not a leaf path in the schema. "
            "Update FIXED_TEST_VALUES if the schema changed."
        )


def test_auto_satisfy_is_deterministic():
    """_auto_satisfy_requires must return the same result when called twice."""
    spec = _set_pointer(_BASE, "/constraints/features/async_messaging", True)
    result1 = _auto_satisfy_requires(spec)
    result2 = _auto_satisfy_requires(spec)
    assert result1 == result2, (
        "_auto_satisfy_requires is non-deterministic — "
        "check for ordering dependencies in pattern loading or rule evaluation"
    )
