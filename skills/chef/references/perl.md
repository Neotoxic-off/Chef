# Perl

Target Perl 5.36 or later and start every file with `use v5.36;` (or the project's newer version): it enables `strict`, `warnings` and subroutine signatures. Manage dependencies with a `cpanfile` and Carton (`cpanfile.snapshot` committed). Check current tool versions on metacpan.org or with `cpanm --info <Module>`. Written for Perl 5.44, Perl::Critic 1.156, Perl::Tidy 20260826, Devel::Cover 1.52 (Nov 2026), not benchmarked.

## Lint and format: Perl::Critic, perltidy

`.perlcriticrc`:

```ini
severity = 3
verbose = 8

[Subroutines::ProhibitExcessComplexity]
max_mccabe = 10
```

At severity 3, the `Documentation::*` policies stay off (they are severity 2 and below). If you lower `severity` to 2 or 1, disable `Documentation::RequirePodSections` in the config: it contradicts the house rule (POD only on a library's public API).

`.perltidyrc`: `-pbp` (Perl Best Practices style) plus `-l=100`. CI runs `perltidy --assert-tidy` on every file and `perlcritic lib/ bin/ t/`; both fail the build. Never use `## no critic`.

Perl::Critic 1.144+ treats `use v5.36` as enabling `strict` and `warnings`; on an older one, upgrade it rather than add `use strict; use warnings;`.

## Code

- Perl has no type annotations. Use signatures so arity is checked: `sub withdraw ($account, $amount) { ... }`. Validate values at the boundary; use Type::Tiny if the project already does.
- Name constants: `use constant MAX_RETRIES => 3;`.
- Lexical variables only (`my`), three-argument `open` with a lexical handle, `/x` on any non-trivial regex.
- Errors: `die` with an exception object (a class, not a string). Check before acting (`exists`, `defined`, `looks_like_number` from `Scalar::Util`) instead of catching.
- When catching is unavoidable (I/O, network), use `try`/`catch` (stable since 5.40, `use v5.40`), with the smallest `try` block. On older Perls, use `eval` with a `local $@` guard; never a bare `eval` whose result you ignore.
- Modern OO: core `class` (5.38+, still experimental in 5.44) only if the project accepts it; otherwise Moo. No hand-rolled `bless` in new code.
- Inject I/O and time (`$clock->now`) through constructor arguments.

## Tests

- Test2::V0, files under `t/`, run with `prove -lr t/`. Subtest names state the behavior:
  ```perl
  use v5.36;
  use Test2::V0;

  subtest 'withdraw with insufficient funds dies' => sub {
      my $account = Account->new(balance => 10);
      like(dies { $account->withdraw(20) }, qr/insufficient funds/);
  };

  done_testing;
  ```
- Integration tests under `xt/` or behind an environment flag, against real services in containers.
- Coverage: `cover -test` (Devel::Cover) reports statement, branch and condition coverage. Devel::Cover has no fail-under flag: gate in CI by reading `cover_db/cover.json` from `cover -report json` and failing under 90%.

Order before done: `perltidy` then `perlcritic` then `prove -lr t/` then `cover -test`.
