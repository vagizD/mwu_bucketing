"""Shared utility functions for configuration, random seeds, and statistical helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Tuple
import numpy as np
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ab_testing")


def load_config(config_path: str | Path = "configs/default.yaml") -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def set_seed(seed: int = 42) -> np.random.Generator:
    """Set global seed and return a modern numpy Generator instance."""
    np.random.seed(seed)
    return np.random.default_rng(seed)


def wilson_score_interval(
    successes: int,
    trials: int,
    confidence_level: float = 0.95,
) -> Tuple[float, float, float]:
    """Compute Wilson score confidence interval for a binomial proportion.

    Parameters
    ----------
    successes : int
        Number of successes (e.g. rejections).
    trials : int
        Total number of trials (e.g. Monte Carlo repetitions).
    confidence_level : float
        Confidence level (default 0.95 for alpha=0.05).

    Returns
    -------
    proportion : float
        Point estimate successes / trials.
    lower_bound : float
        Wilson score interval lower bound.
    upper_bound : float
        Wilson score interval upper bound.
    """
    if trials == 0:
        return 0.0, 0.0, 0.0
    p = successes / trials
    if confidence_level == 0.95:
        z = 1.959963984540054
    else:
        from scipy import stats
        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)

    z2 = z * z
    denom = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / denom
    half_width = (z * np.sqrt((p * (1 - p) + z2 / (4 * trials)) / trials)) / denom

    lower = max(0.0, float(center - half_width))
    upper = min(1.0, float(center + half_width))
    if successes == 0:
        lower = 0.0
    if successes == trials:
        upper = 1.0
    return float(p), float(lower), float(upper)
