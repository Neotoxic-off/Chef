# Electron

Builds on `typescript.md` (and `react.md` for a React renderer). Verified against the Electron security tutorial (latest docs) and npm: electron 45.3.4, @electron/fuses 2.1.3 (Nov 2026). Current version: `npm view electron version`. Upgrade one major at a time with the Breaking Changes page; an unsupported major gets no Chromium security fixes.

## Security (non-negotiable)

- Every `BrowserWindow` / `WebContentsView` keeps the isolation settings on. Write them out so a reviewer sees them:
  ```ts
  const mainWindow: BrowserWindow = new BrowserWindow({
    webPreferences: { preload: PRELOAD_PATH, contextIsolation: true, sandbox: true, nodeIntegration: false },
  });
  ```
  `contextIsolation` is the default since Electron 12 and `sandbox` since 20. Turning off context isolation also turns off the sandbox.
- Never set `webSecurity: false`, `allowRunningInsecureContent`, `experimentalFeatures` or `enableBlinkFeatures`.
- Content Security Policy on every page, starting from `default-src 'self'; script-src 'self'`. No `unsafe-eval`, no remote scripts.
- Load the app from a custom protocol (`protocol.handle`), not `file://`.
- Block navigation and new windows; open allowlisted links in the system browser:
  ```ts
  contents.on("will-navigate", (event: Electron.Event): void => event.preventDefault());
  contents.setWindowOpenHandler(({ url }: Electron.HandlerDetails): Electron.WindowOpenHandlerResponse => {
    if (isAllowedExternalUrl(url)) void shell.openExternal(url);
    return { action: "deny" };
  });
  ```
- Never pass untrusted input to `shell.openExternal`; allowlist scheme and host.
- Remote content: `session.setPermissionRequestHandler` denies everything the app does not need.
- Flip fuses at package time with `@electron/fuses`: turn off `RunAsNode`, `EnableNodeOptionsEnvironmentVariable`, `EnableNodeCliInspectArguments`; turn on `EnableEmbeddedAsarIntegrityValidation` and `OnlyLoadAppFromAsar`. Check which fuses your version has before flipping.

## IPC

- The preload exposes one narrow function per action through `contextBridge`. Never expose `ipcRenderer`, `require` or a generic `send(channel, ...)`:
  ```ts
  const settingsApi: SettingsApi = {
    load: (): Promise<Settings> => ipcRenderer.invoke(Channel.LoadSettings) as Promise<Settings>,
  };
  contextBridge.exposeInMainWorld("settings", settingsApi);
  ```
- Main validates the sender of every message by frame origin against an allowlist, then validates the payload with zod. The renderer is untrusted.
  ```ts
  ipcMain.handle(Channel.SaveSettings, (event: IpcMainInvokeEvent, input: unknown): Promise<void> => {
    if (event.senderFrame?.origin !== APP_ORIGIN) throw new UntrustedSenderError();
    return saveSettings(settingsSchema.parse(input));
  });
  ```
- `invoke`/`handle` for request-response; channel names are constants in one shared module. Share the `SettingsApi` type, never code, between main and renderer.
- Sandboxed preloads cannot load Node modules beyond the few Electron allows: bundle the preload.

## Structure and tooling

- Three TypeScript projects: `main`, `preload`, `renderer`, each with its own tsconfig `lib` (no DOM types in main, no Node types in renderer).
- Package and sign with Electron Forge (the officially recommended tool) unless the project already uses electron-builder.

## Tests

- Main-process logic as plain functions tested with Vitest (`typescript.md`); IPC handlers tested by calling them with a fake event.
- Renderer: as for any web UI (`react.md`), with `window.settings` replaced by a typed fake.
- End to end: Playwright's Electron support (`_electron.launch`), still marked experimental by Playwright.
