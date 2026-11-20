This folder holds the PostgreSQL 18 migrations of a shop database. `migrations/001_initial.sql` is already applied in production: do not edit it.

Add the migration `migrations/002_email_and_revenue.sql`. It runs once with `psql -v ON_ERROR_STOP=1` against the existing data and must:
- add the column `customers.email_normalized`: the email with surrounding whitespace removed and lowercased, never null, unique, filled in for the existing rows and kept up to date when a customer is inserted or its `email` changes, without the application having to set it;
- create the view `customer_monthly_revenue` with the columns `customer_id`, `month` (type `date`, the first day of the month), `paid_orders` (`bigint`) and `revenue_cents` (`bigint`): one row per customer and month that has at least one order with status `paid`, counting only those orders. Months are calendar months in UTC, whatever the time zone of the session that queries the view.

The existing data has no two emails that differ only by case or surrounding whitespace.

Work autonomously: nobody will answer questions.
