# Tailwind CSS

Written for Tailwind CSS 4.3, prettier-plugin-tailwindcss 0.8, eslint-plugin-better-tailwindcss 4.11 (Nov 2026), not benchmarked.

## Setup

- Tailwind v4 is configured in CSS, not in `tailwind.config.js`. Use the bundler plugin (`@tailwindcss/vite`, or `@tailwindcss/postcss`) and one entry stylesheet:
  ```css
  @import "tailwindcss";

  @theme {
    --color-brand-500: oklch(0.62 0.19 255);
    --color-surface: oklch(0.99 0 0);
    --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
    --radius-card: 0.75rem;
  }

  @custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));
  ```
- Keep a `tailwind.config.js` only in an existing v3 project; migrate with `npx @tailwindcss/upgrade`.

## Class order and lint

- Sort classes with `prettier-plugin-tailwindcss`. For v4 it needs the entry stylesheet:
  ```json
  {
    "plugins": ["prettier-plugin-tailwindcss"],
    "tailwindStylesheet": "./src/app.css",
    "tailwindFunctions": ["clsx", "cva", "cn"]
  }
  ```
- Catch unknown or conflicting classes with `eslint-plugin-better-tailwindcss` `configs.correctness` (set `settings["better-tailwindcss"].entryPoint`). Leave its `stylistic` rules off: Prettier owns ordering and wrapping.

## Design tokens

- Every color, font, spacing step, radius and shadow the design uses is a `@theme` variable. No arbitrary values (`bg-[#3b82f6]`, `p-[13px]`) for things that belong in the theme.
- Replace a whole default palette with `--color-*: initial;` before defining your own, so off-brand colors cannot be used.
- Name tokens by role (`surface`, `brand`, `danger`), not by hue, so dark mode swaps values, not class names.
- Read tokens elsewhere as CSS variables (`var(--color-brand-500)`), never copy their values.

## Code

- Write complete class names; Tailwind cannot see names built at runtime (`` `bg-${color}-500` ``). Map props to full class strings:
  ```ts
  const toneClasses: Record<Tone, string> = { info: "bg-sky-100 text-sky-900", danger: "bg-red-100 text-red-900" };
  ```
- Long or repeated class lists become a component (React, Vue, Svelte), not `@apply`. Use `@apply` only to style markup you do not control.
- Merge conditional classes with `clsx`; resolve conflicting overrides with `tailwind-merge` only in shared components that accept a `className`.
- Register class sources outside the project with `@source`; never safelist by hand when `@source inline(...)` fits.

## Accessibility

- Every interactive element keeps a visible focus style: `focus-visible:outline-2 focus-visible:outline-offset-2`. Never `outline-none` without a replacement.
- Text and UI tokens meet WCAG AA contrast (4.5:1 for body text, 3:1 for large text and UI) in light and dark themes.
- Hide visually but keep for screen readers with `sr-only`; never `hidden` on content a screen reader needs.
- Respect motion settings: animations behind `motion-safe:`, or remove them with `motion-reduce:`.
- Touch targets at least 24 by 24 CSS pixels (`min-h-6 min-w-6`); 44 by 44 for primary mobile controls.
