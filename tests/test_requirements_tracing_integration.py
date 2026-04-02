#!/usr/bin/env python3
"""
Integration test for requirements tracing in verbose mode.
"""
import subprocess
import yaml
from pathlib import Path


def test_requirements_tracing_verbose():
    """Test that verbose mode adds inline comments to compiled-spec.yaml."""
    output_dir = Path("/tmp/test-req-trace-integration")
    output_dir.mkdir(exist_ok=True)

    # Compile with verbose mode
    result = subprocess.run([
        "python3", "tools/archcompiler.py",
        "test-specs/misc_persona_enterprise-production-full-requirements_pass.yaml",
        "-o", str(output_dir),
        "-v"
    ], capture_output=True, text=True)

    assert result.returncode == 0, f"Compilation failed: {result.stderr}"

    # Read compiled-spec.yaml as text (to check comments)
    compiled_spec_path = output_dir / "compiled-spec.yaml"
    assert compiled_spec_path.exists(), "compiled-spec.yaml not created"

    content = compiled_spec_path.read_text()

    # Check that inline comments with pattern names exist
    lines_with_comments = [line for line in content.split('\n') if ' #' in line and not line.strip().startswith('#')]
    assert len(lines_with_comments) > 0, "No inline comments found in verbose mode"

    # Extract selected patterns from the patterns: section
    patterns_section = content.split('patterns:')[1].split('\n')
    selected_patterns = set()
    for line in patterns_section:
        if ':' in line and not line.strip().startswith('#'):
            pattern_id = line.split(':')[0].strip()
            if pattern_id and pattern_id[0].islower():  # Valid pattern ID
                selected_patterns.add(pattern_id)

    assert len(selected_patterns) > 0, "No selected patterns found"

    # Verify that all patterns mentioned in requirements comments are in the selected set.
    # Requirements comments (on spec fields like nfr/constraints) look like "# pid1, pid2, ...".
    # Description comments (on pattern keys) contain free-form text and must be excluded.
    import re
    comment_patterns = set()
    for line in lines_with_comments:
        if ' #' not in line:
            continue
        key_part = line.split(':')[0].strip()
        # Skip lines where the key itself is a pattern ID (these are description comments)
        if key_part in selected_patterns:
            continue
        comment = line.split(' #')[1].strip()
        for pattern in comment.split(','):
            pattern = pattern.strip()
            # Valid pattern IDs start with lowercase and contain only lowercase, digits, hyphens
            if pattern and re.match(r'^[a-z][a-z0-9-]+$', pattern):
                comment_patterns.add(pattern)

    # All patterns in requirements comments must be in selected patterns
    extra_patterns = comment_patterns - selected_patterns
    assert len(extra_patterns) == 0, f"Requirements comments contain patterns not in selected set: {extra_patterns}"

    # Verify at least one selected pattern appears in requirements comments
    assert len(comment_patterns & selected_patterns) > 0, "No selected patterns found in requirements comments"

    # Per user feedback: cost/operating_model fields should NOT have pattern comments
    # because patterns are not directly contributing to these fields
    # So we verify NO comment on monthly_operational_usd
    lines_with_cost = [line for line in content.split('\n') if 'monthly_operational_usd' in line]
    if lines_with_cost:
        # Should not have inline comment with pattern names
        assert '#' not in lines_with_cost[0], "Cost field should not have any comments"

    # Verify still valid YAML despite comments
    with open(compiled_spec_path) as f:
        spec = yaml.safe_load(f)

    assert spec is not None, "Failed to parse commented YAML"
    assert "constraints" in spec
    assert "nfr" in spec

    print("✅ Integration test passed: requirements tracing in verbose mode works")


def test_non_verbose_no_comments():
    """Test that non-verbose mode has no inline comments."""
    output_dir = Path("/tmp/test-req-trace-no-verbose")
    output_dir.mkdir(exist_ok=True)

    # Compile without verbose mode
    result = subprocess.run([
        "python3", "tools/archcompiler.py",
        "test-specs/misc_persona_enterprise-production-full-requirements_pass.yaml",
        "-o", str(output_dir)
    ], capture_output=True, text=True)

    assert result.returncode == 0, f"Compilation failed: {result.stderr}"

    # Read compiled-spec.yaml as text
    compiled_spec_path = output_dir / "compiled-spec.yaml"
    content = compiled_spec_path.read_text()

    # Check that NO pattern comments exist (no inline comments with pattern names)
    # Patterns should not appear as inline comments in non-verbose mode
    lines = content.split('\n')
    inline_comments = [line for line in lines if ' #' in line and not line.strip().startswith('#')]

    # Should have no inline comments with pattern names
    # Check for any lowercase-hyphenated identifiers in comments (pattern naming convention)
    import re
    has_pattern_comments = any(re.search(r'#\s*[a-z][a-z0-9-]+', line) for line in inline_comments)
    assert not has_pattern_comments, "Unexpected pattern comment in non-verbose mode"

    print("✅ Integration test passed: non-verbose mode has no comments")


def test_verbose_assumptions_patterns_have_description_comments():
    """In verbose mode, each pattern key in assumptions.patterns has a description as EOL comment."""
    output_dir = Path("/tmp/test-verbose-pattern-desc-assumptions")
    output_dir.mkdir(exist_ok=True)

    # Minimal spec has no user-provided patterns, so all go into assumptions.patterns
    result = subprocess.run([
        "python3", "tools/archcompiler.py",
        "test-specs/input_minimal_required-fields-only_pass.yaml",
        "-o", str(output_dir),
        "-v"
    ], capture_output=True, text=True)

    assert result.returncode == 0, f"Compilation failed: {result.stderr}"

    # Get selected pattern IDs to know what to look for
    selected = yaml.safe_load((output_dir / "selected-patterns.yaml").read_text())
    selected_ids = {p["id"] for p in selected}
    assert len(selected_ids) > 0, "No selected patterns"

    content = (output_dir / "compiled-spec.yaml").read_text()
    lines = content.split("\n")

    # Every pattern ID key found in the file must have an inline description comment
    for pid in selected_ids:
        # Find the line where this pattern is a YAML key
        key_line = next((l for l in lines if l.lstrip().startswith(f"{pid}:")), None)
        assert key_line is not None, f"Pattern key '{pid}' not found in compiled-spec.yaml"
        assert " #" in key_line, (
            f"Pattern '{pid}' in assumptions.patterns is missing a description comment.\n"
            f"  Line: {key_line!r}"
        )
        comment = key_line.split(" #", 1)[1].strip()
        assert len(comment) > 5, f"Description comment for '{pid}' is too short: {comment!r}"


def test_verbose_user_patterns_have_description_comments():
    """In verbose mode, pattern keys in top-level patterns section have a description as EOL comment."""
    output_dir = Path("/tmp/test-verbose-pattern-desc-user")
    output_dir.mkdir(exist_ok=True)

    # This spec has patterns.arch-serverless--aws as user-provided config (top-level patterns)
    result = subprocess.run([
        "python3", "tools/archcompiler.py",
        "test-specs/config_override_verbose-pattern-config-multiple-overrides_pass.yaml",
        "-o", str(output_dir),
        "-v"
    ], capture_output=True, text=True)

    assert result.returncode == 0, f"Compilation failed: {result.stderr}"

    content = (output_dir / "compiled-spec.yaml").read_text()
    lines = content.split("\n")

    # arch-serverless--aws should appear in top-level patterns (user-provided, not in assumptions)
    pid = "arch-serverless--aws"
    key_line = next((l for l in lines if l.lstrip().startswith(f"{pid}:")), None)
    assert key_line is not None, f"'{pid}' key not found in compiled-spec.yaml"
    assert " #" in key_line, (
        f"'{pid}' in top-level patterns is missing a description comment.\n"
        f"  Line: {key_line!r}"
    )
    comment = key_line.split(" #", 1)[1].strip()
    assert len(comment) > 10, f"Description comment for '{pid}' too short: {comment!r}"
    # Verify comment is the actual pattern description (not a requirements comment)
    assert "serverless" in comment.lower() or "event" in comment.lower() or "function" in comment.lower(), (
        f"Comment doesn't look like arch-serverless--aws description: {comment!r}"
    )


def test_non_verbose_no_description_comments_on_pattern_keys():
    """In non-verbose mode, pattern keys have no description comments."""
    output_dir = Path("/tmp/test-non-verbose-no-pattern-desc")
    output_dir.mkdir(exist_ok=True)

    result = subprocess.run([
        "python3", "tools/archcompiler.py",
        "test-specs/input_minimal_required-fields-only_pass.yaml",
        "-o", str(output_dir)
    ], capture_output=True, text=True)

    assert result.returncode == 0, f"Compilation failed: {result.stderr}"

    # Load selected pattern IDs
    selected = yaml.safe_load((output_dir / "selected-patterns.yaml").read_text())
    selected_ids = {p["id"] for p in selected}

    content = (output_dir / "compiled-spec.yaml").read_text()
    lines = content.split("\n")

    # No pattern key should have a description comment in non-verbose mode
    for pid in selected_ids:
        key_line = next((l for l in lines if l.lstrip().startswith(f"{pid}:")), None)
        if key_line is not None:
            assert " #" not in key_line, (
                f"Pattern '{pid}' has an unexpected comment in non-verbose mode.\n"
                f"  Line: {key_line!r}"
            )


if __name__ == "__main__":
    test_requirements_tracing_verbose()
    test_non_verbose_no_comments()
    test_verbose_assumptions_patterns_have_description_comments()
    test_verbose_user_patterns_have_description_comments()
    test_non_verbose_no_description_comments_on_pattern_keys()
    print("\n✅ All integration tests passed!")
