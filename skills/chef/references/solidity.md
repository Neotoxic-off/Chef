# Solidity

Foundry by default; Hardhat 3 if the project uses it (it runs forge-std Solidity tests natively with `npx hardhat test`). Written in Nov 2026 (not benchmarked): Foundry 1.9, Solhint 6.2, Slither 0.11, Aderyn 0.6, OpenZeppelin Contracts 5.7; check with `forge --version`, `slither --version`, and each project's GitHub releases. Pin the compiler exactly: `pragma solidity 0.8.30;` (use the project's version), never `^`.

## Lint and format

`foundry.toml`:

```toml
[profile.default]
deny = "warnings"

[fmt]
line_length = 100

[lint]
severity = ["high", "med", "low"]

[fuzz]
runs = 1000
```

`forge lint` runs on every `forge build`; its mixed-case lint already exempts `test*` and `invariant_*` functions. `.solhint.json` for `src/`:

```json
{
  "extends": "solhint:recommended",
  "rules": {
    "explicit-types": ["error", "explicit"],
    "use-natspec": "off"
  }
}
```

`use-natspec` is off because it contradicts the house rule: NatSpec only on interfaces and libraries other projects import. CI: `forge fmt --check`, `forge build`, `solhint --max-warnings 0 'src/**/*.sol'`, `slither . --fail-low`, then `aderyn .` as a second opinion. Never `// forge-lint: disable-*` or `// slither-disable-*`; fix the finding or tell the user.

## Code

- Explicit sized types: `uint256`, never `uint`. Name every constant: `uint256 private constant MAX_SUPPLY = 1_000_000e18;`.
- Checks, Effects, Interactions: validate, update state, then call out. Add OpenZeppelin `ReentrancyGuard` on functions that call untrusted contracts.
- Pull over push for payments: record what is owed, let the recipient withdraw.
- Custom errors (`error InsufficientBalance(uint256 available, uint256 required);`), not revert strings. `require(cond, CustomError())` works from 0.8.26 with via-IR and from 0.8.27 on the legacy pipeline.
- Access control with `Ownable2Step` or `AccessControl`; never `tx.origin`.
- Token transfers through `SafeERC20`. Never trust a token's return value or balance before the call.
- No randomness from `block.timestamp`, `blockhash` or `prevrandao` where value is at stake.
- `unchecked` only with a one-line proof that the math cannot overflow.
- Emit an event for every state change off-chain systems need.
- `try`/`catch` only around an external call whose failure you can handle; otherwise let it revert.
- Upgradeable contracts: OpenZeppelin upgrades tooling with storage-layout checks; set state in an `initializer`, and call `_disableInitializers()` in the implementation's constructor.

## Tests

- forge-std tests in `test/*.t.sol`. Names follow Foundry's convention and state the behavior:
  ```solidity
  function test_RevertWhen_WithdrawExceedsBalance() public {
      vm.expectRevert(abi.encodeWithSelector(Vault.InsufficientBalance.selector, DEPOSIT, WITHDRAWAL));
      vault.withdraw(WITHDRAWAL);
  }
  ```
- `testFuzz_` for every function taking amounts or addresses; bound inputs with `bound()`. Invariant tests (`invariant_`) for core accounting (total supply equals sum of balances).
- Fork tests against a pinned block for integrations with live protocols.
- Coverage: `forge coverage --report lcov`; fail CI under 90% line and branch coverage. Forge has no built-in threshold flag that I could verify: gate with a script over `lcov.info`.
- Get an external audit before mainnet for anything holding value.

Order before done: `forge fmt` then `forge build` then solhint then `forge test` then Slither.
