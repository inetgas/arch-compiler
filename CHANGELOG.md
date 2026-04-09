# Changelog

## Unreleased

- Clarified Codex skill installation for direct GitHub installs:
  - documented the working single-`--path` multi-skill install command for the three Architecture Compiler skills
  - warned that repeating `--path` keeps only the last value in the current installer
  - added post-install verification steps in the English and Simplified Chinese human-facing docs

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
