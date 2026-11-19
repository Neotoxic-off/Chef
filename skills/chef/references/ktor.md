# Ktor (server)

Builds on `kotlin.md`. Verified against Ktor 3.6.1 (Nov 2026). Current version: `https://ktor.io/docs/releases.html` or Maven Central `io.ktor:ktor-server-core-jvm`; keep all `io.ktor` artifacts on one version in the catalog.

## Structure

- `EngineMain` with `application.yaml` (or `.conf`) so production and tests load the same modules.
- One module function per concern (`Application.configureSerialization()`, `configureSecurity()`, `configureRouting()`), routes as `Route` extensions per feature.
- Routes map HTTP only: receive, call a service, respond. DTOs are `@Serializable` classes (kotlinx.serialization via `ContentNegotiation`), never database entities.
- Blocking calls (JDBC, file I/O) inside `withContext(Dispatchers.IO)`. No `runBlocking` in request code.

```kotlin
fun Route.orderRoutes(orders: OrderService) {
    route("/orders") {
        get("/{id}") {
            val id: Long = call.parameters["id"]?.toLongOrNull()
                ?: throw BadRequestException("id must be a number")
            val order: OrderDto = orders.find(id) ?: throw OrderNotFoundException(id)
            call.respond(order)
        }
    }
}
```

## Validation and errors

- Validate bodies with the `RequestValidation` plugin; it throws `RequestValidationException` before the route runs:
  ```kotlin
  install(RequestValidation) {
      validate<CreateOrderRequest> { request: CreateOrderRequest ->
          if (request.quantity > 0) ValidationResult.Valid else ValidationResult.Invalid("quantity must be positive")
      }
  }
  ```
- Map exceptions to responses in one `StatusPages` install; no `try`/`catch` in routes:
  ```kotlin
  install(StatusPages) {
      exception<RequestValidationException> { call: ApplicationCall, cause: RequestValidationException ->
          call.respond(HttpStatusCode.BadRequest, cause.reasons)
      }
      exception<OrderNotFoundException> { call: ApplicationCall, _: OrderNotFoundException ->
          call.respond(HttpStatusCode.NotFound)
      }
  }
  ```
- Typed paths: the `Resources` plugin, when a project has many parameterized routes.

## Dependencies and config

- Built-in DI (`ktor-server-di`): `dependencies { provide<OrderRepository> { PostgresOrderRepository(get()) } }`, read with `val repository: OrderRepository by dependencies`. Do not add Koin unless the project already uses it.
- Config through `environment.config`; secrets from environment variables, never committed in `application.yaml`.
- Security: `Authentication` plugin with every non-public route inside `authenticate { }`; `CORS` with explicit hosts; `CallId` + `CallLogging` for request correlation.

## Tests

- `testApplication` runs the real modules in memory, no port:
  ```kotlin
  @Test
  fun `get order when missing returns 404`() = testApplication {
      val response: HttpResponse = client.get("/orders/0")
      assertEquals(HttpStatusCode.NotFound, response.status)
  }
  ```
- JSON bodies: `createClient { install(ContentNegotiation) { json() } }`.
- Override dependencies for tests through the DI plugin's test support; real database from Testcontainers.
