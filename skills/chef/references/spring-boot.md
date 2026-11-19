# Spring Boot

Builds on `java.md` (and `kotlin.md`). Verified against Spring Boot 4.1.2, Spring Framework 7.0.10, Testcontainers 2.0.5 (Nov 2026). Boot 4.2.0-RC2 (Framework 7.1.0-RC2) was out on 5 Nov 2026, not GA.

## Structure

- Package by feature (`order/`, `customer/`), not by layer. Controllers map HTTP, services hold logic and transactions, repositories do I/O.
- Constructor injection only, one constructor, no `@Autowired` on fields.
- HTTP clients: `RestClient` (or declarative `@HttpExchange` interfaces), not `RestTemplate`.

## Configuration properties

Bind config to validated records, never `@Value` scattered across beans:

```java
@ConfigurationProperties("app.mail")
@Validated
public record MailProperties(@NotBlank String host, @Min(1) int port, @NotNull Duration timeout) {}
```

- Register with `@ConfigurationPropertiesScan` on the application class. Bad config fails at startup.
- Secrets from the environment or a vault, never committed in `application.yml`. Profiles only for real environment differences.

## Validation and errors

- `spring-boot-starter-validation`; `@Valid @RequestBody CreateOrderRequest request` with Jakarta constraints on the record.
- RFC 9457 errors: `spring.mvc.problemdetails.enabled=true` (WebFlux: `spring.webflux.problemdetails.enabled`).
- Domain errors map in one `@RestControllerAdvice` that extends `ResponseEntityExceptionHandler` and returns `ProblemDetail`. No `try`/`catch` in controllers.

## Data (JPA)

- `spring.jpa.open-in-view=false`: no lazy loading from the web layer.
- Avoid N+1 with `@EntityGraph` or `join fetch` on the repository query that needs the relation. Return DTO projections for read endpoints.
- `@Transactional` on service methods (`readOnly = true` for reads), never on controllers.
- Schema through Flyway or Liquibase migrations, `spring.jpa.hibernate.ddl-auto=validate`.

## Actuator

- Expose only what you need: `management.endpoints.web.exposure.include=health,info,prometheus`.
- Kubernetes probes: `management.endpoint.health.probes.enabled=true` (`/actuator/health/liveness`, `/readiness`).
- Put management on its own port or behind auth; never expose `env`, `heapdump` or `beans` publicly.

## Tests

- Slices for focused tests. Boot 4 moved them to per-module packages:
  - `@WebMvcTest` from `org.springframework.boot.webmvc.test.autoconfigure`, with `MockMvcTester` (AssertJ).
  - `@DataJpaTest` from `org.springframework.boot.data.jpa.test.autoconfigure`, with `@AutoConfigureTestDatabase(replace = Replace.NONE)` to use the real database.
- Mock collaborators with `@MockitoBean` / `@MockitoSpyBean` (Spring Framework), not the old `@MockBean`.
- Full app: `@SpringBootTest` with `@AutoConfigureRestTestClient` (`RestTestClient`) or `webEnvironment = RANDOM_PORT`.
- Databases from Testcontainers with `@ServiceConnection` (needs `spring-boot-testcontainers`); no hand-written URLs:
  ```java
  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:17");
  ```
  Testcontainers 2: artifact `org.testcontainers:testcontainers-postgresql`, class `org.testcontainers.postgresql.PostgreSQLContainer`, no generic parameter.
- Share one container config class across tests (`@Import`) so the Spring context is cached and reused.
