# tests/test_disallowed_patterns.py
import subprocess, tempfile, yaml
from pathlib import Path

COMPILER = str(Path(__file__).parent.parent / "tools" / "archcompiler.py")
ROOT = Path(__file__).parent.parent

SPEC = """
project:
  name: Test
  domain: test
functional:
  summary: Test app
constraints:
  cloud: agnostic
  language: python
  platform: api
disallowed-patterns:
  - resilience-circuit-breaker
"""

def _run(spec_text, extra_args=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_file = Path(tmpdir) / "spec.yaml"
        spec_file.write_text(spec_text)
        cmd = ["python3", COMPILER, str(spec_file), "-o", tmpdir] + (extra_args or [])
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        selected = []
        rejected = []
        sel_file = Path(tmpdir) / "selected-patterns.yaml"
        rej_file = Path(tmpdir) / "rejected-patterns.yaml"
        if sel_file.exists():
            selected = yaml.safe_load(sel_file.read_text()) or []
        if rej_file.exists():
            rejected = yaml.safe_load(rej_file.read_text()) or []
        return result, selected, rejected

def test_schema_accepts_disallowed_patterns_field():
    """Spec with top-level disallowed-patterns must compile (exit 0), and the field
    must be formally declared in canonical-schema.yaml with correct type."""
    # Verify compilation succeeds
    result, _, _ = _run(SPEC, ["-v"])
    assert result.returncode == 0, f"Compilation failed with disallowed-patterns field:\n{result.stdout}"

    # Verify the field is formally declared in the schema (regression guard)
    import yaml as _yaml
    schema_path = ROOT / "schemas" / "canonical-schema.yaml"
    schema = _yaml.safe_load(schema_path.read_text())
    props = schema.get("properties", {})
    assert "disallowed-patterns" in props, (
        "disallowed-patterns not found in canonical-schema.yaml top-level properties"
    )
    field = props["disallowed-patterns"]
    assert field.get("type") == "array", "disallowed-patterns must be type: array"
    assert field.get("items", {}).get("type") == "string", "disallowed-patterns items must be type: string"

def test_disallowed_pattern_is_not_selected():
    """A pattern in disallowed-patterns must not appear in selected-patterns.yaml."""
    result, selected, _ = _run(SPEC, ["-v"])
    assert result.returncode == 0, result.stdout
    selected_ids = [p["id"] for p in selected]
    assert "resilience-circuit-breaker" not in selected_ids

def test_disallowed_pattern_appears_in_rejected_with_reason():
    """A disallowed pattern must appear in rejected-patterns.yaml with a clear reason."""
    result, _, rejected = _run(SPEC, ["-v"])
    assert result.returncode == 0, result.stdout
    rejected_ids = {p["id"]: p for p in rejected}
    assert "resilience-circuit-breaker" in rejected_ids, "Disallowed pattern missing from rejected-patterns"
    reason = rejected_ids["resilience-circuit-breaker"]["reason"]
    assert "disallowed-patterns" in reason, f"Reason does not mention disallowed-patterns: {reason}"

def test_disallowed_pattern_rejected_phase_label():
    """Rejected entry must have correct phase label."""
    result, _, rejected = _run(SPEC, ["-v"])
    assert result.returncode == 0, result.stdout
    rejected_ids = {p["id"]: p for p in rejected}
    assert "resilience-circuit-breaker" in rejected_ids
    assert rejected_ids["resilience-circuit-breaker"]["phase"] == "phase_2_5_disallowed_patterns"

def test_multiple_patterns_can_be_disallowed():
    """Multiple patterns in disallowed-patterns must all be excluded."""
    spec = """
project:
  name: Test
  domain: test
functional:
  summary: Test app
constraints:
  cloud: agnostic
  language: python
  platform: api
disallowed-patterns:
  - resilience-circuit-breaker
  - resilience-timeouts-retries-backoff
"""
    result, selected, rejected = _run(spec, ["-v"])
    assert result.returncode == 0, result.stdout
    selected_ids = [p["id"] for p in selected]
    assert "resilience-circuit-breaker" not in selected_ids
    assert "resilience-timeouts-retries-backoff" not in selected_ids
    rejected_ids = [p["id"] for p in rejected]
    assert "resilience-circuit-breaker" in rejected_ids
    assert "resilience-timeouts-retries-backoff" in rejected_ids

def test_empty_disallowed_patterns_has_no_effect():
    """Empty disallowed-patterns list must not change selected patterns."""
    spec_without = """
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
    spec_with_empty = spec_without + "disallowed-patterns: []\n"
    _, selected_without, _ = _run(spec_without)
    _, selected_with, _ = _run(spec_with_empty)
    ids_without = {p["id"] for p in selected_without}
    ids_with = {p["id"] for p in selected_with}
    assert ids_without == ids_with, "Empty disallowed-patterns changed pattern selection"

def test_unknown_disallowed_pattern_id_rejects():
    """A pattern ID in disallowed-patterns that doesn't exist in registry must cause a hard error."""
    spec = """
project:
  name: Test
  domain: test
functional:
  summary: Test app
constraints:
  cloud: agnostic
  language: python
  platform: api
disallowed-patterns:
  - this-pattern-does-not-exist
"""
    result, _, _ = _run(spec, ["-v"])
    assert result.returncode != 0, "Unknown disallowed pattern ID must cause non-zero exit"
    assert "this-pattern-does-not-exist" in result.stderr, \
        "Error about unknown pattern ID must appear in stderr"
    assert "not found in registry" in result.stderr, \
        "Error must say pattern was not found in registry"

def test_flutter_spec_disallows_observability_patterns():
    """Integration: Flutter spec with ops patterns disallowed must compile cleanly without them."""
    spec_path = Path(__file__).parent.parent / "test-specs" / "disallowed_patterns_ops-patterns-excluded_pass.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["python3", COMPILER, str(spec_path), "-o", tmpdir, "-v"],
            capture_output=True, text=True, cwd=ROOT
        )
        assert result.returncode == 0, f"Compilation failed:\n{result.stdout}"
        selected = yaml.safe_load((Path(tmpdir) / "selected-patterns.yaml").read_text()) or []
        rejected = yaml.safe_load((Path(tmpdir) / "rejected-patterns.yaml").read_text()) or []
        selected_ids = [p["id"] for p in selected]
        rejected_map = {p["id"]: p for p in rejected}

        assert "ops-low-cost-observability" not in selected_ids
        assert "ops-slo-error-budgets" not in selected_ids
        assert "ops-low-cost-observability" in rejected_map
        assert "ops-slo-error-budgets" in rejected_map
        assert rejected_map["ops-low-cost-observability"]["phase"] == "phase_2_5_disallowed_patterns"
        assert rejected_map["ops-slo-error-budgets"]["phase"] == "phase_2_5_disallowed_patterns"
