# Choosing the Number of Buckets in Large-Scale A/B Testing

An AIPI 510 statistics project exploring how random bucket aggregation affects
hypothesis testing for highly skewed, zero-inflated customer revenue.

**Research question:** How should the number of buckets be chosen so that a
large-scale A/B test can reliably detect a target revenue uplift?

The pipeline compares the Mann–Whitney U test and Welch's t-test across bucket
counts, checks false-positive rates under the null, injects controlled
synthetic treatment effects, and estimates the minimum detectable effect (MDE)
at a target statistical power.

## Approach

1. **Prepare the baseline.** Aggregate transactions into each customer's
   total revenue within a configured date window, retaining zero-spending
   customers, and randomly assign customers to control A or treatment B.
2. **Bucket the customers.** Shuffle customers independently within each arm.
   Partition each arm into K balanced buckets and sum revenue per bucket.
   K equal to the arm size represents the original user level.
3. **Check distribution shape.** Compare skewness, zero shares, and normality
   diagnostics across levels of aggregation.
4. **Calibrate the tests.** Perform repeated A/A splits with no intervention.
   Record how often each test incorrectly rejects the null at alpha = 0.05.
5. **Simulate treatment.** Add synthetic purchases to B only. The expected
   additional revenue is delta times B's baseline total revenue. The number of
   purchases follows a Poisson model; purchase prices are sampled from the
   observed price distribution. Customer selection can be uniform or
   activity-weighted.
6. **Estimate power and MDE.** Repeat treated experiments for configured
   uplifts. Power is the fraction of runs with p < alpha. Interpolate the
   smallest uplift reaching the configured power target (typically 80%).

Welch's t-test is evaluated on bucket sums only in the current research
protocol; Mann–Whitney U is evaluated at every aggregation level.

## Data

The intended baseline source is the Kaggle
[H&M Personalized Fashion Recommendations dataset](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data).
For a real-data run, place the following files in the **data/** directory:

- **customers.csv** with a customer_id column.
- **transactions_train.csv** with t_dat, customer_id, and price columns.

The data loader filters the observation period, removes non-positive or
missing prices, samples up to the configured number of eligible customers,
and includes customers with zero revenue.

**Important:** If either input file is missing, the current loader
automatically generates an H&M-like **synthetic baseline fixture**. Check
your input files before interpreting a run as a real-data experiment.
Synthetic treatment purchases are a separate, intentional part of the
experiment regardless of whether the baseline is real or synthetic.

## Setup

Python 3.10 is recommended for the pinned dependencies. From the repository root:

~~~bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests/ -v
~~~

On Windows, the commands above work in WSL Ubuntu. In PowerShell, activate
the virtual environment with .venv\Scripts\Activate.ps1 instead.

## Run the experiment

The main configuration is **conf.toml**. It controls the observation window,
number of customers, bucket counts, treatment strategy, uplift grid, random
seed, null/alternative repetitions, significance threshold, and output paths.

**Recommended: run a smoke test without replacing committed results.**

1. Copy conf.toml to conf.local.toml.
2. In the local copy, set these output paths:

~~~toml
[output]
results_dir = "local_results"
plots_dir = "local_results/plots"
tables_dir = "local_results/tables"
report_path = "local_result.md"
~~~

3. Run the reduced experiment:

~~~bash
python run_pipeline.py --config conf.local.toml --smoke-test
~~~

The smoke test temporarily uses 2,000 customers, fewer bucket counts, and
fewer repetitions. It is a functionality check, **not** a source of final
power estimates.

For a complete run with outputs stored under the same local paths:

~~~bash
python run_pipeline.py --config conf.local.toml
~~~

To regenerate the repository's standard outputs, run
**python run_pipeline.py** with the default config. **This overwrites**
the tracked result.md and existing results/tables and results/plots files.
Review the generated changes carefully before committing them.

## Outputs

| Output | Description |
| --- | --- |
| Table 1 / Figure 1 | Customer-revenue summary and distribution |
| Table 2 / Figure 2 | Bucket-size, skewness, and normality diagnostics |
| Table 3 / Figure 3 | Null false-positive rates with 95% Wilson intervals |
| Table 4 / Figures 4 and 4b | One treated run, distributions, and p-values |
| Table 5 / Figures 5 and 6 | Empirical power and p-values across uplifts |
| Table 6 / Figure 7 | Interpolated MDE and power curves with uncertainty bands |
| result.md | Generated Markdown results report |

### How to read the uncertainty estimates

Power and null false-positive rates are proportions: k rejections in n
simulations. The tables report k, n, the observed proportion k/n, and a
**95% Wilson score confidence interval** for that proportion. Figures 3, 5,
and 7 visualize these bounds.

For example, 18 significant results in 20 repetitions gives a 90% observed
rejection rate, but its Wilson interval is approximately **70%–97%**.
Even 20 of 20 rejections has a lower confidence bound of about **84%**.
The intervals make it easier to distinguish a point estimate from the
precision of that estimate.

These intervals describe finite-repetition uncertainty **conditional on the
experiment's simulation setup**. In particular, the alternative simulations
keep the original A/B split fixed and regenerate treatment purchases and
bucket assignments. The intervals do not cover variability across fresh
randomized splits, different populations, or alternative treatment models.
The interpolated MDE also has no separate confidence interval.

## Repository structure

| Path | Responsibility |
| --- | --- |
| conf.toml | Experiment settings |
| src/data_loader.py | Data preparation and A/B cohorts |
| src/bucketing.py | Bucket aggregation, diagnostics, null tests |
| src/treatment.py | Synthetic treatment generation |
| src/simulation.py | Power simulations, figures, MDE |
| src/uncertainty.py | Wilson score confidence interval utility |
| src/plots.py | Legacy plotting helpers that reuse the interval utility |
| run_pipeline.py | End-to-end orchestration and report generation |
| tests/test_pipeline.py | Regression and statistical utility tests |
| results/ | Published figures and tables |
| pipeline.md | Project design and research requirements |
| result.md | Generated research report |

## Main limitations

- The simulated purchases are a simplified treatment model, not observed
  customer responses to a real intervention.
- Alternative repetitions reuse a fixed A/B split, so reported power is
  conditional on that split.
- Twenty alternative repetitions and fifty null repetitions provide fairly
  wide uncertainty intervals. More repetitions improve precision.
- MDE is interpolated from a discrete uplift grid rather than estimated
  from a continuous search with uncertainty bounds.

## Reproducibility

All main experiment settings live in **conf.toml**, including the random seed.
Keep a copy of the exact configuration and record which baseline dataset was
used for any results you report. The CSV tables make it possible to check
individual numerical results independently of the plots.
