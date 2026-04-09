# Pattern Schemas

Schema definitions for design patterns and canonical specifications.

## Files

| File | Purpose |
|------|---------|
| `pattern-schema.yaml` | JSON Schema for design pattern JSON files |
| `canonical-schema.yaml` | JSON Schema for input specification files |
| `capability-vocabulary.yaml` | Canonical names, aliases, and categories for `provides`/`requires` capability strings |

---

## Pattern Schema (`pattern-schema.yaml`)

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique pattern identifier (e.g. `cache-aside--redis`) |
| `version` | string | Pattern version |
| `title` | string | Human-readable name |
| `description` | string | Purpose and behaviour |
| `types` | array | Categories — see Types below |
| `cost` | object | Cost metadata — see Cost below |
| `provides` | array | Capabilities this pattern provides |
| `requires` | array | Capabilities this pattern requires |
| `tags` | array | Free-form tags |
| `supports_nfr` | array | NFR selection rules — see Rule Arrays below |
| `supports_constraints` | array | Constraint selection rules — see Rule Arrays below |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `generic` | boolean | Marks this as a generic base pattern with specific variants |
| `requires_nfr` | array | Hard NFR validators — spec must satisfy these when pattern is selected |
| `requires_constraints` | array | Hard constraint validators — spec must satisfy these when pattern is selected |
| `warn_nfr` | array | Advisory NFR rules — emits a warning on failure but still selects pattern |
| `warn_constraints` | array | Advisory constraint rules — emits a warning on failure but still selects pattern |
| `conflicts.incompatibleWithDesignPatterns` | array | Pattern IDs this pattern conflicts with (must be bidirectional) |
| `availability.tier` | enum | `open`, `pro`, or `enterprise` |
| `defaultConfig` | object | Default configuration values for this pattern |
| `configSchema` | object | JSON Schema validating user overrides in `spec.patterns.<id>` |

---

### Rule Arrays

All six rule-array fields (`supports_nfr`, `supports_constraints`, `requires_nfr`, `requires_constraints`, `warn_nfr`, `warn_constraints`) share the same item structure:

```json
{
  "path": "/nfr/availability/target",
  "op": ">=",
  "value": 0.99,
  "reason": "Pattern requires high availability."
}
```

**`path`** — JSON Pointer into the spec (must start with `/`).

**Supported operators:** `==`, `!=`, `in`, `not-in`, `contains-any`, `>`, `<`, `>=`, `<=`

`warn_nfr` and `warn_constraints` also accept an optional `message` field. Use `{actual}` to interpolate the spec value:

```json
{
  "path": "/nfr/throughput/peak_jobs_per_hour",
  "op": "<=",
  "value": 10000,
  "reason": "Pattern is not optimised for very high job throughput.",
  "message": "Peak throughput {actual} jobs/hr may exceed this pattern's capacity."
}
```

#### Semantics of each field

| Field | Evaluated | Effect on failure |
|-------|-----------|-------------------|
| `supports_constraints` | Phase 3.1 — before selection | Pattern silently excluded |
| `supports_nfr` | Phase 3.2 — before selection | Pattern silently excluded |
| `requires_constraints` | Phase 3.3.5 — after selection | Compilation error (exit 1) |
| `requires_nfr` | Phase 3.3.5 — after selection | Compilation error (exit 1) |
| `warn_constraints` | Phase 4 — after cost check | Advisory warning printed |
| `warn_nfr` | Phase 4 — after cost check | Advisory warning printed |

A pattern with an **empty `supports_nfr`** is also rejected (Phase 3.2) when the spec has any NFR requirements — it has declared no NFR compatibility.

---

### Gating Patterns

A **gating pattern** has all four fields non-empty: `supports_nfr`, `requires_nfr`, `supports_constraints`, `requires_constraints`. These patterns:

1. Are activated by a specific spec feature (via `supports_constraints`)
2. Always pass Phase 3.2 when active (via a permissive `supports_nfr` rule)
3. Hard-fail compilation if spec NFR targets are incompatible (via `requires_nfr`)
4. Hard-fail compilation if spec constraints are incompatible (via `requires_constraints`)

Example: `genai-inference` activates on `constraints.features.ai_inference == true`. It keeps one permissive rule in `supports_nfr` (so Phase 3.2 passes) and enforces `nfr.latency.p95Milliseconds >= 500` in `requires_nfr` (GenAI inference cannot physically meet sub-500ms p95 latency — a spec claiming otherwise gets a hard error instead of silent exclusion).

---

### Types

Valid values for the `types` array. Patterns can have multiple types. Counts below reflect a snapshot of the registry and may change as patterns are added or removed.

| Value | Snapshot Count | Meaning |
|-------|----------------|---------|
| `design` | 121 | Architectural design patterns |
| `ops` | 133 | Operations / SRE patterns |
| `build` | 115 | Build and delivery patterns |
| `cost` | 27 | Cost optimisation patterns |
| `deploy` | 27 | Deployment strategy patterns |
| `data` | 21 | Data architecture patterns |
| `platform` | 19 | Platform / infrastructure patterns |
| `coding` | 15 | Code-level implementation patterns (GoF, DI, test strategies) |
| `test` | 11 | Testing strategy patterns |
| `security` | 5 | Security / compliance patterns (`sec` is also accepted) |

Patterns with type `coding` are excluded by default. Pass `--include-coding-patterns` to the compiler to include them.

#### Patterns by type

**`cost` (27)**
`arch-cold-archive-tiering`, `arch-egress-minimization`, `arch-multi-tenant-consolidation`, `arch-serverless-pay-per-use`, `arch-serverless-pay-per-use--aws-lambda`, `arch-serverless-pay-per-use--azure-functions`, `arch-serverless-pay-per-use--gcp-cloud-functions`, `arch-spot-preemptible-batch`, `db-managed-postgres`, `db-managed-postgres--render`, `db-managed-postgres--supabase`, `finops-budget-guardrails`, `finops-cost-allocation-tags`, `hosting-managed-paas`, `hosting-managed-paas--aws`, `hosting-managed-paas--azure`, `hosting-managed-paas--digitalocean-app-platform`, `hosting-managed-paas--flyio`, `hosting-managed-paas--gcp`, `hosting-managed-paas--railway`, `hosting-managed-paas--render`, `hosting-managed-paas--vercel`, `hosting-static-frontend`, `hosting-static-frontend--cloudflare-pages`, `hosting-static-frontend--netlify`, `hosting-static-frontend--vercel`, `ops-low-cost-observability`

**`data` (21)**
`compliance-gdpr-right-to-be-forgotten`, `db-graph--generic`, `db-graph--neo4j-aura`, `db-graph--neptune`, `db-key-value--generic`, `db-key-value--redis-cloud`, `db-managed-mysql--planetscale`, `db-managed-postgres--neon`, `db-managed-postgres--railway`, `db-nosql-document--dynamodb`, `db-nosql-document--generic`, `db-nosql-document--mongodb-atlas`, `db-timeseries--generic`, `db-timeseries--influxdb`, `db-timeseries--influxdb-cloud`, `db-timeseries--timescale-cloud`, `db-timeseries--timescaledb`, `db-timeseries--timestream`, `db-vector--generic`, `db-vector--pgvector`, `db-vector--pinecone`

**`deploy` (27)**
`arch-microservices`, `arch-serverless`, `arch-serverless--aws`, `arch-serverless--azure`, `arch-serverless--gcp`, `deploy-blue-green`, `deploy-canary`, `deploy-rolling`, `genai-inference`, `genai-inference--anthropic`, `genai-inference--fal`, `genai-inference--huggingface`, `genai-inference--openai`, `genai-inference--replicate`, `iac-bicep`, `iac-cloudformation`, `iac-terraform`, `platform-kubernetes`, `platform-no-mesh`, `platform-service-mesh`, `platform-vm-first`, `release-feature-flags`, `sec-auth-mtls-service-mesh`, `ui-cross-platform`, `ui-cross-platform--flutter`, `ui-cross-platform--react-native`, `ui-cross-platform--xamarin`

**`platform` (19)**
`db-graph--generic`, `db-graph--neo4j-aura`, `db-graph--neptune`, `db-key-value--generic`, `db-key-value--redis-cloud`, `db-managed-mysql--planetscale`, `db-managed-postgres--neon`, `db-nosql-document--dynamodb`, `db-nosql-document--generic`, `db-nosql-document--mongodb-atlas`, `db-timeseries--generic`, `db-timeseries--influxdb`, `db-timeseries--influxdb-cloud`, `db-timeseries--timescale-cloud`, `db-timeseries--timescaledb`, `db-timeseries--timestream`, `db-vector--generic`, `db-vector--pgvector`, `db-vector--pinecone`

**`security` (5)**
`compliance-ccpa`, `compliance-gdpr-basic`, `compliance-gdpr-right-to-be-forgotten`, `compliance-hipaa`, `compliance-sox`

**`test` (11)**
`api-graphql-schema-first`, `api-rest-resource-oriented`, `build-hermetic-builds`, `event-sourcing`, `queue-consumer-idempotency`, `release-feature-flags`, `resilience-timeouts-retries-backoff`, `saga-orchestration`, `test-contract-testing`, `test-pyramid`, `ui-spa`

**`coding` (15)**
`build-hermetic-builds`, `code-di-pure`, `dev-gitflow`, `dev-trunk-based-development`, `gof-adapter`, `gof-command`, `gof-decorator`, `gof-dependency-injection`, `gof-factory-method`, `gof-observer`, `gof-singleton`, `gof-strategy`, `gof-template-method`, `test-contract-testing`, `test-pyramid`

**`design` (121)**, **`ops` (133)**, **`build` (115)** — these types apply broadly across most of the registry (nearly all non-database patterns carry all three). They are not listed exhaustively here; filter with `jq '[.types[] | select(. == "design")]' patterns/*.json` if needed.

---

### Cost Fields

```json
  "cost": {
    "adoptionCost": 3500.0,
    "licenseCost": 0.0,
    "estimatedMonthlyRangeUsd": {
      "min": 0.0,
      "max": 5000.0
    },
    "freeTierEligible": false,
    "preferredProviders": [
      "aws",
      "azure",
      "gcp"
    ],
    "costCeilingCompatibleUsd": 2000,
    "costNotes": "Seeded via heuristics; validate against current pricing and expected workload (throughput, storage, retention, egress).",
    "provenance": {
      "estimatedMonthlyRangeUsd": "Serverless architectures have true pay-per-use pricing. Min=$0 represents development/staging environments with minimal traffic that stay within generous free tiers (AWS Lambda 1M free requests/month, API Gateway 1M calls/month first year, DynamoDB 25GB free). Max=$5000 represents a production workload with ~100M Lambda invocations/month ($20), API Gateway (~$350 for 100M requests), DynamoDB on-demand ($500-1000), S3 storage/transfer ($200-500), EventBridge ($100), Step Functions ($500), CloudWatch logs ($300), and data transfer costs ($1000-2000). High-traffic applications can exceed this, but $5000 covers most mid-scale serverless deployments processing millions of events monthly. Costs scale linearly with usage, making it cost-efficient for variable workloads but potentially expensive at very high scale compared to dedicated infrastructure.",
      "adoptionCost": "High complexity adoption requiring significant architectural shift. Team needs to learn event-driven design patterns, function composition, cold start optimization, distributed tracing, and stateless architecture principles. Implementation involves: refactoring existing code into functions (40-80 hours), setting up event buses and message routing (20-40 hours), implementing observability/monitoring for distributed functions (20-30 hours), configuring IAM/security policies (15-25 hours), setting up CI/CD pipelines for function deployment (15-25 hours), and handling distributed debugging/testing (20-30 hours). Requires expertise in cloud provider's serverless ecosystem (Lambda/Functions, EventBridge/EventGrid, Step Functions/Logic Apps). Initial productivity drop as team adapts to function-based development. Includes potential for architectural mistakes (over-fragmentation, chatty functions) requiring rework. Estimated 130-230 engineering hours at $150/hour blended rate = $3500 average.",
      "licenseCost": "Serverless services are consumption-based with no upfront licensing fees. AWS Lambda, Azure Functions, Google Cloud Functions, API Gateway, EventBridge, and similar managed services charge only for usage with no license costs. Open-source frameworks like Serverless Framework, AWS SAM, or Terraform for infrastructure-as-code are free. Optional commercial tools exist (Serverless.com Pro/Enterprise for teams, Datadog/New Relic for enhanced monitoring) but aren't required. The pattern itself uses cloud-native managed services that bundle licensing into per-request pricing. Organizations may choose commercial observability tools ($500-2000/month) but these are operational costs, not adoption licenses.",
      "source": "LLM analysis (as of 18-Feb-2026)"
    }
  }```

Required sub-fields: `adoptionCost`, `licenseCost`, `estimatedMonthlyRangeUsd`, `freeTierEligible`.

---

### `defaultConfig` and `configSchema`

`defaultConfig` holds sensible defaults for pattern-level configuration. When a pattern is selected and the user has not provided explicit config in `spec.patterns.<id>`, these defaults are merged into `spec.assumptions.patterns.<id>`.

`configSchema` is a JSON Schema object validating any user overrides.

```json
"defaultConfig": {
  "ttl_seconds": 3600,
  "eviction_policy": "lru"
},
"configSchema": {
  "type": "object",
  "properties": {
    "ttl_seconds": { "type": "integer", "minimum": 60, "description": "Cache TTL in seconds" },
    "eviction_policy": { "type": "string", "enum": ["lru", "lfu", "fifo"] }
  }
}
```

---

## Canonical Spec Schema (`canonical-schema.yaml`)

Only `project` is required. All other sections are optional.

### `project` (required)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Project name |
| `domain` | string | Business domain |

### `functional`

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | One-paragraph description of what the app does |
| `users` | array | User roles with goals |
| `workflows` | array | Named workflows with steps |
| `entities` | array | Core domain entities |

### `constraints`

| Field | Type | Values |
|-------|------|--------|
| `cloud` | enum | `agnostic`, `aws`, `azure`, `gcp`, `on-prem`, `n/a` |
| `language` | enum | `agnostic`, `python`, `typescript`, `javascript`, `java`, `go`, `csharp`, `rust`, `kotlin`, `sql`, `dart`, `swift`, `php`, `ruby`, `scala`, `objective-c`, `c`, `cpp`, `n/a` |
| `platform` | enum | `web`, `mobile`, `desktop`, `api`, `worker`, `batch`, `data-pipeline`, `ml-training`, `ml-inference`, `iot`, `library`, `cli`, `agnostic`, `n/a` |
| `tenantCount` | integer | Number of tenants (≥ 0) |
| `saas-providers` | array | Acceptable SaaS providers for pattern variant selection. Includes IdP providers (`auth0`, `okta`) and monitoring providers (`datadog`, `grafana-cloud`) in addition to hosting and database SaaS. Note: AWS-native services (Cognito, DynamoDB, Timestream) are selected via `cloud: aws`, not via `saas-providers`. |
| `disallowed-saas-providers` | array | Providers explicitly excluded; provider-specific patterns requiring them are rejected |
| `features` | object | Boolean feature toggles — see Features below |

#### `constraints.features`

All fields are boolean (default: absent = false):

| Field | Description |
|-------|-------------|
| `caching` | Application uses a caching layer |
| `async_messaging` | Application uses message queues or event streaming |
| `ai_inference` | Application includes AI/ML inference |
| `multi_tenancy` | Application supports multiple tenants |
| `batch_processing` | Application includes batch jobs |
| `distributed_transactions` | Application requires distributed transaction coordination |
| `real_time_streaming` | Application requires real-time data streaming |
| `vector_search` | Application requires vector/embedding search |
| `document_store` | Application uses a document-oriented NoSQL database |
| `key_value_store` | Application uses a key-value store |
| `graph_database` | Application requires graph database |
| `time_series_db` | Application stores and queries time-series data |
| `oltp_workload` | Online Transaction Processing workload |
| `olap_workload` | Online Analytical Processing workload |
| `cold_archive_tiering` | Data tiered to cold/archive storage to reduce cost |
| `messaging_delivery_guarantee` | `at-most-once` / `at-least-once` / `exactly-once` (enum, not boolean) |

### `nfr`

| Field | Type | Description |
|-------|------|-------------|
| `availability.target` | number 0–1 | Uptime target (e.g. `0.999` = 99.9%) |
| `rpo_minutes` | integer | Recovery Point Objective in minutes |
| `rto_minutes` | integer | Recovery Time Objective in minutes |
| `latency.p95Milliseconds` | number or `"n/a"` | 95th-percentile request latency in ms |
| `latency.p99Milliseconds` | number or `"n/a"` | 99th-percentile request latency in ms |
| `latency.jobStartP95Seconds` | number | 95th-percentile job start latency in seconds |
| `latency.jobStartP99Seconds` | number | 99th-percentile job start latency in seconds |
| `throughput.peak_jobs_per_hour` | integer | Peak batch/async jobs per hour |
| `throughput.peak_query_per_second_read` | number | Peak read QPS for OLTP workloads |
| `throughput.peak_query_per_second_write` | number | Peak write QPS for OLTP workloads |
| `data.retention_days` | integer | Data retention period in days |
| `data.pii` | boolean | Application handles personally identifiable information |
| `data.compliance.gdpr` | boolean | Must comply with EU GDPR |
| `data.compliance.ccpa` | boolean | Must comply with California CCPA |
| `data.compliance.hipaa` | boolean | Must comply with HIPAA |
| `data.compliance.sox` | boolean | Must comply with Sarbanes-Oxley |
| `data.compliance.gdpr_rtbf` | boolean | Must implement GDPR Article 17 Right to be Forgotten |
| `consistency.needsReadYourWrites` | boolean | Requires read-your-writes consistency |
| `durability.strict` | boolean | Messages/events must not be lost |
| `security.auth` | enum | `oauth2_oidc`, `api_key`, `jwt`, `mtls`, `saml`, `password`, `n/a` |
| `security.tenant_isolation` | enum | `shared-db-row-level`, `schema-per-tenant`, `per-tenant-db`, `n/a`, `unknown` |
| `security.audit_logging` | boolean | Requires audit logging |

### `operating_model`

| Field | Type | Description |
|-------|------|-------------|
| `on_call` | boolean | Whether the team is on-call |
| `deploy_freq` | enum | `on-demand`, `daily`, `weekly`, `biweekly`, `monthly`, `quarterly`, `n/a` |
| `ops_team_size` | integer | Number of operations engineers (0 = no dedicated ops) |
| `single_resource_monthly_ops_usd` | number | Monthly cost per operations engineer (USD) |
| `amortization_months` | integer | Amortization period for TCO calculation (default: 24) |

### `cost`

| Field | Type | Description |
|-------|------|-------------|
| `intent.priority` | enum | `minimize-opex`, `minimize-capex`, `optimize-tco` |
| `ceilings.monthly_operational_usd` | number | Monthly opex ceiling |
| `ceilings.one_time_setup_usd` | number | Capex ceiling |
| `preferences.prefer_free_tier_if_possible` | boolean | Favour patterns with free tiers |
| `preferences.prefer_saas_first` | boolean | Favour managed SaaS patterns |

### `disallowed-patterns`

Array of pattern IDs to unconditionally exclude before any rules-based evaluation (Phase 2.5). Providing an ID that does not exist in the registry causes a hard error (exit 1).

### `patterns`

Object of user overrides for pattern-specific configuration. Keys are pattern IDs; values are validated against each pattern's `configSchema`.

### `assumptions`

Written by the compiler (not user-provided). Records which fields were defaulted. Sub-sections: `constraints`, `nfr`, `cost`, `operating_model`, `patterns`. Null-default fields are not written to this section.

---

## Capability Vocabulary (`capability-vocabulary.yaml`)

Defines canonical names and aliases for capability strings used in pattern `provides` and `requires` arrays. The vocabulary is **additive** — unknown capability names are allowed through; only registered aliases are rejected (triggering a test failure in `test_registry_integrity.py`).

### Capability categories

| Category | Meaning |
|----------|---------|
| `pattern` | Must be provided by a selected pattern |
| `environment` | Always satisfied by the deployment environment — no pattern needs to provide it |

### Naming convention

Canonical capability names use `lowercase-with-hyphens` (e.g. `auto-scaling`, `api-versioning`, `secrets-management`). Aliases in the vocabulary are non-canonical strings found in patterns that mean the same thing. When an alias is registered, any pattern still using it will fail `test_registry_integrity.py` until updated to the canonical form.

---

## Field Naming Convention

Pattern rule paths match spec field names exactly (no mapping layer):

- `p95Milliseconds`, `p99Milliseconds` — camelCase, matches spec exactly
- `cloud`, `language` — singular, match `constraints.cloud` / `constraints.language`
- Capability names — `lowercase-with-hyphens` throughout
