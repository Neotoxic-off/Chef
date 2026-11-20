# Ruby

Written for Ruby 4.0, RuboCop 1.92, rubocop-sorbet 0.17, Sorbet 0.6, Tapioca 0.20, Steep 2.1, SimpleCov 1.3, mutant 0.17 (Nov 2026), not benchmarked.

Bundler manages tools (`Gemfile.lock` committed); run them with `bundle exec`.

## Lint and format: RuboCop

`.rubocop.yml`:

```yaml
plugins:
  - rubocop-performance
  - rubocop-rspec      # or rubocop-minitest
  - rubocop-sorbet
AllCops:
  NewCops: enable
  TargetRubyVersion: 4.0
Sorbet/StrictSigil:
  Enabled: true
Sorbet/EnforceSignatures:
  Enabled: true
```

- RuboCop is both linter and formatter: `rubocop -a` locally, `rubocop` in CI (any offense fails). Use `-A` (unsafe autocorrect) only when you review the diff.
- Load extensions with `plugins:`, not the old `require:`.

## Types: Sorbet

- Every file `# typed: strict` (new code); never lower than `# typed: true`. `srb tc` runs in CI.
- Explicit types: a `sig` on every method, including `void`:
  ```ruby
  sig { params(id: Integer).returns(T.nilable(User)) }
  def find(id); end
  ```
  Instance variables: `@count = T.let(0, Integer)`. Constants: `NAMES = T.let([], T::Array[String])`.
- Generate RBI for gems and DSLs with Tapioca (`tapioca gems`, `tapioca dsl`).
- No `T.untyped` or `T.unsafe` unless the value truly is untyped (parsed JSON); narrow it right away, e.g. into a `T::Struct`.
- Alternative: RBS signatures checked by Steep (`steep check`). Pick one system per project.

## Code

- `# frozen_string_literal: true` at the top of every file.
- Small objects with constructor injection. No monkey patching, no global state, no `method_missing` for business logic.
- Value objects: `Data.define(:x, :y)`, or `T::Struct` with Sorbet.
- Raise specific error classes; never `rescue Exception` or a bare `rescue => e` that hides the cause.

## Warnings as errors

Run tests with `RUBYOPT="-W:deprecated -w"` and make warnings raise from the test helper:

```ruby
module RaiseOnWarning
  def warn(message, category: nil, **) = raise(message)
end
Warning.singleton_class.prepend(RaiseOnWarning)
```

## Tests

- RSpec (or Minitest). One behavior per example, `let` over instance variables, `instance_double` for collaborators at the boundary. RSpec: `config.raise_errors_for_deprecations!`.
- Tag slow tests (`:integration`) and run them against a real database in Docker (CI service or Testcontainers).
- Coverage: SimpleCov, loaded first in `spec_helper.rb`:
  ```ruby
  SimpleCov.start do
    enable_coverage :branch
    coverage :line, minimum: 90
    coverage :branch, minimum: 90
  end
  ```
- Mutation testing: mutant (`mutant-rspec` / `mutant-minitest`) on critical logic. Free for open source with `--usage opensource`; commercial use needs a paid license.

Order before done: `rubocop -a` then `srb tc` (or `steep check`) then `rspec` (or `rake test`).
