# Architecture Compiler: An Architecture-Level AI Harness

ArchCompiler compiles constraints and NFRs into explicit, reviewable architectural decisions with clear trade-offs and cost impact.

It is an architecture-level AI harness built from three parts: a deterministic compiler, a curated pattern registry, and three workflow skills for agents. Together they turn requirements into compiled architecture, route work through approval and re-approval when architectural decisions change, and guide implementation against an explicit architectural contract.

The compiler itself is intentionally simple: no LLM inference, no hidden defaults, and no black-box selection logic. The architectural intelligence lives in the registry and in the workflow discipline carried by:
- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

[![CI - Test Suite](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml/badge.svg)](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Patterns](https://img.shields.io/badge/Patterns-180+-success)
![Documentation](https://img.shields.io/badge/Documentation-Agent--Skills-orange)

> **Tags:** `architecture-as-code`, `design-patterns`, `harness-engineering`, `agent-harness`, `deterministic-compiler`, `cloud-native`, `pattern-registry`, `agentic-engineering`, `on-the-loop`, `nfr-enforcement`

## Core Philosophy

- **Patterns are the knowledge base.** All architectural logic lives in the pattern files under `patterns/`. The compiler is deliberately simple.
- **Include-based filtering.** Patterns declare what spec conditions they support via `supports_constraints` and `supports_nfr` rules. A pattern is selected when all its rules match the spec.
- **Schema-first.** `schemas/canonical-schema.yaml` defines the spec contract; `schemas/pattern-schema.yaml` defines the pattern contract. Both are the source of truth.

---

## Quick Start

If `python` is unavailable on your system, replace it with `python3` in the commands below.

```bash
# Install pipx if needed (recommended for Python CLI apps)
brew install pipx

# Install the CLI from the current repo
pipx install .

# Compile a real example spec (output to stdout)
archcompiler tests/fixtures/no-advisory-success.yaml

# Compile and write artifacts to a directory
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/

# Verbose mode — inline pattern comments + rejected-patterns file
archcompiler tests/fixtures/no-advisory-success.yaml -v
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v

# Add UTC timestamp to output filenames
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v -t
```

### Development Setup

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install repo dependencies for local development
python -m pip install -r tools/requirements.txt
python -m pip install -e .

# Run the compiler from the source tree
python tools/archcompiler.py tests/fixtures/no-advisory-success.yaml
```

Run development commands from the `arch-compiler/` repo root. Some tests invoke `tools/archcompiler.py` via a cwd-relative path and will fail if you run them from a parent directory.

---

## Install The Agent Skills

This repo also ships installable agent skills.

### Codex

Tell Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/inetgas/arch-compiler/refs/heads/main/.codex/INSTALL.md
```

Or follow the native install steps directly:

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

Restart Codex after installing.

### Skill Entry Points

- `skills/using-arch-compiler` = choose the correct workflow and route back to compilation if architecture changes
- `skills/compiling-architecture` = compile and finalise architecture
- `skills/implementing-architecture` = implement an approved architecture

### Claude Code

Claude Code does not use Codex native skill discovery, but this repo includes ready-to-copy command adapters in `adapters/claude-code/commands/`, including a router entrypoint.

Available command adapters:
- `using-arch-compiler.md`
- `compile-architecture.md`
- `implement-architecture.md`

---

## Spec Format

The input spec is a YAML file validated against `schemas/canonical-schema.yaml`. One example:

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

All fields not provided are filled from `config/defaults.yaml` and recorded in the `assumptions` section of the output.

To explicitly exclude patterns that would otherwise be selected (e.g. too complex for scope), add a top-level `disallowed-patterns` list:

```yaml
disallowed-patterns:
  - ops-low-cost-observability
  - ops-slo-error-budgets
```

Excluded patterns appear in `rejected-patterns.yaml` with `phase: phase_2_5_disallowed_patterns`. A warning is emitted for any ID not found in the registry.

See `test-specs/` for a comprehensive set of example specs covering edge cases, platform combinations, compliance requirements, and more.

---

## Compiler Output

### stdout

The compiler always prints the compiled spec to stdout — the merged spec with all defaults applied and inline pattern comments (in verbose mode). Exit code `0` on success, `1` on validation errors.

### Files written with `-o`

| File | Mode | Description |
|------|------|-------------|
| `compiled-spec.yaml` | always | Full merged spec with assumptions; can be re-fed as input |
| `selected-patterns.yaml` | always | Selected patterns with match scores and honored rules |
| `rejected-patterns.yaml` | `-v` only | Rejected patterns with reason and filter phase |
| `compiled-spec-<timestamp>.yaml` | `-t` | Same files with UTC timestamp appendix (e.g. `compiled-spec-2026-03-17T19:36:31Z.yaml`) |

### Verbose mode inline comments

With `-v`, the compiled spec annotates each field with the patterns it triggered:

```yaml
constraints:
  platform: api  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
  cloud: aws     # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
nfr:
  availability:
    target: 0.999  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (14 more)
```

This makes the relationship between your spec values and the selected patterns immediately visible.

---

## How Pattern Selection Works

| Phase | What happens |
|-------|-------------|
| **1. Parse & Validate** | Load spec, validate schema, check semantic consistency |
| **2. Merge Defaults** | Fill missing fields from `config/defaults.yaml`; record in `assumptions` |
| **2.5 Disallowed filter** | Remove any pattern listed in `disallowed-patterns`; warn on unknown IDs |
| **3.1 Constraint filter** | Keep patterns whose `supports_constraints` rules all match the spec |
| **3.2 NFR filter** | Keep patterns whose `supports_nfr` rules all match the spec |
| **3.3 Conflict resolution** | Remove conflicting patterns; winner = highest match score, then lowest cost based on intent |
| **3.4 Config merge** | Merge pattern `defaultConfig` into `assumptions.patterns` |
| **3.5 Coding filter** | Drop coding-level patterns unless `--include-coding-patterns` is set |
| **4. Cost feasibility** | Check total cost against `cost.ceilings`; emit advisory warnings |
| **5. Output** | Emit compiled spec to stdout; write artifact files if `-o` specified |

### Coding patterns

By default patterns with type `coding` (GoF, DI, test strategies, dev workflows) are excluded — in the AI coding agent era these can be handled on demand. Use `--include-coding-patterns` to include them.

---

## Progressive Refinement

The compiler is designed for iterative, incremental use. You don't need a complete spec upfront — start minimal and add constraints progressively as your understanding grows.

### One sample workflow

```
Start minimal → compile → review assumptions → add constraints → recompile → ...
```

**Step 1: Start with just the basics**

```yaml
constraints:
  cloud: aws
  language: javascript
  platform: api
nfr:
  availability:
    target: 0.999
```

Run the compiler. The `assumptions` section in the output shows every default that was applied — these are decisions the compiler made on your behalf. Review them to understand what the compiler assumed.

**Step 2: Add NFR constraints as you discover them**

```yaml
nfr:
  availability:
    target: 0.999
  latency:           # ← add this when you know your latency target
    p95Milliseconds: 50
    p99Milliseconds: 100
```

Each new constraint narrows the pattern selection. Some patterns will be rejected that weren't before — the compiler tells you why via the `rejected-patterns.yaml` file (in `-v` mode).

In some cases the spec itself may be rejected: if a hard NFR target (e.g. a very tight latency or high availability requirement) cannot be satisfied by any available pattern, the compiler exits with code `1` and explains what failed. This is useful signal — it means your constraints are either contradictory or require a pattern that doesn't yet exist in the registry.

**Step 3: Opt in to features explicitly**

```yaml
constraints:
  features:
    caching: true       # ← triggers cache-aside and related patterns
```

Feature flags live under `constraints.features`, not under `nfr`. They represent opt-in capabilities, not performance targets.

When a pattern is matched, the compiler may emit `warn_nfr` advisories — warnings that a selected pattern is under-utilized given your current NFR values. For example, enabling caching without a throughput NFR may produce:

```
⚠️  cache-aside: peak read QPS is 5 req/s (<10 req/s). Caching overhead
    (infrastructure, invalidation, serialization) may outweigh benefit at this scale.
```

This is the compiler telling you the pattern is selected but unlikely to pay off — a prompt to either provide more specific NFR data or reconsider the feature flag.

**Step 4: Provide throughput data to resolve warn_nfr advisories**

If you see a `warn_nfr` advisory after enabling caching (or other throughput-sensitive patterns), add your actual peak QPS:

```yaml
nfr:
  throughput:
    peak_query_per_second_read: 20    # ← compiler re-evaluates caching benefit
    peak_query_per_second_write: 10
```

With real throughput numbers the compiler can make a definitive call — either the advisory disappears (caching is justified) or it persists with more specific reasoning. Either outcome is more useful than a pattern selected in the dark.

**Step 5: Explicitly specify cost and operating_model when you care about it**

```yaml
cost:
  intent:
    priority: optimize-tco   # default is minimize-opex, another option is minimize-capex
  ceilings:
    monthly_operational_usd: 500
    one_time_setup_usd: 1000
operating_model:
  ops_team_size: 2                    # number of dedicated ops engineers
  single_resource_monthly_ops_usd: 10000  # fully-loaded monthly cost per engineer
  on_call: true                       # adds 1.5× multiplier to ops team cost
  deploy_freq: daily                  # affects ops overhead (daily = 1.0×, weekly = 0.8×, on-demand = 1.2×)
  amortization_months: 24             # period over which CapEx is spread for TCO
```

The compiler runs a full cost feasibility analysis across three buckets:

- **Pattern OpEx** — sum of each selected pattern's estimated monthly infrastructure cost
- **Ops team cost** — `ops_team_size × single_resource_monthly_ops_usd × on_call_multiplier × deploy_freq_multiplier` (on-call multiplier reflects SRE on-call overhead from [Google SRE Book](https://sre.google/sre-book/being-on-call/); deploy frequency multiplier reflects operational burden findings from [DORA State of DevOps](https://dora.dev/research/))
- **CapEx (one-time)** — adoption and setup costs for selected patterns

These are checked against your declared ceilings. Breaches emit `[high]` warnings referencing the active cost intent (e.g. `⚠️ [high] TCO exceeds ceiling by $26,760 (intent: optimize-tco)`). Without an `operating_model`, the compiler defaults to `ops_team_size: 0` — meaning ops team cost is zero, which can significantly understate real TCO for teams with dedicated engineers.

### Why this works

`compiled-spec.yaml` is a valid input spec. Running the compiler on it again produces the same output — the `assumptions` section is preserved and only genuinely missing fields are backfilled. This means:

- You can edit a compiled spec and recompile — your changes are respected
- The output is always a complete, self-contained record of every decision
- At any stage the output is meaningful; you never need a "complete" spec to get value

### What changes at each stage

This table follows the same progression as the demo video [[Architecture Compiler](https://youtu.be/1uh2pSOO1WA)]:

| Step | You add | What the compiler does |
|------|---------|----------------------|
| 1 | Minimal spec (cloud, language, platform, availability) | Selects baseline patterns; fills all missing fields into `assumptions` |
| 2 | `-v` flag | Annotates every spec field with the patterns it triggered; writes `rejected-patterns.yaml` |
| 3 | Latency NFR (`p95`, `p99`) | Rejects patterns that can't meet the target; spec may be rejected entirely if no pattern qualifies |
| 4 | `features.caching: true` | Activates cache-aside and related patterns; emits `warn_nfr` if current QPS is too low to justify the overhead |
| 5 | Throughput NFR (`peak_query_per_second_read/write`) | Resolves `warn_nfr` advisories; patterns re-evaluated against real load data |
| 6 | Cost intent (`optimize-tco`, `minimize-opex`, `minimize-capex`) | Triggers cost feasibility check; emits `[high]` warnings if ceilings are exceeded |

---

## Project Structure

```
.
├── README.md                   This file
├── README-AGENTS.md            Repo guide for AI agents
├── LICENSE                     MIT License
├── CHANGELOG.md                Repo change log
├── CODE_OF_CONDUCT.md          Repo code of conduct
├── CONTRIBUTING.md             Repo guide for contributions
├── pyproject.toml              Project metadata, dependencies, and tool config
├── .github/                    GitHub configuration (CI/CD workflows)
├── patterns/                   180 pattern JSON files — the knowledge base
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
├── test-specs/                 116 named integration specs
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
└── skills/                     Agent skills (AI use only)
    ├── compiling-architecture/SKILL.md     Skill for compiling a spec into pattern selection
    └── implementing-architecture/SKILL.md  Skill for implementing from approved architecture
```

---

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -q

# Verbose test output
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_compiler_integration.py -v
```

Tests cover the compiler pipeline end-to-end, pattern schema validation, conflict symmetry, NFR/constraint logic, cost feasibility, and more. See `docs/test-inventory.md` for the full list.

---

## Installing the Skills

This repo also publishes two reusable agent skills:

- `compiling-architecture`
- `implementing-architecture`

Codex users can install them directly from the GitHub repo path:

```bash
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/compiling-architecture
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/implementing-architecture
```

Claude Code users can use the included adapters in `adapters/claude-code/commands/` by copying them into `.claude/commands/`.

See `skills/README.md` for install details and cross-agent usage notes.

---

## Audit Tools

```bash
# Audit pattern metadata quality (descriptions, costs, NFR rules)
python tools/audit_patterns.py

# Audit NFR/constraint rule paths (catch stale JSON pointer references)
python tools/audit_nfr_logic.py

# Audit conflict symmetry (if A conflicts B, B must conflict A)
python tools/audit_asymmetric_conflicts.py
```

See `docs/tools.md` for full documentation of each tool.

---

## Adding or Editing Patterns

1. Update `schemas/pattern-schema.yaml` if a new field is needed
2. Update `schemas/canonical-schema.yaml` if a new spec field is needed
3. Add or edit pattern files in `patterns/`
4. Run `python tools/audit_patterns.py` to check quality
5. Run `python -m pytest tests/ -q` to verify nothing is broken

Key rules:
- Pattern IDs must match their filename (e.g. `cache-aside.json` → `id: "cache-aside"`)
- `supports_constraints` and `supports_nfr` rules use AND logic — all must match for the pattern to be selected
- Conflict declarations must be **bidirectional** — if A conflicts with B, B must also declare A
- Sibling variant patterns (e.g. `arch-serverless--aws`, `arch-serverless--azure`) must each conflict with all their siblings
- Never use pattern ID string matching in the compiler — encode all logic in pattern metadata
