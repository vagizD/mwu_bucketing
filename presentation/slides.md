# Retail A/B Testing with Bucketization

**Authors**: Vagiz Daudov, Konur Nordberg  
**Institution**: Duke University  
**Interactive Deck**: [presentation/index.html](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/presentation/index.html) *(Use ArrowRight / Space to reveal elements sequentially, `F` for fullscreen, `Ctrl+P` for PDF print).*

---

### Slide 1: Title
- **Retail A/B Testing with Bucketization**
- Vagiz Daudov · Konur Nordberg
- Duke University

---

### Slide 2: Problem Setup & Hypotheses
- **Title**: Problem Setup & Hypotheses
- **Research Question**: *"How to make sure algorithm X is better than current baseline Y?"*
- **Experimental Cohorts**:
  - Control ($A$): Current Baseline $Y$
  - Treatment ($B$): Candidate Algorithm $X$
- **Formal Hypotheses**:
  - Null Hypothesis ($H_0$): No revenue difference
    $$H_0: F_A(y) = F_B(y) \quad (\mu_A = \mu_B)$$
  - Alternative Hypothesis ($H_1$): Algorithm $X$ drives revenue uplift
    $$H_1: F_A(y) \neq F_B(y) \quad (\mu_B > \mu_A)$$
- **Design Thresholds**: $\alpha = 0.05$, target power $1 - \beta \ge 0.80$.

---

### Slide 3: Customer Revenue Distribution
- **Title**: Customer Revenue Distribution
- **Figure**: [pres_figure1a_user_revenue.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure1a_user_revenue.png)
- Single plot showing real customer revenue distribution (65.0% zeros, long tail).

---

### Slide 4: Customer Revenue: Control vs. Treatment (+3% Lift)
- **Title**: Customer Revenue: Control vs. Treatment (+3% Lift)
- **Figure**: [pres_figure1b_mwu_failure.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure1b_mwu_failure.png)
- Single plot showing +3% active lift comparison:
  - Welch t-test: $p = 0.0009$ (Rejected: data non-normal).
  - Mann-Whitney U: $p = 0.1402$ (Holds: fails to reject null).

---

### Slide 5: Bucketization: Central Limit Theorem
- **Title**: Bucketization: Central Limit Theorem
- **Figure**: [pres_figure2_bucketization.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure2_bucketization.png)
- Single plot showing distribution transition across buckets:
  - $K = 10$: Normal
  - $K = 100$: Normal
  - $K = 1000$: Non-normal
  - User-Level: Non-normal

---

### Slide 6: How to choose number of buckets?
- **Title**: How to choose number of buckets?
- **We need to fix K before A/B, considering:**
  1. Statistical power: $1 - \beta \ge 0.80$
  2. Significance level: $\alpha \le 0.05$ (control False Positive Rate)
  3. Minimum Detectable Effect (MDE): minimal possible

---

### Slide 7: Significance: A/A False Positive Rate
- **Title**: Significance: A/A False Positive Rate
- **Figure**: [pres_figure4_significance.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure4_significance.png)
- Single plot showing False Positive Rate across $K$ under the null ($\text{Uplift} = 0\%$, $N=50$ repetitions, 95% Wilson CIs).

---

### Slide 8: P-value vs # of Buckets (B has +2.3% Lift)
- **Title**: P-value vs # of Buckets (B has +2.3% Lift)
- **Figure**: [pres_figure5a_pvalues.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure5a_pvalues.png)
- Single plot showing P-value curve across $K$ under true treatment $\delta = +2.3\%$:
  - Mann-Whitney U fails at user-level ($p=0.965$).
  - Buckets successfully detect lift ($p=0.032$ at $K=100$).

---

### Slide 9: Statistical Power vs. Uplift (B has Lift)
- **Title**: Statistical Power vs. Uplift (B has Lift)
- **Figure**: [pres_figure5b_power_uplift.png](file:///home/vagiz/Desktop/desktop_vagiz/duke/sda/project2/results/plots/pres_figure5b_power_uplift.png)
- Single plot showing empirical power curves across uplifts with 95% Wilson CIs:
  - Vertical dotted line at $\delta = 2.3\%$.
  - Horizontal reference line at $80\%$ target power.

---

### Slide 10: Optimal Bucket Count
- **Title**: Optimal Bucket Count
- **Process Sequence**:
  $$\text{A/B Experiment} \longrightarrow \text{Non-normal Data} \longrightarrow \text{Bucketization } (K^* \approx 100\text{--}1000) \longrightarrow \text{Mann-Whitney U}$$
- **Key Points**:
  - Optimal range: $K \in [100, 1000]$
  - Satisfies power $\ge 80\%$ and significance $\le 0.05$
  - Minimizes detectable effect ($\text{MDE} = 2.26\%$)

---

### Slide 11: Modeling Caveats
- **Title**: Modeling Caveats
- **Key Points**:
  - Monte-Carlo Resolution (number of uplift runs).
  - Uplift Mechanism: Requires empirical knowledge.
  - Population Structure: Heavy Skewness, Non-normality.

---

### Slide 12: Thank You
- **Title**: Thank you
- **Subtitle**: Remember us once you get in large-scale
- Vagiz Daudov · Konur Nordberg · Duke University

---

### Slide 13: Appendix: Treatment Injection Modeling
- **Title**: Appendix: Treatment Injection Modeling
- **Formulas**:
  - Activity Weighting:
    $$w_i = \frac{A_i + \epsilon}{\sum_{j=1}^{N_B} (A_j + \epsilon)}$$
  - Purchase Intensity & Extra Items:
    $$\lambda_i = \lambda_0 \cdot w_i \cdot N_B, \quad K_i \sim \text{Poisson}(\lambda_i), \quad P_{i, m} \sim \hat{F}_{\text{empirical}}$$
  - Expectation Calibration:
    $$\mathbb{E}[\Delta R_B] = \sum_{i \in B} \mathbb{E}[K_i] \cdot \mathbb{E}[P] = \bar{P} \cdot \lambda_0 \cdot N_B = \delta \cdot R_B^{\text{base}} \implies \lambda_0 = \frac{\delta \cdot R_B^{\text{base}}}{N_B \cdot \bar{P}}$$
- **Notation Definitions**:
  - $i \in B, N_B$: Customer index & treatment cohort size ($N_B = 100,000$)
  - $A_i$: Historical 30-day transaction count (activity)
  - $\epsilon = 0.01$: Laplace smoothing parameter ($\epsilon > 0$)
  - $w_i$: Normalized customer activity probability weight
  - $\lambda_i, \lambda_0$: Individual & base Poisson purchase intensities
  - $K_i \sim \text{Poisson}(\lambda_i)$: Count of additional purchases for user $i$
  - $P_{i, m} \sim \hat{F}_{\text{empirical}}$: Empirical transaction price drawn with replacement
  - $\bar{P} = \mathbb{E}[P]$: Empirical mean transaction price
  - $R_B^{\text{base}}$: Baseline total revenue of treatment cohort
  - $\delta$: Target relative revenue uplift ($\delta = +2.3\%$)
  - $\Delta R_B$: Realized incremental revenue injected into group $B$
  - $\mathbb{E}[\Delta R_B] = \delta \cdot R_B^{\text{base}}$: Unbiased revenue uplift guarantee

---

### Slide 14: Appendix: Diagnostic Table
| Aggregation Level | $K$ | Normality Status | MWU FPR ($\alpha=0.05$) [95% CI] | Single-run $p$ ($\delta=+2.3\%$) | Estimated MDE ($\text{Power}=80\%$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 10 Buckets | 10 | **Holds** | 0.040 [0.011, 0.135] | 0.0640 (Rejected) | +2.70% |
| 50 Buckets | 50 | **Holds** | 0.060 [0.021, 0.162] | 0.0189 (Holds) | +2.50% |
| **100 Buckets** | **100** | **Rejected** | **0.020 [0.004, 0.105]** | **0.0318 (Holds)** | **+2.26% (Optimal)** |
| 500 Buckets | 500 | **Rejected** | 0.040 [0.011, 0.135] | 0.0233 (Holds) | +2.45% |
| **1000 Buckets** | **1000** | **Rejected** | **0.020 [0.004, 0.105]** | **0.0252 (Holds)** | **+2.27% (Optimal)** |
| 5000 Buckets | 5000 | **Rejected** | 0.040 [0.011, 0.135] | 0.0805 (Rejected) | +2.85% |
| 10000 Buckets | 10000 | **Rejected** | 0.020 [0.004, 0.105] | 0.1505 (Rejected) | +2.73% |
| **User-Level (Raw)** | **100000** | **Rejected** | **0.040 [0.011, 0.135]** | **0.9652 (Rejected)** | **> +5.00%** |
