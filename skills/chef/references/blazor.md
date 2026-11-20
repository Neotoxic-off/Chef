# Blazor

Builds on `csharp.md` and `aspnetcore.md`. Written for .NET 10 (LTS), .NET 11 (STS, Nov 2026) and bUnit 2.15 (Nov 2026), not benchmarked. Current versions: `dotnet --list-sdks`, and nuget.org for `bunit`.

## Render modes

- New apps: the Blazor Web App template. Static SSR is the default; add interactivity per page or component, not globally, unless the whole app needs it.
- Pick the smallest mode that works: static SSR (+ enhanced navigation and forms), then `InteractiveServer`, then `InteractiveWebAssembly`. Use `InteractiveAuto` only when both are needed: components must then run on server and client.
- Prerendering renders interactive components twice. Persist state across it with `[PersistentState]` on a public property (.NET 10+) instead of fetching twice. `OnAfterRender{Async}` does not run during prerendering.
- A `.Client` component that injects a client-only service fails during prerendering: register the service on the server too, or disable prerendering for that component (`new InteractiveWebAssemblyRenderMode(prerender: false)`).

## Components

- Markup in `.razor`, logic in a `.razor.cs` partial class, so the C# analyzers and house rules apply in full. Unverified: which analyzers also run on `@code` blocks.
- Types in `@code` and code-behind as in `csharp.md`: `var` when the type is apparent, explicit types otherwise. Inject services through the constructor (as in the .NET 10 docs), not `[Inject]` with `= default!`: `!` is banned (`csharp.md`). `[Parameter]` properties are set by the framework only; never assign them from inside the component.
  ```csharp
  public sealed partial class OrderDetails(IOrderService orders) : IDisposable
  {
      private readonly CancellationTokenSource cancellation = new();
      private OrderDto? order;

      [Parameter] public int Id { get; set; }

      protected override async Task OnParametersSetAsync() =>
          order = await orders.FindAsync(Id, cancellation.Token);

      public void Dispose()
      {
          cancellation.Cancel();
          cancellation.Dispose();
      }
  }
  ```
- Stable `@key` from the data on list items. `EventCallback<T>` for child-to-parent events, not `Action<T>`.
- Shared state: a scoped service with an event, or cascading values. No static mutable state: on the server it leaks between users.
- JS interop: load ES modules with `IJSRuntime.InvokeAsync<IJSObjectReference>("import", path)` and dispose them in `DisposeAsync`. On the server, disposing after the circuit is gone throws `JSDisconnectedException`; this is the one case where Microsoft documents a `try`/`catch`. Catch only that type and log it at Debug.

## Forms and security

- `EditForm` + `DataAnnotationsValidator`. Static SSR forms need `FormName` and `[SupplyParameterFromForm]`. .NET 11 runs async validation (`AsyncValidationAttribute`, `IAsyncValidatableObject`) and turns on client-side validation for static SSR forms that use `DataAnnotationsValidator`.
- Keep `app.UseAntiforgery()` after `UseHttpsRedirection()`. In .NET 11 the Razor Components endpoint no longer validates antiforgery tokens itself; the middleware does.
- WebAssembly code runs on the user's machine: no secrets, connection strings or keys in a `.Client` project. Enforce authorization in the server API; `AuthorizeView` only hides UI.
- `[Authorize]` only on routable `@page` components; use `AuthorizeView` for parts of a page.

## Tests

- bUnit for components, in an `X.Tests` project (xUnit v3, see `csharp.md`). Inherit `BunitContext` or create one per test; `Render<T>(...)` then assert:
  ```csharp
  [Fact]
  public void Render_WhenOrderMissing_ShowsNotFoundMessage()
  {
      Services.AddSingleton<IOrderService>(new FakeOrderService());
      IRenderedComponent<OrderDetails> cut = Render<OrderDetails>((ComponentParameterCollectionBuilder<OrderDetails> p) => p.Add((OrderDetails c) => c.Id, MissingOrderId));
      cut.Find("[role=alert]").TextContent.ShouldContain(OrderDetails.NotFoundMessage);
  }
  ```
- Mock JS with bUnit's `JSInterop` (strict by default: unplanned calls throw), not a hand-written `IJSRuntime`. Keep strict mode.
- `bunit.web.query` offers Testing Library queries by role and label, but it is experimental: ask before adding it.
- Playwright (`e2e-testing.md`) for render-mode switches, prerendering and navigation, against the published app.
