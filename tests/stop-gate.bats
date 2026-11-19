setup() {
  source "${BATS_TEST_DIRNAME}/../skills/transform/scripts/stop-gate.sh"
  CLAUDE_PROJECT_DIR="$(mktemp -d)"
  export CLAUDE_PROJECT_DIR
  plan="${CLAUDE_PROJECT_DIR}/TRANSFORM.md"
}

teardown() {
  rm -rf "${CLAUDE_PROJECT_DIR}"
}

@test "allows stop when there is no TRANSFORM.md" {
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "blocks stop while a batch is in progress" {
  printf -- '- [x] Batch 1: bump SDK\n- [~] Batch 2: fix nullable warnings\n- [ ] Batch 3: tests\n' > "${plan}"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"marked [~]"* ]]
}

@test "reads the plan from the working directory without CLAUDE_PROJECT_DIR" {
  printf -- '- [~] Batch 1: bump SDK\n' > "${plan}"
  cd "${CLAUDE_PROJECT_DIR}"
  CLAUDE_PROJECT_DIR="" run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
}

@test "allows stop when the hook already continued the turn" {
  printf -- '- [~] Batch 1: bump SDK\n' > "${plan}"
  run main <<<'{"hook_event_name":"Stop", "stop_hook_active": true}'
  [ "${status}" -eq 0 ]
}

@test "allows stop when every started batch is validated" {
  printf -- '- [x] Batch 1: bump SDK\r\n- [x] Batch 2: fix warnings\r\n- [ ] Batch 3: tests\r\n' > "${plan}"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "the script run as the hook blocks with status 2" {
  printf -- '- [~] Batch 1: bump SDK\n' > "${plan}"
  run bash "${BATS_TEST_DIRNAME}/../skills/transform/scripts/stop-gate.sh" <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"marked [~]"* ]]
}
