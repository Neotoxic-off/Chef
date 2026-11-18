# PHP

Composer manages tools as dev dependencies (`composer.lock` committed); run them from `vendor/bin`.

## Lint and format: PHP-CS-Fixer (PER-CS) + PHPStan

`.php-cs-fixer.dist.php`:

```php
<?php

declare(strict_types=1);

return (new PhpCsFixer\Config())
    ->setRiskyAllowed(true)
    ->setRules([
        '@PER-CS' => true,
        '@PER-CS:risky' => true,
        '@autoPHPMigration' => true,
        'declare_strict_types' => true,
        'void_return' => true,
        'no_unused_imports' => true,
    ])
    ->setFinder(PhpCsFixer\Finder::create()->in([__DIR__ . '/src', __DIR__ . '/tests']));
```

CI: `php-cs-fixer check --diff`.

`phpstan.neon` (with `phpstan/phpstan-strict-rules`; PHPStan 2 `max` is level 10):

```neon
includes:
    - vendor/phpstan/phpstan-strict-rules/rules.neon
parameters:
    level: max
    paths: [src, tests]
```

- Fix errors; do not grow a baseline. A baseline is only for adopting PHPStan on legacy code.
- Psalm (`errorLevel="1"`) is the alternative. Pick one, not both.

## Code

- `declare(strict_types=1);` as the first statement of every file.
- Explicit types: every parameter, return (including `: void`, `: never`) and property is typed. `private readonly int $count;`. Use PHPDoc only for what native types cannot hold: `/** @var list<User> */`, `/** @param array<string, int> $map */`.
- No `mixed` unless the value truly is untyped (decoded JSON). Narrow it right away, or map it into a typed DTO.
- `final` classes by default. `readonly` classes for value objects. Enums instead of string or int constants.
- Constructor injection with interface types. No static service locators, no `new` of collaborators inside business logic.
- Exceptions over `false`/`null` error returns. `json_decode(..., flags: JSON_THROW_ON_ERROR)`.

## Tests

- PHPUnit (attributes: `#[Test]`, `#[DataProvider]`, `#[CoversClass]`) or Pest. Split `unit` and `integration` test suites in `phpunit.xml`; integration hits a real database in Docker.
- Warnings fail the run, in `phpunit.xml`:
  ```xml
  <phpunit failOnWarning="true" failOnNotice="true" failOnDeprecation="true"
           failOnRisky="true" beStrictAboutCoverageMetadata="true">
      <coverage pathCoverage="true"/>
  </phpunit>
  ```
- Coverage needs Xdebug (`XDEBUG_MODE=coverage`) or PCOV. Only Xdebug gives branch/path coverage.
- 90% gate. Pest: `pest --coverage --min=90`. PHPUnit has no threshold option; check the Clover report:
  ```sh
  phpunit --coverage-clover=clover.xml
  php -r '$m=simplexml_load_file("clover.xml")->project->metrics; exit((int)$m["coveredstatements"]*100<90*(int)$m["statements"]?1:0);'
  ```
- Mutation testing: Infection on critical logic, with `minMsi` and `minCoveredMsi` in `infection.json5` (or `--min-msi=80 --min-covered-msi=90`).

Order before done: `php-cs-fixer fix` then `phpstan analyse` then `phpunit` (or `pest`).
