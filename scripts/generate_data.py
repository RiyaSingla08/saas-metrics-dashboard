"""
Generates realistic synthetic SaaS data and loads it into the DuckDB database:
customers, subscriptions (with upgrades/downgrades/churn), and payments.

Run this AFTER init_db.py has created the empty tables:
    python scripts/generate_data.py

Re-running this script clears existing data first, so it's safe to re-run
any time you want a fresh random dataset.
"""

import random
from datetime import date, timedelta
from pathlib import Path

import duckdb
from dateutil.relativedelta import relativedelta
from faker import Faker

fake = Faker()
random.seed(42)   # fixed seed = reproducible data, easier to debug together
Faker.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "saas_metrics.duckdb"

# ------------------------------------------------------------------
# Simulation parameters
# ------------------------------------------------------------------
NUM_CUSTOMERS = 600
SIM_START = date(2023, 1, 1)
SIM_END = date(2026, 8, 1)   # "today" for this simulated business

PLANS = [
    # (plan_id, plan_name, monthly_price, signup_weight)
    (1, "Starter", 29.00, 0.55),
    (2, "Pro", 99.00, 0.35),
    (3, "Enterprise", 299.00, 0.10),
]
PLAN_BY_ID = {p[0]: p for p in PLANS}

COUNTRIES = ["United States", "United Kingdom", "India", "Germany",
             "Canada", "Australia", "France", "Brazil"]

# Monthly churn probability by plan (cheaper plans churn more)
BASE_MONTHLY_CHURN = {1: 0.035, 2: 0.018, 3: 0.007}
# Extra churn risk multiplier during a customer's first 3 months
EARLY_CHURN_MULTIPLIER = 2.2
EARLY_MONTHS = 3

MONTHLY_UPGRADE_PROB = 0.02
MONTHLY_DOWNGRADE_PROB = 0.008


def weighted_plan_choice():
    plans, weights = zip(*[(p[0], p[3]) for p in PLANS])
    return random.choices(plans, weights=weights, k=1)[0]


def month_range(start: date, end: date):
    """Yield the first-of-month date for every month from start to end inclusive."""
    current = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while current <= end_month:
        yield current
        current += relativedelta(months=1)


def signup_dates(n):
    """
    Generate n signup dates across the sim window with:
    - overall upward growth trend (more signups per month as time goes on)
    - a seasonal dip in December, bump in January/September
    """
    months = list(month_range(SIM_START, SIM_END - relativedelta(months=1)))
    weights = []
    for i, m in enumerate(months):
        growth_weight = 1 + (i / len(months)) * 2.5   # ramps up over time
        seasonal = 1.0
        if m.month == 12:
            seasonal = 0.5
        elif m.month in (1, 9):
            seasonal = 1.4
        weights.append(growth_weight * seasonal)

    chosen_months = random.choices(months, weights=weights, k=n)
    dates = []
    for m in chosen_months:
        # spread signups randomly across the days of that month
        day = random.randint(1, 28)
        dates.append(date(m.year, m.month, day))
    return sorted(dates)


def simulate_customer(customer_id, signup_date):
    """
    Walk a customer forward month by month from signup to SIM_END,
    producing a list of subscription rows and payment rows.
    Returns (subscriptions, payments) for this one customer.
    """
    subscriptions = []
    payments = []

    plan_id = weighted_plan_choice()
    sub_start = signup_date
    months_on_current_plan = 0
    subscription_id_counter = 0  # local counter, remapped to global later

    current_month = date(signup_date.year, signup_date.month, 1)

    while current_month <= date(SIM_END.year, SIM_END.month, 1):
        months_on_current_plan += 1

        # Record a payment for this active month
        plan = PLAN_BY_ID[plan_id]
        payments.append({
            "customer_id": customer_id,
            "subscription_seq": subscription_id_counter,
            "payment_date": current_month + timedelta(days=random.randint(0, 4)),
            "amount": plan[2],
        })

        # Roll for churn
        churn_prob = BASE_MONTHLY_CHURN[plan_id]
        if months_on_current_plan <= EARLY_MONTHS:
            churn_prob *= EARLY_CHURN_MULTIPLIER

        if random.random() < churn_prob:
            subscriptions.append({
                "customer_id": customer_id,
                "subscription_seq": subscription_id_counter,
                "plan_id": plan_id,
                "start_date": sub_start,
                "end_date": current_month,
                "status": "churned",
            })
            return subscriptions, payments  # customer is gone, stop simulating

        # Roll for plan change (only if not churning this month)
        roll = random.random()
        new_plan_id = None
        if roll < MONTHLY_UPGRADE_PROB and plan_id != 3:
            new_plan_id = plan_id + 1  # move up one tier
        elif roll < MONTHLY_UPGRADE_PROB + MONTHLY_DOWNGRADE_PROB and plan_id != 1:
            new_plan_id = plan_id - 1  # move down one tier

        if new_plan_id is not None:
            status = "upgraded" if new_plan_id > plan_id else "downgraded"
            subscriptions.append({
                "customer_id": customer_id,
                "subscription_seq": subscription_id_counter,
                "plan_id": plan_id,
                "start_date": sub_start,
                "end_date": current_month,
                "status": status,
            })
            # start a new subscription segment on the new plan
            subscription_id_counter += 1
            plan_id = new_plan_id
            sub_start = current_month
            months_on_current_plan = 0

        current_month += relativedelta(months=1)

    # Reached SIM_END still active
    subscriptions.append({
        "customer_id": customer_id,
        "subscription_seq": subscription_id_counter,
        "plan_id": plan_id,
        "start_date": sub_start,
        "end_date": None,
        "status": "active",
    })
    return subscriptions, payments


def generate_all():
    print(f"Generating {NUM_CUSTOMERS} customers from {SIM_START} to {SIM_END}...")

    customers = []
    all_subscriptions = []
    all_payments = []

    dates = signup_dates(NUM_CUSTOMERS)

    for i, sdate in enumerate(dates, start=1):
        customers.append({
            "customer_id": i,
            "company_name": fake.company(),
            "signup_date": sdate,
            "country": random.choice(COUNTRIES),
        })
        subs, pays = simulate_customer(i, sdate)
        all_subscriptions.extend(subs)
        all_payments.extend(pays)

    # Assign global subscription_ids and remap payments to point at them
    sub_id_lookup = {}  # (customer_id, subscription_seq) -> subscription_id
    for idx, s in enumerate(all_subscriptions, start=1):
        s["subscription_id"] = idx
        sub_id_lookup[(s["customer_id"], s["subscription_seq"])] = idx

    for idx, p in enumerate(all_payments, start=1):
        p["payment_id"] = idx
        p["subscription_id"] = sub_id_lookup[(p["customer_id"], p["subscription_seq"])]

    print(f"  customers:     {len(customers)}")
    print(f"  subscriptions: {len(all_subscriptions)}")
    print(f"  payments:      {len(all_payments)}")

    return customers, all_subscriptions, all_payments


def load_into_db(customers, subscriptions, payments):
    con = duckdb.connect(str(DB_PATH))

    # Clear existing data (safe to re-run this script)
    con.execute("DELETE FROM payments")
    con.execute("DELETE FROM subscriptions")
    con.execute("DELETE FROM customers")
    con.execute("DELETE FROM plans")

    con.executemany(
        "INSERT INTO plans (plan_id, plan_name, monthly_price) VALUES (?, ?, ?)",
        [(p[0], p[1], p[2]) for p in PLANS],
    )

    con.executemany(
        "INSERT INTO customers (customer_id, company_name, signup_date, country) VALUES (?, ?, ?, ?)",
        [(c["customer_id"], c["company_name"], c["signup_date"], c["country"]) for c in customers],
    )

    con.executemany(
        "INSERT INTO subscriptions (subscription_id, customer_id, plan_id, start_date, end_date, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(s["subscription_id"], s["customer_id"], s["plan_id"], s["start_date"], s["end_date"], s["status"])
         for s in subscriptions],
    )

    con.executemany(
        "INSERT INTO payments (payment_id, subscription_id, payment_date, amount) VALUES (?, ?, ?, ?)",
        [(p["payment_id"], p["subscription_id"], p["payment_date"], p["amount"]) for p in payments],
    )

    # Quick sanity check
    counts = con.execute("""
        SELECT 'customers', COUNT(*) FROM customers
        UNION ALL SELECT 'plans', COUNT(*) FROM plans
        UNION ALL SELECT 'subscriptions', COUNT(*) FROM subscriptions
        UNION ALL SELECT 'payments', COUNT(*) FROM payments
    """).fetchall()

    print("\nLoaded into database:")
    for table, count in counts:
        print(f"  {table}: {count} rows")

    con.close()


if __name__ == "__main__":
    customers, subscriptions, payments = generate_all()
    load_into_db(customers, subscriptions, payments)
    print(f"\nDone. Database at: {DB_PATH}")