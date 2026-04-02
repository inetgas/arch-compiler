# Skills

This repo publishes two reusable agent skills:

- `skills/compiling-architecture`
- `skills/implementing-architecture`

Each skill is packaged as a self-contained folder with a top-level `SKILL.md`.

## Install in Codex

Install directly from this GitHub repo by path:

```bash
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/compiling-architecture
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/implementing-architecture
```

Or use the GitHub URL form:

```bash
scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/compiling-architecture
scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/implementing-architecture
```

Restart Codex after installing new skills.

## Use in Claude Code

Claude Code does not install Codex skills natively, but the same behavior can be exposed as project slash commands.

This repo includes ready-to-copy command files:

- `adapters/claude-code/commands/compile-architecture.md`
- `adapters/claude-code/commands/implement-architecture.md`

Copy them into your target repo at `.claude/commands/`:

```bash
mkdir -p .claude/commands
cp adapters/claude-code/commands/compile-architecture.md .claude/commands/
cp adapters/claude-code/commands/implement-architecture.md .claude/commands/
```

These create Claude Code commands:

- `/compile-architecture`
- `/implement-architecture`

They point Claude at the canonical skill files in this repo:

- `skills/compiling-architecture/SKILL.md`
- `skills/implementing-architecture/SKILL.md`

If you want Claude Code to always load repo guidance, you can also add project memory in `CLAUDE.md` and reference the same skill files from there.

## Portability Notes

- Codex: installable directly by GitHub path because the skill unit is a folder containing `SKILL.md`
- Claude Code: best mapped to custom slash commands in `.claude/commands/` or project memory in `CLAUDE.md`
- Other agent frameworks: use `skills/<name>/SKILL.md` as the source of truth and wrap it in that tool's native prompt or command format
