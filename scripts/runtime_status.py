from __future__ import annotations

from shared.config.runtime import load_dotenv, load_runtime_config
from shared.runtime_health import evaluate_runtime_health


def main() -> None:
    load_dotenv()
    config = load_runtime_config()
    statuses = evaluate_runtime_health(
        config,
        required_env=["ASANA_ACCESS_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
    )

    print("## Runtime Status\n")
    for name, ok, _detail in statuses:
        state = "OK" if ok else "FAIL"
        print(f"{name}: {state}")


if __name__ == "__main__":
    main()
