#!/usr/bin/env bash
# Runs every task in bench/tasks once per arm and per run, in a fresh git folder each time.
# Usage: bench/run.sh <out-dir> <runs> <arm>=<plugin-dir, a .md file used as CLAUDE.md, or empty> ...
# Example: bench/run.sh /tmp/bench 2 none= old=/tmp/chef-0.8.1 new=/tmp/chef-new
# Set TASKS="python bugfix" to run only those tasks. Needs Docker running and PYTHON (default: python)
# able to import bench/score.py; the batch stops at the first run that gave no answer (usage limit).
set -euo pipefail
shopt -s inherit_errexit nullglob

readonly MODEL="claude-sonnet-5-5"
readonly MAX_BUDGET_USD="1"
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BENCH_DIR
readonly TASKS_DIR="${BENCH_DIR}/tasks"
readonly PYTHON="${PYTHON:-python}"

die() {
  printf 'bench: %s\n' "$*" >&2
  exit 1
}

prepare_workspace() {
  local -r task_dir="$1"
  local -r workspace="$2"
  local -r claude_md="$3"
  mkdir -p "${workspace}"
  if [[ -d "${task_dir}/seed" ]]; then
    cp -r "${task_dir}/seed/." "${workspace}/"
  fi
  [[ -z "${claude_md}" ]] || cp "${claude_md}" "${workspace}/CLAUDE.md"
  git -C "${workspace}" init -q
  git -C "${workspace}" add -A
  git -C "${workspace}" -c user.name=bench -c user.email=bench@localhost commit -q --allow-empty -m seed
}

run_one() {
  local -r task_dir="$1"
  local -r run_dir="$2"
  local -r arm_source="$3"
  local -a plugin_args=()
  local claude_md=""
  local prompt=""
  [[ ! -e "${run_dir}" ]] || die "${run_dir} exists: use a new out-dir"
  prompt="$(cat "${task_dir}/prompt.md")"
  if [[ "${arm_source}" == *.md ]]; then
    claude_md="${arm_source}"
  elif [[ -n "${arm_source}" ]]; then
    plugin_args=(--plugin-dir "${arm_source}")
  fi
  prepare_workspace "${task_dir}" "${run_dir}/workspace" "${claude_md}"
  (
    cd "${run_dir}/workspace"
    claude -p "${prompt}" \
      --model "${MODEL}" \
      --output-format stream-json \
      --verbose \
      --setting-sources project \
      --strict-mcp-config \
      --no-session-persistence \
      --dangerously-skip-permissions \
      --max-budget-usd "${MAX_BUDGET_USD}" \
      "${plugin_args[@]}" \
      </dev/null >"${run_dir}/stream.jsonl" 2>"${run_dir}/stderr.log"
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
  local -a run_dirs=()
  local -i pid=0
  [[ ! -e "${out_dir}" ]] || die "${out_dir} exists: use a new out-dir"
  docker info --format '{{.ServerVersion}}' >/dev/null || die "the Docker daemon is not reachable: start it first"
  "${PYTHON}" "${BENCH_DIR}/score.py" check || die "PYTHON=${PYTHON} cannot run bench/score.py (it needs PyYAML)"
  mkdir -p "${out_dir}"
  {
    claude --version
    printf 'model: %s\n' "${MODEL}"
    for arm in "$@"; do
      printf 'arm %s: %s\n' "${arm%%=*}" "${arm#*=}"
    done
  } >"${out_dir}/versions.txt"
  for task_dir in "${TASKS_DIR}"/*/; do
    task_dir="${task_dir%/}"
    [[ -z "${TASKS:-}" || " ${TASKS} " == *" $(basename "${task_dir}") "* ]] || continue
    for ((run = 1; run <= runs; run++)); do
      pids=()
      run_dirs=()
      for arm in "$@"; do
        run_dirs+=("${out_dir}/${arm%%=*}/$(basename "${task_dir}")/${run}")
        run_one "${task_dir}" "${run_dirs[-1]}" "${arm#*=}" &
        pids+=("$!")
      done
      for pid in "${pids[@]}"; do
        wait "${pid}" || printf 'bench: a run of %s failed before claude started\n' "${task_dir}" >&2
      done
      "${PYTHON}" "${BENCH_DIR}/score.py" check "${run_dirs[@]}" ||
        die "stopped: a run gave no answer (usage limit or API error); rerun the batch in a new out-dir"
    done
  done
}

main "$@"
