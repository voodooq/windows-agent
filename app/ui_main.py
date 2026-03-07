from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.main_window import run_sidebar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows Agent Sidebar UI")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to config yaml",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(run_sidebar(config_path=args.config))


if __name__ == "__main__":
    main()