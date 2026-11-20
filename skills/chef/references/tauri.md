# Tauri

Builds on `rust.md` (backend) and `typescript.md` (frontend). Written for the Tauri 2 security docs (capabilities) and registries: tauri 2.12.7, @tauri-apps/api 2.12.5, tauri-specta 2.0.0-rc.29 (Nov 2026; tauri 3 is alpha), not benchmarked. Current versions: `cargo info tauri`, `npm view @tauri-apps/api version`. Keep the Rust crates and the npm packages on the same minor.

## Capabilities: least privilege

- One capability file per window or role in `src-tauri/capabilities/`, granting only the permissions that window uses:
  ```json
  {
    "$schema": "../gen/schemas/desktop-schema.json",
    "identifier": "main-capability",
    "windows": ["main"],
    "permissions": ["core:default", "dialog:allow-open", "allow-load-note"]
  }
  ```
- Capabilities match windows by label, and a window in several capabilities gets the union: keep labels distinct.
- No wildcard or broad permissions (`fs:default` plus a `**` scope). Narrow file scopes to app directories (`$APPDATA/...`).
- Once `app.security.capabilities` is listed in `tauri.conf.json`, only those files apply; otherwise every file in the folder is active. List them explicitly.
- No `remote` URLs in a capability unless the app truly loads remote content; then grant that origin the minimum.
- Each custom command gets its own permission (`[[permission]]` with `commands.allow` in `src-tauri/permissions/*.toml`), so a capability names exactly what it can call.

## Security config

- Set a strict `app.security.csp` (`default-src 'self'`); no `unsafe-eval`, no remote scripts.
- Frontend dependencies you do not trust fully: use the Isolation pattern so IPC passes through an isolated script first.
- Ship the updater only with signed updates; keep the private key out of the repo and CI logs.

## Commands

- Commands are thin: parse input, call a plain Rust function, map the error. Logic lives in modules testable without Tauri.
- Return `Result<T, Error>` with one error enum per domain; it must serialize, so give it an explicit string form:
  ```rust
  #[derive(Debug, thiserror::Error)]
  pub enum Error {
      #[error(transparent)]
      Io(#[from] std::io::Error),
      #[error("note {0} not found")]
      NotFound(NoteId),
  }

  impl serde::Serialize for Error {
      fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
          serializer.serialize_str(&self.to_string())
      }
  }

  #[tauri::command]
  async fn load_note(id: NoteId, store: tauri::State<'_, NoteStore>) -> Result<Note, Error> {
      let note: Note = store.load(id).await?;
      Ok(note)
  }
  ```
- Async commands that borrow (`State<'_, T>`, `&str`) must return `Result`.
- Never trust arguments from the webview: validate paths, ids and sizes in the command.
- Type the frontend side: wrap each `invoke<Note>("load_note", { id })` in one typed function per command, or generate bindings with tauri-specta (still a release candidate: ask before adding).

## Tests

- Rust logic: `cargo test` plus coverage and mutation tools from `rust.md`.
- Commands: Tauri's mock runtime (`tauri::test`, behind the `test` feature) to call commands without a window.
- Frontend: Vitest with `mockIPC` from `@tauri-apps/api/mocks`; clear mocks after each test with `clearMocks()`.
- End to end: WebDriver. Driven directly, `tauri-driver` supports only Windows and Linux; macOS needs the WebdriverIO service's embedded WebDriver server (see the Tauri WebDriver docs).

Order before done: `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test`, then the frontend checks from `typescript.md`, then `npm run tauri build` on at least one platform.
