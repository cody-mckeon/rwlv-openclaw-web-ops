import json
import tempfile
from pathlib import Path

from shared.telegram_intents import TelegramIntent, route_telegram_intent
from shared.telegram_operations import (
    FALLBACK_RESPONSE,
    dispatch_telegram_operational_request,
    process_telegram_operational_message,
)


def test_slash_commands_still_route_to_deterministic_handlers():
    assert route_telegram_intent("/status").intent == TelegramIntent.STATUS
    assert route_telegram_intent("/blocked please").intent == TelegramIntent.BLOCKED
    assert route_telegram_intent("/governance").intent == TelegramIntent.GOVERNANCE
    assert route_telegram_intent("/summary").intent == TelegramIntent.SUMMARY
    assert route_telegram_intent("/help").intent == TelegramIntent.HELP


def test_natural_language_phrases_route_to_expected_intents():
    examples = {
        "what is blocked?": TelegramIntent.BLOCKED,
        "what should I follow up on?": TelegramIntent.BLOCKED,
        "how are we doing today?": TelegramIntent.STATUS,
        "what is the state?": TelegramIntent.STATUS,
        "why are we overloaded?": TelegramIntent.GOVERNANCE,
        "what rules triggered?": TelegramIntent.GOVERNANCE,
        "what changed?": TelegramIntent.SUMMARY,
        "give me the summary": TelegramIntent.SUMMARY,
        "show me launch risks": TelegramIntent.LAUNCH_RISKS,
        "what can you do?": TelegramIntent.HELP,
    }

    for message, expected_intent in examples.items():
        route = route_telegram_intent(message)
        assert route.intent == expected_intent
        assert route.handler_name == expected_intent.value
        assert route.fallback is False


def test_unknown_phrases_fall_back_safely():
    route, response = dispatch_telegram_operational_request("tell me a joke about robots")

    assert route.intent == TelegramIntent.UNKNOWN
    assert route.fallback is True
    assert response == FALLBACK_RESPONSE


def test_routing_calls_only_selected_handler():
    calls = []

    def status_handler(runtime_cfg):
        calls.append("status")
        return "status response"

    def blocked_handler(runtime_cfg):
        calls.append("blocked")
        return "blocked response"

    route, response = dispatch_telegram_operational_request(
        "what is blocked?",
        handlers={
            TelegramIntent.STATUS: status_handler,
            TelegramIntent.BLOCKED: blocked_handler,
        },
    )

    assert route.intent == TelegramIntent.BLOCKED
    assert response == "blocked response"
    assert calls == ["blocked"]


def test_process_logs_message_route_fallback_and_delivery_events():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "telegram.jsonl"
        response = process_telegram_operational_message(
            "unrecognized operational question",
            runtime_cfg={},
            log_file=log_file,
        )

        assert response == FALLBACK_RESPONSE
        events = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
        assert [event["event_type"] for event in events] == [
            "telegram_message_received",
            "telegram_intent_routed",
            "telegram_fallback_triggered",
            "telegram_response_delivered",
        ]
        assert events[0]["raw_message"] == "unrecognized operational question"
        assert events[1]["detected_intent"] == "unknown"
        assert events[1]["fallback_triggered"] is True


def test_blocked_handler_uses_generated_priorities_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        snapshots = root / "snapshots"
        snapshot = snapshots / "2026-05-28"
        snapshot.mkdir(parents=True)
        (snapshot / "CURRENT_PRIORITIES.generated.md").write_text(
            "## Blocked / Waiting / At Risk\n"
            "- Waiting on vendor copy | Assignee: Cody | Due: No due date | Section: QA\n"
            "\n## Intake\n- New request | Assignee: Cody\n",
            encoding="utf-8",
        )
        runtime_cfg = {"paths": {"snapshots_dir": str(snapshots)}}

        route, response = dispatch_telegram_operational_request("what should I follow up on?", runtime_cfg=runtime_cfg)

        assert route.intent == TelegramIntent.BLOCKED
        assert "Waiting on vendor copy" in response
        assert "Basis: generated CURRENT_PRIORITIES artifact." in response
