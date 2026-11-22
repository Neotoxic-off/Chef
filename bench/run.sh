#!/usr/bin/env bash
# Runs every task in bench/tasks once per arm and per run, in a fresh git folder each time.
# Usage: bench/run.sh <out-dir> <runs> <arm>=<plugin-dir, a .md file used as CLAUDE.md, or empty> ...
# Example: bench/run.sh /tmp/bench 2 none= old=/tmp/chef-0.8.1 new=/tmp/chef-new
# Set TASKS="python bugfix" to run only those tasks. Needs Docker running and PYTHON (default: python)
# able to import bench/score.py; the batch stops at the first run that gave no answer (usage limit).
# RESUME=1 reuses an existing out-dir: runs that gave an answer are kept, the others are run again.
# MAX_TOTAL_USD=20 stops before the next batch once the streams of the out-dir cost that much.
set -euo pipefail
shopt -s inherit_errexit nullglob

readonly MODEL="claude-sonnet-5-5"
readonly MAX_BUDGET_USD="1"
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BENCH_DIR
readonly TASKS_DIR="${BENCH_DIR}/tasks"
readonly PYTHON="${PYTHON:-python}"
# Exit code of `score.py budget` when the cap is reached; any other failure is a crash.
readonly BUDGET_REACHED=3

die() {
  printf 'bench: %s\n' "$*" >&2
  exit 1
}

check_budget() {
  local -r out_dir="$1"
  local -i status=0
  [[ -n "${MAX_TOTAL_USD:-}" ]] || return 0
  "${PYTHON}" "${BENCH_DIR}/score.py" budget "${out_dir}" "${MAX_TOTAL_USD}" || status=$?
  ((status != BUDGET_REACHED)) || die "stopped: MAX_TOTAL_USD=${MAX_TOTAL_USD} reached; raise it and rerun with RESUME=1"
  ((status == 0)) || die "stopped: score.py budget failed (exit ${status}) on ${out_dir}"
}

# Pull the images the references run before any arm starts, so no arm pays for a first pull and the
# arms that run in parallel compare on a warm cache.
pull_images() {
  local -r images_file="${BENCH_DIR}/../scripts/container-images.txt"
  local image=""
  while read -r image; do
    [[ -n "${image}" ]] || continue
    docker pull --quiet "${image}" >/dev/null || die "cannot pull ${image}, listed in ${images_file}"
  done <"${images_file}"
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
  if [[ -e "${run_dir}" ]]; then
    [[ "${RESUME:-}" == 1 ]] || die "${run_dir} exists: use a new out-dir"
    if "${PYTHON}" "${BENCH_DIR}/score.py" check "${run_dir}"; then
      printf 'bench: %s gave an answer, kept\n' "${run_dir}" >&2
      return 0
    fi
    rm -rf "${run_dir}"
  fi
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

stop_runs() {
  trap - INT TERM
  local -a groups=()
  local pid=""
  for pid in $(jobs -p); do
    groups+=("-${pid}")
  done
  # set -m gives each background run its own process group, so this reaches claude and its children.
  ((${#groups[@]} == 0)) || kill -TERM -- "${groups[@]}" 2>/dev/null ||
    printf 'bench: some runs had already ended\n' >&2
  die "interrupted: every run was stopped"
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
  [[ -z "${MAX_TOTAL_USD:-}" || "${MAX_TOTAL_USD}" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
    die "MAX_TOTAL_USD must be a number of dollars, got '${MAX_TOTAL_USD}'"
  local task_dir=""
  local -i run=0
  local -a pids=()
  local -a run_dirs=()
  local -i pid=0
  [[ "${RESUME:-}" == 1 || ! -e "${out_dir}" ]] || die "${out_dir} exists: use a new out-dir, or RESUME=1"
  docker info --format '{{.ServerVersion}}' >/dev/null || die "the Docker daemon is not reachable: start it first"
  pull_images
  "${PYTHON}" "${BENCH_DIR}/score.py" check || die "PYTHON=${PYTHON} cannot run bench/score.py (it needs PyYAML)"
  local kept=""
  for arm in "$@"; do
    # The kept runs of an arm must come from the plugin dir it runs now: versions.txt names the last one.
    kept="$(awk -v line="arm ${arm%%=*}: " 'index($0, line) == 1 { last = $0 } END { print last }' \
      "${out_dir}/versions.txt" 2>/dev/null || true)"
    [[ -z "${kept}" || "${kept}" == "arm ${arm%%=*}: ${arm#*=}" ]] ||
      die "RESUME=1: ${out_dir} kept runs of '${kept}', not of ${arm}; use a new out-dir"
  done
  mkdir -p "${out_dir}"
  {
    claude --version
    printf 'model: %s\n' "${MODEL}"
    for arm in "$@"; do
      printf 'arm %s: %s\n' "${arm%%=*}" "${arm#*=}"
    done
  } >>"${out_dir}/versions.txt"
  set -m
  trap stop_runs INT TERM
  for task_dir in "${TASKS_DIR}"/*/; do
    task_dir="${task_dir%/}"
    [[ -z "${TASKS:-}" || " ${TASKS} " == *" $(basename "${task_dir}") "* ]] || continue
    for ((run = 1; run <= runs; run++)); do
      check_budget "${out_dir}"
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
        die "stopped: a run gave no answer (usage limit or API error); rerun with RESUME=1 once it is fixed"
    done
  done
}

main "$@"
