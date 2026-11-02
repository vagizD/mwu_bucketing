"""Simulation engine, MDE analysis, and visualization routines.

Fulfills Steps 4, 5, and 6 of pipeline:
- Single-run demonstration under alternative (Table 4, Figure 4, Figure 4b)
- Repeated experiments across delta grid (Table 5, Figure 5, Figure 6)
- MDE analysis and power curves (Table 6, Figure 7)
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter

from src.config import TreatmentConfig, BucketsConfig
from src.bucketing import partition_and_sum, run_welch_test, run_mwu_test
from src.treatment import generate_treatment


def run_single_run_demonstration(
    a_rev: np.ndarray,
    b_rev: np.ndarray,
    b_act: np.ndarray,
    observed_prices: np.ndarray,
    delta: float,
    bucket_counts: List[int],
    treatment_cfg: TreatmentConfig,
    out_dir: Path,
    seed: int = 42,
) -> Tuple[pd.DataFrame, Path, Path]:
    """Execute Step 4: Single-run demonstration under alternative (Table 4, Figure 4, Figure 4b)."""
    rng = np.random.default_rng(seed)
    n_users = len(a_rev)

    # 1. Generate synthetic treatment in B
    treated_b_rev, meta = generate_treatment(
        b_revenues=b_rev,
        b_activities=b_act,
        observed_prices=observed_prices,
        delta=delta,
        treatment_cfg=treatment_cfg,
        rng=rng,
    )

    levels = sorted(bucket_counts)
    user_k = max(levels)
    table_rows = []
    bucket_pairs = {}

    for k in levels:
        xA = partition_and_sum(a_rev, k, rng=rng)
        xB = partition_and_sum(treated_b_rev, k, rng=rng)
        bucket_pairs[k] = (xA, xB)

        lvl_name = f"{k} (User Level)" if k >= n_users else f"{k} Buckets"
        diff_mean = float(np.mean(xB) - np.mean(xA))

        # MWU across all levels (Primary Test)
        _, mwu_p = run_mwu_test(xA, xB)
        table_rows.append({
            "Aggregation Level": lvl_name,
            "K": k,
            "Test": "Mann-Whitney U",
            "p-value": mwu_p,
            "Mean Difference (B - A)": diff_mean,
        })

        # Welch ONLY on bucket levels (k < n_users)
        if k < n_users:
            _, welch_p = run_welch_test(xA, xB)
            table_rows.append({
                "Aggregation Level": lvl_name,
                "K": k,
                "Test": "Welch t-test",
                "p-value": welch_p,
                "Mean Difference (B - A)": diff_mean,
            })

    df_table_4 = pd.DataFrame(table_rows)

    # Generate Figure 4: Example treated distributions across key representative levels
    fig4_path = out_dir / "plots" / "figure4_treated_distributions.png"
    fig4_path.parent.mkdir(parents=True, exist_ok=True)

    candidate_levels = [50, 100, 500, 1000, user_k]
    plot_levels = [k for k in candidate_levels if k in bucket_pairs]
    if len(plot_levels) < 3:
        plot_levels = levels[:5]

    n_levels = len(plot_levels)
    fig, axes = plt.subplots(1, n_levels, figsize=(4.6 * n_levels, 4.0))
    if n_levels == 1:
        axes = [axes]

    for idx, k in enumerate(plot_levels):
        ax = axes[idx]
        xA, xB = bucket_pairs[k]
        lvl_name = "User Level (Raw)" if k == user_k else f"{k} Buckets"

        p99 = max(np.percentile(xA, 99), np.percentile(xB, 99))
        plot_max = max(p99 * 1.6, 0.02)

        ax.hist(xA, bins=35, range=(0, plot_max), alpha=0.55, color="#2b5c8f", label="Group A (Control)", density=True)
        ax.hist(xB, bins=35, range=(0, plot_max), alpha=0.55, color="#d95f02", label="Group B (Treated)", density=True)
        ax.set_title(f"{lvl_name}\n(Target Uplift = {delta:+.1%})", fontsize=10.5, fontweight="bold")
        ax.set_xlabel("Aggregated Revenue")
        ax.set_ylabel("Density")
        ax.grid(True, alpha=0.3)
        if idx == 0:
            ax.legend(loc="upper right", fontsize=8.5)

    plt.tight_layout()
    plt.savefig(fig4_path, dpi=160)
    plt.close()

    # Generate Figure 4b: Line plot of single-run p-values across ordered aggregation levels
    fig4b_path = out_dir / "plots" / "figure4b_single_run_pvalues.png"
    fig, ax = plt.subplots(figsize=(10.5, 4.8))

    x_labels = [f"{k}\n(User)" if k == user_k else str(k) for k in levels]
    x_indices = np.arange(len(levels))

    mwu_pvals = []
    welch_pvals = []
    for k in levels:
        row_m = df_table_4[(df_table_4["K"] == k) & (df_table_4["Test"] == "Mann-Whitney U")]
        mwu_pvals.append(row_m["p-value"].values[0] if len(row_m) > 0 else np.nan)

        row_w = df_table_4[(df_table_4["K"] == k) & (df_table_4["Test"] == "Welch t-test")]
        welch_pvals.append(row_w["p-value"].values[0] if len(row_w) > 0 else np.nan)

    ax.plot(x_indices, mwu_pvals, "o-", color="#d95f02", linewidth=2.4, markersize=7, label="Mann-Whitney U")
    valid_w_idx = [i for i, p in enumerate(welch_pvals) if not np.isnan(p)]
    ax.plot([x_indices[i] for i in valid_w_idx], [welch_pvals[i] for i in valid_w_idx], "s--", color="#2b5c8f", linewidth=2.2, markersize=6.5, label="Welch t-test")

    ax.axhline(0.05, color="red", linestyle="--", linewidth=1.5, label="alpha = 0.05 (Threshold: Significant below red line)")

    # Data value labels on points
    for idx, (xm, ym) in enumerate(zip(x_indices, mwu_pvals)):
        if not np.isnan(ym):
            lbl = f"{ym:.3f}" if ym >= 0.001 else f"{ym:.1e}"
            ax.annotate(lbl, (xm, ym), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8.5, fontweight="bold", color="#a63603")
    for idx in valid_w_idx:
        xw = x_indices[idx]
        yw = welch_pvals[idx]
        lbl = f"{yw:.3f}" if yw >= 0.001 else f"{yw:.1e}"
        ax.annotate(lbl, (xw, yw), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8.5, fontweight="bold", color="#08519c")

    ax.set_xticks(x_indices)
    ax.set_xticklabels(x_labels, fontsize=9.5)
    ax.set_xlabel("Number of Buckets Growing Monotonically", fontsize=11, fontweight="bold")
    ax.set_ylabel("Single-Run p-value", fontsize=11, fontweight="bold")
    ax.set_title(f"Figure 4b: Single-Run Test p-Values by Bucket Count (Target Uplift = {delta:+.1%})", fontsize=12, fontweight="bold")
    ax.set_ylim(-0.02, 1.08)
    ax.grid(True, alpha=0.3, linestyle=":")
    ax.legend(loc="upper left", fontsize=9.5)

    plt.tight_layout()
    plt.savefig(fig4b_path, dpi=160)
    plt.close()

    df_table_4_clean = df_table_4.drop(columns=["K"])
    return df_table_4_clean, fig4_path, fig4b_path


def run_alternative_simulations(
    a_rev: np.ndarray,
    b_rev: np.ndarray,
    b_act: np.ndarray,
    observed_prices: np.ndarray,
    uplifts: List[float],
    bucket_counts: List[int],
    treatment_cfg: TreatmentConfig,
    n_reps: int = 20,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute Step 5: Repeated experiments across delta grid (Table 5)."""
    master_rng = np.random.default_rng(seed)
    n_users = len(a_rev)
    levels = sorted(bucket_counts)
    records = []

    for delta in uplifts:
        for rep in range(n_reps):
            rep_seed = int(master_rng.integers(0, 10_000_000))
            rep_rng = np.random.default_rng(rep_seed)

            # Generate synthetic treatment in B
            treated_b_rev, meta = generate_treatment(
                b_revenues=b_rev,
                b_activities=b_act,
                observed_prices=observed_prices,
                delta=delta,
                treatment_cfg=treatment_cfg,
                rng=rep_rng,
            )

            for k in levels:
                xA = partition_and_sum(a_rev, k, rng=rep_rng)
                xB = partition_and_sum(treated_b_rev, k, rng=rep_rng)
                lvl_str = f"{k}_user" if k >= n_users else f"{k}_buckets"

                # MWU test across all levels (Primary Test)
                mwu_stat, mwu_p = run_mwu_test(xA, xB)
                records.append({
                    "delta": delta,
                    "repetition": rep,
                    "K": k,
                    "level_label": lvl_str,
                    "test": "Mann-Whitney U",
                    "p_value": mwu_p,
                    "rejected": bool(mwu_p < alpha),
                    "observed_uplift": meta["realized_uplift"],
                })

                # Welch test ONLY on bucketed data (k < n_users)
                if k < n_users:
                    welch_stat, welch_p = run_welch_test(xA, xB)
                    records.append({
                        "delta": delta,
                        "repetition": rep,
                        "K": k,
                        "level_label": lvl_str,
                        "test": "Welch t-test",
                        "p_value": welch_p,
                        "rejected": bool(welch_p < alpha),
                        "observed_uplift": meta["realized_uplift"],
                    })

    df_alt = pd.DataFrame(records)

    # Compute Table 5: Rejection rate (empirical power) summary
    summary_rows = []
    grouped = df_alt.groupby(["delta", "K", "level_label", "test"])
    for (d, k, lvl, tst), grp in grouped:
        disp_name = f"{k} (User Level)" if k >= n_users else f"{k} Buckets"
        summary_rows.append({
            "Target Uplift (delta)": d,
            "K": k,
            "Aggregation Level": disp_name,
            "Test": tst,
            "Repetitions": len(grp),
            "Empirical Power": float(grp["rejected"].mean()),
            "Mean p-value": float(grp["p_value"].mean()),
            "Median p-value": float(grp["p_value"].median()),
            "Mean Realized Uplift": float(grp["observed_uplift"].mean()),
        })

    df_table_5 = pd.DataFrame(summary_rows).sort_values(by=["Target Uplift (delta)", "K", "Test"]).reset_index(drop=True)
    return df_table_5, df_alt


def plot_figure_5_rejection_vs_delta(df_alt: pd.DataFrame, out_path: Path) -> None:
    """Generate Figure 5: Bucket Count (K) vs Empirical Rejection Rate (Power) per delta."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    deltas = sorted(df_alt["delta"].unique())
    levels_all = sorted(df_alt["K"].unique())
    user_k = max(levels_all)
    levels_welch = [k for k in levels_all if k < user_k]

    fig, (ax_mwu, ax_welch) = plt.subplots(1, 2, figsize=(14, 5.2), sharey=True)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(deltas)))

    for d, color in zip(deltas, colors):
        # MWU across all K (including User Level)
        sub_m = df_alt[(df_alt["delta"] == d) & (df_alt["test"] == "Mann-Whitney U")]
        rates_m = sub_m.groupby("K")["rejected"].mean().reindex(levels_all, fill_value=0.0)
        ax_mwu.plot(levels_all, rates_m.values, "o-", color=color, linewidth=2, markersize=5.5, label=f"{d:+.1%}")

        # Welch across K < User Level
        sub_w = df_alt[(df_alt["delta"] == d) & (df_alt["test"] == "Welch t-test")]
        rates_w = sub_w.groupby("K")["rejected"].mean().reindex(levels_welch, fill_value=0.0)
        ax_welch.plot(levels_welch, rates_w.values, "s-", color=color, linewidth=2, markersize=5.5, label=f"{d:+.1%}")

    ax_mwu.axhline(0.80, color="red", linestyle="--", linewidth=1.4, label="80% Target Power")
    ax_welch.axhline(0.80, color="red", linestyle="--", linewidth=1.4, label="80% Target Power")

    ax_mwu.set_xscale("log")
    ax_welch.set_xscale("log")

    ax_mwu.set_title("Mann-Whitney U: Power vs. Aggregation Level", fontsize=11.5, fontweight="bold")
    ax_mwu.set_xlabel("Number of Buckets (log scale, max = User Level)", fontsize=10.5)
    ax_mwu.set_ylabel("Empirical Rejection Rate (Power under H1)", fontsize=10.5)
    ax_mwu.set_ylim(-0.02, 1.05)
    ax_mwu.grid(True, alpha=0.3, which="both")
    ax_mwu.legend(loc="upper right", fontsize=8.5, title="Uplift")

    ax_welch.set_title("Welch's t-test: Power vs. Aggregation Level", fontsize=11.5, fontweight="bold")
    ax_welch.set_xlabel("Number of Buckets (log scale, Buckets only)", fontsize=10.5)
    ax_welch.grid(True, alpha=0.3, which="both")
    ax_welch.legend(loc="upper right", fontsize=8.5, title="Uplift")

    plt.suptitle("Figure 5: Empirical Power vs. Number of Buckets Across Target Uplifts", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_figure_6_pvalues_vs_delta(df_alt: pd.DataFrame, out_path: Path) -> None:
    """Generate Figure 6: Bucket Count vs Median p-value per delta."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    deltas = sorted(df_alt["delta"].unique())
    levels_all = sorted(df_alt["K"].unique())
    user_k = max(levels_all)
    levels_welch = [k for k in levels_all if k < user_k]

    fig, (ax_mwu, ax_welch) = plt.subplots(1, 2, figsize=(14, 5.2), sharey=True)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(deltas)))

    for d, color in zip(deltas, colors):
        # MWU across all K (including User Level)
        sub_m = df_alt[(df_alt["delta"] == d) & (df_alt["test"] == "Mann-Whitney U")]
        med_p_m = sub_m.groupby("K")["p_value"].median().reindex(levels_all, fill_value=1.0)
        p_vals_m = np.clip(med_p_m.values, 1e-12, 1.0)
        ax_mwu.plot(levels_all, p_vals_m, "o-", color=color, linewidth=2, markersize=5.5, label=f"{d:+.1%}")

        # Welch across K < User Level
        sub_w = df_alt[(df_alt["delta"] == d) & (df_alt["test"] == "Welch t-test")]
        med_p_w = sub_w.groupby("K")["p_value"].median().reindex(levels_welch, fill_value=1.0)
        p_vals_w = np.clip(med_p_w.values, 1e-12, 1.0)
        ax_welch.plot(levels_welch, p_vals_w, "s-", color=color, linewidth=2, markersize=5.5, label=f"{d:+.1%}")

    ax_mwu.axhline(0.05, color="red", linestyle="--", linewidth=1.4, label="alpha = 0.05 (Threshold)")
    ax_welch.axhline(0.05, color="red", linestyle="--", linewidth=1.4, label="alpha = 0.05 (Threshold)")

    ax_mwu.set_xscale("log")
    ax_welch.set_xscale("log")
    ax_mwu.set_yscale("log")
    ax_welch.set_yscale("log")

    ax_mwu.set_title("Mann-Whitney U: Median p-value vs. Aggregation Level", fontsize=11.5, fontweight="bold")
    ax_mwu.set_xlabel("Number of Buckets (log scale, max = User Level)", fontsize=10.5)
    ax_mwu.set_ylabel("Median p-value (log scale)", fontsize=10.5)
    ax_mwu.grid(True, alpha=0.3, which="both")
    ax_mwu.legend(loc="lower right", fontsize=8.5, title="Uplift")

    ax_welch.set_title("Welch's t-test: Median p-value vs. Aggregation Level", fontsize=11.5, fontweight="bold")
    ax_welch.set_xlabel("Number of Buckets (log scale, Buckets only)", fontsize=10.5)
    ax_welch.grid(True, alpha=0.3, which="both")
    ax_welch.legend(loc="lower right", fontsize=8.5, title="Uplift")

    plt.suptitle("Figure 6: Median Test p-value vs. Number of Buckets Across Target Uplifts", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close()


def _interpolate_mde(pow_series: pd.Series, target: float = 0.80) -> str:
    """Compute interpolated Minimum Detectable Effect (MDE) where empirical power crosses target."""
    deltas = pow_series.index.values
    powers = pow_series.values
    if np.all(powers < target):
        return f"> {deltas[-1]:.1%}"
    if powers[0] >= target:
        return f"<= {deltas[0]:.1%}"
    idx = np.where(powers >= target)[0][0]
    d0, d1 = deltas[idx - 1], deltas[idx]
    p0, p1 = powers[idx - 1], powers[idx]
    if p1 == p0:
        val = d1
    else:
        val = d0 + (target - p0) / (p1 - p0) * (d1 - d0)
    return f"{val:.2%}"


def compute_table_6_mde_and_figure_7(
    df_alt: pd.DataFrame,
    target_power: float,
    bucket_counts: List[int],
    out_dir: Path,
) -> Tuple[pd.DataFrame, Path]:
    """Execute Step 6: Estimate MDE across all bucket counts and generate Figure 7."""
    rows = []
    levels = sorted(bucket_counts)
    user_k = max(levels)

    for k in levels:
        # MWU MDE (Primary Test)
        sub_m = df_alt[(df_alt["K"] == k) & (df_alt["test"] == "Mann-Whitney U")]
        pow_by_delta_m = sub_m.groupby("delta")["rejected"].mean().sort_index()
        mde_m = _interpolate_mde(pow_by_delta_m, target_power)

        lvl_name = f"{k} (User Level)" if k >= user_k else f"{k} Buckets"
        mwu_suit = "Severe zero ties degrade rank tests" if k >= user_k else "Continuous bucket sums eliminate zero rank-ties"

        rows.append({
            "Aggregation Level": lvl_name,
            "K": k,
            "Test": "Mann-Whitney U (Main)",
            "Target Power": target_power,
            "Estimated MDE": mde_m,
            "Distribution Suitability": mwu_suit,
        })

        # Welch MDE (only for K < user_k)
        if k < user_k:
            sub_w = df_alt[(df_alt["K"] == k) & (df_alt["test"] == "Welch t-test")]
            pow_by_delta_w = sub_w.groupby("delta")["rejected"].mean().sort_index()
            mde_w = _interpolate_mde(pow_by_delta_w, target_power)

            sk_note = "Normal (CLT bell-shaped, p > 0.05)" if k <= 300 else "Non-normal (skewness persists, p < 0.05)"

            rows.append({
                "Aggregation Level": lvl_name,
                "K": k,
                "Test": "Welch t-test",
                "Target Power": target_power,
                "Estimated MDE": mde_w,
                "Distribution Suitability": sk_note,
            })

    df_table_6 = pd.DataFrame(rows)

    # Figure 7: Power curves across target uplifts for key bucket counts
    fig_path = out_dir / "plots" / "figure7_welch_power_curves.png"
    fig_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    highlight_k = [k for k in [10, 50, 100, 500, 1000, 5000, 10000, user_k] if k in levels]
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(highlight_k)))
    deltas = sorted(df_alt["delta"].unique())

    for idx, (k, color) in enumerate(zip(highlight_k, colors)):
        sub = df_alt[(df_alt["K"] == k) & (df_alt["test"] == "Mann-Whitney U")]
        powers = sub.groupby("delta")["rejected"].mean().reindex(deltas, fill_value=0.0).values
        label_txt = f"MWU (User Level, K={k})" if k == user_k else f"MWU (K={k})"
        ax.plot(deltas, powers, "o-", color=color, linewidth=2.2, markersize=6, label=label_txt)

    ax.axhline(target_power, color="red", linestyle="--", linewidth=1.5, label=f"Target Power ({int(target_power*100)}%)")
    ax.set_xscale("log")

    # Set explicit ticks at all tested deltas with clear percentage labels
    ax.xaxis.set_major_locator(FixedLocator(deltas))
    tick_labels = [f"{d*100:.1f}%" if (d*100) % 1 != 0 else f"{int(d*100)}%" for d in deltas]
    ax.xaxis.set_major_formatter(FixedFormatter(tick_labels))
    ax.minorticks_off()

    ax.set_xlabel("Target Relative Revenue Uplift (delta, log scale)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Empirical Power (Rejection Rate under H1)", fontsize=11, fontweight="bold")
    ax.set_title("Figure 7: Empirical Power Curves for Mann-Whitney U Across K", fontsize=12, fontweight="bold")
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, alpha=0.4, which="major", linestyle=":")
    ax.legend(loc="lower right", fontsize=9.5)

    plt.tight_layout()
    plt.savefig(fig_path, dpi=160)
    plt.close()

    return df_table_6, fig_path
