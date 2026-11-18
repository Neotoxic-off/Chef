# Bundlers: Vite, Rolldown, esbuild, webpack

Builds on `typescript.md`. Verified against Vite 8.3, Rolldown 1.3, esbuild 0.28, webpack 5.112, Rspack 2.3, tsdown 0.23 (Nov 2026). Look up the current version with `npm view <package> version`.

## Choice

- New app: Vite (or the framework's own Vite-based CLI). New library: tsdown (Rolldown-based; Rolldown's docs point libraries to it).
- Existing webpack app: keep webpack 5. If builds are too slow, migrate to Rspack (`@rspack/core`), which keeps the webpack config, loaders and most plugins.
- esbuild directly only for small scripts or tools that need one fast transform; it is still 0.x, so install it with `--save-exact`.
- Rolldown is stable (1.0 since May 2026), but use it through Vite or tsdown, not as a raw bundler, unless the project already does.

## Vite 8

- Vite 8 bundles with Rolldown and transforms with Oxc. esbuild and Rollup are no longer used; esbuild is an optional dependency.
- Node 20.19+ or 22.12+. Default `build.target` is Baseline Widely Available (Chrome/Edge 111, Firefox 114, Safari 16.4).
- Use the new option names; the old ones are deprecated and auto-converted:
  - `build.rolldownOptions` / `worker.rolldownOptions`, not `rollupOptions`.
  - `oxc`, not `esbuild`; `transformWithOxc`, not `transformWithEsbuild`.
  - Rolldown `output.codeSplitting`, not `manualChunks` (object form removed, function form deprecated).
- Vite does not type-check. Run `tsc --noEmit` (or the framework checker: `vue-tsc`, `svelte-check`, `astro check`) in CI before `vite build`.
- `tsconfig.json`: `"isolatedModules": true` (required: Oxc transpiles file by file) and `"types": ["vite/client"]`. Vite ignores the tsconfig `target`.
- Type the config and env vars:
  ```ts
  import { defineConfig, type UserConfig } from "vite";

  const config: UserConfig = defineConfig({
    build: { sourcemap: true },
  });
  export default config;
  ```
  ```ts
  interface ImportMetaEnv {
    readonly VITE_API_URL: string;
  }
  ```
- Only `VITE_`-prefixed variables reach client code, and they are public: never put secrets in them. Validate them at startup with a schema (see `typescript.md`).
- Upgrading a large project from Vite 7: first switch to `rolldown-vite` on Vite 7 to isolate bundler issues, then move to Vite 8.

## webpack 5

- `webpack.config.ts` typed with `import type { Configuration } from "webpack"`; `mode` set explicitly per environment.
- `ts-loader` with `transpileOnly: true` plus `fork-ts-checker-webpack-plugin`, or `tsc --noEmit` in CI: the build must fail on type errors.
- `devtool: "source-map"` for production builds that upload maps to error tracking; never serve maps publicly unless intended.
- `contenthash` in output file names for long-term caching.

## All bundlers

- Commit the lockfile; pin the bundler and its plugins to exact or tilde ranges in apps.
- Bundler warnings (circular imports, missing exports, large chunks) count as errors (see SKILL.md): fix the cause, do not raise limits to hide them.
- Never import server-only modules or secrets into client entry points; check the built output when unsure.
