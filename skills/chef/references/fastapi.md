# FastAPI (and Flask)

Builds on `python.md`. Written for FastAPI 0.165 (Python 3.11+), Pydantic 2.14, pydantic-settings 2.16, SQLAlchemy 2.1, Alembic 1.20, Flask 3.1 (Nov 2026), not benchmarked.

## Lint

Add Ruff's FastAPI rules; `FAST002` enforces `Annotated` dependencies, which also keeps `B008` quiet:

```toml
[tool.ruff.lint]
extend-select = ["FAST"]
```

## Models

- Pydantic models at every boundary; separate input and output models (`UserCreate`, `UserRead`), never return ORM objects raw.
- Reject unknown fields on input: `model_config = ConfigDict(extra="forbid")`.
- Declare the response type on the path operation (return annotation or `response_model`) so FastAPI filters the output.

## Dependency injection

Use `Annotated` type aliases for dependencies:

```python
SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/orders/{order_id}")
async def read_order(order_id: int, session: SessionDep) -> OrderRead:
    order: Order | None = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderRead.model_validate(order, from_attributes=True)
```

- Resources with cleanup are `yield` dependencies (session per request).
- Routes stay thin: call a service that receives its dependencies as parameters.

## Settings

- `pydantic-settings`: `class Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_prefix="APP_")`. Required fields have no default, so a missing variable fails at startup.
- Provide it through `get_settings()` wrapped in `@lru_cache`, injected as a dependency; never read `os.environ` elsewhere.

## Async and the database

- `async def` only when every call inside is awaitable. Blocking libraries go in plain `def` routes (FastAPI runs them in a threadpool).
- SQLAlchemy 2.x async: one `create_async_engine` per app, `async_sessionmaker(engine, expire_on_commit=False)`, typed models with `Mapped[...]`.
- Load relations explicitly (`selectinload(...)`); lazy loading in async code raises.
- Startup and shutdown in a `lifespan` context manager, not `on_event`.
- Migrations with Alembic, committed; CI runs `alembic check` to fail on model changes without a migration.

## Errors

- `HTTPException` for expected HTTP outcomes. Domain errors map to responses in one `@app.exception_handler(DomainError)`; no `try`/`catch` in routes.

## Tests

- Override dependencies, not modules: `app.dependency_overrides[get_settings] = lambda: test_settings`, cleared in fixture teardown.
- Sync tests: `with TestClient(app) as client:` (the `with` runs lifespan).
- Async tests: `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` with `@pytest.mark.anyio`. It does not run lifespan; use `asgi-lifespan` if the app needs it.
- Database tests against PostgreSQL from `testcontainers`, one transaction per test rolled back.
- Names: `test_read_order_when_missing_returns_404`.

## Flask notes

- App factory `create_app(config)` and blueprints; no app object at import time.
- Config from the environment (`app.config.from_prefixed_env()`), validated once into a typed settings object.
- Validate request bodies with Pydantic at the start of each view; register error handlers with `@app.errorhandler(DomainError)`.
- Tests with `app.test_client()` from a fixture that builds the app with test config.
