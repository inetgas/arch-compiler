"""Shared preflight checks for architecture compilation and implementation workflows."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COMPILER_ENTRIES = [
    "tools/archcompiler.py",
    "schemas",
    "config",
    "patterns",
]


@dataclass
class PreflightResult:
    ok: bool
    lines: list[str]


def _run_git(app_repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(app_repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _is_temporary_path(path: Path) -> bool:
    resolved = path.resolve()
    return str(resolved).startswith("/tmp/") or str(resolved).startswith("/private/tmp/")


def _check_compiler_root(compiler_root: Path) -> list[str]:
    errors: list[str] = []

    if not compiler_root.exists():
        errors.append(f"Compiler repo does not exist: {compiler_root}")
        return errors

    if _is_temporary_path(compiler_root):
        errors.append(
            f"Compiler repo is installed in a temporary path: {compiler_root}. "
            "Use a stable location such as ~/.codex/arch-compiler or ~/.claude/arch-compiler."
        )

    for entry in REQUIRED_COMPILER_ENTRIES:
        if not (compiler_root / entry).exists():
            errors.append(
                f"Compiler repo is missing required entry: {(compiler_root / entry)}"
            )

    return errors


def _check_app_repo(app_repo: Path) -> list[str]:
    errors: list[str] = []

    if not app_repo.exists():
        errors.append(f"Application repo does not exist: {app_repo}")
        return errors

    if not app_repo.is_dir():
        errors.append(f"Application repo path is not a directory: {app_repo}")
        return errors

    git_dir = _run_git(app_repo, "rev-parse", "--git-dir")
    if git_dir.returncode != 0:
        errors.append(
            f"Application repo git is not initialized: {app_repo}. "
            'Run: git -C <app-repo> init'
        )
        return errors

    head = _run_git(app_repo, "rev-parse", "HEAD")
    if head.returncode != 0:
        errors.append(
            f"Application repo has no initial commit: {app_repo}. "
            'Run: git -C <app-repo> commit --allow-empty -m "chore: initial commit"'
        )

    return errors


def _check_approved_architecture(app_repo: Path) -> list[str]:
    errors: list[str] = []
    architecture_yaml = app_repo / "docs" / "architecture" / "architecture.yaml"

    if not architecture_yaml.exists():
        errors.append(
            f"Approved architecture is missing: {architecture_yaml}. "
            "Implement mode requires docs/architecture/architecture.yaml with STATUS: APPROVED."
        )
        return errors

    contents = architecture_yaml.read_text(encoding="utf-8")
    if "STATUS: APPROVED" not in contents:
        errors.append(
            f"Approved architecture header missing: {architecture_yaml}. "
            "Implement mode requires STATUS: APPROVED."
        )

    return errors


def run_preflight(app_repo: Path, mode: str, compiler_root: Path) -> PreflightResult:
    errors: list[str] = []
    errors.extend(_check_compiler_root(compiler_root))
    errors.extend(_check_app_repo(app_repo))

    if mode == "implement":
        errors.extend(_check_approved_architecture(app_repo))

    if errors:
        lines = ["Preflight failed:"] + [f"- {error}" for error in errors]
        return PreflightResult(ok=False, lines=lines)

    lines = [
        "Preflight passed.",
        f"- Compiler repo: {compiler_root}",
        f"- App repo: {app_repo}",
        f"- Mode: {mode}",
    ]
    return PreflightResult(ok=True, lines=lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run shared preflight checks for architecture compilation or implementation workflows."
    )
    parser.add_argument("--app-repo", required=True, help="Path to the application repository")
    parser.add_argument(
        "--mode",
        choices=["compile", "implement"],
        required=True,
        help="Which workflow is about to run",
    )
    parser.add_argument(
        "--compiler-root",
        help="Stable local path to the Architecture Compiler repo. Defaults to the repo containing this script.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    compiler_root = (
        Path(args.compiler_root).expanduser()
        if args.compiler_root
        else Path(__file__).resolve().parent.parent
    )
    app_repo = Path(args.app_repo).expanduser().resolve()

    result = run_preflight(app_repo=app_repo, mode=args.mode, compiler_root=compiler_root)
    output = "\n".join(result.lines)
    stream = sys.stdout if result.ok else sys.stderr
    print(output, file=stream)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
