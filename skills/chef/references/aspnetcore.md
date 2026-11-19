# ASP.NET Core

Builds on `csharp.md`. Verified against ASP.NET Core 10.0.15 (LTS) and 11.0.0 (STS, released 10 Nov 2026) (Nov 2026).

## Endpoints

- New HTTP APIs: minimal APIs, one static class per feature with a `Map<Feature>Endpoints` extension and `MapGroup`. Keep controllers in a project that already uses them; do not mix both styles in one feature.
- Return `TypedResults` with an explicit `Results<...>` return type, so OpenAPI and tests see every outcome.
- Handlers stay thin: bind, call an injected service, map the result. Pass the `CancellationToken`.

```csharp
public static class OrderEndpoints
{
    public static RouteGroupBuilder MapOrderEndpoints(this IEndpointRouteBuilder routes)
    {
        RouteGroupBuilder group = routes.MapGroup("/orders").RequireAuthorization();
        group.MapGet("/{id:int}", GetAsync);
        return group;
    }

    private static async Task<Results<Ok<OrderDto>, NotFound>> GetAsync(
        int id, IOrderService orders, CancellationToken cancellationToken)
    {
        OrderDto? order = await orders.FindAsync(id, cancellationToken);
        return order is null ? TypedResults.NotFound() : TypedResults.Ok(order);
    }
}
```

## DI and options

- `AddScoped` for anything that uses a `DbContext`. Never inject a scoped service into a singleton.
- Bind each config section to a `sealed` options class and fail at startup, not at first use:
  ```csharp
  builder.Services.AddOptions<SmtpOptions>()
      .BindConfiguration(SmtpOptions.SectionName)
      .ValidateDataAnnotations()
      .ValidateOnStart();
  ```
- `IOptions<T>` for fixed values, `IOptionsSnapshot<T>` per request, `IOptionsMonitor<T>` in singletons that need reloads.
- Secrets: user-secrets locally, environment or a vault in production. Never in `appsettings*.json`.

## Errors and validation

- Every error is a ProblemDetails response: `AddProblemDetails()`, `UseExceptionHandler()`, `UseStatusCodePages()`.
- Map domain exceptions to status codes in one `IExceptionHandler` (`AddExceptionHandler<T>()`). No `try`/`catch` in handlers.
- Expected outcomes (not found, conflict) are return values (`TypedResults.NotFound()`, `TypedResults.Problem(...)`), not exceptions.
- Minimal APIs: `builder.Services.AddValidation();` validates data-annotated parameters and DTOs before the handler runs. .NET 11 adds async validation (`IAsyncValidatableObject`, async attributes) for checks that need I/O.
- Controllers: `[ApiController]` returns `ValidationProblemDetails` on invalid model state; do not re-check `ModelState` by hand.

## Auth, health, OpenAPI

- Closed by default; open public endpoints with `.AllowAnonymous()`:
  ```csharp
  builder.Services.AddAuthorizationBuilder()
      .SetFallbackPolicy(new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build());
  ```
- Named policies, not role strings scattered across endpoints. CORS with explicit origins. HSTS and HTTPS redirection outside Development.
- Health: `AddHealthChecks()` with a check per dependency (`AddDbContextCheck<T>()` from `Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore`); `MapHealthChecks("/health/ready")`, plus a liveness endpoint with `Predicate = (HealthCheckRegistration _) => false`.
- OpenAPI: built-in `Microsoft.AspNetCore.OpenApi` (`AddOpenApi()`, `MapOpenApi()`), not Swashbuckle. .NET 11 emits OpenAPI 3.2 by default; set `options.OpenApiVersion = OpenApiSpecVersion.OpenApi3_1` if a client tool lacks 3.2. Serve a UI only in Development.

## Tests

- Integration test projects end in `Tests` (`X.IntegrationTests`) so the CA1707 exception in `csharp.md` covers them.
- Integration: `WebApplicationFactory<Program>` (`Microsoft.AspNetCore.Mvc.Testing`). Since .NET 10 a source generator makes `Program` public; do not declare `public partial class Program` by hand (ASP0027 flags it).
- Start the database with Testcontainers in the factory and point the connection string at it with `builder.UseSetting(...)` in `ConfigureWebHost`. Swap the clock (`FakeTimeProvider`) and outbound clients in `ConfigureTestServices`.
  ```csharp
  [Fact]
  public async Task GetOrder_WhenMissing_Returns404()
  {
      HttpClient client = factory.CreateClient();
      HttpResponseMessage response = await client.GetAsync("/orders/999", TestContext.Current.CancellationToken);
      response.StatusCode.ShouldBe(HttpStatusCode.NotFound);
  }
  ```
- Assert the ProblemDetails body on error paths, not only the status code.
