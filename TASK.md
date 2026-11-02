# AIPI 510 Module Project 2 — Task for Antigravity Agent

## Project title
**Statistical vs. Practical Significance in Large-Scale A/B Testing: Does User Bucketing Change Statistical Power?**

## Objective
Build a fully reproducible, script-based statistical study using **real customer-spending distributions** from the public **H&M Personalized Fashion Recommendations** dataset and **synthetic randomized A/B treatments**. Investigate how total sample size and the number of random user buckets affect hypothesis-test rejection rates, statistical power, and minimum detectable effect (MDE). Contrast statistical significance with a prespecified economically meaningful uplift.

This is a **Monte Carlo simulation calibrated to observational retail data**, **not** a real H&M A/B test. Never describe synthetic treatment assignments or treatment effects as observed H&M experiments.

**Primary research question:**
> Holding the total number of randomized customers and the true revenue effect fixed, does aggregating customers into different numbers of equally sized random buckets change the operating characteristics (Type I error, power, and MDE) of bucket-level Mann–Whitney U and Welch tests compared with a user-level Welch test?

**Secondary research question:**
> At large sample sizes, how often can a statistically detectable revenue difference fail to satisfy a prespecified minimum practically important uplift?

## Scientific hypotheses and key caveats
1. **Sample size:** For a fixed nonzero effect and valid procedure, statistical power generally increases with customer sample size.
2. **Bucket count:** Under independent user outcomes and equal-size buckets, a bucket-level test of **means** should retain nearly the same information about the difference in mean revenue as a user-level test (with finite-sample effects at small bucket counts). It is an empirical question how the bucket-level **Mann–Whitney U** test behaves as bucket count changes. **Do not assume or manufacture a monotonic relationship** between bucket count and power/MDE.
3. **Practical significance:** Rejecting a zero-effect null does not imply that an improvement meets a business threshold.
4. **Correct test interpretations:** Welch tests differences in means; Mann–Whitney compares relative ranks/distributions and is **not generally a test of equality of mean revenue**. Under distributional differences, these tests may be detecting different estimands. Make this explicit in the report.
5. **Bucketing does not automatically produce independent replicas of a single global optimization system**. This simulation assumes independently generated or sampled customer outcomes and independent, noninterfering treatment responses; results do not prove validity in production ads systems with shared budgets or spillovers.

## Dataset and access
- H&M Personalized Fashion Recommendations, Kaggle: https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data
- Relevant files: `transactions_train.csv` (`customer_id`, `t_dat`, `price`) and `customers.csv` (`customer_id`). Product images and article metadata are **not required**.
- Treat `price` as the dataset's recorded/normalized price field; **do not call it USD revenue** or assume absolute currency comparability. Relative spending measures remain useful.
- Dataset may require Kaggle account/competition rule acceptance. **Do not hard-code credentials or commit raw large files**. Provide a clear manual download instruction and a useful small synthetic-data smoke-test mode that runs without Kaggle access.
- Confirm real schema before processing. Document customer coverage and the number of zero-spend customers.
- Choose one fixed observation window (e.g. final 8–12 weeks of available transactions; document actual dates) and compute **one sum of purchase prices per customer**. Left-join onto a customer universe that includes customers with no transactions in the window and fill spending with zero. Avoid including non-customer rows or treating transactions as independent experimental units.
- Acknowledge that purchase transactions alone do not give a complete picture of visits, exposures, or causal processes. Analyze customer spending in the selected window only.
- Scale using streaming/chunked CSV processing or efficient columnar operations; avoid loading unused data/images.

## Experimental design
The **customer** is the independent unit in the simulation; a bucket is a random grouping of customers, not an independently budgeted marketplace.

For each Monte Carlo repetition:
1. Draw **disjoint customer sets** for arms A and B from an empirical customer-spending population, with equal numbers of customers per arm. Prefer sampling *without replacement within each repetition*; repetitions can resample the same empirical population. Ensure adequate population size or explicitly implement/document resampling rules.
2. Generate the **known synthetic treatment effect** for arm B. Begin with a simple, transparent spending-multiplier model, `y_B = (1 + delta) * y_B_baseline` (including zeros). This targets a relative mean-spending effect, but is not a realistic conversion-lift mechanism. Optionally add one clearly labeled robustness scenario: treatment increases the probability of a purchase and/or average purchase amount via an explicit stochastic process. Do not overextend before core analysis works.
3. Compute user-level spending for both arms. For each bucket count K, independently/randomly shuffle users within each arm, partition into **equal-sized buckets**, and compute **sum of spending per bucket**. Choose user counts divisible by K, or document balanced remainder-handling and use per-user bucket means/normalization so different bucket sizes do not confound rank tests. Prefer strictly equal bucket sizes in the primary experiment.
4. Run three **two-sided** tests at alpha = 0.05:
   - User-level Welch t-test on individual customer spending.
   - Bucket-level Welch t-test on bucket **sums** (equal bucket sizes).
   - Bucket-level Mann–Whitney U on bucket **sums** (two independent arm samples). Use a documented tie handling / `method` choice.
5. For each test calculate p-value and rejection indicator. Also record the **mean-spending uplift** `(mean_B / mean_A - 1)` when denominator > 0, the absolute mean difference, and a confidence interval for the mean difference (at least for Welch comparisons). Treat MWU conclusions as distributional/rank conclusions, not effect-size estimates of mean revenue.
6. Re-run the entire experiment for independent Monte Carlo random seeds. **Do not count simulated repetitions as additional customers in a single hypothesis test.** Use repetitions to estimate a test's operating characteristics.

**Baseline parameter grid (adjust for available time/compute, recording changes):**
- Customers per arm: `n = [10_000, 50_000, 100_000, 500_000]` (only values feasible for available customer universe; never silently exceed it).
- Buckets per arm: `K = [10, 20, 50, 100, 200, 500]`, restricted to `K <= n` and equal-size grouping.
- True relative uplift: `delta = [0.0, 0.001, 0.005, 0.01, 0.02]` (0%, 0.1%, 0.5%, 1%, 2%).
- Initial repetitions: 100 for a pilot; target >= 500 for selected main configurations if affordable. Report Monte Carlo uncertainty. Focus on fewer well-powered configurations rather than an uncompleted giant grid.
- Practical importance threshold: predeclare **1% revenue uplift** as an *illustrative assumed business rule*, not a fact about H&M.

**Efficiency and validity details:**
- Under `delta=0`, control false-positive rate should be approximately `alpha` for correctly calibrated tests; estimate a Wilson/binomial CI for rejection rates. If calibration is off, investigate before comparing power curves.
- Calculate empirical power as `rejections / repetitions` at nonzero delta; use binomial confidence intervals for Monte Carlo power estimates.
- Estimate an **80%-power MDE** separately by test, sample size, and K. Use a sufficiently fine or adaptive effect grid around the crossing. If 80% is never reached, report MDE as outside studied range; do not extrapolate unjustifiably. Because the grid and Monte Carlo estimates are noisy, report uncertainty/precision and interpret cautiously.
- Use common random numbers across test comparisons where convenient (same simulated A/B sample evaluated by every test and K); this improves fairness of method comparison. Do not inadvertently change underlying user samples while attributing results solely to K.
- Avoid data snooping: choose alpha, power target, primary endpoints, K values, and practical threshold before inspecting main results. Keep exploratory variants labeled as such.
- If user-level t-test on all observations is computationally expensive, record performance and optimize without changing statistical meaning. Sampling fixed data repeatedly creates **conditional** simulation results relative to the H&M empirical distribution, not population-wide causal evidence.
- Do not confuse a small p-value with a small effect, and **do not set K by searching for a desired p-value**.

## Power analysis requirement
Provide an **a priori** benchmark using `statsmodels.stats.power.TTestIndPower` for a two-sample mean test, based on customer-spending SD and a stated meaningful mean difference (e.g. 1% of average spending), plus an explanation of how heavily skewed spending, treatment design, and bucket-level rank testing motivate **simulation-based** power estimates.

Report standardized effect, alpha, target power (80%), allocation ratio, estimated required sample size, and limitations of the approximation. Compare approximate analytical power with empirical Monte Carlo power, without treating them as identical.

## Analyses and visualizations (priority order)
1. **Data characterization:** spending distribution (including zero fraction, median, mean, upper quantiles, and outliers), sample counts, chosen observation window.
2. **Type I error check:** empirical rejection rate vs K at `delta=0`, with uncertainty bands and a 5% reference line.
3. **Power vs sample size:** fixed small treatment effects, one curve per test; include confidence bands or error bars.
4. **Power vs K:** for fixed n and delta, bucket-level Welch vs Mann–Whitney; show user-level Welch as a K-invariant reference. Include error bars.
5. **80% MDE vs K:** clearly label any estimated/undetermined values and simulation error.
6. **Significance vs practical importance:** show examples or a plot where p < 0.05 but uplift < 1%; additionally classify intervals into (a) evidence of positive effect, (b) evidence effect exceeds 1% if its lower CI bound > 1%, and (c) inconclusive. Do not equate point estimate > 1% with convincing evidence of meeting the threshold.
7. Optional sensitivity analysis: re-run with a more realistic conversion/zero-inflation treatment mechanism and compare conclusions.

## Repository deliverables
Use Python **scripts, not notebooks**, with a simple, maintainable structure (adapt if justified):

```
README.md
TASK.md                 # this specification (or task.md)
requirements.txt        # or pyproject.toml with lock info
.gitignore
src/
  prepare_data.py
  simulate.py
  analyze.py
  plots.py
  power_analysis.py
  utils.py              # only if genuinely shared logic is needed
configs/
  default.yaml          # or a simple JSON/config file
scripts/
  smoke_test.sh         # optional
results/
  summary.csv
  figures/              # generated, small output files
report/
  report.md             # report draft with tables and figure references
```

- Avoid overengineering; prefer simple explicit functions, type hints, deterministic seeds, and short readable modules.
- Store big Kaggle files under `data/raw/` and derived customer data under `data/processed/` (gitignored). Document raw/cleaned data provenance and reproduction, or include a tiny synthetic sample and its generation script.
- README: setup, data acquisition, preprocessing, commands for a quick smoke test and full run, expected outputs, seed policy, computational requirements, and limitations.
- Include data-cleaning summary and QA checks: unique customers after aggregation, no unexpected NaNs/negative values, counts, same users not in both arms within a repetition, equal bucket sizes, finite test outputs.
- Tests (pytest or lightweight asserts) for: zero-effect generation, bucket partitioning and exact sum preservation, test behavior on synthetic inputs, reproducibility with fixed seeds, and safe treatment of zero means.
- Keep reproducible outputs as CSV/PNG/SVG; figure scripts must read saved results rather than manually embed values.
- Git collaboration requirement: ensure both teammates contribute through separate branches and at least one reviewed PR each. Do not impersonate teammates or claim PRs occurred without evidence.

## Written report (course-required sections)
- Title and abstract; background/motivation; research question and precise null/alternative hypotheses.
- Experimental design: variables, independent unit, treatment simulation, randomization, control, dataset and preprocessing.
- A priori power analysis (assumptions and software) and Monte Carlo power/MDE design.
- Statistical tests and justified assumptions; p-values, confidence intervals, meaningful effect sizes.
- Results with properly labeled simulation results (not observed H&M causal effects).
- Practical significance decisions; limitations; conclusion/recommendations; references.

## Presentation (8 minutes maximum)
Tell one coherent story: **Why do large experiments find tiny p-values? → Can bucketing change sensitivity? → Which tests answer which question? → What effect would actually matter to a business?** Emphasize 3–4 interpretable plots, uncertainty, and a concise takeaway rather than implementation details.

## Implementation stages / working rules
Work incrementally. At the end of each stage, report files created/changed, exact commands run, tests passed/failed, and immediate next step. Do not invent results.

1. **Scaffold and confirm data access:** inspect working directory and any provided files; create minimal project skeleton and configuration. If H&M data are absent, implement a clearly labeled synthetic smoke-test dataset, explain Kaggle download steps, and keep the real-data path ready. Do not silently substitute synthetic data for final results.
2. **Data preparation:** efficient customer-level aggregation, validation, distribution summary, and smoke test.
3. **Simulation engine:** deterministic randomized disjoint arm assignments, synthetic uplift, exact balanced buckets, and three test procedures. Include focused unit tests.
4. **Pilot and power planning:** check run time, Type I error and power behavior; calibrate a feasible grid, analytically justify sample size, and document any changes.
5. **Main study:** run reproducible experiments, record complete configuration/seeds, save result tables with binomial uncertainty intervals.
6. **Figures and report:** plot only computed results; write the course-required report and an 8-minute presentation outline. Include candid limitations and conclusions grounded in observed simulations.

## Acceptance criteria
- A reviewer can reproduce a smoke test without Kaggle access and the real-data study once raw files are downloaded.
- The statistical unit and simulated treatment are clearly identified; disjoint randomized arm assignment and fixed customer-level outcome definitions are correct.
- Every reported statistical claim has a generated result, and no figures are presented as observed data unless actually computed.
- At least the three planned tests, null calibration, power estimates with uncertainty, one a priori power calculation, and a practical-significance comparison are delivered.
- The report explicitly explains **why changing K should not be presumed to change Welch's mean-test power dramatically** and why Mann–Whitney may respond differently.
- Repo supports two-person PR workflow, scripts-only analysis, and a concise reproducibility README.
