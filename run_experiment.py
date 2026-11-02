"""CLI redirect wrapper to run_pipeline.py for backwards compatibility."""

import sys
from run_pipeline import run_all

if __name__ == "__main__":
    smoke = "--smoke-test" in sys.argv
    config = "conf.toml"
    if "--config" in sys.argv:
        idx = sys.argv.index("--config")
        if idx + 1 < len(sys.argv):
            config = sys.argv[idx + 1]
    run_all(config_path=config, smoke_test=smoke)
