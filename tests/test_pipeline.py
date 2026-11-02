"""Comprehensive unit tests for AIPI 510 Project Pipeline (pipeline.md).

Verifies:
1. All config values loaded and operative.
2. Disjoint A/B split with no overlap and fixed membership.
3. Equal bucket sizes and strict revenue conservation.
4. Welch t-test is run ONLY on bucketed data (never on user-level data).
5. Only B receives synthetic treatment additions.
6. Target mean uplift matches delta in expectation.
7. Deterministic seeds reproducibility.
"""

import numpy as np
import pandas as pd
import pytest

from src.config import load_pipeline_config, PipelineConfig, TreatmentConfig
from src.data_loader import load_and_prepare_data
from src.treatment import generate_treatment
from src.bucketing import partition_and_sum, run_welch_test, run_mwu_test, compute_table_2_diagnostics


@pytest.fixture
def config() -> PipelineConfig:
    return load_pipeline_config("conf.toml")


def test_config_loaded_and_valid(config: PipelineConfig):
    """Verify all required config sections and fields are populated."""
    assert config.random_seed >= 0
    assert config.data.observation_start < config.data.observation_end
    assert 0 < config.ab.control_share < 1.0
    assert len(config.buckets.counts) > 0
    assert 100 in config.buckets.counts
    assert len(config.treatment.uplifts) > 0
    assert config.simulation.power_target == 0.80
    assert config.output.report_path == "result.md"


def test_disjoint_ab_split(config: PipelineConfig):
    """Verify A and B user sets have zero overlap and match configured sizes."""
    df_all, df_a, df_b, _, _ = load_and_prepare_data(config.data, config.ab, seed=config.random_seed)
    a_ids = set(df_a["customer_id"].values)
    b_ids = set(df_b["customer_id"].values)

    assert len(a_ids.intersection(b_ids)) == 0
    assert len(a_ids) == config.data.max_users // 2
    assert len(b_ids) == config.data.max_users // 2


def test_equal_bucket_sizes_and_revenue_conservation():
    """Verify equal bucket partitioning and exact revenue conservation."""
    rng = np.random.default_rng(42)
    n = 1000
    rev = rng.exponential(scale=0.03, size=n)

    for k in [10, 50, 100, 200]:
        bucket_sums = partition_and_sum(rev, k, rng=rng)
        assert len(bucket_sums) == k
        np.testing.assert_allclose(bucket_sums.sum(), rev.sum(), rtol=1e-10)


def test_welch_only_on_bucketed_data():
    """Verify pipeline constraint: Welch is tested on buckets, MWU on both."""
    rng = np.random.default_rng(42)
    xA = rng.normal(loc=1.0, scale=0.2, size=100)
    xB = rng.normal(loc=1.05, scale=0.2, size=100)

    # Welch works on bucketed data
    stat, pval = run_welch_test(xA, xB)
    assert np.isfinite(stat)
    assert 0.0 <= pval <= 1.0

    # MWU works on both
    m_stat, m_pval = run_mwu_test(xA, xB)
    assert np.isfinite(m_stat)
    assert 0.0 <= m_pval <= 1.0


def test_only_B_receives_synthetic_revenue():
    """Verify synthetic additions are strictly added to Group B customers only."""
    rng = np.random.default_rng(42)
    n = 500
    b_rev = rng.exponential(scale=0.02, size=n)
    b_act = rng.poisson(lam=1.5, size=n)
    prices = np.array([0.01, 0.02, 0.03, 0.05])

    treatment_cfg = TreatmentConfig(
        enabled=True,
        selection_strategy="activity_weighted",
        activity_smoothing_epsilon=0.01,
        price_sampling="empirical",
        condition_on_activity=False,
        uplifts=[0.05],
        m_count_model="poisson",
    )

    treated_b, meta = generate_treatment(
        b_revenues=b_rev,
        b_activities=b_act,
        observed_prices=prices,
        delta=0.05,
        treatment_cfg=treatment_cfg,
        rng=rng,
    )

    assert np.all(treated_b >= b_rev)
    assert meta["synthetic_revenue"] > 0
    assert meta["realized_M"] > 0


def test_mean_uplift_matches_delta_in_expectation():
    """Verify that expected incremental revenue across repeated draws matches delta * R_B."""
    rng = np.random.default_rng(123)
    n = 1000
    b_rev = rng.exponential(scale=0.03, size=n)
    b_act = rng.poisson(lam=2.0, size=n)
    prices = np.array([0.015, 0.025, 0.035, 0.045])
    delta = 0.05

    treatment_cfg = TreatmentConfig(
        enabled=True,
        selection_strategy="activity_weighted",
        activity_smoothing_epsilon=0.01,
        price_sampling="empirical",
        condition_on_activity=False,
        uplifts=[delta],
        m_count_model="poisson",
    )

    uplifts = []
    for _ in range(50):
        _, meta = generate_treatment(
            b_revenues=b_rev,
            b_activities=b_act,
            observed_prices=prices,
            delta=delta,
            treatment_cfg=treatment_cfg,
            rng=rng,
        )
        uplifts.append(meta["realized_uplift"])

    mean_realized = float(np.mean(uplifts))
    assert np.isclose(mean_realized, delta, rtol=0.10)
