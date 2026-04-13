"""Tests for constraints.disallowed-saas-providers enforcement."""
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent / "tools"
COMPILER = str(TOOLS_DIR / "archcompiler.py")


def _run_compiler(spec_text: str, tmpdir: str) -> subprocess.CompletedProcess:
    spec_file = Path(tmpdir) / "spec.yaml"
    spec_file.write_text(spec_text)
    return subprocess.run(
        [sys.executable, COMPILER, str(spec_file), "-o", tmpdir],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )


MINIMAL_SPEC = """
project:
  name: Test
  domain: test
functional:
  summary: Test API
constraints:
  cloud: agnostic
  language: python
  platform: api
  saas-providers: {saas}
  disallowed-saas-providers: {disallowed}
"""


def test_disallowed_provider_blocks_pattern():
    """Pattern requiring a disallowed SaaS provider must be rejected."""
    spec = MINIMAL_SPEC.format(saas="[]", disallowed="[netlify]")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_compiler(spec, tmpdir)
        assert result.returncode == 0, result.stderr
        selected_file = Path(tmpdir) / "selected-patterns.yaml"
        selected = yaml.safe_load(selected_file.read_text())
        selected_ids = [p["id"] for p in selected]
        assert "cost-free-saas-tier--netlify" not in selected_ids, (
            "Netlify pattern must be excluded when netlify is in disallowed-saas-providers"
        )


def test_allowed_provider_not_affected():
    """Pattern requiring an allowed provider is still selected normally."""
    # This spec is intentionally warehouse-shaped rather than lakehouse-shaped:
    # tighter serving latency, higher read concurrency than the Snowflake lakehouse
    # default envelope, and no batch-processing signal.
    # Under those conditions, the Snowflake warehouse variant should remain selected
    # when snowflake is allowed and not disallowed.
    spec = """
project:
  name: Test
  domain: test
functional:
  summary: Test API
constraints:
  cloud: aws
  language: python
  platform: api
  saas-providers: [snowflake]
  disallowed-saas-providers: []
  features:
    olap_workload: true
    batch_processing: false
    caching: true
nfr:
  availability:
    target: 0.999
  latency:
    p95Milliseconds: 300
    p99Milliseconds: 1200
  throughput:
    peak_query_per_second_read: 600
    peak_query_per_second_write: 40
  consistency:
    needsReadYourWrites: false
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_compiler(spec, tmpdir)
        assert result.returncode == 0, result.stderr
        selected_file = Path(tmpdir) / "selected-patterns.yaml"
        selected = yaml.safe_load(selected_file.read_text())
        selected_ids = [p["id"] for p in selected]
        assert "data-olap-warehouse--snowflake" in selected_ids, (
            "Snowflake pattern must be selected when snowflake is in saas-providers "
            "and not in disallowed-saas-providers"
        )


def test_contradiction_fails_compilation():
    """Provider in both saas-providers and disallowed-saas-providers must fail compilation."""
    spec = MINIMAL_SPEC.format(saas="[netlify]", disallowed="[netlify]")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_compiler(spec, tmpdir)
        assert result.returncode != 0, (
            "Compiler must fail when a provider is in both saas-providers and disallowed-saas-providers"
        )
        output = result.stdout + result.stderr
        assert "netlify" in output.lower(), (
            "Error message must mention the conflicting provider"
        )


def test_multiple_disallowed_providers():
    """Multiple disallowed providers are each individually enforced."""
    spec = MINIMAL_SPEC.format(saas="[]", disallowed="[netlify, render]")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_compiler(spec, tmpdir)
        assert result.returncode == 0, result.stderr
        selected_file = Path(tmpdir) / "selected-patterns.yaml"
        selected = yaml.safe_load(selected_file.read_text())
        selected_ids = [p["id"] for p in selected]
        assert "cost-free-saas-tier--netlify" not in selected_ids
        assert "cost-free-saas-tier--render" not in selected_ids
        assert "cost-managed-api-hosting-free-lowcost-paas--render" not in selected_ids


def test_empty_disallowed_list_has_no_effect():
    """An empty disallowed-saas-providers list must not affect pattern selection."""
    spec_with = MINIMAL_SPEC.format(saas="[netlify]", disallowed="[]")
    spec_without_field = """
project:
  name: Test
  domain: test
functional:
  summary: Test API
constraints:
  cloud: agnostic
  language: python
  platform: api
  saas-providers: [netlify]
"""
    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        r1 = _run_compiler(spec_with, tmpdir1)
        r2 = _run_compiler(spec_without_field, tmpdir2)
        assert r1.returncode == 0 and r2.returncode == 0
        s1 = {p["id"] for p in yaml.safe_load((Path(tmpdir1) / "selected-patterns.yaml").read_text())}
        s2 = {p["id"] for p in yaml.safe_load((Path(tmpdir2) / "selected-patterns.yaml").read_text())}
        assert s1 == s2, "Empty disallowed list must produce identical output to omitting the field"
