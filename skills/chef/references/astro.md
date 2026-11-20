# Astro

Builds on `typescript.md`. Written for Astro 7.4, @astrojs/check 0.9, eslint-plugin-astro 3.2 (Nov 2026), not benchmarked. Current version: `npm view astro version`; upgrade with `npx @astrojs/upgrade`.

## Setup

- Astro 7 needs Node 22+ and runs on Vite 8. The compiler is now Rust-based and rejects unclosed non-void tags that Astro 6 accepted.
- `tsconfig.json` extends `astro/tsconfigs/strictest`, then adds the flags from `typescript.md`:
  ```json
  { "extends": "astro/tsconfigs/strictest", "include": [".astro/types.d.ts", "**/*"], "exclude": ["dist"] }
  ```
- `astro build` does not type check, and `tsc` ignores `.astro` files. Run `astro check` (needs `@astrojs/check`) in CI and before the build: `"build": "astro check && astro build"`.
- ESLint flat config (eslint-plugin-astro 3 needs ESLint 10):
  ```js
  import eslintPluginAstro from "eslint-plugin-astro";

  ...eslintPluginAstro.configs.recommended,
  ...eslintPluginAstro.configs["jsx-a11y-recommended"],
  ```
  For typed linting of `.astro` files, point `parserOptions.project` at a `tsconfig.eslint.json` that also includes a `jsx.d.ts` overriding `JSX.Element` to `HTMLElement`; otherwise `no-unsafe-return` fires on the `any` JSX type. Fix it that way, never by disabling the rule.
- Format with Prettier and `prettier-plugin-astro`.
- Markdown now renders with Astro's native pipeline. Projects that use remark/rehype plugins install `@astrojs/markdown-remark`.
- Default whitespace is `compressHTML: "jsx"`: write `{" "}` between inline elements that need a space.

## Components

- Ship zero JS by default. A component is static HTML unless it needs interactivity; then render a framework island with the laziest `client:` directive that works (`client:visible` or `client:idle` before `client:load`).
- Type props with an interface named `Props` and annotate the destructuring:
  ```astro
  ---
  interface Props {
    readonly title: string;
    readonly tags: readonly string[];
  }
  const { title, tags }: Props = Astro.props;
  const tagCount: number = tags.length;
  ---
  <h2>{title} ({tagCount})</h2>
  ```
- `<script>` tags are bundled TypeScript modules: type them like any `.ts` file. No `is:inline` unless the script must run before the bundle loads.
- No `set:html` with user content.
- Images through `astro:assets` `<Image>` / `<Picture>`, with `alt` on every image.

## Data, actions, env

- Content lives in collections in `src/content.config.ts`: `defineCollection` with a loader (`glob`, `file`) and a schema from `astro/zod`. Query with `getCollection` / `getEntry`; never parse frontmatter by hand.
- Mutations through Actions (`src/actions/index.ts`, `defineAction` with an `input` schema; `accept: "form"` for forms). Callers read `{ data, error }`; no `try`/`catch` around an action call.
- In a handler, check auth from `context.locals` and throw `ActionError` with a code (`"UNAUTHORIZED"`, `"NOT_FOUND"`) instead of returning `undefined`.
- Env vars: declare every one in `env.schema` with `envField` (`context` + `access`), read them from `astro:env/server` or `astro:env/client`. Secrets are `context: "server", access: "secret"`.
- Per-request data (user, session) goes in middleware (`src/middleware.ts`: `export const onRequest = defineMiddleware(...)` from `astro:middleware`) onto `context.locals`; type `App.Locals` in `src/env.d.ts`.

## Tests

- Vitest configured through `getViteConfig()` from `astro/config`.
- Test `.astro` components with the Container API (`experimental_AstroContainer` from `astro/container`, `renderToString`), and assert on the HTML.
- Islands: test with the framework's own Testing Library (`react.md`, `svelte.md`...).
- Playwright against `astro build && astro preview` (see `e2e-testing.md`).
