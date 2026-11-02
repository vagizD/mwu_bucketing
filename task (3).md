# AIPI 510 Module Project 2 — Preliminary A/B Bucketing Experiment

## Objective

Implement a **small, reproducible experiment** testing how random user-bucket aggregation affects the behavior of Welch's two-sample t-test and the Mann–Whitney U (MWU) test on realistic, highly skewed customer revenue data.

We use the **H&M Personalized Fashion Recommendations** transactions dataset. H&M did not run this A/B experiment: treatment transactions are **synthetic**, generated from the empirical transaction-price distribution.

**Do not build a large framework or produce a report/presentation yet.** First get the specified pipeline running and produce inspectable preliminary charts and results. Keep implementations concrete, type-annotated, and modular enough to switch customer-selection strategies.

## Research question

For a fixed underlying A/B population and a known *expected* incremental revenue effect, how does aggregating users into `K` random, equal-sized buckets change the p-values and rejection rates of Welch's test and MWU? How do their conclusions differ for skewed, sparse user-spending data?

We are **not** assuming that fewer buckets must reduce power or that MWU tests equality of means. These are questions to investigate.

## Dataset and metric

Use the H&M Kaggle dataset: https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data

- Required: `transactions_train.csv` (`customer_id`, `price`, `t_dat`) and `customers.csv` (`customer_id`).
- Read the dataset from paths specified in `conf.toml`; **do not** download automatically or embed absolute paths.
- Use a configurable fixed observation window (start and end dates). Filter transactions to this window, then aggregate spending by customer.
- Include all customers from the customer table in the eligible population, including **zero-transaction** users. If a configurable user subsample is needed for speed, draw it reproducibly from the full eligible population, then restrict transactions accordingly.
- Keep the dataset's price units as-is (they are normalized, not necessarily currency amounts). Ignore missing/invalid and nonpositive prices with documented cleaning counts.
- Revenue for customer `i`: `r_i = sum(price for transactions by i)`; activity `a_i = number of observed transactions by i`.
- Show basic descriptive statistics: users, purchasers, transactions, revenue, spending quantiles, fraction with zero revenue, and activity concentration.

## Configuration: conf.toml

**All experimental parameters must be configurable in a single `conf.toml`** (not hardcoded throughout the scripts). Include a documented example with working defaults, e.g.:

```toml
[data]
transactions_path = "data/transactions_train.csv"
customers_path = "data/customers.csv"
start_date = "2019-09-01"
end_date = "2020-08-31"
max_users = 200000  # 0 means all; subsample BEFORE A/B assignment

[experiment]
seed = 42
ab_fraction = 0.5
bucket_counts = [100, 1000, 0]  # 0 = one observation per user
uplifts = [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]
repetitions = 20  # at least 10 per uplift; can increase later
alpha = 0.05

[treatment]
customer_selection = "activity_weighted" # interchangeable: "uniform"
activity_weight_exponent = 1.0 # weights = activity ** exponent; zero activity => zero weight
price_sampling = "empirical"  # sample with replacement from original observed transaction prices
count_distribution = "poisson"
count_dispersion = 1.0 # reserved for optional later extension; Poisson currently uses dispersion 1

[output]
dir = "results/preliminary"
plot_format = "png"
```

If a configuration entry is unsupported in the first implementation, **do not expose it as if it works**. In particular, either omit `count_dispersion` entirely for now, or implement and document its actual effect. Prefer omitting it for the initial Poisson-only model. Validate `K` against group size and ensure bucket sizes are exactly equal (e.g., sample a number of users per group divisible by all requested finite `K`, or reject invalid configurations with a helpful error).

## Pipeline — follow this order

### 0. Prepare the original data and fix the A/B split

- Randomly partition eligible customers once into disjoint A (control) and B (treatment) groups of equal size, using the configured seed.
- Persist the assignment or its deterministic reproducibility metadata. **Hold the A/B split fixed across the main repetitions and all `delta` values.**
- A and B begin with unchanged original revenue and transaction counts. Never modify A's transactions.
- For both populations, preserve user IDs and baseline activity counts for subsequent weighting.

### 1. Baseline (no synthetic transactions)

- Analyze original A and B spending without injection.
- For each `K`, shuffle customers independently within A and B, assign them to exactly equal-sized buckets, and sum customer revenue within each bucket.
- `K=0` means **user-level** observations (each customer's revenue is one observation; do not physically construct millions of single-user bucket records).
- Visualize distributions and compute Welch and MWU p-values.
- This is the **true null scenario** for no imposed treatment; do not pretend that adding positive transactions to B with a zero parameter is a null.

### 2. Synthetic transaction generator (B only)

For each configured uplift `delta > 0`, using B's **original baseline** revenue `R_B`:

1. Target expected incremental revenue `delta_R = delta * R_B`.
2. Estimate `mean_price` from the observed individual transaction prices in the configured window, prior to any synthetic additions.
3. Set `lambda_M = delta_R / mean_price` and draw `M ~ Poisson(lambda_M)`. Thus **E[synthetic revenue | baseline] = delta_R**. `M` must fluctuate; do not stop after reaching an exact revenue target.
4. Draw `M` user IDs from **B only**, with replacement, using an explicitly swappable selection function/module:
   - Default `activity_weighted`: `P(select user i) proportional to a_i ** exponent`, with `exponent = 1` by default. Inactive users with zero activity have zero probability under this default. This is intentional to avoid an unrealistic surge in previously inactive shoppers; report this modeling assumption.
   - Alternative `uniform`: every B user equally likely.
   - Reject or clearly handle a cohort with zero total activity.
   - Use **original activity**, not activity updated by synthetic purchases, so sampling probabilities do not drift while generating the treatment.
5. Independently draw `M` positive prices **with replacement from actual H&M transaction prices**. Do not fit a Cauchy distribution and do not multiply original prices by `(1 + delta)`.
6. Add synthetic amounts to the selected customers' original revenues (and optionally retain a compact synthetic transaction table for inspection).
7. Record realized `M`, synthetic revenue, realized uplift `synthetic_revenue / R_B`, and the distribution of synthetic purchases per customer. Delta controls the **expected** uplift, not a guaranteed realized uplift.

Keep customer-ID selection and price selection as separate interchangeable blocks. A later extension may condition prices on activity, but **do not implement that now**.

### 3. Compare bucket counts for the same generated treatment

For each repetition and each `delta`:

- Generate the synthetic B transactions **once**.
- Reuse the same A/B split and same generated revenues for `K = 100`, `1000`, and user-level (`K=0`). This is essential for an apples-to-apples comparison of aggregation effects.
- For each finite `K`, independently shuffle users within A and within B, partition into equal-size buckets, and **sum** revenue within each bucket (do not use means).
- Bucket labels in A and B are not paired observations. Run **unpaired** tests.
- Use a deterministic, documented RNG hierarchy so replications are reproducible but not identical.

### 4. Plot distributions and run the tests

For the baseline and **one representative repetition per positive delta**:

- Plot A/B revenue distributions for `K=100`, `K=1000`, and user-level. Use sensible axis scaling, common binning where feasible, and clear display of extreme values/zero mass; optionally use log1p for visualization only.
- Include summary statistics (mean, median, standard deviation, skew, zero fraction, sample size) for each group and K.
- Compute two-sided Welch's t-test and two-sided MWU p-values for each K. Report the sample sizes, test statistics, and p-values, not only significance flags.
- **Do not run Shapiro–Wilk or Q–Q plots** in this preliminary phase.
- Discuss whether bucket-level histograms look approximately normal, but **do not choose a test automatically based on a normality diagnostic**.
- Welch targets mean revenue difference under suitable independence/moment conditions; MWU is a rank-based comparison and is not generally a test of equal means. State this clearly in chart captions/README.

### 5. Repeat to estimate rejection frequencies

- Repeat Steps 2–4 **at least 10 times per positive delta** (default 20). Keep original A/B assignment fixed, but redraw `M`, synthetic customer IDs, synthetic prices, and bucket randomizations.
- Record one row per `(scenario, delta, repetition, K, test)` including p-value, rejection decision at `alpha`, mean revenue difference, expected and realized uplift, and `M`.
- Plot p-value against `K` for each delta and test (individual repetition points plus median or distribution), and **rejection fraction** against `K` for each delta and test.
- For positive delta, rejection fraction estimates **conditional empirical power** against the test's own null, conditional on this fixed A/B split. Its complement is the non-rejection fraction; explain that this is not a universal Type II error estimate for all possible A/B splits.
- With 10–20 repetitions, estimates are noisy. Show numerator/denominator and/or binomial uncertainty intervals and avoid over-interpreting small differences.

### 6. Proper Type I error calibration (separate from the fixed-split main experiment)

- Repeat the **untreated baseline** with **fresh randomized A/B splits** across simulations, each with no synthetic data, and repeat bucket assignment as specified above.
- For each test/K, report fraction of `p < alpha` with uncertainty intervals. This estimates false-positive behavior across randomized user populations.
- Keeping one single A/B split and merely reshuffling buckets does **not** provide an unconditional Type I error estimate, since any existing baseline imbalance persists. Label fixed-split baseline repetitions as a *diagnostic* rather than Type I error estimation.
- These fresh-split null repetitions may use a separate config setting (`null_repetitions`, default at least 100 if practical), distinct from the positive-delta repetitions.

## Statistical interpretation requirements

- The key comparison is **fixed total users**, changing only aggregation level; do not inadvertently shrink the population when increasing `K`.
- User observations are disjoint, but aggregation does not by itself establish independence if actual platform users interact. Here, the synthetic experiment assumes independent customer outcomes conditional on the empirical data-generating setup; state the limits.
- The induced treatment creates extra purchases for historically active B users. This is a simplified intervention, not an actual recommendation algorithm or real-world causal estimate from H&M.
- Small p-values do **not** imply a practically important effect. Provide a table showing relative mean revenue differences alongside p-values. Do not manufacture results or tune K to obtain a desired conclusion.
- Revenue distribution, especially at user level, may have many zeros; MWU and Welch can answer different questions and have different power. Do not conflate the results.
- Under the fixed baseline sample, random re-bucketing changes rank-test inputs; the aim is to measure this, not assume any direction of change.

## Outputs

Required files (names may be adapted but keep them discoverable):

- `conf.toml`: every operative parameter plus data/output paths.
- `README.md`: dataset acquisition, environment/setup, commands to reproduce, definition of `delta`, assumptions, and caveats.
- A small number of **Python scripts, not notebooks**: data preparation; swappable user-selection strategies; synthetic transaction generation; bucket aggregation and tests; experiment runner; plotting.
- `results/preliminary/summary.csv`: all p-values, uplift measurements and test statistics from all repetitions.
- `results/preliminary/`: labeled baseline and treated distribution plots, p-value-versus-K plots, rejection-rate-versus-K plots, and null-calibration results.
- A concise `results/preliminary/notes.md`: what actually happened, any surprising results, known limitations, and recommended next experiment. Never write hypothetical findings as observed ones.
- Tests for: equal bucket sizes; no overlap between A/B; only B receives synthetic revenue; actual target mean uplift in repeated draws approximately matches `delta`; fixed split across positive experiments; deterministic seeds; `K=0` handling; all config values actually used.

## Implementation priorities and guardrails

1. Inspect any existing repository and previous agent work. Reuse only correct and useful pieces; **replace** the old pipeline rather than layering a second competing design on top.
2. Implement data loading and one fixed A/B split; inspect baseline group balances.
3. Implement activity-weighted user sampling, empirical price sampling, and one single positive-delta run; test each part.
4. Produce distributions and both tests for baseline and one treated repetition across all K.
5. Only then add positive-delta repetitions and separate fresh-split null calibration.
6. Keep memory/runtime manageable: pre-aggregate originals once, retain numerical arrays of user revenue/activity, use vectorized sampling and `numpy.bincount` for bucket sums. Avoid copying millions of transaction rows every repetition.
7. Do not run a huge sweep until a minimal end-to-end pilot succeeds. Do not claim convergence or stable Type I/II estimates based on ten repetitions.
8. Use Python typing, small understandable functions, deterministic random generators, and clear error messages. Keep dependencies conventional (`numpy`, `pandas`, `scipy`, `matplotlib`, optional `pyarrow`).

**Success criterion for the first milestone:** With an available H&M dataset, one command produces baseline and positive-delta A/B bucket distributions, Welch/MWU p-values for all three K values, and a concise summary. Repeated simulations and power plots follow after inspection.
