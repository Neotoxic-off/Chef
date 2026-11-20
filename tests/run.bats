setup() {
  stub_dir="$(mktemp -d)"
  out_dir="$(mktemp -d)/out"
  cat > "${stub_dir}/claude" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "--version" ]]; then
  echo "stub"
  exit 0
fi
echo '{"type":"system"}'
echo "${STUB_RESULT}"
EOF
  cat > "${stub_dir}/docker" <<'EOF'
#!/usr/bin/env bash
[[ "${STUB_DOCKER_UP}" == "yes" ]] && echo "29.0.0"
[[ "${STUB_DOCKER_UP}" == "yes" ]]
EOF
  chmod +x "${stub_dir}/claude" "${stub_dir}/docker"
  PATH="${stub_dir}:${PATH}"
  STUB_DOCKER_UP="yes"
  STUB_RESULT='{"type":"result","subtype":"success","is_error":false,"terminal_reason":"completed","total_cost_usd":0.01}'
  TASKS="python go"
  export PATH STUB_DOCKER_UP STUB_RESULT TASKS
}

teardown() {
  rm -rf "${stub_dir}" "$(dirname "${out_dir}")"
}

@test "runs every batch when every run completes" {
  run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 0 ]
  [ -f "${out_dir}/none/go/1/stream.jsonl" ]
  [ -f "${out_dir}/none/python/1/stream.jsonl" ]
}

@test "stops after the first batch when a run hits the usage limit" {
  STUB_RESULT='{"type":"result","subtype":"success","is_error":true,"terminal_reason":"api_error","api_error":"usage_limit_reached"}'
  run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 2 none=
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"API error: usage_limit_reached"* ]]
  [ ! -e "${out_dir}/none/go/2" ]
  [ ! -e "${out_dir}/none/python" ]
}

@test "starts no run when the Docker daemon is down" {
  STUB_DOCKER_UP="no"
  run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"Docker daemon is not reachable"* ]]
  [ ! -e "${out_dir}" ]
}
