# Agent Guide — Architecture Compiler

`AGENTS.md` is the canonical root agent file for tooling that looks for standard agent-memory filenames. This file is the human-readable companion guide with the same repo-specific intent.

This repo contains a deterministic architecture compiler and a registry of curated design patterns. Read this before acting.

---

## What This Repo Does

Given a YAML spec (constraints, targets for nfr/operating_model/cost), the compiler selects applicable architecture patterns and produces deterministic/reproducible architecture decision artifacts. Same input → same output, every time. No LLM inference in the compiler itself.

---

## Three Skills — Use the Right One

| Situation | Skill to use |
|-----------|-------------|
| User wants help choosing the correct architecture workflow, or planning uncovered new architecture choices | `skills/using-arch-compiler/SKILL.md` |
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

If planning or implementation exposes provider-binding decisions that would change `constraints.*`, `constraints.saas-providers`, top-level `patterns.*`, or accepted risk posture, stop and return to the compiling workflow. That is architecture work, not routine implementation detail.

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
| `tools/archcompiler_preflight.py` | Shared workflow preflight for app-repo, git, and approval checks before compile/implement flows |
| `tools/audit_patterns.py` | Pattern metadata quality audit (run after editing patterns) |
| `tools/audit_nfr_logic.py` | Validates all rule `path` values reference valid spec fields |
| `tools/audit_asymmetric_conflicts.py` | Finds A→B conflicts missing B→A declarations |
| `tools/requirements.txt` | Python dependencies |
| `docs/tools.md` | Full reference documentation for all tools above |

### Pattern registry

| Path | What it is |
|------|-----------|
| `patterns/` | Curated pattern JSON files — the knowledge base |
| `patterns/<id>.json` | Pattern ID must match filename exactly (e.g. `cache-aside.json` → `id: "cache-aside"`) |

Pattern file naming convention: `<family>-<name>[--<provider-or-variant>].json`
- `arch-serverless.json` — generic base
- `arch-serverless--aws.json` — provider-specific variant (must conflict with all sibling variants)

### Tests

| Path | What it is |
|------|-----------|
| `tests/` | pytest test suite |
| `tests/README.md` | Test suite overview and how to run |
| `tests/fixtures/` | Reusable YAML fixtures for warn_nfr / cost tests |
| `test-specs/` | Named integration specs |

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
| Author a new pattern in a human-designated staging location outside `patterns/` | ✅ Yes — staging only, never directly to `patterns/` |
| Edit an existing pattern in `patterns/` | ❌ No — human-only |
| Edit `schemas/canonical-schema.yaml` or `schemas/pattern-schema.yaml` | ❌ No — human-only |
| Edit `config/defaults.yaml` | ❌ No — human-only |
| Move a staged pattern into `patterns/` | ❌ No — human review required first |

---

## Running the Compiler

```bash
# Run from the arch-compiler repo root
cd arch-compiler

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install repo dependencies
python -m pip install -r tools/requirements.txt
python -m pip install -e .

# Run workflow preflight before app-facing compile or implement work
archcompiler-preflight --app-repo /path/to/app-repo --mode compile

# Compile to stdout
archcompiler tests/fixtures/no-advisory-success.yaml

# Compile and write artifacts
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v

# Or run directly from the source tree
python tools/archcompiler.py tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v
```

Run tests and compiler commands from the `arch-compiler/` repo root. Several tests call `tools/archcompiler.py` using cwd-relative paths.

Exit code `0` = success. Exit code `1` = validation error — read the `💡 Suggestions` block in stdout.
