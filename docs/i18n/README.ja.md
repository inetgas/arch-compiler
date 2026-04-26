# Architecture Compiler: アーキテクチャレベルの AI Harness

注意: 英語版ドキュメントが正本です。翻訳と英語版に差異がある場合は、英語版を優先してください。

言語: [English](../../README.md) | [简体中文](README.zh-CN.md) | [Español](README.es.md) | 日本語 | [한국어](README.ko.md)

ArchCompiler は、制約と非機能要件（NFR）を、明示的でレビュー可能なアーキテクチャ判断へとコンパイルし、トレードオフとコスト影響を明確にします。

これは、決定的コンパイラ、厳選されたパターンレジストリ、そして agent 向けワークフロースキルの 3 つで構成された、アーキテクチャレベルの AI harness です。これらを組み合わせることで、要件をコンパイル済みアーキテクチャに変換し、アーキテクチャ判断が変わったときには承認・再承認の流れに戻し、明示的なアーキテクチャ契約に基づいて実装を進められます。

コンパイラ自体は意図的にシンプルです。LLM 推論はなく、隠れたデフォルトもなく、ブラックボックスな選定ロジックもありません。アーキテクチャ上の知性は、レジストリと、次のスキルが担うワークフロー規律にあります。

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

## このリポジトリが見つかる検索意図

次のようなものを探している場合:

- architecture selection skill
- deterministic architecture compiler
- architecture-as-code tools
- NFR enforcement for agent workflows
- implementation from approved architecture
- architecture harness / harness engineering
- architecture design pattern registry

まず見るべきもの:

- `skills/using-arch-compiler` — 適切なアーキテクチャワークフローへルーティング
- `skills/compiling-architecture` — 要件、制約、NFR、コスト意図を明示的なアーキテクチャ判断へコンパイル
- `skills/implementing-architecture` — 承認済みアーキテクチャ契約から実装

[![CI - Test Suite](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml/badge.svg)](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Registry](https://img.shields.io/badge/Registry-Curated-success)
![Skills](https://img.shields.io/badge/Skills-Workflow-orange)
![Core](https://img.shields.io/badge/Core-No--LLM%20Inference-black)

> **タグ:** `architecture-as-code`, `architecture-harness`, `agent-harness`, `deterministic-compiler`, `pattern-registry`, `nfr-enforcement`, `ai-governance`

## 基本思想

- **パターンが知識ベースです。** すべてのアーキテクチャロジックは `patterns/` 配下のパターンファイルにあります。コンパイラは意図的に単純に保っています。
- **包含条件ベースのフィルタリング。** パターンは `supports_constraints` と `supports_nfr` ルールで、どの spec 条件をサポートするかを宣言します。すべてのルールが spec に一致したとき、そのパターンが選ばれます。
- **Schema-first。** `schemas/canonical-schema.yaml` が spec 契約を定義し、`schemas/pattern-schema.yaml` が pattern 契約を定義します。どちらも正本です。

---

## クイックスタート

環境に `python` がない場合は、以下のコマンドの `python` を `python3` に置き換えてください。

```bash
# 必要であれば pipx をインストール（Python CLI アプリ向けに推奨）
brew install pipx

# 現在のリポジトリから CLI をインストール
pipx install .

# 実際のサンプル spec をコンパイル（stdout に出力）
archcompiler tests/fixtures/no-advisory-success.yaml

# コンパイルして成果物をディレクトリに書き出す
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/

# Verbose モード — インラインの pattern コメント + rejected-patterns ファイル
archcompiler tests/fixtures/no-advisory-success.yaml -v
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v

# 出力ファイル名に UTC タイムスタンプを付加
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v -t
```

### 開発環境セットアップ

```bash
# 仮想環境を作成して有効化
python3 -m venv .venv
source .venv/bin/activate

# ローカル開発用依存関係をインストール
python -m pip install -r tools/requirements.txt
python -m pip install -e .

# ソースツリーからコンパイラを実行
python tools/archcompiler.py tests/fixtures/no-advisory-success.yaml
```

開発コマンドは `arch-compiler/` リポジトリのルートで実行してください。一部のテストは `tools/archcompiler.py` を現在の作業ディレクトリ基準の相対パスで呼び出すため、親ディレクトリから実行すると失敗します。

---

## Agent Skills のインストール

このリポジトリにはインストール可能な agent skills も含まれています。

### Codex

推奨: 公式の Codex bootstrap installer を使ってください。3 つの skill をインストールし、完全な runtime リポジトリを標準の Codex パスへ clone または更新します。

```bash
# GitHub からワンコマンドでインストール
bash <(curl -fsSL https://raw.githubusercontent.com/inetgas/arch-compiler/main/scripts/install_codex_skills.sh)
```

先にリポジトリを確認したい場合:

```bash
git clone https://github.com/inetgas/arch-compiler.git
cd arch-compiler
./scripts/install_codex_skills.sh
```

インストール後に Codex を再起動してください。

installer が行うこと:

- `using-arch-compiler`、`compiling-architecture`、`implementing-architecture` を共有グローバル agent skills ディレクトリ `~/.agents/skills/` にインストール
- 完全な runtime リポジトリを `~/.codex/arch-compiler` に clone または更新
- インストール済み skill と runtime リポジトリ構成の両方を検証

別案: オープンな `skills.sh` / Vercel skills CLI を使って手動インストール。

```bash
# この repo が公開している skill を一覧表示
npx skills add inetgas/arch-compiler --list

# 3 つすべてを共有グローバル agent skills ディレクトリ（~/.agents/skills/）にインストール
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -g -y

# インストールされた skill が使う完全な runtime リポジトリを clone
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler

# 3 つの skill がグローバルにインストールされたことを確認
ls ~/.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

`-g` を省略すると、skill はグローバル Codex ディレクトリではなく、現在のプロジェクトの `./.agents/skills/` にインストールされます。

```bash
# プロジェクトローカルにインストール（現在の repo と共有）
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -y

# プロジェクトローカルインストールを確認
ls ./.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

重要: `skills` CLI がインストールするのは skill フォルダだけです。ワークフローには依然として、コンパイラ、パターンレジストリ、schema、config、adapter に agent がアクセスできるよう、`~/.codex/arch-compiler` のような安定したローカルパスに完全な Architecture Compiler リポジトリが必要です。

グローバル `skills.sh` レイアウトをアンインストールするには:

```bash
rm -rf ~/.agents/skills/using-arch-compiler
rm -rf ~/.agents/skills/compiling-architecture
rm -rf ~/.agents/skills/implementing-architecture
```

プロジェクトローカル `skills.sh` レイアウトをアンインストールするには:

```bash
rm -rf ./.agents/skills/using-arch-compiler
rm -rf ./.agents/skills/compiling-architecture
rm -rf ./.agents/skills/implementing-architecture
```

必要なら runtime clone も削除できます:

```bash
rm -rf ~/.codex/arch-compiler
```

別案: この repo に含まれる Codex ネイティブのオンボーディング手順を使う。

このフォールバックは bootstrap installer とは異なるディスク構成を使います。`~/.agents/skills/` 配下に 3 つのコピー済み skill ディレクトリを置く代わりに、`~/.agents/skills/arch-compiler` に 1 つの symlink pack entry を作ります。

Codex には次のように伝えます:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/inetgas/arch-compiler/refs/heads/main/.codex/INSTALL.md
```

または、ネイティブのインストール手順を直接実行:

```bash
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

この symlink レイアウトを確認:

```bash
ls -la ~/.agents/skills/arch-compiler
```

この symlink レイアウトをアンインストール:

```bash
rm ~/.agents/skills/arch-compiler
```

必要なら runtime clone も削除できます:

```bash
rm -rf ~/.codex/arch-compiler
```

重要: skill ファイルだけでは不十分です。ワークフローは、agent がコンパイラ、パターンレジストリ、schema、adapter にアクセスできるよう、完全なリポジトリが安定したローカルパスにあることを前提とします。再 clone や `/tmp/` 依存は避けてください。

高度なフォールバック: 公開 repo から 3 つの skill を直接インストール。

このフォールバックは 3 番目のディスクレイアウトを使います。Codex 組み込み GitHub installer が、`~/.codex/skills/` 配下に 3 つの skill ディレクトリをコピーします。

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo inetgas/arch-compiler \
  --path skills/using-arch-compiler skills/compiling-architecture skills/implementing-architecture
```

Codex installer の注意: この repo から複数の skill をインストールする場合は、すべての skill path を 1 つの `--path` 引数の後ろに並べてください。`--path` を繰り返さないでください。現在の installer では最後の繰り返し値だけが保持されます。

インストール後、3 つのディレクトリが存在することを確認:

```bash
ls ~/.codex/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

このレイアウトをアンインストール:

```bash
rm -rf ~/.codex/skills/using-arch-compiler
rm -rf ~/.codex/skills/compiling-architecture
rm -rf ~/.codex/skills/implementing-architecture
```

### Skill Entry Points

- `skills/using-arch-compiler` = 適切なワークフローを選び、アーキテクチャ変更時にはコンパイルへ戻す
- `skills/compiling-architecture` = アーキテクチャをコンパイルして確定する
- `skills/implementing-architecture` = 承認済みアーキテクチャを実装する

### Agent Workflow Preflight

アプリ側のアーキテクチャコンパイルや実装ワークフローに入る前に、共有 preflight helper を実行してください。これは Codex、Claude Code、その他の agent wrapper のどれがワークフローを駆動していても同じです。

```bash
# パッケージを CLI としてインストールした場合:
archcompiler-preflight --app-repo /path/to/app-repo --mode compile

# または、安定したローカル repo パスから helper を直接実行:
python3 ~/.codex/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
python3 ~/.claude/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
python3 ~/.hermes/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
```

承認済み `docs/architecture/` フォルダからコードを書き始める場合は `--mode implement` を使ってください。

### Claude Code

Claude Code には Codex ネイティブの skill discovery はありませんが、この repo には `adapters/claude-code/commands/` 配下に、router entrypoint を含むすぐ使える command adapter が用意されています。

セッションをまたいでも command がコンパイラ、pattern、schema を確実に見つけられるよう、完全な repo を `~/.claude/arch-compiler` のような安定したローカルパスに置いてください。

利用可能な command adapter:
- `using-arch-compiler.md`
- `compile-architecture.md`
- `implement-architecture.md`

### Hermes

Hermes は、`skills.sh` / GitHub install からも、共有の外部 skill directory をスキャンする形でも、これらの skill を見つけられます。

すでに Codex 用に skill をインストールしているなら、最も簡単なのは同じ skill directory を Hermes から再利用することです。

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

Hermes 実行の skill が再 clone なしでコンパイラ、pattern、schema、config、adapter を見つけられるよう、完全な runtime repo を `~/.hermes/arch-compiler` のような安定したローカルパスに置いてください。

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.hermes/arch-compiler
```

共有外部 directory ではなく Hermes ネイティブのインストールを使いたい場合は、Hermes の通常の `skills.sh` または GitHub tap の discovery フローに従い、そのうえで同じ安定した runtime clone を `~/.hermes/arch-compiler` に保持してください。

---

## Spec 形式

入力 spec は `schemas/canonical-schema.yaml` に対して検証される YAML ファイルです。例:

```yaml
# ─── EXAMPLE SPEC ───
# これは基本構造を示す最小 spec です。
# 要件が明確になるにつれて、フィールドを段階的に追加します。
# より完全な例やエッジケースは test-specs/ を参照してください。
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

指定されていないフィールドはすべて `config/defaults.yaml` から補完され、出力の `assumptions` セクションに記録されます。

通常なら選ばれる pattern を明示的に除外したい場合（例: スコープに対して複雑すぎる）は、トップレベルに `disallowed-patterns` リストを追加します。

```yaml
disallowed-patterns:
  - ops-low-cost-observability
  - ops-slo-error-budgets
```

除外された pattern は `rejected-patterns.yaml` に `phase: phase_2_5_disallowed_patterns` として記録されます。レジストリに存在しない ID には warning が出ます。

エッジケース、platform の組み合わせ、compliance 要件などを網羅した包括的な spec 例は `test-specs/` を参照してください。

---

## コンパイラ出力

### stdout

コンパイラは常に、コンパイル済み spec を stdout に出力します。これは、すべてのデフォルトが適用されたマージ済み spec であり、verbose mode ではインライン pattern comment も含みます。成功時の終了コードは `0`、検証エラー時は `1` です。

### `-o` で書き込まれるファイル

| File | Mode | Description |
|------|------|-------------|
| `compiled-spec.yaml` | always | assumptions を含む完全なマージ済み spec。再入力として使える |
| `selected-patterns.yaml` | always | 一致スコアと honor された rule を含む選択済み pattern |
| `rejected-patterns.yaml` | `-v` only | reason と filter phase を含む却下された pattern |
| `compiled-spec-<timestamp>.yaml` | `-t` | 同じファイルに UTC タイムスタンプを付けたもの（例: `compiled-spec-2026-03-17T19:36:31Z.yaml`） |

### Verbose mode のインラインコメント

`-v` を使うと、コンパイル済み spec の各フィールドに、それをトリガーした pattern が注釈されます。

```yaml
constraints:
  platform: api  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
  cloud: aws     # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
nfr:
  availability:
    target: 0.999  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (14 more)
```

これにより、spec の値と選択された pattern の関係がすぐに見えるようになります。

---

## Pattern 選択の仕組み

| Phase | What happens |
|-------|-------------|
| **1. Parse & Validate** | spec を読み込み、schema を検証し、semantic consistency を確認 |
| **2. Merge Defaults** | `config/defaults.yaml` から不足フィールドを補完し、`assumptions` に記録 |
| **2.5 Disallowed filter** | `disallowed-patterns` に含まれる pattern を除外し、未知 ID には warning |
| **3.1 Constraint filter** | `supports_constraints` ルールがすべて spec に一致する pattern を残す |
| **3.2 NFR filter** | `supports_nfr` ルールがすべて spec に一致する pattern を残す |
| **3.3 Conflict resolution** | 競合する pattern を除外。勝者は最高 match score、その後 cost intent に基づく最小コスト |
| **3.4 Config merge** | pattern の `defaultConfig` を `assumptions.patterns` にマージ |
| **3.5 Coding filter** | `--include-coding-patterns` がない限り coding-level pattern を除外 |
| **4. Cost feasibility** | 合計コストを `cost.ceilings` と照合し、advisory warning を出す |
| **5. Output** | コンパイル済み spec を stdout に出力し、`-o` 指定時は artifact file を書き出す |

### Coding patterns

デフォルトでは `coding` type の pattern（GoF、DI、test strategy、dev workflow）は除外されます。AI coding agent の時代では、これらは必要に応じて扱えるためです。含めたい場合は `--include-coding-patterns` を使ってください。

---

## Progressive Refinement

コンパイラは反復的・段階的な利用を前提に設計されています。最初から完全な spec は不要です。最小限から始めて、理解が進むにつれて制約を追加していきます。

### サンプルワークフロー

```
Start minimal → compile → review assumptions → add constraints → recompile → ...
```

**Step 1: まずは最小限から始める**

```yaml
constraints:
  cloud: aws
  language: javascript
  platform: api
nfr:
  availability:
    target: 0.999
```

コンパイラを実行すると、出力の `assumptions` セクションに適用されたデフォルトがすべて出ます。これはコンパイラがあなたの代わりに下した判断です。何を前提にしたかを理解するために確認してください。

**Step 2: わかってきた NFR 制約を追加する**

```yaml
nfr:
  availability:
    target: 0.999
  latency:           # ← latency target が分かった時点で追加
    p95Milliseconds: 50
    p99Milliseconds: 100
```

制約を追加するたびに pattern selection は絞り込まれます。以前は選ばれていた pattern が却下されることもあり、その理由は `rejected-patterns.yaml`（`-v` モード）で確認できます。

場合によっては spec 自体が reject されます。たとえば厳しい latency や高い availability などの hard NFR target を、利用可能な pattern のどれも満たせない場合、コンパイラは終了コード `1` で終了し、何が失敗したかを説明します。これは有用なシグナルです。制約同士が矛盾しているか、レジストリにまだ存在しない pattern が必要であることを意味します。

**Step 3: 機能は明示的に opt-in する**

```yaml
constraints:
  features:
    caching: true       # ← cache-aside などの関連 pattern をトリガー
```

feature flag は `nfr` ではなく `constraints.features` 配下に置きます。これは performance target ではなく、opt-in capability を表します。

pattern が一致すると、コンパイラは `warn_nfr` advisory を出すことがあります。これは、選択された pattern が現在の NFR 値では十分に活かされていないことを示す warning です。たとえば、throughput NFR なしで caching を有効にすると、次のような出力になることがあります。

```
⚠️  cache-aside: peak read QPS is 5 req/s (<10 req/s). Caching overhead
    (infrastructure, invalidation, serialization) may outweigh benefit at this scale.
```

これは、その pattern は選択されたが、現状の規模では見合わない可能性が高い、ということです。より具体的な NFR データを足すか、feature flag を見直すべきだという合図です。

**Step 4: throughput データを追加して warn_nfr advisory を解消する**

caching や他の throughput-sensitive な pattern を有効にした後で `warn_nfr` advisory が出た場合は、実際の peak QPS を追加してください。

```yaml
nfr:
  throughput:
    peak_query_per_second_read: 20    # ← compiler が caching benefit を再評価
    peak_query_per_second_write: 10
```

実際の throughput 数値が入ると、コンパイラは確定的な判断ができます。advisory が消えて caching が正当化されるか、あるいはより具体的な理由とともに advisory が残るかのどちらかです。どちらでも、根拠なく選ばれた pattern より有益です。

**Step 5: cost と operating_model は必要になった時点で明示する**

```yaml
cost:
  intent:
    priority: optimize-tco   # default は minimize-opex、他に minimize-capex
  ceilings:
    monthly_operational_usd: 500
    one_time_setup_usd: 1000
operating_model:
  ops_team_size: 2                    # 専任 ops エンジニアの人数
  single_resource_monthly_ops_usd: 10000  # エンジニア 1 人あたりのフルロード月額コスト
  on_call: true                       # ops team cost に 1.5× の multiplier を追加
  deploy_freq: daily                  # ops overhead に影響（daily = 1.0×、weekly = 0.8×、on-demand = 1.2×）
  amortization_months: 24             # TCO 用に CapEx を按分する期間
```

コンパイラは 3 つのコスト区分で完全な cost feasibility analysis を行います。

- **Pattern OpEx** — 選択された各 pattern の推定月次インフラコスト合計
- **Ops team cost** — `ops_team_size × single_resource_monthly_ops_usd × on_call_multiplier × deploy_freq_multiplier`（on-call multiplier は [Google SRE Book](https://sre.google/sre-book/being-on-call/) の on-call overhead、deploy frequency multiplier は [DORA State of DevOps](https://dora.dev/research/) の運用負荷知見を反映）
- **CapEx (one-time)** — 選択された pattern の導入・セットアップコスト

これらは宣言した ceiling と照合されます。超過すると、アクティブな cost intent を参照する `[high]` warning が出ます（例: `⚠️ [high] TCO exceeds ceiling by $26,760 (intent: optimize-tco)`）。`operating_model` がない場合、コンパイラは `ops_team_size: 0` をデフォルトにします。つまり ops team cost は 0 とみなされ、専任エンジニアがいるチームでは実際の TCO を大きく過小評価する可能性があります。

### なぜこれが機能するのか

`compiled-spec.yaml` は有効な入力 spec です。これを再度コンパイルしても同じ出力になり、`assumptions` は保持され、本当に欠けているフィールドだけが再補完されます。つまり:

- コンパイル済み spec を編集して再コンパイルできる。変更は尊重される
- 出力は常に、すべての判断を含む完全で自己完結した記録になる
- どの段階でも出力は意味を持つ。価値を得るのに「完全な」spec は不要

### 各段階で何が変わるか

この表はデモ動画 [[Architecture Compiler](https://www.youtube.com/watch?v=QPqNyozTArY)] と同じ進行を追っています。

| Step | You add | What the compiler does |
|------|---------|----------------------|
| 1 | Minimal spec (cloud, language, platform, availability) | baseline pattern を選び、未指定フィールドをすべて `assumptions` に補完 |
| 2 | `-v` flag | 各 spec field に、それをトリガーした pattern を注釈し、`rejected-patterns.yaml` を出力 |
| 3 | Latency NFR (`p95`, `p99`) | target を満たせない pattern を却下し、条件次第で spec 全体を reject |
| 4 | `features.caching: true` | cache-aside と関連 pattern を有効化し、現状の QPS が低すぎると `warn_nfr` を出す |
| 5 | Throughput NFR (`peak_query_per_second_read/write`) | `warn_nfr` advisory を解消し、実際の負荷データに基づいて pattern を再評価 |
| 6 | Cost intent (`optimize-tco`, `minimize-opex`, `minimize-capex`) | cost feasibility check を実行し、ceiling 超過時に `[high]` warning を出す |

---

## プロジェクト構成

```
.
├── README.md                   This file
├── AGENTS.md                   Canonical root guidance for agent workflows
├── README-AGENTS.md            Repo guide for AI agents
├── CLAUDE.md                   Claude-specific pointer to AGENTS.md and the skills
├── LICENSE                     MIT License
├── CHANGELOG.md                Repo change log
├── CODE_OF_CONDUCT.md          Repo code of conduct
├── CONTRIBUTING.md             Repo guide for contributions
├── pyproject.toml              Project metadata, dependencies, and tool config
├── .codex/                     Codex-native install and integration helpers
├── .github/                    GitHub configuration (CI/CD workflows)
├── adapters/                   Cross-agent command adapters
├── patterns/                   Curated pattern JSON files — the knowledge base
│   ├── arch-*.json             Macro-architecture patterns (monolith, microservices, serverless, …)
│   ├── api-*.json              API design patterns (REST, GraphQL, versioning)
│   ├── async-*.json            Async messaging patterns (event-driven, fire-and-forget, …)
│   ├── cache-*.json / write-*.json   Caching strategies (cache-aside, write-through, write-back)
│   ├── compliance-*.json       Regulatory compliance patterns (GDPR, CCPA, HIPAA, SOX)
│   ├── cost-*.json             Cost optimisation (cold-archive, egress, multi-tenant consolidation)
│   ├── cqrs-*.json / event-*.json / saga-*.json   CQRS, event sourcing, sagas
│   ├── data-*.json             Analytical data patterns (OLAP warehouse, stream processing, batch)
│   ├── db-*.json               Database patterns (managed Postgres, read replicas, sharding,
│   │                           NoSQL document, key-value, graph, time-series, vector)
│   ├── deploy-*.json           Deployment strategies (blue-green, canary, rolling)
│   ├── dev-*.json / gof-*.json / code-*.json   Coding-level patterns (excluded by default)
│   ├── finops-*.json           FinOps patterns (cost allocation, budget guardrails)
│   ├── genai-*.json            GenAI / LLM inference patterns (generic + provider variants)
│   ├── gov-*.json              Governance patterns (ADRs)
│   ├── hosting-*.json          Hosting patterns (managed PaaS, static frontend)
│   ├── iac-*.json              Infrastructure-as-code (Terraform, CloudFormation, Bicep)
│   ├── idp-oidc-*.json         OAuth2/OIDC identity provider patterns (Auth0, Okta, AWS Cognito)
│   ├── idp-saml-*.json         SAML 2.0 identity provider patterns (Auth0, Okta)
│   ├── obs-*.json              Observability (OpenTelemetry, golden signals)
│   ├── onprem-*.json           Air-gapped / on-premise patterns
│   ├── ops-*.json              Operations patterns (SLOs, runbooks, low-cost observability)
│   ├── pki-*.json              PKI / certificate authority patterns (internal CA)
│   ├── platform-*.json         Platform patterns (Kubernetes, service mesh, VM-first)
│   ├── policy-*.json           Policy enforcement patterns (PII, audit export)
│   ├── queue-*.json / exactly-once-*.json / distributed-*.json   Messaging guarantees
│   ├── release-*.json          Release management (feature flags)
│   ├── resilience-*.json       Resilience patterns (circuit breaker, bulkhead, rate limiting, retries)
│   ├── sec-*.json / secrets-*.json   Security patterns (auth variants, zero trust, secrets)
│   ├── sync-*.json             Synchronous request patterns (REST, gRPC)
│   ├── tenancy-*.json          Multi-tenancy isolation patterns (row-level, schema, per-tenant DB)
│   ├── test-*.json             Testing strategy patterns
│   └── ui-*.json               UI patterns (SPA, SSR, cross-platform)
│
├── schemas/
│   ├── canonical-schema.yaml       Input spec contract — authoritative source for all spec fields
│   ├── pattern-schema.yaml         Pattern manifest contract — authoritative source for pattern fields
│   ├── capability-vocabulary.yaml  Canonical names and aliases for provides/requires capability strings
│   └── README.md                   Schema reference documentation
│
├── config/
│   └── defaults.yaml           Default values applied when spec fields are omitted
│
├── tools/
│   ├── archcompiler.py             Main compiler (3,786 lines)
│   ├── audit_patterns.py           Pattern metadata quality audit
│   ├── audit_nfr_logic.py          NFR/constraint JSON pointer path validation
│   ├── audit_asymmetric_conflicts.py   Conflict symmetry audit (A↔B must be bidirectional)
│   └── requirements.txt
│
├── scripts/
│   ├── install_codex_skills.sh     Codex bootstrap installer
│   └── package_smoke_test.py       Built-wheel smoke test helper
│
├── tests/
│   ├── README.md                   Test suite overview
│   ├── run_all_tests.py            Helper to run the full suite
│   ├── fixtures/                   Reusable YAML fixtures for warn_nfr / cost tests
│   │   ├── cost-infeasibility.yaml
│   │   ├── eq-gate-multi-violation.yaml
│   │   ├── lte-threshold-violation.yaml
│   │   ├── nfr-threshold-violation.yaml
│   │   ├── no-advisory-success.yaml
│   │   └── ryw-advisory-success.yaml
│   │
│   │   Unit / component tests:
│   ├── test_evaluate_rule.py           Rule evaluator (_evaluate_rule) unit tests
│   ├── test_phase2_merge.py            Defaults merge (Phase 2)
│   ├── test_phase3_1_constraints.py    Constraint filtering (Phase 3.1)
│   ├── test_phase3_2_nfr.py            NFR filtering (Phase 3.2)
│   ├── test_phase3_3_conflicts.py      Conflict resolution (Phase 3.3)
│   ├── test_phase3_4_defaultconfig.py  Pattern defaultConfig merge (Phase 3.4)
│   ├── test_phase4_cost.py             Cost feasibility (Phase 4)
│   ├── test_requires_rules.py          requires_nfr / requires_constraints hard validators
│   ├── test_warn_nfr.py                warn_nfr / warn_constraints advisory warnings
│   ├── test_strip_null_values.py       Null stripping (unit + integration)
│   ├── test_semantic_validation.py     Semantic consistency checks (Phase 1)
│   ├── test_annotated_error_output.py  Error annotation output format
│   ├── test_error_suggestions.py       💡 Suggestions block in error output
│   ├── test_assumptions_preservation.py  Assumption round-trip / idempotency
│   ├── test_minimal_spec_recompile.py  Minimal spec recompile stability
│   ├── test_recompilation_idempotency.py  Full idempotency (compiled-spec → recompile = same)
│   ├── test_schema_driven_idempotency.py  Schema-level idempotency regression
│   ├── test_user_input_precedence.py   User values not overwritten by defaults
│   ├── test_proposals_1_4.py           Proposals 1–4 regression tests
│   │
│   │   Registry / pattern quality tests:
│   ├── test_pattern_schema_validation.py   All patterns valid against pattern-schema.yaml
│   ├── test_pattern_schema_regression.py   Pattern schema regression
│   ├── test_pattern_conflicts.py           Conflict symmetry (uses audit_asymmetric_conflicts.py)
│   ├── test_pattern_quality.py             Metadata quality (uses audit_patterns.py)
│   ├── test_nfr_constraint_logic.py        NFR/constraint path validity (uses audit_nfr_logic.py)
│   ├── test_registry_integrity.py          Capability vocabulary alias enforcement
│   ├── test_pattern_config_validation.py   defaultConfig / configSchema validation
│   ├── test_schema_compliance.py           Schema compliance regression
│   │
│   │   Integration / end-to-end tests:
│   ├── test_compiler_integration.py        Full pipeline integration (all test-specs/)
│   ├── test_disallowed_patterns.py         disallowed-patterns field behaviour
│   ├── test_disallowed_saas_providers.py   disallowed-saas-providers field behaviour
│   ├── test_nfr_filtering.py               NFR filtering end-to-end
│   ├── test_sec_auth_pattern_selection.py  Security auth pattern selection
│   ├── test_requirements_tracing.py        Requirements tracing
│   └── test_requirements_tracing_integration.py  Requirements tracing integration
│
├── test-specs/                 Named integration specs
│   │                           Naming: <category>_<sub-category>_<description>_<pass|fail>.yaml
│   │                           _pass = must compile with exit 0
│   │                           _fail = must compile with exit 1
│   ├── cloud_*                Cloud constraint tests
│   ├── cost_*                 Cost ceiling and preference tests
│   ├── feature_*              Feature flag tests (ai_inference, caching, streaming, …)
│   ├── input_*                Input shape and validation tests
│   ├── language_*             Language constraint tests
│   ├── messaging_*            Messaging delivery guarantee tests
│   ├── misc_*                 Persona and regression tests
│   ├── nfr_*                  NFR target tests (availability, latency, compliance, …)
│   ├── platform_*             Platform constraint tests
│   ├── saas_*                 SaaS provider and disallowed-provider tests
│   ├── schema_*               Schema validation error tests
│   ├── security_*             Security and PII tests
│   ├── tenancy_*              Multi-tenancy isolation tests
│   ├── config_override_*      Pattern config override tests
│   └── disallowed_patterns_*  disallowed-patterns tests
│
├── docs/
│   ├── tools.md                        Full reference for all tools in tools/
│   ├── test-inventory.md               All tests with descriptions and what they cover
│   ├── arch-platform-pattern-relationship.md   Platform ↔ pattern selection reference
│   └── COMPILER-CONFLICT-RESOLUTION.md         Conflict resolution algorithm documentation
│
├── reports/                    Audit tool output (generated locally, gitignored)
│   ├── asymmetric-conflicts-audit.json
│   ├── asymmetric-conflicts-fixes.json
│   └── nfr-constraint-logic-audit.json
│
└── skills/                     Agent skills and install docs
    ├── README.md                           Cross-agent skill install and usage notes
    ├── using-arch-compiler/SKILL.md       Workflow router skill
    ├── compiling-architecture/SKILL.md    Skill for compiling and finalising architecture
    └── implementing-architecture/SKILL.md Skill for implementing from approved architecture
```

---

## テスト実行

```bash
# すべてのテストを実行
python -m pytest tests/ -q

# 詳細出力でテスト実行
python -m pytest tests/ -v

# 特定のテストファイルだけ実行
python -m pytest tests/test_compiler_integration.py -v
```

テストは、コンパイラパイプラインの end-to-end、pattern schema validation、conflict symmetry、NFR/constraint logic、cost feasibility などをカバーしています。全一覧は `docs/test-inventory.md` を参照してください。

---

## Skills のインストール

この repo は再利用可能な agent skill を 3 つ公開しています。

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

Codex ユーザーは GitHub repo path から直接インストールできます。

```bash
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/using-arch-compiler
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/compiling-architecture
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/implementing-architecture
```

Claude Code ユーザーは `adapters/claude-code/commands/` の adapter を `.claude/commands/` にコピーして使えます。router command も含まれています。

インストール詳細と agent 横断の利用メモは `skills/README.md` を参照してください。

---

## 監査ツール

```bash
# Pattern metadata quality を監査（description, costs, NFR rules）
python tools/audit_patterns.py

# NFR/constraint rule path を監査（古い JSON pointer 参照を検出）
python tools/audit_nfr_logic.py

# Conflict symmetry を監査（A が B と conflict するなら、B も A を conflict すべき）
python tools/audit_asymmetric_conflicts.py
```

各ツールの詳細は `docs/tools.md` を参照してください。

---

## Pattern の追加・編集

1. 新しいフィールドが必要なら `schemas/pattern-schema.yaml` を更新
2. 新しい spec field が必要なら `schemas/canonical-schema.yaml` を更新
3. `patterns/` 配下の pattern file を追加または編集
4. `python tools/audit_patterns.py` を実行して品質を確認
5. `python -m pytest tests/ -q` を実行して破壊がないことを確認

重要なルール:
- Pattern ID は filename と一致している必要があります（例: `cache-aside.json` → `id: "cache-aside"`）
- `supports_constraints` と `supports_nfr` ルールは AND ロジックです。すべて一致したときだけ pattern が選ばれます
- Conflict 宣言は **双方向** でなければなりません。A が B と conflict するなら、B も A を宣言する必要があります
- sibling variant pattern（例: `arch-serverless--aws`, `arch-serverless--azure`）は、それぞれすべての sibling と conflict する必要があります
- コンパイラ内で pattern ID 文字列マッチングを使わないでください。すべてのロジックは pattern metadata にエンコードしてください
