-- Run after the migrations with psql -v ON_ERROR_STOP=1 on an empty database; rolls back what it inserts.
BEGIN;
SET LOCAL TIME ZONE 'Asia/Tokyo';

INSERT INTO customers (email) VALUES (' Erin@Example.com');
INSERT INTO orders (customer_id, status, total_cents, created_at)
SELECT id, 'paid', 250, '2026-05-31 20:00:00+00' FROM customers WHERE email_normalized = 'erin@example.com';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM customer_monthly_revenue
        WHERE month = '2026-05-01' AND paid_orders = 1 AND revenue_cents = 250
    ) THEN
        RAISE EXCEPTION 'a paid order on 31 May UTC must count in May, not in the session''s June';
    END IF;
END $$;

ROLLBACK;
