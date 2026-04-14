# Changelog

## Unreleased

- Improved brownfield routing across the three workflow skills:
  - `using-arch-compiler` now routes existing-prototype cases explicitly between architecture compilation/re-approval and implementation/refactoring
  - `compiling-architecture` now treats prototype/codebase reality as input to spec compilation and re-approval, not as architectural authority
  - `implementing-architecture` now explicitly supports refactoring an existing prototype into compliance with an approved architecture, while routing any request to replace approved choices back to architecture compilation
- Added OLAP lakehouse pattern family and validation coverage:
  - added `data-olap-lakehouse` meta-policy plus provider variants for `aws`, `azure`, `gcp`, `self-hosted`, `databricks`, and `snowflake`
  - added supporting schema and capability-vocabulary updates, including `databricks` as a canonical SaaS provider and explicit lakehouse-oriented capabilities
  - added regression specs covering AWS-native, self-hosted, Databricks, Snowflake, and warehouse-preferred selection cases
  - normalized OLAP conflict semantics so lakehouse and warehouse variants conflict consistently as alternative primary analytical architectures
- Tightened pattern authoring and OLAP gating semantics:
  - removed orthogonality-breaking `saas-providers == []` requirements from cloud-native and self-hosted lakehouse variants
  - aligned the Snowflake warehouse control test with an explicitly warehouse-biased NFR envelope instead of relying on an under-specified SaaS-provider-only spec
  - recorded pattern-authoring rules for future work: avoid exact opposite `supports_nfr`/`warn_nfr` pairs, avoid fake `requires_*` null checks when defaults already populate fields, and only gate on `saas-providers` when the provider is actually the selector
- Improved cross-agent skill distribution and installation:
  - added `scripts/install_codex_skills.sh` as an official Codex bootstrap installer that installs the three skills, clones or updates the runtime repo, and verifies both
  - reorganized Codex install docs around the bootstrap path while clearly separating the `skills.sh`, native symlink, and direct GitHub-installer fallback layouts
  - added matching verify/uninstall guidance for each documented Codex install layout
  - added Hermes-specific `SKILL.md` metadata (`version`, `metadata.hermes.tags`, `category`, `requires_toolsets`) for the three workflow skills
  - documented Hermes usage via `skills.external_dirs`, plus stable runtime-path guidance for `~/.hermes/arch-compiler`
- Clarified Codex skill installation for direct GitHub installs:
  - documented the working single-`--path` multi-skill install command for the three Architecture Compiler skills
  - warned that repeating `--path` keeps only the last value in the current installer
  - added post-install verification steps in the English and Simplified Chinese human-facing docs
- Added Vertex AI provider support and related registry hardening:
  - added `patterns/genai-inference--vertex-ai.json` as a GCP-managed GenAI inference provider variant
  - aligned the generic `genai-inference` provider vocabulary and reciprocal provider conflicts
  - updated `schemas/capability-vocabulary.yaml` for GenAI and cloud-auth capabilities, and normalized older `quota-enforcement` aliases to canonical `rate-limiting`
  - added Vertex AI integration specs under `test-specs/` for positive GCP selection and non-GCP fallback behavior
- Tightened pattern-authoring guidance:
  - `compiling-architecture` now requires checking `schemas/capability-vocabulary.yaml` during new pattern authoring
  - agent guidance now makes staging-first the default for new pattern authoring; “author a new pattern” does not by itself authorize placing it directly into `patterns/`
- Removed exact live counts from README-family docs so pattern, skill, and test-spec growth no longer forces routine documentation churn

## [1.0.1] - 2026-04-09

- Added a shared workflow preflight helper:
  - `tools/archcompiler_preflight.py`
  - installed CLI entrypoint: `archcompiler-preflight`
  - test coverage in `tests/test_archcompiler_preflight.py`
- Hardened architecture workflow skills and agent docs:
  - front-loaded stable-path and app-repo setup checks in `compiling-architecture`
  - explicit app-repo git initialization and initial-commit verification before architecture work
  - explicit approved-architecture commit verification during finalisation
  - stronger implementation-plan enforcement with Pattern Coverage Matrix, artifact-level coverage, runtime-semantics checks, post-implementation smoke testing, and post-implementation adversarial review
  - clarified that `config/` is part of the read-only agent boundary alongside `tools/`, `schemas/`, and `patterns/`
- Aligned Claude Code adapters and install docs with the stable-path repo model instead of implicit `@skills/...` resolution
- Added Simplified Chinese translations for the main public documentation under `docs/i18n/`:
  - `docs/i18n/README.zh-CN.md`
  - `docs/i18n/skills.README.zh-CN.md`
- Added language-switch links to `README.md` and `skills/README.md`
- Documented that English remains the canonical source of truth when translations differ
- Updated packaging metadata in `pyproject.toml` to remove setuptools license deprecation warnings

## [1.0.0] - 2026-04-02

### 🚀 Initial Release: An Architecture-Level AI Harness

This release establishes Architecture Compiler as an architecture-level AI harness: a deterministic compiler, a curated pattern registry, and three workflow skills that let humans and agents move from requirements to approved architecture and implementation with an explicit contract.

### 🧠 The Architecture Harness Philosophy
- **The Registry is the Trajectory:** Phil Schmid's thesis—"competitive advantage is the trajectories your harness captures"—applied to architecture. Our 180+ pattern registry is the accumulated trajectory of architectural intelligence that future agents inherit.
- **Deterministic Kernel:** An architecture compiler with **zero LLM inference** at its core. It serves as the kernel of the architecture harness, enforcing policy through hard NFR validation and include-based filtering.
- **Defendable AI Decisions:** Moves away from "vibe coding" to reproducible, auditable architectural artifacts (`architecture.yaml`, `selected-patterns.yaml`) that humans and agents can defend.

### ✨ Key Capabilities
- **Progressive Refinement:** An iterative workflow that translates requirements into machine-readable canonical specifications. (Requirements capture is pluggable — Superpowers, Gstack, Compound Engineering, or custom skill.)
- **Multi-Phase Filtering:** Hard validation against targets for Availability, Latency, Throughput, and Compliance (GDPR, HIPAA, etc.).
- **Cost Intent:** Three explicit modes — `optimize-tco` (balance CapEx/OpEx), `minimize-opex` (monthly costs), `minimize-capex` (one-time setup).
- **Conflict Resolution Engine:** Automated resolution based on match scores and declared cost intent.
- **Full TCO Analysis:** Cost feasibility checking across Pattern OpEx, one-time CapEx, and operational labor costs.
- **Explainable Infrastructure:** Verbose mode (`-v`) provides inline annotations for every spec field, turning the repo into a "living architectural contract."

### 🤖 AI-Native Governance (The Workflow Skills)
The release introduces three workflow skills:
- **`using-arch-compiler`:** Routes work to the correct workflow and sends it back for recompilation when architectural decisions change.
- **`compiling-architecture`:** Guides agents through requirements capture, deterministic pattern selection, approval, and re-approval.
- **`implementing-architecture`:** Ensures implementation strictly follows the approved architectural contract.
- **Immutable Schemas and Registry Boundaries:** Protection of core spec and pattern contracts to prevent agentic drift.

### 📦 The Pattern Registry (180+ Patterns)

A comprehensive knowledge base covering:

- **Foundation:** `arch-*`, `platform-*`, `hosting-*`, `iac-*`, `onprem-*`
- **Secrets, Security & Identity:** `secrets-*`, `sec-*`, `policy-*`, `idp-*`, `pki-*`
- **Compliance:** `compliance-*`
- **Storage:** `db-*`, `data-*`
- **Caching:** `cache-*`, `caching-*`, `write-*`
- **Communication:** `api-*`, `sync-*`, `async-*`, `queue-*`
- **Reliability:** `resilience-*`, `consistency-*`, `distributed-*`, `exactly-*`, `saga-*`
- **Application:** `cqrs-*`, `event-*`, `crud-*`, `multi-*`, `tenancy-*`, `batch-*`, `genai-*`
- **Front-end:** `ui-*`
- **Observability:** `obs-*`, `ops-*`, `finops-*`
- **Delivery:** `deploy-*`, `release-*`, `build-*`, `dev-*`, `test-*`, `gof-*`
- **Governance:** `gov-*`

### 🛠️ Developer & Audit Tools
- **`archcompiler.py`:** The core 3,700+ line compilation engine.
- **Audit Suite:** Tools for metadata quality, NFR logic validation, and bidirectional conflict symmetry.
- **Test Infrastructure:** 110+ integration specs covering thousands of unique architectural combinations.
