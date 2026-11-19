setup() {
  PINNED_SHA="3d3c42e5aac5ba805825da76410c181273ba90b1"
  source "${BATS_TEST_DIRNAME}/../hooks/pin-gate.sh"
  CLAUDE_PROJECT_DIR="$(mktemp -d)"
  CHEF_PIN_GATE_DIR="${CLAUDE_PROJECT_DIR}/state"
  export CLAUDE_PROJECT_DIR CHEF_PIN_GATE_DIR
  mkdir -p "${CHEF_PIN_GATE_DIR}"
  workflows="${CLAUDE_PROJECT_DIR}/.github/workflows"
  mkdir -p "${workflows}"
  stop_input='{"session_id":"s1","hook_event_name":"Stop","stop_hook_active":false}'
}

teardown() {
  rm -rf "${CLAUDE_PROJECT_DIR}"
}

edit_input() {
  printf '{"session_id":"s1","hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"%s","old_string":"a"}}' "$1"
}

record_edit() {
  main record <<<"$(edit_input "$1")"
}

@test "allows stop when every edited action is pinned to a commit SHA" {
  printf 'steps:\n  - uses: actions/checkout@%s # v7.0.1\n  - uses: "actions/setup-node@%s"\n' "${PINNED_SHA}" "${PINNED_SHA}" > "${workflows}/ci.yml"
  record_edit "${workflows}/ci.yml"
  run main check <<<"${stop_input}"
  [ "${status}" -eq 0 ]
}

@test "blocks stop when an edited workflow pins an action to a tag" {
  printf 'steps:\n  - uses: actions/checkout@%s\n  - uses: actions/setup-node@v4 # latest\n' "${PINNED_SHA}" > "${workflows}/ci.yaml"
  record_edit "${workflows}/ci.yaml"
  run main check <<<"${stop_input}"
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"ci.yaml:3: actions/setup-node@v4"* ]]
  [[ "${output}" == *"gh api repos/OWNER/REPO/commits/TAG --jq .sha"* ]]
}

@test "blocks stop when an edited reusable workflow is pinned to a branch" {
  printf 'jobs:\n  call:\n    uses: org/repo/.github/workflows/build.yml@main\r\n' > "${workflows}/ci.yml"
  record_edit "${workflows}/ci.yml"
  run main check <<<"${stop_input}"
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"ci.yml:3: org/repo/.github/workflows/build.yml@main"* ]]
}

@test "skips local and docker actions" {
  printf 'steps:\n  - uses: ./.github/actions/setup\n  - uses: docker://alpine:3.20\n' > "${workflows}/ci.yml"
  record_edit "${workflows}/ci.yml"
  run main check <<<"${stop_input}"
  [ "${status}" -eq 0 ]
}

@test "ignores workflows Claude did not edit" {
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/legacy.yml"
  run main check <<<"${stop_input}"
  [ "${status}" -eq 0 ]
}

@test "does not record files outside .github/workflows" {
  printf 'uses: actions/checkout@v4\n' > "${CLAUDE_PROJECT_DIR}/notes.yml"
  record_edit "${CLAUDE_PROJECT_DIR}/notes.yml"
  [ ! -f "${CHEF_PIN_GATE_DIR}/chef-pin-gate-s1" ]
}

@test "records a Windows path with escaped backslashes" {
  run main record <<<'{"session_id":"s1","tool_input":{"file_path":"D:\\repo\\.github\\workflows\\ci.yml"}}'
  [ "${status}" -eq 0 ]
  [ "$(cat "${CHEF_PIN_GATE_DIR}/chef-pin-gate-s1")" = 'D:\repo\.github\workflows\ci.yml' ]
}

@test "blocks once, then allows and stops checking for the session" {
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/ci.yml"
  record_edit "${workflows}/ci.yml"
  run main check <<<"${stop_input}"
  [ "${status}" -eq 2 ]
  run main check <<<'{"session_id":"s1","hook_event_name":"Stop","stop_hook_active":true}'
  [ "${status}" -eq 0 ]
  run main check <<<"${stop_input}"
  [ "${status}" -eq 0 ]
}

@test "keeps sessions apart" {
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/ci.yml"
  record_edit "${workflows}/ci.yml"
  run main check <<<'{"session_id":"s2","hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "skips a recorded workflow that was deleted" {
  record_edit "${workflows}/gone.yml"
  run main check <<<"${stop_input}"
  [ "${status}" -eq 0 ]
}

@test "unknown mode fails" {
  run main nope <<<'{}'
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"unknown mode nope"* ]]
}

@test "the script run as the hook records then blocks with status 2" {
  local -r script="${BATS_TEST_DIRNAME}/../hooks/pin-gate.sh"
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/ci.yml"
  bash "${script}" record <<<"$(edit_input "${workflows}/ci.yml")"
  run bash "${script}" check <<<"${stop_input}"
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"not pinned to a full commit SHA"* ]]
}
