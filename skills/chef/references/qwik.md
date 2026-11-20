# Qwik and Qwik City

Builds on `typescript.md`. Written for Qwik 1.20.4 (`@builder.io/qwik`, `@builder.io/qwik-city`), eslint-plugin-qwik 1.20.4, and Qwik 2.0.0-rc.5 (Nov 2026), not benchmarked. Look up versions with `npm view @builder.io/qwik dist-tags` and `npm view @qwik.dev/core dist-tags`.

## Version

- Qwik 1 is the stable line. Qwik 2 is still a release candidate, under new package names (`@qwik.dev/core`, `@qwik.dev/router`, which replaces Qwik City). Do not start or migrate to Qwik 2 without asking the user.
- Qwik 1.20 peer-depends on `vite >=5 <8`: stay on Vite 7. Qwik 2 RC needs Vite 8 and `vitest <5`.

## Lint

- Add the plugin to the flat config from `typescript.md`. Typed rules need `projectService` and `tsconfigRootDir`, already set there:
  ```js
  import { qwikEslint9Plugin } from "eslint-plugin-qwik";

  qwikEslint9Plugin.configs.recommended,
  ```
  `configs.strict` turns the a11y and JSX warnings (`jsx-a`, `jsx-img`, `jsx-key`, `prefer-classlist`) into errors; use it in new projects.
- `qwik/no-use-visible-task` warns on every `useVisibleTask$`. The Qwik docs suggest an `eslint-disable` comment: never do that (see SKILL.md). Rewrite with `useTask$` or `useOn*`; if no rewrite works, stop and ask the user.

## Components

- `component$` for components, `$()` for any function that crosses a lazy boundary (event handlers, tasks, functions captured by them). Captured values must be serializable; `qwik/valid-lexical-scope` checks this.
- Route files need `export default component$(...)`: a framework-required default export (`typescript.md`). Other components use named exports.
  ```tsx
  import { component$, useComputed$, useSignal, type JSXOutput, type Signal } from "@builder.io/qwik";
  import { routeLoader$, type RequestEventLoader } from "@builder.io/qwik-city";

  export const useProduct = routeLoader$(async (event: RequestEventLoader): Promise<Product> =>
    productSchema.parse(await fetchProduct(event.params.productId)));

  export default component$((): JSXOutput => {
    const product: Readonly<Signal<Product>> = useProduct();
    const quantity: Signal<number> = useSignal<number>(MIN_QUANTITY);
    const total: Signal<number> = useComputed$((): number => quantity.value * product.value.price);
    return <button type="button" onClick$={(): void => { quantity.value++; }}>{total.value}</button>;
  });
  ```
- Derive values with `useComputed$`, or inline them in JSX; reading a signal in the component body re-runs the whole component.
- `useTask$` to react to state (runs on the server too, `track()` its inputs). `useVisibleTask$` only as a last resort: it runs eagerly on the client and blocks the main thread. DOM events: `useOn`, `useOnWindow`, `useOnDocument`.
- Read the URL with `useLocation()`, never `window.location`.

## Qwik City

- `routeLoader$` only in `src/routes` `layout.tsx` / `index.tsx`, exported, named `use*`, with the function inlined so server code never leaks to the client (the plugin checks all three).
- Mutations: `routeAction$` with `zod$(...)` validation and `<Form action={...}>`, so forms work without JavaScript. Read `action.value?.fieldErrors` for errors. Check auth inside each action and loader.
- Server-only helpers live in modules imported only by loaders, actions or `server$` functions. Secrets come from `event.env.get(...)`, never `import.meta.env` in client code (unverified: whether the plugin flags this).

## Tests

- Vitest with `createDOM` from `@builder.io/qwik/testing`. `npm run qwik add vitest` pins Vitest `^0.34`: bump it to the current version Qwik's Vite range allows.
  ```tsx
  test("adds one to the counter on click", async (): Promise<void> => {
    const { screen, render, userEvent } = await createDOM();
    await render(<Counter />);
    await userEvent("button", "click");
    expect(screen.querySelector("output")?.textContent).toBe(EXPECTED_COUNT);
  });
  ```
  `createDOM` has no role queries: select by element or label, not by class.
- Playwright (`e2e-testing.md`) against `npm run build && npm run preview`, to cover resumability and loaders/actions.
