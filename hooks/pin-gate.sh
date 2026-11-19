#!/usr/bin/env bash
# GitHub Actions pin gate, two modes:
#   record (PostToolUse on Edit|Write|MultiEdit): remembers workflow files Claude edited in this session.
#   check  (Stop): blocks the end of a turn once if a remembered workflow uses an action not pinned to a commit SHA.
# Workflows the user edits, or legacy ones Claude never touched, are never checked.
set -euo pipefail
shopt -s inherit_errexit

readonly WORKFLOW_PATH_PATTERN='(^|/)\.github/workflows/[^/]+\.ya?ml$'
readonly USES_PATTERN='^[[:space:]]*(-[[:space:]]+)?uses:'
readonly SHA_PATTERN='^[0-9a-f]{40}$'
readonly STOP_HOOK_ACTIVE_PATTERN='"stop_hook_active"[[:space:]]*:[[:space:]]*true'
readonly DEFAULT_SESSION="default"
readonly EXIT_BLOCK=2

# Value of a top-level JSON string field, with \\ and \/ unescaped; empty when absent.
json_string_field() {
  local -r name="$1" json="$2"
  local value=""
  value="$(sed -n "s/.*\"${name}\"[[:space:]]*:[[:space:]]*\"\(\([^\"\\\\]\|\\\\.\)*\)\".*/\1/p" <<<"${json}" | head -n 1)"
  value="${value//\\\//\/}"
  printf '%s' "${value//\\\\/\\}"
}

marker_path() {
  local -r hook_input="$1"
  local session=""
  session="$(json_string_field session_id "${hook_input}")"
  session="${session//[^[:alnum:]-]/}"
  printf '%s/chef-pin-gate-%s' "${CHEF_PIN_GATE_DIR:-${TMPDIR:-/tmp}}" "${session:-${DEFAULT_SESSION}}"
}

# shortcut: only Edit/Write/MultiEdit are seen; a workflow written through Bash (sed, heredoc) is not checked. Add a Bash matcher if that shows up.
record() {
  local -r hook_input="$1"
  local file_path=""
  file_path="$(json_string_field file_path "${hook_input}")"
  if [[ ! "${file_path//\\//}" =~ ${WORKFLOW_PATH_PATTERN} ]]; then return 0; fi
  printf '%s\n' "${file_path}" >>"$(marker_path "${hook_input}")"
}

action_of() {
  local value="$1"
  value="${value#*uses:}"
  value="${value%%#*}"
  printf '%s' "${value//[\"\'[:space:]]/}"
}

unpinned_actions_in() {
  local -r file="$1"
  local -i line_number=0
  local line="" action=""
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line_number+=1
    if [[ ! "${line}" =~ ${USES_PATTERN} ]]; then continue; fi
    action="$(action_of "${line}")"
    if [[ "${action}" == ./* || "${action}" == docker://* ]]; then continue; fi
    if [[ "${action}" == *@* && "${action##*@}" =~ ${SHA_PATTERN} ]]; then continue; fi
    printf '  %s:%d: %s\n' "${file}" "${line_number}" "${action}"
  done <"${file}"
}

unpinned_actions_in_recorded() {
  local -r marker="$1"
  local file="" files=""
  files="$(sort -u "${marker}")"
  while IFS= read -r file; do
    if [[ -f "${file}" ]]; then unpinned_actions_in "${file}"; fi
  done <<<"${files}"
}

check() {
  local -r hook_input="$1"
  local marker="" findings=""
  marker="$(marker_path "${hook_input}")"
  if [[ ! -f "${marker}" ]]; then return 0; fi
  if grep -qE "${STOP_HOOK_ACTIVE_PATTERN}" <<<"${hook_input}"; then
    rm -f "${marker}"
    return 0
  fi
  findings="$(unpinned_actions_in_recorded "${marker}")"
  if [[ -z "${findings}" ]]; then
    rm -f "${marker}"
    return 0
  fi
  printf 'pin-gate: these GitHub Actions are not pinned to a full commit SHA:\n%s\nPin each to its 40-char commit SHA with the version in a trailing comment, e.g. "uses: actions/checkout@<sha> # v4.2.2". Get the SHA with: gh api repos/OWNER/REPO/commits/TAG --jq .sha (never invent one). If no tool can reach GitHub, tell the user the SHA is still to pin: the next stop is allowed and the check is not repeated.\n' "${findings}" >&2
  exit "${EXIT_BLOCK}"
}

main() {
  local -r mode="${1:-check}"
  local hook_input=""
  hook_input="$(cat)"
  case "${mode}" in
    record) record "${hook_input}" ;;
    check) check "${hook_input}" ;;
    *)
      printf 'pin-gate: unknown mode %s (record|check)\n' "${mode}" >&2
      exit 1
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
