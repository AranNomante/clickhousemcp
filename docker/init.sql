-- Seed data for local development / example runs
-- Database: demo (created automatically via CLICKHOUSE_DB env var)

CREATE TABLE IF NOT EXISTS demo.products
(
    id           UInt32,
    name         String,
    category     LowCardinality(String),
    price        Float64,
    stock        UInt32
)
ENGINE = MergeTree()
ORDER BY id;

INSERT INTO demo.products VALUES
    (1,  'Wireless Headphones',  'Electronics',  89.99,  150),
    (2,  'Mechanical Keyboard',  'Electronics', 129.99,   60),
    (3,  'USB-C Hub',            'Electronics',  49.99,  200),
    (4,  'Running Shoes',        'Sports',       119.99,   80),
    (5,  'Yoga Mat',             'Sports',        34.99,  120),
    (6,  'Water Bottle',         'Sports',        24.99,  300),
    (7,  'Desk Lamp',            'Home',          39.99,   90),
    (8,  'Scented Candle Set',   'Home',          19.99,  250),
    (9,  'Python Cookbook',      'Books',         45.99,   70),
    (10, 'Data Engineering',     'Books',         54.99,   40);


CREATE TABLE IF NOT EXISTS demo.orders
(
    id          UInt32,
    customer_id UInt32,
    product_id  UInt32,
    quantity    UInt32,
    total       Float64,
    status      LowCardinality(String),
    created_at  DateTime
)
ENGINE = MergeTree()
ORDER BY (created_at, id);

INSERT INTO demo.orders VALUES
    (1,  101, 1, 1,  89.99, 'completed', '2026-05-01 09:14:00'),
    (2,  102, 4, 2, 239.98, 'completed', '2026-05-02 11:30:00'),
    (3,  103, 9, 1,  45.99, 'completed', '2026-05-02 14:05:00'),
    (4,  104, 2, 1, 129.99, 'completed', '2026-05-03 10:22:00'),
    (5,  105, 7, 2,  79.98, 'completed', '2026-05-04 16:45:00'),
    (6,  101, 5, 1,  34.99, 'completed', '2026-05-05 08:10:00'),
    (7,  106, 3, 3, 149.97, 'completed', '2026-05-06 13:00:00'),
    (8,  107, 1, 2, 179.98, 'completed', '2026-05-07 09:55:00'),
    (9,  108, 6, 4,  99.96, 'completed', '2026-05-08 17:20:00'),
    (10, 109, 10,1,  54.99, 'completed', '2026-05-09 12:33:00'),
    (11, 110, 8, 2,  39.98, 'completed', '2026-05-10 10:15:00'),
    (12, 102, 2, 1, 129.99, 'pending',   '2026-05-11 14:40:00'),
    (13, 103, 4, 1, 119.99, 'pending',   '2026-05-12 09:05:00'),
    (14, 111, 1, 1,  89.99, 'completed', '2026-05-13 11:50:00'),
    (15, 112, 9, 2,  91.98, 'completed', '2026-05-14 15:30:00'),
    (16, 104, 3, 1,  49.99, 'cancelled', '2026-05-15 08:45:00'),
    (17, 113, 7, 1,  39.99, 'completed', '2026-05-16 13:10:00'),
    (18, 114, 5, 3, 104.97, 'completed', '2026-05-17 10:00:00'),
    (19, 115, 2, 2, 259.98, 'pending',   '2026-05-18 16:25:00'),
    (20, 101, 6, 2,  49.98, 'completed', '2026-05-19 09:35:00'),
    (21, 116, 10,1,  54.99, 'completed', '2026-05-20 12:00:00'),
    (22, 105, 1, 1,  89.99, 'completed', '2026-05-21 14:15:00'),
    (23, 117, 8, 3,  59.97, 'cancelled', '2026-05-22 10:50:00'),
    (24, 118, 4, 1, 119.99, 'completed', '2026-05-23 11:20:00'),
    (25, 119, 3, 2,  99.98, 'pending',   '2026-05-24 09:00:00');
