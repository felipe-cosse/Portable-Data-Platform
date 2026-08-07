CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL
);

INSERT IGNORE INTO products (product_id, name, category, unit_price)
VALUES
    (501, 'Portable Analytics Starter', 'software', 49.00),
    (502, 'Data Quality Review', 'service', 250.00);
