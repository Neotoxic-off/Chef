#!/usr/bin/env bash
# Stop hook for /chef:transform: blocks the end of a turn while a TRANSFORM.md batch is edited but not validated.
set -euo pipefail
shopt -s inherit_errexit

readonly PLAN_NAME="TRANSFORM.md"
readonly IN_PROGRESS_PATTERN='^- \[~\]'
readonly STOP_HOOK_ACTIVE_PATTERN='"stop_hook_active"[[:space:]]*:[[:space:]]*true'
readonly EXIT_BLOCK=2

main() {
  local hook_input=""
  hook_input="$(cat)"
  # shortcut: reads the plan at the session's project root, not in a worktree or a subfolder; parse `cwd` from the input if transform ever runs in one.
  local -r plan_path="${CLAUDE_PROJECT_DIR:-${PWD}}/${PLAN_NAME}"
  if grep -qE "${STOP_HOOK_ACTIVE_PATTERN}" <<<"${hook_input}"; then exit 0; fi
  if [[ ! -f "${plan_path}" ]] || ! grep -qE "${IN_PROGRESS_PATTERN}" "${plan_path}"; then exit 0; fi
  printf 'transform: a batch in %s is marked [~] (edited, not validated). Run its validation command, review it, tick it [x] and commit before you stop. If you need the user, ask now: the next stop is allowed.\n' "${PLAN_NAME}" >&2
  exit "${EXIT_BLOCK}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
