# Skills

说明：英文文档为权威版本。如本翻译与英文版本存在差异，请以英文版本为准。

语言： [English](../../skills/README.md) | 简体中文

本仓库发布了三个可复用的 agent skills：

- `skills/using-arch-compiler`
- `skills/compiling-architecture`
- `skills/implementing-architecture`

每个 skill 都被打包为一个独立文件夹，顶层包含一个 `SKILL.md`。

## 在 Codex 中安装

推荐方式：通过 Codex 原生 skill discovery 安装整个 skill 包。

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

安装新 skills 后，请重启 Codex。

高级方式：直接按路径从这个 GitHub 仓库安装：

```bash
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/using-arch-compiler
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/compiling-architecture
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/implementing-architecture
```

也可以使用 GitHub URL 形式：

```bash
scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/using-arch-compiler
scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/compiling-architecture
scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/implementing-architecture
```

## 在 Claude Code 中使用

Claude Code 不会像 Codex 那样原生安装 skills，但你可以把相同能力映射为项目级 slash commands。

本仓库已经提供了可直接复制使用的命令文件：

- `adapters/claude-code/commands/using-arch-compiler.md`
- `adapters/claude-code/commands/compile-architecture.md`
- `adapters/claude-code/commands/implement-architecture.md`

将它们复制到目标仓库的 `.claude/commands/`：

```bash
mkdir -p .claude/commands
cp adapters/claude-code/commands/compile-architecture.md .claude/commands/
cp adapters/claude-code/commands/implement-architecture.md .claude/commands/
cp adapters/claude-code/commands/using-arch-compiler.md .claude/commands/
```

这样会创建以下 Claude Code 命令：

- `/using-arch-compiler`
- `/compile-architecture`
- `/implement-architecture`

这些命令会把 Claude 指向本仓库中的权威 skill 文件：

- `~/.claude/arch-compiler/skills/using-arch-compiler/SKILL.md`
- `~/.claude/arch-compiler/skills/compiling-architecture/SKILL.md`
- `~/.claude/arch-compiler/skills/implementing-architecture/SKILL.md`

如果你的本地安装路径不同，请在首次使用前修改复制过去的命令文件，使其指向正确的稳定路径。

如果你希望 Claude Code 始终加载仓库级指导，也可以在 `CLAUDE.md` 中加入项目记忆，并引用同样的稳定路径 skill 文件。

## 可移植性说明

- Codex：由于 skill 单元是包含 `SKILL.md` 的文件夹，因此可以直接通过 GitHub 路径安装
- Claude Code：更适合通过 `.claude/commands/` 中的自定义 slash commands 或 `CLAUDE.md` 项目记忆来映射
- 其他 agent 框架：将 `skills/<name>/SKILL.md` 作为权威来源，再包装成该工具的原生 prompt 或命令格式
