# Laravel

Builds on `php.md`. Written for Laravel 13.43.0 (PHP 8.3+), Larastan 3.15.0, Pest 5.3.7 (Nov 2026), not benchmarked.

## Structure

- Controllers stay thin: a Form Request validates, an action or service does the work, an API Resource shapes the output.
- Authorization in Policies, called from the Form Request's `authorize()` or `Gate`.
- `env()` only inside `config/` files; the app reads `config('mail.host')`. After `php artisan config:cache`, `env()` elsewhere returns `null`.

## Validation: Form Requests

```php
final class StoreOrderRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()?->can('create', Order::class) ?? false;
    }

    /** @return array<string, list<string>> */
    public function rules(): array
    {
        return [
            'customer_id' => ['required', 'integer', 'exists:customers,id'],
            'lines' => ['required', 'array', 'min:1'],
        ];
    }
}
```

- Use `$request->validated()` (or `safe()`), never `$request->all()` or `input()` for writes.
- Map validated data into a typed DTO before it reaches the service.

## Eloquent

- In `AppServiceProvider::boot()`, catch mistakes outside production:
  ```php
  Model::preventLazyLoading(! $this->app->isProduction());
  Model::preventSilentlyDiscardingAttributes(! $this->app->isProduction());
  ```
- Eager load what you read: `with('customer')`, `withCount('lines')`. Fix every lazy-loading violation at its query.
- Explicit mass-assignment list on every model (`#[Fillable([...])]` or `$fillable`); never `$guarded = []`.
- Big sets: `chunkById()` or `lazyById()` when updating while iterating; `cursor()` cannot eager load.
- Multi-step writes inside `DB::transaction(...)`. Typed casts (`casts()` returning enum and value-object casts) instead of raw strings.
- Query scopes and model methods for reusable queries; no raw SQL with interpolated input.

## Queues

- Slow or external work goes in a job implementing `ShouldQueue`. Production uses a real driver (database, Redis, SQS), never `sync`.
- Jobs are idempotent: they may run twice. Set `$tries`, `$backoff` and a `failed()` handler; `ShouldBeUnique` where duplicates hurt.
- Pass ids or models (`SerializesModels`), not large payloads. Dispatch after the transaction commits (`->afterCommit()`).
- Supervise workers (Horizon for Redis) and alert on the failed-jobs table.

## Static analysis: Larastan

`larastan/larastan` (3.x) teaches PHPStan about Eloquent, facades and container bindings. Extend the `phpstan.neon` from `php.md`:

```neon
includes:
    - vendor/larastan/larastan/extension.neon
    - vendor/phpstan/phpstan-strict-rules/rules.neon
parameters:
    level: max
    paths: [app, config, database, routes, tests]
```

Type relations and collections in PHPDoc where native types cannot: `/** @return HasMany<OrderLine, $this> */`.

## Tests: Pest

- Pest 5 (on PHPUnit; needs PHP 8.4, stay on Pest 4 for PHP 8.3). Feature tests hit routes through the kernel; `RefreshDatabase` against the same database engine as production (Docker), not SQLite when production is MySQL or PostgreSQL.
  ```php
  it('store_WithNoLines_Returns422', function (): void {
      $user = User::factory()->create();

      $this->actingAs($user)
          ->postJson('/api/orders', ['customer_id' => 1, 'lines' => []])
          ->assertUnprocessable()
          ->assertJsonValidationErrors(['lines']);
  });
  ```
- Fake boundaries: `Queue::fake()`, `Mail::fake()`, `Http::fake()` with `Http::preventStrayRequests()`.
- Architecture rules: `arch()->preset()->laravel();`.
- Coverage gate: `php artisan test --coverage --min=90` (or `pest --coverage --min=90`).
