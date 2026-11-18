# Storybook

Builds on `typescript.md` and the UI framework's file (`react.md`, `vue.md`...). Verified against Storybook 10.6, @storybook/addon-vitest 10.6, @storybook/addon-a11y 10.6, eslint-plugin-storybook 10.6, Vitest 5.1 (Nov 2026). Look up the current version with `npm view storybook version`; upgrade with `npx storybook@latest upgrade`.

## Setup

- Storybook 10 is ESM-only: `.storybook/main.ts` must be valid ESM, and Node 20.19+ or 22.12+ is required.
- Use a Vite-based framework package (`@storybook/react-vite`, `@storybook/vue3-vite`, `@storybook/sveltekit`...): the Vitest addon needs Vite.
- Keep every `storybook` and `@storybook/*` package on the same version.
- Lint stories with the official plugin:
  ```js
  import storybook from "eslint-plugin-storybook";

  ...storybook.configs["flat/recommended"],
  ```
- Story files need a default export (the meta): this is a framework requirement, the one allowed exception to named exports.

## Stories

- CSF 3 with explicit types. CSF Next (`preview.meta` / `meta.story`) is still a preview feature in Storybook 10: do not adopt it without asking.
  ```ts
  import type { Meta, StoryObj } from "@storybook/react-vite";
  import { expect } from "storybook/test";
  import { SaveButton } from "./SaveButton";

  const meta: Meta<typeof SaveButton> = {
    component: SaveButton,
    parameters: { a11y: { test: "error" } },
  };
  export default meta;

  type Story = StoryObj<typeof SaveButton>;

  export const DisabledWhileSaving: Story = {
    args: { saving: true },
    play: async ({ canvas }): Promise<void> => {
      await expect(canvas.getByRole("button", { name: "Save" })).toBeDisabled();
    },
  };
  ```
- Name each story after the state it shows (`DisabledWhileSaving`, `EmptyList`), not `Default` / `Story1`: the Vitest addon turns stories into tests with these names.
- One story per meaningful state: empty, loading, error, long content, each permission level.
- Stories render components with props and mocked providers only; no real network calls. Mock HTTP with MSW (`msw-storybook-addon`) or pass data through args.
- `play` functions use `canvas` queries by role, label or text, and `userEvent` from the context; await every interaction (`storybook/await-interactions` checks it).
- Import test helpers from `storybook/test`, not the old `@storybook/test` package.

## Tests

- Run stories as tests with `@storybook/addon-vitest`: a separate Vitest project with the `storybookTest()` plugin and browser mode (`provider: playwright()` from `@vitest/browser-playwright`, Chromium, headless). Add it with `npx storybook add @storybook/addon-vitest`.
- Accessibility: `@storybook/addon-a11y` with `parameters: { a11y: { test: "error" } }` in `.storybook/preview.ts`, so violations fail CI. `"todo"` hides them in CI: use it only for a baseline the user approved, with an issue to fix each one.
- Stories count toward coverage (the addon computes it), but business logic still needs its own unit tests.
- The older Jest-based test-runner is for non-Vite frameworks only.
- Visual regression (Chromatic or Playwright `toHaveScreenshot`) only if the project already has it or the user asks.
