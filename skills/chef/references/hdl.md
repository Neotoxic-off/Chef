# HDL: SystemVerilog, Verilog, VHDL

Verified Nov 2026: Verilator 5.054, Verible v0.0-4302, cocotb 2.1, VSG 3.36; check with `verilator --version`, `verible-verilog-lint --version`, `pip show cocotb`, `vsg --version`. cocotb testbenches are Python: `python.md` applies to them.

## Lint and format

- SystemVerilog/Verilog: `verilator --lint-only -Wall` on every top level (fails on any warning), and `verible-verilog-lint` with the default ruleset plus a committed `.rules.verible_lint`. Format with `verible-verilog-format --inplace`; CI checks with `--verify`.
- Verible's default `explicit-parameter-storage-type` rule enforces the house rule on parameters; keep it on.
- VHDL: VSG (`vsg -f <files> -c vsg.yaml`; `--fix` to format) and GHDL analysis with `ghdl -a --std=08` (or NVC).
- Never `/* verilator lint_off */` or Verible waivers. A warning on a signal left unused on purpose: route it to one `_unused_ok` wire, the pattern Verilator's manual recommends.

## Code

- First line of every Verilog/SystemVerilog file: `` `default_nettype none `` (no implicit nets); restore `` `default_nettype wire `` at the end for third-party files that need it.
- Explicit types and widths everywhere (see SKILL.md): `logic [7:0] data_q;`, `localparam int unsigned FIFO_DEPTH = 16;`. No bare `parameter N = 4`.
- Name every width, depth and timing constant with a `localparam`; derive widths with `$clog2`.
- `always_ff` with nonblocking (`<=`) for registers; `always_comb` with blocking (`=`) for logic; assign every output in every branch (Verilator `LATCH` catches misses).
- One clock domain per module unless it is a synchronizer; cross domains only through a reviewed synchronizer or async FIFO.
- Reset style (sync or async, active level) is one project decision; follow it everywhere.
- `enum logic [1:0]` for state machines; a `default` arm that goes to a safe state.
- Packages for shared types; `typedef struct packed` for buses.
- VHDL: `numeric_std` only (never `std_logic_arith`), `rising_edge(clk)`, `constant` for every magic value.
- Assertions (SVA or PSL) for every protocol rule; they run in simulation and formal.

## Tests

- cocotb 2 testbenches, run through pytest with `cocotb_tools.runner.get_runner("verilator")`. Test names state the behavior:
  ```python
  @cocotb.test()
  async def test_write_when_full_is_ignored(dut: HierarchyObject) -> None:
      Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start()
      await fill_fifo(dut)
      dut.wr_data.value = EXTRA_WORD
      await RisingEdge(dut.clk)
      assert dut.count.value == FIFO_DEPTH
  ```
- VHDL-only projects may use VUnit; same naming rule.
- Constrained random stimulus with a fixed seed logged per run, checked against a Python reference model.
- Coverage: build with `verilator --coverage`, export with `verilator_coverage --write-info coverage.info`, and gate at 90% line and toggle coverage in CI. Add functional coverage points for every protocol case.
- Formal: SymbiYosys (`sby -f <module>.sby`) proves the assertions on control logic (FIFOs, arbiters, FSMs).

Order before done: format, Verilator and Verible lint (or VSG and GHDL), cocotb tests with coverage, formal.
