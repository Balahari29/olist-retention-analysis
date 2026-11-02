-- =====================================================================================
-- 01_schema.sql : Olist database schema (MySQL 8)
-- Re-runnable: drops and recreates the olist database.
-- Tables are created parents first so every FOREIGN KEY points to an existing table.
-- Design evidence (key uniqueness, orphan checks) is summarised in README "Schema decisions".
-- =====================================================================================

DROP DATABASE IF EXISTS olist;
CREATE DATABASE olist CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE olist;

-- -------------------------------------------------------------------------------------
-- Lookup: Portuguese -> English category names  (product_category_name_translation.csv)
-- -------------------------------------------------------------------------------------
CREATE TABLE category_translation (
    product_category_name          VARCHAR(60) NOT NULL,
    product_category_name_english  VARCHAR(60) NOT NULL,
    PRIMARY KEY (product_category_name)
);

-- -------------------------------------------------------------------------------------
-- customers  (olist_customers_dataset.csv)
-- customer_id is unique PER ORDER; customer_unique_id is the real person.
-- -------------------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id               CHAR(32)    NOT NULL,
    customer_unique_id        CHAR(32)    NOT NULL,
    customer_zip_code_prefix  CHAR(5)     NOT NULL,   -- text, so leading zeros survive (e.g. '01310')
    customer_city             VARCHAR(60) NOT NULL,
    customer_state            CHAR(2)     NOT NULL,
    PRIMARY KEY (customer_id),
    INDEX idx_customers_unique_id (customer_unique_id),        -- repeat-customer and cohort queries
    INDEX idx_customers_zip (customer_zip_code_prefix)         -- join to geolocation
);

-- -------------------------------------------------------------------------------------
-- sellers  (olist_sellers_dataset.csv)
-- -------------------------------------------------------------------------------------
CREATE TABLE sellers (
    seller_id               CHAR(32)    NOT NULL,
    seller_zip_code_prefix  CHAR(5)     NOT NULL,
    seller_city             VARCHAR(60) NOT NULL,
    seller_state            CHAR(2)     NOT NULL,
    PRIMARY KEY (seller_id),
    INDEX idx_sellers_zip (seller_zip_code_prefix)
);

-- -------------------------------------------------------------------------------------
-- products  (olist_products_dataset.csv)
-- Source columns product_name_lenght / product_description_lenght (typo in source)
-- are renamed to *_length by the loader.
-- No FK to category_translation: 2 categories in products have no translation row
-- (found while profiling), so an FK would reject those products. Checked in 02_data_quality_checks.sql.
-- -------------------------------------------------------------------------------------
CREATE TABLE products (
    product_id                  CHAR(32)          NOT NULL,
    product_category_name       VARCHAR(60)       NULL,   -- NULL = category missing in source
    product_name_length         SMALLINT UNSIGNED NULL,
    product_description_length  SMALLINT UNSIGNED NULL,
    product_photos_qty          TINYINT UNSIGNED  NULL,
    product_weight_g            INT UNSIGNED      NULL,
    product_length_cm           SMALLINT UNSIGNED NULL,
    product_height_cm           SMALLINT UNSIGNED NULL,
    product_width_cm            SMALLINT UNSIGNED NULL,
    PRIMARY KEY (product_id),
    INDEX idx_products_category (product_category_name)       -- join to category_translation
);

-- -------------------------------------------------------------------------------------
-- orders  (olist_orders_dataset.csv)
-- Timestamps are nullable: undelivered / canceled orders have no delivery dates.
-- -------------------------------------------------------------------------------------
CREATE TABLE orders (
    order_id                       CHAR(32)    NOT NULL,
    customer_id                    CHAR(32)    NOT NULL,
    order_status                   VARCHAR(20) NOT NULL,
    order_purchase_timestamp       DATETIME    NOT NULL,
    order_approved_at              DATETIME    NULL,
    order_delivered_carrier_date   DATETIME    NULL,
    order_delivered_customer_date  DATETIME    NULL,
    order_estimated_delivery_date  DATETIME    NOT NULL,
    PRIMARY KEY (order_id),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    INDEX idx_orders_status (order_status),                    -- filter valid / delivered orders
    INDEX idx_orders_purchase (order_purchase_timestamp)       -- monthly cohorts and trends
);

-- -------------------------------------------------------------------------------------
-- order_items  (olist_order_items_dataset.csv)  one row per item in an order
-- -------------------------------------------------------------------------------------
CREATE TABLE order_items (
    order_id             CHAR(32)          NOT NULL,
    order_item_id        SMALLINT UNSIGNED NOT NULL,   -- 1, 2, 3 ... within the order
    product_id           CHAR(32)          NOT NULL,
    seller_id            CHAR(32)          NOT NULL,
    shipping_limit_date  DATETIME          NOT NULL,   -- seller's deadline to hand over to carrier
    price                DECIMAL(10,2)     NOT NULL,   -- DECIMAL, not FLOAT: exact money sums
    freight_value        DECIMAL(10,2)     NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_items_order   FOREIGN KEY (order_id)   REFERENCES orders (order_id),
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products (product_id),
    CONSTRAINT fk_items_seller  FOREIGN KEY (seller_id)  REFERENCES sellers (seller_id)
    -- MySQL creates indexes on product_id and seller_id automatically for these FKs;
    -- order_id is already the first column of the primary key.
);

-- -------------------------------------------------------------------------------------
-- order_payments  (olist_order_payments_dataset.csv)  one row per payment in an order
-- -------------------------------------------------------------------------------------
CREATE TABLE order_payments (
    order_id              CHAR(32)          NOT NULL,
    payment_sequential    SMALLINT UNSIGNED NOT NULL,
    payment_type          VARCHAR(20)       NOT NULL,
    payment_installments  TINYINT UNSIGNED  NOT NULL,
    payment_value         DECIMAL(10,2)     NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- -------------------------------------------------------------------------------------
-- order_reviews  (olist_order_reviews_dataset.csv)
-- review_id alone is NOT unique (same review linked to several orders), so the
-- primary key is (review_id, order_id). Duplicate-review rule is decided in Phase 2 DQ.
-- -------------------------------------------------------------------------------------
CREATE TABLE order_reviews (
    review_id                CHAR(32)     NOT NULL,
    order_id                 CHAR(32)     NOT NULL,
    review_score             TINYINT      NOT NULL,
    review_comment_title     VARCHAR(100) NULL,
    review_comment_message   TEXT         NULL,
    review_creation_date     DATETIME     NOT NULL,   -- when the survey was sent
    review_answer_timestamp  DATETIME     NOT NULL,   -- when the customer answered
    PRIMARY KEY (review_id, order_id),
    CONSTRAINT fk_reviews_order FOREIGN KEY (order_id) REFERENCES orders (order_id),
    CONSTRAINT chk_review_score CHECK (review_score BETWEEN 1 AND 5)
);

-- -------------------------------------------------------------------------------------
-- geolocation  (olist_geolocation_dataset.csv)
-- Many rows per zip prefix, so there is no natural key: a surrogate id is used.
-- No FK from customers/sellers: some of their zip prefixes are missing here.
-- Aggregate to one row per zip (mean lat/lng) before joining.
-- -------------------------------------------------------------------------------------
CREATE TABLE geolocation (
    geolocation_id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
    geolocation_zip_code_prefix  CHAR(5)      NOT NULL,
    geolocation_lat              DOUBLE       NOT NULL,
    geolocation_lng              DOUBLE       NOT NULL,
    geolocation_city             VARCHAR(60)  NOT NULL,
    geolocation_state            CHAR(2)      NOT NULL,
    PRIMARY KEY (geolocation_id),
    INDEX idx_geolocation_zip (geolocation_zip_code_prefix)
);
