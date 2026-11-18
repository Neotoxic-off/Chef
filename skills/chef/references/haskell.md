# Haskell

Verified against GHC 9.14.1, HLint 3.10, Fourmolu 0.21, hspec 2.11, hedgehog 1.7 (Nov 2026). Pick the GHC version with GHCup (`ghcup list`; it marks the recommended one) and pin it in `cabal.project` (`with-compiler: ghc-9.14.1`). Package versions: Hackage.

## Lint and format: GHC warnings + HLint + Fourmolu

Shared warnings in the `.cabal` file, imported by every component:

```cabal
common warnings
  default-language: GHC2024
  ghc-options:
    -Wall -Wcompat -Werror
    -Wmissing-local-signatures
    -Wmissing-export-lists
    -Wpartial-fields
    -Wunused-packages
```

- `-Wall` includes `-Wmissing-signatures` (every top-level binding) and `-Wincomplete-uni-patterns`.
- `-Wmissing-local-signatures` only flags *polymorphic* local bindings. GHC cannot enforce signatures on monomorphic locals: write them by hand (see Code).
- Format with Fourmolu (or Ormolu, its stricter parent; pick one per repo). CI: `fourmolu --mode check src test`.
- Lint with HLint: `hlint src test` in CI. Never generate a `.hlint.yaml` with `hlint --default`: it ignores every current hint, which hides them.

## Code

- Explicit types (see SKILL.md): a signature on every top-level and local binding, including `where` and `let`:
  ```haskell
  withdraw :: Balance -> Amount -> Either WithdrawError Balance
  withdraw balance amount
    | amount > balance = Left InsufficientFunds
    | otherwise = Right remaining
    where
      remaining :: Balance
      remaining = balance - amount
  ```
- `newtype` for domain values (`newtype Amount = Amount Natural`). Smart constructors validate at the boundary.
- Errors as values: `Either`, `Maybe`, or `ExceptT` at the edges. Use `throwIO` only in `IO` for truly exceptional cases, and `bracket` for resources.
- No partial functions (`head`, `tail`, `fromJust`, `!!`, `read`): use `NonEmpty`, pattern matching, `readMaybe`.
- Keep logic pure. Inject effects through a record of functions or a typeclass so tests can replace them.
- Strict fields (`!Int`) in data types; `foldl'`, not `foldl`.
- Haddock comments (`-- |`) only on a library's public API (see SKILL.md).

## Tests

- hspec with `hspec-discover`; the spec text states the behavior:
  ```haskell
  spec :: Spec
  spec = describe "withdraw" $
    it "returns InsufficientFunds when the amount exceeds the balance" $
      withdraw smallBalance largeAmount `shouldBe` Left InsufficientFunds
  ```
- Property tests with hedgehog (or QuickCheck) for pure logic and parser round-trips.
- Integration tests in a separate `test-suite`, against real services in containers.
- Coverage: `cabal test --enable-coverage` (HPC). `hpc report` gives expression, boolean and alternative coverage. HPC has no built-in threshold: gate in CI by parsing the report (fail under 90%).
- No maintained mutation testing tool known for Haskell (unverified).

Order before done: `fourmolu --mode inplace src test` then `hlint src test` then `cabal build all` then `cabal test all --enable-coverage`.
