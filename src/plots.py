"""Plotting module for distribution diagnostics, p-values vs K, and rejection rates.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate the Wilson score interval for a binomial proportion."""
    if n <= 0:
        return 0.0, 0.0
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p = k / n
    denominator = 1 + z**2 / n
    centre_adjusted_probability = (p + z**2 / (2 * n)) / denominator
    half_width = (z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)) / denominator
    lower = max(0.0, float(centre_adjusted_probability - half_width))
    upper = min(1.0, float(centre_adjusted_probability + half_width))
    if k == 0:
        lower = 0.0
    if k == n:
        upper = 1.0
    return lower, upper


def plot_distribution_comparison(
    x_A: np.ndarray,
    x_B: np.ndarray,
    K: int,
    delta: float,
    out_path: Path,
    test_res: Dict[str, Any],
) -> None:
    """Plot A/B revenue distribution with linear and log1p scales plus summary statistics."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(14, 5))

    k_label = f"K={K} Buckets" if K > 0 else "User-Level (K=0)"
    title_prefix = f"Baseline ($\Delta=0$)" if delta == 0 else f"Treated ($\Delta={delta:.3f}$)"

    # Linear scale
    # Determine common range up to 99th percentile to keep visual clarity while noting extremes
    q99 = max(np.percentile(x_A, 99), np.percentile(x_B, 99))
    max_val = max(np.max(x_A), np.max(x_B))
    min_val = min(np.min(x_A), np.min(x_B))

    bins_lin = np.linspace(min_val, max(q99 * 1.5, 0.01), 40)
    ax_lin.hist(x_A, bins=bins_lin, alpha=0.5, label="Group A (Control)", color="#2b5c8f", density=True)
    ax_lin.hist(x_B, bins=bins_lin, alpha=0.5, label="Group B (Treatment)", color="#d95f02", density=True)
    ax_lin.set_title(f"{title_prefix} — Linear Density ({k_label})", fontsize=11, fontweight="bold")
    ax_lin.set_xlabel("Aggregated Revenue")
    ax_lin.set_ylabel("Density")
    ax_lin.legend(loc="upper right")
    ax_lin.grid(True, alpha=0.3)

    # Log1p scale
    log_A = np.log1p(np.maximum(0, x_A))
    log_B = np.log1p(np.maximum(0, x_B))
    bins_log = np.linspace(0, max(np.max(log_A), np.max(log_B), 0.1), 40)
    ax_log.hist(log_A, bins=bins_log, alpha=0.5, label="Group A", color="#2b5c8f", density=True)
    ax_log.hist(log_B, bins=bins_log, alpha=0.5, label="Group B", color="#d95f02", density=True)
    ax_log.set_title(f"{title_prefix} — log1p(Revenue) ({k_label})", fontsize=11, fontweight="bold")
    ax_log.set_xlabel("log1p(Revenue)")
    ax_log.set_ylabel("Density")
    ax_log.legend(loc="upper right")
    ax_log.grid(True, alpha=0.3)

    # Annotate summary stats in linear panel
    stats_text = (
        f"A: n={test_res['n_A']}, mean={test_res['mean_A']:.4f}, med={test_res['median_A']:.4f}, 0-frac={test_res['zero_frac_A']:.1%}\n"
        f"B: n={test_res['n_B']}, mean={test_res['mean_B']:.4f}, med={test_res['median_B']:.4f}, 0-frac={test_res['zero_frac_B']:.1%}\n"
        f"Diff: {test_res['diff_mean']:.5f} ({test_res['rel_diff_mean']:+.2%})\n"
        f"Welch t: {test_res['welch_stat']:.3f} (p={test_res['welch_p']:.4e})\n"
        f"MWU stat: {test_res['mwu_stat']:.0f} (p={test_res['mwu_p']:.4e})"
    )
    ax_lin.text(
        0.03, 0.97, stats_text,
        transform=ax_lin.transAxes,
        fontsize=8.5,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85, edgecolor="#ccc"),
    )

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_pvalues_vs_K(
    df_summary: pd.DataFrame,
    out_path: Path,
) -> None:
    """Plot p-value distributions versus K across deltas for Welch and MWU."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    deltas = sorted(df_summary["delta"].unique())
    # Exclude delta = 0 for power/delta sweep plot, or keep as reference
    pos_deltas = [d for d in deltas if d > 0]
    if not pos_deltas:
        pos_deltas = deltas

    fig, axes = plt.subplots(len(pos_deltas), 2, figsize=(12, 3.2 * len(pos_deltas)), sharex=True, sharey=True)
    if len(pos_deltas) == 1:
        axes = np.array([axes])

    k_order = [str(k) if k > 0 else "0 (user)" for k in sorted(df_summary["K"].unique())]

    for i, delta in enumerate(pos_deltas):
        sub = df_summary[df_summary["delta"] == delta].copy()
        sub["K_label"] = sub["K"].apply(lambda k: str(k) if k > 0 else "0 (user)")

        # Welch
        ax_w = axes[i, 0]
        welch_data = [sub[sub["K_label"] == kl]["welch_p"].values for kl in k_order]
        ax_w.boxplot(welch_data, labels=k_order, patch_artist=True, boxprops=dict(facecolor="#c6dbef", color="#2b5c8f"))
        # Add jittered points
        for pos_idx, vals in enumerate(welch_data, start=1):
            jitter = np.random.uniform(-0.1, 0.1, size=len(vals))
            ax_w.scatter(pos_idx + jitter, vals, color="#08519c", alpha=0.6, s=20, zorder=3)
        ax_w.axhline(0.05, color="red", linestyle="--", linewidth=1.2, label=r"$\alpha=0.05$")
        ax_w.set_title(f"Welch t-test (Uplift $\Delta={delta}$)", fontsize=10, fontweight="bold")
        ax_w.set_ylabel("p-value")
        ax_w.set_ylim(-0.05, 1.05)
        ax_w.grid(True, alpha=0.3)
        if i == 0:
            ax_w.legend(loc="upper right", fontsize=8)

        # MWU
        ax_m = axes[i, 1]
        mwu_data = [sub[sub["K_label"] == kl]["mwu_p"].values for kl in k_order]
        ax_m.boxplot(mwu_data, labels=k_order, patch_artist=True, boxprops=dict(facecolor="#fdd0a2", color="#d95f02"))
        for pos_idx, vals in enumerate(mwu_data, start=1):
            jitter = np.random.uniform(-0.1, 0.1, size=len(vals))
            ax_m.scatter(pos_idx + jitter, vals, color="#d94801", alpha=0.6, s=20, zorder=3)
        ax_m.axhline(0.05, color="red", linestyle="--", linewidth=1.2, label=r"$\alpha=0.05$")
        ax_m.set_title(f"Mann–Whitney U (Uplift $\Delta={delta}$)", fontsize=10, fontweight="bold")
        ax_m.set_ylabel("p-value")
        ax_m.set_ylim(-0.05, 1.05)
        ax_m.grid(True, alpha=0.3)
        if i == 0:
            ax_m.legend(loc="upper right", fontsize=8)

    for col in (0, 1):
        axes[-1, col].set_xlabel("Bucket Count K")

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_rejection_rates_vs_K(
    df_summary: pd.DataFrame,
    out_path: Path,
    alpha: float = 0.05,
) -> None:
    """Plot empirical rejection fraction versus K across deltas with Wilson intervals."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pos_deltas = sorted([d for d in df_summary["delta"].unique() if d > 0])
    if not pos_deltas:
        pos_deltas = sorted(df_summary["delta"].unique())

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    k_vals = sorted(df_summary["K"].unique())
    k_labels = [str(k) if k > 0 else "0 (user)" for k in k_vals]
    x_indices = np.arange(len(k_vals))

    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(pos_deltas)))

    for ax, test_name, col_name in zip(axes, ["Welch's t-test", "Mann–Whitney U"], ["welch_reject", "mwu_reject"]):
        for delta, color in zip(pos_deltas, colors):
            sub = df_summary[df_summary["delta"] == delta]
            rates = []
            lowers = []
            uppers = []
            for k in k_vals:
                k_sub = sub[sub["K"] == k]
                k_rej = int(k_sub[col_name].sum())
                n_rep = len(k_sub)
                rate = k_rej / n_rep if n_rep > 0 else 0.0
                low, high = wilson_interval(k_rej, n_rep)
                rates.append(rate)
                lowers.append(max(0.0, float(rate - low)))
                uppers.append(max(0.0, float(high - rate)))

            ax.errorbar(
                x_indices,
                rates,
                yerr=[lowers, uppers],
                marker="o",
                linewidth=2,
                capsize=4,
                label=f"$\Delta={delta:.3f}$",
                color=color,
            )

        ax.set_xticks(x_indices)
        ax.set_xticklabels(k_labels)
        ax.set_xlabel("Bucket Count K (0 = User-Level)", fontsize=11)
        ax.set_ylabel("Empirical Rejection Fraction", fontsize=11)
        ax.set_title(f"{test_name} — Rejection Rate vs. K", fontsize=12, fontweight="bold")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(title="Expected Uplift", fontsize=8.5, title_fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_null_calibration(
    df_null: pd.DataFrame,
    out_path: Path,
    alpha: float = 0.05,
) -> None:
    """Plot empirical Type I error rate vs K under fresh-split null repetitions."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    k_vals = sorted(df_null["K"].unique())
    k_labels = [str(k) if k > 0 else "0 (user)" for k in k_vals]
    x_indices = np.arange(len(k_vals))

    fig, ax = plt.subplots(figsize=(8, 5))

    for test_label, col_name, color, marker in [
        ("Welch's t-test", "welch_reject", "#2b5c8f", "o"),
        ("Mann–Whitney U", "mwu_reject", "#d95f02", "s"),
    ]:
        rates = []
        lowers = []
        uppers = []
        for k in k_vals:
            k_sub = df_null[df_null["K"] == k]
            k_rej = int(k_sub[col_name].sum())
            n_rep = len(k_sub)
            rate = k_rej / n_rep if n_rep > 0 else 0.0
            low, high = wilson_interval(k_rej, n_rep)
            rates.append(rate)
            lowers.append(max(0.0, float(rate - low)))
            uppers.append(max(0.0, float(high - rate)))

        ax.errorbar(
            x_indices,
            rates,
            yerr=[lowers, uppers],
            marker=marker,
            linewidth=2,
            capsize=4,
            label=test_label,
            color=color,
        )

    ax.axhline(alpha, color="black", linestyle="--", linewidth=1.2, label=f"Nominal $\\alpha={alpha}$")
    ax.set_xticks(x_indices)
    ax.set_xticklabels(k_labels)
    ax.set_xlabel("Bucket Count K (0 = User-Level)", fontsize=11)
    ax.set_ylabel("Empirical False Positive Rate (Type I Error)", fontsize=11)
    ax.set_title("Untreated Fresh-Split Null Calibration", fontsize=12, fontweight="bold")
    ax.set_ylim(-0.02, max(0.20, ax.get_ylim()[1]))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
