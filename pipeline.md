# AIPI 510 Project Pipeline

## Project title
**Choosing the Number of Buckets in Large-Scale A/B Testing**

## Main research question
> How should we choose the number of buckets in a large-scale A/B experiment so that bucket-level metrics are suitable for parametric testing and the experiment achieves a desired minimum detectable effect (MDE)?

## Secondary questions
1. Does random bucket aggregation transform highly skewed user-level revenue into approximately normal bucket-level statistics?
2. How does the number of buckets affect the validity and power of hypothesis tests?
3. For a chosen target effect size `Y` (desired MDE), which bucket counts achieve adequate power (e.g. 80%)?

---

## High-level idea
We use the H&M transactions dataset as a realistic source of customer spending behavior.

- Raw **user-level revenue** is expected to be highly skewed and zero-inflated.
- We randomly aggregate users into **equal-sized buckets**.
- For each bucket count `N`, we study:
  1. the distribution of bucket revenue sums,
  2. whether Welch's t-test becomes reasonable on those bucket statistics,
  3. the test's empirical behavior under null and alternative scenarios.

The goal is **not** to prove in advance that bucketization controls significance. The goal is to measure what happens.

---

## Key assumptions and intended narrative

### What we assume
1. **Users are independent experimental units** for the purpose of simulation.
2. Revenue is nonnegative and strongly skewed at the user level.
3. Equal-sized random buckets are a valid way to construct aggregate statistics.
4. When bucket sizes are sufficiently large, bucket sums may become approximately normal enough for Welch's t-test.
5. The treatment effect is simulated by adding synthetic positive transactions to users in group B.

### What we do *not* assume
1. We do **not** assume in advance that the number of buckets changes power or MDE.
2. We do **not** assume Welch is appropriate on raw user-level aggregates.
3. We do **not** claim that bucketization automatically solves all inference problems.
4. We do **not** discuss practical significance yet except when defining a target MDE later.

### Intended conclusion structure
The final conclusions should answer:
1. Whether bucketization makes Welch more reasonable.
2. Which bucket counts produce bucket distributions that look sufficiently close to normal.
3. Whether changing bucket count affects test power / MDE in a meaningful way.
4. How to choose a bucket count given a target MDE and power requirement.

---

## Dataset
Use the **H&M Personalized Fashion Recommendations** dataset.

Required files:
- `transactions_train.csv`
- `customers.csv` (optional but useful if needed to construct zero-revenue customers)

### Minimum data preparation requirements
1. Choose a fixed observation window and document it.
2. Compute **customer-level total revenue** in that window.
3. Include customers with zero revenue in that window if feasible.
4. Document:
   - number of customers,
   - number of nonzero-revenue customers,
   - total revenue,
   - median, mean, standard deviation,
   - proportion of zero-revenue users.

If using all customers with zero purchases is too heavy initially, create a documented subsample, but preserve zero inflation.

---

## Core experimental pipeline

## Step 0. Configuration
All important parameters must be read from `conf.toml`.

### Required config fields
```toml
random_seed = 42

[data]
transactions_path = "..."
customers_path = "..."
observation_start = "2019-09-01"
observation_end = "2019-09-30"
max_users = 200000            # optional subsample for faster iteration
include_zero_revenue_users = true

[ab]
control_share = 0.5           # A/B split
keep_ab_split_fixed = true

[buckets]
counts = [100, 1000]          # bucket counts to study
include_user_level = true
shuffle_within_group = true

[treatment]
enabled = true
selection_strategy = "activity_weighted"   # alternatives: uniform
price_sampling = "empirical"               # initial required approach
condition_on_activity = false               # optional later extension
uplifts = [0.001, 0.005, 0.01, 0.02, 0.05] # interpreted as expected relative revenue uplift
m_count_model = "poisson"

[simulation]
null_repetitions = 50
alt_repetitions = 20
significance_level = 0.05
power_target = 0.80
mde_targets = [0.005, 0.01, 0.02]

[output]
results_dir = "results"
plots_dir = "results/plots"
tables_dir = "results/tables"
```

Notes:
- `alt_repetitions` can be small at first for speed, but not below 10.
- `null_repetitions` should be large enough to estimate empirical Type I error roughly.
- The agent may add more config fields if necessary, but must preserve these concepts.

---

## Step 1. Baseline exploratory analysis on user-level revenue
Using the original data only, before any synthetic treatment:

1. Build customer-level revenue.
2. Randomly split customers into A and B.
3. Compare A and B at the **user level only**.
4. Produce the required plots and summary table.

### Required outputs

#### Table 1. User-level revenue summary
For all users, A users, B users:
- count
- mean
- median
- standard deviation
- min / max
- zero-revenue share
- 90th / 99th percentiles

#### Figure 1. Distribution of user-level revenue
At least one of:
- histogram,
- histogram with log-scaled x-axis,
- ECDF,
- boxplot (optional).

Goal: visually show that user-level revenue is highly skewed and zero-inflated.

### Expected qualitative interpretation
State explicitly that user-level revenue is clearly non-normal, which motivates bucketization before using Welch's t-test.

---

## Step 2. Bucketization diagnostics on baseline data
Randomly bucket users **within A and within B separately** into equal-sized buckets.

Study:
- user level (for visualization/reference only),
- 1000 buckets,
- 100 buckets.

If the sample size makes one of these impossible, use the configured counts and document it.

For each bucket count:
1. Aggregate **sum of user revenues** in each bucket.
2. Plot bucket revenue distributions.
3. Summarize mean, variance, skewness, and bucket size.

### Required outputs

#### Table 2. Bucket-level diagnostic summary
Rows: aggregation levels (`user`, `1000 buckets`, `100 buckets`)
Columns:
- number of observations
- users per observation
- mean bucket revenue
- standard deviation
- skewness
- fraction of zeros (if any)
- informal note on approximate normality

#### Figure 2. Distribution comparison across aggregation levels
A clear multi-panel figure or separate figures comparing:
- user-level revenue
- 1000-bucket revenues
- 100-bucket revenues

Important: these plots should make the normalizing effect of aggregation visually evident if present.

### Expected interpretation
The report should comment on whether bucketization appears to reduce skewness and whether this makes Welch's t-test more plausible.

Do **not** use Shapiro-Wilk. Visual diagnostics and descriptive statistics are enough.

---

## Step 3. Baseline/null testing on original data
Purpose: estimate whether, under no synthetic treatment, the tests reject near the nominal rate after random A/B assignment.

### Protocol
For each null repetition:
1. Re-randomize customers into A and B.
2. For each aggregation level (`user`, `1000 buckets`, `100 buckets`):
   - aggregate the data,
   - run **Mann-Whitney U**,
   - run **Welch's t-test only for bucketized data**.
3. Save p-values.

### Important rule
- **Do not run Welch on user-level revenue in the final reported analysis.**
- MWU may be run at user level as a nonparametric reference.
- Welch is for bucket-level aggregates only.

### Required outputs

#### Table 3. Null rejection rates
Rows: aggregation level / test combination
- user-level MWU
- 1000-bucket MWU
- 100-bucket MWU
- 1000-bucket Welch
- 100-bucket Welch

Columns:
- number of repetitions
- rejection rate at alpha = 0.05
- mean p-value
- median p-value

#### Figure 3. Null p-value distributions
Suggested:
- histograms of p-values under the null,
- or bar chart of rejection rates.

### Expected interpretation
The report should assess whether the tests are approximately calibrated under the null.

---

## Step 4. Synthetic treatment generation
Now simulate a positive uplift in B.

### Treatment design
Let `R_B` be the original total revenue of group B.
For a configured uplift `delta`, the **target expected additional revenue** is:

`Delta_R = delta * R_B`

Use a **compound Poisson** style generator:

1. Compute empirical average transaction price `p_bar` from the original transactions.
2. Set expected number of synthetic transactions:
   `lambda = Delta_R / p_bar`
3. Draw:
   `M ~ Poisson(lambda)`
4. Generate `M` synthetic transactions.

For each synthetic transaction:
1. Choose a B user according to a configurable selection strategy.
2. Sample a transaction amount from the empirical transaction-price distribution.
3. Add that transaction to the selected user.

### Required selection block
Implement customer selection as a separate interchangeable component.

Required strategies:
- `uniform`
- `activity_weighted` (**default**)

### Definition of activity_weighted
Use a reasonable customer activity signal, documented explicitly. Prefer one of:
- number of original transactions in the observation window,
- original revenue in the observation window,
- a smoothed version to avoid zero-probability issues.

The exact formula must be documented in the report and code.

Example acceptable approach:
`weight_i = original_transaction_count_i + epsilon`
with small `epsilon > 0`.

### Required note in report
Make clear that treatment changes are introduced **only in B**.
The simulation reflects an intervention that creates additional purchases.

---

## Step 5. Single-run demonstration under alternative
Before running many repetitions, perform one fully inspectable run for 1-2 `delta` values.

For each chosen `delta`:
1. Generate synthetic treatment data in B.
2. Aggregate at user level, 1000 buckets, 100 buckets.
3. Plot distributions.
4. Run MWU and Welch (Welch only on bucket levels).

### Required outputs

#### Table 4. Single-run p-values and summary statistics
Rows: aggregation level / test
Columns:
- delta
- test statistic
- p-value
- estimated difference in mean revenue (or bucket revenue)

#### Figure 4. Example treated distributions
Show how A and B compare for:
- user-level revenue,
- 1000-bucket sums,
- 100-bucket sums.

Purpose: ensure the pipeline works and produce interpretable visuals.

---

## Step 6. Repeated experiments under alternatives
For each configured `delta` and each repetition:
1. Keep the original A/B split fixed if configured so.
2. Regenerate synthetic transactions in B.
3. For each aggregation level, form buckets and compute tests.
4. Save p-values and summary statistics.

### Required outputs

#### Table 5. Power / rejection-rate table under alternatives
Rows: each combination of `delta`, aggregation level, and test.
Columns:
- repetitions
- rejection rate (empirical power)
- mean p-value
- median p-value
- mean observed uplift
- std observed uplift

#### Figure 5. Rejection rate vs delta
Recommended format:
- x-axis: `delta`
- y-axis: empirical rejection rate
- separate lines for:
  - user-level MWU
  - 1000-bucket MWU
  - 100-bucket MWU
  - 1000-bucket Welch
  - 100-bucket Welch

#### Figure 6. P-value vs delta (optional but useful)
Can show median p-value or boxplots of p-values.

### Expected interpretation
This section should answer whether bucket count changes detection behavior and whether MWU and Welch behave differently.

---

## Step 7. MDE analysis / choosing the number of buckets
Now connect the results to the main research question.

### Goal
For each candidate bucket count `N`, estimate the smallest uplift `delta` for which empirical power reaches the target level (e.g. 80%).

Formally, estimate:

`MDE(N) = smallest delta such that empirical_power(N, delta) >= target_power`

Do this separately at least for:
- bucket-level Welch,
- bucket-level MWU.

### Required outputs

#### Table 6. Estimated MDE by bucket count
Rows:
- 1000 buckets
- 100 buckets
- (optional other bucket counts if explored)

Columns:
- test
- target power
- estimated MDE
- comments on distribution shape / suitability

#### Figure 7. Power curves for bucketized Welch
At minimum:
- x-axis: `delta`
- y-axis: empirical power
- one line per bucket count.

This is the figure that should support the answer to “How to choose the number of buckets?”

### Final expected conclusion for this section
The report should explicitly answer:
1. Which bucket counts make Welch plausible?
2. Which bucket counts achieve the desired power for the target MDE?
3. If multiple bucket counts work, which one is preferable and why?

Possible reasons may include:
- more normal-looking bucket distributions,
- stable null calibration,
- adequate power,
- simplicity / practicality.

---

## Statistical testing rules

### Mann-Whitney U
Run on:
- user-level revenues,
- 1000-bucket revenues,
- 100-bucket revenues.

Document that ties are expected because of many zeros.
Use the standard implementation with tie handling.

### Welch's t-test
Run **only** on bucketized revenues, not on raw user-level revenues.

Reason to document:
- user-level revenue is manifestly non-normal,
- bucketization is intended to create more suitable aggregate statistics.

### Significance level
Use alpha = 0.05 unless overridden in config.

---

## Deliverables expected from the agent
The agent should not only write code but also produce artifacts.

### Required files
- `conf.toml`
- analysis scripts (plain Python scripts, not notebooks)
- generated figures
- generated tables (CSV and/or markdown)
- `result.md`

### `result.md` must include
1. Short statement of the research question.
2. Brief description of dataset and preprocessing.
3. Summary of bucketization idea.
4. Inserted figures and tables.
5. Interpretation after each figure/table.
6. Final answer to the main question:
   **How should we choose the number of buckets?**
7. Limitations.

---

## Limitations that must be acknowledged
1. Synthetic treatment is a simulation, not a real randomized production algorithm.
2. The treatment model adds purchases rather than changing latent customer preference or recommendation quality.
3. Results may depend on the observation window and customer subsampling choices.
4. Approximate normality is assessed visually / descriptively rather than through a strict formal rule.
5. Fixed A/B split under alternatives produces conditional power estimates; null experiments should re-randomize A/B.

---

## What the agent should NOT do
1. Do not broaden the project back into a general “statistical vs practical significance” essay.
2. Do not run Welch's t-test on raw user-level revenues in the final analysis.
3. Do not introduce unnecessary methods such as Shapiro-Wilk, bootstrap CIs, or Q-Q plots unless clearly useful and lightweight.
4. Do not replace the empirical-price synthetic generator with another model unless explicitly added as an optional extension.
5. Do not overclaim causal conclusions beyond the simulation setup.

---

## Minimal success criteria
The pipeline is successful if the agent produces:
1. A reproducible data-preparation pipeline on H&M data.
2. Clear visual evidence about how bucketization changes the distribution.
3. Null calibration results.
4. Alternative power results for multiple deltas.
5. An estimated MDE-by-bucket-count table.
6. A reasoned answer to the bucket-count choice question.

