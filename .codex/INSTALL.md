# Installing Architecture Compiler Skills for Codex

Enable these skills in Codex via native skill discovery. Clone the repo and symlink its `skills/` directory.

## Installation

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
```

You should see a symlink pointing to `~/.codex/arch-compiler/skills`.

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
