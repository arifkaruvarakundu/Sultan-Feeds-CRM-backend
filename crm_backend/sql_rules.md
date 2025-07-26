NL: "Total amount of last 7 orders"
SQL:
SELECT SUM(total_amount)
FROM (
  SELECT total_amount FROM orders
  ORDER BY created_at DESC
  LIMIT 7
) AS last_n_orders;

NL: "How many orders in the last 7 days?"
SQL:
SELECT COUNT(*) FROM orders
WHERE created_at >= NOW() - INTERVAL '7 days';

NL: "Show last 5 orders"
SQL:
SELECT * FROM orders
ORDER BY created_at DESC
LIMIT 5;

NL: "Who are the top 5 customers by spend?"
SQL:
SELECT c.first_name, c.last_name, SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id
ORDER BY total_spent DESC
LIMIT 5;

NL: "Which customers ordered most?"
SQL:
SELECT c.first_name, c.last_name, COUNT(o.id) AS order_count
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id
ORDER BY order_count DESC;

NL: "Top 10 selling products"
SQL:
SELECT p.name, SUM(oi.quantity) AS total_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.external_id
GROUP BY p.id
ORDER BY total_sold DESC
LIMIT 10;

NL: "How much revenue per product?"
SQL:
SELECT p.name, SUM(oi.price * oi.quantity) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.external_id
GROUP BY p.id;

NL: "Orders by device type"
SQL:
SELECT device_type, COUNT(*) AS total_orders
FROM orders
GROUP BY device_type;

NL: "How many orders from Instagram?"
SQL:
SELECT COUNT(*) FROM orders
WHERE attribution_referrer ILIKE '%instagram%';

NL: "Which customers are from California?"
SQL:
SELECT c.first_name, c.last_name, a.city, a.state
FROM customers c
JOIN addresses a ON a.customer_id = c.id
WHERE a.state ILIKE '%california%';

NL: "List all orders with customer and product names"
SQL:
SELECT o.id AS order_id, o.created_at, c.first_name, c.last_name,
       oi.product_name, oi.quantity, oi.price
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
ORDER BY o.created_at DESC;