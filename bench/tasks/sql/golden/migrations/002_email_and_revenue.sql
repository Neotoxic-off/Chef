BEGIN;

-- Stored and generated: backfills existing rows, follows every email change.
ALTER TABLE customers
ADD COLUMN email_normalized text
GENERATED ALWAYS AS (lower(btrim(email, E' \t\n\r'))) STORED NOT NULL;

ALTER TABLE customers
ADD CONSTRAINT customers_email_normalized_key UNIQUE (email_normalized);

-- Months in UTC, so the rows do not depend on the session time zone.
CREATE VIEW customer_monthly_revenue AS
SELECT
    customer_id,
    cast(date_trunc('month', created_at AT TIME ZONE 'UTC') AS date) AS month,
    count(*) AS paid_orders,
    sum(total_cents) AS revenue_cents
FROM orders
WHERE status = 'paid'
GROUP BY customer_id, month;

COMMIT;
