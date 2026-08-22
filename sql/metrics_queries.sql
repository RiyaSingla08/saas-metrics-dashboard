-- ============================================================
-- SaaS Metrics Dashboard: Core Metric Queries
-- ============================================================
-- Four standalone queries. Each is written to run independently
-- against saas_metrics.duckdb. The Dash app (Step 5+) wraps these
-- in Python functions inside app/queries.py.
-- ============================================================


-- ------------------------------------------------------------
-- 1. MRR (Monthly Recurring Revenue) by month
-- ------------------------------------------------------------
-- Every row in `payments` already represents one month of revenue
-- at the price actually paid, so MRR is a straight sum grouped by month.
SELECT
    date_trunc('month', payment_date) AS month,
    SUM(amount) AS mrr
FROM payments
GROUP BY 1
ORDER BY 1;


-- ------------------------------------------------------------
-- 2. Churn rate by month
-- ------------------------------------------------------------
-- Logic: a customer is "active at the start of month M" if they'd
-- signed up before M and hadn't churned yet. Churn rate = customers
-- who churned DURING month M / customers active at the START of M.
WITH customer_churn AS (
    SELECT
        c.customer_id,
        c.signup_date,
        MAX(CASE WHEN s.status = 'churned' THEN s.end_date END) AS churn_date
    FROM customers c
    LEFT JOIN subscriptions s ON c.customer_id = s.customer_id
    GROUP BY c.customer_id, c.signup_date
),
months AS (
    SELECT unnest(generate_series(
        date_trunc('month', (SELECT MIN(signup_date) FROM customers)),
        date_trunc('month', (SELECT MAX(payment_date) FROM payments)),
        INTERVAL '1 month'
    )) AS month_start
)
SELECT
    m.month_start,
    COUNT(DISTINCT CASE
        WHEN cc.signup_date <= m.month_start
         AND (cc.churn_date IS NULL OR cc.churn_date > m.month_start)
        THEN cc.customer_id
    END) AS active_at_start,
    COUNT(DISTINCT CASE
        WHEN cc.churn_date IS NOT NULL
         AND date_trunc('month', cc.churn_date) = m.month_start
        THEN cc.customer_id
    END) AS churned_this_month,
    ROUND(
        COUNT(DISTINCT CASE
            WHEN cc.churn_date IS NOT NULL
             AND date_trunc('month', cc.churn_date) = m.month_start
            THEN cc.customer_id
        END) * 100.0
        / NULLIF(COUNT(DISTINCT CASE
            WHEN cc.signup_date <= m.month_start
             AND (cc.churn_date IS NULL OR cc.churn_date > m.month_start)
            THEN cc.customer_id
        END), 0),
        2
    ) AS churn_rate_pct
FROM months m
CROSS JOIN customer_churn cc
GROUP BY m.month_start
ORDER BY m.month_start;


-- ------------------------------------------------------------
-- 3. LTV (Lifetime Value) per customer
-- ------------------------------------------------------------
-- Total revenue collected from each customer across their whole history.
SELECT
    c.customer_id,
    c.company_name,
    SUM(p.amount) AS lifetime_value
FROM customers c
JOIN subscriptions s ON c.customer_id = s.customer_id
JOIN payments p ON s.subscription_id = p.subscription_id
GROUP BY c.customer_id, c.company_name
ORDER BY lifetime_value DESC;

-- Average LTV across all customers (useful as a single headline KPI)
SELECT AVG(total) AS avg_ltv
FROM (
    SELECT s.customer_id, SUM(p.amount) AS total
    FROM subscriptions s
    JOIN payments p ON s.subscription_id = p.subscription_id
    GROUP BY s.customer_id
);


-- ------------------------------------------------------------
-- 4. Cohort retention
-- ------------------------------------------------------------
-- Group customers by signup month (their "cohort"), then for each
-- month afterward, what % of that cohort is still active.
-- This is the data source for a cohort retention heatmap.
WITH customer_churn AS (
    SELECT
        c.customer_id,
        date_trunc('month', c.signup_date) AS cohort_month,
        MAX(CASE WHEN s.status = 'churned' THEN s.end_date END) AS churn_date
    FROM customers c
    LEFT JOIN subscriptions s ON c.customer_id = s.customer_id
    GROUP BY c.customer_id, c.signup_date
),
months AS (
    SELECT unnest(generate_series(
        date_trunc('month', (SELECT MIN(signup_date) FROM customers)),
        date_trunc('month', (SELECT MAX(payment_date) FROM payments)),
        INTERVAL '1 month'
    )) AS month_start
)
SELECT
    cc.cohort_month,
    date_diff('month', cc.cohort_month, m.month_start) AS month_number,
    COUNT(DISTINCT CASE
        WHEN (cc.churn_date IS NULL OR cc.churn_date > m.month_start)
        THEN cc.customer_id
    END) AS retained,
    COUNT(DISTINCT cc.customer_id) AS cohort_size,
    ROUND(
        COUNT(DISTINCT CASE
            WHEN (cc.churn_date IS NULL OR cc.churn_date > m.month_start)
            THEN cc.customer_id
        END) * 100.0 / COUNT(DISTINCT cc.customer_id),
        1
    ) AS retention_pct
FROM customer_churn cc
CROSS JOIN months m
WHERE m.month_start >= cc.cohort_month
GROUP BY cc.cohort_month, month_number
ORDER BY cc.cohort_month, month_number;