"""Bucket aggregation, diagnostics, and hypothesis testing.

Fulfills Step 2 and Step 3 of pipeline.md:
- Equal-sized / balanced random bucketing.
- Monotonic bucket counts: K = 10, 50, ..., 1000, 10000, 100000 (User Level).
- Bucket diagnostic metrics (skewness, zeros, normality test p-values).
- Table 2 and Figure 2 generation.
- Strict testing rule: Welch's t-test is run ONLY on bucketed data (K < N_arm), never on raw user-level data.
- Mann-Whitney U is the primary statistical test across all aggregation levels.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


def partition_and_sum(
    revenues: np.ndarray,
    K: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Shuffle revenues and partition into K buckets, summing revenues within each bucket.

    If K >= len(revenues), returns the individual user revenues directly (raw user level).
    If n % K != 0, partitions into buckets differing in size by at most 1 user (via np.array_split),
    strictly conserving total revenue to machine precision.
    """
    n = len(revenues)
    if K >= n:
        return revenues.copy()

    shuffled = rng.permutation(revenues)
    if n % K == 0:
        bucket_size = n // K
        bucket_sums = shuffled.reshape(K, bucket_size).sum(axis=1)
    else:
        splits = np.array_split(shuffled, K)
        bucket_sums = np.array([b.sum() for b in splits], dtype=np.float64)

    # Assert revenue conservation
    np.testing.assert_allclose(bucket_sums.sum(), revenues.sum(), rtol=1e-10)
    return bucket_sums


def compute_table_2_diagnostics(
    user_rev: np.ndarray,
    bucket_counts: List[int],
    rng: np.random.Generator,
) -> Tuple[pd.DataFrame, Dict[int, np.ndarray]]:
    """Generate Table 2: Bucket-level diagnostic summary with normality test p-values."""
    n_users = len(user_rev)
    rows = []
    bucket_vectors: Dict[int, np.ndarray] = {}

    levels = sorted(bucket_counts)

    for k in levels:
        vec = partition_and_sum(user_rev, k, rng=rng)
        bucket_vectors[k] = vec

        n_obs = len(vec)
        users_per_obs = max(1, int(round(n_users / k)))
        m = float(np.mean(vec))
        s = float(np.std(vec, ddof=1))
        sk = float(stats.skew(vec))
        zero_frac = float((vec == 0.0).mean())

        # Normality test: normaltest requires at least 20 samples, shapiro for smaller
        if len(vec) >= 20:
            norm_res = stats.normaltest(vec)
            p_norm = float(norm_res.pvalue)
        else:
            norm_res = stats.shapiro(vec)
            p_norm = float(norm_res.pvalue)

        if k >= n_users:
            norm_note = "Rejected (Severe zero-inflation & right-skew)"
        elif p_norm < 0.01:
            norm_note = "Rejected (Residual skewness present)"
        elif p_norm < 0.05:
            norm_note = "Borderline (Weak non-normality)"
        else:
            norm_note = "Not Rejected (CLT bell-shaped)"

        label = f"{k} (User Level)" if k >= n_users else f"{k} Buckets"
        rows.append({
            "Aggregation Level": label,
            "K": k,
            "Observations": n_obs,
            "Users per Obs": users_per_obs,
            "Mean Revenue": m,
            "Std Dev": s,
            "Skewness": sk,
            "Zero Fraction": zero_frac,
            "Normality p-value": p_norm,
            "Normality Assessment": norm_note,
        })

    return pd.DataFrame(rows), bucket_vectors


def plot_figure_2_comparison(
    bucket_vectors: Dict[int, np.ndarray],
    out_path: Path,
) -> None:
    """Generate Figure 2: Multi-panel distribution comparison showing CLT normalization across key levels."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_k = sorted(bucket_vectors.keys())
    user_k = max(all_k)

    # Highlight progression: 50, 100, 500, 1000, User Level
    candidate_levels = [50, 100, 500, 1000, user_k]
    levels = [k for k in candidate_levels if k in bucket_vectors]
    if len(levels) < 3:
        levels = all_k[:5]

    n_panels = len(levels)
    fig, axes = plt.subplots(1, n_panels, figsize=(4.6 * n_panels, 4.0))
    if n_panels == 1:
        axes = [axes]

    colors = ["#2b5c8f", "#e66101", "#5e3c99", "#1b9e77", "#d95f02"]

    for idx, k in enumerate(levels):
        ax = axes[idx]
        vec = bucket_vectors[k]
        color = colors[idx % len(colors)]
        label = "User Level (Raw)" if k == user_k else f"{k} Buckets"

        sk = stats.skew(vec)
        zero_pct = (vec == 0.0).mean() * 100

        p99 = np.percentile(vec, 99)
        max_val = max(np.max(vec), 0.01)
        plot_max = max(p99 * 1.6, max_val if k < user_k else p99 * 1.5)

        ax.hist(vec, bins=35, range=(0, plot_max), color=color, edgecolor="black", alpha=0.75, density=True)
        ax.set_title(f"{label}\nSkewness: {sk:.2f} | Zeros: {zero_pct:.1f}%", fontsize=10.5, fontweight="bold")
        ax.set_xlabel("Aggregated Revenue")
        ax.set_ylabel("Density")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def run_welch_test(xA: np.ndarray, xB: np.ndarray) -> Tuple[float, float]:
    """Run two-sided Welch's t-test (unequal variance)."""
    res = stats.ttest_ind(xB, xA, equal_var=False)
    stat = float(res.statistic) if np.isfinite(res.statistic) else np.nan
    pval = float(res.pvalue) if np.isfinite(res.pvalue) else np.nan
    return stat, pval


def run_mwu_test(xA: np.ndarray, xB: np.ndarray) -> Tuple[float, float]:
    """Run two-sided Mann-Whitney U test."""
    res = stats.mannwhitneyu(xB, xA, alternative="two-sided")
    stat = float(res.statistic) if np.isfinite(res.statistic) else np.nan
    pval = float(res.pvalue) if np.isfinite(res.pvalue) else np.nan
    return stat, pval


def run_null_simulations(
    df_users: pd.DataFrame,
    control_share: float,
    bucket_counts: List[int],
    n_reps: int = 50,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute Step 3: Baseline null testing across fresh randomized A/B splits.

    Crucial rule: Welch is run ONLY on bucketed data (K < N_arm), MWU is run on all levels.
    """
    n_total = len(df_users)
    n_a = int(n_total * control_share)
    rng = np.random.default_rng(seed)

    records = []
    levels = sorted(bucket_counts)

    for rep in range(n_reps):
        perm = rng.permutation(n_total)
        a_rev = df_users["revenue"].values[perm[:n_a]]
        b_rev = df_users["revenue"].values[perm[n_a:]]

        for k in levels:
            xA = partition_and_sum(a_rev, k, rng=rng)
            xB = partition_and_sum(b_rev, k, rng=rng)

            # MWU is run across all levels (including User Level)
            mwu_stat, mwu_p = run_mwu_test(xA, xB)
            records.append({
                "repetition": rep,
                "K": k,
                "level_label": f"{k}_user" if k >= n_a else f"{k}_buckets",
                "test": "Mann-Whitney U",
                "statistic": mwu_stat,
                "p_value": mwu_p,
                "rejected": bool(mwu_p < alpha),
            })

            # Welch is run ONLY on bucketed data (K < N_arm)
            if k < n_a:
                welch_stat, welch_p = run_welch_test(xA, xB)
                records.append({
                    "repetition": rep,
                    "K": k,
                    "level_label": f"{k}_buckets",
                    "test": "Welch t-test",
                    "statistic": welch_stat,
                    "p_value": welch_p,
                    "rejected": bool(welch_p < alpha),
                })

    df_null = pd.DataFrame(records)

    # Compute Table 3 summary ordered by increasing K
    summary_rows = []
    for k in levels:
        lvl_str = f"{k} (User Level)" if k >= n_a else f"{k} Buckets"
        sub_mwu = df_null[(df_null["K"] == k) & (df_null["test"] == "Mann-Whitney U")]
        if len(sub_mwu) > 0:
            summary_rows.append({
                "Aggregation Level": lvl_str,
                "K": k,
                "Test": "Mann-Whitney U",
                "Repetitions": len(sub_mwu),
                "False Positive Rate": float(sub_mwu["rejected"].mean()),
                "Mean p-value": float(sub_mwu["p_value"].mean()),
                "Median p-value": float(sub_mwu["p_value"].median()),
            })
        if k < n_a:
            sub_w = df_null[(df_null["K"] == k) & (df_null["test"] == "Welch t-test")]
            if len(sub_w) > 0:
                summary_rows.append({
                    "Aggregation Level": lvl_str,
                    "K": k,
                    "Test": "Welch t-test",
                    "Repetitions": len(sub_w),
                    "False Positive Rate": float(sub_w["rejected"].mean()),
                    "Mean p-value": float(sub_w["p_value"].mean()),
                    "Median p-value": float(sub_w["p_value"].median()),
                })

    df_table_3 = pd.DataFrame(summary_rows)
    return df_table_3, df_null


def plot_figure_3_null_pvalues(df_null: pd.DataFrame, out_path: Path) -> None:
    """Generate Figure 3: Grouped bar chart with two colors (MWU vs Welch) ordered monotonically by increasing K."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    levels = sorted(df_null["K"].unique())
    user_k = max(levels)
    x_labels = [f"{k}\n(User)" if k == user_k else str(k) for k in levels]
    x_indices = np.arange(len(levels))
    bar_width = 0.38

    mwu_rates = []
    welch_rates = []

    for k in levels:
        sub_m = df_null[(df_null["K"] == k) & (df_null["test"] == "Mann-Whitney U")]
        mwu_rates.append(sub_m["rejected"].mean() if len(sub_m) > 0 else 0.0)

        sub_w = df_null[(df_null["K"] == k) & (df_null["test"] == "Welch t-test")]
        welch_rates.append(sub_w["rejected"].mean() if len(sub_w) > 0 else np.nan)

    fig, ax = plt.subplots(figsize=(11.5, 4.8))

    # Plot bars: MWU shifted left, Welch shifted right
    bars_mwu = ax.bar(x_indices - bar_width / 2, mwu_rates, width=bar_width, color="#d95f02", edgecolor="black", alpha=0.85, label="Mann-Whitney U (Main Test)")
    # For Welch, only plot for K < user_k
    valid_welch_idx = [i for i, r in enumerate(welch_rates) if not np.isnan(r)]
    bars_welch = ax.bar(
        [x_indices[i] + bar_width / 2 for i in valid_welch_idx],
        [welch_rates[i] for i in valid_welch_idx],
        width=bar_width,
        color="#2b5c8f",
        edgecolor="black",
        alpha=0.85,
        label="Welch t-test (Buckets only)",
    )

    # Reference line at nominal alpha = 0.05
    ax.axhline(0.05, color="red", linestyle="--", linewidth=1.6, label="Nominal alpha = 0.05")

    for bar in bars_mwu:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.003, f"{h:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#a63603")
    for bar in bars_welch:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.003, f"{h:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#08519c")

    ax.set_xticks(x_indices)
    ax.set_xticklabels(x_labels, fontsize=9.0)
    ax.set_xlabel("Number of Buckets (K) Growing Monotonically", fontsize=11, fontweight="bold")
    ax.set_ylabel("Empirical False Positive Rate (Type I Error)", fontsize=11, fontweight="bold")
    ax.set_title("Figure 3: Null False-Positive Rates across Fresh A/B Splits (Target = 0.05)", fontsize=12, fontweight="bold")
    ax.set_ylim(0, max(0.12, max(mwu_rates + [r for r in welch_rates if not np.isnan(r)]) + 0.03))
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(loc="upper right", fontsize=9.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
