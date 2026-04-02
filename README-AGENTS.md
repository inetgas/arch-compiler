# Agent Guide — Architecture Compiler

This repo contains a deterministic architecture compiler and a registry of curated design patterns. Read this before acting.

---

## What This Repo Does

Given a YAML spec (constraints, targets for nfr/operating_model/cost), the compiler selects applicable architecture patterns and produces deterministic/reproducible architecture decision artifacts. Same input → same output, every time. No LLM inference in the compiler itself.

---

## Two Skills — Use the Right One

| Situation | Skill to use |
|-----------|-------------|
| User wants to compile a spec, select patterns, or finalise an architecture | `skills/compiling-architecture/SKILL.md` |
| User wants to implement a system from an already-approved `docs/architecture/` folder | `skills/implementing-architecture/SKILL.md` |

Read the relevant skill before taking any action. Each skill has a "When NOT to Use" section — check it first.

---

## Typical Workflow

These skills are independent and composable with any requirements-gathering or planning approach:

1. **Gather requirements** — understand the user's constraints (cloud, language, platform), NFR targets (availability, latency, compliance), operating model, and cost budget using whatever method fits your context (conversation, brainstorming, existing docs)
2. **Compile** — once requirements are known, use `skills/compiling-architecture/SKILL.md` to produce a deterministic pattern selection and finalise `docs/architecture/`
3. **Plan implementation** — use any planning approach to break the approved pattern set into tasks
4. **Implement** — use `skills/implementing-architecture/SKILL.md` before writing any code; it consumes `docs/architecture/` as its input contract

Each skill defines its input interface clearly — satisfy the interface however fits your workflow.

---

## Key Files and Directories

### Schemas — read these first when authoring specs or patterns

| Path | What it is |
|------|-----------|
| `schemas/canonical-schema.yaml` | Authoritative contract for every spec field — source of truth for what a spec may contain |
| `schemas/pattern-schema.yaml` | Authoritative contract for every pattern field — source of truth for pattern structure |
| `schemas/capability-vocabulary.yaml` | Canonical names and aliases for `provides`/`requires` capability strings |
| `schemas/README.md` | Human-readable field reference for both schemas |
| `config/defaults.yaml` | Default values the compiler applies when spec fields are omitted |

### Compiler and tools

| Path | What it is |
|------|-----------|
| `tools/archcompiler.py` | The compiler — only file to run for compiling a spec |
| `tools/audit_patterns.py` | Pattern metadata quality audit (run after editing patterns) |
| `tools/audit_nfr_logic.py` | Validates all rule `path` values reference valid spec fields |
| `tools/audit_asymmetric_conflicts.py` | Finds A→B conflicts missing B→A declarations |
| `tools/requirements.txt` | Python dependencies |
| `docs/tools.md` | Full reference documentation for all tools above |

### Pattern registry

| Path | What it is |
|------|-----------|
| `patterns/` | 180 curated pattern JSON files — the knowledge base |
| `patterns/<id>.json` | Pattern ID must match filename exactly (e.g. `cache-aside.json` → `id: "cache-aside"`) |

Pattern file naming convention: `<family>-<name>[--<provider-or-variant>].json`
- `arch-serverless.json` — generic base
- `arch-serverless--aws.json` — provider-specific variant (must conflict with all sibling variants)

### Tests

| Path | What it is |
|------|-----------|
| `tests/` | pytest test suite (34 test files) |
| `tests/README.md` | Test suite overview and how to run |
| `tests/fixtures/` | Reusable YAML fixtures for warn_nfr / cost tests |
| `test-specs/` | 116 named integration specs |

Test spec naming: `<category>_<sub-category>_<description>_<pass\|fail>.yaml`
- `_pass` = must compile with exit 0
- `_fail` = must compile with exit 1

### Documentation and plans

| Path | What it is |
|------|-----------|
| `docs/test-inventory.md` | All tests with descriptions — read before adding tests |
| `docs/arch-platform-pattern-relationship.md` | Which patterns each platform value activates |
| `docs/plans/` | Dated implementation plans |

### Reports (generated output)

| Path | What it is |
|------|-----------|
| `reports/asymmetric-conflicts-audit.json` | Output of `audit_asymmetric_conflicts.py` |
| `reports/asymmetric-conflicts-fixes.json` | Suggested conflict additions from same audit |
| `reports/nfr-constraint-logic-audit.json` | Output of `audit_nfr_logic.py` |

---

## What Agents May and May Not Do

| Action | Allowed? |
|--------|---------|
| Read any file in this repo | ✅ Yes |
| Run the compiler (`tools/archcompiler.py`) | ✅ Yes |
| Run audit tools (`tools/audit_*.py`) | ✅ Yes |
| Run tests (`pytest tests/`) | ✅ Yes |
| Author a new pattern to `patterns-staging/` | ✅ Yes — staging only, never directly to `patterns/` |
| Edit an existing pattern in `patterns/` | ❌ No — human-only |
| Edit `schemas/canonical-schema.yaml` or `schemas/pattern-schema.yaml` | ❌ No — human-only |
| Edit `config/defaults.yaml` | ❌ No — human-only |
| Move a staged pattern into `patterns/` | ❌ No — human review required first |

---

## Running the Compiler

```bash
python3 -m pip install -r tools/requirements.txt

# Compile to stdout
python3 tools/archcompiler.py my-spec.yaml

# Compile and write artifacts
mkdir -p compiled_output/
python3 tools/archcompiler.py my-spec.yaml -o compiled_output/ -v
```

Exit code `0` = success. Exit code `1` = validation error — read the `💡 Suggestions` block in stdout.
