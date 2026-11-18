# TypeScript / JavaScript

Write TypeScript, not JavaScript, for any new file.

## tsconfig

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noPropertyAccessFromIndexSignature": true
  }
}
```

## Lint and format

- ESLint flat config (`eslint.config.mjs`) with typescript-eslint `strictTypeChecked` and `stylisticTypeChecked`:
  ```js
  import eslint from "@eslint/js";
  import tseslint from "typescript-eslint";

  export default tseslint.config(
    eslint.configs.recommended,
    ...tseslint.configs.strictTypeChecked,
    ...tseslint.configs.stylisticTypeChecked,
    { languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } } },
  );
  ```
- Add `@typescript-eslint/explicit-function-return-type` and `@typescript-eslint/typedef` to enforce explicit types.
- Format with Prettier (or Biome if the project already uses it). CI checks formatting.

## Code

- Explicit types everywhere (see SKILL.md). No `any`; use `unknown` and narrow it.
- Validate external data (HTTP, JSON, env) at the boundary with a schema library (e.g. zod), then trust the typed result.
- `const` over `let`, never `var`. `readonly` on fields and arrays that do not change.
- Named exports, no default exports.
- `async`/`await`, no floating promises.

## Tests

- Vitest for unit and integration tests; Playwright for end-to-end and UI.
- Coverage with `@vitest/coverage-v8`, thresholds in `vitest.config.ts`:
  ```ts
  coverage: { provider: "v8", thresholds: { lines: 90, branches: 90, functions: 90, statements: 90 } }
  ```
- Lint tests with `@vitest/eslint-plugin`.
- React: Testing Library, query by role and label, not by class or test id.
- Mutation testing: StrykerJS.
