# Clojure

Written for Clojure 1.12.7, clj-kondo 2026.10.26, cljfmt 0.16.6, kaocha 1.91.1392, cloverage 1.2.4, test.check 1.1.3, Malli 0.20.3 (Nov 2026), not benchmarked. Current versions: Maven Central for `org.clojure/*`, https://clojars.org for the rest. Pin every dependency in `deps.edn` with an exact version.

## Lint and format: clj-kondo + cljfmt

- Lint with clj-kondo: `clj-kondo --lint src test`. The default fail level is `warning`, so any warning fails CI; keep that default.
- Config in `.clj-kondo/config.edn`. Raise useful linters, never lower one to pass:
  ```clojure
  {:linters {:unused-binding {:level :error}
             :unused-private-var {:level :error}
             :refer-all {:level :error}}}
  ```
  `:missing-docstring` is off by default; leave it off (see SKILL.md: docstrings only on a library's public API).
- Never use `#_:clj-kondo/ignore` or `{:clj-kondo/ignore ...}` metadata (see SKILL.md).
- Format with cljfmt (`clj -Ttools install io.github.weavejester/cljfmt '{:git/tag "0.16.6"}' :as cljfmt`). CI runs `cljfmt check`; fix with `cljfmt fix`.
- Turn on `(set! *warn-on-reflection* true)` at the top of every namespace that does Java interop, and fix each reflection warning with a type hint.

## Types

Clojure is dynamically typed, so the house type rule maps to schemas:

- Malli schemas on every public function at a boundary (HTTP, DB, queue, config). Validate input there with `m/validate` / `m/coerce` and return an error value on failure.
- Function schemas with `:malli/schema` metadata; turn on `malli.dev/start!` in dev and tests so calls are checked.
- Type hints (`^String`, `^long`) where interop needs them; they are not a substitute for schemas.

## Code

- Pure functions over immutable maps; side effects at the edges, passed in as functions or protocol implementations.
- Errors: return data (`{:error :insufficient-funds}`) for expected failures. `ex-info` with a data map for real exceptions. `try`/`catch` only around interop or I/O, catching the specific class.
- No `def` inside functions, no global `atom` for app state: use a component system (Integrant or Component) and pass state in.
- Name constants: `(def max-retries 3)`, no literals in logic.

```clojure
(def WithdrawResult
  [:or [:map [:ok nat-int?]] [:map [:error [:enum :insufficient-funds]]]])

(defn withdraw
  {:malli/schema [:=> [:cat nat-int? nat-int?] WithdrawResult]}
  [balance amount]
  (if (> amount balance)
    {:error :insufficient-funds}
    {:ok (- balance amount)}))
```

## Tests

- `clojure.test`, run by kaocha (`bin/kaocha` or a `:test` alias). Test names are kebab-case behaviors:
  ```clojure
  (deftest withdraw-with-insufficient-funds-returns-error
    (is (= {:error :insufficient-funds} (withdraw small-balance large-amount))))
  ```
- Property tests with test.check (`defspec`) for pure logic and parsers.
- Integration tests in a separate kaocha suite (`:integration` in `tests.edn`), against real services in containers (clj-test-containers).
- Coverage: kaocha-cloverage plugin with a gate in `tests.edn`:
  ```clojure
  {:plugins [:kaocha.plugin/cloverage]
   :cloverage/opts {:fail-threshold 90}}
  ```
  `:fail-threshold` applies to both line and form coverage.
- No maintained mutation testing tool known for Clojure (unverified).

Order before done: `cljfmt fix` then `clj-kondo --lint src test` then `bin/kaocha`.
