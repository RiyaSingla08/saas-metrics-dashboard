-- ============================================================
-- SaaS Metrics Dashboard: Database Schema
-- ============================================================
-- Four tables model the full lifecycle of a SaaS customer:
--   customers     -> who they are
--   plans         -> what pricing tiers exist
--   subscriptions -> what they're subscribed to, and when that changed
--   payments      -> what money actually came in
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id     INTEGER PRIMARY KEY,
    company_name    VARCHAR NOT NULL,
    signup_date     DATE NOT NULL,
    country         VARCHAR
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id         INTEGER PRIMARY KEY,
    plan_name       VARCHAR NOT NULL,
    monthly_price   DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(customer_id),
    plan_id         INTEGER NOT NULL REFERENCES plans(plan_id),
    start_date      DATE NOT NULL,
    end_date        DATE,
    status          VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id      INTEGER PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(subscription_id),
    payment_date    DATE NOT NULL,
    amount          DECIMAL(10, 2) NOT NULL
);