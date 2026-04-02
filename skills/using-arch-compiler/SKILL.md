---
name: using-arch-compiler
description: Use when starting architecture work and you need to decide whether to compile/finalise architecture or implement an already-approved architecture.
---

# Using Architecture Compiler

## Read This First

Before doing anything else:

1. Read `AGENTS.md`.
2. Treat `tools/`, `schemas/`, and `patterns/` as read-only unless the human explicitly asked for compiler-maintenance work in this repo.
3. Decide whether the task is about architecture selection or architecture implementation.

## Routing Rule

Use `skills/compiling-architecture/SKILL.md` when:
- the user wants to turn requirements into architecture decisions
- the user wants to write or refine a spec
- the user wants to compile, recompile, inspect pattern selection, or finalise an architecture
- `docs/architecture/` does not exist yet
- `docs/architecture/architecture.yaml` is missing approval
- implementation planning or coding exposes unresolved provider/runtime/auth/retention/message-path decisions
- any later decision would change `constraints.*`, `constraints.saas-providers`, top-level `patterns.*`, or accepted risk posture

Use `skills/implementing-architecture/SKILL.md` when:
- `docs/architecture/architecture.yaml` exists
- it is approved
- the task is to write code that follows that architecture
- provider/runtime bindings are already concrete enough that coding will not silently replace the approved contract

## Hard Stops

- If no application repo exists yet, do not write app architecture artifacts into the compiler repo.
- If an implementation task lacks approved architecture, stop and switch to the compiling skill.
- If planning starts under the implementing skill and reveals unresolved architecture-binding choices, stop and route back to the compiling skill before more planning or coding.
- If a previously approved architecture is recompiled or materially changed, treat the old approval as invalid until the human re-approves the new output.
- If the user is asking to change compiler behavior or the pattern registry itself, this is compiler-maintenance work, not normal skill usage.

## Output

After choosing, explicitly say which of the two skills you are using and why.
