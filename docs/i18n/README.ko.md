# Architecture Compiler: 아키텍처 레벨 AI Harness

참고: 영어 문서가 정본입니다. 이 번역과 영어 버전이 다를 경우 영어 버전을 따르세요.

언어: [English](../../README.md) | [简体中文](README.zh-CN.md) | [Español](README.es.md) | [日本語](README.ja.md) | 한국어

ArchCompiler는 제약 조건과 비기능 요구사항(NFR)을 명시적이고 검토 가능한 아키텍처 결정으로 컴파일하며, 트레이드오프와 비용 영향을 분명하게 드러냅니다.

이 도구는 결정적 컴파일러, 엄선된 패턴 레지스트리, 그리고 agent용 워크플로 스킬이라는 세 부분으로 구성된 아키텍처 레벨 AI harness입니다. 이 셋이 함께 요구사항을 컴파일된 아키텍처로 바꾸고, 아키텍처 결정이 바뀌면 승인 및 재승인 흐름으로 되돌리며, 명시적 아키텍처 계약을 기준으로 구현을 진행하게 합니다.

컴파일러 자체는 의도적으로 단순합니다. LLM 추론도 없고, 숨겨진 기본값도 없고, 블랙박스 선택 로직도 없습니다. 아키텍처 지능은 레지스트리와 다음 스킬들이 강제하는 워크플로 규율에 있습니다.

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

## 이 저장소를 찾는 검색 의도

다음과 같은 것을 찾고 있다면:

- architecture selection skill
- deterministic architecture compiler
- architecture-as-code tools
- NFR enforcement for agent workflows
- implementation from approved architecture
- architecture harness / harness engineering
- architecture design pattern registry

다음부터 시작하세요:

- `skills/using-arch-compiler` — 올바른 아키텍처 워크플로로 라우팅
- `skills/compiling-architecture` — 요구사항, 제약, NFR, 비용 의도를 명시적 아키텍처 결정으로 컴파일
- `skills/implementing-architecture` — 승인된 아키텍처 계약으로부터 시스템 구현

[![CI - Test Suite](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml/badge.svg)](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Registry](https://img.shields.io/badge/Registry-Curated-success)
![Skills](https://img.shields.io/badge/Skills-Workflow-orange)
![Core](https://img.shields.io/badge/Core-No--LLM%20Inference-black)

> **태그:** `architecture-as-code`, `architecture-harness`, `agent-harness`, `deterministic-compiler`, `pattern-registry`, `nfr-enforcement`, `ai-governance`

## 핵심 철학

- **패턴이 곧 지식 베이스입니다.** 모든 아키텍처 로직은 `patterns/` 아래 패턴 파일에 있습니다. 컴파일러는 의도적으로 단순하게 유지됩니다.
- **포함 조건 기반 필터링.** 패턴은 `supports_constraints` 와 `supports_nfr` 규칙을 통해 어떤 spec 조건을 지원하는지 선언합니다. 모든 규칙이 spec과 일치할 때 패턴이 선택됩니다.
- **Schema-first.** `schemas/canonical-schema.yaml` 이 spec 계약을, `schemas/pattern-schema.yaml` 이 pattern 계약을 정의합니다. 둘 다 진실의 원천입니다.

---

## 빠른 시작

시스템에 `python` 명령이 없다면 아래 명령의 `python` 을 `python3` 으로 바꾸세요.

```bash
# 필요하면 pipx 설치 (Python CLI 앱에 권장)
brew install pipx

# 현재 저장소에서 CLI 설치
pipx install .

# 실제 예제 spec 컴파일 (stdout 출력)
archcompiler tests/fixtures/no-advisory-success.yaml

# 컴파일하고 산출물을 디렉터리에 기록
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/

# Verbose 모드 — 인라인 패턴 주석 + rejected-patterns 파일
archcompiler tests/fixtures/no-advisory-success.yaml -v
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v

# 출력 파일명에 UTC 타임스탬프 추가
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v -t
```

### 개발 환경 설정

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 로컬 개발용 저장소 의존성 설치
python -m pip install -r tools/requirements.txt
python -m pip install -e .

# 소스 트리에서 컴파일러 실행
python tools/archcompiler.py tests/fixtures/no-advisory-success.yaml
```

개발 명령은 `arch-compiler/` 저장소 루트에서 실행하세요. 일부 테스트는 현재 작업 디렉터리 기준 상대 경로로 `tools/archcompiler.py` 를 호출하므로, 상위 디렉터리에서 실행하면 실패합니다.

---

## Agent Skills 설치

이 저장소는 설치 가능한 agent skills도 제공합니다.

### Codex

권장: 공식 Codex bootstrap installer를 사용하세요. 세 개의 skill을 설치하고, 전체 runtime 저장소를 canonical Codex 경로에 clone 또는 업데이트합니다.

```bash
# GitHub에서 한 줄로 설치
bash <(curl -fsSL https://raw.githubusercontent.com/inetgas/arch-compiler/main/scripts/install_codex_skills.sh)
```

먼저 저장소를 확인하고 싶다면:

```bash
git clone https://github.com/inetgas/arch-compiler.git
cd arch-compiler
./scripts/install_codex_skills.sh
```

설치 후 Codex를 재시작하세요.

이 installer가 하는 일:

- `using-arch-compiler`, `compiling-architecture`, `implementing-architecture` 를 공유 전역 agent skills 디렉터리 `~/.agents/skills/` 에 설치
- 전체 runtime 저장소를 `~/.codex/arch-compiler` 에 clone 또는 업데이트
- 설치된 skills와 runtime 저장소 레이아웃을 모두 검증

대안: 공개된 `skills.sh` / Vercel skills CLI로 수동 설치.

```bash
# 이 저장소가 게시한 skill 목록 보기
npx skills add inetgas/arch-compiler --list

# 세 개 모두를 공유 전역 agent skills 디렉터리(~/.agents/skills/)에 설치
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -g -y

# 설치된 skills가 사용하는 전체 runtime 저장소 clone
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler

# 세 skill이 전역으로 설치되었는지 확인
ls ~/.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

`-g` 를 생략하면 skills는 전역 Codex 디렉터리 대신 현재 프로젝트의 `./.agents/skills/` 에 설치됩니다.

```bash
# 프로젝트 로컬 설치 (현재 저장소와 함께 공유)
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -y

# 프로젝트 로컬 설치 확인
ls ./.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

중요: `skills` CLI는 skill 폴더만 설치합니다. 워크플로는 여전히 `~/.codex/arch-compiler` 같은 안정적인 로컬 경로에 전체 Architecture Compiler 저장소가 있어야 하며, 그래야 agent가 컴파일러, 패턴 레지스트리, 스키마, 설정, 어댑터에 접근할 수 있습니다.

전역 `skills.sh` 레이아웃 제거:

```bash
rm -rf ~/.agents/skills/using-arch-compiler
rm -rf ~/.agents/skills/compiling-architecture
rm -rf ~/.agents/skills/implementing-architecture
```

프로젝트 로컬 `skills.sh` 레이아웃 제거:

```bash
rm -rf ./.agents/skills/using-arch-compiler
rm -rf ./.agents/skills/compiling-architecture
rm -rf ./.agents/skills/implementing-architecture
```

원하면 runtime clone도 제거할 수 있습니다:

```bash
rm -rf ~/.codex/arch-compiler
```

대안: 저장소 자체의 Codex 네이티브 온보딩 안내를 사용.

이 fallback은 bootstrap installer와 다른 디스크 레이아웃을 사용합니다. `~/.agents/skills/` 아래에 복사된 세 개의 skill 디렉터리 대신, `~/.agents/skills/arch-compiler` 에 하나의 symlink pack entry를 둡니다.

Codex에는 이렇게 말하면 됩니다:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/inetgas/arch-compiler/refs/heads/main/.codex/INSTALL.md
```

또는 네이티브 설치 절차를 직접 따르세요:

```bash
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

이 symlink 레이아웃 확인:

```bash
ls -la ~/.agents/skills/arch-compiler
```

이 symlink 레이아웃 제거:

```bash
rm ~/.agents/skills/arch-compiler
```

원하면 runtime clone도 제거할 수 있습니다:

```bash
rm -rf ~/.codex/arch-compiler
```

중요: skill 파일만으로는 충분하지 않습니다. 워크플로는 전체 저장소가 안정적인 로컬 경로에 있어야 컴파일러, 패턴 레지스트리, 스키마, 어댑터에 접근할 수 있습니다. `/tmp/` 재클론이나 임시 경로 의존을 피하세요.

고급 fallback: 공개 저장소에서 세 개의 skill을 직접 설치.

이 fallback은 세 번째 디스크 레이아웃을 사용합니다. Codex 내장 GitHub installer가 `~/.codex/skills/` 아래에 세 개의 skill 디렉터리를 복사합니다.

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo inetgas/arch-compiler \
  --path skills/using-arch-compiler skills/compiling-architecture skills/implementing-architecture
```

Codex installer 참고: 이 저장소에서 여러 skill을 설치할 때는 모든 skill 경로를 하나의 `--path` 뒤에 넣으세요. `--path` 를 반복하지 마세요. 현재 installer는 마지막 반복 값만 유지합니다.

설치 후 세 디렉터리가 존재하는지 확인:

```bash
ls ~/.codex/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

이 레이아웃 제거:

```bash
rm -rf ~/.codex/skills/using-arch-compiler
rm -rf ~/.codex/skills/compiling-architecture
rm -rf ~/.codex/skills/implementing-architecture
```

### Skill 진입점

- `skills/using-arch-compiler` = 올바른 워크플로 선택, 아키텍처 변경 시 다시 컴파일 단계로 라우팅
- `skills/compiling-architecture` = 아키텍처 컴파일 및 최종 확정
- `skills/implementing-architecture` = 승인된 아키텍처 구현

### Agent 워크플로 Preflight

앱 저장소를 대상으로 아키텍처 컴파일이나 구현 워크플로를 시작하기 전에, 공유 preflight helper를 먼저 실행하세요. 이 규칙은 Codex, Claude Code, 기타 agent wrapper 중 무엇이 워크플로를 구동하든 동일합니다.

```bash
# 패키지를 CLI로 설치했다면:
archcompiler-preflight --app-repo /path/to/app-repo --mode compile

# 또는 안정적인 로컬 저장소 경로에서 helper를 직접 실행:
python3 ~/.codex/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
python3 ~/.claude/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
python3 ~/.hermes/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
```

승인된 `docs/architecture/` 폴더에서 코드를 쓰려는 경우에는 `--mode implement` 를 사용하세요.

### Claude Code

Claude Code는 Codex처럼 네이티브 skill discovery를 사용하지 않지만, 이 저장소는 `adapters/claude-code/commands/` 아래에 router entrypoint를 포함한 바로 복사 가능한 command adapter를 제공합니다.

세션 간에도 command가 컴파일러, 패턴, 스키마를 안정적으로 찾을 수 있도록 전체 저장소를 `~/.claude/arch-compiler` 와 같은 안정적인 로컬 경로에 두세요.

사용 가능한 command adapter:
- `using-arch-compiler.md`
- `compile-architecture.md`
- `implement-architecture.md`

### Hermes

Hermes는 `skills.sh` / GitHub 설치를 통해서도, 공유 외부 skill directory를 스캔하는 방식으로도 이 스킬들을 찾을 수 있습니다.

이미 Codex용으로 skills를 설치했다면, 가장 쉬운 Hermes 설정은 같은 skill 디렉터리를 재사용하는 것입니다.

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

Hermes에서 실행되는 skill이 컴파일러, 패턴, 스키마, 설정, 어댑터를 재클론 없이 찾을 수 있도록 전체 runtime 저장소를 `~/.hermes/arch-compiler` 같은 안정적인 로컬 경로에 두세요.

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.hermes/arch-compiler
```

공유 외부 디렉터리 대신 Hermes 네이티브 설치를 선호한다면, Hermes의 일반적인 `skills.sh` 또는 GitHub tap discovery 흐름을 따르고, 동일한 안정적 runtime clone을 `~/.hermes/arch-compiler` 에 유지하세요.

---

## Spec 형식

입력 spec은 `schemas/canonical-schema.yaml` 에 대해 검증되는 YAML 파일입니다. 예시:

```yaml
# ─── EXAMPLE SPEC ───
# 기본 구조를 보여주는 최소 spec 예시입니다.
# 요구사항이 명확해질수록 필드를 점진적으로 추가합니다.
# 더 완전한 예시와 엣지 케이스는 test-specs/ 를 참고하세요.
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

제공되지 않은 모든 필드는 `config/defaults.yaml` 에서 채워지고, 출력의 `assumptions` 섹션에 기록됩니다.

원래 선택될 패턴을 명시적으로 제외하고 싶다면(예: 현재 범위에 비해 너무 복잡한 경우), 최상위에 `disallowed-patterns` 목록을 추가하세요.

```yaml
disallowed-patterns:
  - ops-low-cost-observability
  - ops-slo-error-budgets
```

제외된 패턴은 `rejected-patterns.yaml` 에 `phase: phase_2_5_disallowed_patterns` 와 함께 나타납니다. 레지스트리에 없는 ID에 대해서는 warning이 출력됩니다.

엣지 케이스, 플랫폼 조합, 컴플라이언스 요구사항 등을 포함한 종합 예시는 `test-specs/` 를 참고하세요.

---

## 컴파일러 출력

### stdout

컴파일러는 항상 컴파일된 spec을 stdout으로 출력합니다. 즉, 모든 기본값이 적용된 병합 spec이며, verbose mode에서는 인라인 패턴 주석도 포함됩니다. 성공 시 종료 코드는 `0`, 검증 오류 시에는 `1` 입니다.

### `-o` 로 기록되는 파일

| File | Mode | Description |
|------|------|-------------|
| `compiled-spec.yaml` | always | assumptions를 포함한 전체 병합 spec. 다시 입력으로 사용할 수 있음 |
| `selected-patterns.yaml` | always | 일치 점수와 충족된 규칙이 포함된 선택된 패턴 |
| `rejected-patterns.yaml` | `-v` only | 거부 이유와 필터 단계가 포함된 거부된 패턴 |
| `compiled-spec-<timestamp>.yaml` | `-t` | 동일한 파일명에 UTC 타임스탬프를 붙인 버전 (예: `compiled-spec-2026-03-17T19:36:31Z.yaml`) |

### Verbose 모드 인라인 주석

`-v` 를 사용하면 컴파일된 spec의 각 필드에 어떤 패턴이 그것을 트리거했는지 주석이 붙습니다.

```yaml
constraints:
  platform: api  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
  cloud: aws     # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
nfr:
  availability:
    target: 0.999  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (14 more)
```

이렇게 하면 spec 값과 선택된 패턴 사이의 관계가 즉시 보입니다.

---

## 패턴 선택 방식

| Phase | What happens |
|-------|-------------|
| **1. Parse & Validate** | spec 로드, 스키마 검증, 의미 일관성 검사 |
| **2. Merge Defaults** | `config/defaults.yaml` 에서 누락 필드 채움, `assumptions` 에 기록 |
| **2.5 Disallowed filter** | `disallowed-patterns` 에 있는 패턴 제거, 알 수 없는 ID는 warning |
| **3.1 Constraint filter** | `supports_constraints` 규칙이 모두 spec과 맞는 패턴 유지 |
| **3.2 NFR filter** | `supports_nfr` 규칙이 모두 spec과 맞는 패턴 유지 |
| **3.3 Conflict resolution** | 충돌 패턴 제거. 승자 = 최고 match score, 이후 비용 의도 기준 최저 비용 |
| **3.4 Config merge** | 패턴 `defaultConfig` 를 `assumptions.patterns` 에 병합 |
| **3.5 Coding filter** | `--include-coding-patterns` 가 없으면 coding-level 패턴 제거 |
| **4. Cost feasibility** | 총 비용을 `cost.ceilings` 와 비교하고 advisory warning 출력 |
| **5. Output** | 컴파일된 spec을 stdout에 출력, `-o` 지정 시 아티팩트 파일 기록 |

### Coding patterns

기본적으로 `coding` 타입 패턴(GoF, DI, 테스트 전략, 개발 워크플로)은 제외됩니다. AI coding agent 시대에는 이들은 필요할 때 처리할 수 있기 때문입니다. 포함하려면 `--include-coding-patterns` 를 사용하세요.

---

## Progressive Refinement

컴파일러는 반복적이고 점진적인 사용을 전제로 설계되었습니다. 처음부터 완전한 spec가 필요하지 않습니다. 최소한으로 시작해서 이해가 깊어질수록 제약을 점진적으로 추가하세요.

### 한 가지 샘플 워크플로

```
Start minimal → compile → review assumptions → add constraints → recompile → ...
```

**Step 1: 기본만으로 시작**

```yaml
constraints:
  cloud: aws
  language: javascript
  platform: api
nfr:
  availability:
    target: 0.999
```

컴파일러를 실행하면 출력의 `assumptions` 섹션에 적용된 모든 기본값이 표시됩니다. 이는 컴파일러가 대신 내린 결정입니다. 컴파일러가 무엇을 가정했는지 이해하기 위해 이를 검토하세요.

**Step 2: 알게 되는 NFR 제약을 추가**

```yaml
nfr:
  availability:
    target: 0.999
  latency:           # ← 지연 시간 목표를 알게 되었을 때 추가
    p95Milliseconds: 50
    p99Milliseconds: 100
```

새로운 제약이 들어올 때마다 패턴 선택은 더 좁아집니다. 이전에는 선택되던 패턴이 거부될 수 있으며, 컴파일러는 `rejected-patterns.yaml` 파일(`-v` 모드)로 그 이유를 알려줍니다.

경우에 따라 spec 자체가 거부될 수도 있습니다. 예를 들어 매우 빡빡한 지연 시간이나 높은 가용성처럼 하드 NFR 목표를 어떤 패턴도 만족할 수 없는 경우, 컴파일러는 종료 코드 `1` 로 끝나고 무엇이 실패했는지 설명합니다. 이것은 유용한 신호입니다. 제약이 서로 모순되거나, 레지스트리에 아직 없는 패턴이 필요하다는 뜻입니다.

**Step 3: 기능은 명시적으로 opt-in**

```yaml
constraints:
  features:
    caching: true       # ← cache-aside 및 관련 패턴 트리거
```

feature flag는 `nfr` 아래가 아니라 `constraints.features` 아래에 있습니다. 이것은 성능 목표가 아니라 opt-in capability를 의미합니다.

패턴이 일치하면 컴파일러는 `warn_nfr` advisory를 출력할 수 있습니다. 이는 선택된 패턴이 현재 NFR 값에 비해 과도하다는 경고입니다. 예를 들어 throughput NFR 없이 caching을 활성화하면 다음과 같은 메시지가 나올 수 있습니다.

```
⚠️  cache-aside: peak read QPS is 5 req/s (<10 req/s). Caching overhead
    (infrastructure, invalidation, serialization) may outweigh benefit at this scale.
```

즉, 패턴은 선택되었지만 이 규모에서는 이득보다 오버헤드가 더 클 수 있다는 뜻입니다. 보다 구체적인 NFR 데이터를 추가하거나 feature flag를 재고하라는 신호입니다.

**Step 4: throughput 데이터를 추가해 warn_nfr advisory 해소**

caching(또는 다른 throughput-sensitive 패턴)을 활성화한 뒤 `warn_nfr` advisory가 보이면 실제 peak QPS를 추가하세요.

```yaml
nfr:
  throughput:
    peak_query_per_second_read: 20    # ← compiler가 caching benefit 재평가
    peak_query_per_second_write: 10
```

실제 throughput 숫자가 들어오면 컴파일러는 확정적인 판단을 내릴 수 있습니다. advisory가 사라져 caching이 정당화되거나, 더 구체적인 이유와 함께 advisory가 유지됩니다. 어느 쪽이든 근거 없이 선택된 패턴보다 훨씬 유용합니다.

**Step 5: 비용과 operating_model이 중요해질 때 명시**

```yaml
cost:
  intent:
    priority: optimize-tco   # default는 minimize-opex, 다른 옵션은 minimize-capex
  ceilings:
    monthly_operational_usd: 500
    one_time_setup_usd: 1000
operating_model:
  ops_team_size: 2                    # 전담 운영 엔지니어 수
  single_resource_monthly_ops_usd: 10000  # 엔지니어 1명당 완전부담 월 비용
  on_call: true                       # ops team cost에 1.5× multiplier 추가
  deploy_freq: daily                  # 운영 오버헤드에 영향 (daily = 1.0×, weekly = 0.8×, on-demand = 1.2×)
  amortization_months: 24             # TCO 계산을 위해 CapEx를 분산하는 기간
```

컴파일러는 세 개의 버킷에 대해 전체 cost feasibility analysis를 수행합니다.

- **Pattern OpEx** — 선택된 각 패턴의 추정 월간 인프라 비용 합
- **Ops team cost** — `ops_team_size × single_resource_monthly_ops_usd × on_call_multiplier × deploy_freq_multiplier` (on-call multiplier는 [Google SRE Book](https://sre.google/sre-book/being-on-call/)의 온콜 오버헤드, deploy frequency multiplier는 [DORA State of DevOps](https://dora.dev/research/)의 운영 부담 결과 반영)
- **CapEx (one-time)** — 선택된 패턴의 도입 및 초기 설정 비용

이 값들은 선언한 ceiling과 비교됩니다. 초과 시 활성화된 cost intent를 참조하는 `[high]` warning이 출력됩니다(예: `⚠️ [high] TCO exceeds ceiling by $26,760 (intent: optimize-tco)`). `operating_model` 이 없으면 컴파일러는 기본값으로 `ops_team_size: 0` 을 사용하므로 ops team cost는 0이 됩니다. 이는 전담 엔지니어가 있는 팀에서 실제 TCO를 크게 과소평가할 수 있습니다.

### 왜 이 방식이 동작하는가

`compiled-spec.yaml` 은 유효한 입력 spec입니다. 여기에 다시 컴파일러를 실행하면 같은 출력이 나옵니다. `assumptions` 섹션은 유지되고, 실제로 비어 있는 필드만 다시 채워집니다. 즉:

- 컴파일된 spec을 수정해서 재컴파일할 수 있고, 변경 사항은 존중됩니다
- 출력은 항상 모든 결정을 담은 완전하고 독립적인 기록입니다
- 어떤 단계에서도 출력은 의미가 있으며, 가치를 얻기 위해 “완전한” spec가 필요하지 않습니다

### 각 단계에서 무엇이 바뀌는가

이 표는 데모 영상 [[Architecture Compiler](https://www.youtube.com/watch?v=QPqNyozTArY)] 과 같은 진행을 따릅니다.

| Step | You add | What the compiler does |
|------|---------|----------------------|
| 1 | Minimal spec (cloud, language, platform, availability) | 기본 패턴 선택, 누락 필드를 `assumptions` 에 채움 |
| 2 | `-v` flag | 각 spec 필드에 어떤 패턴이 트리거되었는지 주석 추가, `rejected-patterns.yaml` 기록 |
| 3 | Latency NFR (`p95`, `p99`) | 목표를 만족하지 못하는 패턴 제거, 조건에 따라 spec 전체가 reject될 수 있음 |
| 4 | `features.caching: true` | cache-aside 및 관련 패턴 활성화, 현재 QPS가 낮으면 `warn_nfr` 출력 |
| 5 | Throughput NFR (`peak_query_per_second_read/write`) | `warn_nfr` advisory 해소, 실제 부하 데이터에 따라 패턴 재평가 |
| 6 | Cost intent (`optimize-tco`, `minimize-opex`, `minimize-capex`) | cost feasibility check 실행, ceiling 초과 시 `[high]` warning 출력 |

---

## 프로젝트 구조

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

## 테스트 실행

```bash
# 전체 테스트 실행
python -m pytest tests/ -q

# 상세 출력으로 테스트 실행
python -m pytest tests/ -v

# 특정 테스트 파일 실행
python -m pytest tests/test_compiler_integration.py -v
```

테스트는 컴파일러 파이프라인 end-to-end, 패턴 스키마 검증, 충돌 대칭성, NFR/제약 로직, 비용 타당성 등을 포괄합니다. 전체 목록은 `docs/test-inventory.md` 를 참고하세요.

---

## Skills 설치

이 저장소는 재사용 가능한 agent skills 세 개를 게시합니다:

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

Codex 사용자는 GitHub repo path에서 직접 설치할 수 있습니다:

```bash
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/using-arch-compiler
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/compiling-architecture
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/implementing-architecture
```

Claude Code 사용자는 `adapters/claude-code/commands/` 의 adapter를 `.claude/commands/` 로 복사해서 router command와 함께 사용할 수 있습니다.

설치 상세와 cross-agent 사용 메모는 `skills/README.md` 를 참고하세요.

---

## 감사 도구

```bash
# Pattern metadata 품질 감사 (설명, 비용, NFR 규칙)
python tools/audit_patterns.py

# NFR/constraint 규칙 경로 감사 (낡은 JSON pointer 참조 탐지)
python tools/audit_nfr_logic.py

# 충돌 대칭성 감사 (A가 B와 충돌하면 B도 A와 충돌해야 함)
python tools/audit_asymmetric_conflicts.py
```

각 도구의 전체 문서는 `docs/tools.md` 를 참고하세요.

---

## 패턴 추가 또는 수정

1. 새 필드가 필요하면 `schemas/pattern-schema.yaml` 업데이트
2. 새 spec 필드가 필요하면 `schemas/canonical-schema.yaml` 업데이트
3. `patterns/` 아래 패턴 파일 추가 또는 수정
4. `python tools/audit_patterns.py` 실행해 품질 점검
5. `python -m pytest tests/ -q` 실행해 깨진 것이 없는지 확인

핵심 규칙:
- Pattern ID는 파일명과 일치해야 합니다 (예: `cache-aside.json` → `id: "cache-aside"`)
- `supports_constraints` 와 `supports_nfr` 규칙은 AND 로직을 사용합니다. 모두 일치해야 패턴이 선택됩니다
- Conflict 선언은 **양방향** 이어야 합니다. A가 B와 충돌하면 B도 A를 선언해야 합니다
- 형제 variant 패턴(예: `arch-serverless--aws`, `arch-serverless--azure`)은 각각 모든 형제와 충돌해야 합니다
- 컴파일러에서 pattern ID 문자열 매칭을 사용하지 마세요. 모든 로직은 pattern metadata에 인코딩해야 합니다
