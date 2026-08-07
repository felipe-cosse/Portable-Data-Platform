CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    ordered_at TIMESTAMPTZ NOT NULL,
    amount NUMERIC(12, 2) NOT NULL
);

INSERT INTO orders (order_id, customer_id, ordered_at, amount)
VALUES
    (1001, 1, '2026-08-01T10:00:00Z', 125.50),
    (1002, 2, '2026-08-02T13:30:00Z', 42.00)
ON CONFLICT (order_id) DO NOTHING;
