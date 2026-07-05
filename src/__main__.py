import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Detect mode from args
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["daily","weekly"], default="daily")
args = parser.parse_args()

from src.main import run_daily, run_weekly, load_config
config = load_config()
if args.mode == "daily":
    run_daily(config)
else:
    run_weekly(config)
