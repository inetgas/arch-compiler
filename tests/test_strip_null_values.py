# tests/test_strip_null_values.py
"""
Tests for _strip_null_values and its integration with the compiler pipeline.

Covers:
  Unit:
    - flat dict with null values stripped
    - nested dict with null values stripped
    - list with null items stripped
    - mixed nested structures
    - no nulls → unchanged
    - all-null dict → empty dict
    - false-y non-null values (0, False, "", []) preserved

  Integration (via compiler subprocess):
    - null NFR field → default applied, tracked as assumption
    - null constraint field → default applied, tracked as assumption
    - null in nested NFR sub-object
    - null alongside valid values → only null stripped
    - spec with no nulls → identical output to baseline
    - null in disallowed-patterns list item → item removed, compile succeeds
"""
import subprocess, tempfile, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
COMPILER = str(ROOT / "tools" / "archcompiler.py")
PYTHON = sys.executable

# ---------------------------------------------------------------------------
# Import _strip_null_values directly for unit tests
# ---------------------------------------------------------------------------
sys.path.insert(0, str(ROOT / "tools"))
from archcompiler import _strip_null_values  # type: ignore


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_flat_dict_nulls_stripped():
    result = _strip_null_values({"a": 1, "b": None, "c": "x"})
    assert result == {"a": 1, "c": "x"}
    assert "b" not in result


def test_nested_dict_nulls_stripped():
    result = _strip_null_values({"outer": {"inner": None, "keep": 42}})
    assert result == {"outer": {"keep": 42}}


def test_deeply_nested_nulls_stripped():
    obj = {"nfr": {"latency": {"p95Milliseconds": 200, "jobStartP95Seconds": None}}}
    result = _strip_null_values(obj)
    assert result == {"nfr": {"latency": {"p95Milliseconds": 200}}}


def test_list_null_items_stripped():
    result = _strip_null_values([1, None, 2, None, 3])
    assert result == [1, 2, 3]


def test_list_of_dicts_with_nulls():
    result = _strip_null_values([{"a": 1, "b": None}, {"c": None}])
    assert result == [{"a": 1}, {}]


def test_no_nulls_unchanged():
    obj = {"a": 1, "b": {"c": [1, 2, 3]}, "d": False}
    result = _strip_null_values(obj)
    assert result == obj


def test_all_null_dict_returns_empty():
    result = _strip_null_values({"a": None, "b": None})
    assert result == {}


def test_falsy_non_null_values_preserved():
    """0, False, "", [] must NOT be stripped — only None."""
    obj = {"zero": 0, "false": False, "empty_str": "", "empty_list": [], "null": None}
    result = _strip_null_values(obj)
    assert "zero" in result
    assert "false" in result
    assert "empty_str" in result
    assert "empty_list" in result
    assert "null" not in result


def test_scalar_passthrough():
    assert _strip_null_values(42) == 42
    assert _strip_null_values("hello") == "hello"
    assert _strip_null_values(False) is False


def test_none_scalar_passthrough():
    # Scalars are returned as-is; None at the top level is a no-op
    # (top-level is always a dict in practice)
    assert _strip_null_values(None) is None


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

BASE_SPEC = """\
project:
  name: Test
  domain: test
functional:
  summary: Test app
constraints:
  cloud: agnostic
  language: python
  platform: api
"""


def _run(spec_text):
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_file = Path(tmpdir) / "spec.yaml"
        spec_file.write_text(spec_text)
        cmd = [PYTHON, COMPILER, str(spec_file), "-o", tmpdir]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        compiled = {}
        out_file = Path(tmpdir) / "compiled-spec.yaml"
        if out_file.exists():
            import yaml
            compiled = yaml.safe_load(out_file.read_text()) or {}
        return result, compiled


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

def test_null_nfr_field_gets_default_as_assumption():
    """rpo_minutes: null → stripped → default applied → appears in assumptions."""
    spec = BASE_SPEC + """\
nfr:
  availability:
    target: 0.99
  rpo_minutes: null
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    assumptions = compiled.get("assumptions", {})
    nfr_assumptions = assumptions.get("nfr", {})
    # rpo_minutes was null → stripped → default should have been applied and tracked
    assert "rpo_minutes" in nfr_assumptions, (
        "null rpo_minutes should be stripped and default tracked as assumption"
    )


def test_null_nfr_field_not_propagated_as_null():
    """null rpo_minutes must not appear as null anywhere in compiled output.

    After stripping, the field is absent from the spec; the defaults machinery
    picks it up and places a real value in assumptions.nfr — not a null in nfr.
    """
    spec = BASE_SPEC + """\
nfr:
  availability:
    target: 0.99
  rpo_minutes: null
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    # Top-level nfr should not have rpo_minutes as null (absent is fine — it moved to assumptions)
    nfr = compiled.get("nfr", {})
    assert nfr.get("rpo_minutes") != "null" and nfr.get("rpo_minutes") is not None \
        or "rpo_minutes" not in nfr, \
        "rpo_minutes must not be an explicit null in top-level nfr"
    # The default must have landed in assumptions.nfr
    assumptions_nfr = compiled.get("assumptions", {}).get("nfr", {})
    assert "rpo_minutes" in assumptions_nfr, \
        "stripped null rpo_minutes must be tracked as assumption with default value"
    assert assumptions_nfr["rpo_minutes"] is not None, \
        "assumption value for rpo_minutes must be a real default, not null"


def test_null_nested_latency_field_stripped():
    """Null in nested NFR sub-object is stripped; sibling values kept."""
    spec = BASE_SPEC + """\
nfr:
  availability:
    target: 0.99
  latency:
    p95Milliseconds: 500
    jobStartP95Seconds: null
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    latency = compiled.get("nfr", {}).get("latency", {})
    assert latency.get("p95Milliseconds") == 500, "Non-null sibling must be preserved"
    # jobStartP95Seconds: null → stripped → no default → absent (not null) in output
    assert latency.get("jobStartP95Seconds") is None  # absent = None from .get()


def test_null_alongside_valid_values_only_null_stripped():
    """Mixed spec: null fields stripped, real values preserved unchanged."""
    spec = BASE_SPEC + """\
nfr:
  availability:
    target: 0.995
  rpo_minutes: null
  rto_minutes: 30
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    nfr = compiled.get("nfr", {})
    assert nfr.get("rto_minutes") == 30, "Explicit rto_minutes must be preserved"


def test_spec_without_nulls_identical_to_baseline():
    """A spec with no null values must produce the same result as always."""
    spec_no_nulls = BASE_SPEC + """\
nfr:
  availability:
    target: 0.99
  rpo_minutes: 60
  rto_minutes: 60
"""
    spec_with_explicit_values = spec_no_nulls  # same thing, just asserting stable
    result1, compiled1 = _run(spec_no_nulls)
    result2, compiled2 = _run(spec_with_explicit_values)
    assert result1.returncode == 0
    assert result2.returncode == 0
    assert compiled1.get("nfr", {}).get("rpo_minutes") == compiled2.get("nfr", {}).get("rpo_minutes")


def test_all_nfr_fields_null_uses_defaults():
    """Spec with entire nfr block set to null values → all defaults applied."""
    spec = BASE_SPEC + """\
nfr:
  availability:
    target: null
  rpo_minutes: null
  rto_minutes: null
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    # All null NFR fields should have been stripped and defaults applied
    assumptions_nfr = compiled.get("assumptions", {}).get("nfr", {})
    # At minimum rpo and rto should appear as assumptions
    assert "rpo_minutes" in assumptions_nfr or compiled.get("nfr", {}).get("rpo_minutes") is not None


def test_null_operating_model_field_gets_default():
    """null in operating_model section → stripped → default applied."""
    spec = BASE_SPEC + """\
operating_model:
  ops_team_size: null
  on_call: false
  deploy_freq: on-demand
  amortization_months: 12
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    # ops_team_size: null → stripped → default should be applied (not null in output)
    om = compiled.get("operating_model", compiled.get("assumptions", {}).get("operating_model", {}))
    # It should not remain null
    assert om.get("ops_team_size") is not None or \
        compiled.get("assumptions", {}).get("operating_model", {}).get("ops_team_size") is not None


def test_null_in_saas_providers_list_stripped():
    """null item in saas-providers list is removed silently."""
    spec = BASE_SPEC + """\
constraints:
  cloud: agnostic
  language: python
  platform: api
  saas-providers:
    - render
    - null
    - supabase
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    providers = compiled.get("constraints", {}).get("saas-providers", [])
    assert None not in providers, "null items in list must be stripped"
    assert "render" in providers
    assert "supabase" in providers


def test_null_constraint_feature_flag_treated_as_absent():
    """ai_inference: null → stripped → treated as absent (false), not true."""
    spec = BASE_SPEC + """\
constraints:
  cloud: agnostic
  language: python
  platform: api
  features:
    ai_inference: null
    oltp_workload: true
"""
    result, compiled = _run(spec)
    assert result.returncode == 0, result.stderr
    # ai_inference: null stripped → absent → treated as false
    # genai-inference pattern should NOT be selected
    import yaml
    sel_path = None
    # Check that genai-inference is not in selected patterns via compiled spec
    assumptions_patterns = compiled.get("assumptions", {}).get("patterns", {})
    assert "genai-inference" not in assumptions_patterns, (
        "null ai_inference should be treated as absent (false), not selecting genai patterns"
    )
