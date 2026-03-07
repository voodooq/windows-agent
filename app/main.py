from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.runtime.agent_runtime import AgentRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows Agent CLI")
    parser.add_argument("goal", type=str, help="Natural language goal for the agent")
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

    console = Console()
    config = load_config(args.config)
    runtime = AgentRuntime(config)
    result = runtime.run(args.goal)
    console.print_json(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()