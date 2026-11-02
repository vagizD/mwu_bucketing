"""Synthetic treatment generator for Group B customer cohort.

Fulfills Step 4 of pipeline.md:
- Compound Poisson event generation: M ~ Poisson(Delta_R / p_bar)
- Target expected incremental revenue: Delta_R = delta * R_B
- Swappable customer selection: activity_weighted (smoothed with epsilon) and uniform
- Empirical transaction price sampling with replacement
- Strictly treatment in B only; Group A is never modified.
"""

from typing import Dict, Tuple, Any
import numpy as np

from src.config import TreatmentConfig


def select_activity_weighted(
    b_indices: np.ndarray,
    b_activities: np.ndarray,
    M: int,
    epsilon: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Select M customer indices with probability proportional to (activity + epsilon)."""
    if M <= 0:
        return np.empty(0, dtype=np.int64)

    weights = b_activities.astype(np.float64) + epsilon
    total_weight = weights.sum()
    if total_weight <= 0:
        raise ValueError("Total sampling weight in Group B is non-positive.")

    probs = weights / total_weight
    chosen_pos = rng.choice(len(b_indices), size=M, replace=True, p=probs)
    return b_indices[chosen_pos]


def select_uniform(
    b_indices: np.ndarray,
    b_activities: np.ndarray,
    M: int,
    epsilon: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Select M customer indices uniformly with replacement."""
    if M <= 0:
        return np.empty(0, dtype=np.int64)
    chosen_pos = rng.choice(len(b_indices), size=M, replace=True)
    return b_indices[chosen_pos]


def generate_treatment(
    b_revenues: np.ndarray,
    b_activities: np.ndarray,
    observed_prices: np.ndarray,
    delta: float,
    treatment_cfg: TreatmentConfig,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Generate synthetic transactions in B for an expected relative uplift delta.

    Returns:
        treated_b_rev: updated Group B revenue array
        meta: dictionary with realized M, synthetic revenue, realized uplift, etc.
    """
    R_B = float(np.sum(b_revenues))
    Delta_R = delta * R_B
    mean_price = float(np.mean(observed_prices))

    if delta <= 0 or Delta_R <= 0:
        return b_revenues.copy(), {
            "delta": delta,
            "target_delta_R": 0.0,
            "realized_M": 0,
            "synthetic_revenue": 0.0,
            "realized_uplift": 0.0,
        }

    # Step 4.2 & 4.3: Poisson draw
    lam = Delta_R / mean_price
    M = int(rng.poisson(lam=lam))

    if M == 0:
        return b_revenues.copy(), {
            "delta": delta,
            "target_delta_R": Delta_R,
            "realized_M": 0,
            "synthetic_revenue": 0.0,
            "realized_uplift": 0.0,
        }

    # Step 4.4: Select customer IDs from B only
    b_indices = np.arange(len(b_revenues))
    if treatment_cfg.selection_strategy == "activity_weighted":
        selected_idx = select_activity_weighted(
            b_indices=b_indices,
            b_activities=b_activities,
            M=M,
            epsilon=treatment_cfg.activity_smoothing_epsilon,
            rng=rng,
        )
    elif treatment_cfg.selection_strategy == "uniform":
        selected_idx = select_uniform(
            b_indices=b_indices,
            b_activities=b_activities,
            M=M,
            epsilon=treatment_cfg.activity_smoothing_epsilon,
            rng=rng,
        )
    else:
        raise ValueError(f"Unknown selection_strategy: {treatment_cfg.selection_strategy}")

    # Step 4.5: Sample empirical transaction prices with replacement
    synthetic_prices = rng.choice(observed_prices, size=M, replace=True)

    # Step 4.6: Add synthetic amounts to selected B customers
    treated_b_rev = b_revenues.copy()
    user_additions = np.bincount(selected_idx, weights=synthetic_prices, minlength=len(b_revenues))
    treated_b_rev += user_additions

    syn_rev_total = float(np.sum(synthetic_prices))
    realized_uplift = (syn_rev_total / R_B) if R_B > 0 else 0.0

    meta = {
        "delta": delta,
        "target_delta_R": Delta_R,
        "realized_M": M,
        "synthetic_revenue": syn_rev_total,
        "realized_uplift": realized_uplift,
    }
    return treated_b_rev, meta
