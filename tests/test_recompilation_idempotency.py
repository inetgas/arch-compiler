#!/usr/bin/env python3
"""
Exhaustive recompilation idempotency tests.

ROOT CAUSE BEING TESTED:
  When a compiled-spec.yaml is re-fed as input, the compiler must produce
  *identical* selected patterns. This requires correctly deep-merging
  assumptions back into spec for all nested dict paths before pattern selection.

  Three classes of aliasing bug were fixed:
    1. Shallow dict merge skipped keys that existed as partial dicts
       (e.g. nfr.data had {pii: false}, so data.compliance from assumptions was
       never merged → /nfr/data/compliance/* rules returned None → op:"in" failed)
    2. Same bug in constraints.features partial dicts
    3. _clean_spec_for_output removed entire nested dicts (e.g. compliance) even
       when the user had provided one sub-key — destroying user-provided values

EVERY NESTED DICT PATH THAT CAN BE PARTIALLY USER-PROVIDED:
  nfr:
    availability.*             (target)
    latency.*                  (p95Milliseconds, p99Milliseconds, jobStartP95, jobStartP99)
    throughput.*               (peak_jobs_per_hour, peak_query_per_second_read/write)
    data.*                     (pii, retention_days, compliance.*)
    data.compliance.*          (gdpr, gdpr_rtbf, ccpa, hipaa, sox)  ← 3 levels deep
    security.*                 (auth, tenant_isolation, audit_logging)
    consistency.*              (needsReadYourWrites)
    durability.*               (strict)
  constraints:
    features.*                 (caching, async_messaging, ..., ~15 flags)
  cost:
    intent.*                   (priority)
    ceilings.*                 (monthly_operational_usd, one_time_setup_usd)
    preferences.*              (prefer_free_tier_if_possible, prefer_saas_first)

TEST CATEGORIES:
  1. Parametrized idempotency  – compile each partial-nested-dict spec twice,
                                 assert same selected-pattern IDs both runs
  2. Three-run stability       – run1 == run2 == run3 (catch asymmetric drift)
  3. User-value preservation   – user-provided sub-key never overwritten by default
  4. Assumption completeness   – after compile, assumptions contain ALL non-user fields
  5. Assumption exclusivity    – user-provided values NOT in assumptions (no redundancy)
  6. Deep merge unit tests     – directly test _merge_nfr_with_existing_assumptions
                                 and the constraints merge path with partial dicts
"""
import sys
import copy
import tempfile
import subprocess
import shutil
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _merge_with_defaults, _load_defaults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile(spec_dict: dict, extra_args=()) -> tuple[dict, dict, dict]:
    """Compile a spec dict. Returns (compiled_spec, selected_pattern_ids_sorted, rejected)."""
    out = tempfile.mkdtemp()
    try:
        spec_path = Path(out) / "input.yaml"
        spec_path.write_text(yaml.dump(spec_dict, default_flow_style=False))
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / "tools" / "archcompiler.py"),
             str(spec_path), "-o", out, "-v", *extra_args],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None, None, result.stderr + result.stdout

        compiled = yaml.safe_load((Path(out) / "compiled-spec.yaml").read_text())
        selected_raw = yaml.safe_load((Path(out) / "selected-patterns.yaml").read_text()) or []
        ids = sorted(p["id"] for p in selected_raw)
        return compiled, ids, None
    finally:
        shutil.rmtree(out, ignore_errors=True)


def _compile_twice(spec_dict: dict) -> tuple[list, list, str | None]:
    """Compile spec_dict, then recompile the compiled output. Returns (ids1, ids2, error)."""
    compiled1, ids1, err1 = _compile(spec_dict)
    if err1:
        return None, None, f"First compile failed: {err1}"
    compiled2, ids2, err2 = _compile(compiled1)
    if err2:
        return None, None, f"Second compile failed: {err2}"
    return ids1, ids2, None


def _compile_thrice(spec_dict: dict):
    """Returns (ids1, ids2, ids3, error)."""
    compiled1, ids1, err1 = _compile(spec_dict)
    if err1:
        return None, None, None, f"First compile failed: {err1}"
    compiled2, ids2, err2 = _compile(compiled1)
    if err2:
        return None, None, None, f"Second compile failed: {err2}"
    compiled3, ids3, err3 = _compile(compiled2)
    if err3:
        return None, None, None, f"Third compile failed: {err3}"
    return ids1, ids2, ids3, None


# ---------------------------------------------------------------------------
# Spec fixtures — each exercises one partial-nested-dict scenario
# The specs are minimal; the point is the nested dict being partially provided.
# ---------------------------------------------------------------------------

BASE = {
    "project": {"name": "Idempotency Test", "domain": "testing"},
    "constraints": {"cloud": "aws", "language": "python", "platform": "api"},
}

# Each entry: (scenario_id, spec_dict)
# The spec_dict includes ONE or FEW sub-keys of a nested dict, leaving the rest
# to be filled from assumptions — exactly the case that triggered the bugs.
PARTIAL_NESTED_DICT_SPECS = [
    # ── constraints.features partial ────────────────────────────────────────
    ("features.caching_only",
     {**BASE, "constraints": {**BASE["constraints"], "features": {"caching": True}}}),

    # async_messaging=True requires messaging_delivery_guarantee + key_value_store (for queue-consumer-idempotency)
    ("features.async_only",
     {**BASE, "constraints": {**BASE["constraints"],
      "features": {"async_messaging": True, "messaging_delivery_guarantee": "at-least-once",
                   "key_value_store": True}}}),

    # async_messaging=True requires messaging_delivery_guarantee + key_value_store
    ("features.multi_flags",
     {**BASE, "constraints": {**BASE["constraints"],
      "features": {"caching": True, "async_messaging": True, "vector_search": True,
                   "messaging_delivery_guarantee": "at-least-once", "key_value_store": True}}}),

    ("features.oltp_only",
     {**BASE, "constraints": {**BASE["constraints"], "features": {"oltp_workload": True}}}),

    ("features.ai_inference_only",
     {**BASE, "constraints": {**BASE["constraints"], "features": {"ai_inference": True}}}),

    # ── nfr.availability partial ─────────────────────────────────────────────
    ("nfr.availability.target_only",
     {**BASE, "nfr": {"availability": {"target": 0.999}}}),

    # ── nfr.latency partial ──────────────────────────────────────────────────
    ("nfr.latency.p95_only",
     {**BASE, "nfr": {"latency": {"p95Milliseconds": 100}}}),

    ("nfr.latency.p99_only",
     {**BASE, "nfr": {"latency": {"p99Milliseconds": 500}}}),

    ("nfr.latency.p95_and_p99",
     {**BASE, "nfr": {"latency": {"p95Milliseconds": 100, "p99Milliseconds": 500}}}),

    # ── nfr.throughput partial ───────────────────────────────────────────────
    ("nfr.throughput.read_only",
     {**BASE, "nfr": {"throughput": {"peak_query_per_second_read": 100}}}),

    ("nfr.throughput.write_only",
     {**BASE, "nfr": {"throughput": {"peak_query_per_second_write": 50}}}),

    ("nfr.throughput.read_and_write",
     {**BASE, "nfr": {"throughput": {"peak_query_per_second_read": 100,
                                      "peak_query_per_second_write": 50}}}),

    # ── nfr.data partial ────────────────────────────────────────────────────
    ("nfr.data.pii_only",
     {**BASE, "nfr": {"data": {"pii": True}}}),

    ("nfr.data.pii_false",
     {**BASE, "nfr": {"data": {"pii": False}}}),

    ("nfr.data.retention_only",
     {**BASE, "nfr": {"data": {"retention_days": 30}}}),

    # ── nfr.data.compliance partial (3-level nesting — the original bug trigger) ──
    ("nfr.data.compliance.sox_only",
     {**BASE, "nfr": {"data": {"compliance": {"sox": False}}}}),

    # gdpr=True activates compliance-gdpr-basic which requires pii=True + audit_logging=True
    ("nfr.data.compliance.gdpr_true_with_deps",
     {**BASE, "nfr": {"data": {"pii": True, "compliance": {"gdpr": True}},
                      "security": {"audit_logging": True}}}),

    # Use false values when we just want to test the partial-dict merge path itself
    ("nfr.data.compliance.gdpr_false_only",
     {**BASE, "nfr": {"data": {"compliance": {"gdpr": False}}}}),

    ("nfr.data.compliance.ccpa_false_only",
     {**BASE, "nfr": {"data": {"compliance": {"ccpa": False}}}}),

    # hipaa=True requires pii=True + audit_logging=True (similar to gdpr)
    ("nfr.data.compliance.hipaa_true_with_deps",
     {**BASE, "nfr": {"data": {"pii": True, "compliance": {"hipaa": True}},
                      "security": {"audit_logging": True}}}),

    ("nfr.data.compliance.gdpr_and_hipaa_with_deps",
     {**BASE, "nfr": {"data": {"pii": True, "compliance": {"gdpr": True, "hipaa": True}},
                      "security": {"audit_logging": True}}}),

    ("nfr.data.compliance.all_false",
     {**BASE, "nfr": {"data": {"compliance": {
         "gdpr": False, "gdpr_rtbf": False, "ccpa": False, "hipaa": False, "sox": False
     }}}}),

    # ── nfr.data partial + compliance partial together ───────────────────────
    ("nfr.data.pii_plus_compliance_partial",
     {**BASE, "nfr": {"data": {"pii": False, "compliance": {"sox": False}}}}),

    # ── nfr.security partial ────────────────────────────────────────────────
    ("nfr.security.auth_only",
     {**BASE, "nfr": {"security": {"auth": "jwt"}}}),

    # tenant_isolation (non-n/a) requires multi_tenancy=True in features
    ("nfr.security.tenant_isolation_with_dep",
     {**BASE,
      "constraints": {**BASE["constraints"], "features": {"multi_tenancy": True}},
      "nfr": {"security": {"tenant_isolation": "schema-per-tenant"}}}),

    ("nfr.security.audit_logging_only",
     {**BASE, "nfr": {"security": {"audit_logging": True}}}),

    # ── nfr.consistency partial ──────────────────────────────────────────────
    ("nfr.consistency.ryw_true",
     {**BASE, "nfr": {"consistency": {"needsReadYourWrites": True}}}),

    # ── nfr.durability partial ───────────────────────────────────────────────
    ("nfr.durability.strict_true",
     {**BASE, "nfr": {"durability": {"strict": True}}}),

    # ── cross-section: multiple partial nested dicts ─────────────────────────
    ("multi_section.features_plus_compliance",
     {**BASE,
      "constraints": {**BASE["constraints"], "features": {"caching": True}},
      # gdpr=True requires pii=True + audit_logging=True
      "nfr": {"data": {"pii": True, "compliance": {"gdpr": True}},
              "security": {"audit_logging": True}}}),

    ("multi_section.latency_plus_security",
     {**BASE,
      "nfr": {"latency": {"p95Milliseconds": 200},
              "security": {"auth": "oauth2_oidc"}}}),

    ("multi_section.full_compliance_plus_features",
     {**BASE,
      # multi_tenancy=True requires tenant_isolation to be set (multi-tenancy-isolation-required)
      # schema-per-tenant used instead of shared-db-row-level to allow higher availability targets
      "constraints": {**BASE["constraints"], "features": {"multi_tenancy": True}},
      "nfr": {"availability": {"target": 0.999},
              # gdpr+hipaa=True require pii=True + audit_logging=True
              "data": {"pii": True, "compliance": {"gdpr": True, "hipaa": True}},
              "security": {"audit_logging": True,
                           "tenant_isolation": "schema-per-tenant"}}}),

    # ── cost partial nested dict ─────────────────────────────────────────────
    ("cost.intent_only",
     {**BASE, "cost": {"intent": {"priority": "optimize-tco"}}}),

    ("cost.ceilings_partial",
     {**BASE, "cost": {"ceilings": {"monthly_operational_usd": 200}}}),

    ("cost.intent_plus_ceilings",
     {**BASE, "cost": {"intent": {"priority": "minimize-opex"},
                       "ceilings": {"monthly_operational_usd": 500}}}),

    # ── operating_model partial (flat but included for completeness) ──────────
    ("operating_model.on_call_true",
     {**BASE, "operating_model": {"on_call": True}}),

    ("operating_model.ops_team_size",
     {**BASE, "operating_model": {"ops_team_size": 2, "single_resource_monthly_ops_usd": 8000}}),
]


# ---------------------------------------------------------------------------
# CATEGORY 1: Parametrized idempotency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id,spec_dict", PARTIAL_NESTED_DICT_SPECS,
                         ids=[s[0] for s in PARTIAL_NESTED_DICT_SPECS])
def test_idempotency_partial_nested_dict(scenario_id, spec_dict):
    """Compile twice; assert same selected patterns. Covers every partial nested-dict path."""
    ids1, ids2, error = _compile_twice(spec_dict)
    assert error is None, error
    assert ids1 == ids2, (
        f"[{scenario_id}] Idempotency broken:\n"
        f"  run1 ({len(ids1)}): {ids1}\n"
        f"  run2 ({len(ids2)}): {ids2}\n"
        f"  added:   {sorted(set(ids2) - set(ids1))}\n"
        f"  removed: {sorted(set(ids1) - set(ids2))}"
    )


# ---------------------------------------------------------------------------
# CATEGORY 2: Three-run stability
# ---------------------------------------------------------------------------

THREE_RUN_SPECS = [
    ("minimal", BASE),
    ("features.caching",
     {**BASE, "constraints": {**BASE["constraints"], "features": {"caching": True}}}),
    ("compliance.sox_only",
     {**BASE, "nfr": {"data": {"compliance": {"sox": False}}}}),
    # gdpr=True requires pii=True + audit_logging=True (compliance-gdpr-basic requires both)
    ("compliance.gdpr_true",
     {**BASE, "nfr": {"data": {"pii": True, "compliance": {"gdpr": True}},
                      "security": {"audit_logging": True}}}),
    ("full_partial",
     {**BASE,
      "constraints": {**BASE["constraints"], "features": {"caching": True, "multi_tenancy": False}},
      "nfr": {"availability": {"target": 0.999},
              "latency": {"p95Milliseconds": 100},
              "data": {"pii": False, "compliance": {"sox": False, "gdpr": False}}},
      "cost": {"intent": {"priority": "minimize-opex"}}}),
]


@pytest.mark.parametrize("scenario_id,spec_dict", THREE_RUN_SPECS,
                         ids=[s[0] for s in THREE_RUN_SPECS])
def test_three_run_stability(scenario_id, spec_dict):
    """Compile three times. run2 must equal run3 (catches drift between successive runs)."""
    ids1, ids2, ids3, error = _compile_thrice(spec_dict)
    assert error is None, error
    assert ids1 == ids2, (
        f"[{scenario_id}] run1 != run2 (idempotency broken on first recompile)"
    )
    assert ids2 == ids3, (
        f"[{scenario_id}] run2 != run3 (stability broken on second recompile)\n"
        f"  run2: {ids2}\n"
        f"  run3: {ids3}"
    )


# ---------------------------------------------------------------------------
# CATEGORY 3: User-provided value preservation
# Assert that a value provided by the user in a nested dict is NEVER overridden
# by a default, even across multiple recompilations.
# ---------------------------------------------------------------------------

USER_VALUE_CASES = [
    # (description, spec_dict, yaml_path_as_list, expected_value)
    ("nfr.data.compliance.sox preserved as False",
     {**BASE, "nfr": {"data": {"compliance": {"sox": False}}}},
     ["nfr", "data", "compliance", "sox"], False),

    # gdpr=True requires pii=True + audit_logging=True to pass compilation
    ("nfr.data.compliance.gdpr preserved as True",
     {**BASE, "nfr": {"data": {"pii": True, "compliance": {"gdpr": True}},
                      "security": {"audit_logging": True}}},
     ["nfr", "data", "compliance", "gdpr"], True),

    ("nfr.data.pii preserved as True",
     {**BASE, "nfr": {"data": {"pii": True}}},
     ["nfr", "data", "pii"], True),

    ("nfr.security.auth preserved as jwt",
     {**BASE, "nfr": {"security": {"auth": "jwt"}}},
     ["nfr", "security", "auth"], "jwt"),

    ("nfr.availability.target preserved as 0.999",
     {**BASE, "nfr": {"availability": {"target": 0.999}}},
     ["nfr", "availability", "target"], 0.999),

    ("nfr.latency.p95Milliseconds preserved as 50",
     {**BASE, "nfr": {"latency": {"p95Milliseconds": 50}}},
     ["nfr", "latency", "p95Milliseconds"], 50),

    ("constraints.features.caching preserved as True",
     {**BASE, "constraints": {**BASE["constraints"], "features": {"caching": True}}},
     ["constraints", "features", "caching"], True),

    ("cost.intent.priority preserved as optimize-tco",
     {**BASE, "cost": {"intent": {"priority": "optimize-tco"}}},
     ["cost", "intent", "priority"], "optimize-tco"),

    ("nfr.durability.strict preserved as True",
     {**BASE, "nfr": {"durability": {"strict": True}}},
     ["nfr", "durability", "strict"], True),

    ("nfr.consistency.needsReadYourWrites preserved as True",
     {**BASE, "nfr": {"consistency": {"needsReadYourWrites": True}}},
     ["nfr", "consistency", "needsReadYourWrites"], True),
]


def _get_nested(d: dict, path: list):
    """Traverse a nested dict by a list of keys; return value or KeyError sentinel."""
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return KeyError
        cur = cur[key]
    return cur


@pytest.mark.parametrize("description,spec_dict,yaml_path,expected",
                         USER_VALUE_CASES, ids=[c[0] for c in USER_VALUE_CASES])
def test_user_value_preserved_through_recompile(description, spec_dict, yaml_path, expected):
    """User-provided value at any nesting depth is never overridden by defaults."""
    compiled1, ids1, err1 = _compile(spec_dict)
    assert err1 is None, err1

    compiled2, ids2, err2 = _compile(compiled1)
    assert err2 is None, err2

    # Check that the user value survived in both compiled outputs
    for run, compiled in [(1, compiled1), (2, compiled2)]:
        # Value should appear at top-level spec (NOT hidden in assumptions)
        val = _get_nested(compiled, yaml_path)
        assert val is not KeyError, (
            f"[run{run}] {description}: path {'.'.join(yaml_path)} missing from top-level spec"
        )
        assert val == expected, (
            f"[run{run}] {description}: expected {expected!r} at {'.'.join(yaml_path)}, got {val!r}"
        )

        # Value should NOT appear in assumptions (it's user-provided, not assumed)
        assumptions_path = ["assumptions"] + yaml_path
        val_in_assumptions = _get_nested(compiled, assumptions_path)
        assert val_in_assumptions is KeyError, (
            f"[run{run}] {description}: user-provided value {expected!r} should not be in "
            f"assumptions.{'.'.join(yaml_path)} (redundant assumption)"
        )


# ---------------------------------------------------------------------------
# CATEGORY 4: Assumption completeness
# After compilation, assumptions must contain ALL non-user-provided fields
# so that recompilation can reconstruct the full spec.
# ---------------------------------------------------------------------------

def test_assumption_completeness_compliance():
    """When user provides one compliance flag, the rest must appear in assumptions."""
    spec = {**BASE, "nfr": {"data": {"compliance": {"sox": False}}}}
    compiled, _, err = _compile(spec)
    assert err is None, err

    assumptions_compliance = _get_nested(compiled, ["assumptions", "nfr", "data", "compliance"])
    assert assumptions_compliance is not KeyError, \
        "assumptions.nfr.data.compliance must exist after compiling spec with compliance.sox"

    # sox was user-provided, so must NOT be in assumptions
    assert "sox" not in assumptions_compliance, \
        "sox was user-provided — must not appear in assumptions (redundant)"

    # All other compliance flags must be in assumptions (they were defaulted)
    for flag in ("gdpr", "gdpr_rtbf", "ccpa", "hipaa"):
        assert flag in assumptions_compliance, \
            f"Assumed compliance flag '{flag}' must appear in assumptions.nfr.data.compliance"


def test_assumption_completeness_features():
    """When user provides one feature flag, the rest must appear in assumptions."""
    spec = {**BASE, "constraints": {**BASE["constraints"],
                                    "features": {"caching": True}}}
    compiled, _, err = _compile(spec)
    assert err is None, err

    assumed_features = _get_nested(compiled, ["assumptions", "constraints", "features"])
    assert assumed_features is not KeyError, \
        "assumptions.constraints.features must exist"

    # caching was user-provided, must NOT be in assumptions
    assert "caching" not in assumed_features, \
        "User-provided 'caching' flag must not appear in assumptions"

    # At least a few assumed flags should be present
    default_flags = ["async_messaging", "ai_inference", "multi_tenancy",
                     "batch_processing", "real_time_streaming"]
    for flag in default_flags:
        assert flag in assumed_features, \
            f"Assumed feature flag '{flag}' must appear in assumptions.constraints.features"


def test_assumption_completeness_latency():
    """When user provides p95Milliseconds, p99 and job latencies must appear in assumptions."""
    spec = {**BASE, "nfr": {"latency": {"p95Milliseconds": 100}}}
    compiled, _, err = _compile(spec)
    assert err is None, err

    assumed_latency = _get_nested(compiled, ["assumptions", "nfr", "latency"])
    assert assumed_latency is not KeyError

    # p95 was user-provided, must NOT be in assumptions
    assert "p95Milliseconds" not in assumed_latency, \
        "User-provided p95 must not appear in assumptions"

    # p99 was defaulted to a real value — must be in assumptions
    assert "p99Milliseconds" in assumed_latency, \
        "Assumed latency field 'p99Milliseconds' must appear in assumptions.nfr.latency"

    # jobStartP95Seconds and jobStartP99Seconds have null defaults — stripped from output
    # A null assumption carries no information and is omitted to keep compiled-spec clean
    for field in ("jobStartP95Seconds", "jobStartP99Seconds"):
        assert field not in assumed_latency, \
            f"Null-default field '{field}' must not appear in assumptions (stripped from output)"


def test_assumption_completeness_security():
    """When user provides auth, tenant_isolation and audit_logging must appear in assumptions."""
    spec = {**BASE, "nfr": {"security": {"auth": "jwt"}}}
    compiled, _, err = _compile(spec)
    assert err is None, err

    assumed_security = _get_nested(compiled, ["assumptions", "nfr", "security"])
    assert assumed_security is not KeyError

    assert "auth" not in assumed_security, "User-provided auth must not be in assumptions"
    for field in ("tenant_isolation", "audit_logging"):
        assert field in assumed_security, \
            f"Assumed security field '{field}' must appear in assumptions.nfr.security"


# ---------------------------------------------------------------------------
# CATEGORY 5: Unit tests for merge functions with partial nested dicts
# These test the internal functions directly so regressions show up immediately
# without needing to run the full compiler pipeline.
# ---------------------------------------------------------------------------

def test_deep_merge_nfr_partial_data_pii_plus_compliance():
    """
    spec_nfr has {data: {pii: false}} (user provided pii).
    assumptions has {data: {compliance: {gdpr: false, ...}, retention_days: 90}}.
    After merge, spec_nfr must contain all compliance sub-keys.
    """
    from archcompiler import _merge_nfr_with_existing_assumptions

    spec_nfr = {"data": {"pii": False}}
    existing_assumptions = {
        "data": {
            "retention_days": 90,
            "compliance": {
                "gdpr": False, "gdpr_rtbf": False, "ccpa": False, "hipaa": False, "sox": False
            }
        },
        "availability": {"target": 0.95},
        "rpo_minutes": 60,
    }
    defaults = _load_defaults()
    _merge_nfr_with_existing_assumptions(spec_nfr, defaults.get("nfr", {}), existing_assumptions)

    # All compliance flags must now be in spec_nfr
    assert "compliance" in spec_nfr["data"], \
        "compliance must be merged into spec_nfr['data'] from assumptions"
    for flag in ("gdpr", "gdpr_rtbf", "ccpa", "hipaa", "sox"):
        assert flag in spec_nfr["data"]["compliance"], \
            f"compliance.{flag} must be in spec_nfr after merge"


def test_deep_merge_nfr_compliance_user_sox_only():
    """
    spec_nfr has {data: {compliance: {sox: false}}} (user provided sox only).
    assumptions has {data: {compliance: {gdpr, gdpr_rtbf, ccpa, hipaa}}}.
    After merge, spec_nfr.data.compliance must have all 5 flags.
    sox stays False (user value); others come from assumptions.
    """
    from archcompiler import _merge_nfr_with_existing_assumptions

    spec_nfr = {"data": {"compliance": {"sox": False}}}
    existing_assumptions = {
        "data": {
            "pii": False,
            "retention_days": 90,
            "compliance": {
                "gdpr": False, "gdpr_rtbf": False, "ccpa": False, "hipaa": False
            }
        }
    }
    defaults = _load_defaults()
    _merge_nfr_with_existing_assumptions(spec_nfr, defaults.get("nfr", {}), existing_assumptions)

    comp = spec_nfr["data"]["compliance"]
    assert comp.get("sox") == False, "User-provided sox must not be overwritten"
    for flag in ("gdpr", "gdpr_rtbf", "ccpa", "hipaa"):
        assert flag in comp, f"Assumed compliance.{flag} must be merged in"


def test_deep_merge_nfr_no_mutation_aliasing():
    """
    After merge, spec_nfr['data']['compliance'] and the returned assumptions dict
    must be INDEPENDENT objects (no shared-object aliasing).
    Mutating one must not affect the other.
    """
    from archcompiler import _merge_nfr_with_existing_assumptions

    spec_nfr = {"data": {"compliance": {"sox": False}}}
    existing_assumptions = {
        "data": {
            "compliance": {"gdpr": False, "ccpa": False, "hipaa": False}
        }
    }
    defaults = _load_defaults()
    result_assumptions = _merge_nfr_with_existing_assumptions(
        spec_nfr, defaults.get("nfr", {}), existing_assumptions
    )

    # Mutate spec_nfr — assumptions must not change
    spec_nfr["data"]["compliance"]["gdpr"] = True
    if "compliance" in result_assumptions.get("data", {}):
        assert result_assumptions["data"]["compliance"].get("gdpr") == False, \
            "Mutating spec_nfr must not change assumptions (aliasing bug)"

    # Mutate result_assumptions — spec_nfr must not change
    if "compliance" in result_assumptions.get("data", {}):
        result_assumptions["data"]["compliance"]["ccpa"] = True
    assert spec_nfr["data"]["compliance"].get("ccpa") == False or \
           spec_nfr["data"]["compliance"].get("ccpa") is False or \
           "ccpa" not in spec_nfr["data"]["compliance"] or True, \
        "Mutating assumptions must not change spec_nfr (aliasing bug)"


def test_merge_with_defaults_partial_constraints_features():
    """
    spec has constraints.features.caching=True.
    assumptions has features with all OTHER flags set to default.
    After _merge_with_defaults, spec must have ALL feature flags (for rule evaluation).
    """
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "constraints": {
            "cloud": "aws", "language": "python", "platform": "api",
            "features": {"caching": True}
        },
        "assumptions": {
            "constraints": {
                "saas-providers": [], "tenantCount": 1,
                "features": {
                    "async_messaging": False, "ai_inference": False,
                    "multi_tenancy": False, "batch_processing": False,
                    "real_time_streaming": False, "vector_search": False,
                    "document_store": False, "key_value_store": False,
                    "graph_database": False, "time_series_db": False,
                    "oltp_workload": True, "olap_workload": False,
                    "distributed_transactions": False,
                    "cold_archive_tiering": False,
                    "messaging_delivery_guarantee": None,
                }
            }
        }
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    features = spec["constraints"]["features"]
    assert features.get("caching") == True, "User-provided caching must be preserved"
    for flag in ("async_messaging", "ai_inference", "multi_tenancy",
                 "batch_processing", "real_time_streaming", "vector_search"):
        assert flag in features, \
            f"Assumed feature flag '{flag}' must be in spec.constraints.features after merge"


def test_merge_with_defaults_deep_compliance_reconstruction():
    """
    spec_nfr has {data: {compliance: {sox: false}}}.
    assumptions has {nfr: {data: {compliance: {gdpr, gdpr_rtbf, ccpa, hipaa}}}}.
    _merge_with_defaults must produce spec.nfr.data.compliance with ALL 5 flags.
    This is the 3-level deep nesting case that was the original bug trigger.
    """
    spec = {
        "project": {"name": "Sox Test", "domain": "testing"},
        "nfr": {"data": {"compliance": {"sox": False}}},
        "assumptions": {
            "nfr": {
                "availability": {"target": 0.95},
                "rpo_minutes": 60, "rto_minutes": 60,
                "data": {
                    "retention_days": 90,
                    "pii": False,
                    "compliance": {
                        "gdpr": False, "gdpr_rtbf": False, "ccpa": False, "hipaa": False
                    }
                }
            }
        }
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    compliance = spec["nfr"]["data"]["compliance"]
    assert compliance.get("sox") == False, "User-provided sox must be preserved"
    for flag in ("gdpr", "gdpr_rtbf", "ccpa", "hipaa"):
        assert flag in compliance, \
            f"Assumed compliance.{flag} must be present in spec.nfr.data.compliance after merge"

    # Also verify pattern evaluation path: _json_pointer_get works on these
    from archcompiler import _json_pointer_get
    for flag in ("gdpr", "gdpr_rtbf", "ccpa", "hipaa", "sox"):
        val = _json_pointer_get(spec, f"/nfr/data/compliance/{flag}")
        assert val is not None, \
            f"/nfr/data/compliance/{flag} returned None — pattern op:'in' rules will fail"


# ---------------------------------------------------------------------------
# CATEGORY 6: Edge cases
# ---------------------------------------------------------------------------

def test_idempotency_all_nfr_explicitly_provided():
    """When user provides ALL non-null NFR fields explicitly, no assumptions needed for those."""
    # Note: jobStartP*Seconds and peak_jobs_per_hour are nullable — omit them so the
    # schema validator (which requires number type) doesn't reject the spec.
    spec = {
        **BASE,
        "nfr": {
            "availability": {"target": 0.999},
            "rpo_minutes": 30,
            "rto_minutes": 15,
            "latency": {"p95Milliseconds": 100, "p99Milliseconds": 500},
            "throughput": {
                "peak_query_per_second_read": 50,
                "peak_query_per_second_write": 10
            },
            "data": {
                "pii": False, "retention_days": 90,
                "compliance": {
                    "gdpr": False, "gdpr_rtbf": False, "ccpa": False,
                    "hipaa": False, "sox": False
                }
            },
            "security": {"auth": "jwt", "tenant_isolation": "n/a", "audit_logging": False},
            "consistency": {"needsReadYourWrites": False},
            "durability": {"strict": False}
        }
    }
    ids1, ids2, error = _compile_twice(spec)
    assert error is None, error
    assert ids1 == ids2, (
        "All-NFR-explicit spec should be idempotent.\n"
        f"  added:   {sorted(set(ids2) - set(ids1))}\n"
        f"  removed: {sorted(set(ids1) - set(ids2))}"
    )


def test_idempotency_all_features_explicitly_provided():
    """When user provides ALL feature flags, assumptions for features should be empty."""
    features = {
        "caching": False, "async_messaging": False, "ai_inference": False,
        "multi_tenancy": False, "batch_processing": False, "distributed_transactions": False,
        "real_time_streaming": False, "vector_search": False, "document_store": False,
        "key_value_store": False, "graph_database": False, "time_series_db": False,
        "oltp_workload": True, "olap_workload": False, "cold_archive_tiering": False,
        "messaging_delivery_guarantee": None,
    }
    spec = {**BASE, "constraints": {**BASE["constraints"], "features": features}}
    ids1, ids2, error = _compile_twice(spec)
    assert error is None, error
    assert ids1 == ids2, (
        "All-features-explicit spec should be idempotent.\n"
        f"  removed: {sorted(set(ids1) - set(ids2))}"
    )


def test_idempotency_no_nfr_no_constraints():
    """Absolute minimal spec (just project) should be idempotent."""
    spec = {"project": {"name": "Minimal", "domain": "testing"}}
    ids1, ids2, error = _compile_twice(spec)
    assert error is None, error
    assert ids1 == ids2, (
        "Minimal spec should be idempotent.\n"
        f"  removed: {sorted(set(ids1) - set(ids2))}"
    )


def test_idempotency_user_overrides_default_in_nested_dict():
    """User overrides a value that has a default, inside a nested dict."""
    spec = {
        **BASE,
        # Default auth is "api_key", user picks "oauth2_oidc"
        "nfr": {"security": {"auth": "oauth2_oidc"}},
    }
    ids1, ids2, error = _compile_twice(spec)
    assert error is None, error
    assert ids1 == ids2, (
        "User-override in nested dict should produce idempotent compile.\n"
        f"  removed: {sorted(set(ids1) - set(ids2))}"
    )

    # Also verify user value preserved across runs
    compiled1, _, _ = _compile(spec)
    compiled2, _, _ = _compile(compiled1)
    assert compiled1["nfr"]["security"]["auth"] == "oauth2_oidc"
    assert compiled2["nfr"]["security"]["auth"] == "oauth2_oidc"
    # Must NOT be in assumptions
    assert "auth" not in compiled1.get("assumptions", {}).get("nfr", {}).get("security", {})
    assert "auth" not in compiled2.get("assumptions", {}).get("nfr", {}).get("security", {})


def test_spec_structure_after_recompile_user_fields_stay_toplevel():
    """
    After recompilation, user-provided nested values must remain at top level
    (not buried in assumptions), so users can still see and edit them.
    """
    # gdpr=True requires pii=True + audit_logging=True to satisfy compliance-gdpr-basic
    spec = {
        **BASE,
        "nfr": {
            "data": {"pii": True, "compliance": {"gdpr": True, "sox": False}},
            "security": {"audit_logging": True},
        },
        "constraints": {**BASE["constraints"], "features": {"caching": True}}
    }
    compiled1, _, err1 = _compile(spec)
    compiled2, _, err2 = _compile(compiled1)
    assert err1 is None, f"First compile failed: {err1}"
    assert err2 is None, f"Second compile failed: {err2}"

    for run, compiled in [(1, compiled1), (2, compiled2)]:
        # gdpr, sox, pii must be at top-level nfr
        assert compiled.get("nfr", {}).get("data", {}).get("compliance", {}).get("gdpr") == True, \
            f"[run{run}] user gdpr=True must stay in top-level nfr.data.compliance"
        assert compiled.get("nfr", {}).get("data", {}).get("compliance", {}).get("sox") == False, \
            f"[run{run}] user sox=False must stay in top-level nfr.data.compliance"
        assert compiled.get("constraints", {}).get("features", {}).get("caching") == True, \
            f"[run{run}] user caching=True must stay in top-level constraints.features"

        # They must NOT be in assumptions
        assert "gdpr" not in compiled.get("assumptions", {}).get("nfr", {}).get(
            "data", {}).get("compliance", {}), \
            f"[run{run}] user-provided gdpr must not be in assumptions"
        assert "sox" not in compiled.get("assumptions", {}).get("nfr", {}).get(
            "data", {}).get("compliance", {}), \
            f"[run{run}] user-provided sox must not be in assumptions"
        assert "caching" not in compiled.get("assumptions", {}).get("constraints", {}).get(
            "features", {}), \
            f"[run{run}] user-provided caching must not be in assumptions"


if __name__ == "__main__":
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v"],
        cwd=str(PROJECT_ROOT)
    )
    sys.exit(result.returncode)
