# Presentation Deck: A/B Testing on Zero-Inflated Revenue
**Subtitle**: Why Mann-Whitney U Fails on User-Level Data and How Bucketization Restores Power  
**Design System**: Stripe & Linear Technical Slate (Clean off-white canvas `#f8fafc`, crisp deep navy `#0f172a`, monospaced parameter tags, high-contrast scientific graphics)  
**Interactive Deck File**: [presentation/index.html](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/presentation/index.html) (Open in any web browser, use Arrow keys / Spacebar to navigate, press `F` for fullscreen, or `Ctrl+P` to export to PDF).

---

## Slide 1: Cover Slide
- **Title**: A/B Testing on Zero-Inflated Revenue
- **Subtitle**: When Non-Parametric Rank Tests Break Down & How Bucketization Restores Power
- **Badges**: `AIPI 510` | `Large-Scale Inference` | `E-Commerce Experimentation` | `2026 Benchmark`
- **Metadata**: 200,000 Customers (100k A / 100k B) · 65.0% Zero Purchases · Severe Rank Ties

---

## Slide 2: The Production Dilemma (3a)
- **Title**: Retail Recommender Upgrade: The Zero-Inflation Trap
- **Hypotheses**:
  - $H_0: \mathbb{E}[R_B] = \mathbb{E}[R_A]$ (No revenue uplift)
  - $H_1: \mathbb{E}[R_B] > \mathbb{E}[R_A]$ (Positive revenue uplift)
- **Visual**: [pres_figure1_mwu_failure.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure1_mwu_failure.png)
  - **Panel A**: Real E-Commerce Baseline (65.0% zeros, Skewness = 3.0). Normality $p < 10^{-50}$.
  - **Panel B**: Production Dilemma (+3.0% lift on spenders). Welch $p = 0.0009$ (invalid due to non-normality); Mann-Whitney U $p = 0.1402 > 0.05$ (fails to detect due to massive zero ties!).
- **Takeaways (Strictly $\le 5$ words)**:
  1. *65% users spend nothing.*
  2. *Welch assumes non-existent normality.*
  3. *Zero-ties destroy rank tests.*
  4. *Obvious uplift remains undetected.*

---

## Slide 3: The Solution — Bucketization & CLT (3b)
- **Title**: Bucketization: Eliminating Zero-Ties via CLT
- **Visual Schematic**:
  - $100\text{k Users} \xrightarrow{\text{Hash mod } K} K\text{ Equal Buckets} \xrightarrow{\sum} \text{Gaussian Aggregates (0.0% Zero Ties)}$
- **Visual**: [pres_figure2_bucketization.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure2_bucketization.png)
  - Subplots showing distribution transition across $K$:
    - $K=10$: Normality $p = 0.687$ (Holds) | Zeros: $0.0\%$
    - $K=100$: Normality $p = 0.806$ (Holds) | Zeros: $0.0\%$
    - $K=1000$: Normality $p < 0.001$ (Rejected) | Zeros: $0.0\%$
    - User-Level ($K=100\text{k}$): Normality $p < 10^{-50}$ (Severely Rejected) | Zeros: $65.0\%$
- **Takeaways (Strictly $\le 5$ words)**:
  1. *Aggregates eliminate zero ties.*
  2. *CLT restores approximate normality.*
  3. *Bucket sums preserve expectations.*
  4. *Small K enables Welch.*

---

## Slide 4: Pre-Experiment Simulation — Controlled Uplift (3c)
- **Title**: Calibrated Synthetic Treatment Injection
- **Subtitle**: Testing Statistical Sensitivity Before Live Deployment
- **Visual Schematic**:
  - `User Activity`: 30-day historical purchases $A_i$
  - `Activity Weighting`: $w_i \propto A_i + \epsilon$
  - `Price Bootstrap`: Sample items from empirical transaction pool $P \sim \hat{F}$
  - `Analytic Guarantee`: Calibrated to exact target uplift $\mathbb{E}[\Delta R] = \delta \cdot R_{\text{total}}$
- **Takeaways (Strictly $\le 5$ words)**:
  1. *Simulate before live deployment.*
  2. *Weight by customer activity.*
  3. *Sample empirical item prices.*
  4. *Guarantees exact expected uplift.*

---

## Slide 5: Performance Across Bucket Counts — The Detection Window (3d)
- **Title**: P-Value vs. Number of Buckets (Target Uplift $\delta = +2.3\%$)
- **Visual**: [pres_figure4_pvalues.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure4_pvalues.png)
  - Horizontal threshold line at $\alpha = 0.05$ (Must be below red line to detect).
  - $K=10$: $p = 0.064$ (Under-bucketing: low DF, above red line).
  - $K \in [50, 1000]$: $p \in [0.019, 0.032] < 0.05$ (**Optimal Detection Zone**).
  - $K \ge 5000$: $p \ge 0.081 > 0.05$ (Over-bucketing: zero inflation returns).
  - User-Level ($K=100\text{k}$): $p = 0.965$ (Total failure).
- **Pre-Experiment Criteria**:
  1. Preserve nominal significance ($\alpha = 0.05$).
  2. Ensure empirical power $\ge 80\%$.
  3. Minimize Minimum Detectable Effect (MDE).
- **Takeaways (Strictly $\le 5$ words)**:
  1. *Under-bucketing lacks sample size.*
  2. *Over-bucketing restores zero-ties.*
  3. *K in [50, 1000] succeeds.*
  4. *Never tune on live-data.*

---

## Slide 6: Pre-Experiment Power & Significance Analysis (3e)
- **Title**: Power Curves & Significance Calibration Across $K$
- **Visual**: [pres_figure5_power_significance.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure5_power_significance.png)
  - **Panel A (Power vs Uplift)**: Target power $\ge 80\%$ line. $K=100$ and $K=1000$ achieve lowest MDE ($+2.26\%$), while User-Level remains at $0\%$ power ($\text{MDE} > +5.0\%$).
  - **Panel B (Significance Calibration under $H_0$)**: Nominal $\alpha = 0.05$ line. All bucket counts maintain false-positive control within 95% Wilson intervals.
- **Takeaways (Strictly $\le 5$ words)**:
  1. *Significance calibrated across all K.*
  2. *K=100-1000 minimizes MDE (2.26%).*
  3. *User-level MDE exceeds 5%.*
  4. *Select K minimizing MDE.*

---

## Slide 7: Conclusion & Engineering Principles (3f)
- **Title**: Conclusion: Principles for Production Experimentation
- **Takeaways (Strictly $\le 5$ words)**:
  1. *Real data violates textbook normality.*
  2. *Zero-ties destroy rank tests.*
  3. *Bucketing restores statistical power.*
  4. *Pre-simulate optimal bucket count.*
  5. *Pipeline generalizes to any metric.*

---

## Slide 8: Real-World Impact & Closing (3g)
- **Title**: Thank You
- **Core Message**: *"We hope that you learned from real-world scenario"*
- **Subtitle**: A principled production simulation framework for machine learning and data science engineers tackling zero-inflated metrics in industry experimentation.
- **Badges**: `git@github.com:vagizD/mwu_bucketing.git` | `Validated Simulation Suite` | `Q&A`

---

## Slide 9: Appendix A — Mathematical Treatment Formulation
- **Activity Weighting**:
  $$w_i = \frac{A_i + \epsilon}{\sum_{j=1}^{N_B} (A_j + \epsilon)}$$
- **Poisson Intensity**:
  $$\lambda_i = \lambda_0 \cdot w_i \cdot N_B, \quad K_i \sim \text{Poisson}(\lambda_i)$$
- **Price Sampling**:
  $$P_{i, m} \sim \hat{F}_{\text{empirical}}$$
- **Expectation Calibration**:
  $$\mathbb{E}[\Delta R_B] = \sum_{i \in B} \mathbb{E}[K_i] \cdot \mathbb{E}[P] = \bar{P} \cdot \lambda_0 \cdot N_B = \delta \cdot R_B^{\text{base}}$$
  $$\implies \lambda_0 = \frac{\delta \cdot R_B^{\text{base}}}{N_B \cdot \bar{P}}$$

---

## Slide 10: Appendix B — Hyperparameter Table (`conf.toml`)
| Hyperparameter | Value | Category | Production Importance |
| :--- | :--- | :--- | :--- |
| `max_users` | 200,000 | Data | Dictates experiment population (100k per arm) and degrees of freedom. |
| `bucket_counts` | [10..100000] | Bucketing | Controls the CLT normality vs. rank-tie aggregation trade-off. |
| `activity_smoothing_epsilon` | 0.01 | Treatment | Laplace smoothing ensuring inactive users retain positive exploration probability. |
| `uplifts (deltas)` | [0.005..0.050] | Treatment | Retail effect sizes (+0.5% to +5.0%) spanning sub-MDE to easily detectable zones. |
| `null_repetitions` | 50 | Simulation | Replications for Type I error calibration with 95% Wilson score intervals. |
| `alt_repetitions` | 20 | Simulation | Monte Carlo replications per uplift to construct empirical power curves. |
| `significance_level` | 0.05 | Simulation | Nominal threshold $\alpha$ for statistical significance. |
| `power_target` | 0.80 | Simulation | Standard 80% power intercept used to solve for Minimum Detectable Effect (MDE). |

---

## Slide 11: Appendix C — Diagnostics & MDE across All Levels
| Aggregation Level | $K$ | Zero Share | Normality $p$ | Status | FPR ($\alpha=0.05$) [95% Wilson CI] | Single-Run $p$ ($\delta=+2.3\%$) | Estimated MDE ($\text{Power}=80\%$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 10 Buckets | 10 | 0.0% | 0.6868 | Holds | 0.040 [0.011, 0.135] | 0.0640 (Fail) | +2.70% |
| 50 Buckets | 50 | 0.0% | 0.0792 | Holds | 0.060 [0.021, 0.162] | 0.0189 (Pass) | +2.50% |
| **100 Buckets** | **100** | **0.0%** | **0.0347** | **Marginal** | **0.020 [0.004, 0.105]** | **0.0318 (Pass)** | **+2.26% (Optimal)** |
| 500 Buckets | 500 | 0.0% | 0.0003 | Rejected | 0.040 [0.011, 0.135] | 0.0233 (Pass) | +2.45% |
| **1000 Buckets** | **1000** | **0.0%** | **0.0000** | **Rejected** | **0.020 [0.004, 0.105]** | **0.0252 (Pass)** | **+2.27% (Optimal)** |
| 5000 Buckets | 5000 | 0.0% | 0.0000 | Rejected | 0.040 [0.011, 0.135] | 0.0805 (Fail) | +2.85% |
| 10000 Buckets | 10000 | 0.0% | 0.0000 | Rejected | 0.020 [0.004, 0.105] | 0.1505 (Fail) | +2.73% |
| **User-Level (Raw)** | **100000** | **65.0%** | **0.0000** | **Rejected** | **0.040 [0.011, 0.135]** | **0.9652 (Total Fail)** | **> +5.00% (Undetectable)** |
