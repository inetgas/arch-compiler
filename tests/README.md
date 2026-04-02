# Pattern Registry Regression Tests

Comprehensive regression test suite for the pattern registry. These tests validate pattern data quality, schema compliance, and relationship correctness.

## Quick Start

```bash
# Install dependencies (if not already installed)
pip install pytest pyyaml

# Run all tests
python3 tests/run_all_tests.py

# Or run specific test suites
python3 -m pytest tests/test_pattern_schema_validation.py -v
python3 -m pytest tests/test_nfr_constraint_logic.py -v
python3 -m pytest tests/test_pattern_conflicts.py -v
python3 -m pytest tests/test_pattern_quality.py -v
```

## Test Suites

### 1. Schema Validation Tests (`test_pattern_schema_validation.py`)

Validates all patterns conform to `pattern-schema.yaml`.

**Tests:**
- ✅ All patterns valid against schema
- ✅ All pattern files loadable as valid JSON
- ✅ All required top-level fields present
- ✅ All patterns have `supports_nfr` and `supports_constraints` (Part 2A requirement)
- ✅ No legacy `excludedIf` fields remain

**Audit Tool:** `tools/audit_patterns.py`

**Example Failure:**
```
FAILED: Found 3 patterns with schema issues:
  - pattern-foo: Missing required field 'supports_constraints'
  - pattern-bar: Invalid JSON syntax
Run 'python3 tools/audit_patterns.py' for details.
```

### 2. NFR & Constraint Logic Tests (`test_nfr_constraint_logic.py`)

Validates NFR and constraint rule correctness (directional bounds, valid operators, valid paths).

**Tests:**
- ✅ No NFR logic errors (latency/throughput/RTO/RPO bounds correct)
- ✅ No constraint logic errors (platform entries, operators, mobile platform)
- ✅ Mixed operators only for count/range fields
- ✅ All NFR paths exist in `canonical-schema.yaml`
- ✅ All constraint paths exist in `canonical-schema.yaml`
- ✅ All operators valid (==, !=, in, >, >=, <, <=, =)

**Audit Tool:** `tools/audit_nfr_logic.py`

**Example Failure:**
```
FAILED: Found 5 NFR logic errors:
  - Latency both bounds: 2 (should only have >= min)
  - Throughput both bounds: 1 (should only have <= max)
  - Invalid paths: 2
Run 'python3 tools/audit_nfr_logic.py' for details.
```

### 3. Pattern Conflict Tests (`test_pattern_conflicts.py`)

Validates conflict relationship symmetry and correctness.

**Tests:**
- ✅ No asymmetric conflict relationships (all bidirectional)
- ✅ All conflict references point to existing patterns
- ✅ Generic patterns conflict with all their variants
- ✅ Variant patterns conflict with their generic
- ✅ Sibling variants conflict with each other
- ✅ Architecture patterns mutually exclusive

**Audit Tool:** `tools/audit_asymmetric_conflicts.py`

**Example Failure:**
```
FAILED: Found 3 asymmetric conflict relationships.
  - db-graph--generic missing conflict with db-graph--neo4j-aura
  - compliance-gdpr-basic ↔ cost-free-saas-tier not bidirectional
Run 'python3 tools/audit_asymmetric_conflicts.py' for details.
```

### 4. Pattern Quality Tests (`test_pattern_quality.py`)

Validates pattern data quality (costs, capabilities, naming conventions).

**Tests:**
- ✅ All patterns have cost provenance
- ✅ No legacy `runtimeCostImpact` fields
- ✅ Adoption costs in reasonable range ($0-$10K)
- ✅ Monthly cost ranges valid (min <= max, reasonable values)
- ✅ Capabilities use lowercase-with-hyphens convention
- ✅ No duplicate conflicts
- ✅ Conflicts sorted alphabetically
- ✅ Pattern types valid
- ✅ Cloud compatibility valid
- ✅ Version follows semantic versioning

**Example Failure:**
```
FAILED: Found 2 patterns with cost provenance issues:
  - pattern-foo: Missing provenance.adoptionCost
  - pattern-bar: adoptionCost $50000 outside range $0-$10K
```

## Integration with Development Workflow

### Pre-Commit Testing

Run tests before committing pattern changes:

```bash
# Before committing
python3 tests/run_all_tests.py

# If tests pass, commit
git add patterns/*.json
git commit -m "feat: update patterns"
```

### CI/CD Integration

Add to GitHub Actions workflow:

```yaml
name: Pattern Registry Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install pytest pyyaml
      - run: python3 tests/run_all_tests.py
```

### Pre-Push Hook

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash
echo "Running regression tests..."
python3 tests/run_all_tests.py
exit $?
```

```bash
chmod +x .git/hooks/pre-push
```

## Adding New Tests

### Pattern Data Tests

Add new test functions to existing suites:

```python
# tests/test_pattern_quality.py

def test_new_quality_check():
    """New quality validation."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        # Your validation logic
        if not pattern.get("new_field"):
            errors.append(f"{pattern['id']}: Missing new_field")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with issues:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )
```

### Compiler Tests (Part 2B)

Create new test suite for compiler:

```bash
# Create compiler test suite
touch tests/test_compiler_selection.py
touch tests/test_compiler_conflict_resolution.py
touch tests/test_compiler_progressive_refinement.py
```

Example compiler test structure:

```python
# tests/test_compiler_selection.py

def test_compiler_selects_compatible_patterns():
    """Compiler selects only patterns matching spec constraints."""
    # Load test spec
    # Run compiler
    # Validate selected patterns

def test_compiler_rejects_conflicting_patterns():
    """Compiler prevents selection of conflicting patterns."""
    # Load spec that could trigger conflicts
    # Run compiler
    # Verify no conflicts in selected set
```

## Test Data Quality Metrics

When all tests pass, we guarantee:

- **100% schema compliance** - All patterns valid against schema
- **0 asymmetric conflicts** - All conflicts bidirectional
- **0 NFR logic errors** - Correct directional bounds
- **0 invalid references** - All referenced patterns exist
- **Consistent naming** - All capabilities use hyphens
- **Complete provenance** - All costs have reasoning

## Troubleshooting

### Tests Fail After Pattern Modification

1. **Run specific audit tool to see details:**
   ```bash
   python3 tools/audit_patterns.py
   python3 tools/audit_nfr_logic.py
   python3 tools/audit_asymmetric_conflicts.py
   ```

2. **Fix issues manually or use fix tools:**
   ```bash
   python3 tools/fix_asymmetric_conflicts.py
   python3 tools/fix_nfr_logic.py
   ```

3. **Re-run tests:**
   ```bash
   python3 tests/run_all_tests.py
   ```

### False Positives

Some patterns may have legitimate exceptions to rules. Update test to skip specific patterns:

```python
def test_with_exceptions():
    # Patterns with legitimate exceptions
    exceptions = {"pattern-foo", "pattern-bar"}

    for pattern in patterns:
        if pattern["id"] in exceptions:
            continue  # Skip validation for exceptions

        # Normal validation
```

### Performance

Tests run in ~5-10 seconds total. If tests become slow:
- Cache loaded patterns across tests
- Parallelize test execution with pytest-xdist
- Run only changed pattern tests

## Future Enhancements

- [ ] Add compiler unit tests (Part 2B)
- [ ] Add integration tests with real specs
- [ ] Add performance regression tests
- [ ] Add schema version compatibility tests
- [ ] Add pattern coverage metrics
- [ ] Generate HTML test reports

## References

- Pattern Schema: `pattern-schema.yaml`
- Canonical Schema: `canonical-schema.yaml`
- Audit Tools: `tools/audit_*.py`
- Fix Tools: `tools/fix_*.py`
