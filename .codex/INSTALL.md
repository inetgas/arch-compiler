# Installing Architecture Compiler Skills for Codex

Recommended: use the official bootstrap installer. It installs the three skills into Codex and clones or updates the full runtime repo in the canonical Codex path.

## Recommended Install

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/inetgas/arch-compiler/main/scripts/install_codex_skills.sh)
```

If you prefer to inspect the repo first:

```bash
git clone https://github.com/inetgas/arch-compiler.git
cd arch-compiler
./scripts/install_codex_skills.sh
```

This installs:
- `~/.agents/skills/using-arch-compiler`
- `~/.agents/skills/compiling-architecture`
- `~/.agents/skills/implementing-architecture`

and ensures the runtime repo exists at:
- `~/.codex/arch-compiler`

## Verify Bootstrap Install

```bash
ls ~/.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
test -f ~/.codex/arch-compiler/tools/archcompiler.py
test -f ~/.codex/arch-compiler/tools/archcompiler_preflight.py
test -d ~/.codex/arch-compiler/patterns
test -d ~/.codex/arch-compiler/schemas
test -d ~/.codex/arch-compiler/config
```

## Uninstall Bootstrap Install

```bash
rm -rf ~/.agents/skills/using-arch-compiler
rm -rf ~/.agents/skills/compiling-architecture
rm -rf ~/.agents/skills/implementing-architecture
```

Optionally remove the runtime clone:

```bash
rm -rf ~/.codex/arch-compiler
```

## Manual Installation

Manual installation uses a different on-disk layout: a single symlinked pack entry at `~/.agents/skills/arch-compiler` instead of three copied skill directories.

Enable these skills in Codex via native skill discovery. Clone the repo and symlink its `skills/` directory.

1. Clone the repository:

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler
```

2. Create the discovery symlink:

```bash
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

3. Restart Codex.

## Verify

```bash
ls -la ~/.agents/skills/arch-compiler
test -f ~/.codex/arch-compiler/tools/archcompiler.py
test -f ~/.codex/arch-compiler/tools/archcompiler_preflight.py
test -d ~/.codex/arch-compiler/patterns
test -d ~/.codex/arch-compiler/schemas
test -d ~/.codex/arch-compiler/config
```

You should see a symlink pointing to `~/.codex/arch-compiler/skills`, and the runtime repo should contain the compiler, preflight helper, patterns, schemas, and config directories.

## Updating

```bash
cd ~/.codex/arch-compiler && git pull
```

## Uninstalling

```bash
rm ~/.agents/skills/arch-compiler
```

Optionally remove the clone:

```bash
rm -rf ~/.codex/arch-compiler
```
