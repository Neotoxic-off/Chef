# Quarkus (and Micronaut)

Builds on `java.md` (and `kotlin.md`). Verified against Quarkus 3.40.1.2 (LTS; 3.33 LTS maintained to 25 Mar 2027), Micronaut platform 5.2.7 (Nov 2026). Quarkus 4.0.0 artifacts reached Maven Central on 18 Nov 2026; the release is planned for 25 Nov 2026. Current versions: `https://quarkus.io/releases`; upgrade with `quarkus update`.

## REST

- Quarkus REST (`quarkus-rest`, `quarkus-rest-jackson`), not the legacy RESTEasy Classic. Resources stay thin.
- Return `RestResponse<T>` so the status is part of the signature.
- Validate at the boundary: `quarkus-hibernate-validator` and `@Valid` on the body; a violation returns 400 before your code runs.
- Map domain exceptions once with `@ServerExceptionMapper`; no `try`/`catch` in resources.

```java
@Path("/orders")
public class OrderResource {
    private final OrderService orders;

    public OrderResource(OrderService orders) {
        this.orders = orders;
    }

    @POST
    public RestResponse<OrderDto> create(@Valid CreateOrderRequest request) {
        OrderDto created = orders.create(request);
        return RestResponse.status(RestResponse.Status.CREATED, created);
    }
}

public class OrderExceptionMappers {
    @ServerExceptionMapper
    public RestResponse<String> mapNotFound(OrderNotFoundException exception) {
        return RestResponse.status(RestResponse.Status.NOT_FOUND, exception.getMessage());
    }
}
```

## Threads

- A method returning `Uni`/`Multi` runs on the event loop: never block in it. A plain return type runs on a worker thread. `@RunOnVirtualThread` for blocking code on virtual threads.

## Config and data

- Group config in `@ConfigMapping(prefix = "app.mail")` interfaces with constraint annotations; bad config fails at startup. Secrets from the environment or a vault; profile overrides with `%dev.` / `%prod.`.
- Hibernate ORM (with Panache if the project uses it), `@Transactional` on service methods, schema through Flyway (`quarkus-flyway`).
- Health: `quarkus-smallrye-health` (`/q/health/live`, `/q/health/ready`).

## Tests

- `@QuarkusTest` with REST Assured, artifact `quarkus-junit` (older projects: `quarkus-junit5`; check the name for your version).
- Dev Services start the database and broker containers in dev and test automatically; do not hard-code test URLs.
- `@InjectMock` (`quarkus-junit-mockito`) only at boundaries. `@QuarkusIntegrationTest` tests the packaged (or native) artifact.
- Coverage: `quarkus-jacoco` writes `target/jacoco-quarkus.exec`; gate it as in `java.md`.

```java
@QuarkusTest
class OrderResourceTest {
    @Test
    void getOrder_whenMissing_returns404() {
        given().when().get("/orders/0").then().statusCode(RestResponse.StatusCode.NOT_FOUND);
    }
}
```

## Micronaut

Micronaut platform 5 (5.0 GA in May 2026: Java 25 baseline, Jackson 3 in the Jackson Databind module, RxJava 2 dropped). Current version: `https://micronaut.io/category/release-announcements/`.

- DI is compile time: the annotation processors must be on the build path, or beans silently do not exist.
- DTOs with `@Serdeable` (Micronaut Serialization), validated with `@Valid @Body`.
- Map exceptions in `ExceptionHandler<E, HttpResponse<?>>` beans; no `try`/`catch` in controllers.
- Tests: `@MicronautTest`; containers through Micronaut Test Resources.
