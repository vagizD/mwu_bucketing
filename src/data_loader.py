"""Data loading, cleaning, baseline user-level aggregation, and exploratory analysis.

Fulfills Step 1 of pipeline.md:
- Prepares customer-level revenue within observation window.
- Handles zero-revenue users.
- Splits into fixed A and B groups.
- Generates Table 1 (User-level revenue summary) and Figure 1 (User revenue distribution).
"""

from pathlib import Path
from typing import Dict, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.config import DataConfig, ABConfig


def create_synthetic_fixture(
    customers_path: Path,
    transactions_path: Path,
    start_date: str = "2019-09-01",
    end_date: str = "2019-09-30",
    n_customers: int = 25000,
    seed: int = 42,
) -> None:
    """Generate synthetic H&M-like data fixture conforming to exact schema and date window."""
    customers_path.parent.mkdir(parents=True, exist_ok=True)
    transactions_path.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    customer_ids = [f"cust_{i:07d}" for i in range(n_customers)]

    # Customers table
    df_customers = pd.DataFrame({"customer_id": customer_ids})
    df_customers.to_csv(customers_path, index=False)

    # Activity: ~65% zero purchases in the 30-day window
    active_mask = rng.random(n_customers) > 0.65
    active_customers = [cid for cid, act in zip(customer_ids, active_mask) if act]

    tx_custs = []
    tx_prices = []
    tx_dates = []

    start_ts = pd.to_datetime(start_date).timestamp()
    end_ts = pd.to_datetime(end_date).timestamp()

    # Draw purchase counts per active customer (1 to ~8 purchases)
    counts = rng.geometric(p=0.45, size=len(active_customers))
    for cid, cnt in zip(active_customers, counts):
        tx_custs.extend([cid] * cnt)
        # Log-normal prices typical of H&M normalized prices (median ~ 0.025)
        prices = np.clip(rng.lognormal(mean=-3.7, sigma=0.6, size=cnt), 0.001, 0.5)
        tx_prices.extend(prices)
        dates = pd.to_datetime(rng.uniform(start_ts, end_ts, size=cnt), unit="s").strftime("%Y-%m-%d")
        tx_dates.extend(dates)

    df_tx = pd.DataFrame({
        "t_dat": tx_dates,
        "customer_id": tx_custs,
        "price": tx_prices,
    })
    df_tx.to_csv(transactions_path, index=False)


def load_and_prepare_data(
    data_cfg: DataConfig,
    ab_cfg: ABConfig,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, Dict[str, Any]]:
    """Load transactions and customers, filter by date, clean, and partition into A and B.

    Returns:
        df_all: DataFrame with all eligible customers (revenue, activity, group)
        df_a: Control arm DataFrame
        df_b: Treatment arm DataFrame
        observed_prices: 1D array of cleaned transaction prices
        stats: dictionary of data hygiene and baseline statistics
    """
    tx_path = Path(data_cfg.transactions_path)
    cust_path = Path(data_cfg.customers_path)

    is_synthetic = False
    required_users = data_cfg.max_users if data_cfg.max_users > 0 else 20000
    n_fixture = max(25000, required_users + 4000)

    if not tx_path.is_file() or not cust_path.is_file():
        is_synthetic = True
        create_synthetic_fixture(
            customers_path=cust_path,
            transactions_path=tx_path,
            start_date=data_cfg.observation_start,
            end_date=data_cfg.observation_end,
            n_customers=n_fixture,
            seed=seed,
        )

    # Read customers
    df_cust = pd.read_csv(cust_path, usecols=["customer_id"])
    if len(df_cust) < data_cfg.max_users and df_cust["customer_id"].iloc[0].startswith("cust_"):
        is_synthetic = True
        create_synthetic_fixture(
            customers_path=cust_path,
            transactions_path=tx_path,
            start_date=data_cfg.observation_start,
            end_date=data_cfg.observation_end,
            n_customers=n_fixture,
            seed=seed,
        )
        df_cust = pd.read_csv(cust_path, usecols=["customer_id"])

    total_customers_raw = len(df_cust)

    # Subsample customers BEFORE A/B assignment if max_users > 0
    if 0 < data_cfg.max_users < total_customers_raw:
        rng = np.random.default_rng(seed)
        sampled_indices = rng.choice(total_customers_raw, size=data_cfg.max_users, replace=False)
        df_cust = df_cust.iloc[sampled_indices].reset_index(drop=True)

    eligible_cust_set = set(df_cust["customer_id"].values)
    eligible_count = len(df_cust)

    # Read transactions
    df_tx = pd.read_csv(tx_path)
    total_tx_raw = len(df_tx)

    # Filter by date window
    df_tx["t_dat"] = pd.to_datetime(df_tx["t_dat"], errors="coerce")
    start_dt = pd.to_datetime(data_cfg.observation_start)
    end_dt = pd.to_datetime(data_cfg.observation_end)
    window_mask = (df_tx["t_dat"] >= start_dt) & (df_tx["t_dat"] <= end_dt)
    df_tx = df_tx[window_mask].copy()

    # Clean prices: positive, finite, non-null
    valid_price_mask = (df_tx["price"].notna()) & (df_tx["price"] > 0) & np.isfinite(df_tx["price"])
    df_tx = df_tx[valid_price_mask].copy()

    # Restrict transactions to eligible cohort
    tx_eligible_mask = df_tx["customer_id"].isin(eligible_cust_set)
    df_tx = df_tx[tx_eligible_mask].copy()

    observed_prices = df_tx["price"].values.astype(np.float64)

    # Aggregate by customer
    tx_agg = df_tx.groupby("customer_id")["price"].agg(["sum", "count"]).reset_index()
    tx_agg.columns = ["customer_id", "revenue", "activity"]

    if data_cfg.include_zero_revenue_users:
        df_all = pd.merge(df_cust, tx_agg, on="customer_id", how="left")
        df_all["revenue"] = df_all["revenue"].fillna(0.0).astype(np.float64)
        df_all["activity"] = df_all["activity"].fillna(0).astype(np.int64)
    else:
        df_all = tx_agg.copy()

    n_total = len(df_all)
    n_a = int(n_total * ab_cfg.control_share)
    n_b = n_total - n_a

    # Fixed A/B split with deterministic seed
    rng_split = np.random.default_rng(seed)
    shuffled_idx = rng_split.permutation(n_total)
    idx_a = shuffled_idx[:n_a]
    idx_b = shuffled_idx[n_a:]

    df_a = df_all.iloc[idx_a].copy().reset_index(drop=True)
    df_b = df_all.iloc[idx_b].copy().reset_index(drop=True)

    df_a["group"] = "A"
    df_b["group"] = "B"
    df_all["group"] = ""
    df_all.loc[idx_a, "group"] = "A"
    df_all.loc[idx_b, "group"] = "B"

    stats = {
        "is_synthetic_fixture": is_synthetic,
        "eligible_customers": n_total,
        "n_a": n_a,
        "n_b": n_b,
        "observed_transactions": len(df_tx),
        "mean_price": float(np.mean(observed_prices)) if len(observed_prices) > 0 else 0.0,
        "median_price": float(np.median(observed_prices)) if len(observed_prices) > 0 else 0.0,
    }

    return df_all, df_a, df_b, observed_prices, stats


def compute_table_1_summary(df_all: pd.DataFrame, df_a: pd.DataFrame, df_b: pd.DataFrame) -> pd.DataFrame:
    """Generate Table 1: User-level revenue summary without percentiles (Zero Share is sufficient)."""
    rows = []
    for label, df in [("All Users", df_all), ("Group A (Control)", df_a), ("Group B (Treatment)", df_b)]:
        rev = df["revenue"].values
        n = len(rev)
        zero_share = (rev == 0.0).mean() if n > 0 else 0.0
        rows.append({
            "Cohort": label,
            "Count": n,
            "Mean": float(np.mean(rev)),
            "Median": float(np.median(rev)),
            "Std Dev": float(np.std(rev, ddof=1)),
            "Min": float(np.min(rev)),
            "Max": float(np.max(rev)),
            "Zero Share": float(zero_share),
        })
    return pd.DataFrame(rows)


def plot_figure_1_distribution(df_all: pd.DataFrame, out_path: Path) -> None:
    """Generate Figure 1: 2-panel distribution of user revenue (Linear and log(1 + revenue))."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rev = df_all["revenue"].values

    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(12, 4.5))

    # Linear histogram
    p99 = np.percentile(rev, 99)
    ax_lin.hist(rev, bins=40, range=(0, max(p99 * 1.5, 0.05)), color="#2b5c8f", edgecolor="black", alpha=0.7)
    zero_pct = (rev == 0.0).mean() * 100
    ax_lin.set_title(f"User Revenue (Linear Scale)\nZero-Mass = {zero_pct:.1f}%", fontsize=11, fontweight="bold")
    ax_lin.set_xlabel("User Total Revenue")
    ax_lin.set_ylabel("Customer Count")
    ax_lin.grid(True, alpha=0.3)

    # Log1p histogram
    log_rev = np.log1p(rev)
    ax_log.hist(log_rev, bins=40, color="#d95f02", edgecolor="black", alpha=0.7)
    ax_log.set_title("User Revenue (log(1 + Revenue))", fontsize=11, fontweight="bold")
    ax_log.set_xlabel("log(1 + Revenue)")
    ax_log.set_ylabel("Customer Count")
    ax_log.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
