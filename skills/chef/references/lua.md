# Lua

Name the runtime first (Lua 5.4, LuaJIT, Neovim, Roblox Luau, LÖVE): it sets the `std` for every tool below. Install tools with LuaRocks (`.rockspec` committed).

## Lint and format: StyLua + selene (or luacheck)

`stylua.toml`:

```toml
column_width = 100
indent_type = "Spaces"
indent_width = 2
quote_style = "AutoPreferDouble"
call_parentheses = "Always"
```

CI: `stylua --check .`.

Linter: selene, or luacheck if the project already uses it.

- `selene.toml`: `std = "lua54"`. selene fails on warnings by default; never pass `--allow-warnings`.
- `.luacheckrc`: `std = "lua54"`, `max_line_length = 100`, `unused_args = true`. luacheck exits 1 on any warning.

## Types: LuaLS annotations

- Explicit types (see SKILL.md): annotate every function, field and local with LuaCATS comments.
  ```lua
  ---@class Account
  ---@field id integer
  ---@field balance number

  ---@param account Account
  ---@param amount number
  ---@return boolean ok
  ---@return string? err
  local function withdraw(account, amount) end

  ---@type integer
  local retries = 0
  ```
- `.luarc.json`: set `runtime.version`, and raise type diagnostics (`param-type-mismatch`, `return-type-mismatch`, `missing-parameter`, `undefined-field`) to `Error`.
- Check in CI with `lua-language-server --check . --checklevel=Warning` (or the `llscheck` wrapper, which exits non-zero on findings).
- No `any` unless the value is truly untyped; narrow with `type(x) == "..."` right away.

## Code

- `local` for everything. No globals; modules return a table.
- Errors: return `nil, err` for expected failures; `error()` only for bugs. Wrap boundaries with `pcall`.
- Constructors (`M.new`) take dependencies as arguments; no `require` of I/O modules inside logic.
- Use `#` only on sequences. Use `ipairs` for arrays, `pairs` for maps.
- No `setfenv`/`load` of untrusted strings.

## Tests

- busted with `describe`/`it`; spies and stubs from `luassert`. `.busted`:
  ```lua
  return { default = { coverage = true, verbose = true } }
  ```
- Integration tests in `spec/integration/`, tagged `#integration`, run against real services in containers.
- Coverage: luacov (line coverage only; no branch coverage). It has no built-in threshold: in CI, read the `Total` line of `luacov.report.out` and fail under 90%.
- No maintained mutation testing tool exists for Lua.

Order before done: `stylua .` then `selene .` (or `luacheck .`) then the LuaLS check then `busted --coverage && luacov`.
