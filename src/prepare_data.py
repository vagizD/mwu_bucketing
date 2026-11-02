"""Data preparation script for H&M customer-spending distribution or synthetic smoke test.

Supports both:
1. Processing raw H&M competition files (transactions_train.csv and customers.csv)
   over a chosen observation window.
2. Generating a clearly labeled synthetic smoke-test customer-spending dataset
   when raw Kaggle files are not yet downloaded.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

from src.utils import load_config, logger, set_seed


def check_raw_data_exists(
    transactions_path: str | Path,
    customers_path: str | Path,
) -> Tuple[bool, str]:
    """Check if the required raw H&M dataset files exist."""
    t_path = Path(transactions_path)
    c_path = Path(customers_path)
    if not t_path.is_file():
        return False, f"Missing transactions file: {t_path}"
    if not c_path.is_file():
        return False, f"Missing customers file: {c_path}"
    return True, "Both raw files exist."


def generate_synthetic_smoke_data(
    n_customers: int = 50_000,
    zero_fraction: float = 0.65,
    mean_nonzero_spend: float = 0.05,
    sd_nonzero_spend: float = 0.08,
    seed: int = 42,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Generate a synthetic customer-spending population mimicking retail fashion data.

    Characteristics:
    - Zero-inflation: ~60-70% of customers have zero transactions in the window.
    - Right-skewed positive spending: Log-normal distribution for active buyers.
    - Clearly labeled synthetic data for smoke tests and unit testing.

    Parameters
    ----------
    n_customers : int
        Total number of customers in the synthetic universe.
    zero_fraction : float
        Proportion of customers with zero spending.
    mean_nonzero_spend : float
        Mean spending among non-zero customers.
    sd_nonzero_spend : float
        Standard deviation of spending among non-zero customers.
    seed : int
        Random seed for reproducibility.
    output_path : str | Path | None
        Path to save CSV. If None, returns DataFrame without saving.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['customer_id', 'spending', 'is_synthetic'].
    """
    logger.info("Generating synthetic smoke-test data (n=%d, zero_frac=%.2f)...", n_customers, zero_fraction)
    rng = set_seed(seed)

    # Generate customer IDs
    customer_ids = [f"synth_{i:08d}" for i in range(n_customers)]

    # Determine zero vs non-zero customers
    is_zero = rng.random(n_customers) < zero_fraction
    n_positive = np.sum(~is_zero)

    # Log-normal parameters matching mean_nonzero_spend and sd_nonzero_spend
    # For lognormal: mean = exp(mu + sigma^2 / 2), var = (exp(sigma^2) - 1) * exp(2*mu + sigma^2)
    var = sd_nonzero_spend ** 2
    mu = np.log((mean_nonzero_spend ** 2) / np.sqrt(var + mean_nonzero_spend ** 2))
    sigma = np.sqrt(np.log(1 + var / (mean_nonzero_spend ** 2)))

    positive_spending = rng.lognormal(mean=mu, sigma=sigma, size=n_positive)
    # Clip negative values if any (lognormal is positive, but ensure safety)
    positive_spending = np.clip(positive_spending, a_min=0.001, a_max=None)

    spending = np.zeros(n_customers, dtype=np.float64)
    spending[~is_zero] = positive_spending

    df = pd.DataFrame({
        "customer_id": customer_ids,
        "spending": spending,
        "is_synthetic": True,
    })

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        logger.info("Synthetic customer spending saved to: %s", out)

    return df


def process_real_hm_data(
    transactions_path: str | Path,
    customers_path: str | Path,
    window_start_date: str = "2020-07-15",
    window_end_date: str = "2020-09-22",
    chunksize: int = 500_000,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Process raw H&M transaction data over a fixed observation window.

    - Sums transaction `price` by `customer_id` for dates in [window_start_date, window_end_date].
    - Left-joins onto full customer universe from `customers.csv`.
    - Imputes 0.0 for customers with no transactions in the observation window.
    - Validates data hygiene: no NaNs, non-negative spending, unique customers.

    Parameters
    ----------
    transactions_path : str | Path
        Path to raw transactions_train.csv.
    customers_path : str | Path
        Path to raw customers.csv.
    window_start_date : str
        Start date (inclusive, YYYY-MM-DD).
    window_end_date : str
        End date (inclusive, YYYY-MM-DD).
    chunksize : int
        Chunk size for streaming transactions.
    output_path : str | Path | None
        Path to save processed CSV.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['customer_id', 'spending', 'is_synthetic'].
    """
    logger.info("Processing real H&M data in window [%s, %s]...", window_start_date, window_end_date)
    t_path = Path(transactions_path)
    c_path = Path(customers_path)

    # 1. Read customer universe
    logger.info("Reading customer universe from %s...", c_path)
    customers_df = pd.read_csv(c_path, usecols=["customer_id"])
    total_customers = len(customers_df)
    unique_customers = customers_df["customer_id"].nunique()
    if unique_customers != total_customers:
        logger.warning("Duplicate customers detected in universe (%d unique out of %d)", unique_customers, total_customers)
        customers_df = customers_df.drop_duplicates(subset=["customer_id"])

    # 2. Stream transactions and aggregate in window
    logger.info("Streaming transactions from %s in chunks of %d...", t_path, chunksize)
    agg_chunks = []
    chunk_count = 0
    total_tx_in_window = 0

    for chunk in pd.read_csv(
        t_path,
        usecols=["t_dat", "customer_id", "price"],
        chunksize=chunksize,
        dtype={"customer_id": str, "price": np.float64, "t_dat": str},
    ):
        chunk_count += 1
        mask = (chunk["t_dat"] >= window_start_date) & (chunk["t_dat"] <= window_end_date)
        window_chunk = chunk.loc[mask]
        total_tx_in_window += len(window_chunk)

        if len(window_chunk) > 0:
            agg_chunk = window_chunk.groupby("customer_id")["price"].sum().reset_index()
            agg_chunks.append(agg_chunk)

    if agg_chunks:
        all_agg = pd.concat(agg_chunks, ignore_index=True)
        tx_agg = all_agg.groupby("customer_id")["price"].sum().reset_index()
        tx_agg.rename(columns={"price": "spending"}, inplace=True)
    else:
        logger.warning("No transactions found in specified window!")
        tx_agg = pd.DataFrame(columns=["customer_id", "spending"])

    logger.info("Found %d transactions across %d active customers in window.", total_tx_in_window, len(tx_agg))

    # 3. Left join with customer universe
    merged = customers_df.merge(tx_agg, on="customer_id", how="left")
    merged["spending"] = merged["spending"].fillna(0.0).astype(np.float64)
    merged["is_synthetic"] = False

    # 4. QA checks
    assert merged["spending"].isna().sum() == 0, "Error: NaN spending values detected."
    assert (merged["spending"] < 0).sum() == 0, "Error: Negative spending values detected."
    assert merged["customer_id"].nunique() == len(merged), "Error: Duplicate customer records detected."

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(out, index=False)
        logger.info("Processed customer spending saved to: %s", out)

    return merged


def validate_spending_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate summary statistics and distribution QA metrics for customer spending."""
    spending = df["spending"].values
    n = len(spending)
    zero_count = int(np.sum(spending == 0))
    zero_frac = float(zero_count / n) if n > 0 else 0.0
    positive_spend = spending[spending > 0]

    stats: Dict[str, Any] = {
        "n_customers": n,
        "n_zeros": zero_count,
        "zero_fraction": zero_frac,
        "mean_spending": float(np.mean(spending)) if n > 0 else 0.0,
        "std_spending": float(np.std(spending, ddof=1)) if n > 1 else 0.0,
        "median_spending": float(np.median(spending)) if n > 0 else 0.0,
        "max_spending": float(np.max(spending)) if n > 0 else 0.0,
        "q75": float(np.percentile(spending, 75)) if n > 0 else 0.0,
        "q90": float(np.percentile(spending, 90)) if n > 0 else 0.0,
        "q99": float(np.percentile(spending, 99)) if n > 0 else 0.0,
    }

    if len(positive_spend) > 0:
        stats["mean_positive_spending"] = float(np.mean(positive_spend))
        stats["median_positive_spending"] = float(np.median(positive_spend))
        stats["std_positive_spending"] = float(np.std(positive_spend, ddof=1)) if len(positive_spend) > 1 else 0.0

    return stats


def main() -> None:
    """CLI entry point for data preparation."""
    parser = argparse.ArgumentParser(description="Prepare customer spending data for A/B testing simulation.")
    parser.add_argument("--config", type=str, default="configs/default.yaml", help="Path to config file.")
    parser.add_argument("--smoke", action="store_true", help="Force synthetic smoke-test data generation.")
    parser.add_argument("--real", action="store_true", help="Force processing real H&M data.")
    args = parser.parse_args()

    config = load_config(args.config)
    raw_tx = config["data"]["raw_transactions_path"]
    raw_cust = config["data"]["raw_customers_path"]
    proc_out = config["data"]["processed_spending_path"]
    synth_out = config["data"]["synthetic_spending_path"]

    exists, msg = check_raw_data_exists(raw_tx, raw_cust)

    if args.smoke or (not exists and not args.real):
        logger.info("Running in smoke-test mode with synthetic customer spending.")
        if not exists:
            logger.info("Real H&M dataset not detected (%s).", msg)
            logger.info("See README.md for instructions on downloading real H&M Kaggle data.")
        smoke_cfg = config["smoke_test"]
        df = generate_synthetic_smoke_data(
            n_customers=smoke_cfg.get("n_customers_universe", 50_000),
            zero_fraction=smoke_cfg.get("zero_fraction", 0.65),
            mean_nonzero_spend=smoke_cfg.get("mean_nonzero_spend", 0.05),
            sd_nonzero_spend=smoke_cfg.get("sd_nonzero_spend", 0.08),
            seed=config["project"].get("seed", 42),
            output_path=synth_out,
        )
    else:
        if not exists:
            raise FileNotFoundError(f"Real data requested but files not found: {msg}")
        df = process_real_hm_data(
            transactions_path=raw_tx,
            customers_path=raw_cust,
            window_start_date=config["data"]["window_start_date"],
            window_end_date=config["data"]["window_end_date"],
            chunksize=config["data"].get("chunksize", 500_000),
            output_path=proc_out,
        )

    summary = validate_spending_distribution(df)
    logger.info("--- Spending Distribution Summary ---")
    for k, v in summary.items():
        logger.info("  %s: %.4f" if isinstance(v, float) else "  %s: %s", k, v)


if __name__ == "__main__":
    main()
