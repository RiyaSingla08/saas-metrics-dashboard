"""
Runs all four core metric queries against saas_metrics.duckdb and prints
a preview of each, so you can verify the data model + queries are working
correctly before wiring them into the Dash app.

Run:
    python scripts/test_queries.py
"""

from pathlib import Path
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "saas_metrics.duckdb"

con = duckdb.connect(str(DB_PATH))

print("=" * 60)
print("1. MRR by month (last 6 months)")
print("=" * 60)
mrr = con.execute("""
    SELECT date_trunc('month', payment_date) AS month, SUM(amount) AS mrr
    FROM payments
    GROUP BY 1
    ORDER BY 1
""").df()
print(mrr.tail(6).to_string(index=False))

print()
print("=" * 60)
print("2. Churn rate by month (last 6 months)")
print("=" * 60)
churn = con.execute("""
    WITH customer_churn AS (
        SELECT c.customer_id, c.signup_date,
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
        COUNT(DISTINCT CASE WHEN cc.signup_date <= m.month_start
                              AND (cc.churn_date IS NULL OR cc.churn_date > m.month_start)
                             THEN cc.customer_id END) AS active_at_start,
        COUNT(DISTINCT CASE WHEN cc.churn_date IS NOT NULL
                              AND date_trunc('month', cc.churn_date) = m.month_start
                             THEN cc.customer_id END) AS churned_this_month
    FROM months m
    CROSS JOIN customer_churn cc
    GROUP BY m.month_start
    ORDER BY m.month_start
""").df()
churn["churn_rate_pct"] = (churn["churned_this_month"] / churn["active_at_start"] * 100).round(2)
print(churn.tail(6).to_string(index=False))

print()
print("=" * 60)
print("3. LTV - top 5 customers + average")
print("=" * 60)
ltv = con.execute("""
    SELECT c.customer_id, c.company_name, SUM(p.amount) AS lifetime_value
    FROM customers c
    JOIN subscriptions s ON c.customer_id = s.customer_id
    JOIN payments p ON s.subscription_id = p.subscription_id
    GROUP BY c.customer_id, c.company_name
    ORDER BY lifetime_value DESC
    LIMIT 5
""").df()
print(ltv.to_string(index=False))
avg_ltv = con.execute("""
    SELECT AVG(total) FROM (
        SELECT s.customer_id, SUM(p.amount) AS total
        FROM subscriptions s JOIN payments p ON s.subscription_id = p.subscription_id
        GROUP BY s.customer_id
    )
""").fetchone()[0]
print(f"\nAverage LTV across all customers: {avg_ltv:.2f}")

print()
print("=" * 60)
print("4. Cohort retention - Jan 2023 cohort, first 6 months")
print("=" * 60)
cohort = con.execute("""
    WITH customer_churn AS (
        SELECT c.customer_id, date_trunc('month', c.signup_date) AS cohort_month,
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
        COUNT(DISTINCT CASE WHEN (cc.churn_date IS NULL OR cc.churn_date > m.month_start)
                             THEN cc.customer_id END) AS retained,
        COUNT(DISTINCT cc.customer_id) AS cohort_size
    FROM customer_churn cc
    CROSS JOIN months m
    WHERE m.month_start >= cc.cohort_month
    GROUP BY cc.cohort_month, month_number
    ORDER BY cc.cohort_month, month_number
""").df()
cohort["retention_pct"] = (cohort["retained"] / cohort["cohort_size"] * 100).round(1)
first_cohort = cohort[cohort["cohort_month"] == cohort["cohort_month"].min()]
print(first_cohort.head(6).to_string(index=False))

con.close()
print("\nAll four queries ran successfully.")