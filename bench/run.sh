#!/usr/bin/env bash
# Runs every task in bench/tasks once per arm and per run, in a fresh git folder each time.
# Usage: bench/run.sh <out-dir> <runs> <arm>=<plugin-dir or empty> ...
# Example: bench/run.sh /tmp/bench 2 none= old=/tmp/chef-0.8.1 new=/tmp/chef-new
set -euo pipefail
shopt -s inherit_errexit nullglob

readonly MODEL="claude-sonnet-5-5"
readonly MAX_BUDGET_USD="3"
TASKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tasks"
readonly TASKS_DIR

die() {
  printf 'bench: %s\n' "$*" >&2
  exit 1
}

prepare_workspace() {
  local -r task_dir="$1"
  local -r workspace="$2"
  mkdir -p "${workspace}"
  if [[ -d "${task_dir}/seed" ]]; then
    cp -r "${task_dir}/seed/." "${workspace}/"
  fi
  git -C "${workspace}" init -q
  git -C "${workspace}" add -A
  git -C "${workspace}" -c user.name=bench -c user.email=bench@localhost commit -q --allow-empty -m seed
}

run_one() {
  local -r task_dir="$1"
  local -r run_dir="$2"
  local -r plugin_dir="$3"
  local -a plugin_args=()
  [[ ! -e "${run_dir}" ]] || die "${run_dir} exists: use a new out-dir"
  [[ -z "${plugin_dir}" ]] || plugin_args=(--plugin-dir "${plugin_dir}")
  prepare_workspace "${task_dir}" "${run_dir}/workspace"
  (
    cd "${run_dir}/workspace"
    claude -p "$(cat "${task_dir}/prompt.md")" \
      --model "${MODEL}" \
      --output-format json \
      --setting-sources project \
      --strict-mcp-config \
      --no-session-persistence \
      --dangerously-skip-permissions \
      --max-budget-usd "${MAX_BUDGET_USD}" \
      "${plugin_args[@]}" \
      </dev/null >"${run_dir}/result.json" 2>"${run_dir}/stderr.log"
  ) || printf 'bench: %s exited with an error, see stderr.log\n' "${run_dir}" >&2
}

main() {
  (($# >= 3)) || die "usage: run.sh <out-dir> <runs> <arm>=<plugin-dir> ..."
  [[ "$2" =~ ^[1-9][0-9]*$ ]] || die "runs must be a positive integer, got '$2'"
  local -r out_dir="$1"
  local -ri runs="$2"
  shift 2
  local arm=""
  for arm in "$@"; do
    [[ "${arm}" == *=* ]] || die "arm '${arm}' must be <name>=<plugin-dir>"
  done
  local task_dir=""
  local -i run=0
  local -a pids=()
  local -i pid=0
  for task_dir in "${TASKS_DIR}"/*/; do
    task_dir="${task_dir%/}"
    for ((run = 1; run <= runs; run++)); do
      pids=()
      for arm in "$@"; do
        run_one "${task_dir}" "${out_dir}/${arm%%=*}/$(basename "${task_dir}")/${run}" "${arm#*=}" &
        pids+=("$!")
      done
      for pid in "${pids[@]}"; do
        wait "${pid}" || printf 'bench: a run of %s failed before claude started\n' "${task_dir}" >&2
      done
    done
  done
}

main "$@"
