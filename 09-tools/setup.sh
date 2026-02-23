#!/usr/bin/env bash
# Vibe Marketing - Setup Script
# Configura dependencias e valida ambiente para o executor threaded.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REQ_FILE="${SCRIPT_DIR}/requirements.txt"

INSTALL_DEPS=1
PERSIST_KEYS=0
CHECK_ONLY=0
SHELL_FILE=""
RUN_ONBOARD=0
ONBOARD_DRY_RUN=0
ONBOARD_AUTO_APPLY=0
ONBOARD_APPLY_KEYS=0
ONBOARD_IDE=""

print_usage() {
  cat <<'USAGE'
Usage:
  ./09-tools/setup.sh [options]

Options:
  --check-only         Apenas valida ambiente (nao instala deps).
  --skip-deps          Nao instala dependencias Python.
  --persist-keys       Persiste PERPLEXITY_API_KEY e FIRECRAWL_API_KEY no shell profile.
  --shell-file <path>  Forca arquivo de profile (ex: ~/.zshrc).
  --run-onboard        Executa onboarding MCP/IDE via 09-tools/onboard.py.
  --onboard-dry-run    Executa onboarding em modo preview (diff sem aplicar).
  --onboard-yes        Auto-aplica mudancas por IDE (equivale a --yes no onboard).
  --onboard-apply-keys Aplica PERPLEXITY_API_KEY/FIRECRAWL_API_KEY no profile via onboard.
  --onboard-ide <csv>  IDEs alvo (ex: codex,cursor,kimi,antigravity).
  --help               Mostra esta ajuda.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      INSTALL_DEPS=0
      shift
      ;;
    --skip-deps)
      INSTALL_DEPS=0
      shift
      ;;
    --persist-keys)
      PERSIST_KEYS=1
      shift
      ;;
    --shell-file)
      SHELL_FILE="${2:-}"
      if [[ -z "${SHELL_FILE}" ]]; then
        echo "ERROR: --shell-file requires a path."
        exit 1
      fi
      shift 2
      ;;
    --run-onboard)
      RUN_ONBOARD=1
      shift
      ;;
    --onboard-dry-run)
      RUN_ONBOARD=1
      ONBOARD_DRY_RUN=1
      shift
      ;;
    --onboard-yes)
      RUN_ONBOARD=1
      ONBOARD_AUTO_APPLY=1
      shift
      ;;
    --onboard-apply-keys)
      RUN_ONBOARD=1
      ONBOARD_APPLY_KEYS=1
      shift
      ;;
    --onboard-ide)
      RUN_ONBOARD=1
      ONBOARD_IDE="${2:-}"
      if [[ -z "${ONBOARD_IDE}" ]]; then
        echo "ERROR: --onboard-ide requires a csv value."
        exit 1
      fi
      shift 2
      ;;
    --help|-h)
      print_usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1"
      print_usage
      exit 1
      ;;
  esac
done

detect_shell_file() {
  if [[ -n "${SHELL_FILE}" ]]; then
    echo "${SHELL_FILE/#\~/$HOME}"
    return
  fi

  case "${SHELL:-}" in
    */zsh) echo "$HOME/.zshrc" ;;
    */bash) echo "$HOME/.bashrc" ;;
    *) echo "$HOME/.profile" ;;
  esac
}

escape_single_quotes() {
  local raw="$1"
  printf "%s" "$raw" | sed "s/'/'\"'\"'/g"
}

upsert_export_in_profile() {
  local profile_file="$1"
  local var_name="$2"
  local var_value="$3"
  local escaped_value
  local tmp_file

  escaped_value="$(escape_single_quotes "$var_value")"
  mkdir -p "$(dirname "$profile_file")"
  touch "$profile_file"
  tmp_file="$(mktemp)"

  awk -v var="$var_name" '$0 !~ ("^export " var "=") { print }' "$profile_file" > "$tmp_file"
  printf "export %s='%s'\n" "$var_name" "$escaped_value" >> "$tmp_file"
  mv "$tmp_file" "$profile_file"
}

validate_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Install Python 3.8+ first."
    exit 1
  fi

  local py_ver
  py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  echo "Python detected: ${py_ver}"

  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "ERROR: Python 3.8+ is required."
    exit 1
  fi
}

install_dependencies() {
  if [[ ! -f "${REQ_FILE}" ]]; then
    echo "ERROR: requirements.txt not found at ${REQ_FILE}"
    exit 1
  fi

  if [[ "${INSTALL_DEPS}" -eq 1 ]]; then
    echo "Installing Python dependencies..."
    python3 -m pip install -r "${REQ_FILE}"
  else
    echo "Skipping dependency install (--check-only/--skip-deps)."
  fi
}

validate_imports() {
  echo "Validating Python modules..."
  python3 - <<'PY'
import requests
import bs4
import yaml
print("Imports OK: requests, bs4, yaml")
PY
}

configure_output_dirs() {
  mkdir -p "${SKILL_DIR}/08-output"
  echo "Output directory ready: ${SKILL_DIR}/08-output"
}

persist_keys_if_requested() {
  if [[ "${PERSIST_KEYS}" -ne 1 ]]; then
    return
  fi

  local profile_file
  profile_file="$(detect_shell_file)"
  echo "Persisting API keys in: ${profile_file}"

  local perplexity_key="${PERPLEXITY_API_KEY:-}"
  local firecrawl_key="${FIRECRAWL_API_KEY:-}"

  if [[ -z "${perplexity_key}" ]]; then
    read -r -s -p "Enter PERPLEXITY_API_KEY: " perplexity_key
    echo
  fi
  if [[ -z "${firecrawl_key}" ]]; then
    read -r -s -p "Enter FIRECRAWL_API_KEY: " firecrawl_key
    echo
  fi

  if [[ -n "${perplexity_key}" ]]; then
    upsert_export_in_profile "${profile_file}" "PERPLEXITY_API_KEY" "${perplexity_key}"
    export PERPLEXITY_API_KEY="${perplexity_key}"
  fi
  if [[ -n "${firecrawl_key}" ]]; then
    upsert_export_in_profile "${profile_file}" "FIRECRAWL_API_KEY" "${firecrawl_key}"
    export FIRECRAWL_API_KEY="${firecrawl_key}"
  fi

  echo "Keys updated. Open a new shell or run: source ${profile_file}"
}

report_key_status() {
  echo
  echo "API key status:"
  if [[ -n "${PERPLEXITY_API_KEY:-}" ]]; then
    echo "  - PERPLEXITY_API_KEY: configured"
  else
    echo "  - PERPLEXITY_API_KEY: missing"
  fi
  if [[ -n "${FIRECRAWL_API_KEY:-}" ]]; then
    echo "  - FIRECRAWL_API_KEY: configured"
  else
    echo "  - FIRECRAWL_API_KEY: missing"
  fi

  if [[ -z "${PERPLEXITY_API_KEY:-}" || -z "${FIRECRAWL_API_KEY:-}" ]]; then
    local profile_hint
    profile_hint="$(detect_shell_file)"
    echo
    echo "Premium providers need both keys. To configure manually:"
    echo "  export PERPLEXITY_API_KEY='your_key_here'"
    echo "  export FIRECRAWL_API_KEY='your_key_here'"
    echo
    echo "For persistence across sessions on this machine, add to ${profile_hint}."
    echo "Or run this script with --persist-keys."
  fi
}

run_onboard_if_requested() {
  if [[ "${RUN_ONBOARD}" -ne 1 ]]; then
    return
  fi

  local cmd=(python3 "${SCRIPT_DIR}/onboard.py" run)
  if [[ "${ONBOARD_DRY_RUN}" -eq 1 ]]; then
    cmd+=("--dry-run")
  fi
  if [[ "${ONBOARD_AUTO_APPLY}" -eq 1 ]]; then
    cmd+=("--yes")
  fi
  if [[ "${ONBOARD_APPLY_KEYS}" -eq 1 ]]; then
    cmd+=("--apply-keys")
  fi
  if [[ -n "${ONBOARD_IDE}" ]]; then
    cmd+=("--ide" "${ONBOARD_IDE}")
  fi
  if [[ -n "${SHELL_FILE}" ]]; then
    cmd+=("--shell-file" "${SHELL_FILE}")
  fi

  echo
  echo "Running vm-onboard:"
  echo "  ${cmd[*]}"
  "${cmd[@]}"
}

print_next_steps() {
  echo
  echo "Setup complete."
  echo
  echo "Next steps:"
  echo "  1. Run threaded foundation flow:"
  echo "     python3 ${SCRIPT_DIR}/pipeline_runner.py run --project-id demo --thread-id t1 --stack-path ${SKILL_DIR}/06-stacks/foundation-stack/stack.yaml --query 'crm para clinicas'"
  echo "  2. Check status:"
  echo "     python3 ${SCRIPT_DIR}/pipeline_runner.py status --project-id demo --thread-id t1"
  echo "  3. Run onboarding preview (optional):"
  echo "     python3 ${SCRIPT_DIR}/onboard.py run --dry-run --ide codex,cursor,kimi,antigravity"
  echo "  4. Approve next stage:"
  echo "     python3 ${SCRIPT_DIR}/pipeline_runner.py approve --project-id demo --thread-id t1 --stage brand-voice"
}

echo "Vibe Marketing setup"
echo "Skill directory: ${SKILL_DIR}"
echo

validate_python
install_dependencies
validate_imports
configure_output_dirs
persist_keys_if_requested
report_key_status
run_onboard_if_requested
print_next_steps
