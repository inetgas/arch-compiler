#!/usr/bin/env python3
"""Validate a built wheel and smoke-test the installed CLI in an isolated venv."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path


REQUIRED_WHEEL_CONTENTS = [
    "config/defaults.yaml",
    "schemas/canonical-schema.yaml",
]

REQUIRED_WHEEL_PREFIXES = [
    "patterns/",
    "schemas/",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify built wheel contents and smoke-test the installed archcompiler CLI."
    )
    parser.add_argument("wheel", help="Path to the built .whl artifact")
    parser.add_argument("fixture", help="Path to a YAML spec fixture expected to compile successfully")
    return parser.parse_args()


def _assert_wheel_contents(wheel_path: Path) -> None:
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    for required in REQUIRED_WHEEL_CONTENTS:
        if not any(name.endswith(required) for name in names):
            raise SystemExit(f"Wheel is missing required file: {required}")

    for prefix in REQUIRED_WHEEL_PREFIXES:
        if not any(prefix in name for name in names):
            raise SystemExit(f"Wheel is missing required package content under: {prefix}")


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _smoke_test_cli(wheel_path: Path, fixture_path: Path) -> None:
    temp_root = Path(tempfile.mkdtemp(prefix="arch-compiler-package-smoke-"))
    try:
        venv_dir = temp_root / "venv"
        work_dir = temp_root / "work"
        work_dir.mkdir()

        venv.EnvBuilder(with_pip=True).create(venv_dir)

        bin_dir = venv_dir / ("Scripts" if sys.platform == "win32" else "bin")
        python_bin = bin_dir / ("python.exe" if sys.platform == "win32" else "python")
        archcompiler_bin = bin_dir / ("archcompiler.exe" if sys.platform == "win32" else "archcompiler")

        install = _run([str(python_bin), "-m", "pip", "install", str(wheel_path)])
        if install.returncode != 0:
            raise SystemExit(f"Wheel install failed:\n{install.stdout}\n{install.stderr}")

        smoke = _run([str(archcompiler_bin), str(fixture_path)], cwd=work_dir)
        if smoke.returncode != 0:
            raise SystemExit(f"Installed CLI smoke test failed:\n{smoke.stdout}\n{smoke.stderr}")
        if "Cost Feasibility Analysis" not in smoke.stdout:
            raise SystemExit("Installed CLI smoke test did not emit expected cost analysis output")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> None:
    args = _parse_args()
    wheel_path = Path(args.wheel).resolve()
    fixture_path = Path(args.fixture).resolve()

    if not wheel_path.exists():
        raise SystemExit(f"Wheel not found: {wheel_path}")
    if not fixture_path.exists():
        raise SystemExit(f"Fixture not found: {fixture_path}")

    _assert_wheel_contents(wheel_path)
    _smoke_test_cli(wheel_path, fixture_path)
    print(f"Package smoke test passed for {wheel_path.name}")


if __name__ == "__main__":
    main()
