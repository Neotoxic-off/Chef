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
  printf -- 'Target: .NET 10\r\n## Council\r\n- [x] Batch 1: bump SDK\r\n- [x] Batch 2: fix warnings\r\n- [ ] Batch 3: tests\r\n' > "${plan}"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "the script run as the hook blocks with status 2" {
  printf -- '- [~] Batch 1: bump SDK\n' > "${plan}"
  run bash "${BATS_TEST_DIRNAME}/../skills/transform/scripts/stop-gate.sh" <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"marked [~]"* ]]
}

git_in_project() {
  git -C "${CLAUDE_PROJECT_DIR}" -c user.name=test -c user.email=test@example.com -c commit.gpgsign=false "$@"
}

commit_batch() {
  git_in_project commit --quiet --allow-empty -m "$1"
}

@test "blocks stop when a batch is ticked and the plan has no council section" {
  printf -- 'Target: Python 3.13
- [x] Batch 1: bump
' > "${plan}"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"## Council"* ]]
}

@test "blocks stop when a batch is ticked and the plan has no target line" {
  printf -- '## Council
- [x] Batch 1: bump
' > "${plan}"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"Target:"* ]]
}

@test "allows stop without council or target while no batch is ticked" {
  printf -- '- [ ] Batch 1: bump
' > "${plan}"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "blocks stop when more batches are ticked than committed" {
  printf -- 'Target: Python 3.13
## Council
- [x] Batch 1: bump
- [x] Batch 2: fix
' > "${plan}"
  git_in_project init --quiet
  commit_batch "chore: transform plan for py313"
  commit_batch "build: transform batch 1: bump"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"One commit per batch"* ]]
}

@test "blocks stop when batches are ticked in a repo with no commits" {
  printf -- 'Target: Python 3.13
## Council
- [x] Batch 1: bump
' > "${plan}"
  git_in_project init --quiet
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"One commit per batch"* ]]
}

@test "allows stop when every ticked batch has its commit" {
  printf -- 'Target: Python 3.13
## Council
- [x] Batch 1: bump
- [x] Batch 2: fix
' > "${plan}"
  git_in_project init --quiet
  commit_batch "build: transform batch 1: bump"
  commit_batch "fix: transform batch 2: fix"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "allows stop on a missing commit when the hook already continued the turn" {
  printf -- 'Target: Python 3.13
## Council
- [x] Batch 1: bump
' > "${plan}"
  git_in_project init --quiet
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":true}'
  [ "${status}" -eq 0 ]
}

@test "ignores batch commits made before this plan was committed" {
  printf -- 'Target: Python 3.13
## Council
- [x] Batch 1: bump
' > "${plan}"
  git_in_project init --quiet
  commit_batch "build: transform batch 1: earlier transform"
  git_in_project add TRANSFORM.md
  commit_batch "chore: transform plan for py313"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"One commit per batch"* ]]
}
