setup() {
  PINNED_SHA="3d3c42e5aac5ba805825da76410c181273ba90b1"
  source "${BATS_TEST_DIRNAME}/../hooks/pin-gate.sh"
  CLAUDE_PROJECT_DIR="$(mktemp -d)"
  export CLAUDE_PROJECT_DIR
  workflows="${CLAUDE_PROJECT_DIR}/.github/workflows"
  mkdir -p "${workflows}"
}

teardown() {
  rm -rf "${CLAUDE_PROJECT_DIR}"
}

git_in_project() {
  git -C "${CLAUDE_PROJECT_DIR}" -c user.name=test -c user.email=test@example.com -c commit.gpgsign=false "$@"
}

@test "allows stop when every action is pinned to a commit SHA" {
  printf 'steps:\n  - uses: actions/checkout@%s # v7.0.1\n  - uses: "actions/setup-node@%s"\n' "${PINNED_SHA}" "${PINNED_SHA}" > "${workflows}/ci.yml"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "blocks stop when an action is pinned to a tag" {
  printf 'steps:\n  - uses: actions/checkout@%s\n  - uses: actions/setup-node@v4 # latest\n' "${PINNED_SHA}" > "${workflows}/ci.yaml"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *".github/workflows/ci.yaml:3: actions/setup-node@v4"* ]]
  [[ "${output}" == *"gh api repos/OWNER/REPO/commits/TAG --jq .sha"* ]]
}

@test "blocks stop when a reusable workflow is pinned to a branch" {
  printf 'jobs:\n  call:\n    uses: org/repo/.github/workflows/build.yml@main\r\n' > "${workflows}/ci.yml"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"ci.yml:3: org/repo/.github/workflows/build.yml@main"* ]]
}

@test "skips local and docker actions" {
  printf 'steps:\n  - uses: ./.github/actions/setup\n  - uses: docker://alpine:3.20\n' > "${workflows}/ci.yml"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "allows stop when an unchanged legacy workflow uses a tag" {
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/legacy.yml"
  git_in_project init --quiet
  git_in_project add .
  git_in_project commit --quiet -m "legacy"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "blocks stop when a committed workflow is changed to use a tag" {
  printf 'steps:\n  - uses: actions/checkout@%s\n' "${PINNED_SHA}" > "${workflows}/ci.yml"
  git_in_project init --quiet
  git_in_project add .
  git_in_project commit --quiet -m "ci"
  printf '  - uses: actions/cache@v4\n' >> "${workflows}/ci.yml"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"ci.yml:3: actions/cache@v4"* ]]
}

@test "blocks stop when an untracked workflow uses a tag" {
  git_in_project init --quiet
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/new.yml"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
}

@test "allows stop when the hook already continued the turn" {
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/ci.yml"
  run main <<<'{"hook_event_name":"Stop", "stop_hook_active": true}'
  [ "${status}" -eq 0 ]
}

@test "allows stop when the project has no workflows" {
  rm -rf "${CLAUDE_PROJECT_DIR}/.github"
  run main <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 0 ]
}

@test "the script run as the hook blocks with status 2" {
  printf 'steps:\n  - uses: actions/checkout@v4\n' > "${workflows}/ci.yml"
  run bash "${BATS_TEST_DIRNAME}/../hooks/pin-gate.sh" <<<'{"hook_event_name":"Stop","stop_hook_active":false}'
  [ "${status}" -eq 2 ]
  [[ "${output}" == *"not pinned to a full commit SHA"* ]]
}
