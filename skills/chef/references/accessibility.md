# Accessibility (WCAG 2.2)

Checked November 2026 against WCAG 2.2 (W3C Recommendation, also ISO/IEC 40500:2025), axe-core 4.14 and @axe-core/playwright 4.14. WCAG 3 is still a Working Draft: do not target it.

## Target

- WCAG 2.2 level AA for every UI. It is the level that laws and procurement rules point to (e.g. the European Accessibility Act, in force since 28 June 2025).
- Criteria new in 2.2 to check by hand: Focus Not Obscured (2.4.11), Dragging Movements (2.5.7, give a single-pointer alternative), Target Size Minimum (2.5.8, 24 by 24 CSS px), Consistent Help (3.2.6), Redundant Entry (3.3.7), Accessible Authentication (3.3.8, allow paste and password managers, no cognitive tests).

## Markup

- Native HTML first: `<button>`, `<a href>`, `<label>`, `<fieldset>`, `<dialog>`, landmarks (`<main>`, `<nav>`). ARIA only when no element does the job, and then the full pattern from the ARIA Authoring Practices Guide.
- Every input has a visible `<label>`. Errors name the field, say how to fix it, and are tied with `aria-describedby`.
- Images: meaningful `alt`, `alt=""` for decoration. Icon-only buttons get an accessible name.
- `<html lang>` set; `lang` on passages in another language.
- One `<h1>`, headings in order.

## Keyboard, focus, motion, color

- Everything works with the keyboard alone, in a logical order, with no traps. No positive `tabindex`.
- Focus stays visible and is never hidden under sticky headers. Move focus into dialogs and back out on close.
- Contrast: 4.5:1 for text, 3:1 for large text, icons and focus indicators. Never use color as the only signal.
- Respect `prefers-reduced-motion`. Nothing flashes more than 3 times per second.
- Content reflows at 320 CSS px width and 200% text zoom without loss.
- Announce dynamic updates (toasts, async results) through an `aria-live` region.

## Lint

- React: `eslint-plugin-jsx-a11y` with `jsxA11y.flatConfigs.recommended`. Vue: `eslint-plugin-vuejs-accessibility`. Angular: the `@angular-eslint` template accessibility rules.
- Fix findings; never disable a rule inline.

## Tests

```ts
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { AxeResults } from "axe-core";

const WCAG_22_AA_TAGS: string[] = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test("checkout page has no detectable WCAG 2.2 AA violations", async ({ page }): Promise<void> => {
  await page.goto("/checkout");
  const results: AxeResults = await new AxeBuilder({ page }).withTags(WCAG_22_AA_TAGS).analyze();
  expect(results.violations).toEqual([]);
});
```

- Run axe on every page and on each state that changes the DOM (open dialog, error state).
- Component tests: Testing Library queries by role and label (`getByRole("button", { name: "Pay" })`). A query that cannot find the element by role is an accessibility bug.
- Automated tools find only part of the problems. Before release, test by hand: keyboard only, a screen reader (NVDA or JAWS on Windows, VoiceOver on macOS and iOS, TalkBack on Android), and 200% zoom.
