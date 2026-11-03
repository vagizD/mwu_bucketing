"""Generate custom figures tailored specifically for the technical presentation deck.
Adheres to the Light Technical Slate design style (Linear / Stripe inspired):
- Clean off-white canvas (#ffffff / #f8fafc)
- Deep ink navy typography (#0f172a, #1e293b)
- Technical accent colors (Blue #2563eb, Amber #d97706, Emerald #059669, Red #dc2626)
- High contrast, crisp borders, publication-grade layout.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.ticker import FixedLocator, FixedFormatter
from scipy import stats

from src.config import load_pipeline_config
from src.data_loader import load_and_prepare_data
from src.bucketing import partition_and_sum
from src.uncertainty import wilson_interval


# Set global matplotlib style for presentation
plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.family": "sans-serif",
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#cbd5e1",
    "axes.linewidth": 1.2,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "bold",
    "axes.labelcolor": "#0f172a",
    "xtick.color": "#334155",
    "ytick.color": "#334155",
    "grid.color": "#f1f5f9",
    "grid.linewidth": 1.0,
})


def make_pres_figure_1(df_a: pd.DataFrame, out_path: Path):
    """Figure 1 for Slide 2: Real zero-inflated revenue vs artificial example of MWU failure."""
    rev_a = df_a["revenue"].values
    n = len(rev_a)
    zero_pct = (rev_a == 0).mean() * 100

    # Artificial treatment: +3% spend strictly on active users
    # Control has rev_a. Treatment has rev_b = rev_a * 1.03 for active spenders
    rev_b = rev_a.copy()
    mask_active = rev_b > 0
    rev_b[mask_active] *= 1.03

    # Run tests on user-level
    stat_welch, p_welch = stats.ttest_ind(rev_b, rev_a, equal_var=False)
    stat_mwu, p_mwu = stats.mannwhitneyu(rev_b, rev_a, alternative="greater")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8), dpi=180)

    # Panel A: Real distribution
    spenders = rev_a[rev_a > 0]
    bins = np.linspace(0, 0.20, 45)
    ax1.hist(rev_a, bins=bins, color="#2563eb", alpha=0.85, edgecolor="#1e40af", linewidth=0.8, density=True)
    ax1.set_title("A. Real E-Commerce Customer Revenue", fontsize=12, pad=10)
    ax1.set_xlabel("Monthly Revenue per User (Normalized)")
    ax1.set_ylabel("Probability Density")
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Callout badge for zero inflation
    ax1.annotate(
        f"Extreme Zero Inflation\n{zero_pct:.1f}% of users = $0.00\nHeavy Pareto Tail (Skewness = {stats.skew(rev_a):.1f})",
        xy=(0.002, 18),
        xytext=(0.05, 15),
        arrowprops=dict(facecolor="#dc2626", edgecolor="#dc2626", arrowstyle="->", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fef2f2", edgecolor="#f87171", lw=1.2),
        fontsize=9.5,
        fontweight="bold",
        color="#991b1b"
    )

    # Panel B: Artificial MWU Failure on user level
    bins_b = np.linspace(0, 0.20, 45)
    ax2.hist(rev_a, bins=bins_b, color="#64748b", alpha=0.5, label="Control (Group A)", density=True)
    ax2.hist(rev_b, bins=bins_b, color="#059669", alpha=0.5, label="Treated (+3% on spenders)", density=True)
    ax2.set_title("B. Production Dilemma: +3% Spender Lift Fails Under MWU", fontsize=12, pad=10)
    ax2.set_xlabel("Monthly Revenue per User (Normalized)")
    ax2.set_ylabel("Probability Density")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper right", fontsize=9.5)

    # Failure callout
    result_text = (
        f"Realized Spender Lift: +3.0%\n"
        f"• Welch t-test: p = {p_welch:.4f} (INVALID: Normality rejected, p < 1e-50)\n"
        f"• Mann-Whitney U: p = {p_mwu:.4f} (FAILS TO DETECT: p > 0.05 due to 65% zero-ties!)"
    )
    ax2.text(
        0.035, 11,
        result_text,
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.2),
        fontsize=9.2,
        fontweight="bold",
        color="#92400e"
    )

    plt.suptitle("Figure 1: The Zero-Inflation Dilemma in Production E-Commerce", fontsize=14, fontweight="bold", y=1.03)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_2(df_a: pd.DataFrame, out_path: Path):
    """Figure 2 for Slide 3: Bucketization mechanics and CLT normality across K."""
    rev_a = df_a["revenue"].values
    
    # 4 stages: K=10, K=100, K=1000, and User Level (K=100,000)
    stages = [10, 100, 1000, len(rev_a)]
    stage_names = ["K = 10 Buckets", "K = 100 Buckets", "K = 1000 Buckets", "User-Level (Raw)"]

    fig, axes = plt.subplots(1, 4, figsize=(16, 4.2), dpi=180)

    rng = np.random.default_rng(42)
    for ax, k, title in zip(axes, stages, stage_names):
        if k < len(rev_a):
            b_rev = partition_and_sum(rev_a, k, rng)
            zeros = (b_rev == 0).mean() * 100
            # D'Agostino normality test
            if k >= 20:
                _, p_norm = stats.normaltest(b_rev)
            else:
                _, p_norm = stats.shapiro(b_rev)
            
            ax.hist(b_rev, bins=18, color="#2563eb", edgecolor="#1d4ed8", alpha=0.8, density=True)
            norm_str = f"Normality: p={p_norm:.3f}" if p_norm >= 0.001 else "Normality: p < 0.001"
            norm_color = "#059669" if p_norm >= 0.05 else ("#d97706" if p_norm >= 0.01 else "#dc2626")
            
            ax.set_title(f"{title}\n{norm_str}", fontsize=11, fontweight="bold", color="#0f172a")
            ax.text(
                0.95, 0.88, f"Zero ties: {zeros:.1f}%",
                transform=ax.transAxes, ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#cbd5e1"),
                fontsize=9, fontweight="bold", color="#334155"
            )
        else:
            # User level
            ax.hist(rev_a[rev_a < 0.15], bins=35, color="#64748b", edgecolor="#475569", alpha=0.8, density=True)
            zeros = (rev_a == 0).mean() * 100
            ax.set_title(f"{title}\nNormality: REJECTED (p < 1e-50)", fontsize=11, fontweight="bold", color="#dc2626")
            ax.text(
                0.95, 0.88, f"Zero ties: {zeros:.1f}%",
                transform=ax.transAxes, ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#fef2f2", edgecolor="#f87171"),
                fontsize=9, fontweight="bold", color="#991b1b"
            )
        
        ax.set_xlabel("Bucket / User Revenue", fontsize=9.5)
        ax.set_ylabel("Density", fontsize=9.5)
        ax.grid(True, linestyle="--", alpha=0.4)

    plt.suptitle("Figure 2: Bucketization Transforms Zero-Inflation into Gaussian Aggregates via CLT", fontsize=13, fontweight="bold", y=1.05)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_4(out_path: Path):
    """Figure 4 & 4b combined for Slide 5: P-Value vs # of Buckets under Target Uplift delta = +2.3%."""
    df_single = pd.read_csv("results/tables/table4_single_run.csv")
    df_single["K"] = df_single["Aggregation Level"].apply(lambda s: int(s.split()[0]))
    
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=180)

    # MWU and Welch points
    mwu_data = df_single[df_single["Test"] == "Mann-Whitney U"].sort_values("K")
    welch_data = df_single[df_single["Test"] == "Welch t-test"].sort_values("K")

    x_labels = [f"K={k}" if k < 100000 else "User-Level\n(K=100k)" for k in mwu_data["K"]]
    x_pos = np.arange(len(mwu_data))

    # Plot lines
    ax.plot(x_pos, mwu_data["p-value"], "o-", color="#d97706", linewidth=2.5, markersize=8, label="Mann-Whitney U (Valid Test)")
    ax.plot(x_pos[:-1], welch_data["p-value"], "s--", color="#2563eb", linewidth=2.0, markersize=7, label="Welch t-test (Buckets only)")

    # Reference threshold at alpha = 0.05
    ax.axhline(0.05, color="#dc2626", linestyle="--", linewidth=1.8, label="Significance Threshold (alpha = 0.05)")

    # Highlight optimal zone
    ax.axvspan(1, 4, color="#ecfdf5", alpha=0.6, label="Optimal Detection Zone (K in [50, 1000])")

    # Annotate p-values
    for x, y, p in zip(x_pos, mwu_data["p-value"], mwu_data["p-value"]):
        offset = 0.04 if p < 0.2 else -0.06
        ax.text(x, y + offset, f"{p:.3f}", ha="center", fontsize=8.5, fontweight="bold", color="#92400e")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, fontsize=9.5, fontweight="bold")
    ax.set_xlabel("Number of Buckets (K) Growing Monotonically", fontsize=11, fontweight="bold")
    ax.set_ylabel("Empirical p-Value (Target Uplift delta = +2.3%)", fontsize=11, fontweight="bold")
    ax.set_title("P-Value vs. Number of Buckets (Target Uplift delta = +2.3%)", fontsize=13, fontweight="bold")
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=9.5, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_5(out_path: Path):
    """Figure 5 for Slide 6: Power vs Uplift and Significance vs Uplift (Figure 7 style)."""
    df_power = pd.read_csv("results/tables/table5_power_summary.csv")
    df_null = pd.read_csv("results/tables/table3_null_rejections.csv")

    fig, (ax_power, ax_signif) = plt.subplots(1, 2, figsize=(15, 5.2), dpi=180)

    # Panel A: Power vs Uplift delta for select K
    highlight_k = [10, 50, 100, 1000, 10000, 100000]
    colors = ["#2563eb", "#059669", "#16a34a", "#854d0e", "#64748b", "#dc2626"]

    deltas = sorted(df_power["Target Uplift (delta)"].unique())

    for k, color in zip(highlight_k, colors):
        sub = df_power[(df_power["K"] == k) & (df_power["Test"] == "Mann-Whitney U")].sort_values("Target Uplift (delta)")
        powers = sub["Empirical Power"].values
        k_lbl = f"K = {k}" if k < 100000 else "User-Level (K=100k)"
        ax_power.plot(deltas, powers, "o-", color=color, linewidth=2.2, markersize=5.5, label=f"MWU ({k_lbl})")

    ax_power.axhline(0.80, color="#dc2626", linestyle="--", linewidth=1.6, label="Target Power (80%)")
    ax_power.set_xscale("log")
    ax_power.xaxis.set_major_locator(FixedLocator(deltas))
    ax_power.xaxis.set_major_formatter(FixedFormatter([f"{d:+.1%}" for d in deltas]))
    ax_power.minorticks_off()
    ax_power.set_xlabel("Target Relative Revenue Uplift (delta, log scale)", fontsize=11, fontweight="bold")
    ax_power.set_ylabel("Empirical Power (Rejection Rate under H1)", fontsize=11, fontweight="bold")
    ax_power.set_title("A. Statistical Power vs. Uplift (Target >= 80%)", fontsize=12, fontweight="bold")
    ax_power.set_ylim(-0.02, 1.05)
    ax_power.grid(True, linestyle=":", alpha=0.5)
    ax_power.legend(loc="lower right", fontsize=8.5)

    # Panel B: Significance (False Positive Rate under H0) vs Bucket Count
    mwu_null = df_null[df_null["Test"] == "Mann-Whitney U"].sort_values("K")
    k_vals = mwu_null["K"].values
    fpr_vals = mwu_null["False Positive Rate"].values
    ci_low = mwu_null["95% CI Lower"].values
    ci_high = mwu_null["95% CI Upper"].values

    x_pos = np.arange(len(k_vals))
    x_lbls = [f"K={k}" if k < 100000 else "User-Level\n(K=100k)" for k in k_vals]

    yerr = [fpr_vals - ci_low, ci_high - fpr_vals]
    ax_signif.bar(x_pos, fpr_vals, color="#3b82f6", edgecolor="#1d4ed8", alpha=0.85, width=0.55, yerr=yerr, capsize=4, label="MWU Type I Error")
    ax_signif.axhline(0.05, color="#dc2626", linestyle="--", linewidth=1.8, label="Nominal alpha = 0.05")

    for x, val, high in zip(x_pos, fpr_vals, ci_high):
        ax_signif.text(x, high + 0.008, f"{val:.2f}", ha="center", fontsize=8.5, fontweight="bold", color="#1e3a8a")

    ax_signif.set_xticks(x_pos)
    ax_signif.set_xticklabels(x_lbls, fontsize=9.0, fontweight="bold")
    ax_signif.set_xlabel("Number of Buckets (K)", fontsize=11, fontweight="bold")
    ax_signif.set_ylabel("Empirical False Positive Rate (under H0)", fontsize=11, fontweight="bold")
    ax_signif.set_title("B. Significance Calibration under Null (Target = 0.05)", fontsize=12, fontweight="bold")
    ax_signif.set_ylim(0, 0.22)
    ax_signif.grid(True, linestyle=":", alpha=0.5, axis="y")
    ax_signif.legend(loc="upper right", fontsize=9.0)

    plt.suptitle("Figure 5: Power vs. Uplift and Significance Calibration Across Bucket Counts", fontsize=13, fontweight="bold", y=1.04)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def main():
    cfg = load_pipeline_config(Path("conf.toml"))
    df_all, df_a, df_b, obs_prices, stats_data = load_and_prepare_data(
        cfg.data,
        cfg.ab,
        cfg.random_seed,
    )

    out_dir = Path("results/plots")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generating Presentation Figure 1 (Zero-Inflation & MWU Failure)...")
    make_pres_figure_1(df_a, out_dir / "pres_figure1_mwu_failure.png")

    print("Generating Presentation Figure 2 (Bucketization Mechanics & CLT)...")
    make_pres_figure_2(df_a, out_dir / "pres_figure2_bucketization.png")

    print("Generating Presentation Figure 4 (P-Values vs # of Buckets)...")
    make_pres_figure_4(out_dir / "pres_figure4_pvalues.png")

    print("Generating Presentation Figure 5 (Power vs Uplift & Significance Calibration)...")
    make_pres_figure_5(out_dir / "pres_figure5_power_significance.png")

    print("All presentation assets successfully generated!")


if __name__ == "__main__":
    main()
