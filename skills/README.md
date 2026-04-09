# Skills

Languages: English | [简体中文](../docs/i18n/skills.README.zh-CN.md)

Note: The English documentation is the canonical source of truth. If translations differ, follow the English version.

Official Architecture Compiler skill pack for deterministic architecture selection, approval/re-approval workflow, and implementation against an approved architecture contract.

This repo publishes three reusable agent skills:

- `skills/using-arch-compiler`
- `skills/compiling-architecture`
- `skills/implementing-architecture`

Each skill is packaged as a self-contained folder with a top-level `SKILL.md`.

Important: installing the skill files alone does not install the Architecture Compiler runtime. The skills depend on the full repo — compiler, patterns, schemas, and docs — being available in a stable local path such as `~/.codex/arch-compiler` or `~/.claude/arch-compiler`.

## Install in Codex

Recommended: install the whole skill pack via native Codex skill discovery.

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

Restart Codex after installing new skills.

The stable repo path above is also the canonical runtime location the skills should use when invoking the compiler. Avoid cloning the repo into `/tmp/` for normal use; that creates session-to-session drift and forces unnecessary re-installs.

Advanced option: install all three skills directly from this GitHub repo by path:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo inetgas/arch-compiler \
  --path skills/using-arch-compiler skills/compiling-architecture skills/implementing-architecture
```

Codex installer note: when installing multiple skills from this repo, pass all skill paths after a single `--path` argument. Do not repeat `--path`; in the current installer only the last repeated value is kept.

After installation, verify the three directories exist:

```bash
ls ~/.codex/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

Or use the GitHub URL form to install them one-by-one:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/using-arch-compiler
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/compiling-architecture
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/implementing-architecture
```

## Use in Claude Code

Claude Code does not install Codex skills natively, but the same behavior can be exposed as project slash commands.

For Claude Code, keep the full Architecture Compiler repo in a stable path such as `~/.claude/arch-compiler` so the commands and skills can find the compiler, patterns, and schemas without re-cloning.

This repo includes ready-to-copy command files:

- `adapters/claude-code/commands/using-arch-compiler.md`
- `adapters/claude-code/commands/compile-architecture.md`
- `adapters/claude-code/commands/implement-architecture.md`

Copy them into your target repo at `.claude/commands/`:

```bash
mkdir -p .claude/commands
cp adapters/claude-code/commands/compile-architecture.md .claude/commands/
cp adapters/claude-code/commands/implement-architecture.md .claude/commands/
cp adapters/claude-code/commands/using-arch-compiler.md .claude/commands/
```

These create Claude Code commands:

- `/using-arch-compiler`
- `/compile-architecture`
- `/implement-architecture`

They point Claude at the canonical skill files in this repo:

- `~/.claude/arch-compiler/skills/using-arch-compiler/SKILL.md`
- `~/.claude/arch-compiler/skills/compiling-architecture/SKILL.md`
- `~/.claude/arch-compiler/skills/implementing-architecture/SKILL.md`

If your local install path differs, edit the copied command files to reference that stable path before first use.

If you want Claude Code to always load repo guidance, you can also add project memory in `CLAUDE.md` and reference the same stable-path skill files from there.

## Portability Notes

- Codex: installable directly by GitHub path because the skill unit is a folder containing `SKILL.md`
- Claude Code: best mapped to custom slash commands in `.claude/commands/` or project memory in `CLAUDE.md`
- Other agent frameworks: use `skills/<name>/SKILL.md` as the source of truth and wrap it in that tool's native prompt or command format
