# Compiler Conflict Resolution

## Overview

The compiler enforces `incompatibleWithDesignPatterns` relationships to ensure no conflicting patterns are selected together.

**Algorithm**: Greedy sequential rejection (first-selected pattern wins)

## Examples of Conflicts

- **Architecture**: `arch-monolith` vs `arch-microservices` vs `arch-serverless`
- **Caching**: `cache-aside` vs `write-through-cache` vs `write-back-cache`
- **Tenancy**: `tenancy-database-per-tenant` vs `tenancy-schema-per-tenant`
- **Dev Workflow**: `dev-gitflow` vs `dev-trunk-based-development`
- **Logging**: `logging-structured` vs `logging-unstructured`

## How It Works

1. Patterns are selected based on `supports_constraints` and `supports_nfr` rules (Phases 3.1–3.2)
2. Selected patterns are scored by how many spec rules they match
3. If two patterns conflict, the one with the higher match score wins; the lower-scoring one is rejected
4. Rejection reason includes which pattern(s) caused the conflict

## Output

Rejected patterns appear in `rejected-patterns.yaml` with:

```json
{
  "id": "arch-microservices",
  "reason": "Incompatible with already-selected pattern(s): arch-monolith",
  "tier": "open",
  "conflictsWith": ["arch-monolith"]
}
```

## Selection Order

**Important**: Selection order matters. Patterns earlier in the selection list take priority over later ones.

If both `arch-monolith` and `arch-microservices` pass compatibility checks:
- If `arch-monolith` is processed first → `arch-monolith` is selected, `arch-microservices` is rejected
- If `arch-microservices` is processed first → `arch-microservices` is selected, `arch-monolith` is rejected

## Pattern Registry

As of 2026-03-21:
- **170 total patterns** in registry
- All patterns validated against `schemas/pattern-schema.yaml`

## Implementation

**Function**: `_resolve_conflicts_with_match_scoring()` in `tools/archcompiler.py`

**Integration**: Called in `main()` as Phase 3.3, after Phase 3.1 (supports_constraints) and Phase 3.2 (supports_nfr)

**Test Suite**: `tests/test_phase3_3_conflicts.py`, `tests/test_pattern_conflicts.py`

## Usage

```bash
# Compile a spec
python3 tools/archcompiler.py test-specs/input_minimal_required-fields-only_pass.yaml -o /tmp/output

# Check rejected patterns for conflicts
cat /tmp/output/rejected-patterns.yaml | python3 -c "import sys,yaml; [print(p['id'], p.get('conflictsWith')) for p in yaml.safe_load(sys.stdin) if p.get('conflictsWith')]"
```

## Verification

To verify no conflicting patterns are in the selected set:

```python
import yaml, json, pathlib

selected = yaml.safe_load(open('compiled_output/selected-patterns.yaml'))
patterns = {
    p.stem: json.loads(p.read_text())
    for p in pathlib.Path('patterns').glob('*.json')
}

selected_ids = set(s['id'] for s in selected)
for s in selected:
    pid = s['id']
    conflicts = patterns[pid].get('conflicts', {}).get('incompatibleWithDesignPatterns', [])
    conflicting = [c for c in conflicts if c in selected_ids]
    if conflicting:
        print(f"ERROR: {pid} conflicts with {conflicting}")
```

## Related Documentation

- Pattern schema: `schemas/pattern-schema.yaml`
- Pattern audit tool: `tools/audit_patterns.py`
- Asymmetric conflict report: `reports/asymmetric-conflicts-audit.json`
