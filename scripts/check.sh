#!/usr/bin/env bash
# Consistency checks for the chef plugin: index, agents, skills, README badge, JSON manifests.
set -euo pipefail
shopt -s inherit_errexit nullglob

readonly INDEX_NAME="INDEX.md"
readonly BACKTICK=$'\x60'
# Every byte of these files is written into the model context, so growth costs tokens on every task.
readonly MAX_SKILL_BYTES=10752
readonly MAX_REFERENCE_BYTES=6144

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

check_frontmatter() {
  local -r file_path="$1"
  shift
  local first_line=""
  local frontmatter=""
  local key=""
  first_line="$(head -n 1 "${file_path}")"
  [[ "${first_line}" == "---" ]] || die "${file_path}: no frontmatter"
  frontmatter="$(sed -n '2,/^---$/p' "${file_path}")"
  for key in "$@"; do
    grep -qE "^${key}: ." <<<"${frontmatter}" || die "${file_path}: missing '${key}:'"
  done
}

check_agents() {
  local -r agents_dir="$1/agents"
  local -a agent_paths=("${agents_dir}"/*.md)
  local agent_path=""
  ((${#agent_paths[@]} > 0)) || die "${agents_dir}: no agents"
  for agent_path in "${agent_paths[@]}"; do
    check_frontmatter "${agent_path}" name description tools
  done
}

check_skills() {
  local -r skills_dir="$1/skills"
  local -a skill_paths=("${skills_dir}"/*/SKILL.md)
  local skill_path=""
  ((${#skill_paths[@]} > 0)) || die "${skills_dir}: no skills"
  for skill_path in "${skill_paths[@]}"; do
    check_frontmatter "${skill_path}" name description
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

check_size() {
  local -r file_path="$1"
  local -ri max_bytes="$2"
  local -i size=0
  size="$(wc -c <"${file_path}")"
  ((size <= max_bytes)) || die "${file_path}: ${size} bytes, budget is ${max_bytes}"
}

check_sizes() {
  local -r root="$1"
  local reference_path=""
  check_size "${root}/skills/chef/SKILL.md" "${MAX_SKILL_BYTES}"
  [[ ! -f "${root}/skills/chef/team.md" ]] || check_size "${root}/skills/chef/team.md" "${MAX_REFERENCE_BYTES}"
  for reference_path in "${root}"/skills/chef/references/*.md; do
    check_size "${reference_path}" "${MAX_REFERENCE_BYTES}"
  done
}

bullets() {
  sed -n '/^- /p' "$1"
}

core_rules() {
  sed -n '/^## Core rules$/,/^## /{/^- /p}' "$1"
}

check_agents_md() {
  local -r root="$1"
  local -r export_path="${root}/export/AGENTS.md"
  local core=""
  local exported=""
  [[ -f "${export_path}" ]] || die "${export_path}: missing"
  core="$(core_rules "${root}/skills/chef/SKILL.md")"
  [[ -n "${core}" ]] || die "SKILL.md: no '## Core rules' bullets"
  exported="$(bullets "${export_path}")"
  [[ -n "${exported}" ]] || die "${export_path}: no rules"
  [[ "${core}" == "${exported}" ]] || die "export/AGENTS.md rules differ from SKILL.md '## Core rules'"
}

check_version() {
  local -r root="$1"
  local manifest_version=""
  local changelog_heading=""
  manifest_version="$(jq -r .version "${root}/.claude-plugin/plugin.json")"
  changelog_heading="$(grep -m1 -oE '^## [0-9]+\.[0-9]+\.[0-9]+' "${root}/CHANGELOG.md")" || die "CHANGELOG.md: no version heading"
  [[ "${manifest_version}" == "${changelog_heading#\#\# }" ]] || die "plugin.json version ${manifest_version} differs from CHANGELOG ${changelog_heading#\#\# }"
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
  check_skills "${root}"
  check_badge "${root}"
  check_sizes "${root}"
  check_agents_md "${root}"
  check_version "${root}"
  check_json "${root}"
  printf 'check: all good\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
