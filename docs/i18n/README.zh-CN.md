# Architecture Compiler：面向架构层的 AI Harness

说明：英文文档为权威版本。如本翻译与英文版本存在差异，请以英文版本为准。

语言：[English](../../README.md) | 简体中文

ArchCompiler 会将约束条件和非功能性需求（NFR）编译成明确、可审查的架构决策，并给出清晰的权衡与成本影响。

它是一个构建在三个部分之上的“架构层 AI harness”：

- 一个确定性的编译器
- 一个经过整理的设计模式知识库
- 三个面向 agent 的工作流 skills

三者结合后，可以把需求转化为编译后的架构，要求在架构决策发生变化时重新审批，并在实现阶段围绕一个明确的架构契约开展工作。

编译器本身刻意保持简单：没有 LLM 推理、没有隐藏默认值，也没有黑箱式的选择逻辑。真正的架构智能来自模式库，以及以下三个 skill 所承载的工作流纪律：

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

[![CI - Test Suite](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml/badge.svg)](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Patterns](https://img.shields.io/badge/Patterns-180+-success)
![Skills](https://img.shields.io/badge/Skills-3-orange)
![Core](https://img.shields.io/badge/Core-No--LLM%20Inference-black)

> **标签：** `architecture-as-code`, `architecture-harness`, `agent-harness`, `deterministic-compiler`, `pattern-registry`, `nfr-enforcement`, `ai-governance`

## 核心理念

- **模式就是知识库。** 所有架构逻辑都保存在 `patterns/` 下的 pattern 文件中，编译器本身刻意保持简单。
- **基于包含条件的筛选。** Pattern 通过 `supports_constraints` 和 `supports_nfr` 规则声明它适用的 spec 条件；只有当所有规则都匹配 spec 时，该 pattern 才会被选中。
- **Schema 优先。** `schemas/canonical-schema.yaml` 定义 spec 契约；`schemas/pattern-schema.yaml` 定义 pattern 契约。它们都是事实来源。

---

## 快速开始

如果你的系统中没有 `python` 命令，请在下面的命令里使用 `python3` 替代。

```bash
# 如有需要，先安装 pipx（推荐用于 Python CLI 应用）
brew install pipx

# 从当前仓库安装 CLI
pipx install .

# 编译一个真实示例 spec（输出到 stdout）
archcompiler tests/fixtures/no-advisory-success.yaml

# 编译并将产物写入目录
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/

# Verbose 模式：内联 pattern 注释 + rejected-patterns 文件
archcompiler tests/fixtures/no-advisory-success.yaml -v
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v

# 为输出文件名附加 UTC 时间戳
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v -t
```

### 开发环境搭建

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装本地开发依赖
python -m pip install -r tools/requirements.txt
python -m pip install -e .

# 直接从源码树运行编译器
python tools/archcompiler.py tests/fixtures/no-advisory-success.yaml
```

请在 `arch-compiler/` 仓库根目录运行开发命令。有些测试会通过相对当前工作目录的路径调用 `tools/archcompiler.py`；如果你从父目录运行，这些测试会失败。

---

## 安装 Agent Skills

这个仓库还提供可安装的 agent skills。

### Codex

可以直接告诉 Codex：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/inetgas/arch-compiler/refs/heads/main/.codex/INSTALL.md
```

或者按原生方式手动安装：

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

安装完成后请重启 Codex。

### Skill 入口

- `skills/using-arch-compiler` = 选择正确工作流；如果架构发生变化，路由回编译阶段
- `skills/compiling-architecture` = 编译并最终确认架构
- `skills/implementing-architecture` = 按已审批架构实现系统

### Claude Code

Claude Code 不会像 Codex 那样原生发现 skills，但本仓库在 `adapters/claude-code/commands/` 中提供了可直接复制使用的命令适配文件，其中包括路由入口。

可用命令适配文件：

- `using-arch-compiler.md`
- `compile-architecture.md`
- `implement-architecture.md`

---

## Spec 格式

输入 spec 是一个 YAML 文件，并按照 `schemas/canonical-schema.yaml` 进行校验。示例如下：

```yaml
# ─── EXAMPLE SPEC ───
# This is a minimal spec showing the basic structure.
# You'll add fields progressively as your requirements become clearer.
# See test-specs/ for more complete examples and edge cases.
project:
  name: My Service
  domain: ecommerce
functional:
  summary: REST API for product catalogue
constraints:
  cloud: azure
  language: python
  platform: api
nfr:
  availability:
    target: 0.999
  latency:
    p95Milliseconds: 100
    p99Milliseconds: 200
  security:
    auth: jwt
```

所有未提供的字段都会从 `config/defaults.yaml` 中补齐，并记录到输出中的 `assumptions` 部分。

如果你想显式排除那些本来会被选中的 pattern（例如对当前范围来说太复杂），可以在顶层添加 `disallowed-patterns`：

```yaml
disallowed-patterns:
  - ops-low-cost-observability
  - ops-slo-error-budgets
```

被排除的 pattern 会出现在 `rejected-patterns.yaml` 中，并带有 `phase: phase_2_5_disallowed_patterns`。如果某个 ID 在模式库中不存在，编译器会给出警告。

更多覆盖边界条件、平台组合、合规需求等示例，请查看 `test-specs/`。

---

## 编译器输出

### stdout

编译器总会把编译后的 spec 输出到 stdout，也就是应用了所有默认值后的合并 spec；在 verbose 模式下，还会带上内联 pattern 注释。成功退出码为 `0`，校验失败退出码为 `1`。

### 使用 `-o` 写出的文件

| 文件 | 模式 | 说明 |
|------|------|------|
| `compiled-spec.yaml` | 总是输出 | 带 assumptions 的完整合并 spec；可以重新作为输入 |
| `selected-patterns.yaml` | 总是输出 | 被选中的 patterns，包含 match score 和 honored rules |
| `rejected-patterns.yaml` | 仅 `-v` | 被过滤掉的 patterns，包含原因和过滤阶段 |
| `compiled-spec-<timestamp>.yaml` | `-t` | 与上述同类文件一致，但文件名追加 UTC 时间戳 |

### Verbose 模式下的内联注释

启用 `-v` 后，编译后的 spec 会在字段旁标注触发该字段的 patterns：

```yaml
constraints:
  platform: api  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
  cloud: aws     # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
nfr:
  availability:
    target: 0.999  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (14 more)
```

这样你可以直接看到 spec 值与被选中 patterns 之间的关系。

---

## Pattern 选择流程

| 阶段 | 发生什么 |
|------|----------|
| **1. Parse & Validate** | 加载 spec，校验 schema，检查语义一致性 |
| **2. Merge Defaults** | 用 `config/defaults.yaml` 填补缺失字段，并记录到 `assumptions` |
| **2.5 Disallowed filter** | 去除 `disallowed-patterns` 中列出的 patterns；未知 ID 产生警告 |
| **3.1 Constraint filter** | 保留那些 `supports_constraints` 规则全部匹配 spec 的 patterns |
| **3.2 NFR filter** | 保留那些 `supports_nfr` 规则全部匹配 spec 的 patterns |
| **3.3 Conflict resolution** | 去除冲突 patterns；胜出者按更高 match score、再按更低成本意图决定 |
| **3.4 Config merge** | 将 pattern 的 `defaultConfig` 合并到 `assumptions.patterns` |
| **3.5 Coding filter** | 除非设置 `--include-coding-patterns`，否则移除 coding-level patterns |
| **4. Cost feasibility** | 检查总成本是否超过 `cost.ceilings`；超出时发 advisory warning |
| **5. Output** | 输出编译后的 spec 到 stdout；如果指定 `-o`，则写出文件产物 |

### Coding patterns

默认情况下，类型为 `coding` 的 patterns（如 GoF、DI、测试策略、开发工作流）会被排除；在 AI coding agent 时代，这些通常可以按需处理。若要包含它们，请使用 `--include-coding-patterns`。

---

## 渐进式细化

编译器是为迭代式、渐进式使用而设计的。你不需要一开始就写出完整 spec；可以先从最小集合开始，再随着理解加深逐步增加约束。

### 一个典型工作流

```text
Start minimal → compile → review assumptions → add constraints → recompile → ...
```

**步骤 1：先从最基本的字段开始**

```yaml
constraints:
  cloud: aws
  language: javascript
  platform: api
nfr:
  availability:
    target: 0.999
```

运行编译器后，输出中的 `assumptions` 会展示所有被自动补齐的默认值，也就是编译器替你做出的默认决策。先审查这些值，再决定是否要显式写入。

**步骤 2：随着需求明确，逐步加入 NFR 约束**

```yaml
nfr:
  availability:
    target: 0.999
  latency:
    p95Milliseconds: 50
    p99Milliseconds: 100
```

每增加一个约束，都会进一步缩小 pattern 选择范围。有些之前会被选中的 patterns 会被排除；在 `-v` 模式下，你可以通过 `rejected-patterns.yaml` 查看具体原因。

在某些情况下，spec 本身也可能被拒绝：如果某个硬性 NFR 目标（例如非常严格的延迟或高可用要求）无法被当前模式库中的任何 pattern 满足，编译器会以退出码 `1` 结束，并告诉你具体失败点。这通常意味着你的约束彼此冲突，或需要模式库中尚不存在的新 pattern。

**步骤 3：显式启用功能特性**

```yaml
constraints:
  features:
    caching: true
```

功能开关位于 `constraints.features` 下，而不是 `nfr` 下。它们表示你显式需要的功能特性，而不是性能目标。

当某个 pattern 被选中时，编译器可能输出 `warn_nfr` advisory，也就是提示该 pattern 在你当前 NFR 条件下可能被“用得不值”。例如，在没有吞吐量 NFR 的情况下开启缓存，可能会出现：

```text
⚠️  cache-aside: peak read QPS is 5 req/s (<10 req/s). Caching overhead
    (infrastructure, invalidation, serialization) may outweigh benefit at this scale.
```

这表示编译器认为该 pattern 虽然被选中了，但在当前规模下未必值得引入，提示你补充更具体的 NFR 数据，或者重新评估这个功能开关。

**步骤 4：补充吞吐量数据以消除 warn_nfr advisory**

如果你在启用缓存（或其他对吞吐量敏感的 pattern）后看到了 `warn_nfr` advisory，可以补充实际峰值 QPS：

```yaml
nfr:
  throughput:
    peak_query_per_second_read: 20
    peak_query_per_second_write: 10
```

有了真实吞吐量数据后，编译器就能做出更明确的判断：要么 advisory 消失（说明缓存是合理的），要么继续保留并给出更具体原因。无论哪种情况，都比在信息不足时盲目选中一个 pattern 更有价值。

**步骤 5：当你关心成本与运维模型时，请显式给出 `cost` 与 `operating_model`**

```yaml
cost:
  intent:
    priority: optimize-tco
  ceilings:
    monthly_operational_usd: 500
    one_time_setup_usd: 1000
operating_model:
  ops_team_size: 2
  single_resource_monthly_ops_usd: 10000
  on_call: true
  deploy_freq: daily
  amortization_months: 24
```

编译器会对三类成本做完整的可行性分析：

- **Pattern OpEx**：所有被选中 patterns 的月度基础设施成本之和
- **Ops team cost**：`ops_team_size × single_resource_monthly_ops_usd × on_call_multiplier × deploy_freq_multiplier`
- **CapEx (one-time)**：采用和落地这些 patterns 的一次性成本

其中 on_call_multiplier 反映了 [Google SRE Book](https://sre.google/sre-book/being-on-call/) 中描述的 SRE 值班开销；deploy_freq_multiplier 则反映了 [DORA State of DevOps](https://dora.dev/research/) 关于部署频率与运维负担关系的研究结论。

这些成本会与你声明的 ceiling 做比较。超出后会产生 `[high]` warning，并说明当前活跃的成本意图（例如 `optimize-tco`）。如果没有显式给出 `operating_model`，编译器会默认 `ops_team_size: 0`，这会让运维团队成本变成 0，从而明显低估真实 TCO。

### 为什么这种方式有效

`compiled-spec.yaml` 本身就是一个合法的输入 spec。再次将它输入编译器，会得到同样的输出——`assumptions` 会被保留，只有真正缺失的字段才会被继续补齐。这意味着：

- 你可以直接编辑编译后的 spec，然后再次编译；你的修改会被尊重
- 输出始终是完整、自洽、可独立存在的决策记录
- 在任何阶段，输出都具有意义；你不需要“先把 spec 填完整”才有价值

### 每个阶段会发生什么变化

下表对应演示视频 [[Architecture Compiler](https://www.youtube.com/watch?v=QPqNyozTArY)] 中展示的同一条渐进式流程：

| 步骤 | 你新增什么 | 编译器会做什么 |
|------|-----------|--------------|
| 1 | 最小 spec（cloud、language、platform、availability） | 选择基础 patterns，并把缺失字段补入 `assumptions` |
| 2 | `-v` 参数 | 给每个 spec 字段附加触发它的 pattern 注释，并写出 `rejected-patterns.yaml` |
| 3 | 延迟 NFR（`p95`、`p99`） | 拒绝无法满足目标的 patterns；若没有任何 pattern 满足，整个 spec 也可能被拒绝 |
| 4 | `features.caching: true` | 激活 cache-aside 及相关 patterns；如果当前 QPS 太低，会产生 `warn_nfr` advisory |
| 5 | 吞吐量 NFR（`peak_query_per_second_read/write`） | 用真实负载数据重新评估 advisory 和 patterns |
| 6 | 成本意图（`optimize-tco`、`minimize-opex`、`minimize-capex`） | 触发成本可行性检查；如果超出 ceiling，输出 `[high]` warning |

---

## 项目结构

```text
.
├── README.md                   英文主文档
├── AGENTS.md                   Agent 工作流的权威根指导
├── README-AGENTS.md            面向 AI agents 的仓库说明
├── CLAUDE.md                   Claude 专用入口，指向 AGENTS.md 和 skills
├── LICENSE                     MIT License
├── CHANGELOG.md                仓库变更记录
├── CODE_OF_CONDUCT.md          行为准则
├── CONTRIBUTING.md             贡献指南
├── pyproject.toml              项目元数据、依赖和工具配置
├── .codex/                     Codex 原生安装与集成辅助文件
├── .github/                    GitHub 配置（CI/CD 工作流）
├── adapters/                   跨 agent 的命令适配器
├── patterns/                   pattern JSON 文件 —— 知识库本体
├── schemas/                    spec / pattern / capability 契约
├── config/                     默认值配置
├── tools/                      编译器与审计工具
├── tests/                      pytest 测试套件
├── test-specs/                 直接可参考的 spec
├── docs/                       补充文档
├── reports/                    审计工具输出（本地生成）
└── skills/                     Agent skills 与安装说明
```

更细的结构、子目录和文件说明，请参考英文版 `README.md` 中的 Project Structure 部分。

---

## 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -q

# 输出更详细的测试日志
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_compiler_integration.py -v
```

测试覆盖整个编译器流水线、pattern schema 校验、冲突对称性、NFR/constraint 逻辑、成本可行性等。完整列表请看英文版 `docs/test-inventory.md`。

---

## 安装 Skills

本仓库还发布了三个可复用的 agent skills：

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

Codex 用户可以直接按 GitHub 路径安装：

```bash
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/using-arch-compiler
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/compiling-architecture
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/implementing-architecture
```

Claude Code 用户可以把 `adapters/claude-code/commands/` 中的适配文件复制到 `.claude/commands/`，其中包括路由命令。

安装细节和跨 agent 使用方式，请看 [skills README 中文版](skills.README.zh-CN.md)。

---

## 审计工具

```bash
# 审计 pattern 元数据质量（描述、成本、NFR 规则）
python tools/audit_patterns.py

# 审计 NFR/constraint 规则路径（捕获过期 JSON pointer）
python tools/audit_nfr_logic.py

# 审计冲突对称性（如果 A 冲突 B，则 B 也必须冲突 A）
python tools/audit_asymmetric_conflicts.py
```

每个工具的完整说明请见英文版 `docs/tools.md`。

---

## 新增或编辑 Patterns

1. 如果需要新字段，更新 `schemas/pattern-schema.yaml`
2. 如果需要新的 spec 字段，更新 `schemas/canonical-schema.yaml`
3. 在 `patterns/` 中新增或编辑 pattern 文件
4. 运行 `python tools/audit_patterns.py` 检查质量
5. 运行 `python -m pytest tests/ -q` 确认没有破坏现有行为

关键规则：

- Pattern ID 必须与文件名一致（例如 `cache-aside.json` → `id: "cache-aside"`）
- `supports_constraints` 和 `supports_nfr` 规则使用 AND 逻辑 —— 所有规则都必须匹配，pattern 才会被选中
- 冲突声明必须是**双向的** —— 如果 A 冲突 B，则 B 也必须声明冲突 A
- 同一组变体 pattern（例如 `arch-serverless--aws`、`arch-serverless--azure`）必须与其所有同级变体彼此冲突
- 不要在编译器中使用 pattern ID 字符串匹配来写逻辑 —— 所有逻辑都应编码在 pattern 元数据中

---

## 下一步

如果你想进一步阅读：

- skills 安装与使用：请看 [skills README 中文版](skills.README.zh-CN.md)
- schema 详细说明：请参考英文版 `schemas/README.md`
- 编译器工具细节：请参考英文版 `docs/tools.md`
- agent 工作流说明：请参考英文版 `README-AGENTS.md`

如果翻译尚未覆盖你需要的某个更深层文档，请优先查看英文版本。
