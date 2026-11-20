# Phoenix

Builds on `elixir.md`. Written for Phoenix 1.8.16 and LiveView 1.2.13, not benchmarked. Current versions: `mix hex.info phoenix` and `mix hex.info phoenix_live_view`; upgrade notes in each package's `CHANGELOG.md` on HexDocs.

## Structure

- Web layer (controllers, LiveViews) calls context functions only. No `Repo` calls outside contexts.
- Scopes (1.8): pass `current_scope` as the first argument of every context function and filter queries by it. `mix phx.gen.auth` and the 1.8 generators already do this; keep the pattern in hand-written code.
- Verified routes (`~p"/orders/#{order}"`) for every path; never build path strings.
- Secrets and URLs in `config/runtime.exs` with `System.fetch_env!/1`, never in compile-time config.

```elixir
@spec get_order(Scope.t(), integer()) :: {:ok, Order.t()} | {:error, :not_found}
def get_order(%Scope{} = scope, id) do
  case Repo.get_by(Order, id: id, user_id: scope.user.id) do
    nil -> {:error, :not_found}
    %Order{} = order -> {:ok, order}
  end
end
```

## Input and errors

- Validate at the boundary with changesets: `cast/3` with an explicit field list (never cast `user_id` or roles from params), then `validate_*` and `unique_constraint`. Non-database input: schemaless changesets (`{%{}, types}`).
- Controllers return context results and let `action_fallback MyAppWeb.FallbackController` turn `{:error, :not_found}` and `{:error, %Ecto.Changeset{}}` into responses. No `rescue` in controllers.
- HTTP clients: `Req` (the 1.8 default); stub it in tests with `Req.Test`.

## LiveView

- Authorize in `on_mount` hooks *and* in every `handle_event`: a client can send any event with any `phx-value-*`. Re-load records through the scope, never trust ids from the socket.
- Slow loads with `assign_async` / `start_async`; large or growing lists with `stream/3`.
- Keep logic in contexts; LiveViews map events to context calls and assigns.

## Checks

- Generated apps have a `precommit` alias (`compile --warnings-as-errors`, `deps.unlock --unused`, `format`, `test`). Extend it, do not replace it:
  ```elixir
  precommit: ["compile --warnings-as-errors", "deps.unlock --unused", "format", "credo --strict", "sobelow --exit Low", "test"]
  ```
- Sobelow (security) fails on any finding with `--exit Low`. Its `# sobelow_skip` comments and `.sobelow-conf` ignore lists are suppressions: forbidden (see SKILL.md); fix the finding or ask the user.

## Tests

- `ConnCase` with `Phoenix.ConnTest` for controllers; assert status and body:
  ```elixir
  test "get order when missing returns 404", %{conn: conn} do
    conn = get(conn, ~p"/api/orders/0")
    assert json_response(conn, :not_found)
  end
  ```
- LiveView: `Phoenix.LiveViewTest` (`live/2`, `render_submit/2`, `has_element?/3`). 1.8 apps parse HTML with `LazyHTML` (replaces Floki in generated tests).
- `DataCase` with the Ecto SQL Sandbox so database tests run `async: true`.
- Test each context function through its scope, including the "other user's record" case.
