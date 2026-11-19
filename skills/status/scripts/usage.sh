#!/usr/bin/env bash
# Prints the /chef:status block: level and overrides from .chef.md, detected stacks, and the session token usage.
set -euo pipefail
shopt -s inherit_errexit nullglob

readonly SETTINGS_NAME=".chef.md"
readonly DEFAULT_LEVEL="full"
readonly OVERRIDE_PATTERN='^(level|strict|coverage|council):[[:space:]]*[^[:space:]]'
readonly SUBAGENTS_DIR_NAME="subagents"

die() {
  printf 'status: %s\n' "$*" >&2
  exit 1
}

project_dir() {
  printf '%s\n' "${CLAUDE_PROJECT_DIR:-${PWD}}"
}

# Claude Code names a project's transcript folder after its native path with every non-alphanumeric char as '-'.
transcript_folder_name() {
  local native_path="$1"
  if command -v cygpath >/dev/null; then native_path="$(cygpath -w "${native_path}")"; fi
  printf '%s\n' "${native_path//[^[:alnum:]]/-}"
}

transcript_folder() {
  local root="" folder_name=""
  root="$(project_dir)"
  folder_name="$(transcript_folder_name "${root}")"
  printf '%s/projects/%s\n' "${CLAUDE_CONFIG_DIR:-${HOME}/.claude}" "${folder_name}"
}

# CHEF_SESSION_ID (set by the skill from ${CLAUDE_SESSION_ID}) picks this session even when another one wrote later.
session_transcript() {
  local folder=""
  folder="$(transcript_folder)"
  if [[ -z "${CHEF_SESSION_ID:-}" ]]; then
    newest_transcript "${folder}"
    return
  fi
  [[ -f "${folder}/${CHEF_SESSION_ID}.jsonl" ]] || die "no transcript for session ${CHEF_SESSION_ID} in ${folder}"
  printf '%s\n' "${folder}/${CHEF_SESSION_ID}.jsonl"
}

newest_transcript() {
  local -r folder="$1"
  local newest=""
  local candidate=""
  for candidate in "${folder}"/*.jsonl; do
    if [[ -z "${newest}" || "${candidate}" -nt "${newest}" ]]; then newest="${candidate}"; fi
  done
  [[ -n "${newest}" ]] || die "no transcript found in ${folder}"
  printf '%s\n' "${newest}"
}

setting_lines() {
  local -r settings_path="$1"
  [[ -f "${settings_path}" ]] || return 0
  awk -v pattern="${OVERRIDE_PATTERN}" '{ sub(/\r$/, "") } $0 ~ pattern' "${settings_path}"
}

level_line() {
  local -r overrides="$1"
  local level=""
  level="$(sed -n 's/^level:[[:space:]]*//p' <<<"${overrides}" | head -n 1)"
  if [[ -z "${level}" ]]; then level="${DEFAULT_LEVEL} (default)"; fi
  printf 'level: %s\n' "${level}"
}

overrides_line() {
  local -r overrides="$1"
  local joined="none"
  if [[ -n "${overrides}" ]]; then joined="$(paste -sd, - <<<"${overrides}" | sed 's/,/, /g')"; fi
  printf 'overrides: %s\n' "${joined}"
}

decision_count() {
  local -r settings_path="$1"
  [[ -f "${settings_path}" ]] || { printf '0\n'; return 0; }
  awk '{ sub(/\r$/, "") } /^## /{in_decisions = ($0 ~ /^## Decisions[[:space:]]*$/); next} in_decisions && /^[-*] /{count++} END{print count + 0}' "${settings_path}"
}

detected_stacks() {
  local -r root="$1"
  local -a stacks=()
  local -a csproj_paths=("${root}"/*.csproj)
  if [[ -f "${root}/package.json" && -f "${root}/tsconfig.json" ]]; then stacks+=("typescript.md"); fi
  if [[ -f "${root}/pyproject.toml" ]]; then stacks+=("python.md"); fi
  if ((${#csproj_paths[@]} > 0)); then stacks+=("csharp.md"); fi
  if [[ -f "${root}/go.mod" ]]; then stacks+=("go.md"); fi
  if [[ -f "${root}/Cargo.toml" ]]; then stacks+=("rust.md"); fi
  if [[ -f "${root}/Dockerfile" ]]; then stacks+=("docker.md"); fi
  if [[ -d "${root}/.github/workflows" ]]; then stacks+=("ci.md"); fi
  if ((${#stacks[@]} == 0)); then stacks=("none detected"); fi
  local joined=""
  printf -v joined '%s, ' "${stacks[@]}"
  printf 'stacks: %s\n' "${joined%, }"
}

# Streamed replies write one line per content block, each repeating the message id and usage: count each id once.
usage_report() {
  awk '
    function first_number(text, key,    found) {
      if (!match(text, "\"" key "\":[0-9]+")) return 0
      found = substr(text, RSTART, RLENGTH)
      sub(/.*:/, "", found)
      return found + 0
    }
    function epoch_seconds(stamp,    year, month, day, era_days) {
      year = substr(stamp, 1, 4) + 0; month = substr(stamp, 6, 2) + 0; day = substr(stamp, 9, 2) + 0
      if (month <= 2) { year--; month += 12 }
      era_days = 365 * year + int(year / 4) - int(year / 100) + int(year / 400) + int((153 * (month - 3) + 2) / 5) + day
      return era_days * 86400 + substr(stamp, 12, 2) * 3600 + substr(stamp, 15, 2) * 60 + substr(stamp, 18, 2)
    }
    match($0, /"timestamp":"[0-9T:.Z-]+"/) {
      stamp = substr($0, RSTART + 13, RLENGTH - 14)
      if (first == "" || stamp < first) first = stamp
      if (stamp > last) last = stamp
    }
    /"role":"assistant"/ && match($0, /"id":"msg_[A-Za-z0-9]+"/) {
      message_id = substr($0, RSTART, RLENGTH)
      if (!(message_id in seen_messages) && (start = index($0, "\"usage\":{"))) {
        seen_messages[message_id] = 1
        usage = substr($0, start)
        input += first_number(usage, "input_tokens")
        output += first_number(usage, "output_tokens")
        cache_read += first_number(usage, "cache_read_input_tokens")
        cache_write += first_number(usage, "cache_creation_input_tokens")
      }
      rest = $0
      while (match(rest, /"type":"tool_use","id":"[^"]+","name":"(Agent|Task)"/)) {
        seen_agents[substr(rest, RSTART, RLENGTH)] = 1
        rest = substr(rest, RSTART + RLENGTH)
      }
    }
    END {
      for (call in seen_agents) agents++
      elapsed = (first == "") ? 0 : epoch_seconds(last) - epoch_seconds(first)
      printf "tokens: %.0f input, %.0f output, %.0f cache read, %.0f cache write (%.0f total)\n", input, output, cache_read, cache_write, input + output + cache_read + cache_write
      printf "subagents spawned: %d\n", agents
      printf "elapsed: %dh %02dm %02ds\n", int(elapsed / 3600), int(elapsed % 3600 / 60), elapsed % 60
    }
  ' "$@"
}

main() {
  local transcript_path="${1:-}"
  if [[ -z "${transcript_path}" ]]; then transcript_path="$(session_transcript)"; fi
  [[ -f "${transcript_path}" ]] || die "transcript not found: ${transcript_path}"
  local -a transcript_paths=("${transcript_path}" "${transcript_path%.jsonl}/${SUBAGENTS_DIR_NAME}"/*.jsonl)
  local root=""
  local overrides=""
  local decisions=""
  root="$(project_dir)"
  overrides="$(setting_lines "${root}/${SETTINGS_NAME}")"
  decisions="$(decision_count "${root}/${SETTINGS_NAME}")"
  printf 'chef status\n'
  level_line "${overrides}"
  overrides_line "${overrides}"
  printf 'decisions: %s\n' "${decisions}"
  detected_stacks "${root}"
  usage_report "${transcript_paths[@]}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
