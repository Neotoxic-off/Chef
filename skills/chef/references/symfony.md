# Symfony

Builds on `php.md`. Checked against Symfony 8.1 (stable, needs PHP 8.4) and 7.4 (LTS); 8.2 was in beta in November 2026. Current versions: `https://symfony.com/releases.json`; installed ones: `composer show 'symfony/*'`.

## Controllers and input

- Thin `final` controllers: map the request, call an injected service, return the response. No business rules, no `Doctrine` queries in controllers.
- Validate at the boundary: map the body to a readonly DTO with `#[MapRequestPayload]` (query string: `#[MapQueryString]`). A failed constraint returns 422 before your code runs.
- Access rules with `#[IsGranted]` and voters, not role checks inside methods. Get the user with `#[CurrentUser]`.

```php
final readonly class CreateOrderRequest
{
    public function __construct(
        #[Assert\NotBlank] public string $sku,
        #[Assert\Positive] public int $quantity,
    ) {}
}

final class OrderController extends AbstractController
{
    public function __construct(private readonly OrderService $orders) {}

    #[Route('/orders', methods: ['POST'])]
    #[IsGranted('ROLE_USER')]
    public function create(#[MapRequestPayload] CreateOrderRequest $request): JsonResponse
    {
        return $this->json($this->orders->create($request), Response::HTTP_CREATED);
    }
}
```

## Errors

- No `try`/`catch` in controllers. Give domain exceptions a status with `#[WithHttpStatus(Response::HTTP_NOT_FOUND)]` on the exception class, or map them once in a `kernel.exception` listener (`#[AsEventListener]`).
- Expected outcomes the caller must handle (not found in a lookup) are return values (`?Order`), not exceptions.

## Services and config

- Keep `autowire` and `autoconfigure` on; constructor injection only. Never fetch services from the container.
- Scalars from config with `#[Autowire(env: 'MAILER_DSN')]` or `#[Autowire(param: '...')]`.
- Secrets in the vault (`bin/console secrets:set`) or real environment variables. `.env` holds only non-secret defaults; `.env.local` is never committed.
- Clock: inject `Psr\Clock\ClockInterface` (`symfony/clock`); use `MockClock` in tests.
- Slow work goes to Messenger (`#[AsMessageHandler]`) with a retry strategy and a failure transport.

## Lint

- PHPStan with `phpstan/phpstan-symfony` and `phpstan/phpstan-doctrine`; point it at the container so it knows service types:
  ```neon
  parameters:
      symfony:
          containerXmlPath: var/cache/dev/App_KernelDevDebugContainer.xml
  ```
- CI also runs `bin/console lint:container`, `lint:yaml config --parse-tags`, `lint:twig templates` and `doctrine:schema:validate`.
- Schema changes only through reviewed Doctrine migrations.

## Tests

- `KernelTestCase` for services with the real container; `WebTestCase` with `static::createClient()` for HTTP.
- Real database in Docker, reset per test with `dama/doctrine-test-bundle` (one rollback per test); build data with Zenstruck Foundry factories.
- Outbound HTTP: `MockHttpClient` / `MockResponse`, never a real call.

```php
#[Test]
public function createOrderWithZeroQuantityReturns422(): void
{
    $client = static::createClient();
    $client->jsonRequest('POST', '/orders', ['sku' => 'A-1', 'quantity' => 0]);
    self::assertResponseStatusCodeSame(Response::HTTP_UNPROCESSABLE_ENTITY);
}
```
