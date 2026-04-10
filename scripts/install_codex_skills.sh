#!/usr/bin/env bash
set -euo pipefail

readonly REPO_URL="${ARCHCOMPILER_REPO_URL:-https://github.com/inetgas/arch-compiler.git}"
readonly SKILLS_SOURCE="${ARCHCOMPILER_SKILLS_SOURCE:-inetgas/arch-compiler}"
readonly CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
readonly AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
readonly RUNTIME_HOME="${ARCHCOMPILER_RUNTIME_HOME:-$CODEX_HOME/arch-compiler}"
readonly SKILLS_HOME="${ARCHCOMPILER_SKILLS_HOME:-$AGENTS_HOME/skills}"
readonly SKILL_NAMES=(
  "using-arch-compiler"
  "compiling-architecture"
  "implementing-architecture"
)

usage() {
  cat <<'EOF'
Install Architecture Compiler skills for Codex.

This script:
1. Installs the three Codex skills via the public skills.sh / Vercel skills CLI into ~/.agents/skills
2. Clones or updates the full Architecture Compiler runtime repo at ~/.codex/arch-compiler
3. Verifies both the installed skills and the runtime repo layout

Usage:
  ./scripts/install_codex_skills.sh

Optional environment overrides:
  HOME                         Override the base home directory (useful for testing)
  CODEX_HOME                   Override Codex home (default: $HOME/.codex)
  AGENTS_HOME                  Override shared agent home (default: $HOME/.agents)
  ARCHCOMPILER_RUNTIME_HOME    Override runtime repo path (default: $CODEX_HOME/arch-compiler)
  ARCHCOMPILER_SKILLS_HOME     Override installed skills dir (default: $AGENTS_HOME/skills)
  ARCHCOMPILER_REPO_URL        Override runtime repo clone URL
  ARCHCOMPILER_SKILLS_SOURCE   Override skills source for `npx skills add`
EOF
}

log() {
  printf '[arch-compiler] %s\n' "$1"
}

fail() {
  printf '[arch-compiler] ERROR: %s\n' "$1" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "Missing required command: $cmd"
}

ensure_runtime_repo() {
  mkdir -p "$CODEX_HOME"

  if [[ -d "$RUNTIME_HOME/.git" ]]; then
    log "Updating runtime repo at $RUNTIME_HOME"
    git -C "$RUNTIME_HOME" pull --ff-only
    return
  fi

  if [[ -e "$RUNTIME_HOME" ]]; then
    fail "Runtime path exists but is not a git repo: $RUNTIME_HOME"
  fi

  log "Cloning runtime repo to $RUNTIME_HOME"
  git clone "$REPO_URL" "$RUNTIME_HOME"
}

install_skills() {
  local args=()
  local skill
  for skill in "${SKILL_NAMES[@]}"; do
    args+=(--skill "$skill")
  done

  log "Installing Codex skills into $SKILLS_HOME"
  npx skills add "$SKILLS_SOURCE" "${args[@]}" -a codex -g -y
}

verify_runtime_repo() {
  local required_paths=(
    "$RUNTIME_HOME/tools/archcompiler.py"
    "$RUNTIME_HOME/tools/archcompiler_preflight.py"
    "$RUNTIME_HOME/patterns"
    "$RUNTIME_HOME/schemas"
    "$RUNTIME_HOME/config"
    "$RUNTIME_HOME/skills"
  )
  local path
  for path in "${required_paths[@]}"; do
    [[ -e "$path" ]] || fail "Runtime repo verification failed: missing $path"
  done
}

verify_skills() {
  local skill
  for skill in "${SKILL_NAMES[@]}"; do
    [[ -f "$SKILLS_HOME/$skill/SKILL.md" ]] || fail "Skill verification failed: missing $SKILLS_HOME/$skill/SKILL.md"
  done
}

print_summary() {
  cat <<EOF

Architecture Compiler Codex install complete.

Installed skills:
  - $SKILLS_HOME/using-arch-compiler
  - $SKILLS_HOME/compiling-architecture
  - $SKILLS_HOME/implementing-architecture

Runtime repo:
  - $RUNTIME_HOME

Next step:
  Restart Codex so the new skills are loaded.
EOF
}

main() {
  if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
  fi

  require_cmd git
  require_cmd npx

  install_skills
  ensure_runtime_repo
  verify_skills
  verify_runtime_repo
  print_summary
}

main "$@"
