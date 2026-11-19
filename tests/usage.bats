setup() {
  source "${BATS_TEST_DIRNAME}/../skills/status/scripts/usage.sh"
  CLAUDE_PROJECT_DIR="$(mktemp -d)"
  export CLAUDE_PROJECT_DIR
  transcript="${CLAUDE_PROJECT_DIR}/session.jsonl"
  cat > "${transcript}" <<'EOF'
{"type":"user","message":{"role":"user","content":"hi"},"timestamp":"2026-11-19T10:00:00.000Z"}
{"message":{"model":"m","id":"msg_A","role":"assistant","content":[{"type":"thinking"}],"usage":{"input_tokens":10,"cache_creation_input_tokens":100,"cache_read_input_tokens":1000,"output_tokens":5,"iterations":[{"input_tokens":10,"output_tokens":5}]}},"type":"assistant","timestamp":"2026-11-19T10:00:05.000Z"}
{"message":{"model":"m","id":"msg_A","role":"assistant","content":[{"type":"tool_use","id":"toolu_1","name":"Agent","input":{}}],"usage":{"input_tokens":10,"cache_creation_input_tokens":100,"cache_read_input_tokens":1000,"output_tokens":5}},"type":"assistant","timestamp":"2026-11-19T10:00:06.000Z"}
{"message":{"model":"m","id":"msg_B","role":"assistant","content":[{"type":"tool_use","id":"toolu_2","name":"Task","input":{}},{"type":"tool_use","id":"toolu_3","name":"Read","input":{}}],"usage":{"input_tokens":1,"cache_creation_input_tokens":2,"cache_read_input_tokens":3,"output_tokens":4}},"type":"assistant","timestamp":"2026-11-19T11:01:01.000Z"}
EOF
}

teardown() {
  rm -rf "${CLAUDE_PROJECT_DIR}"
}

@test "sums usage once per message id across streamed lines" {
  run usage_report "${transcript}"
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"tokens: 11 input, 9 output, 1003 cache read, 102 cache write (1125 total)"* ]]
}

@test "counts Agent and Task tool calls as subagents" {
  run usage_report "${transcript}"
  [[ "${output}" == *"subagents spawned: 2"* ]]
}

@test "reports elapsed time between first and last timestamp" {
  run usage_report "${transcript}"
  [[ "${output}" == *"elapsed: 1h 01m 01s"* ]]
}

@test "adds the session's subagent transcripts to the totals" {
  mkdir -p "${CLAUDE_PROJECT_DIR}/session/subagents"
  printf '%s\n' '{"message":{"id":"msg_C","role":"assistant","usage":{"input_tokens":1000,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0}},"timestamp":"2026-11-19T10:30:00.000Z"}' > "${CLAUDE_PROJECT_DIR}/session/subagents/agent-1.jsonl"
  run main "${transcript}"
  [[ "${output}" == *"tokens: 1011 input"* ]]
}

@test "missing transcript fails with a clear error" {
  run main "${CLAUDE_PROJECT_DIR}/nope.jsonl"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"transcript not found"* ]]
}

@test "no transcript folder fails with a clear error" {
  CLAUDE_CONFIG_DIR="${CLAUDE_PROJECT_DIR}/config" run bash "${BATS_TEST_DIRNAME}/../skills/status/scripts/usage.sh"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"no transcript found"* ]]
}

@test "finds the newest transcript in the project folder" {
  local folder=""
  folder="${CLAUDE_PROJECT_DIR}/config/projects/$(transcript_folder_name "${CLAUDE_PROJECT_DIR}")"
  mkdir -p "${folder}"
  cp "${transcript}" "${folder}/old.jsonl"
  touch -d '2020-01-01' "${folder}/old.jsonl"
  printf '%s\n' '{"message":{"id":"msg_N","role":"assistant","usage":{"input_tokens":7,"output_tokens":0}}}' > "${folder}/new.jsonl"
  CLAUDE_CONFIG_DIR="${CLAUDE_PROJECT_DIR}/config" run main
  [[ "${output}" == *"tokens: 7 input"* ]]
}

@test "folder name replaces every non-alphanumeric character" {
  run transcript_folder_name "/a/b.c_d"
  [[ "${output}" == *"b-c-d" ]]
}

@test "defaults to level full with no overrides and no decisions" {
  run main "${transcript}"
  [[ "${output}" == *"level: full (default)"* ]]
  [[ "${output}" == *"overrides: none"* ]]
  [[ "${output}" == *"decisions: 0"* ]]
}

@test "reads level, overrides and decisions from .chef.md" {
  printf 'level: max\r\ncoverage: 80\r\nnote: x\r\n\r\n## Decisions\r\n- use bats\r\n- no jq\r\n\r\n## Other\r\n- not a decision\r\n' > "${CLAUDE_PROJECT_DIR}/.chef.md"
  run main "${transcript}"
  [[ "${output}" == *"level: max"* ]]
  [[ "${output}" == *"overrides: level: max, coverage: 80"* ]]
  [[ "${output}" == *"decisions: 2"* ]]
}

@test "detects stacks from marker files" {
  touch "${CLAUDE_PROJECT_DIR}/package.json" "${CLAUDE_PROJECT_DIR}/tsconfig.json" "${CLAUDE_PROJECT_DIR}/App.csproj" "${CLAUDE_PROJECT_DIR}/Dockerfile"
  run detected_stacks "${CLAUDE_PROJECT_DIR}"
  [ "${output}" = "stacks: typescript.md, csharp.md, docker.md" ]
}

@test "says when no stack is detected" {
  run detected_stacks "${CLAUDE_PROJECT_DIR}"
  [ "${output}" = "stacks: none detected" ]
}
