"""Confidence intervals for simulated hypothesis-test rejection rates."""

from typing import Tuple

import numpy as np
from scipy import stats


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Return a Wilson score interval for k rejections in n independent trials.

    For n=0, return (0, 0) so callers can represent missing observations
    without dividing by zero. A nonempty trial count is needed to interpret
    the interval statistically.
    """
    if n < 0 or not (0 <= k <= n):
        raise ValueError("Require 0 <= k <= n and n >= 0")
    if not (0 < confidence < 1):
        raise ValueError("confidence must be between 0 and 1")
    if n == 0:
        return 0.0, 0.0

    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p = k / n
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    half_width = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    lower = max(0.0, float(centre - half_width))
    upper = min(1.0, float(centre + half_width))
    if k == 0:
        lower = 0.0
    if k == n:
        upper = 1.0
    return lower, upper
