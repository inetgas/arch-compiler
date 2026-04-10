# Architecture Compiler Skill Discovery

Architecture Compiler publishes three agent skills for deterministic architecture workflows.

## What These Skills Help With

These skills are useful if you are looking for:

- architecture planning for AI agents
- architecture selection from requirements and constraints
- deterministic architecture compilation
- non-functional requirements enforcement
- cost-aware architecture decisions
- implementation from approved architecture
- architecture governance and re-approval
- architecture-as-code workflows
- design-pattern-based architecture selection

## Skill Pack

- `using-arch-compiler`
  - Use when starting architecture work and you need to route between architecture compilation and implementation.

- `compiling-architecture`
  - Use when selecting architecture patterns, compiling a spec, iterating on constraints/NFRs, auditing why patterns were selected or rejected, or finalising architecture for implementation.

- `implementing-architecture`
  - Use when an approved `docs/architecture/architecture.yaml` already exists and implementation must stay inside that contract.

## Supported Agent Workflows

- Codex
- Claude Code
- Hermes
- other `SKILL.md`-compatible agent frameworks

## Install Paths

### Codex

```bash
npx skills add inetgas/arch-compiler --list
```

### Hermes

Hermes can discover these skills from `skills.sh`, GitHub installs, or shared external skill directories such as `~/.agents/skills`.

## Related Concepts

- architecture harness
- harness engineering
- deterministic execution
- architecture constraints enforcement
- architecture trade-off considerations
- architectural decision records
- software architecture patterns
- design pattern registry
- AI governance
