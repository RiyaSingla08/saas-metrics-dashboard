"""
Python wrappers around the core SQL metric queries.
Every function opens its own short-lived DuckDB connection, runs one
query, and returns a pandas DataFrame. Keeping these separate from the
Dash layout/callback code means the SQL logic can be tested and reused
independently of the web app (see scripts/test_queries.py).
"""

from pathlib import Path
import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "saas_metrics.duckdb"


def _connect():
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_plans() -> pd.DataFrame:
    """All pricing plans, used to populate the plan filter dropdown."""
    con = _connect()
    df = con.execute("SELECT plan_id, plan_name FROM plans ORDER BY plan_id").df()
    con.close()
    return df


def get_mrr_by_month(plan_ids=None) -> pd.DataFrame:
    """MRR per month, optionally filtered to a subset of plan_ids."""
    con = _connect()
    query = """
        SELECT date_trunc('month', p.payment_date) AS month, SUM(p.amount) AS mrr
        FROM payments p
        JOIN subscriptions s ON p.subscription_id = s.subscription_id
        WHERE (? IS NULL OR s.plan_id IN (SELECT UNNEST(?)))
        GROUP BY 1
        ORDER BY 1
    """
    has_filter = plan_ids is not None and len(plan_ids) > 0
    df = con.execute(query, [None if not has_filter else True, plan_ids if has_filter else []]).df()
    con.close()
    return df


def get_churn_by_month() -> pd.DataFrame:
    """Monthly churn rate. (Not plan-filtered for now -- churn is a whole-customer event.)"""
    con = _connect()
    df = con.execute("""
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
            m.month_start AS month,
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
    con.close()
    df["churn_rate_pct"] = (df["churned_this_month"] / df["active_at_start"] * 100).round(2)
    return df


def get_ltv_by_customer() -> pd.DataFrame:
    """Lifetime value per customer, highest first."""
    con = _connect()
    df = con.execute("""
        SELECT c.customer_id, c.company_name, SUM(p.amount) AS lifetime_value
        FROM customers c
        JOIN subscriptions s ON c.customer_id = s.customer_id
        JOIN payments p ON s.subscription_id = p.subscription_id
        GROUP BY c.customer_id, c.company_name
        ORDER BY lifetime_value DESC
    """).df()
    con.close()
    return df


def get_cohort_retention() -> pd.DataFrame:
    """Cohort retention table: one row per (cohort_month, month_number)."""
    con = _connect()
    df = con.execute("""
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
    con.close()
    df["retention_pct"] = (df["retained"] / df["cohort_size"] * 100).round(1)
    return df


def get_new_customers_by_month() -> pd.DataFrame:
    """New customer signups per month, used for the active-customers delta."""
    con = _connect()
    df = con.execute("""
        SELECT date_trunc('month', signup_date) AS month, COUNT(*) AS new_customers
        FROM customers
        GROUP BY 1
        ORDER BY 1
    """).df()
    con.close()
    return df


def get_kpi_summary() -> dict:
    """Headline numbers for the top KPI cards, including month-over-month deltas."""
    mrr_df = get_mrr_by_month()
    churn_df = get_churn_by_month()
    ltv_df = get_ltv_by_customer()
    new_cust_df = get_new_customers_by_month()

    con = _connect()
    active_customers = con.execute(
        "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
    ).fetchone()[0]
    con.close()

    current_mrr = mrr_df["mrr"].iloc[-1] if len(mrr_df) else 0
    prev_mrr = mrr_df["mrr"].iloc[-2] if len(mrr_df) > 1 else 0
    mrr_delta_pct = ((current_mrr - prev_mrr) / prev_mrr * 100) if prev_mrr else 0

    current_churn = churn_df["churn_rate_pct"].iloc[-1] if len(churn_df) else 0
    prev_churn = churn_df["churn_rate_pct"].iloc[-2] if len(churn_df) > 1 else 0
    churn_delta_pts = current_churn - prev_churn

    new_this_month = new_cust_df["new_customers"].iloc[-1] if len(new_cust_df) else 0
    churned_this_month = churn_df["churned_this_month"].iloc[-1] if len(churn_df) else 0
    net_new_customers = new_this_month - churned_this_month

    return {
        "current_mrr": current_mrr,
        "prev_mrr": prev_mrr,
        "mrr_delta_pct": mrr_delta_pct,
        "current_churn_pct": current_churn,
        "churn_delta_pts": churn_delta_pts,
        "avg_ltv": ltv_df["lifetime_value"].mean() if len(ltv_df) else 0,
        "active_customers": active_customers,
        "net_new_customers": net_new_customers,
    }
