# SolidJS

Builds on `typescript.md`. Written for solid-js 2.0.1, @solidjs/vite-plugin 3.0, @solidjs/router 2.0, eslint-plugin-solid 0.20, SolidStart 2.2 (Nov 2026), not benchmarked. Current versions: `npm view solid-js dist-tags`, and `npm view @solidjs/start peerDependencies` to see which Solid a framework supports.

## Which Solid

- Solid 2.0 shipped on 2026-11-17. New apps start on 2.0 from `solidjs/templates/solid-v2/*` (`bare`, `basic`, `fullstack`).
- In 2.0, `@solidjs/vite-plugin` with `start: true` (add `ssr: true` for streaming SSR) is the app layer and replaces SolidStart.
- SolidStart 2.2 still requires `solid-js ^1.9`, `vite-plugin-solid` 2 and `@solidjs/router` < 2. Keep existing Start apps on 1.9 until its peer range allows 2.0.
- Migrate 1.x code with the official guide (`documentation/solid-2.0/MIGRATION.md` in `solidjs/solid`). Main renames: `solid-js/web` to `@solidjs/web`, `solid-js/store` to `solid-js`, `Suspense` to `Loading`, `ErrorBoundary` to `Errored`, `onMount` to `onSettled`, `Index` to `<For keyed={false}>`, `mergeProps`/`splitProps` to `merge`/`omit`.

## Setup (2.0)

- `tsconfig.json`: `"jsx": "preserve"`, `"jsxImportSource": "@solidjs/web"`.
- The official template ships TypeScript 7 and oxlint. Keep TypeScript `~6.0` and typed ESLint per `typescript.md` until typescript-eslint supports 7.
- ESLint: the `v2` config of eslint-plugin-solid (the one the 2.0 templates ship), added to the flat config from `typescript.md`:
  ```js
  import solid from "eslint-plugin-solid/configs/v2";

  solid,
  ```
  Its `reactivity` rule catches destructured props and top-level reactive reads; fix the code, never silence it. 1.x projects use `eslint-plugin-solid/configs/typescript`.

## Components

- Props are values, not accessors. Read `props.x` in JSX; never destructure props, and pass `count()`, not `count`, at the call site.
- Type props with an interface and give components a return type:
  ```tsx
  import { createMemo, createSignal, For, type Accessor, type Signal, type SourceAccessor } from "solid-js";
  import type { JSX } from "@solidjs/web";

  interface TodoListProps {
    readonly todos: readonly Todo[];
    readonly onToggle: (id: string) => void;
  }

  export function TodoList(props: TodoListProps): JSX.Element {
    const [showDone, setShowDone]: Signal<boolean> = createSignal<boolean>(true);
    const visible: SourceAccessor<readonly Todo[]> = createMemo((): readonly Todo[] =>
      props.todos.filter((todo: Todo): boolean => showDone() || !todo.done));
    return (
      <>
      <button type="button" onClick={(): void => setShowDone(!showDone())}>Toggle done</button>
      <ul>
        <For each={visible()} keyed={(todo: Todo): string => todo.id}>
          {(todo: Accessor<Todo>): JSX.Element => <li><button type="button" onClick={(): void => props.onToggle(todo().id)}>{todo().title}</button></li>}
        </For>
      </ul>
      </>
    );
  }
  ```
- Event handlers are camelCase (`onClick`). In 2.0, lowercase `onclick` sets an attribute.
- Derive with `createMemo`. `createEffect` takes two functions (compute, then apply) and is only for syncing with the outside world; never use it to derive state.
- Component setup and teardown: `onSettled` returning a cleanup, not `onCleanup`.
- Async data: a `createMemo` that returns a promise, under a `<Loading>` boundary; `isPending(() => value())` for "updating" UI. No `createResource` in 2.0 code.
- Mutations: `action(function* () { ... })` with `createOptimistic` / `createOptimisticStore`, then `refresh(...)`.
- Stores: `createStore` from `solid-js` with draft setters; `snapshot(store)` for a plain copy.

## Tests

- Vitest + jsdom. `@solidjs/testing-library` 1.0 (still RC) for 2.0; 0.8 for 1.x. Query by role and label, `user-event` for input.
- Playwright for end-to-end (see `e2e-testing.md`).
