# Skills

Languages: English | [简体中文](../docs/i18n/skills.README.zh-CN.md)

Note: The English documentation is the canonical source of truth. If translations differ, follow the English version.

Official Architecture Compiler skill pack for deterministic architecture selection, approval/re-approval workflow, and implementation against an approved architecture contract.

This repo publishes three reusable agent skills:

- `skills/using-arch-compiler`
- `skills/compiling-architecture`
- `skills/implementing-architecture`

Each skill is packaged as a self-contained folder with a top-level `SKILL.md`.

Important: installing the skill files alone does not install the Architecture Compiler runtime. The skills depend on the full repo — compiler, patterns, schemas, and docs — being available in a stable local path such as `~/.codex/arch-compiler`, `~/.claude/arch-compiler`, or `~/.hermes/arch-compiler`.

## Install in Codex

Recommended: use the official Codex bootstrap installer. It installs the three skills and clones or updates the full runtime repo in the canonical Codex path.

```bash
# One-command install from GitHub
bash <(curl -fsSL https://raw.githubusercontent.com/inetgas/arch-compiler/main/scripts/install_codex_skills.sh)
```

If you prefer to inspect the repo first:

```bash
git clone https://github.com/inetgas/arch-compiler.git
cd arch-compiler
./scripts/install_codex_skills.sh
```

Restart Codex after installing new skills.

What the installer does:

- installs `using-arch-compiler`, `compiling-architecture`, and `implementing-architecture` into the shared global agent skills directory at `~/.agents/skills/`
- clones or updates the full runtime repo at `~/.codex/arch-compiler`
- verifies both the installed skills and the runtime repo layout

The stable repo path above is the canonical runtime location the skills should use when invoking the compiler. Avoid cloning the repo into `/tmp/` for normal use; that creates session-to-session drift and forces unnecessary re-installs.

Alternative: manual install with the open `skills.sh` / Vercel skills CLI.

```bash
# List the skills published by this repo
npx skills add inetgas/arch-compiler --list

# Install all three into the shared global agent skills directory (~/.agents/skills/)
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -g -y

# Clone the full runtime repo used by the installed skills
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler

# Verify the three skills were installed globally
ls ~/.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

If you omit `-g`, the skills install into the current project at `./.agents/skills/` instead of your global Codex directory.

```bash
# Project-local install (shared with the current repo)
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -y

# Verify the project-local install
ls ./.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

Important: the `skills` CLI installs only the skill folders. The workflows still require the full Architecture Compiler repo in a stable local path such as `~/.codex/arch-compiler` for runtime access to the compiler, pattern registry, schemas, config, and adapters.

To uninstall the global `skills.sh` layout:

```bash
rm -rf ~/.agents/skills/using-arch-compiler
rm -rf ~/.agents/skills/compiling-architecture
rm -rf ~/.agents/skills/implementing-architecture
```

To uninstall the project-local `skills.sh` layout:

```bash
rm -rf ./.agents/skills/using-arch-compiler
rm -rf ./.agents/skills/compiling-architecture
rm -rf ./.agents/skills/implementing-architecture
```

Optionally remove the runtime clone too:

```bash
rm -rf ~/.codex/arch-compiler
```

Alternative: install the whole skill pack via native Codex skill discovery.

This fallback uses a different on-disk layout from the bootstrap installer: one symlinked pack entry at `~/.agents/skills/arch-compiler` instead of three copied skill directories under `~/.agents/skills/`.

```bash
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

Verify this symlink layout:

```bash
ls -la ~/.agents/skills/arch-compiler
```

Uninstall this symlink layout:

```bash
rm ~/.agents/skills/arch-compiler
```

Optionally remove the runtime clone too:

```bash
rm -rf ~/.codex/arch-compiler
```

Advanced fallback: install all three skills directly from this GitHub repo by path:

This fallback uses a third on-disk layout: three copied skill directories under `~/.codex/skills/` managed by Codex's built-in GitHub installer.

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

To uninstall this layout:

```bash
rm -rf ~/.codex/skills/using-arch-compiler
rm -rf ~/.codex/skills/compiling-architecture
rm -rf ~/.codex/skills/implementing-architecture
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

## Use in Hermes

Hermes can discover these skills either from `skills.sh` / GitHub installs or by scanning a shared external skill directory.

If you already installed the skills for Codex, the easiest Hermes setup is to reuse the same installed skill folders:

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

Keep the full Architecture Compiler runtime repo in a stable local path such as `~/.hermes/arch-compiler` so Hermes-executed skills can find the compiler, patterns, schemas, config, and adapters without re-cloning.

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.hermes/arch-compiler
```

If you prefer Hermes-native installation instead of shared external directories, use Hermes' normal `skills.sh` or GitHub tap flow for discovery, then keep the same stable runtime clone at `~/.hermes/arch-compiler`.

## Portability Notes

- Codex: installable directly by GitHub path because the skill unit is a folder containing `SKILL.md`
- Claude Code: best mapped to custom slash commands in `.claude/commands/` or project memory in `CLAUDE.md`
- Other agent frameworks: use `skills/<name>/SKILL.md` as the source of truth and wrap it in that tool's native prompt or command format
