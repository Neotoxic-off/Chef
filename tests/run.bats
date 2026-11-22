setup() {
  stub_dir="$(mktemp -d)"
  out_dir="$(mktemp -d)/out"
  cat > "${stub_dir}/claude" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "--version" ]]; then
  echo "stub"
  exit 0
fi
pwd >>"${STUB_LOG}"
if [[ -n "${STUB_HANG:-}" ]]; then
  echo "$$" >"${STUB_HANG}/$$"
  exec sleep 60
fi
echo '{"type":"system"}'
echo "${STUB_RESULT}"
EOF
  cat > "${stub_dir}/docker" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "pull" ]]; then
  echo "${*: -1}" >>"${STUB_PULLS}"
  [[ -z "${STUB_PULL_FAILS:-}" ]]
  exit
fi
[[ "${STUB_DOCKER_UP}" == "yes" ]] && echo "29.0.0"
[[ "${STUB_DOCKER_UP}" == "yes" ]]
EOF
  chmod +x "${stub_dir}/claude" "${stub_dir}/docker"
  PATH="${stub_dir}:${PATH}"
  STUB_DOCKER_UP="yes"
  STUB_RESULT='{"type":"result","subtype":"success","is_error":false,"terminal_reason":"completed","total_cost_usd":0.01}'
  TASKS="python go"
  STUB_LOG="${stub_dir}/claude.log"
  STUB_PULLS="${stub_dir}/pulls.log"
  export PATH STUB_DOCKER_UP STUB_RESULT TASKS STUB_LOG STUB_PULLS
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

@test "pulls every listed image before the first run" {
  run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 0 ]
  diff <(grep -v '^$' "${BATS_TEST_DIRNAME}/../scripts/container-images.txt") "${STUB_PULLS}"
}

@test "starts no run when an image cannot be pulled" {
  local first_image=""
  first_image="$(grep -m1 -v '^$' "${BATS_TEST_DIRNAME}/../scripts/container-images.txt")"
  STUB_PULL_FAILS=1 run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"cannot pull ${first_image}"* ]]
  [ ! -e "${STUB_LOG}" ]
}

@test "a crashing budget check is not reported as the cap" {
  cat > "${stub_dir}/python-stub" <<'EOF'
#!/usr/bin/env bash
[[ "$2" != "budget" ]] || exit 1
exec python "$@"
EOF
  chmod +x "${stub_dir}/python-stub"
  MAX_TOTAL_USD=100 PYTHON="${stub_dir}/python-stub" run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"score.py budget failed (exit 1)"* ]]
  [[ "${output}" != *"reached"* ]]
}

@test "BENCH_TASKS_DIR runs the tasks of another task set" {
  local -r tasks_dir="${stub_dir}/quality"
  mkdir -p "${tasks_dir}/slug"
  printf 'Write a slug function.\n' >"${tasks_dir}/slug/prompt.md"
  BENCH_TASKS_DIR="${tasks_dir}" TASKS="slug" run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 0 ]
  [ -f "${out_dir}/none/slug/1/stream.jsonl" ]
}

@test "refuses an existing out-dir without RESUME" {
  mkdir -p "${out_dir}"
  run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"exists: use a new out-dir, or RESUME=1"* ]]
}

@test "RESUME=1 keeps the runs that gave an answer and reruns the others" {
  bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  echo '{"type":"result","terminal_reason":"api_error","api_error":"usage_limit_reached"}' \
    >"${out_dir}/none/python/1/stream.jsonl"
  touch "${out_dir}/none/go/1/kept"
  : >"${STUB_LOG}"
  RESUME=1 run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  [ "${status}" -eq 0 ]
  [ -f "${out_dir}/none/go/1/kept" ]
  grep -q '"terminal_reason":"completed"' "${out_dir}/none/python/1/stream.jsonl"
  [ "$(wc -l <"${STUB_LOG}")" -eq 1 ]
  [[ "$(cat "${STUB_LOG}")" == *python* ]]
}

@test "RESUME=1 refuses an arm whose plugin dir differs from the kept runs'" {
  bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=
  : >"${STUB_LOG}"
  RESUME=1 run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 none=/other/plugin
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"kept runs of 'arm none: ', not of none=/other/plugin"* ]]
  [ ! -s "${STUB_LOG}" ]
}

@test "MAX_TOTAL_USD stops before the batch that would pass the cap" {
  MAX_TOTAL_USD=0.015 run bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 2 none=
  [ "${status}" -eq 1 ]
  [[ "${output}" == *"MAX_TOTAL_USD=0.015 reached"* ]]
  [ -f "${out_dir}/none/go/2/stream.jsonl" ]
  [ ! -e "${out_dir}/none/python" ]
}

@test "TERM stops every claude the batch started" {
  STUB_HANG="${stub_dir}/hang"
  mkdir "${STUB_HANG}"
  export STUB_HANG
  bash "${BATS_TEST_DIRNAME}/../bench/run.sh" "${out_dir}" 1 a= b= 3>&- &
  local -r bench_pid="$!"
  local -i tries=0
  until [ "$(find "${STUB_HANG}" -type f | wc -l)" -eq 2 ]; do
    ((tries++ < 100))
    sleep 0.1
  done
  kill -TERM "${bench_pid}"
  run wait "${bench_pid}"
  [ "${status}" -ne 0 ]
  sleep 0.5
  local pid_file=""
  for pid_file in "${STUB_HANG}"/*; do
    run kill -0 "$(cat "${pid_file}")"
    [ "${status}" -ne 0 ]
  done
}
