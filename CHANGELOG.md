# CHANGELOG - v1.0.0 (2026-04-02)

## 🚀 Initial Release: AI Harness Engineering at the Architecture Layer

This release establishes the first **Architecture-Level AI Harness**. Moving beyond simple agent operation (context and tools), this system encodes architectural intelligence into a deterministic framework, ensuring AI agents make decisions *within your constraints*, not around them.

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

### 🤖 AI-Native Governance (The Domain Skills)
The release introduces the two "Drivers" for the AI CPU:
- **`compiling-architecture`:** Guides agents through requirements capture and deterministic pattern selection.
- **`implementing-architecture`:** Ensures implementation strictly follows the approved architectural contract.
- **Strict Staging:** A `patterns-staging/` workflow ensures no unvetted architectural logic enters the core registry.
- **Immutable Schemas:** Protection of core spec and pattern contracts to prevent agentic drift.

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
