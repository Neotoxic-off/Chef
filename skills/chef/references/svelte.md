# Svelte and SvelteKit

Builds on `typescript.md`. Verified against Svelte 5.58, SvelteKit 3.3, svelte-check 4.7, eslint-plugin-svelte 3.24 (Nov 2026). SvelteKit 3 needs TypeScript 6, Vite 8 and Node 22.17+.

## Setup

- SvelteKit 3 has no `svelte.config.js`: pass options to the `sveltekit({ ... })` plugin in `vite.config.ts`.
- `tsconfig.json` extends `$app/tsconfig` and lists `include` / `exclude` itself.
- `$lib` is gone: declare `#lib` in `package.json` `imports` and import with the extension (`#lib/user.ts`).
- Type check in CI with `svelte-check --tsconfig ./tsconfig.json --fail-on-warnings`. `tsc` does not check `.svelte` files.
- ESLint flat config:
  ```js
  import svelte from "eslint-plugin-svelte";
  import ts from "typescript-eslint";

  ...svelte.configs.recommended,
  {
    files: ["**/*.svelte", "**/*.svelte.ts"],
    languageOptions: { parserOptions: { projectService: true, parser: ts.parser, extraFileExtensions: [".svelte"] } },
  },
  ```

## Components

- Runes only; no `export let`, `$:` or `on:` event directives in new code.
  ```svelte
  <script lang="ts">
    interface Props { readonly user: User; onselect: (id: string) => void }
    const { user, onselect }: Props = $props();
    let count: number = $state(0);
    const label: string = $derived(user.name.trim());
  </script>

  <button type="button" onclick={(): void => onselect(user.id)}>{label} ({count})</button>
  ```
- `$derived` for computed values; `$effect` only to sync with something outside Svelte (DOM, timers, third-party code). Never set state from an `$effect` to derive it.
- Snippets and `{@render}` instead of slots. `$bindable` only where two-way binding is the point.
- Shared reactive logic lives in `.svelte.ts` modules that export functions or classes with `$state` fields.
- No `{@html}` with user content.

## SvelteKit

- Load data in `+page.server.ts` / `+layout.server.ts` with the generated `PageServerLoad` type; mutations through form actions with `use:enhance`.
- Validate every form action and endpoint input with a schema; check auth in each action, not only in the layout.
- Any `server` directory (outside `src/routes`) and `*.server.ts` files are server-only.
- Env vars: declare them in `src/env.ts` with `defineEnvVars`; import from `$app/env/private` or `$app/env/public` (`$env/*` is deprecated). Variables are private unless marked `public: true`.
- Read page state from `$app/state` (`page`, `navigating`); `$app/stores` is removed.
- Remote functions are still experimental: do not use them without asking.

## Tests

- Vitest. Test runes logic in `*.svelte.test.ts` files; wrap code with effects in `$effect.root` and call `flushSync()` before asserting.
- Components: `@testing-library/svelte` + `user-event`, query by role and label. Set `resolve.conditions: ["browser"]` when running in jsdom.
- Playwright for end-to-end, against a production build (`vite build && vite preview`).
