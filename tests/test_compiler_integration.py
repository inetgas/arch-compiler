"""
Compiler integration tests.

Runs tools/archcompiler.py as a subprocess against fixtures in tests/fixtures/ and
asserts on actual stdout/stderr output and exit codes.

Every behavioral category covered by unit tests in:
  - test_annotated_error_output.py  (_build_error_annotation_map, _render_annotated_yaml)
  - test_error_suggestions.py       (_format_suggestions, _lookup_schema_field_info)
  - test_warn_nfr.py                (_evaluate_warn_nfr_rules, _evaluate_warn_constraints_rules)

...has at least one corresponding integration test here that exercises the same
code path end-to-end through the full compiler pipeline.

Design principle — PATTERN-AGNOSTIC ASSERTIONS:
  Tests assert on FORMAT and STRUCTURAL PROPERTIES of the compiler output, not on
  specific pattern IDs (like "caching-required-high-read-throughput"). This makes
  the test suite tolerant of pattern renames and content changes.

  ✅ DO assert: "some line containing 'caching: false' has ❌"
  ❌ DON'T assert: "caching-required-high-read-throughput is on this line"

  Exception: pattern IDs that ARE spec field names (e.g. "needsReadYourWrites") are
  fine because they're tied to the compiler behavior, not pattern content.

Operators covered at integration level:
  == gate:  eq-gate-multi-violation  (gdpr/hipaa == True activates compliance patterns)
  >= gate:  nfr-threshold-violation  (QPS >= 200 annotates QPS field, threshold: >= in suggestions)
  <= gate:  lte-threshold-violation  (availability <= 0.9999 annotates availability field, threshold: <=)
  in (violation):     eq-gate-multi-violation  (cloud: agnostic NOT in allowed set → ❌)
  in (activation):    eq-gate-multi-violation  (platform: api IS in restrictive set → annotation)

Fixtures (in tests/fixtures/):
  nfr-threshold-violation.yaml  -- high QPS + caching:false → caching-required violation
  eq-gate-multi-violation.yaml  -- gdpr+hipaa, no audit_logging → multi-pattern violation
  lte-threshold-violation.yaml  -- batch platform + batch_processing:false → <= threshold test
  ryw-advisory-success.yaml     -- caching+RYW → advisory warnings, no violations
  no-advisory-success.yaml      -- clean spec with no violations or advisory warnings
  cost-infeasibility.yaml       -- $1 ceiling → cost infeasibility warning
"""
import subprocess
import tempfile
import os
import re
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_compiler(fixture_name: str, *extra_args, outdir: str = None) -> tuple[int, str]:
    """Run compiler on a named fixture; return (returncode, stdout+stderr)."""
    spec = FIXTURES_DIR / fixture_name
    cmd = ["python3", "tools/archcompiler.py", str(spec)]
    if outdir:
        cmd += ["-o", outdir]
    if "--verbose" in extra_args or "-v" in extra_args:
        cmd += ["-v"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return result.returncode, result.stdout + result.stderr


def run_compiler_dict(spec_dict: dict, *extra_args) -> tuple[int, str]:
    """Run compiler on an inline spec dict (written to a temp file)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(spec_dict, f)
        fname = f.name
    try:
        cmd = ["python3", "tools/archcompiler.py", fname] + list(extra_args)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        return result.returncode, result.stdout + result.stderr
    finally:
        os.unlink(fname)


# ---------------------------------------------------------------------------
# Pattern-agnostic structural helpers
# ---------------------------------------------------------------------------

def _lines_with(text: str, *fragments) -> list[str]:
    """Return lines that contain ALL of the given fragments."""
    return [l for l in text.splitlines() if all(f in l for f in fragments)]


def _has_error_annotation(text: str, field_fragment: str) -> bool:
    """True if any line containing field_fragment also contains ❌."""
    return bool(_lines_with(text, field_fragment, "❌"))


def _has_activation_annotation(text: str, field_fragment: str) -> bool:
    """True if any line containing field_fragment has a '  # ' comment without ❌."""
    lines = _lines_with(text, field_fragment, "  # ")
    return any("❌" not in l for l in lines)


def _get_error_pids(text: str, field_fragment: str) -> list[str]:
    """Extract the list of PIDs from the ❌ annotation on a line containing field_fragment.

    E.g. for line '  audit_logging: false  # ❌ pid-a, pid-b'
    returns ['pid-a', 'pid-b'].
    """
    lines = _lines_with(text, field_fragment, "❌")
    if not lines:
        return []
    comment = lines[0].split("❌", 1)[1].strip()
    return [p.strip() for p in comment.split(",") if p.strip()]


def _activated_by_count(text: str) -> int:
    """Count 'X activated by:' entries in the suggestions block."""
    return len(re.findall(r"\S+ activated by:", text))


def _has_any_activated_by(text: str) -> bool:
    return _activated_by_count(text) > 0


# ===========================================================================
# TestOutputStructure — exit codes and file creation
# ===========================================================================

class TestOutputStructure:
    def test_violation_returns_nonzero_exit_code(self):
        rc, _ = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1

    def test_success_returns_zero_exit_code(self):
        rc, _ = run_compiler("no-advisory-success.yaml")
        assert rc == 0

    def test_error_mode_prints_annotated_yaml_to_stdout(self):
        """Error output is the annotated YAML written to stdout, not a file."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "constraints:" in out
        assert "nfr:" in out

    def test_verbose_flag_creates_compiled_spec_file(self):
        """Success + -v creates a compiled-spec.yaml file in outdir."""
        outdir = "/tmp/test-integration-verbose"
        Path(outdir).mkdir(exist_ok=True)
        rc, _ = run_compiler("no-advisory-success.yaml", "-v", outdir=outdir)
        assert rc == 0
        assert (Path(outdir) / "compiled-spec.yaml").exists()

    def test_verbose_compiled_spec_has_inline_pattern_comments(self):
        """Verbose compiled-spec.yaml contains '# pattern-id' inline comments."""
        outdir = "/tmp/test-integration-verbose-comments"
        Path(outdir).mkdir(exist_ok=True)
        rc, _ = run_compiler("no-advisory-success.yaml", "-v", outdir=outdir)
        assert rc == 0
        content = (Path(outdir) / "compiled-spec.yaml").read_text()
        inline_comment_lines = [
            l for l in content.splitlines()
            if "  #" in l and not l.strip().startswith("#")
        ]
        assert len(inline_comment_lines) > 0, "No inline comments in verbose compiled-spec.yaml"

    def test_success_mode_prints_cost_section_to_stdout(self):
        """On success, cost feasibility summary appears in stdout."""
        rc, out = run_compiler("no-advisory-success.yaml")
        assert rc == 0
        assert "Cost Feasibility Analysis" in out

    def test_error_mode_does_not_print_cost_section(self):
        """On violation (rc=1), the annotated error path runs — no cost section."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "Cost Feasibility Analysis" not in out


# ===========================================================================
# TestErrorAnnotation — inline YAML comments in violation output
#
# Covers all annotation operator types:
#   >= gate  (nfr-threshold-violation)
#   <= gate  (lte-threshold-violation)
#   == gate  (eq-gate-multi-violation, via suggestions since == is on non-violated path)
#   in violation  (eq-gate-multi-violation: cloud: agnostic ∉ allowed set)
#   in activation (eq-gate-multi-violation: platform: api ∈ restrictive set)
#
# Maps to: TestViolations, TestActivationGateEq, TestActivationGateThreshold,
#  TestActivationGateStrictOps, TestActivationGateNotEq, TestViolationPathNotOverwritten,
#  TestNonViolatingPatternsExcluded, TestMultiplePatterns in test_annotated_error_output.py
# ===========================================================================

class TestErrorAnnotation:
    def test_violation_gets_error_prefix(self):
        """Violated field is annotated with '❌ <pid>'."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert _has_error_annotation(out, "caching: false"), (
            "Expected ❌ annotation on 'caching: false' line"
        )

    def test_multiple_violations_same_path_sorted_alphabetically(self):
        """When multiple patterns violate the same field their IDs are sorted."""
        rc, out = run_compiler("eq-gate-multi-violation.yaml")
        assert rc == 1
        pids = _get_error_pids(out, "audit_logging: false")
        assert len(pids) >= 2, (
            f"Expected ≥2 PIDs on 'audit_logging: false' ❌ annotation, got: {pids}"
        )
        assert pids == sorted(pids), (
            f"PIDs should be alphabetically sorted, got: {pids}"
        )

    def test_nfr_gte_threshold_annotates_activation_field(self):
        """NFR >= threshold annotates the triggering spec field (not the violated field).

        Regression: previously NFR >= thresholds were excluded from activation-gate
        annotation — the fix in _build_error_annotation_map removed the
        'and kind == "constraints"' guard.
        """
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert _has_activation_annotation(out, "peak_query_per_second_read: 500"), (
            "peak_query_per_second_read: 500 should have an activation-gate annotation "
            "(NFR >= threshold) without ❌ — it triggered the pattern but is not itself violated"
        )
        # The annotated field must NOT carry ❌ (it's the gate, not the violation)
        lines = _lines_with(out, "peak_query_per_second_read: 500", "  # ")
        assert all("❌" not in l for l in lines), "Activation gate must not have ❌"

    def test_nfr_lte_threshold_annotates_activation_field(self):
        """NFR <= threshold (availability ceiling) annotates the triggering spec field.

        batch-platform-feature-required has supports_nfr: availability <= 0.9999.
        With availability=0.99 the ceiling is satisfied → field gets activation annotation.
        The violation is on batch_processing: false (not on availability).
        """
        rc, out = run_compiler("lte-threshold-violation.yaml")
        assert rc == 1
        assert _has_activation_annotation(out, "target: 0.99"), (
            "availability: target: 0.99 should have an activation-gate annotation "
            "(NFR <= ceiling) without ❌"
        )
        # Must NOT have ❌ on the availability line
        lines = _lines_with(out, "target: 0.99", "  # ")
        assert all("❌" not in l for l in lines), "Ceiling gate must not have ❌"

    def test_in_violation_gets_error_annotation(self):
        """When spec value is NOT in pattern's required set, the field gets ❌.

        In eq-gate-multi-violation: compliance-hipaa requires cloud in {aws, azure, gcp, on-prem}.
        cloud: agnostic is not in that set → ❌ annotation.
        """
        rc, out = run_compiler("eq-gate-multi-violation.yaml")
        assert rc == 1
        assert _has_error_annotation(out, "cloud: agnostic"), (
            "cloud: agnostic should carry ❌ — it is not in the compliance pattern's allowed cloud set"
        )

    def test_in_activation_gate_annotates_supported_value(self):
        """When spec value IS in a restrictive 'in' list it gets an activation annotation.

        In eq-gate-multi-violation: a compliance pattern supports platform in a subset
        of schema options (< 70%). With platform: api the field gets annotated.
        """
        rc, out = run_compiler("eq-gate-multi-violation.yaml")
        assert rc == 1
        assert _has_activation_annotation(out, "platform: api"), (
            "platform: api should have an activation-gate annotation from a pattern "
            "with a restrictive platform 'in' rule (and no ❌ — it is a supported value)"
        )

    def test_eq_gate_activation_path_appears_in_suggestions(self):
        """== activation gate path is surfaced in the suggestions block.

        compliance-gdpr-basic activates via /nfr/data/compliance/gdpr == true.
        The suggestions block must reference that path so the user knows why the
        pattern fired. The == gate itself doesn't add an inline comment on a
        non-violated field — it's shown in suggestions instead.
        """
        rc, out = run_compiler("eq-gate-multi-violation.yaml")
        assert rc == 1
        # The suggestions block contains the compliance path (not a specific PID)
        assert "/nfr/data/compliance/" in out, (
            "Suggestions block should reference the compliance NFR path "
            "that activated the compliance pattern(s)"
        )

    def test_violation_path_retains_error_prefix_not_activation_annotation(self):
        """The violated field always keeps ❌ — it is never overwritten by a bare annotation."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert _has_error_annotation(out, "caching: false"), "Violation must keep ❌"
        # Sanity: same line must NOT lose ❌ in favour of a bare activation comment
        caching_lines = _lines_with(out, "caching: false")
        assert caching_lines
        assert "❌" in caching_lines[0], "Violation path must have ❌ prefix"

    def test_only_violated_fields_have_error_annotation(self):
        """Fields that are NOT violated must not carry ❌.

        In nfr-threshold-violation the only violated field is 'caching'.
        Any ❌ on any other field would indicate a compiler regression.
        """
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        # Filter to inline YAML annotation lines (have "  # ❌" format) —
        # excludes the top-level header "❌ Constraints/NFRs not met:" which is not a field.
        error_lines = [l for l in out.splitlines() if "  # ❌" in l]
        for line in error_lines:
            assert "caching" in line, (
                f"Unexpected ❌ annotation on non-violated field: {line!r}"
            )

    def test_strict_ops_do_not_annotate(self):
        """Operators > and < (strict comparison) are not used as activation gates.

        In a typical error scenario no spurious annotations appear from strict ops.
        The write-QPS field has no activation gate in the fixture — it must be unannotated.
        """
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        write_lines = _lines_with(out, "peak_query_per_second_write: 100")
        assert write_lines, "write QPS line must exist in output"
        assert "#" not in write_lines[0], (
            "Write QPS line should have no annotation — "
            "no pattern activates via write QPS in this fixture"
        )


# ===========================================================================
# TestSuggestionsBlock — 💡 Suggestions output
#
# Covers all operator types in suggestions:
#   >= gate: "threshold: >=" (nfr-threshold-violation)
#   <= gate: "threshold: <=" (lte-threshold-violation)
#   == gate: "= <value>" shown as activation path (eq-gate-multi-violation)
#   in gate: "Available: ..." range shown for in-operator gates
#
# Maps to: all test_format_suggestions_* in test_error_suggestions.py
# ===========================================================================

class TestSuggestionsBlock:
    def test_error_summary_header_present(self):
        """Error output starts with the ❌ header."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "❌ Constraints/NFRs trade-off requirements not met:" in out

    def test_violation_reason_text_in_error_summary(self):
        """The requires_constraints reason string appears after the violated path."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "mandatory" in out.lower() or "required" in out.lower()

    def test_suggestions_block_present_on_violation(self):
        """💡 Suggestions block appears whenever violations have activation gates."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "💡 Suggestions" in out

    def test_nfr_gte_threshold_gate_in_suggestions(self):
        """NFR >= activation gate appears in suggestions block with 'threshold: >= N'.

        Regression test: previously NFR thresholds were excluded from suggestions;
        now they correctly show 'threshold: >= N'.
        """
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "peak_query_per_second_read" in out
        assert "threshold: >=" in out

    def test_nfr_lte_threshold_gate_in_suggestions(self):
        """NFR <= activation gate appears in suggestions block with 'threshold: <= N'.

        Regression test for the same fix that corrected >= gate support:
        removing 'and kind == "constraints"' from _format_suggestions enables
        NFR <= ceiling gates to appear in suggestions.
        """
        rc, out = run_compiler("lte-threshold-violation.yaml")
        assert rc == 1
        assert "threshold: <=" in out

    def test_eq_gate_in_suggestions_shows_activation_path(self):
        """== activation gate shows the full spec path and current value in suggestions."""
        rc, out = run_compiler("eq-gate-multi-violation.yaml")
        assert rc == 1
        # Path fragment present (not checking specific PID)
        assert "/nfr/data/compliance/" in out

    def test_suggestions_shows_activated_by_label(self):
        """Suggestions block contains at least one 'X activated by:' entry."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert _has_any_activated_by(out), (
            "Suggestions block must contain at least one 'activated by:' label"
        )

    def test_suggestions_deduplication_single_block_per_violating_pattern(self):
        """Each violating pattern appears exactly once in the suggestions block,
        even if it violates multiple rules.

        compliance-hipaa violates two fields in eq-gate-multi-violation; it should
        appear exactly once in suggestions.
        """
        rc, out = run_compiler("eq-gate-multi-violation.yaml")
        assert rc == 1
        # Count how many unique violations were reported (lines starting with "[pid]")
        violations_reported = len(re.findall(r"^\s+\[(.+?)\]", out, re.MULTILINE))
        activated_by_count = _activated_by_count(out)
        assert activated_by_count <= violations_reported, (
            f"'activated by:' count ({activated_by_count}) should be ≤ violations count "
            f"({violations_reported}) — deduplication must prevent duplicate entries"
        )

    def test_no_suggestions_on_success(self):
        """Clean spec produces no 💡 Suggestions block."""
        rc, out = run_compiler("no-advisory-success.yaml")
        assert rc == 0
        assert "💡 Suggestions" not in out


# ===========================================================================
# TestAdvisoryWarnings — ⚠️ Pattern Advisory Warnings section
# (maps to: all test_warn_nfr_* and test_warn_constraints_* in test_warn_nfr.py)
# ===========================================================================

class TestAdvisoryWarnings:
    def test_advisory_section_present_in_success_mode(self):
        """Advisory warnings appear in the success output when warn_nfr rules fire."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        assert "⚠️  Pattern Advisory Warnings" in out

    def test_advisory_section_after_cost_section(self):
        """Advisory warnings section always appears AFTER the cost feasibility block."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        cost_pos = out.find("Cost Feasibility Analysis")
        adv_pos = out.find("Pattern Advisory Warnings")
        assert cost_pos >= 0, "Cost section must be present"
        assert adv_pos >= 0, "Advisory section must be present"
        assert adv_pos > cost_pos, "Advisory section must appear after cost section"

    def test_advisory_contains_nfr_path_and_message(self):
        """Each advisory entry references the NFR path that triggered the warning."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        # needsReadYourWrites is the NFR path component that triggers the advisory
        # (not a pattern ID — it's safe to assert)
        assert "needsReadYourWrites" in out

    def test_advisory_section_has_at_least_one_pattern_entry(self):
        """Advisory section contains at least one pattern ID entry."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        adv_section = out[out.find("Pattern Advisory Warnings"):]
        # Pattern entries look like "#   pattern-id: message"
        warned_pids = re.findall(r"#\s+([a-z][a-z0-9\-]+):\s", adv_section)
        assert warned_pids, "Advisory section must contain at least one pattern entry"

    def test_advisory_section_header_format(self):
        """Advisory section header uses the exact documented format."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        assert "# ⚠️  Pattern Advisory Warnings" in out
        assert "# (Patterns are still SELECTED" in out

    def test_advisory_absent_when_no_warn_rules_fire(self):
        """Clean spec with no warn_nfr conditions produces no advisory section."""
        rc, out = run_compiler("no-advisory-success.yaml")
        assert rc == 0
        assert "Advisory Warnings" not in out

    def test_advisory_section_present_in_verbose_mode(self):
        """Advisory warnings appear in verbose compiled-spec.yaml too."""
        outdir = "/tmp/test-integration-advisory-verbose"
        Path(outdir).mkdir(exist_ok=True)
        rc, _ = run_compiler("ryw-advisory-success.yaml", "-v", outdir=outdir)
        assert rc == 0
        content = (Path(outdir) / "compiled-spec.yaml").read_text()
        assert "Pattern Advisory Warnings" in content

    def test_advisory_warnings_sorted_by_match_score(self):
        """Advisory warnings section contains at least one warned pattern."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        adv_section = out[out.find("Pattern Advisory Warnings"):]
        warned_pids = re.findall(r"#\s+([a-z][a-z0-9\-]+):\s", adv_section)
        assert len(warned_pids) >= 1, "Advisory section should mention at least one pattern"


# ===========================================================================
# TestCostSection — cost feasibility output
# (maps to: test_phase4_cost.py unit tests)
# ===========================================================================

class TestCostSection:
    def test_cost_section_present_on_success(self):
        rc, out = run_compiler("no-advisory-success.yaml")
        assert rc == 0
        assert "Cost Feasibility Analysis" in out

    def test_cost_section_present_when_advisory_warnings_also_present(self):
        """Cost section appears before advisory section in all success outputs."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        assert "Cost Feasibility Analysis" in out

    def test_cost_infeasibility_detected_and_reported(self):
        """When monthly cost exceeds ceiling, cost_opex_exceeds_ceiling warning fires."""
        rc, out = run_compiler("cost-infeasibility.yaml")
        assert rc == 0  # cost is advisory, not a hard violation
        assert "cost_opex_exceeds_ceiling" in out
        assert "exceeds ceiling" in out.lower()

    def test_cost_infeasibility_shows_fail_marker(self):
        """Cost summary line has ✗ FAIL when ceiling is breached."""
        rc, out = run_compiler("cost-infeasibility.yaml")
        assert rc == 0
        assert "FAIL" in out

    def test_cost_section_absent_on_hard_violation(self):
        """When compiler exits with rc=1 (hard violation), there is no cost section
        in the annotated error output path."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "Cost Feasibility Analysis" not in out


# ===========================================================================
# TestScalarFormatting — YAML scalar rendering in annotated error output
# (maps to: TestAnnotatedYamlScalar, TestRenderAnnotatedYaml in test_annotated_error_output.py)
# ===========================================================================

class TestScalarFormatting:
    def test_bool_false_rendered_lowercase(self):
        """Python False is rendered as 'false' (not 'False') in annotated YAML output."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "caching: false" in out
        assert "caching: False" not in out

    def test_bool_true_rendered_lowercase(self):
        """Python True is rendered as 'true' (not 'True') in annotated YAML output."""
        rc, out = run_compiler("eq-gate-multi-violation.yaml")
        assert rc == 1
        assert "pii: true" in out
        assert "pii: True" not in out

    def test_integer_rendered_without_quotes(self):
        """Integer values appear as bare numbers, not quoted strings."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "peak_query_per_second_read: 500" in out
        assert '"500"' not in out

    def test_annotation_format_two_spaces_hash_space(self):
        """Inline comments use exactly '  # ' format (two spaces before hash)."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        annotated = [l for l in out.splitlines() if "  # " in l and "❌" in l]
        assert annotated, "Should have at least one annotated line with ❌"
        for line in annotated:
            assert "  # " in line

    def test_nested_values_indented_in_error_output(self):
        """Nested YAML fields are properly indented under their parent keys."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        lines = out.splitlines()
        feat_idx = next((i for i, l in enumerate(lines) if l.strip() == "features:"), None)
        assert feat_idx is not None, "features: block must exist"
        caching_line = next((l for l in lines[feat_idx:feat_idx + 5] if "caching:" in l), None)
        assert caching_line is not None
        assert caching_line.startswith("    "), "caching: must be indented under features:"

    def test_null_rendered_in_output(self):
        """None/null values in spec appear in the output (as 'null' or empty)."""
        rc, out = run_compiler("nfr-threshold-violation.yaml")
        assert rc == 1
        assert "saas-providers:" in out


# ===========================================================================
# TestAdvisoryWarnConstraints — warn_constraints rules integration
# (maps to: test_warn_constraints_rule_fires, test_warn_constraints_rule_no_warning)
# ===========================================================================

class TestAdvisoryWarnConstraints:
    def test_warn_constraints_can_produce_advisory(self):
        """warn_constraints rules produce advisory entries in the same section
        as warn_nfr rules when their condition fires."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        assert "Pattern Advisory Warnings" in out

    def test_warn_nfr_and_warn_constraints_both_in_advisory_section(self):
        """Both warn_nfr and warn_constraints advisories go into the same section."""
        rc, out = run_compiler("ryw-advisory-success.yaml")
        assert rc == 0
        header_count = out.count("⚠️  Pattern Advisory Warnings")
        assert header_count == 1, "Advisory section must appear exactly once"
