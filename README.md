# Statistical vs. Practical Significance in Large-Scale A/B Testing: Does User Bucketing Change Statistical Power?

AIPI 510 Module Project 2

## Project Overview

This study investigates how customer sample size ($n$) and random user bucketing ($K$ buckets) affect the operating characteristics (Type I error rate, statistical power, and Minimum Detectable Effect / MDE) of A/B hypothesis tests under highly skewed, zero-inflated retail customer spending distributions. 

We contrast:
1. **User-level Welch's t-test**: Standard parametric test comparing individual customer spending means.
2. **Bucket-level Welch's t-test**: Parametric test comparing bucket sums (under equal-sized user buckets).
3. **Bucket-level Mann–Whitney U test**: Non-parametric rank-sum test comparing bucket sums.

Crucially, the study also contrasts **statistical significance** ($p < 0.05$) with **practical significance** (a prespecified illustrative $+1\%$ revenue uplift threshold).

> [!NOTE]
> This study is a **Monte Carlo simulation calibrated to observational retail distributions** (or synthetic benchmark distributions). Treatment assignments and treatment uplifts are simulated under controlled, known data-generating processes. They do not represent real A/B experiments performed by H&M.

---

## Repository Structure

```
├── README.md                      # Project documentation and reproduction guide
├── TASK.md                        # Project specification and requirements
├── requirements.txt               # Pinned Python package dependencies
├── .gitignore                     # Git ignore rules (prevents tracking raw data/.venv)
├── configs/
│   └── default.yaml               # Experiment and parameter configuration
├── data/
│   ├── raw/                       # Place raw Kaggle H&M files here (gitignored)
│   └── processed/                 # Processed customer spending distributions
├── src/
│   ├── utils.py                   # Config loading, seed management, Wilson score CIs
│   ├── prepare_data.py            # Data preprocessing & synthetic smoke data generation
│   ├── simulate.py                # Monte Carlo A/B simulation engine (Stage 3)
│   ├── analyze.py                 # Results analysis and metric aggregation
│   ├── plots.py                   # Plotting routines for figures
│   └── power_analysis.py          # A priori analytical & empirical power calculations
├── scripts/
│   └── smoke_test.sh              # Fast end-to-end verification script
├── tests/
│   └── test_stage1_scaffold.py    # Unit tests for Stage 1 scaffold and data generation
├── results/
│   ├── summary.csv                # Tabular Monte Carlo simulation outputs
│   └── figures/                   # Rendered publication-ready figures
└── report/
    └── report.md                  # Comprehensive written report
```

---

## Setup & Environment

### 1. Requirements
- Python 3.8+ (tested on Python 3.8.16)
- Linux / macOS / Windows

### 2. Virtual Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Install dependencies using pinned requirements
.venv/bin/pip install -r requirements.txt
```

---

## Data Acquisition & Preprocessing

The primary empirical data source is the public Kaggle competition dataset:
[H&M Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data).

### Raw Files Required
Only two files are needed (product images and article metadata are **not** needed):
1. `transactions_train.csv` (columns: `t_dat`, `customer_id`, `article_id`, `price`, `sales_channel_id`)
2. `customers.csv` (columns: `customer_id`, ...)

Place both files under `data/raw/`:
```bash
mkdir -p data/raw
# Download via Kaggle CLI:
# kaggle competitions download -c h-and-m-personalized-fashion-recommendations -f transactions_train.csv -p data/raw/
# kaggle competitions download -c h-and-m-personalized-fashion-recommendations -f customers.csv -p data/raw/
# Unzip files:
# unzip data/raw/transactions_train.csv.zip -d data/raw/
# unzip data/raw/customers.csv.zip -d data/raw/
```

### Preprocessing Logic
- **Observation Window**: The final 10 weeks of recorded transactions (2020-07-15 to 2020-09-22).
- **Aggregation**: Streaming aggregation of transaction `price` per `customer_id`.
- **Customer Universe**: Left-joined onto the full `customers.csv` list so that inactive customers are retained with `spending = 0.0`.
- **Hygiene & QA**: Validated for zero NaNs, non-negative spending, and strictly unique customer IDs.

To process real data:
```bash
.venv/bin/python src/prepare_data.py --real
```

### Synthetic Smoke-Test Mode (No Kaggle Access Required)
If the raw dataset is not yet downloaded, you can run a zero-dependency synthetic smoke test that generates a realistic zero-inflated, right-skewed spending distribution:
```bash
.venv/bin/python src/prepare_data.py --smoke
```
Or execute the automated test suite and smoke test script:
```bash
./scripts/smoke_test.sh
```

---

## Reproducibility & Seed Policy

All stochastic elements (synthetic customer generation, Monte Carlo arm sampling, customer shuffling, and bucket assignment) use explicit, reproducible pseudorandom seeds managed via `numpy.random.default_rng` initialized from `configs/default.yaml` (`seed: 42`).
