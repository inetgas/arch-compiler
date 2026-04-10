# Skills

说明：英文文档为权威版本。如本翻译与英文版本存在差异，请以英文版本为准。

语言： [English](../../skills/README.md) | 简体中文

本仓库发布了三个可复用的 agent skills：

- `skills/using-arch-compiler`
- `skills/compiling-architecture`
- `skills/implementing-architecture`

每个 skill 都被打包为一个独立文件夹，顶层包含一个 `SKILL.md`。

## 在 Codex 中安装

推荐优先使用官方 Codex 引导安装脚本。它会安装这三个 skill，并在标准 Codex 路径中 clone 或更新完整运行时仓库。

```bash
# 直接从 GitHub 一条命令安装
bash <(curl -fsSL https://raw.githubusercontent.com/inetgas/arch-compiler/main/scripts/install_codex_skills.sh)
```

如果你希望先检查仓库内容：

```bash
git clone https://github.com/inetgas/arch-compiler.git
cd arch-compiler
./scripts/install_codex_skills.sh
```

安装新 skills 后，请重启 Codex。

安装脚本会做这些事情：

- 将 `using-arch-compiler`、`compiling-architecture` 和 `implementing-architecture` 安装到共享的全局 agent skills 目录 `~/.agents/skills/`
- 在 `~/.codex/arch-compiler` clone 或更新完整运行时仓库
- 同时验证 skills 和运行时仓库布局是否正确

另一种方式：手动使用开放的 `skills.sh` / Vercel skills CLI。

```bash
# 列出本仓库发布的 skill
npx skills add inetgas/arch-compiler --list

# 将三个 skill 安装到共享的全局 agent skills 目录（~/.agents/skills/）
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -g -y

# clone 这些已安装 skill 依赖的完整运行时仓库
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler

# 验证三个 skill 已安装到全局目录
ls ~/.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

如果去掉 `-g`，这些 skill 会安装到当前项目的 `./.agents/skills/`，而不是全局 Codex 目录。

```bash
# 安装到当前项目（与当前仓库一起共享）
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -y

# 验证项目级安装
ls ./.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

重要：`skills` CLI 只会安装 skill 文件夹本身。整个工作流仍然需要完整的 Architecture Compiler 仓库位于稳定本地路径（例如 `~/.codex/arch-compiler`），这样 agent 才能在运行时访问编译器、模式库、schema、config 和适配器。

要卸载全局 `skills.sh` 布局：

```bash
rm -rf ~/.agents/skills/using-arch-compiler
rm -rf ~/.agents/skills/compiling-architecture
rm -rf ~/.agents/skills/implementing-architecture
```

要卸载项目级 `skills.sh` 布局：

```bash
rm -rf ./.agents/skills/using-arch-compiler
rm -rf ./.agents/skills/compiling-architecture
rm -rf ./.agents/skills/implementing-architecture
```

如果不再需要，也可以删除运行时仓库：

```bash
rm -rf ~/.codex/arch-compiler
```

另一种方式：通过 Codex 原生 skill discovery 安装整个 skill 包。

这个回退方案与引导安装脚本的磁盘布局不同：它会在 `~/.agents/skills/arch-compiler` 下创建一个 symlink 包入口，而不是像引导安装脚本那样在 `~/.agents/skills/` 下复制三个独立 skill 目录。

```bash
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

验证这种 symlink 布局：

```bash
ls -la ~/.agents/skills/arch-compiler
```

卸载这种 symlink 布局：

```bash
rm ~/.agents/skills/arch-compiler
```

如果不再需要，也可以删除运行时仓库：

```bash
rm -rf ~/.codex/arch-compiler
```

高级回退方案：直接按路径从这个 GitHub 仓库一次安装这三个 skill：

这个回退方案使用第三种磁盘布局：通过 Codex 内置 GitHub 安装器把三个独立 skill 目录复制到 `~/.codex/skills/`。

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo inetgas/arch-compiler \
  --path skills/using-arch-compiler skills/compiling-architecture skills/implementing-architecture
```

Codex 安装器说明：如果要从这个仓库一次安装多个 skill，请把所有 skill 路径都放在同一个 `--path` 参数后面。不要重复写 `--path`；当前安装器只会保留最后一个重复值。

安装后，可以这样确认三个目录都存在：

```bash
ls ~/.codex/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

要卸载这种布局：

```bash
rm -rf ~/.codex/skills/using-arch-compiler
rm -rf ~/.codex/skills/compiling-architecture
rm -rf ~/.codex/skills/implementing-architecture
```

也可以使用 GitHub URL 形式逐个安装：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/using-arch-compiler
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/compiling-architecture
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --url https://github.com/inetgas/arch-compiler/tree/main/skills/implementing-architecture
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

## 在 Hermes 中使用

Hermes 可以通过 `skills.sh` / GitHub 安装流发现这些 skills，也可以通过扫描共享的外部 skill 目录来发现它们。

如果你已经为 Codex 安装了这些 skills，最简单的 Hermes 配置方式是复用同一批已安装的 skill 目录：

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

同时请把完整的 Architecture Compiler 运行时仓库放在稳定本地路径，例如 `~/.hermes/arch-compiler`，这样 Hermes 执行这些 skills 时就能找到编译器、模式库、schema、config 和适配器，而不必重新 clone。

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.hermes/arch-compiler
```

如果你希望完全使用 Hermes 原生安装方式，而不是共享外部目录，也可以按照 Hermes 自己的 `skills.sh` 或 GitHub tap 流程完成发现/安装，但运行时仓库仍建议保存在 `~/.hermes/arch-compiler`。

## 可移植性说明

- Codex：由于 skill 单元是包含 `SKILL.md` 的文件夹，因此可以直接通过 GitHub 路径安装
- Claude Code：更适合通过 `.claude/commands/` 中的自定义 slash commands 或 `CLAUDE.md` 项目记忆来映射
- 其他 agent 框架：将 `skills/<name>/SKILL.md` 作为权威来源，再包装成该工具的原生 prompt 或命令格式
