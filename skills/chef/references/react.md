# React

Builds on `typescript.md`. Verified against React 19.3, eslint-plugin-react-hooks 7.1, TanStack Query 5, Zustand 5, Testing Library 16, Vitest 5 (Nov 2026).

## Lint and config

- Add the official hooks plugin to the flat config from `typescript.md`. Its `recommended` preset includes the React Compiler rules (`purity`, `refs`, `set-state-in-effect`, `immutability`...):
  ```js
  import reactHooks from "eslint-plugin-react-hooks";
  import jsxA11y from "eslint-plugin-jsx-a11y";
  import pluginQuery from "@tanstack/eslint-plugin-query";

  reactHooks.configs.flat.recommended,
  jsxA11y.flatConfigs.recommended,
  ...pluginQuery.configs["flat/recommended"],
  ```
- `exhaustive-deps` ships as a warning; warnings are errors (see SKILL.md), so fix every one by changing the code, never by dropping a dependency.
- React Compiler 1.0 is stable (`babel-plugin-react-compiler`). With it on, do not add `useMemo`, `useCallback` or `memo` by hand; keep the ones that exist.

## Components

- Function components only. Type props with an interface and give every component an explicit return type:
  ```tsx
  interface UserCardProps {
    readonly user: User;
    readonly onSelect: (id: string) => void;
  }

  export function UserCard({ user, onSelect }: UserCardProps): React.JSX.Element {
    return <button type="button" onClick={(): void => onSelect(user.id)}>{user.name}</button>;
  }
  ```
- `ref` is a regular prop in React 19: no `forwardRef` in new code.
- Components and hooks are pure: no side effects, no mutation of props or state during render.
- Derive values during render instead of syncing them with `useEffect`. Use an effect only to sync with something outside React; put non-reactive logic in `useEffectEvent`.
- Call hooks only at the top level of components and custom hooks (`use*`), never in conditions or loops.
- Stable, unique `key` from the data, never the array index for lists that change.

## State and data

- Server data: TanStack Query, not `useEffect` + `fetch`. Validate the response at the boundary (zod), then type the query: `useQuery<User[], Error>({ queryKey: ["users"], queryFn: fetchUsers })`.
- Query keys are arrays that contain every variable the `queryFn` uses (the query ESLint plugin checks this).
- Local UI state: `useState` / `useReducer`. Shared client state: Zustand with the curried typed form, read through narrow selectors:
  ```ts
  export const useCartStore = create<CartState>()((set) => ({ items: [], clear: (): void => set({ items: [] }) }));
  const count: number = useCartStore((state: CartState): number => state.items.length);
  ```
  Wrap selectors that return objects or arrays in `useShallow`.
- Forms: React Hook Form with `zodResolver`, or React 19 `<form action>` + `useActionState` for simple server-backed forms.

## Accessibility

- Native elements first (`<button>`, `<a href>`, `<label>`). Every input has a label; every icon-only button has an `aria-label`.
- Keyboard must reach and operate everything; keep a visible focus style.

## Tests

- React Testing Library + `@testing-library/user-event`. Query by role, label or text, in that order; never by class or test id.
- `await user.click(...)` then assert with `findBy*` for async UI. No manual `act()` around RTL helpers.
- Mock the network at the boundary with MSW, not the hooks or the store.
- Playwright for flows across pages; add `@axe-core/playwright` checks on key pages.
