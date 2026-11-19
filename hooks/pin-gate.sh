#!/usr/bin/env bash
# Stop hook: blocks the end of a turn while a changed GitHub Actions workflow uses an action not pinned to a commit SHA.
set -euo pipefail
shopt -s inherit_errexit nullglob

readonly WORKFLOWS_DIR=".github/workflows"
readonly USES_PATTERN='^[[:space:]]*(-[[:space:]]+)?uses:'
readonly SHA_PATTERN='^[0-9a-f]{40}$'
readonly STOP_HOOK_ACTIVE_PATTERN='"stop_hook_active"[[:space:]]*:[[:space:]]*true'
readonly EXIT_BLOCK=2

action_of() {
  local value="$1"
  value="${value#*uses:}"
  value="${value%%#*}"
  printf '%s' "${value//[\"\'[:space:]]/}"
}

unpinned_actions_in() {
  local -r project_dir="$1" file="$2"
  local -i line_number=0
  local line="" action=""
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line_number+=1
    if [[ ! "${line}" =~ ${USES_PATTERN} ]]; then continue; fi
    action="$(action_of "${line}")"
    if [[ "${action}" == ./* || "${action}" == docker://* ]]; then continue; fi
    if [[ "${action}" == *@* && "${action##*@}" =~ ${SHA_PATTERN} ]]; then continue; fi
    printf '  %s:%d: %s\n' "${file#"${project_dir}/"}" "${line_number}" "${action}"
  done <"${file}"
}

unpinned_actions_in_changed_workflows() {
  local -r project_dir="$1"
  local -i check_all=1
  local file="" file_status=""
  # Not a git repo: nothing tells new workflows from legacy ones, so check them all.
  if command -v git >/dev/null && git -C "${project_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then check_all=0; fi
  for file in "${project_dir}/${WORKFLOWS_DIR}"/*.yml "${project_dir}/${WORKFLOWS_DIR}"/*.yaml; do
    if ((check_all == 0)); then
      file_status="$(git -C "${project_dir}" status --porcelain -- "${file}")"
      if [[ -z "${file_status}" ]]; then continue; fi
    fi
    unpinned_actions_in "${project_dir}" "${file}"
  done
}

main() {
  local hook_input="" findings=""
  hook_input="$(cat)"
  if grep -qE "${STOP_HOOK_ACTIVE_PATTERN}" <<<"${hook_input}"; then exit 0; fi
  findings="$(unpinned_actions_in_changed_workflows "${CLAUDE_PROJECT_DIR:-${PWD}}")"
  if [[ -z "${findings}" ]]; then exit 0; fi
  printf 'pin-gate: these GitHub Actions are not pinned to a full commit SHA:\n%s\nPin each to its 40-char commit SHA with the version in a trailing comment, e.g. "uses: actions/checkout@<sha> # v4.2.2". Get the SHA with: gh api repos/OWNER/REPO/commits/TAG --jq .sha (never invent one). If no tool can reach GitHub, tell the user the SHA is still to pin: the next stop is allowed, but this check runs again every turn until the workflow is pinned or committed.\n' "${findings}" >&2
  exit "${EXIT_BLOCK}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
