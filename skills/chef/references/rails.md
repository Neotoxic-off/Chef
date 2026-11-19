# Rails

Builds on `ruby.md`. Verified against Rails 8.1.4 (security fixes until October 2027), rubocop-rails 2.38, Brakeman 8.1, bundler-audit 0.9, Bullet 8.3 (Nov 2026).

## Lint and security

- Add `rubocop-rails` to the `plugins:` list in `.rubocop.yml` from `ruby.md`.
- `brakeman` in CI; any warning fails the build. `bundler-audit` (or `bundle audit`) for vulnerable gems.
- Sorbet in Rails needs `tapioca dsl` after model, route or association changes so generated RBIs stay current.

## Controllers and strong params

- Thin controllers: permit params, call a model or service object, render. No business rules in controllers or callbacks.
- Rails 8 `params.expect` over `require(...).permit(...)`; malformed input returns 400 instead of raising deep in the code:
  ```ruby
  sig { returns(ActionController::Parameters) }
  def order_params
    params.expect(order: [:customer_id, { lines: [[:product_id, :quantity]] }])
  end
  ```
- Never permit `:role`, `:admin` or foreign keys the user must not set. Never `permit!`.
- Validations live on the model; database constraints (`null: false`, foreign keys, unique indexes) back them up.

## N+1

- Eager load what the view or serializer reads: `includes` by default, `preload` (separate queries) or `eager_load` (`LEFT OUTER JOIN`) when you need to force one.
- Make lazy loads fail in development and test:
  ```ruby
  config.active_record.strict_loading_by_default = true
  ```
  Or per record: `strict_loading!(mode: :n_plus_one_only)`. In production, use `action_on_strict_loading_violation = :log` if you enable it there.
- Bullet in development and test (`Bullet.raise = true` in test) catches unused eager loads too.
- Batch large sets with `find_each` / `in_batches`; use `exists?`, `pluck`, `count` instead of loading records.

## Background jobs

- Rails 8 defaults to Solid Queue (database-backed, no Redis). Keep it unless the project already runs another backend.
- Jobs are idempotent and receive ids or GlobalID records, never large payloads.
- Declare failure handling: `retry_on` with a wait and attempt limit, `discard_on` for errors that will never succeed.
- Long jobs: Rails 8.1 job continuations (`ActiveJob::Continuable`) to resume after a restart instead of starting over.

## Migrations

- Reversible (`change`, or `up`/`down`), one concern each, committed with `db/schema.rb`.
- Add columns nullable, backfill in a job or batched migration, then add `null: false`. Add indexes `algorithm: :concurrently` on PostgreSQL (with `disable_ddl_transaction!`).

## Tests: RSpec

- Request specs (`type: :request`) for HTTP, not controller specs. System specs only for flows that need a browser.
- Structure reads as Method / Condition / Result:
  ```ruby
  RSpec.describe "POST /orders", type: :request do
    context "when lines are empty" do
      it "returns 422 with the field error" do
        post orders_path, params: { order: { customer_id: customer.id, lines: [] } }, as: :json

        expect(response).to have_http_status(:unprocessable_content)
        expect(response.parsed_body["errors"]).to include("lines")
      end
    end
  end
  ```
- Jobs: `have_enqueued_job(SendReceiptJob).with(order.id)`; run them inline only in the spec that tests the job.
- Database: transactional fixtures, same engine as production (PostgreSQL in Docker or a CI service). Factories with FactoryBot, built with the minimum attributes.
