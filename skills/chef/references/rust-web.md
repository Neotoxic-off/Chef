# Rust web: Axum, Actix Web, Tokio, sqlx

Builds on `rust.md`. Checked against axum 0.8.9 (0.9 in development, not released), tower-http 0.7.1, actix-web 4.20, tokio 1.54, sqlx 0.9.1. Current versions: `cargo info <crate>` or `cargo search <crate>`.

## Axum

- Paths use `{id}` (0.8); the old `:id` syntax panics at startup.
- Shared state through `State<AppState>` (cheap to clone, `Arc` inside). No global statics.
- One `AppError` enum (`thiserror`) that implements `IntoResponse`; handlers return `Result<_, AppError>` and use `?`. Log internal errors, return a generic body.
- Parse input into domain newtypes (`TryFrom`) in the handler's first line or in a custom extractor; reject bad input before any I/O.
- Layers from `tower-http`: `TraceLayer`, `TimeoutLayer::with_status_code` (`TimeoutLayer::new` is deprecated), `CorsLayer` with explicit origins. Body limit: `DefaultBodyLimit::max` (default 2 MB).
- Shut down cleanly: `axum::serve(listener, app).with_graceful_shutdown(shutdown_signal())`.

```rust
const REQUEST_TIMEOUT: Duration = Duration::from_secs(10);

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/orders/{id}", get(get_order))
        .layer(TimeoutLayer::with_status_code(StatusCode::REQUEST_TIMEOUT, REQUEST_TIMEOUT))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

async fn get_order(State(state): State<AppState>, Path(id): Path<i64>) -> Result<Json<OrderDto>, AppError> {
    let order: OrderDto = state.orders.find(id).await?.ok_or(AppError::NotFound)?;
    Ok(Json(order))
}
```

## Actix Web

- State in `web::Data<T>`; error type implements `ResponseError`.
- Set `web::JsonConfig::default().limit(...)` and an `error_handler` so bad JSON returns your error format.
- Blocking work in `web::block`. Tests: `test::init_service` + `test::call_service`, no real port.

## Tokio

- Never block an async task: blocking I/O or CPU work goes to `tokio::task::spawn_blocking`. No `std::sync::Mutex` guard held across `.await`.
- Every outbound call has a deadline (`tokio::time::timeout` or the client's timeout).
- Track spawned tasks (`JoinSet`, `tokio_util::sync::CancellationToken`) so shutdown waits for them; no fire-and-forget `tokio::spawn`.
- Time in tests: `#[tokio::test(start_paused = true)]` and `tokio::time::advance`, never real sleeps.
- Enable only the tokio features you use.

## sqlx

- Compile-time checked queries (`query!`, `query_as!`). Commit the `.sqlx` folder from `cargo sqlx prepare`; CI builds with `SQLX_OFFLINE=true` and runs `cargo sqlx prepare --check`.
- 0.9: `query()` takes `impl SqlSafeStr`, not `&str`. Bind values with `.bind()`; never format input into SQL.
- Migrations with `sqlx::migrate!()` or `sqlx migrate run`. Size the pool and set `acquire_timeout` with named constants.
- Per-crate settings in `sqlx.toml` (0.9).

## Tests

- `#[sqlx::test]` gives each test a fresh database with migrations applied (feature `migrate`); point `DATABASE_URL` at a container.
- Test the router without a server via `tower::ServiceExt::oneshot`. Return `Result` so `?` replaces `unwrap()`:
  ```rust
  #[tokio::test]
  async fn get_order_when_missing_returns_not_found() -> Result<(), Box<dyn std::error::Error>> {
      let app: Router = router(AppState::for_tests());
      let request: Request<Body> = Request::get("/orders/0").body(Body::empty())?;
      let response: Response = app.oneshot(request).await?;
      assert_eq!(response.status(), StatusCode::NOT_FOUND);
      Ok(())
  }
  ```
