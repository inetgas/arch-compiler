# Agent Guide — Architecture Compiler

Read this before using any skill in this repo.

## Repo Contract

```text
arch-compiler/
├── README.md
├── AGENTS.md
├── README-AGENTS.md
├── tools/        <-- read-only for agents
├── schemas/      <-- read-only for agents
├── config/       <-- read-only for agents
├── patterns/     <-- read-only for agents
└── skills/
    ├── using-arch-compiler/
    │   └── SKILL.md
    ├── compiling-architecture/
    │   └── SKILL.md
    └── implementing-architecture/
        └── SKILL.md
```

The important split is:
- `AGENTS.md` = canonical global agent rules
- `skills/using-arch-compiler/SKILL.md` = entrypoint/router skill
- `skills/compiling-architecture/SKILL.md` = compile and finalise architecture
- `skills/implementing-architecture/SKILL.md` = implement an already-approved architecture

## What This Repo Does

Given a YAML spec, the compiler selects applicable architecture patterns and produces deterministic architecture decision artifacts. Same input produces the same output every time. No LLM inference happens inside the compiler.

## Which Skill To Use

| Situation | Skill |
|-----------|-------|
| User wants help choosing the correct architecture workflow | `skills/using-arch-compiler/SKILL.md` |
| User wants to compile a spec, select patterns, or finalise an architecture | `skills/compiling-architecture/SKILL.md` |
| User wants to implement a system from an approved `docs/architecture/` folder | `skills/implementing-architecture/SKILL.md` |

If you are unsure, start with `skills/using-arch-compiler/SKILL.md`.

## Read-Only Boundaries

Agents may read any file in this repo.

Unless the human explicitly asks for compiler-maintenance work in this repo:
- treat `tools/` as read-only
- treat `schemas/` as read-only
- treat `config/` as read-only
- treat `patterns/` as read-only

Agents may:
- run the compiler
- run audit tools
- run tests

Agents may not, unless explicitly directed by the human:
- edit an existing pattern in `patterns/`
- edit `schemas/canonical-schema.yaml`
- edit `schemas/pattern-schema.yaml`
- edit `config/defaults.yaml`
- place a newly authored pattern directly into `patterns/` just because the human asked to "author" it

For new pattern work, the default rule is:
- agents may draft a new pattern in a staging location
- agents may prepare companion vocabulary/conflict updates needed for that draft
- agents may not make the new pattern live in `patterns/` unless the human explicitly approves activation

## Working Model

- The compiler repo is the tool and pattern registry.
- The application repo is where specs and architecture outputs belong.
- Do not create or finalise an app's `docs/architecture/` inside this compiler repo.
- For implementation work, `docs/architecture/` is read-only compiler output, not a place to improvise architecture changes.
- If planning or coding exposes provider-binding decisions that would materially change the approved contract, route back to `skills/compiling-architecture/SKILL.md` and re-approve the architecture before continuing.

## Key Files

- `tools/archcompiler.py` = compiler entrypoint
- `tools/archcompiler_preflight.py` = shared workflow preflight for compile/implement checks
- `config/defaults.yaml` = default spec values
- `schemas/canonical-schema.yaml` = spec contract
- `schemas/pattern-schema.yaml` = pattern contract
- `schemas/capability-vocabulary.yaml` = capability vocabulary

## Pattern Maintenance Reminder

When authoring or editing patterns:
- validate against `schemas/pattern-schema.yaml`
- also check `schemas/capability-vocabulary.yaml` for any new or changed `provides` / `requires` capability names
- if you add canonical capability names or aliases, rerun `tools/audit_patterns.py` and fix any older alias usage the vocabulary update exposes elsewhere in the registry
- for new patterns, follow the staging-first workflow in `skills/compiling-architecture/SKILL.md`; "author a new pattern" does not by itself mean "place it in patterns/"

## Running the Compiler

```bash
cd arch-compiler
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tools/requirements.txt
python -m pip install -e .

archcompiler tests/fixtures/no-advisory-success.yaml
```

Exit code `0` means success. Exit code `1` means validation failure or unsatisfied hard constraints.

Run tests and compiler commands from the `arch-compiler/` repo root. Some tests invoke `tools/archcompiler.py` via cwd-relative paths.
