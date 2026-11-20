-- Runs after the migrations, in a session whose time zone is not UTC; any failed check raises an error.
SET TIME ZONE 'America/Los_Angeles';

DO $$
DECLARE
    expected_types CONSTANT jsonb := '{"customer_id": "bigint", "month": "date", "paid_orders": "bigint", "revenue_cents": "bigint"}';
    actual_types jsonb;
BEGIN
    SELECT jsonb_object_agg(column_name, data_type) INTO actual_types
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'customer_monthly_revenue';
    IF actual_types IS DISTINCT FROM expected_types THEN
        RAISE EXCEPTION 'customer_monthly_revenue columns are %, expected %', actual_types, expected_types;
    END IF;
END $$;

CREATE TEMPORARY TABLE expected_revenue (customer_id bigint, month date, paid_orders bigint, revenue_cents bigint);
INSERT INTO expected_revenue VALUES
(1, '2026-01-01', 1, 1000),
(1, '2026-02-01', 1, 2000),
(2, '2026-02-01', 2, 500),
(2, '2026-04-01', 1, 400);

DO $$
DECLARE
    mismatches bigint;
BEGIN
    SELECT count(*) INTO mismatches FROM (
        (SELECT customer_id, month, paid_orders, revenue_cents FROM customer_monthly_revenue
         EXCEPT ALL SELECT * FROM expected_revenue)
        UNION ALL
        (SELECT * FROM expected_revenue
         EXCEPT ALL SELECT customer_id, month, paid_orders, revenue_cents FROM customer_monthly_revenue)
    ) AS differences;
    IF mismatches <> 0 THEN
        RAISE EXCEPTION 'customer_monthly_revenue differs from the expected rows in % rows', mismatches;
    END IF;
END $$;

DO $$
BEGIN
    IF (SELECT is_nullable FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'customers' AND column_name = 'email_normalized') <> 'NO' THEN
        RAISE EXCEPTION 'customers.email_normalized is nullable';
    END IF;
    IF (SELECT email_normalized FROM customers WHERE id = 1) IS DISTINCT FROM 'alice@example.com' THEN
        RAISE EXCEPTION 'existing row not backfilled: %', (SELECT email_normalized FROM customers WHERE id = 1);
    END IF;

    INSERT INTO customers (email) VALUES (E'\tDave@Example.com  ');
    IF (SELECT email_normalized FROM customers WHERE email = E'\tDave@Example.com  ') IS DISTINCT FROM 'dave@example.com' THEN
        RAISE EXCEPTION 'inserted row not normalized';
    END IF;

    UPDATE customers SET email = 'Bobby@Example.com' WHERE id = 2;
    IF (SELECT email_normalized FROM customers WHERE id = 2) IS DISTINCT FROM 'bobby@example.com' THEN
        RAISE EXCEPTION 'updated row not normalized';
    END IF;
END $$;

DO $$
BEGIN
    INSERT INTO customers (email) VALUES ('ALICE@example.com ');
    RAISE EXCEPTION 'a duplicate normalized email was accepted';
EXCEPTION WHEN unique_violation THEN
    NULL;
END $$;
