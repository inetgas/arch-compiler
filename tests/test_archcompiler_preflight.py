import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
PREFLIGHT = PROJECT_ROOT / "tools" / "archcompiler_preflight.py"


def run_preflight(app_repo: Path, mode: str = "compile") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PREFLIGHT), "--app-repo", str(app_repo), "--mode", mode],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class TestArchcompilerPreflightCompileMode:
    def test_compile_mode_fails_when_app_repo_is_not_git_initialized(self, tmp_path):
        app_repo = tmp_path / "app"
        app_repo.mkdir()

        result = run_preflight(app_repo, mode="compile")

        assert result.returncode == 1
        assert "git is not initialized" in (result.stdout + result.stderr)

    def test_compile_mode_fails_when_app_repo_has_no_initial_commit(self, tmp_path):
        app_repo = tmp_path / "app"
        app_repo.mkdir()
        init_result = git(app_repo, "init")
        assert init_result.returncode == 0

        result = run_preflight(app_repo, mode="compile")

        assert result.returncode == 1
        assert "initial commit" in (result.stdout + result.stderr)

    def test_compile_mode_passes_after_git_init_and_initial_commit(self, tmp_path):
        app_repo = tmp_path / "app"
        app_repo.mkdir()
        assert git(app_repo, "init").returncode == 0
        assert git(app_repo, "config", "user.email", "test@example.com").returncode == 0
        assert git(app_repo, "config", "user.name", "Test User").returncode == 0
        assert git(app_repo, "commit", "--allow-empty", "-m", "chore: initial commit").returncode == 0

        result = run_preflight(app_repo, mode="compile")

        assert result.returncode == 0
        assert "Preflight passed" in result.stdout


class TestArchcompilerPreflightImplementMode:
    def test_implement_mode_fails_without_approved_architecture(self, tmp_path):
        app_repo = tmp_path / "app"
        app_repo.mkdir()
        assert git(app_repo, "init").returncode == 0
        assert git(app_repo, "config", "user.email", "test@example.com").returncode == 0
        assert git(app_repo, "config", "user.name", "Test User").returncode == 0
        assert git(app_repo, "commit", "--allow-empty", "-m", "chore: initial commit").returncode == 0

        result = run_preflight(app_repo, mode="implement")

        assert result.returncode == 1
        assert "approved architecture" in (result.stdout + result.stderr).lower()

    def test_implement_mode_passes_with_approved_architecture(self, tmp_path):
        app_repo = tmp_path / "app"
        architecture_dir = app_repo / "docs" / "architecture"
        architecture_dir.mkdir(parents=True)
        (architecture_dir / "architecture.yaml").write_text(
            "# STATUS: APPROVED\nproject:\n  name: test\n",
            encoding="utf-8",
        )
        assert git(app_repo, "init").returncode == 0
        assert git(app_repo, "config", "user.email", "test@example.com").returncode == 0
        assert git(app_repo, "config", "user.name", "Test User").returncode == 0
        assert git(app_repo, "add", "docs").returncode == 0
        assert git(app_repo, "commit", "-m", "feat: add approved architecture").returncode == 0

        result = run_preflight(app_repo, mode="implement")

        assert result.returncode == 0
        assert "Preflight passed" in result.stdout
