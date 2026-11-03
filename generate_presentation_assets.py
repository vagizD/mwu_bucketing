"""Generate custom figures tailored specifically for the technical presentation deck.
Sober engineering style:
- No buzzwords or fancy corporate phrasing.
- Short, direct, clear labels.
- Conservative publication-grade layout.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter
from scipy import stats

from src.config import load_pipeline_config
from src.data_loader import load_and_prepare_data
from src.bucketing import partition_and_sum
from src.uncertainty import wilson_interval


# Conservative engineer plot styling
plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.family": "sans-serif",
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#94a3b8",
    "axes.linewidth": 1.2,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "bold",
    "axes.labelcolor": "#0f172a",
    "xtick.color": "#1e293b",
    "ytick.color": "#1e293b",
    "grid.color": "#e2e8f0",
    "grid.linewidth": 0.8,
})


def make_pres_figure_1a(df_a: pd.DataFrame, out_path: Path):
    """Figure 1a for Slide 2: Real customer revenue distribution."""
    rev_a = df_a["revenue"].values
    zero_pct = (rev_a == 0).mean() * 100

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=180)
    bins = np.linspace(0, 0.20, 45)
    ax.hist(rev_a, bins=bins, color="#2563eb", edgecolor="#1d4ed8", linewidth=0.8, density=True)
    ax.set_title("Customer Revenue Distribution", fontsize=13, pad=10)
    ax.set_xlabel("Revenue", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.5)

    ax.annotate(
        f"{zero_pct:.1f}% of users have zero revenue",
        xy=(0.002, 20),
        xytext=(0.04, 30),
        arrowprops=dict(facecolor="#dc2626", edgecolor="#dc2626", arrowstyle="->", lw=1.5),
        bbox=dict(boxstyle="square,pad=0.5", facecolor="#ffffff", edgecolor="#dc2626", lw=1.2),
        fontsize=10,
        fontweight="bold",
        color="#dc2626"
    )

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_1b(df_a: pd.DataFrame, out_path: Path):
    """Figure 1b for Slide 2b: +3% lift on spenders (Control vs Treatment)."""
    rev_a = df_a["revenue"].values
    rev_b = rev_a.copy()
    rev_b[rev_b > 0] *= 1.03

    stat_welch, p_welch = stats.ttest_ind(rev_b, rev_a, equal_var=False)
    stat_mwu, p_mwu = stats.mannwhitneyu(rev_b, rev_a, alternative="greater")

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=180)
    bins = np.linspace(0, 0.20, 45)
    ax.hist(rev_a, bins=bins, color="#64748b", alpha=0.5, label="Control", density=True)
    ax.hist(rev_b, bins=bins, color="#059669", alpha=0.5, label="Treatment (+3% on spenders)", density=True)
    ax.set_title("Customer Revenue: Control vs. Treatment", fontsize=13, pad=10)
    ax.set_xlabel("Revenue", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", fontsize=10)

    summary = (
        f"Welch t-test: p = {p_welch:.4f} (Rejected: data non-normal)\n"
        f"Mann-Whitney U: p = {p_mwu:.4f} (Holds: fails to reject null)"
    )
    ax.text(
        0.035, 25,
        summary,
        bbox=dict(boxstyle="square,pad=0.6", facecolor="#ffffff", edgecolor="#0f172a", lw=1.2),
        fontsize=9.5,
        fontweight="bold",
        color="#0f172a"
    )

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_2(df_a: pd.DataFrame, out_path: Path):
    """Figure 2 for Slide 3: Bucketization mechanics and CLT across K."""
    rev_a = df_a["revenue"].values
    stages = [10, 100, 1000, len(rev_a)]
    stage_titles = [
        "K = 10: Normal",
        "K = 100: Normal",
        "K = 1000: Non-normal",
        "User-Level: Non-normal"
    ]

    fig, axes = plt.subplots(1, 4, figsize=(15, 3.8), dpi=180)
    rng = np.random.default_rng(42)

    for ax, k, title in zip(axes, stages, stage_titles):
        if k < len(rev_a):
            b_rev = partition_and_sum(rev_a, k, rng)
            ax.hist(b_rev, bins=16, color="#2563eb", edgecolor="#1d4ed8", alpha=0.8, density=True)
        else:
            ax.hist(rev_a[rev_a < 0.15], bins=35, color="#64748b", edgecolor="#475569", alpha=0.8, density=True)

        is_normal = "Non-normal" not in title
        title_color = "#059669" if is_normal else "#dc2626"
        ax.set_title(title, fontsize=11, fontweight="bold", color=title_color)
        ax.set_xlabel("Revenue", fontsize=9.5)
        ax.set_ylabel("Density", fontsize=9.5)
        ax.grid(True, linestyle="--", alpha=0.4)

    plt.suptitle("Revenue Distribution by Number of Buckets (K)", fontsize=13, fontweight="bold", y=1.04)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_4(out_path: Path):
    """Figure 4 for Slide 7: Significance (False Positive Rate) vs # of Buckets (A/A Null, Uplift = 0%)."""
    df_null = pd.read_csv("results/tables/table3_null_rejections.csv")

    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=180)

    mwu_null = df_null[df_null["Test"] == "Mann-Whitney U"].sort_values("K")
    k_vals = mwu_null["K"].values
    fpr_vals = mwu_null["False Positive Rate"].values
    ci_low = mwu_null["95% CI Lower"].values
    ci_high = mwu_null["95% CI Upper"].values

    x_pos = np.arange(len(k_vals))
    x_lbls = [f"{k}" if k < 100000 else "User-Level" for k in k_vals]

    yerr = [fpr_vals - ci_low, ci_high - fpr_vals]
    ax.bar(x_pos, fpr_vals, color="#3b82f6", edgecolor="#1d4ed8", alpha=0.85, width=0.52, yerr=yerr, capsize=4, label="Mann-Whitney U False Positive Rate")
    ax.axhline(0.05, color="#dc2626", linestyle="--", linewidth=1.6, label="Significance alpha = 0.05")

    for x, val, high in zip(x_pos, fpr_vals, ci_high):
        ax.text(x, high + 0.007, f"{val:.2f}", ha="center", fontsize=8.8, fontweight="bold", color="#1e3a8a")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_lbls, fontsize=9.5)
    ax.set_xlabel("Number of Buckets", fontsize=11, fontweight="bold")
    ax.set_ylabel("False Positive Rate", fontsize=11, fontweight="bold")
    ax.set_title("Significance vs # of Buckets (A/A Null, N=50 reps)", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 0.22)
    ax.grid(True, linestyle=":", alpha=0.5, axis="y")
    ax.legend(loc="upper right", fontsize=9.2)

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_5a(out_path: Path):
    """Figure 5a for Slide 8: P-value vs # of Buckets (B has +2.3% Lift)."""
    df_single = pd.read_csv("results/tables/table4_single_run.csv")
    df_single["K"] = df_single["Aggregation Level"].apply(lambda s: int(s.split()[0]))

    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=180)

    mwu_data = df_single[df_single["Test"] == "Mann-Whitney U"].sort_values("K")
    welch_data = df_single[df_single["Test"] == "Welch t-test"].sort_values("K")

    x_labels = [f"{k}" if k < 100000 else "User-Level" for k in mwu_data["K"]]
    x_pos = np.arange(len(mwu_data))

    ax.plot(x_pos, mwu_data["p-value"], "o-", color="#d97706", linewidth=2.2, markersize=7, label="Mann-Whitney U")
    ax.plot(x_pos[:-1], welch_data["p-value"], "s--", color="#2563eb", linewidth=1.8, markersize=6, label="Welch t-test")

    ax.axhline(0.05, color="#dc2626", linestyle="--", linewidth=1.6, label="Significance alpha = 0.05")

    for x, p in zip(x_pos, mwu_data["p-value"]):
        offset = 0.045 if p < 0.2 else -0.065
        ax.text(x, p + offset, f"{p:.3f}", ha="center", fontsize=8.8, fontweight="bold", color="#92400e")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, fontsize=9.5)
    ax.set_xlabel("Number of Buckets", fontsize=11, fontweight="bold")
    ax.set_ylabel("P-value", fontsize=11, fontweight="bold")
    ax.set_title("P-value vs # of Buckets (B has +2.3% Lift)", fontsize=13, fontweight="bold")
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=9.5)

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def make_pres_figure_5b(out_path: Path):
    """Figure 5b for Slide 9: Statistical Power vs Uplift (with Wilson CIs and vertical 2.3% line)."""
    df_power = pd.read_csv("results/tables/table5_power_summary.csv")

    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=180)

    highlight_k = [10, 50, 100, 1000, 10000, 100000]
    colors = ["#2563eb", "#059669", "#16a34a", "#854d0e", "#64748b", "#dc2626"]
    deltas = sorted(df_power["Target Uplift (delta)"].unique())

    for k, color in zip(highlight_k, colors):
        sub = df_power[(df_power["K"] == k) & (df_power["Test"] == "Mann-Whitney U")].sort_values("Target Uplift (delta)")
        powers = sub["Empirical Power"].values
        ci_l = sub["95% CI Lower"].values
        ci_u = sub["95% CI Upper"].values
        k_lbl = f"K = {k}" if k < 100000 else "User-Level"
        
        ax.plot(deltas, powers, "o-", color=color, linewidth=2.0, markersize=5.5, label=f"MWU ({k_lbl})")
        ax.fill_between(deltas, ci_l, ci_u, color=color, alpha=0.08, linewidth=0)

    # Reference lines
    ax.axhline(0.80, color="#dc2626", linestyle="--", linewidth=1.5, label="Power 80%")
    ax.axvline(0.023, color="#0f172a", linestyle=":", linewidth=1.8, label="delta = 2.3%")

    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator(deltas))
    ax.xaxis.set_major_formatter(FixedFormatter([f"{d*100:.1f}%" for d in deltas]))
    ax.minorticks_off()
    ax.tick_params(axis='x', rotation=30)
    ax.set_xlabel("Uplift", fontsize=11, fontweight="bold")
    ax.set_ylabel("Power", fontsize=11, fontweight="bold")
    ax.set_title("Statistical Power vs. Uplift (B has Lift)", fontsize=13, fontweight="bold")
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower right", fontsize=8.5)

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

    print("Generating Figure 1a (Customer Revenue Distribution)...")
    make_pres_figure_1a(df_a, out_dir / "pres_figure1a_user_revenue.png")

    print("Generating Figure 1b (Control vs Treatment Lift)...")
    make_pres_figure_1b(df_a, out_dir / "pres_figure1b_mwu_failure.png")

    print("Generating Figure 2 (Revenue Distribution by Number of Buckets)...")
    make_pres_figure_2(df_a, out_dir / "pres_figure2_bucketization.png")

    print("Generating Figure 4 (Significance vs # of Buckets)...")
    make_pres_figure_4(out_dir / "pres_figure4_significance.png")
    # Also overwrite legacy filename for backwards compatibility
    make_pres_figure_4(out_dir / "pres_figure4_pvalues.png")

    print("Generating Figure 5a (P-value vs # of Buckets)...")
    make_pres_figure_5a(out_dir / "pres_figure5a_pvalues.png")

    print("Generating Figure 5b (Statistical Power vs Uplift)...")
    make_pres_figure_5b(out_dir / "pres_figure5b_power_uplift.png")

    print("All presentation assets successfully generated!")


if __name__ == "__main__":
    main()
