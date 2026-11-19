setup() {
  source "${BATS_TEST_DIRNAME}/../scripts/check.sh"
  root="$(mktemp -d)"
  mkdir -p "${root}/skills/chef/references" "${root}/agents" "${root}/.claude-plugin" "${root}/hooks"
  printf '| Go | `go.md` |\n' > "${root}/skills/chef/references/INDEX.md"
  printf '# Go\n' > "${root}/skills/chef/references/go.md"
  printf -- '---\nname: chef\ndescription: Habits.\n---\n' > "${root}/skills/chef/SKILL.md"
  printf -- '---\nname: reviewer\ndescription: Reviews.\ntools: Read\n---\n' > "${root}/agents/reviewer.md"
  printf 'badge/references-1-D97757\n' > "${root}/README.md"
  printf '{}\n' > "${root}/.claude-plugin/plugin.json"
  printf '{}\n' > "${root}/hooks/hooks.json"
}

teardown() {
  rm -rf "${root}"
}

@test "main passes on a consistent plugin" {
  run main "${root}"
  [ "${status}" -eq 0 ]
}

@test "check_index fails when a reference is not indexed" {
  printf '# Rust\n' > "${root}/skills/chef/references/rust.md"
  run check_index "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"not listed in INDEX.md: rust.md"* ]]
}

@test "check_index fails when an indexed file is missing" {
  rm "${root}/skills/chef/references/go.md"
  run check_index "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"listed in INDEX.md but missing: go.md"* ]]
}

@test "check_agents fails when tools is missing" {
  printf -- '---\nname: x\ndescription: X.\n---\n' > "${root}/agents/x.md"
  run check_agents "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"missing 'tools:'"* ]]
}

@test "check_agents fails without frontmatter" {
  printf '# x\n' > "${root}/agents/x.md"
  run check_agents "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"no frontmatter"* ]]
}

@test "check_agents fails when tools is only in the body" {
  printf -- '---\nname: x\ndescription: X.\n---\ntools: Read\n' > "${root}/agents/x.md"
  run check_agents "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"missing 'tools:'"* ]]
}

@test "check_agents fails when there are no agents" {
  rm "${root}/agents/reviewer.md"
  run check_agents "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"no agents"* ]]
}

@test "check_skills fails when description is missing" {
  mkdir -p "${root}/skills/transform"
  printf -- '---
name: transform
---
' > "${root}/skills/transform/SKILL.md"
  run check_skills "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"transform/SKILL.md: missing 'description:'"* ]]
}

@test "check_skills fails when there are no skills" {
  rm "${root}/skills/chef/SKILL.md"
  run check_skills "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"no skills"* ]]
}

@test "check_badge fails when the README has no badge" {
  printf '# Chef\n' > "${root}/README.md"
  run check_badge "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"has no references badge"* ]]
}

@test "check_badge fails when the README count is stale" {
  printf 'badge/references-2-D97757\n' > "${root}/README.md"
  run check_badge "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"says 2 references, found 1"* ]]
}

@test "check_json fails on invalid JSON" {
  printf '{' > "${root}/hooks/hooks.json"
  run check_json "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"invalid JSON"* ]]
}

@test "check_sizes fails when SKILL.md is over budget" {
  head -c 10753 /dev/zero > "${root}/skills/chef/SKILL.md"
  run check_sizes "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"SKILL.md: 10753 bytes, budget is 10752"* ]]
}

@test "check_sizes fails when a reference is over budget" {
  head -c 6145 /dev/zero > "${root}/skills/chef/references/go.md"
  run check_sizes "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"go.md: 6145 bytes, budget is 6144"* ]]
}

@test "check_sizes passes at exactly the budget" {
  head -c 10752 /dev/zero > "${root}/skills/chef/SKILL.md"
  head -c 6144 /dev/zero > "${root}/skills/chef/references/go.md"
  run check_sizes "${root}"
  [ "${status}" -eq 0 ]
}

@test "check_sizes fails when team.md is over budget" {
  head -c 6145 /dev/zero > "${root}/skills/chef/team.md"
  run check_sizes "${root}"
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"team.md: 6145 bytes, budget is 6144"* ]]
}
