# Django

Builds on `python.md`. Checked against Django 6.1 (August 2026, Python 3.12-3.14); 5.2 is the current LTS.

## Settings

- Split by environment: `config/settings/base.py`, then `dev.py`, `test.py`, `prod.py` that import from `base`. Select with `DJANGO_SETTINGS_MODULE`.
- Secrets and hosts come from environment variables, read once in settings. Missing required values fail at startup (`os.environ["SECRET_KEY"]`, no default).
- `prod.py`: `DEBUG = False`, explicit `ALLOWED_HOSTS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`. Set `SECURE_PROXY_SSL_HEADER` only behind a proxy that sets it.
- CSP (6.0+): `django.middleware.csp.ContentSecurityPolicyMiddleware` with `SECURE_CSP`.
- CI runs `python manage.py check --deploy --fail-level WARNING` with prod settings.
- Email (6.1+): configure `MAILERS`; `EMAIL_BACKEND` is deprecated.

## Types and lint

```toml
[tool.ruff.lint]
extend-select = ["DJ"]

[tool.mypy]
plugins = ["mypy_django_plugin.main"]

[tool.django-stubs]
django_settings_module = "config.settings.test"
```

`django-stubs` (and `djangorestframework-stubs` with DRF) give typed models and querysets: `qs: QuerySet[Order] = Order.objects.filter(...)`.

## ORM

- N+1: `select_related("author")` for foreign keys, `prefetch_related("tags")` for many-to-many and reverse relations. Name the fields; bare `select_related()` is deprecated in 6.1.
- 6.1 fetch modes: `.fetch_mode(models.FETCH_PEERS)` turns lazy loads into one query per field; `FETCH_RAISE` raises `FieldFetchBlocked` on any lazy load in hot paths.
- Fetch only what you use: `.only()`, `.values_list()`, `.exists()`, `.count()`. Stream big sets with `.iterator(chunk_size=...)`.
- Write in bulk: `bulk_create`, `update()`, `F()` expressions for counters (no read-modify-write races).
- Multi-step writes in `transaction.atomic()`; lock rows with `select_for_update()` inside it. Side effects after commit: `transaction.on_commit(...)`.
- Business logic in services or model methods, not in views or signals.

## Migrations

- Commit every migration. CI fails on missing ones: `python manage.py makemigrations --check --dry-run`.
- Never edit a migration that ran anywhere shared; add a new one.
- Data migrations use `RunPython` with `apps.get_model(...)` (historical models) and a reverse function.
- Big tables: add a nullable column, backfill in batches, then add the constraint. Review SQL with `sqlmigrate`.

## DRF

- Serializers validate all input. `ModelSerializer` with an explicit `fields` list, never `"__all__"`.
- Defaults in settings: `DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]`, a pagination class, throttling.
- `get_queryset()` adds `select_related`/`prefetch_related` for what the serializer reads.

## Background work

- `django.tasks` (6.0+) defines tasks, but the built-in backends are for development and tests and there is no worker; production needs a real backend.

## Tests: pytest-django

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
```

- `@pytest.mark.django_db` only on tests that need the database. Use the same engine as production (PostgreSQL via Testcontainers or a CI service), not SQLite.
- Lock query counts on list endpoints with `django_assert_num_queries` so N+1 regressions fail.
- Names stay lowercase for Ruff `N802`: `test_<method>_<condition>_<result>`, e.g. `test_create_order_with_empty_cart_returns_400`.
