from __future__ import annotations

import argparse

from shared.config.runtime import load_dotenv, load_runtime_config
from shared.telegram_operations import process_telegram_operational_message


def main() -> None:
    parser = argparse.ArgumentParser(description="Route a Telegram operational request deterministically.")
    parser.add_argument("message", nargs="+", help="Raw Telegram message text to route.")
    args = parser.parse_args()

    load_dotenv()
    config = load_runtime_config()
    runtime_cfg = config.get("runtime", {}) if isinstance(config, dict) else {}
    print(process_telegram_operational_message(" ".join(args.message), runtime_cfg))


if __name__ == "__main__":
    main()
