# Architecture and Platform Pattern Relationship

## Pattern Categories

### 1. Architecture-only Patterns (Flexible)
- arch-monolith
- arch-microservices
- arch-modular-monolith

**Characteristics:**
- Can run on ANY platform (VMs, K8s)
- Must be paired with a platform pattern
- Compatible with all platform-* patterns

### 2. Architecture+Platform Combined (Constrained)
- arch-serverless
- arch-serverless--aws
- arch-serverless--azure
- arch-serverless--gcp

**Characteristics:**
- Platform choice embedded (Lambda/Functions/Cloud Run)
- CANNOT coexist with any platform-* pattern
- Mutually exclusive with all other arch-* patterns

### 3. Platform-only Patterns (Infrastructure)
- platform-vm-first
- platform-kubernetes
- platform-no-mesh (K8s networking)
- platform-service-mesh (K8s networking)

**Characteristics:**
- Describe HOW to run architecture
- Can pair with architecture-only patterns
- Cannot coexist with arch-serverless-* patterns

## Conflict Resolution

All conflicts enforced via `incompatibleWithDesignPatterns` declarations.
Compiler's existing conflict resolution (Phase 3.3, first-selected wins)
automatically rejects incompatible patterns.

## Examples

**Serverless deployment:**
- arch-serverless--aws ✓
- No platform pattern needed (embedded)

**Monolith on VMs:**
- arch-monolith ✓
- platform-vm-first ✓

**Microservices on K8s:**
- arch-microservices ✓
- platform-kubernetes ✓
- platform-service-mesh ✓ (optional)
