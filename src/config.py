"""Configuration loader and validator for AIPI 510 Project Pipeline.

Parses conf.toml according to pipeline.md specification.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class DataConfig:
    transactions_path: str
    customers_path: str
    observation_start: str
    observation_end: str
    max_users: int
    include_zero_revenue_users: bool


@dataclass
class ABConfig:
    control_share: float
    keep_ab_split_fixed: bool


@dataclass
class BucketsConfig:
    counts: List[int]
    include_user_level: bool
    shuffle_within_group: bool


@dataclass
class TreatmentConfig:
    enabled: bool
    selection_strategy: str
    activity_smoothing_epsilon: float
    price_sampling: str
    condition_on_activity: bool
    uplifts: List[float]
    m_count_model: str


@dataclass
class SimulationConfig:
    null_repetitions: int
    alt_repetitions: int
    significance_level: float
    power_target: float
    mde_targets: List[float]


@dataclass
class OutputConfig:
    results_dir: str
    plots_dir: str
    tables_dir: str
    report_path: str


@dataclass
class PipelineConfig:
    random_seed: int
    data: DataConfig
    ab: ABConfig
    buckets: BucketsConfig
    treatment: TreatmentConfig
    simulation: SimulationConfig
    output: OutputConfig
    raw_dict: Dict[str, Any] = field(default_factory=dict)


def load_pipeline_config(config_path: str = "conf.toml") -> PipelineConfig:
    """Load and validate pipeline configuration from conf.toml."""
    p = Path(config_path)
    if not p.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(p, "rb") as f:
        cfg = tomllib.load(f)

    d = cfg.get("data", {})
    ab = cfg.get("ab", {})
    b = cfg.get("buckets", {})
    t = cfg.get("treatment", {})
    s = cfg.get("simulation", {})
    o = cfg.get("output", {})

    data_cfg = DataConfig(
        transactions_path=str(d.get("transactions_path", "data/transactions_train.csv")),
        customers_path=str(d.get("customers_path", "data/customers.csv")),
        observation_start=str(d.get("observation_start", "2019-09-01")),
        observation_end=str(d.get("observation_end", "2019-09-30")),
        max_users=int(d.get("max_users", 20000)),
        include_zero_revenue_users=bool(d.get("include_zero_revenue_users", True)),
    )

    ab_cfg = ABConfig(
        control_share=float(ab.get("control_share", 0.5)),
        keep_ab_split_fixed=bool(ab.get("keep_ab_split_fixed", True)),
    )

    bucket_counts = [int(k) for k in b.get("counts", [100, 1000])]
    buckets_cfg = BucketsConfig(
        counts=bucket_counts,
        include_user_level=bool(b.get("include_user_level", True)),
        shuffle_within_group=bool(b.get("shuffle_within_group", True)),
    )

    treatment_cfg = TreatmentConfig(
        enabled=bool(t.get("enabled", True)),
        selection_strategy=str(t.get("selection_strategy", "activity_weighted")),
        activity_smoothing_epsilon=float(t.get("activity_smoothing_epsilon", 0.01)),
        price_sampling=str(t.get("price_sampling", "empirical")),
        condition_on_activity=bool(t.get("condition_on_activity", False)),
        uplifts=[float(u) for u in t.get("uplifts", [0.001, 0.005, 0.01, 0.02, 0.05, 0.10])],
        m_count_model=str(t.get("m_count_model", "poisson")),
    )

    sim_cfg = SimulationConfig(
        null_repetitions=int(s.get("null_repetitions", 50)),
        alt_repetitions=int(s.get("alt_repetitions", 20)),
        significance_level=float(s.get("significance_level", 0.05)),
        power_target=float(s.get("power_target", 0.80)),
        mde_targets=[float(m) for m in s.get("mde_targets", [0.005, 0.01, 0.02, 0.05])],
    )

    output_cfg = OutputConfig(
        results_dir=str(o.get("results_dir", "results")),
        plots_dir=str(o.get("plots_dir", "results/plots")),
        tables_dir=str(o.get("tables_dir", "results/tables")),
        report_path=str(o.get("report_path", "result.md")),
    )

    return PipelineConfig(
        random_seed=int(cfg.get("random_seed", 42)),
        data=data_cfg,
        ab=ab_cfg,
        buckets=buckets_cfg,
        treatment=treatment_cfg,
        simulation=sim_cfg,
        output=output_cfg,
        raw_dict=cfg,
    )
