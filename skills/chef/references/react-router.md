# React Router (framework mode, ex-Remix)

Builds on `typescript.md` and `react.md`. Verified against React Router 8.5 (Nov 2026). Current version: `npm view react-router version`; peer ranges: `npm view @react-router/dev peerDependencies`.

## Versions

- v8 (June 2026) needs Node 22.22+, React 19.2.7+ and Vite 7+, and is ESM-only. v7 still ships under the `version-7` npm tag; new apps start on v8.
- v8 made every `future.v8_*` flag the default: middleware is always on, `splitRouteModules` is on, data URLs are trailing-slash aware. On v7, turn these flags on before upgrading.
- `react-router-dom` is gone: import from `react-router` (and `react-router/dom` for `HydratedRouter` / `RouterProvider`).
- Remix 2 apps migrate to React Router 7 first (guide: `reactrouter.com/upgrading/remix`), then to 8. No `@remix-run/*` packages in a React Router app.

## Setup

- Routes are declared in `app/routes.ts` (`RouteConfig` from `@react-router/dev/routes`), not discovered by magic: keep it the one map of the app.
- Route types are generated. Add `.react-router/` to `.gitignore`, then in `tsconfig.json`:
  ```json
  { "include": [".react-router/types/**/*"], "compilerOptions": { "rootDirs": [".", "./.react-router/types"] } }
  ```
- CI type check: `"typecheck": "react-router typegen && tsc"`.
- Route modules must `export default` their component: this is the framework exception to "named exports only" in `typescript.md`.
- Cloudflare: use `@cloudflare/vite-plugin`; the React Router Cloudflare dev proxy was removed in v8.

## Route modules

- Type every export with the generated `Route` types (`LoaderArgs`, `ActionArgs`, `ComponentProps`, `ErrorBoundaryProps`, `MiddlewareFunction`):
  ```tsx
  import { Form, href, redirect } from "react-router";
  import type { Route } from "./+types/project";

  export const middleware: Route.MiddlewareFunction[] = [requireUser];

  export async function loader({ params, context }: Route.LoaderArgs): Promise<ProjectData> {
    const user: User = context.get(userContext);
    const project: Project = await getProject(user, params.projectId);
    return { project };
  }

  export async function action({ params, context }: Route.ActionArgs): Promise<Response> {
    const user: User = context.get(userContext);
    await archiveProject(user, params.projectId);
    return redirect(href("/projects"));
  }

  export default function ProjectPage({ loaderData }: Route.ComponentProps): React.JSX.Element {
    return <Form method="post"><h1>{loaderData.project.name}</h1></Form>;
  }
  ```
- Load data in `loader`, mutate in `action`, submit with `<Form>` or `useFetcher`. No `useEffect` + `fetch` for route data.
- Validate `params`, form data and search params with a schema at the top of each loader and action. Use `safeParse` (a throwing `parse` turns bad input into a 500) and return errors with `data(errors, { status: HTTP_BAD_REQUEST })` when the user must see them.
- Auth, sessions and shared per-request values go in `middleware` with typed `createContext<T>()` + `context.set` / `context.get`. Check auth again in each action that needs it.
- Build URLs with the type-safe `href()`, not string concatenation.
- Server-only code (DB, secrets) lives in `*.server.ts` files or `.server/` folders; the build fails if they leak into the client graph. Never mark a route module `.server`.
- Every route that can fail exports an `ErrorBoundary`, and `root.tsx` always has one. Throw `data(...)` with a 4xx status for expected misses (not found, forbidden) instead of returning `null`.
- Keep `clientLoader` / `clientAction` for browser-only data; server `loader` / `action` by default.

## Tests

- Unit-test loaders and actions as plain functions: build a `Request`, call, assert on the result.
- Components that use router hooks: `createRoutesStub` from `react-router` + Testing Library (see `react.md`).
- Playwright against `react-router build` and `react-router-serve` (see `e2e-testing.md`).
