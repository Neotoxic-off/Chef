# htmx

Server-agnostic: read with the file for the server stack. Verified against htmx 2.0.11 and 4.0 (Nov 2026). Look up versions with `npm view htmx.org dist-tags`.

## Version

- htmx 4.0 shipped on 2026-08-28 but is on the npm `next` tag; `latest` stays 2.x until some point in 2027, and 2.x is supported indefinitely. The htmx.org site documents 4.0; 2.x docs remain at htmx.org/docs.
- Existing 2.x project: stay on 2.x unless the user asks to upgrade. New project: ask the user which line to use.
- Pin an exact version and self-host the file (or use npm). Never load an unversioned CDN URL. With a CDN, add `integrity` (SRI) and `crossorigin`.
- Upgrading 2 to 4: run `npx htmx.org@4.0.0 upgrade-check -- ./templates`, then read "What's New in htmx 4". Main breaks:
  - Inheritance is explicit: `hx-target:inherited`, `hx-headers:inherited` (a CSRF header on `<body>` stops reaching children without it).
  - `hx-disable` now means "disable during request"; the old meaning is `hx-ignore`.
  - Events are `htmx:phase:action` (`htmx:afterRequest` is `htmx:after:request`).
  - 4xx/5xx responses are swapped; default timeout is 60 s; no `localStorage` history cache; extensions load by `<script>` alone, no `hx-ext`.

## Server responses

- Same URL serves a full page or a fragment: branch on the `HX-Request` header and send `Vary: HX-Request`. In 2.x set `htmx.config.historyRestoreAsHxRequest = false` so history restores get full pages.
- Return HTML fragments, not JSON. Render them with the same templates as full pages.
- Status codes carry meaning. Validation errors: `422` with the form fragment.
  - 2.x does not swap 4xx/5xx by default. Swap `422` through `htmx.config.responseHandling` (or the `response-targets` extension).
  - 4.x swaps everything except `204`/`304`. Route codes with `hx-status:422="target:#errors"` and `hx-status:5xx="swap:none"`.
- After a mutation, return the new fragment with `200`; no Post/Redirect/Get needed. To navigate, send `200` + `HX-Redirect` or `HX-Location`. Never `3xx`: the browser follows it internally and htmx never sees your `HX-*` headers.
- `hx-boost` turns links and forms into AJAX swaps of `<body>`. Every boosted URL must still work without JavaScript: build the plain links and forms first.

## Security

- Escape every dynamic value with an auto-escaping template engine. User content goes only inside HTML elements; never inside `<script>`, `<style>`, tag names or attribute names. Never write `hx-*` values from user input.
- Wrap any raw user HTML in `hx-disable` (2.x) or `hx-ignore` (4.x) so htmx ignores attributes in it.
- Requests stay same-origin: `selfRequestsOnly` is `true` by default in 2.x; `htmx.config.mode` is `'same-origin'` by default in 4.x. Do not loosen either.
- CSP: `hx-on`, trigger filters and `js:` values use `eval`. 2.x: set `allowEval: false` when you do not use them, then drop `'unsafe-eval'`. Set `inlineScriptNonce` if swapped content has inline scripts. Unverified: how 4.x evaluates `hx-on` under a strict CSP.
- CSRF: send the token with `hx-headers` on `<body>` (`:inherited` in 4.x), or a hidden form input. Auth cookies: `Secure; HttpOnly; SameSite=Lax`.
- Re-validate every input on the server; htmx client validation is UX only.

## Code

- Behavior in attributes, not scripts. Keep `hx-on` short; move anything longer than a line into a typed TS module (`typescript.md`) that listens for htmx events.
- Name config values once, in `<meta name="htmx-config">`, not scattered `htmx.config` writes.
- Give every swap target a stable `id`. Prefer `hx-target` + `hx-swap="outerHTML"` on the element that owns the state.
- Show progress with `hx-indicator`; disable the trigger during the request (`hx-disabled-elt` in 2.x, `hx-disable` in 4.x).

## Tests

- Server side: test each handler returns the right fragment, status and `HX-*` headers, with and without `HX-Request`.
- Browser: Playwright (`e2e-testing.md`). Wait on what the user sees (`await expect(page.getByRole("row")).toHaveCount(expectedRows)`), never on timeouts. Run a no-JavaScript project (`javaScriptEnabled: false`) over boosted pages.
