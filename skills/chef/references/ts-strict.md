# TypeScript: turn on strict, upgrade TypeScript, Node and frameworks

Builds on `typescript.md`. Verified against TypeScript 6.0 release notes and tsconfig reference, `@andrewbranch/ts5to6` 1.1.1, nodejs/userland-migrations with `codemod` 1.18, npm registry data for ts-migrate and typescript-strict-plugin (Nov 2026).

## When it applies

- `tsconfig.json` has `"strict": false`, or omits it on TypeScript 5.x. TypeScript 6.0 made `strict` default to `true`, so an upgrade to 6.0 already forces this choice.
- A TypeScript, Node.js or framework major upgrade.
- Turning strict on in an existing project needs the user's yes first (SKILL.md).

## Strict, one flag at a time

`strict` turns on the strict family: `alwaysStrict`, `noImplicitAny`, `noImplicitThis`, `strictBindCallApply`, `strictBuiltinIteratorReturn`, `strictFunctionTypes`, `strictNullChecks`, `strictPropertyInitialization`, `useUnknownInCatchVariables`. Future TypeScript versions may add more.

1. Baseline: `npx tsc --noEmit`, lint and tests run, failures recorded. Record the error count per flag, one flag at a time: `npx tsc --noEmit --strictNullChecks`, then `--noImplicitAny`, and so on.
2. Set `"strict": true` and list every family flag that still fails as `false` beside it. Commit: no code change, no new errors.
3. Remove one `false` per batch, cheapest first (`alwaysStrict` first: `alwaysStrict: false` is deprecated in 6.0; then usually `strictBindCallApply`, `noImplicitThis`, `useUnknownInCatchVariables`), then `noImplicitAny`, then `strictNullChecks` and `strictPropertyInitialization` last.
4. A flag with too many errors for one batch: go per folder. Add `tsconfig.strict.json` that `extends` the main config, turns the flag on and `include`s only the folders already fixed; run `npx tsc -p tsconfig.strict.json --noEmit` in CI next to the main check. Grow `include` folder by folder, then move the flag to the main config and delete the extra file.
5. The `typescript.md` extras (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, ...) come after `strict`, same way.

Validation per batch: `npx tsc --noEmit`, ESLint, tests.

Fix errors with real types and narrowing. Never `any`, `!`, `as unknown as`, `@ts-ignore` or `@ts-expect-error` to make a count drop.

## Tools

- `ts-migrate` (Airbnb): last npm release 0.1.35, Nov 2022. Unmaintained; it inserts `any` and `@ts-expect-error`, which the house rules forbid. Do not use.
- `typescript-strict-plugin`: last release 2.4.4, Jun 2024, and works through `//@ts-strict-ignore` comments (a suppression). Do not use; prefer the per-folder config above.
- TypeScript 5 to 6: `npx @andrewbranch/ts5to6 --fixBaseUrl .` and `--fixRootDir .` (experimental, linked from the 6.0 notes). Fix every 6.0 deprecation: 7.0 removes those options. `"ignoreDeprecations": "6.0"` hides the errors, so it needs the user's yes. Check typed-lint support before 7.0 (`typescript.md`).
- Node.js majors: official codemods from nodejs/userland-migrations: `npx codemod @nodejs/<recipe>`. Read the Node release notes for every major crossed; set `engines.node` and the CI matrix to the new version.
- Frameworks: the framework's own upgrade tool, named in its reference file (e.g. `ng update @angular/cli@^<major> @angular/core@^<major>`, `npx @next/codemod upgrade`, `npx @astrojs/upgrade`). One major per batch.

## Pitfalls

- TypeScript 6.0 also changed defaults: `module` is `esnext`, `target` is the latest ES version, `types` is `[]` (add `"types": ["node"]` etc. explicitly), and `rootDir` inference changed.
- `useUnknownInCatchVariables`: narrow `catch (error: unknown)` with `instanceof`, do not cast.
- `strictPropertyInitialization`: initialize in the constructor or make the field optional; no `!` definite-assignment.
- Diff holds only what the flag needs: no reformatting, no renames, no annotations on lines the flag did not flag.

## Leave for the user

- Whether to turn on strict at all, and the order of flags.
- `"ignoreDeprecations": "6.0"` as a bridge, if a deprecation cannot be fixed in this migration.
- Behavior changes a null check reveals (a value really can be `undefined`): report them, do not guess the intended behavior.
