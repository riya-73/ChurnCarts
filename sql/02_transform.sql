-- Clean the staging table in the requested order.
DELETE FROM raw_transactions WHERE customer_id IS NULL OR TRIM(customer_id) = '' OR LOWER(customer_id) = 'nan';
DELETE FROM raw_transactions WHERE rowid NOT IN (
  SELECT MIN(rowid) FROM raw_transactions GROUP BY invoice, stock_code, description, quantity, invoice_date, price, customer_id, country
);
DELETE FROM raw_transactions WHERE UPPER(TRIM(stock_code)) IN ('POST','D','M','BANK CHARGES') OR UPPER(TRIM(stock_code)) LIKE 'C2%' OR UPPER(TRIM(stock_code)) LIKE 'DOT%';

INSERT INTO returns (invoice, stock_code, description, quantity, invoice_date, price, customer_id, country, return_amount)
SELECT invoice, stock_code, description, quantity, invoice_date, price, customer_id, country, ABS(quantity * price)
FROM raw_transactions WHERE UPPER(invoice) LIKE 'C%';
DELETE FROM raw_transactions WHERE UPPER(invoice) LIKE 'C%';
DELETE FROM raw_transactions WHERE quantity <= 0 OR price <= 0;

INSERT INTO dim_date(date_key, full_date, year, quarter, month, month_name, week, week_start)
SELECT CAST(STRFTIME('%Y%m%d', DATE(invoice_date)) AS INTEGER), DATE(invoice_date),
 CAST(STRFTIME('%Y', DATE(invoice_date)) AS INTEGER), ((CAST(STRFTIME('%m', DATE(invoice_date)) AS INTEGER)-1)/3)+1,
 CAST(STRFTIME('%m', DATE(invoice_date)) AS INTEGER), STRFTIME('%Y-%m', DATE(invoice_date)),
 CAST(STRFTIME('%W', DATE(invoice_date)) AS INTEGER), DATE(invoice_date, '-' || ((CAST(STRFTIME('%w', DATE(invoice_date)) AS INTEGER)+6)%7) || ' days')
FROM raw_transactions GROUP BY DATE(invoice_date);

INSERT INTO dim_product(stock_code, description, first_sale_date, total_quantity, total_revenue)
SELECT stock_code, MAX(description), MIN(DATE(invoice_date)), SUM(quantity), SUM(quantity*price)
FROM raw_transactions GROUP BY stock_code;
INSERT INTO dim_customer(customer_id, country, first_purchase_date, last_purchase_date, total_orders, total_revenue)
SELECT customer_id, MAX(country), MIN(DATE(invoice_date)), MAX(DATE(invoice_date)), COUNT(DISTINCT invoice), SUM(quantity*price)
FROM raw_transactions GROUP BY customer_id;
INSERT INTO fact_sales(invoice, stock_code, customer_id, date_key, invoice_date, country, quantity, price, revenue)
SELECT invoice, stock_code, customer_id, CAST(STRFTIME('%Y%m%d', DATE(invoice_date)) AS INTEGER), invoice_date, country, quantity, price, quantity*price
FROM raw_transactions;

CREATE INDEX IF NOT EXISTS ix_fact_date ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS ix_fact_customer ON fact_sales(customer_id);
CREATE INDEX IF NOT EXISTS ix_fact_product ON fact_sales(stock_code);
CREATE VIEW v_daily_revenue AS SELECT DATE(invoice_date) AS day, SUM(revenue) AS revenue, COUNT(DISTINCT invoice) AS orders FROM fact_sales GROUP BY DATE(invoice_date);
CREATE VIEW v_weekly_revenue AS SELECT DATE(invoice_date, '-' || ((CAST(STRFTIME('%w', invoice_date) AS INTEGER)+6)%7) || ' days') AS week_start, SUM(revenue) AS revenue, COUNT(DISTINCT invoice) AS orders FROM fact_sales GROUP BY 1;
CREATE VIEW v_monthly_revenue AS SELECT STRFTIME('%Y-%m', invoice_date) AS month, SUM(revenue) AS revenue, COUNT(DISTINCT invoice) AS orders FROM fact_sales GROUP BY 1;
CREATE VIEW v_customer_aggregates AS SELECT customer_id, MAX(country) AS country, MIN(DATE(invoice_date)) AS first_purchase, MAX(DATE(invoice_date)) AS last_purchase, COUNT(DISTINCT invoice) AS frequency, SUM(revenue) AS monetary, COUNT(DISTINCT stock_code) AS distinct_products FROM fact_sales GROUP BY customer_id;
