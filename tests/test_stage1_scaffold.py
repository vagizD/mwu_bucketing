"""Unit tests for Stage 1 scaffolding, configuration, utilities, and synthetic data generation."""

from pathlib import Path
import numpy as np
import pytest

from src.utils import load_config, set_seed, wilson_score_interval
from src.prepare_data import (
    check_raw_data_exists,
    generate_synthetic_smoke_data,
    validate_spending_distribution,
)


def test_load_config():
    """Verify that the default configuration file loads and contains all required keys."""
    config_path = Path("configs/default.yaml")
    assert config_path.is_file(), "default.yaml must exist"
    config = load_config(config_path)

    assert "project" in config
    assert "data" in config
    assert "smoke_test" in config
    assert "main_study" in config

    # Check key simulation parameters
    assert "n_customers_per_arm" in config["main_study"]
    assert "bucket_counts" in config["main_study"]
    assert "uplifts" in config["main_study"]
    assert config["main_study"]["alpha"] == 0.05
    assert config["main_study"]["practical_threshold"] == 0.01


def test_wilson_score_interval():
    """Verify Wilson score confidence interval calculation."""
    # Zero successes
    p, low, high = wilson_score_interval(0, 100, confidence_level=0.95)
    assert p == 0.0
    assert 0.0 <= low <= high <= 1.0
    assert low == 0.0
    assert high > 0.0

    # 50% successes
    p, low, high = wilson_score_interval(50, 100, confidence_level=0.95)
    assert p == 0.5
    assert 0.39 < low < 0.5
    assert 0.5 < high < 0.61
    assert abs((high - 0.5) - (0.5 - low)) < 1e-5

    # 100% successes
    p, low, high = wilson_score_interval(100, 100, confidence_level=0.95)
    assert p == 1.0
    assert high == 1.0
    assert low < 1.0


def test_raw_data_check():
    """Verify raw data checking on nonexistent paths."""
    exists, msg = check_raw_data_exists("nonexistent_tx.csv", "nonexistent_cust.csv")
    assert not exists
    assert "Missing" in msg


def test_synthetic_data_generation():
    """Verify that synthetic data generation respects constraints and distribution."""
    n = 2000
    zero_frac = 0.60
    df = generate_synthetic_smoke_data(
        n_customers=n,
        zero_fraction=zero_frac,
        mean_nonzero_spend=0.05,
        sd_nonzero_spend=0.08,
        seed=123,
    )

    assert len(df) == n
    assert "customer_id" in df.columns
    assert "spending" in df.columns
    assert "is_synthetic" in df.columns
    assert df["is_synthetic"].all()

    # QA checks
    assert df["spending"].isna().sum() == 0, "No NaNs allowed"
    assert (df["spending"] < 0).sum() == 0, "No negative spending allowed"
    assert df["customer_id"].nunique() == n, "Customer IDs must be unique"

    # Distribution checks
    stats = validate_spending_distribution(df)
    assert abs(stats["zero_fraction"] - zero_frac) < 0.05, "Observed zero fraction should be close to 0.60"
    assert stats["mean_spending"] > 0
    assert stats["median_spending"] == 0.0  # Since >50% are zero
    assert stats["mean_positive_spending"] > 0
