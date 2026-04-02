# Contributing to Architecture Compiler

Thank you for your interest in contributing to the Architecture Compiler! This project is built for a world where both humans and AI agents collaborate on architecture.

## Table of Contents

- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [AI Agent Contributions](#ai-agent-contributions)
- [Pattern Development](#pattern-development)
- [Testing & CI/CD](#testing--cicd)
- [Code Review Guidelines](#code-review-guidelines)

## Getting Started

### Prerequisites

- Python 3.11+
- pip or uv package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/inetgas/arch-compiler.git
cd arch-compiler

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (including test tools)
python -m pip install -r tools/requirements.txt
python -m pip install -e .

# Run tests to verify setup
python -m pytest tests/ -q
```

Run tests and compiler commands from the `arch-compiler/` repo root. Some integration tests invoke `tools/archcompiler.py` using cwd-relative paths.

## How to Contribute

### Reporting Bugs & Suggestions

Please check existing issues first. When creating a report, include exact steps to reproduce, error messages, and your environment (OS, Python version).

### Contributing Code (Humans)

1. **Fork the repository** and create a branch from `main`.
2. **Make your changes** following the project's patterns.
3. **Write tests** for new functionality or patterns.
4. **Submit a pull request**.

## AI Agent Contributions

This repository has strict governance for AI contributors to ensure the integrity of the deterministic compiler:

- **Staging-Only:** Agents **MUST** author new patterns in a human-designated staging location outside `patterns/`. They are strictly forbidden from writing directly to `patterns/`.
- **Immutable Core:** Agents may not modify `schemas/`, `config/defaults.yaml`, or existing pattern JSONs in `patterns/`.
- **Procedural Guidance:** Agents must read and follow the relevant `SKILL.md` before taking action.

## Pattern Development

### Pattern Structure

Patterns are JSON files. Follow these strict rules:

1. **ID Consistency:** Pattern ID must match the filename (e.g., `cache-aside.json` → `id: "cache-aside"`).
2. **Logic:** `supports_constraints` and `supports_nfr` rules use AND logic.
3. **Integrity:** Conflict declarations must be **bidirectional** (if A conflicts B, B must conflict A).
4. **Variants:** Sibling variant patterns (e.g., `arch-serverless--aws`) must conflict with all their siblings.

### Schema-First Approach

1. Update `schemas/pattern-schema.yaml` if a new field is needed (Human only).
2. Update `schemas/canonical-schema.yaml` if a new spec field is needed (Human only).
3. Add/edit pattern files.
4. Run `python tools/audit_patterns.py` to check metadata quality.
5. Run `python -m pytest tests/ -q` from the repo root to verify nothing is broken.

## Testing & CI/CD

### Automated Validation

Every Pull Request triggers a GitHub Actions workflow that:
- Runs audits for pattern metadata, NFR logic, and conflict symmetry.
- Executes the full test suite across Python 3.11 and 3.12.
- Builds the wheel and smoke-tests the installed `archcompiler` CLI outside the repo root.

**PRs will not be merged until all CI checks pass.**

### Local packaging check

Before publishing or cutting a release, run:

```bash
python -m pip install --upgrade pip setuptools wheel build
python -m build --no-isolation
python scripts/package_smoke_test.py dist/*.whl tests/fixtures/no-advisory-success.yaml
```

### Writing Tests

- `test_*.py` — Unit/component tests.
- `test-specs/` — Integration/end-to-end tests.
- Integration spec naming: `<category>_<sub-category>_<description>_<pass|fail>.yaml`.

## Code Review Guidelines

- **Focus:** Maintainability and schema compliance.
- **Verification:** Every new pattern must be accompanied by at least one integration spec in `test-specs/` proving it triggers correctly.
- **Conflicts:** Verify that new conflicts are bidirectional using the `audit_asymmetric_conflicts.py` tool.

## Questions

- **Usage/Technical questions:** Open a GitHub Issue with appropriate labels (`bug`, `enhancement`, `pattern`).

## Code of Conduct

This project adheres to the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Contributions are licensed under the project's [MIT License](LICENSE).
