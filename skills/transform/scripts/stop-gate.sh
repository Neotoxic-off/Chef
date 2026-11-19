#!/usr/bin/env bash
# Stop hook for /chef:transform: blocks the end of a turn while a TRANSFORM.md batch is edited but not validated,
# the plan lacks its council or target, or more batches are ticked than committed.
set -euo pipefail
shopt -s inherit_errexit

readonly PLAN_NAME="TRANSFORM.md"
readonly IN_PROGRESS_PATTERN='^- \[~\]'
readonly DONE_PATTERN='^- \[x\]'
readonly COUNCIL_PATTERN='^## Council'
readonly TARGET_PATTERN='^Target:[[:space:]]*[^[:space:]]'
readonly BATCH_COMMIT_SUBJECT="transform batch"
readonly STOP_HOOK_ACTIVE_PATTERN='"stop_hook_active"[[:space:]]*:[[:space:]]*true'
readonly EXIT_BLOCK=2

count_ticked_batches() {
  local -r plan_path="$1"
  local -i count=0
  local line=""
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ${DONE_PATTERN} ]]; then count+=1; fi
  done <"${plan_path}"
  printf '%d' "${count}"
}

count_batch_commits() {
  local -r project_dir="$1"
  local plan_commit=""
  if ! git -C "${project_dir}" rev-parse --verify --quiet HEAD >/dev/null; then
    printf '0'
    return
  fi
  # Count only since the commit that added this plan, so batches of an earlier transform do not count.
  plan_commit="$(git -C "${project_dir}" log -1 --diff-filter=A --format=%H -- "${PLAN_NAME}")"
  git -C "${project_dir}" rev-list --count -F --grep="${BATCH_COMMIT_SUBJECT}" ${plan_commit:+"${plan_commit}.."}HEAD
}

commit_shortfall_reason() {
  local -r plan_path="$1" project_dir="$2"
  local -i ticked=0 committed=0
  if ! command -v git >/dev/null || ! git -C "${project_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then return; fi
  ticked="$(count_ticked_batches "${plan_path}")"
  committed="$(count_batch_commits "${project_dir}")"
  if ((ticked > committed)); then
    printf 'transform: %s has %d batches ticked [x] but git has %d commits with "%s" in the subject. One commit per batch: commit each ticked batch as "<type>: %s <n>: <what>" before you stop.' \
      "${PLAN_NAME}" "${ticked}" "${committed}" "${BATCH_COMMIT_SUBJECT}" "${BATCH_COMMIT_SUBJECT}"
  fi
}

block_reason() {
  local -r plan_path="$1" project_dir="$2"
  if grep -qE "${IN_PROGRESS_PATTERN}" "${plan_path}"; then
    printf 'transform: a batch in %s is marked [~] (edited, not validated). Run its validation command, review it, tick it [x] and commit before you stop. If you need the user, ask now: the next stop is allowed.' "${PLAN_NAME}"
    return
  fi
  if ! grep -qE "${DONE_PATTERN}" "${plan_path}"; then return; fi
  if ! grep -qE "${COUNCIL_PATTERN}" "${plan_path}"; then
    printf 'transform: %s has a batch ticked [x] but no "## Council" section. Convene the council on the plan and record its members and what changed in the plan.' "${PLAN_NAME}"
    return
  fi
  if ! grep -qE "${TARGET_PATTERN}" "${plan_path}"; then
    printf 'transform: %s has a batch ticked [x] but no "Target:" line. Name the target runtime and version (e.g. "Target: Python 3.13") and validate on it.' "${PLAN_NAME}"
    return
  fi
  commit_shortfall_reason "${plan_path}" "${project_dir}"
}

main() {
  local hook_input="" reason=""
  hook_input="$(cat)"
  # shortcut: reads the plan at the session's project root, not in a worktree or a subfolder; parse `cwd` from the input if transform ever runs in one.
  local -r project_dir="${CLAUDE_PROJECT_DIR:-${PWD}}"
  local -r plan_path="${project_dir}/${PLAN_NAME}"
  if grep -qE "${STOP_HOOK_ACTIVE_PATTERN}" <<<"${hook_input}"; then exit 0; fi
  if [[ ! -f "${plan_path}" ]]; then exit 0; fi
  reason="$(block_reason "${plan_path}" "${project_dir}")"
  if [[ -z "${reason}" ]]; then exit 0; fi
  printf '%s\n' "${reason}" >&2
  exit "${EXIT_BLOCK}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
