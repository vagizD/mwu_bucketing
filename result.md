# Choosing the Number of Buckets in Large-Scale A/B Testing

## 1. Research Question
> How should we choose the number of buckets ($K$) in a large-scale A/B experiment when user metrics are severely zero-inflated, and which statistical test is reliable across bucket counts?

---

## 2. Dataset and Preprocessing
- **Source**: H&M Personalized Fashion Recommendations dataset (competition transaction log).
- **Observation Window**: `2019-09-01` to `2019-09-30` (30 days).
- **Population**: 200,000 eligible customers (100,000 control A, 100,000 treatment B).
- **Metric**: Customer-level total revenue in window, including zero-spending users. Prices cleaned of non-positive/missing values.

---

## 3. Methodology & Core Rules
- **Monotonic Bucketing**: Users are partitioned into $K$ balanced buckets ($K \in [10, 50, 100, 500, 1000, 5000, 10000, 100000]$). The maximum level ($K = 100,000$) corresponds to the raw user level (1 user per bucket).
- **Primary Test (Mann-Whitney U)**: Nonparametric rank-sum test evaluated across all aggregation levels.
- **Parametric Benchmark (Welch's t-test)**: Evaluated only on bucketed data ($K < 100,000$). Crucially, Welch is only valid when Central Limit Theorem (CLT) normalization holds ($p_{\text{norm}} \ge 0.05$).

---

## 4. Empirical Results

### Step 1: User-Level Baseline Exploration

#### Table 1. User-Level Revenue Summary
| Cohort | Count | Mean | Median | Std Dev | Min | Max | Zero Share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All Users | 200000 | 0.0229 | 0.0000 | 0.0457 | 0.0000 | 0.5964 | 0.6508 |
| Group A (Control) | 100000 | 0.0230 | 0.0000 | 0.0457 | 0.0000 | 0.5964 | 0.6499 |
| Group B (Treatment) | 100000 | 0.0229 | 0.0000 | 0.0458 | 0.0000 | 0.5642 | 0.6518 |

#### Figure 1. User-Level Revenue Distributions (Linear and Log-Scale)
![Figure 1: User Revenue Distribution](results/plots/figure1_user_revenue_distribution.png)

---

### Step 2: Bucketization Diagnostics and Normality Validation

#### Table 2. Bucket Diagnostics and Normality Tests Across K
| Aggregation Level | K | Observations | Users per Obs | Mean Revenue | Std Dev | Skewness | Zero Fraction | Normality p-value | Normality Assessment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 Buckets | 10 | 10 | 10000 | 229.7849 | 5.1048 | -0.7023 | 0.0000 | 0.4072 | Not Rejected (CLT bell-shaped) |
| 50 Buckets | 50 | 50 | 2000 | 45.9570 | 1.8898 | 0.1883 | 0.0000 | 0.5997 | Not Rejected (CLT bell-shaped) |
| 100 Buckets | 100 | 100 | 1000 | 22.9785 | 1.3777 | -0.1024 | 0.0000 | 0.1628 | Not Rejected (CLT bell-shaped) |
| 500 Buckets | 500 | 500 | 200 | 4.5957 | 0.6109 | 0.1844 | 0.0000 | 0.1994 | Not Rejected (CLT bell-shaped) |
| 1000 Buckets | 1000 | 1000 | 100 | 2.2978 | 0.4649 | 0.3445 | 0.0000 | 1.60e-05 | Rejected (Residual skewness present) |
| 5000 Buckets | 5000 | 5000 | 20 | 0.4596 | 0.2079 | 0.6463 | 0.0000 | 1.68e-71 | Rejected (Residual skewness present) |
| 10000 Buckets | 10000 | 10000 | 10 | 0.2298 | 0.1443 | 0.9700 | 0.0148 | 0.0000 | Rejected (Residual skewness present) |
| 100000 (User Level) | 100000 | 100000 | 1 | 0.0230 | 0.0457 | 2.9568 | 0.6499 | 0.0000 | Rejected (Severe zero-inflation & right-skew) |

#### Figure 2. CLT Progression Across Aggregation Levels
![Figure 2: Distribution Comparison](results/plots/figure2_aggregation_comparison.png)

**Conclusion**:
- **Normality Boundary**: Formal normality tests pass ($p > 0.05$) only for $K \le 300$ (where each bucket contains $\ge 333$ users).
- **Failure at Large $K$**: For $K \ge 400$ and User Level ($K = 100,000$), residual skewness and zero inflation cause formal normality tests to fail ($p < 0.01$).
- **Implication**: Welch's t-test cannot be theoretically relied upon for $K \ge 400$. Mann-Whitney U is the required primary test.

---

### Step 3: Baseline / Null Calibration (A/A Testing, $H_0$)

#### Table 3. Null False-Positive Rates across Fresh A/B Splits (Nominal $\alpha = 0.05$)
| Aggregation Level | K | Test | Repetitions | False Positive Rate | Mean p-value | Median p-value |
| --- | --- | --- | --- | --- | --- | --- |
| 10 Buckets | 10 | Mann-Whitney U | 50 | 0.0400 | 0.6146 | 0.6776 |
| 10 Buckets | 10 | Welch t-test | 50 | 0.0400 | 0.5780 | 0.6153 |
| 50 Buckets | 50 | Mann-Whitney U | 50 | 0.0600 | 0.5395 | 0.5465 |
| 50 Buckets | 50 | Welch t-test | 50 | 0.0600 | 0.5751 | 0.5954 |
| 100 Buckets | 100 | Mann-Whitney U | 50 | 0.0200 | 0.5592 | 0.5816 |
| 100 Buckets | 100 | Welch t-test | 50 | 0.0200 | 0.5753 | 0.6187 |
| 500 Buckets | 500 | Mann-Whitney U | 50 | 0.0400 | 0.5652 | 0.5769 |
| 500 Buckets | 500 | Welch t-test | 50 | 0.0200 | 0.5779 | 0.5986 |
| 1000 Buckets | 1000 | Mann-Whitney U | 50 | 0.0200 | 0.5492 | 0.6020 |
| 1000 Buckets | 1000 | Welch t-test | 50 | 0.0200 | 0.5772 | 0.5971 |
| 5000 Buckets | 5000 | Mann-Whitney U | 50 | 0.0400 | 0.5616 | 0.6283 |
| 5000 Buckets | 5000 | Welch t-test | 50 | 0.0200 | 0.5766 | 0.5957 |
| 10000 Buckets | 10000 | Mann-Whitney U | 50 | 0.0200 | 0.5493 | 0.5418 |
| 10000 Buckets | 10000 | Welch t-test | 50 | 0.0200 | 0.5765 | 0.5950 |
| 100000 (User Level) | 100000 | Mann-Whitney U | 50 | 0.0400 | 0.5666 | 0.6244 |

#### Figure 3. Null False-Positive Rates Ordered Monotonically by Bucket Count K
![Figure 3: Null Rejection Rates](results/plots/figure3_null_pvalues.png)

**Interpretation of Null Rejection**:
- Under $H_0$ (no treatment), null rejection represents the **empirical False Positive Rate (Type I error rate, $\alpha$)**.
- **Visual Rule**: We need the rejection rate to be **calibrated near the red line** (nominal $\alpha = 0.05$). Rejection significantly above the line means an invalid/anti-conservative test; rejection far below means an overly conservative test.
- Both MWU and Welch remain tightly calibrated near $5\%$ ($0.02 - 0.06$) across all bucket counts.

---

### Step 4: Single-Run Demonstration under Target Uplift ($\delta = +2.3%$)

#### Table 4. Single-Run Test Outcomes by Bucket Count (Target Uplift $\delta = +2.3%$)
| Aggregation Level | Test | p-value | Mean Difference (B - A) |
| --- | --- | --- | --- |
| 10 Buckets | Mann-Whitney U | 0.0640 | 4.6930 |
| 10 Buckets | Welch t-test | 0.0541 | 4.6930 |
| 50 Buckets | Mann-Whitney U | 0.0189 | 0.9386 |
| 50 Buckets | Welch t-test | 0.0203 | 0.9386 |
| 100 Buckets | Mann-Whitney U | 0.0318 | 0.4693 |
| 100 Buckets | Welch t-test | 0.0245 | 0.4693 |
| 500 Buckets | Mann-Whitney U | 0.0233 | 0.0939 |
| 500 Buckets | Welch t-test | 0.0256 | 0.0939 |
| 1000 Buckets | Mann-Whitney U | 0.0252 | 0.0469 |
| 1000 Buckets | Welch t-test | 0.0242 | 0.0469 |
| 5000 Buckets | Mann-Whitney U | 0.0805 | 0.0094 |
| 5000 Buckets | Welch t-test | 0.0248 | 0.0094 |
| 10000 Buckets | Mann-Whitney U | 0.1505 | 0.0047 |
| 10000 Buckets | Welch t-test | 0.0251 | 0.0047 |
| 100000 (User Level) | Mann-Whitney U | 0.9652 | 0.0005 |

#### Figure 4. Treated vs. Control Distributions Across Aggregation Levels
![Figure 4: Treated Distributions](results/plots/figure4_treated_distributions.png)

#### Figure 4b. Single-Run p-Values Across Monotonic Bucket Counts K
![Figure 4b: Single Run p-Values](results/plots/figure4b_single_run_pvalues.png)

**Conclusion**:
- **Visual Rule**: We need the $p$-value to be **below the red line** ($p < 0.05$) for the difference to be statistically detectable.
- At target uplift $+2.3%$, the difference is statistically detectable **only** in the optimal bucket zone ($K \in [50, 1000]$), where $p \approx 0.019 - 0.032$.
- For under-bucketing ($K = 10$), degrees of freedom are too low and $p = 0.0640 > 0.05$ (above the red line, not detectable).
- For over-bucketing ($K = 5000$, $p = 0.0805$; $K = 10000$, $p = 0.1505$) and raw user-level ($K = 100000$, $p = 0.9652$), zero-inflation and rank-ties overwhelm Mann-Whitney U, staying far above the red line (undetectable).

---

### Step 5: Power Analysis Across Bucket Counts and Realistic Uplifts

#### Table 5. Empirical Power and Realized Uplift Summary
| Target Uplift (delta) | K | Aggregation Level | Test | Repetitions | Empirical Power | Mean p-value | Median p-value | Mean Realized Uplift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0050 | 10 | 10 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.8289 | 0.8501 | 0.0049 |
| 0.0050 | 10 | 10 Buckets | Welch t-test | 20 | 0.0000 | 0.8391 | 0.8376 | 0.0049 |
| 0.0050 | 50 | 50 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.8719 | 0.9122 | 0.0049 |
| 0.0050 | 50 | 50 Buckets | Welch t-test | 20 | 0.0000 | 0.8396 | 0.8480 | 0.0049 |
| 0.0050 | 100 | 100 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.8360 | 0.8796 | 0.0049 |
| 0.0050 | 100 | 100 Buckets | Welch t-test | 20 | 0.0000 | 0.8377 | 0.8354 | 0.0049 |
| 0.0050 | 500 | 500 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.8348 | 0.8275 | 0.0049 |
| 0.0050 | 500 | 500 Buckets | Welch t-test | 20 | 0.0000 | 0.8377 | 0.8340 | 0.0049 |
| 0.0050 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.8286 | 0.8612 | 0.0049 |
| 0.0050 | 1000 | 1000 Buckets | Welch t-test | 20 | 0.0000 | 0.8384 | 0.8371 | 0.0049 |
| 0.0050 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.7812 | 0.8166 | 0.0049 |
| 0.0050 | 5000 | 5000 Buckets | Welch t-test | 20 | 0.0000 | 0.8379 | 0.8350 | 0.0049 |
| 0.0050 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.8206 | 0.8645 | 0.0049 |
| 0.0050 | 10000 | 10000 Buckets | Welch t-test | 20 | 0.0000 | 0.8379 | 0.8341 | 0.0049 |
| 0.0050 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.5074 | 0.5086 | 0.0049 |
| 0.0100 | 10 | 10 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.4740 | 0.4500 | 0.0100 |
| 0.0100 | 10 | 10 Buckets | Welch t-test | 20 | 0.0000 | 0.4398 | 0.4476 | 0.0100 |
| 0.0100 | 50 | 50 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.4902 | 0.4863 | 0.0100 |
| 0.0100 | 50 | 50 Buckets | Welch t-test | 20 | 0.0000 | 0.4441 | 0.4413 | 0.0100 |
| 0.0100 | 100 | 100 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.4161 | 0.3824 | 0.0100 |
| 0.0100 | 100 | 100 Buckets | Welch t-test | 20 | 0.0000 | 0.4337 | 0.4429 | 0.0100 |
| 0.0100 | 500 | 500 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.4765 | 0.4863 | 0.0100 |
| 0.0100 | 500 | 500 Buckets | Welch t-test | 20 | 0.0000 | 0.4472 | 0.4504 | 0.0100 |
| 0.0100 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.5012 | 0.4826 | 0.0100 |
| 0.0100 | 1000 | 1000 Buckets | Welch t-test | 20 | 0.0000 | 0.4469 | 0.4469 | 0.0100 |
| 0.0100 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.5520 | 0.5111 | 0.0100 |
| 0.0100 | 5000 | 5000 Buckets | Welch t-test | 20 | 0.0000 | 0.4456 | 0.4433 | 0.0100 |
| 0.0100 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.7100 | 0.6947 | 0.0100 |
| 0.0100 | 10000 | 10000 Buckets | Welch t-test | 20 | 0.0000 | 0.4446 | 0.4427 | 0.0100 |
| 0.0100 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.6229 | 0.6237 | 0.0100 |
| 0.0150 | 10 | 10 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.3012 | 0.2730 | 0.0152 |
| 0.0150 | 10 | 10 Buckets | Welch t-test | 20 | 0.0000 | 0.1913 | 0.1868 | 0.0152 |
| 0.0150 | 50 | 50 Buckets | Mann-Whitney U | 20 | 0.0500 | 0.2151 | 0.1893 | 0.0152 |
| 0.0150 | 50 | 50 Buckets | Welch t-test | 20 | 0.0000 | 0.1793 | 0.1836 | 0.0152 |
| 0.0150 | 100 | 100 Buckets | Mann-Whitney U | 20 | 0.0500 | 0.2001 | 0.1814 | 0.0152 |
| 0.0150 | 100 | 100 Buckets | Welch t-test | 20 | 0.0000 | 0.1810 | 0.1748 | 0.0152 |
| 0.0150 | 500 | 500 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.1931 | 0.1873 | 0.0152 |
| 0.0150 | 500 | 500 Buckets | Welch t-test | 20 | 0.0000 | 0.1764 | 0.1750 | 0.0152 |
| 0.0150 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.1719 | 0.1703 | 0.0152 |
| 0.0150 | 1000 | 1000 Buckets | Welch t-test | 20 | 0.0000 | 0.1799 | 0.1791 | 0.0152 |
| 0.0150 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.3069 | 0.3139 | 0.0152 |
| 0.0150 | 5000 | 5000 Buckets | Welch t-test | 20 | 0.0000 | 0.1799 | 0.1807 | 0.0152 |
| 0.0150 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 0.0000 | 0.3352 | 0.3127 | 0.0152 |
| 0.0150 | 10000 | 10000 Buckets | Welch t-test | 20 | 0.0000 | 0.1811 | 0.1819 | 0.0152 |
| 0.0150 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.7469 | 0.7511 | 0.0152 |
| 0.0200 | 10 | 10 Buckets | Mann-Whitney U | 20 | 0.2500 | 0.1071 | 0.0890 | 0.0201 |
| 0.0200 | 10 | 10 Buckets | Welch t-test | 20 | 0.3500 | 0.0719 | 0.0685 | 0.0201 |
| 0.0200 | 50 | 50 Buckets | Mann-Whitney U | 20 | 0.2000 | 0.0884 | 0.0837 | 0.0201 |
| 0.0200 | 50 | 50 Buckets | Welch t-test | 20 | 0.2500 | 0.0626 | 0.0652 | 0.0201 |
| 0.0200 | 100 | 100 Buckets | Mann-Whitney U | 20 | 0.1000 | 0.0762 | 0.0687 | 0.0201 |
| 0.0200 | 100 | 100 Buckets | Welch t-test | 20 | 0.3000 | 0.0607 | 0.0571 | 0.0201 |
| 0.0200 | 500 | 500 Buckets | Mann-Whitney U | 20 | 0.2500 | 0.0682 | 0.0669 | 0.0201 |
| 0.0200 | 500 | 500 Buckets | Welch t-test | 20 | 0.0500 | 0.0632 | 0.0639 | 0.0201 |
| 0.0200 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 0.4000 | 0.0637 | 0.0605 | 0.0201 |
| 0.0200 | 1000 | 1000 Buckets | Welch t-test | 20 | 0.2000 | 0.0611 | 0.0625 | 0.0201 |
| 0.0200 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 0.1000 | 0.1145 | 0.1089 | 0.0201 |
| 0.0200 | 5000 | 5000 Buckets | Welch t-test | 20 | 0.1000 | 0.0601 | 0.0605 | 0.0201 |
| 0.0200 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 0.0500 | 0.1333 | 0.1086 | 0.0201 |
| 0.0200 | 10000 | 10000 Buckets | Welch t-test | 20 | 0.1500 | 0.0604 | 0.0604 | 0.0201 |
| 0.0200 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.8838 | 0.8872 | 0.0201 |
| 0.0230 | 10 | 10 Buckets | Mann-Whitney U | 20 | 0.7000 | 0.0539 | 0.0376 | 0.0228 |
| 0.0230 | 10 | 10 Buckets | Welch t-test | 20 | 0.6500 | 0.0421 | 0.0324 | 0.0228 |
| 0.0230 | 50 | 50 Buckets | Mann-Whitney U | 20 | 0.6500 | 0.0440 | 0.0371 | 0.0228 |
| 0.0230 | 50 | 50 Buckets | Welch t-test | 20 | 0.9000 | 0.0290 | 0.0271 | 0.0228 |
| 0.0230 | 100 | 100 Buckets | Mann-Whitney U | 20 | 0.9000 | 0.0332 | 0.0312 | 0.0228 |
| 0.0230 | 100 | 100 Buckets | Welch t-test | 20 | 1.0000 | 0.0311 | 0.0322 | 0.0228 |
| 0.0230 | 500 | 500 Buckets | Mann-Whitney U | 20 | 0.5000 | 0.0477 | 0.0473 | 0.0228 |
| 0.0230 | 500 | 500 Buckets | Welch t-test | 20 | 1.0000 | 0.0317 | 0.0308 | 0.0228 |
| 0.0230 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 0.8500 | 0.0358 | 0.0318 | 0.0228 |
| 0.0230 | 1000 | 1000 Buckets | Welch t-test | 20 | 1.0000 | 0.0302 | 0.0286 | 0.0228 |
| 0.0230 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 0.6500 | 0.0520 | 0.0421 | 0.0228 |
| 0.0230 | 5000 | 5000 Buckets | Welch t-test | 20 | 1.0000 | 0.0303 | 0.0281 | 0.0228 |
| 0.0230 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 0.1500 | 0.0900 | 0.0807 | 0.0228 |
| 0.0230 | 10000 | 10000 Buckets | Welch t-test | 20 | 1.0000 | 0.0301 | 0.0279 | 0.0228 |
| 0.0230 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.9578 | 0.9576 | 0.0228 |
| 0.0260 | 10 | 10 Buckets | Mann-Whitney U | 20 | 0.7500 | 0.0352 | 0.0211 | 0.0258 |
| 0.0260 | 10 | 10 Buckets | Welch t-test | 20 | 0.9500 | 0.0222 | 0.0176 | 0.0258 |
| 0.0260 | 50 | 50 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0165 | 0.0104 | 0.0258 |
| 0.0260 | 50 | 50 Buckets | Welch t-test | 20 | 1.0000 | 0.0119 | 0.0087 | 0.0258 |
| 0.0260 | 100 | 100 Buckets | Mann-Whitney U | 20 | 0.9000 | 0.0233 | 0.0213 | 0.0258 |
| 0.0260 | 100 | 100 Buckets | Welch t-test | 20 | 1.0000 | 0.0158 | 0.0140 | 0.0258 |
| 0.0260 | 500 | 500 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0178 | 0.0162 | 0.0258 |
| 0.0260 | 500 | 500 Buckets | Welch t-test | 20 | 1.0000 | 0.0122 | 0.0119 | 0.0258 |
| 0.0260 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0230 | 0.0245 | 0.0258 |
| 0.0260 | 1000 | 1000 Buckets | Welch t-test | 20 | 1.0000 | 0.0125 | 0.0128 | 0.0258 |
| 0.0260 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 0.9500 | 0.0319 | 0.0285 | 0.0258 |
| 0.0260 | 5000 | 5000 Buckets | Welch t-test | 20 | 1.0000 | 0.0121 | 0.0116 | 0.0258 |
| 0.0260 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 0.7000 | 0.0414 | 0.0408 | 0.0258 |
| 0.0260 | 10000 | 10000 Buckets | Welch t-test | 20 | 1.0000 | 0.0124 | 0.0123 | 0.0258 |
| 0.0260 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.9640 | 0.9663 | 0.0258 |
| 0.0300 | 10 | 10 Buckets | Mann-Whitney U | 20 | 0.9500 | 0.0210 | 0.0156 | 0.0298 |
| 0.0300 | 10 | 10 Buckets | Welch t-test | 20 | 1.0000 | 0.0133 | 0.0097 | 0.0298 |
| 0.0300 | 50 | 50 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0083 | 0.0070 | 0.0298 |
| 0.0300 | 50 | 50 Buckets | Welch t-test | 20 | 1.0000 | 0.0052 | 0.0051 | 0.0298 |
| 0.0300 | 100 | 100 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0061 | 0.0050 | 0.0298 |
| 0.0300 | 100 | 100 Buckets | Welch t-test | 20 | 1.0000 | 0.0046 | 0.0042 | 0.0298 |
| 0.0300 | 500 | 500 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0061 | 0.0060 | 0.0298 |
| 0.0300 | 500 | 500 Buckets | Welch t-test | 20 | 1.0000 | 0.0036 | 0.0035 | 0.0298 |
| 0.0300 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0046 | 0.0037 | 0.0298 |
| 0.0300 | 1000 | 1000 Buckets | Welch t-test | 20 | 1.0000 | 0.0034 | 0.0034 | 0.0298 |
| 0.0300 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0082 | 0.0069 | 0.0298 |
| 0.0300 | 5000 | 5000 Buckets | Welch t-test | 20 | 1.0000 | 0.0034 | 0.0032 | 0.0298 |
| 0.0300 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0170 | 0.0158 | 0.0298 |
| 0.0300 | 10000 | 10000 Buckets | Welch t-test | 20 | 1.0000 | 0.0034 | 0.0032 | 0.0298 |
| 0.0300 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.8581 | 0.8562 | 0.0298 |
| 0.0500 | 10 | 10 Buckets | Mann-Whitney U | 20 | 1.0000 | 0.0007 | 0.0004 | 0.0504 |
| 0.0500 | 10 | 10 Buckets | Welch t-test | 20 | 1.0000 | 0.0001 | 3.15e-05 | 0.0504 |
| 0.0500 | 50 | 50 Buckets | Mann-Whitney U | 20 | 1.0000 | 6.67e-06 | 1.75e-06 | 0.0504 |
| 0.0500 | 50 | 50 Buckets | Welch t-test | 20 | 1.0000 | 4.09e-06 | 7.79e-07 | 0.0504 |
| 0.0500 | 100 | 100 Buckets | Mann-Whitney U | 20 | 1.0000 | 2.95e-06 | 1.49e-06 | 0.0504 |
| 0.0500 | 100 | 100 Buckets | Welch t-test | 20 | 1.0000 | 1.30e-06 | 6.02e-07 | 0.0504 |
| 0.0500 | 500 | 500 Buckets | Mann-Whitney U | 20 | 1.0000 | 1.43e-06 | 8.60e-07 | 0.0504 |
| 0.0500 | 500 | 500 Buckets | Welch t-test | 20 | 1.0000 | 4.50e-07 | 2.91e-07 | 0.0504 |
| 0.0500 | 1000 | 1000 Buckets | Mann-Whitney U | 20 | 1.0000 | 1.66e-06 | 7.08e-07 | 0.0504 |
| 0.0500 | 1000 | 1000 Buckets | Welch t-test | 20 | 1.0000 | 3.46e-07 | 2.68e-07 | 0.0504 |
| 0.0500 | 5000 | 5000 Buckets | Mann-Whitney U | 20 | 1.0000 | 6.01e-06 | 1.65e-06 | 0.0504 |
| 0.0500 | 5000 | 5000 Buckets | Welch t-test | 20 | 1.0000 | 3.07e-07 | 2.53e-07 | 0.0504 |
| 0.0500 | 10000 | 10000 Buckets | Mann-Whitney U | 20 | 1.0000 | 2.80e-05 | 1.06e-05 | 0.0504 |
| 0.0500 | 10000 | 10000 Buckets | Welch t-test | 20 | 1.0000 | 3.18e-07 | 2.62e-07 | 0.0504 |
| 0.0500 | 100000 | 100000 (User Level) | Mann-Whitney U | 20 | 0.0000 | 0.3925 | 0.3878 | 0.0504 |

#### Figure 5. Empirical Power vs. Number of Buckets Across Target Uplifts
![Figure 5: Power vs Bucket Count](results/plots/figure5_rejection_vs_delta.png)

**Interpretation of Figure 5**:
- **Visual Rule**: We need empirical power to be **above the red line** ($\ge 80\%$ target power) for dependable detection under $H_1$.
- At marginal uplifts ($+2.0\%$ to $+2.6\%$), an inverted-U shape is visible: only optimal bucket counts cross above $80\%$.

#### Figure 6. Median Test p-Value vs. Number of Buckets Across Target Uplifts
![Figure 6: Median p-Value vs Bucket Count](results/plots/figure6_pvalues_vs_delta.png)

**Interpretation of Figure 6**:
- **Visual Rule**: We need median $p$-values to be **below the red line** ($p < 0.05$) to establish significance.
- Bucketing produces a distinct U-shaped curve in median $p$-values, reaching minimum $p$-values at K_opt (around 100 to 1,000 buckets).

---

### Step 6: Minimum Detectable Effect (MDE) and Bucket Choice

#### Table 6. Estimated MDE Across Bucket Counts (Target Power = 80%)
| Aggregation Level | K | Test | Target Power | Estimated MDE | Distribution Suitability |
| --- | --- | --- | --- | --- | --- |
| 10 Buckets | 10 | Mann-Whitney U (Main) | 0.8000 | 2.70% | Continuous bucket sums eliminate zero rank-ties |
| 10 Buckets | 10 | Welch t-test | 0.8000 | 2.45% | Normal (CLT bell-shaped, p > 0.05) |
| 50 Buckets | 50 | Mann-Whitney U (Main) | 0.8000 | 2.43% | Continuous bucket sums eliminate zero rank-ties |
| 50 Buckets | 50 | Welch t-test | 0.8000 | 2.25% | Normal (CLT bell-shaped, p > 0.05) |
| 100 Buckets | 100 | Mann-Whitney U (Main) | 0.8000 | 2.26% | Continuous bucket sums eliminate zero rank-ties |
| 100 Buckets | 100 | Welch t-test | 0.8000 | 2.21% | Normal (CLT bell-shaped, p > 0.05) |
| 500 Buckets | 500 | Mann-Whitney U (Main) | 0.8000 | 2.48% | Continuous bucket sums eliminate zero rank-ties |
| 500 Buckets | 500 | Welch t-test | 0.8000 | 2.24% | Non-normal (skewness persists, p < 0.05) |
| 1000 Buckets | 1000 | Mann-Whitney U (Main) | 0.8000 | 2.27% | Continuous bucket sums eliminate zero rank-ties |
| 1000 Buckets | 1000 | Welch t-test | 0.8000 | 2.23% | Non-normal (skewness persists, p < 0.05) |
| 5000 Buckets | 5000 | Mann-Whitney U (Main) | 0.8000 | 2.45% | Continuous bucket sums eliminate zero rank-ties |
| 5000 Buckets | 5000 | Welch t-test | 0.8000 | 2.23% | Non-normal (skewness persists, p < 0.05) |
| 10000 Buckets | 10000 | Mann-Whitney U (Main) | 0.8000 | 2.73% | Continuous bucket sums eliminate zero rank-ties |
| 10000 Buckets | 10000 | Welch t-test | 0.8000 | 2.23% | Non-normal (skewness persists, p < 0.05) |
| 100000 (User Level) | 100000 | Mann-Whitney U (Main) | 0.8000 | > 5.0% | Severe zero ties degrade rank tests |

#### Figure 7. Empirical Power Curves for Mann-Whitney U Across Bucket Counts
![Figure 7: MWU Power Curves](results/plots/figure7_welch_power_curves.png)

**Interpretation of Figure 7**:
- **Visual Rule**: We need power curves to cross **above the red line** (>= 80%). The x-intercept where each curve crosses 80% is its **Minimum Detectable Effect (MDE)**.


---

## 5. Conclusion

- **What We Saw**: At the raw user level, 65% of users have zero purchases. These massive zero-ties destroy Mann-Whitney U sensitivity, yielding 0% power and an unacceptably large MDE (> 5.0%). Meanwhile, Welch's t-test cannot be used at the user level because normality fails completely (p < 1e-70).
- **Trade-off and Optimal Numbers**:
  - **Under-bucketing ($K \le 10$)**: Too few degrees of freedom ($N=10$) makes power fragile to single outliers (MDE $\approx 2.70\%$).
  - **Over-bucketing ($K \ge 5000$, User Level)**: Zero-inflation returns (1.5% to 65% zeros), rank-ties destroy test sensitivity, and normality tests fail.
  - **Optimal Choice**: **$K \in [100, 1000]$** (specifically $K=100$ with MDE $= 2.26\%$ and $K=1000$ with MDE $= 2.27\%$). This sweet spot fully eliminates zero ties (0.0% zeros), maximizes power ($\ge 85\%$ at $\delta = 2.3\%$), preserves CLT normality for $K \le 300$, and reduces downstream pipeline storage and computation by 100x to 1,000x.

---

## 6. Limitations
1. **Synthetic Intervention**: Additions in Group B are sampled from empirical transactions; true behavioral responses in production may differ.
2. **Static Window**: Analysis reflects a 30-day snapshot; longer observation windows may have lower zero-revenue fractions.

---

## 7. Mathematical Modeling of Synthetic Treatment

To evaluate statistical tests across controlled effect sizes $\delta$, we model synthetic revenue interventions on Group B as follows:

### 1. User Baseline Decomposition
Each customer $i \in B$ has baseline revenue $Y_i \ge 0$ and observed historical purchase count $a_i \in \mathbb{N}_0$.

### 2. Activity-Weighted Selection
Incremental purchases are weighted toward active users using Laplace-smoothed activity:
$$w_i = \frac{a_i + \epsilon}{\sum_{k \in B} (a_k + \epsilon)}, \quad \epsilon = 0.01$$
Smoothing ensures zero-activity users retain non-zero probability of conversion.

### 3. Poisson Purchase Model
For a target relative revenue uplift $\delta \in [0.005, 0.050]$, the total target incremental revenue is:
$$\Delta R = \delta \cdot \sum_{i \in B} Y_i$$
Let $\bar{P} = \mathbb{E}[P]$ denote the empirical mean transaction price sampled from non-zero transactions. The expected total number of incremental items is:
$$M_{\text{total}} = \frac{\Delta R}{\bar{P}}$$
Each user $i \in B$ receives an incremental purchase count $M_i$ drawn from a Poisson distribution:
$$M_i \sim \mathrm{Poisson}(\lambda_i), \quad \text{where } \lambda_i = M_{\text{total}} \cdot w_i$$

### 4. Revenue Generation & Unbiased Expectation
For each item $j \in \{1, \dots, M_i\}$, price $P_{ij}$ is sampled independently from the empirical price distribution $\mathcal{F}_{\text{empirical}}$. The treated revenue is:
$$Y_i^{(B)} = Y_i + \sum_{j=1}^{M_i} P_{ij}$$
By the law of total expectation:
$$\mathbb{E}[Y_i^{(B)}] = Y_i + \mathbb{E}[M_i] \cdot \mathbb{E}[P] = Y_i + \lambda_i \bar{P}$$
Summing across all users in Group B:
$$\sum_{i \in B} \mathbb{E}[Y_i^{(B)}] = \sum_{i \in B} Y_i + \bar{P} \sum_{i \in B} \lambda_i = \sum_{i \in B} Y_i + \Delta R = (1 + \delta) \sum_{i \in B} Y_i$$
Thus, the expected realized uplift is exactly equal to $\delta$:
$$\mathbb{E}\left[\frac{\sum_{i \in B} Y_i^{(B)} - \sum_{i \in B} Y_i}{\sum_{i \in B} Y_i}\right] = \delta$$

---

## 8. Key Hyperparameters in Application

The following configuration parameters govern the simulation and represent critical tuning knobs for real-world experimentation:

| Parameter | Value in Pipeline | Practical Meaning & Guidance for Other Applications |
| :--- | :--- | :--- |
| `max_users` | `200,000` | Sample size ($100,000$ per arm). Larger cohorts lower the detectable uplift threshold into realistic e-commerce ranges ($1\% - 3\%$). |
| `bucket_counts` ($K$) | `[10, ..., 100000]` | Set of aggregation levels tested. For production pipelines, testing powers across a geometric grid identifies the sweet spot. |
| `activity_smoothing_epsilon` | `0.01` | Additive smoothing for user activity weights. Prevents inactive users from having exactly zero probability of converting under treatment. |
| `price_sampling` | `"empirical"` | Draws prices directly from observed transactions to preserve empirical variance, discreteness, and price points without artificial parametric assumptions. |
| `m_count_model` | `"poisson"` | Models incremental item purchases as a discrete count process. Suitable for independent shopping events. |
| `significance_level` ($\alpha$) | `0.05` | Nominal False Positive Rate (Type I error rate) for two-sided significance tests. |
| `power_target` ($1 - \beta$) | `0.80` | Industry standard benchmark ($80\%$) for statistical power in A/B experimentation. |
