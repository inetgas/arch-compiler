# Tools Reference

Five Python tools live in `tools/`. One runs the compiler, one runs shared workflow preflight checks, and the rest are validation and auditing utilities used during development and by the test suite.

---

## archcompiler.py (3,786 lines)

The main compiler. Reads a canonical YAML spec, selects matching patterns from the registry, resolves conflicts, runs cost feasibility, and emits decision artifacts.

Run all commands in this document from the `arch-compiler/` repo root unless noted otherwise.

### Usage

```bash
python3 tools/archcompiler.py <spec_file> [options]

# Write artifacts to a directory
python3 tools/archcompiler.py spec.yaml -o compiled_output/

# Verbose output with detailed cost breakdown
python3 tools/archcompiler.py spec.yaml -o compiled_output/ -v

# Include coding-level patterns (GoF, DI, test strategies)
python3 tools/archcompiler.py spec.yaml --include-coding-patterns

# Add UTC timestamp to output filenames
python3 tools/archcompiler.py spec.yaml -o compiled_output/ -t
```

| Argument | Description |
|----------|-------------|
| `spec_file` | Path to YAML specification file (positional) |
| `-o / --output DIR` | Write artifacts to this directory (default: stdout only) |
| `-v / --verbose` | Verbose output with detailed cost breakdown and per-pattern ADRs |
| `-t / --timestamp` | Prefix output filenames with UTC timestamp (requires `-o`) |
| `--include-coding-patterns` | Include coding-level patterns (GoF, DI, test strategies, etc.) |

**Exit codes:** `0` = success, `1` = validation errors or requirement violations.

---

## archcompiler_preflight.py

Shared preflight checks for architecture compilation and implementation workflows. This tool verifies that:

- the Architecture Compiler repo is available in a stable local path and contains required runtime folders
- the target application repo exists
- git is initialized in the application repo
- the application repo has an initial commit
- in `implement` mode, `docs/architecture/architecture.yaml` exists and contains `STATUS: APPROVED`

### Usage

```bash
python3 tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
python3 tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode implement
```

Or, if the package is installed:

```bash
archcompiler-preflight --app-repo /path/to/app-repo --mode compile
```

| Argument | Description |
|----------|-------------|
| `--app-repo PATH` | Path to the application repository |
| `--mode {compile,implement}` | Which workflow is about to run |
| `--compiler-root PATH` | Optional stable local path to the Architecture Compiler repo; defaults to the repo containing the script |

**Exit codes:** `0` = preflight passed, `1` = one or more required checks failed.

### Input files

| Path | Purpose |
|------|---------|
| `<spec_file>` | User-provided YAML specification |
| `schemas/canonical-schema.yaml` | JSON Schema for spec validation |
| `schemas/pattern-schema.yaml` | JSON Schema for pattern files |
| `patterns/*.json` | All pattern manifests |
| `config/defaults.yaml` | Default values for constraints, NFR, operating_model, cost |

### Output files (when `-o` is specified)

| File | Description |
|------|-------------|
| `compiled-spec.yaml` | Main output — merged spec with assumptions and inline pattern comments |
| `selected-patterns.yaml` | Patterns that passed all phases with match scores |
| `rejected-patterns.yaml` | *(verbose only)* Patterns filtered out, with reason and phase |

### Pipeline phases

#### Phase 1 — Parse & Validate
Load the spec, strip all explicit `null` values (treating them identically to omitted fields), validate against JSON Schema, and check semantic consistency (e.g. `tenant_count > 1` but `multi_tenancy: false`, or a provider in both `saas-providers` and `disallowed-saas-providers`). Any pattern IDs listed in `disallowed-patterns` that do not exist in the registry cause a hard error here (exit 1).

Key functions: `_load_spec()`, `_strip_null_values()`, `_validate_spec_schema()`, `_validate_semantic_consistency()`, `_validate_user_pattern_configs()`

#### Phase 2 — Merge with Defaults
Apply `config/defaults.yaml` to any unspecified fields in `constraints`, `nfr`, `operating_model`, and `cost`. Applied defaults are recorded in `spec.assumptions` so they are visible and can be overridden on recompilation. Fields with null defaults are not written to the output.

Key function: `_merge_with_defaults()`

#### Phase 2.5 — Disallowed Patterns Filter
Remove any pattern explicitly listed in `spec.disallowed-patterns` before any rules-based evaluation. This gives humans a direct override regardless of how well a pattern matches the spec. Rejected patterns are tagged `phase_2_5_disallowed_patterns` in `rejected-patterns.yaml`.

Key function: `_filter_by_disallowed_patterns()`

#### Phase 3 — Filter Patterns

The `supports_*` fields are **selection gates** — a pattern must pass all its rules to be included. The `requires_*` fields are **post-selection validators** — if a selected pattern's requirement is violated, compilation errors.

**3.1 — Constraint filtering** (`_filter_by_supports_constraints`)\
Each pattern's `supports_constraints` rules are evaluated (AND logic) against the spec. A pattern is rejected if any rule fails. Additionally, any pattern whose required SaaS provider appears in `constraints.disallowed-saas-providers` is rejected here.

**3.2 — NFR filtering** (`_filter_by_supports_nfr`)\
Same AND-logic evaluation using each pattern's `supports_nfr` rules. A pattern with an empty `supports_nfr` array is rejected when the spec has any NFR requirements (it has declared no NFR compatibility).

**3.3 — Conflict resolution** (`_resolve_conflicts_with_match_scoring`)\
Builds a bidirectional conflict graph from `conflicts.incompatibleWithDesignPatterns`. Applies a greedy maximum independent set (MIS) algorithm, breaking ties by: match score (desc) → monthly cost (asc) → pattern ID (asc).

**3.3.5 — Required spec rules validation** (`_validate_required_spec_rules`)\
After selection, validates every selected pattern's `requires_nfr` and `requires_constraints` rules against the spec. Unlike `supports_*` rules (which silently exclude), a violation here causes a hard error (exit 1) with an annotated spec showing exactly which fields are incompatible.

**3.4 — Default config merge** (`_merge_pattern_default_configs`)\
Merges each selected pattern's `defaultConfig` into `spec.assumptions.patterns` for any pattern the user has not explicitly configured.

**3.5 — Coding pattern filter** (`_filter_coding_patterns_post_selection`)\
Removes coding-level patterns (GoF, DI, test strategies) unless `--include-coding-patterns` is set.

#### Phase 4 — Cost Feasibility
Calculates total cost across all selected patterns using the spec's cost intent (`minimize-opex`, `minimize-capex`, `optimize-tco`). Ops team cost is calculated separately using `operating_model` fields (team size, on-call, deploy frequency). Ceiling violations produce advisory warnings — they never reject patterns.

Key functions: `_calculate_ops_team_cost()`, `_check_cost_feasibility()`, `_evaluate_warn_nfr_rules()`, `_evaluate_warn_constraints_rules()`

#### Phase 5 — Output Generation
Emits `compiled-spec.yaml` to stdout (and file if `-o`). Null values are stripped from the output so `compiled-spec.yaml` can be fed back as input and produce identical results (idempotent recompilation). In verbose mode, adds inline `# [pattern-id]` comments next to fields that triggered pattern selection. Writes all other artifact files.

Key functions: `_strip_null_values()`, `_clean_spec_for_output()`, `_build_metadata_comments_index()`, `_render_annotated_yaml()`

### Key functions

| Function | Purpose |
|----------|---------|
| `_load_spec(path)` | Parse and return the YAML spec |
| `_validate_spec_schema(spec)` | Validate against canonical-schema.yaml; exit on errors |
| `_validate_semantic_consistency(spec)` | Check logical contradictions in the spec |
| `_merge_with_defaults(spec, defaults)` | Apply defaults; record in `spec.assumptions` |
| `_evaluate_rule(spec, rule)` | Evaluate a single `supports_*` rule against the spec |
| `_filter_by_supports_constraints(patterns, spec)` | Phase 3.1 — constraint filtering |
| `_filter_by_supports_nfr(ids, patterns, spec, honored)` | Phase 3.2 — NFR filtering |
| `_resolve_conflicts_with_match_scoring(ids, patterns, spec)` | Phase 3.3 — conflict resolution |
| `_calculate_pattern_match_score(pattern, spec)` | Count how many rules a pattern's spec values satisfy |
| `_calculate_pattern_cost_by_intent(pattern, intent, months)` | Calculate cost under a given intent |
| `_check_cost_feasibility(ids, patterns, spec, ops_cost, scores)` | Phase 4 — cost ceiling checks |
| `_validate_required_spec_rules(ids, patterns, spec)` | Hard-fail if `requires_*` rules are violated |
| `_json_pointer_get(doc, path)` | Resolve a JSON Pointer path against a document |
| `_json_pointer_set(doc, path, value)` | Set a value at a JSON Pointer path |
| `_build_error_annotation_map(...)` | Build per-field annotation map for error output |
| `_render_annotated_yaml(doc, annotations, indent)` | Render YAML with inline comments |

### Rule format

All `supports_constraints`, `supports_nfr`, `requires_constraints`, `requires_nfr`, `warn_nfr`, and `warn_constraints` entries follow this structure:

```json
{
  "path": "/constraints/cloud",
  "op": "in",
  "value": ["aws", "gcp", "azure"],
  "reason": "Pattern requires a major cloud provider."
}
```

**Supported operators:** `==`, `!=`, `in`, `not-in`, `contains-any`, `>`, `<`, `>=`, `<=`

### Cost intent behaviour

| Intent | What's compared to ceiling |
|--------|---------------------------|
| `minimize-opex` | Total monthly opex (patterns + ops team) vs `cost.ceilings.monthly_usd` |
| `minimize-capex` | Total adoption cost vs `cost.ceilings.initial_usd` |
| `optimize-tco` | TCO (capex + opex × amortization months) vs both ceilings combined |

### Ops team cost formula

```
ops_cost = team_size × monthly_rate × on_call_multiplier × deploy_freq_multiplier
```

- `on_call_multiplier`: 1.5 if on-call, 1.0 otherwise (Google SRE Handbook)
- `deploy_freq_multiplier`: 0.5 (on-demand) → 1.1 (quarterly) (DORA research)

---

## audit_patterns.py (169 lines)

Quality audit for pattern metadata. Checks required fields, type validity, and conflict consistency. Used directly by the test suite (`test_pattern_schema_validation.py`).

### Usage

```bash
python3 tools/audit_patterns.py
```

No arguments. Prints a summary of issues grouped by category and the top offending patterns to stdout. Always exits `0`.

### What it checks

| Check | Category |
|-------|----------|
| All required fields present | `missing_required_field` |
| `types` values are valid (`cost`, `design`, `build`, `test`, `ops`, `deploy`, `security`, `data`, `platform`, `coding`) | `invalid_type` |
| All patterns in `conflicts.incompatibleWithDesignPatterns` exist | `invalid_conflict_reference` |
| Conflict relationships are symmetric | `asymmetric_conflict` |

**Required fields:** `id`, `version`, `title`, `description`, `types`, `cost`, `provides`, `requires`, `tags`, `supports_nfr`, `supports_constraints`

### Key functions

| Function | Purpose |
|----------|---------|
| `audit_pattern_metadata(pattern, pattern_id)` | Check required fields and type validity |
| `audit_incompatible_patterns(pattern, all_ids)` | Check conflict references and symmetry |
| `main()` | Load all patterns, run audits, print report |

---

## audit_nfr_logic.py (239 lines)

Validates that NFR and constraint rules in every pattern reference valid paths from `canonical-schema.yaml`. Used by `test_nfr_constraint_logic.py`.

### Usage

```bash
python3 tools/audit_nfr_logic.py
```

No arguments. Writes results to both stdout and `reports/nfr-constraint-logic-audit.json`. Always exits `0`.

### What it checks

| Check | Description |
|-------|-------------|
| Valid NFR paths | All `path` values in `supports_nfr`, `requires_nfr`, `warn_nfr` must exist in `canonical-schema.yaml` |
| Valid constraint paths | All `path` values in `supports_constraints`, `requires_constraints`, `warn_constraints` must exist in `canonical-schema.yaml` |
| Valid operators | Only `==`, `!=`, `in`, `not-in`, `contains-any`, `>`, `<`, `>=`, `<=` are allowed |
| No duplicate rules | Same path should not appear with conflicting operators in the same array |

### Output

Writes `reports/nfr-constraint-logic-audit.json`:

```json
{
  "invalid_path": [...],
  "invalid_operator": [...],
  "duplicate_rules": [...]
}
```

### Key functions

| Function | Purpose |
|----------|---------|
| `load_canonical_schema()` | Extract all valid JSON Pointer paths from `canonical-schema.yaml` |
| `analyze_nfr_rules(pattern, valid_paths)` | Check `supports_nfr` / `requires_nfr` / `warn_nfr` rule paths |
| `analyze_constraint_rules(pattern, valid_paths)` | Check `supports_constraints` / `requires_constraints` / `warn_constraints` rule paths |
| `audit_all_patterns()` | Run audits across all patterns; return issue dict |

---

## audit_asymmetric_conflicts.py (243 lines)

Detects asymmetric conflict declarations — where pattern A lists B as incompatible but B does not list A. Used by `test_pattern_conflicts.py`.

### Usage

```bash
python3 tools/audit_asymmetric_conflicts.py
```

No arguments. Writes to stdout and two files in `reports/`. **Exit codes:** `0` = no asymmetric conflicts, `1` = asymmetric conflicts found.

### Output files

| File | Contents |
|------|----------|
| `reports/asymmetric-conflicts-audit.json` | Full audit with `summary.total_asymmetric_conflicts` and categorised issues |
| `reports/asymmetric-conflicts-fixes.json` | Suggested additions per pattern: `{ "pattern-id": ["conflict-to-add", ...] }` |

### Categories of asymmetry

| Category | Description |
|----------|-------------|
| `generic_missing_variant_conflicts` | Generic pattern missing conflict declaration with its own variant |
| `variant_missing_generic_conflict` | Variant missing conflict declaration back to generic |
| `variant_missing_sibling_conflict` | Sibling variants not mutually conflicting |
| `architecture_pattern_missing_conflict` | `arch-*` patterns missing expected mutual conflicts |
| `other_asymmetric` | All other A→B without B→A cases |

### Key functions

| Function | Purpose |
|----------|---------|
| `load_all_patterns(patterns_dir)` | Load all JSON patterns into a dict keyed by ID |
| `get_conflicts(pattern)` | Return the set of IDs in `conflicts.incompatibleWithDesignPatterns` |
| `build_conflict_graph(patterns)` | Build directed graph: `{ id → set(conflicted_ids) }` |
| `find_asymmetric_conflicts(graph)` | Return all A→B pairs where B⇏A |
| `categorize_asymmetric_conflicts(asymmetric, patterns)` | Classify each asymmetry by category |
| `generate_fixes(categories)` | Produce the suggested-additions dict |
| `main()` | Orchestrate full pipeline; return exit code |

---

## Quick Reference

| Tool | Run when... |
|------|-------------|
| `archcompiler.py` | Compiling a spec into selected patterns and decisions |
| `archcompiler_preflight.py` | Checking app-repo git initialization and approved-architecture readiness before compile/implement workflows |
| `audit_patterns.py` | Checking pattern metadata quality (also run by test suite) |
| `audit_nfr_logic.py` | Verifying NFR/constraint rule paths are valid (also run by test suite) |
| `audit_asymmetric_conflicts.py` | Checking conflict symmetry after adding/editing patterns (also run by test suite) |
