PRAGMA foreign_keys = OFF;
DROP VIEW IF EXISTS v_customer_aggregates;
DROP VIEW IF EXISTS v_monthly_revenue;
DROP VIEW IF EXISTS v_weekly_revenue;
DROP VIEW IF EXISTS v_daily_revenue;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS returns;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS raw_transactions;
CREATE TABLE raw_transactions (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice TEXT, stock_code TEXT, description TEXT, quantity INTEGER,
    invoice_date TEXT, price REAL, customer_id TEXT, country TEXT
);
CREATE TABLE returns (
    return_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice TEXT, stock_code TEXT, description TEXT, quantity INTEGER,
    invoice_date TEXT, price REAL, customer_id TEXT, country TEXT,
    return_amount REAL
);
CREATE TABLE dim_customer (
    customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT UNIQUE NOT NULL, country TEXT,
    first_purchase_date TEXT, last_purchase_date TEXT,
    total_orders INTEGER, total_revenue REAL
);
CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT UNIQUE NOT NULL, description TEXT,
    first_sale_date TEXT, total_quantity INTEGER, total_revenue REAL
);
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT UNIQUE NOT NULL, year INTEGER, quarter INTEGER,
    month INTEGER, month_name TEXT, week INTEGER, week_start TEXT
);
CREATE TABLE fact_sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice TEXT NOT NULL, stock_code TEXT NOT NULL, customer_id TEXT NOT NULL,
    date_key INTEGER NOT NULL, invoice_date TEXT NOT NULL, country TEXT,
    quantity INTEGER NOT NULL, price REAL NOT NULL, revenue REAL NOT NULL,
    FOREIGN KEY(date_key) REFERENCES dim_date(date_key)
);
