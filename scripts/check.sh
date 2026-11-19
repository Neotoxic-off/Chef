#!/usr/bin/env bash
# Consistency checks for the chef plugin: index, agents, README badge, JSON manifests.
set -euo pipefail
shopt -s inherit_errexit nullglob

readonly INDEX_NAME="INDEX.md"
readonly BACKTICK=$'\x60'

die() {
  printf 'check: %s\n' "$*" >&2
  exit 1
}

reference_files() {
  local -r references_dir="$1"
  find "${references_dir}" -maxdepth 1 -name '*.md' ! -name "${INDEX_NAME}" -printf '%f\n' | sort
}

indexed_files() {
  local -r index_path="$1"
  grep -oE "${BACKTICK}[a-z0-9-]+\.md${BACKTICK}" "${index_path}" | tr -d "${BACKTICK}" | sort -u
}

check_index() {
  local -r references_dir="$1/skills/chef/references"
  local on_disk=""
  local indexed=""
  local missing_from_index=""
  local missing_on_disk=""
  on_disk="$(reference_files "${references_dir}")"
  indexed="$(indexed_files "${references_dir}/${INDEX_NAME}")"
  missing_from_index="$(comm -23 <(printf '%s\n' "${on_disk}") <(printf '%s\n' "${indexed}"))"
  missing_on_disk="$(comm -13 <(printf '%s\n' "${on_disk}") <(printf '%s\n' "${indexed}"))"
  [[ -z "${missing_from_index}" ]] || die "not listed in ${INDEX_NAME}: ${missing_from_index//$'\n'/ }"
  [[ -z "${missing_on_disk}" ]] || die "listed in ${INDEX_NAME} but missing: ${missing_on_disk//$'\n'/ }"
}

check_agent() {
  local -r agent_path="$1"
  local first_line=""
  local frontmatter=""
  local key=""
  first_line="$(head -n 1 "${agent_path}")"
  [[ "${first_line}" == "---" ]] || die "${agent_path}: no frontmatter"
  frontmatter="$(sed -n '2,/^---$/p' "${agent_path}")"
  for key in name description tools; do
    grep -qE "^${key}: ." <<<"${frontmatter}" || die "${agent_path}: missing '${key}:'"
  done
}

check_agents() {
  local -r agents_dir="$1/agents"
  local -a agent_paths=("${agents_dir}"/*.md)
  local agent_path=""
  ((${#agent_paths[@]} > 0)) || die "${agents_dir}: no agents"
  for agent_path in "${agent_paths[@]}"; do
    check_agent "${agent_path}"
  done
}

check_badge() {
  local -r root="$1"
  local on_disk=""
  local badge=""
  local -i actual_count=0
  on_disk="$(reference_files "${root}/skills/chef/references")"
  actual_count="$(wc -l <<<"${on_disk}")"
  if ! badge="$(grep -oE 'badge/references-[0-9]+' "${root}/README.md")"; then
    die "README.md has no references badge"
  fi
  [[ "${badge##*-}" == "${actual_count}" ]] || die "README badge says ${badge##*-} references, found ${actual_count}"
}

check_json() {
  local -r root="$1"
  local json_path=""
  for json_path in "${root}"/.claude-plugin/*.json "${root}"/hooks/*.json; do
    jq empty "${json_path}" || die "${json_path}: invalid JSON"
  done
}

main() {
  local -r root="${1:-.}"
  check_index "${root}"
  check_agents "${root}"
  check_badge "${root}"
  check_json "${root}"
  printf 'check: all good\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
