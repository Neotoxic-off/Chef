# Next.js

Builds on `typescript.md` and `react.md`. Written for Next.js 16.4 (Nov 2026), not benchmarked. App Router only for new code.

## Lint and config

- Next.js 16 removed `next lint`: run the ESLint CLI. Flat config:
  ```js
  import { defineConfig, globalIgnores } from "eslint/config";
  import nextVitals from "eslint-config-next/core-web-vitals";
  import nextTs from "eslint-config-next/typescript";

  export default defineConfig([
    ...nextVitals,
    ...nextTs,
    globalIgnores([".next/**", "out/**", "next-env.d.ts"]),
  ]);
  ```
  `core-web-vitals` already includes `react-hooks` and `jsx-a11y`; add the type-checked presets from `typescript.md` on top.
- `next.config.ts`, typed `NextConfig`. Turbopack is the default bundler in 16.
- `reactCompiler: true` is stable but off by default; turn it on for new apps.

## Server and Client Components

- Components are Server Components by default. Add `"use client"` only on the leaf that needs state, effects or browser APIs; pass Server Components to it as `children`.
- `params`, `searchParams`, `cookies()`, `headers()` and `draftMode()` are async only: `const { id }: { id: string } = await params;`.
- Put database and secret access in a data access layer that starts with `import "server-only";`. Return DTOs with only the fields the UI needs.
- Fetch in Server Components, close to where the data is used. Use `<Suspense>` and `loading.tsx` for streaming.

## Server Actions

- Every Server Action is a public POST endpoint, even if no page imports it. In each action: validate the input with a schema, check authentication, then authorization on the specific resource.
- A page-level auth check does not protect the actions defined in it.
- Return plain serializable results, not raw database records. Show pending and errors with `useActionState`.

## Caching

- With `cacheComponents: true` (set `partialPrefetching: true` with it), data is dynamic by default; opt in with `"use cache"` plus `cacheLife` and `cacheTag`.
- After a mutation in a Server Action, call `updateTag(tag)` for read-your-own-writes. Elsewhere use `revalidateTag(tag, "max")`; the one-argument form is deprecated.
- Never cache per-user data in a shared cache.

## Env vars and security

- Only `NEXT_PUBLIC_*` variables reach the browser, and they are inlined at `next build`: never put a secret behind that prefix. Validate `process.env` once at startup with a schema.
- `middleware.ts` is deprecated and renamed `proxy.ts`. Keep it thin; do auth checks in the data layer too.
- Set security headers in `next.config.ts` `headers()`: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `frame-ancestors` in the CSP. A nonce-based CSP is generated in `proxy.ts` and forces dynamic rendering.

## Tests

- Vitest + React Testing Library for Client Components and synchronous Server Components. Vitest does not support `async` Server Components: cover them with Playwright.
- Test Server Actions and the data layer as plain async functions, with the auth and database injected.
- Playwright against `next build && next start`, not the dev server.
