-- Rows already in production when the migration runs.
INSERT INTO customers (id, email) OVERRIDING SYSTEM VALUE VALUES
(1, '  Alice@Example.COM '),
(2, 'bob@example.com'),
(3, 'carol@example.com');

ALTER TABLE customers ALTER COLUMN id RESTART WITH 4;

-- Two paid orders fall in a different month in the session time zone (America/Los_Angeles) than in UTC.
INSERT INTO orders (customer_id, status, total_cents, created_at) VALUES
(1, 'paid', 1000, '2026-01-15 12:00:00+00'),
(1, 'paid', 2000, '2026-02-01 03:00:00+00'),
(1, 'refunded', 500, '2026-01-20 12:00:00+00'),
(1, 'pending', 700, '2026-02-10 12:00:00+00'),
(2, 'paid', 300, '2026-02-05 12:00:00+00'),
(2, 'paid', 200, '2026-02-06 12:00:00+00'),
(2, 'paid', 400, '2026-04-01 02:00:00+00'),
(3, 'refunded', 900, '2026-03-03 12:00:00+00');
