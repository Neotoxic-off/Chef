# Embedded C/C++

Read with `c.md` or `cpp.md`; their rules apply. Verified Nov 2026: PlatformIO Core 6.2, Cppcheck 2.22, MISRA C:2025 and MISRA C++:2023 are the current MISRA editions; check with `pio --version`, `cppcheck --version`, and misra.org.uk.

## Build and warnings

PlatformIO `platformio.ini` (or CMake presets for vendor SDKs such as Zephyr, ESP-IDF, STM32Cube):

```ini
[env]
build_flags = -Wall -Wextra -Werror -Wconversion -Wshadow -Wdouble-promotion
  -Wcast-align -Wundef -fstack-usage
check_tool = cppcheck, clangtidy
check_skip_packages = yes

[env:native]
platform = native
test_framework = unity
```

- `-fstack-usage` writes per-function stack use; review it against each task's stack size.
- Arduino sketches: build with `arduino-cli compile --warnings all` and fix every warning (the IDE hides them by default).
- Static analysis in CI: `pio check --fail-on-defect=low --fail-on-defect=medium --fail-on-defect=high`.

## MISRA and static analysis

- Safety or certified product: follow MISRA C:2025 (C) or MISRA C++:2023 (C++) with a qualified checker (Cppcheck Premium, PC-lint Plus, Polyspace, Axivion, Coverity). Record each deviation in the project's deviation log with its justification, never as an inline suppression.
- Not certified: open-source `cppcheck --addon=misra` checks MISRA C:2012 only; use it as a guide, not as compliance evidence.
- Any MISRA rule that contradicts a house rule is a question for the user; do not pick one silently.

## Code

- Fixed-width types everywhere (`uint32_t`, `int16_t`); explicit types on every declaration (see SKILL.md). No `auto` in C++.
- No dynamic allocation after init: static buffers, pools, or RTOS static APIs.
- `volatile` for memory-mapped registers and variables shared with ISRs; protect multi-byte shared data with a critical section or atomics.
- ISRs are short: acknowledge, copy data, signal a task. No blocking calls, no logging, no floating point unless the port saves FPU context.
- Name every register mask, timing and buffer size: `static const uint32_t UART_BAUD_RATE = 115200U;`.
- A hardware abstraction layer (function-pointer structs in C, interfaces in C++) between drivers and logic, so logic builds and tests on the host.
- C++: no exceptions and no RTTI on small targets (`-fno-exceptions -fno-rtti`); return error enums or `std::expected`-style results.
- Enable the watchdog in production builds; feed it from the main loop or a supervisor task, never from an ISR.
- FreeRTOS: `configSUPPORT_STATIC_ALLOCATION 1`, `configCHECK_FOR_STACK_OVERFLOW 2`, and `configASSERT` defined. Zephyr: enable `CONFIG_ASSERT` and stack sentinels in test builds.

## Tests

- Unit tests on the host: `pio test -e native` (Unity) or Unity/CMock with CTest. Names state the behavior: `test_ring_buffer_push_when_full_returns_overflow`.
- Coverage on host builds with gcovr, gated at 90% line and branch (see `c.md`).
- Simulation: Renode or QEMU for firmware-level tests in CI without boards.
- Hardware-in-the-loop on a CI runner with the board attached: `pio test -e <board>`, Zephyr `twister --device-testing`, or pytest-embedded (ESP-IDF). Drive the device through its real interfaces (UART, GPIO, CAN) and assert on observable behavior.
- Fault-injection tests for brown-out, watchdog reset and corrupted flash data.

Order before done: build (warnings are errors), `pio check`, host tests with coverage, simulator or HIL tests.
