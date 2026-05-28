from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from scripts.send_priority_digest import extract_section, fallback_if_empty, format_section
from shared.governance import derive_escalation_routing, evaluate_escalation, evaluate_governance
from shared.logging.runtime_logger import log_event
from shared.telegram_intents import IntentRoute, TelegramIntent, route_telegram_intent
from shared.telemetry import resolve_latest_priorities_file

FALLBACK_RESPONSE = (
    "I can help with status, blocked work, governance, summary, or launch risks. "
    "Try asking: 'what is blocked?' or 'how are we doing today?'"
)

HELP_RESPONSE = "\n".join(
    [
        "ForgePod operational retrieval understands natural language questions and slash commands.",
        "Ask things like:",
        "- what is blocked?",
        "- how are we doing today?",
        "- why are we overloaded?",
        "- show me launch risks",
        "- what changed?",
        "Slash commands also work: /status, /blocked, /governance, /summary, /help.",
    ]
)

Handler = Callable[[Mapping[str, Any]], str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _paths(runtime_cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return runtime_cfg.get("paths", {}) if isinstance(runtime_cfg, Mapping) else {}


def _telemetry_dir(runtime_cfg: Mapping[str, Any]) -> Path:
    return Path(str(_paths(runtime_cfg).get("telemetry_dir", "generated/telemetry")))


def _runtime_log_file(runtime_cfg: Mapping[str, Any]) -> Path:
    paths = _paths(runtime_cfg)
    logs_dir = Path(str(paths.get("logs_dir", "generated/logs")))
    return logs_dir / "telegram_operational_interface.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        payload = json.loads(raw)
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _latest_metrics(runtime_cfg: Mapping[str, Any]) -> dict[str, Any] | None:
    entries = _read_jsonl(_telemetry_dir(runtime_cfg) / "daily_operational_metrics.jsonl")
    return entries[-1] if entries else None


def _metrics_history(runtime_cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _read_jsonl(_telemetry_dir(runtime_cfg) / "daily_operational_metrics.jsonl")


def _read_latest_priorities(runtime_cfg: Mapping[str, Any]) -> str | None:
    priorities_path = resolve_latest_priorities_file(dict(runtime_cfg))
    if priorities_path.exists():
        return priorities_path.read_text(encoding="utf-8")
    return None


def _format_metrics(metrics: Mapping[str, Any]) -> list[str]:
    keys = [
        ("open_task_count", "Open tasks"),
        ("blocked_count", "Blocked / waiting / at risk"),
        ("p0_count", "P0 interrupts"),
        ("in_progress_count", "In progress"),
        ("qa_count", "QA queue"),
        ("intake_count", "Intake queue"),
        ("scheduled_launch_count", "Scheduled / ready to launch"),
        ("contradiction_count", "Contradictions"),
        ("launch_risk_count", "Launch risks"),
    ]
    return [f"- {label}: {int(metrics.get(key, 0) or 0)}" for key, label in keys if key in metrics]


def handle_status(runtime_cfg: Mapping[str, Any]) -> str:
    metrics = _latest_metrics(runtime_cfg)
    if not metrics:
        return "Status unavailable: no telemetry metrics artifact found. Run the operational telemetry job first."

    governance = evaluate_governance(metrics)
    lines = [
        "Operational Status",
        f"Snapshot: {metrics.get('snapshot_date', 'unknown')}",
        f"Governance State: {governance.governance_state}",
        f"Execution Pressure: {governance.execution_pressure}",
        "Metrics:",
        *_format_metrics(metrics),
        "Basis: generated telemetry metrics and deterministic governance rules.",
    ]
    return "\n".join(lines)


def handle_blocked(runtime_cfg: Mapping[str, Any]) -> str:
    markdown = _read_latest_priorities(runtime_cfg)
    if not markdown:
        return "Blocked work unavailable: no generated priority snapshot found. Run the priority generator first."

    blocked = fallback_if_empty(extract_section(markdown, "Blocked / Waiting / At Risk", max_items=10))
    return "\n".join(
        [
            "Blocked / Waiting / At Risk",
            format_section("Current deterministic snapshot", blocked),
            "Basis: generated CURRENT_PRIORITIES artifact.",
        ]
    )


def handle_governance(runtime_cfg: Mapping[str, Any]) -> str:
    history = _metrics_history(runtime_cfg)
    if not history:
        return "Governance unavailable: no telemetry metrics artifact found. Run the operational telemetry job first."

    current = history[-1]
    governance = evaluate_governance(current)
    enriched_history: list[dict[str, Any]] = []
    for entry in history:
        entry_governance = evaluate_governance(entry)
        enriched_history.append({**entry, "governance_state": entry_governance.governance_state})
    escalation = evaluate_escalation(enriched_history)
    routing = derive_escalation_routing(escalation)

    rules = governance.triggered_rules or ["No governance degradation rule was triggered."]
    reasons = governance.reasons or ["No governance degradation reason was produced."]
    lines = [
        "Governance / Operational Pressure",
        f"Snapshot: {current.get('snapshot_date', 'unknown')}",
        f"Governance State: {governance.governance_state}",
        f"Execution Pressure: {governance.execution_pressure}",
        f"Visibility: {routing.visibility_level}",
        f"Routing Reason: {routing.routing_reason}",
        "Triggered Rules:",
        *[f"- {rule}" for rule in rules],
        "Reasons:",
        *[f"- {reason}" for reason in reasons],
        "Basis: generated telemetry metrics, governance health model, and escalation routing model.",
    ]
    return "\n".join(lines)


def handle_summary(runtime_cfg: Mapping[str, Any]) -> str:
    summary_path = _telemetry_dir(runtime_cfg) / "daily_operational_trends.md"
    if not summary_path.exists():
        return "Summary unavailable: no daily operational trends artifact found. Run the telemetry summary job first."
    summary = summary_path.read_text(encoding="utf-8").strip()
    if not summary:
        return "Summary unavailable: daily operational trends artifact is empty."
    return f"Operational Summary\n{summary}\nBasis: generated daily operational trends artifact."


def handle_launch_risks(runtime_cfg: Mapping[str, Any]) -> str:
    telemetry_dir = _telemetry_dir(runtime_cfg)
    debug_dir = telemetry_dir / "debug"
    metrics = _latest_metrics(runtime_cfg)
    launch_risk_count = int(metrics.get("launch_risk_count", 0) or 0) if metrics else 0
    candidates = sorted(debug_dir.glob("launch_risk_tasks_*.json")) if debug_dir.exists() else []
    latest_artifact = candidates[-1] if candidates else None

    if latest_artifact and latest_artifact.exists():
        risks = json.loads(latest_artifact.read_text(encoding="utf-8"))
        if risks:
            lines = ["Launch Risks", f"Count: {len(risks)}"]
            for risk in risks[:10]:
                lines.append(f"- {risk.get('task_name', 'Untitled task')}: {risk.get('reason', 'Launch risk signal')}")
            lines.append("Basis: generated launch risk debug artifact.")
            return "\n".join(lines)

    return "\n".join(
        [
            "Launch Risks",
            f"Count: {launch_risk_count}",
            "No task-level launch risk artifact entries are currently available.",
            "Basis: generated telemetry metrics/debug artifacts only.",
        ]
    )


def handle_help(runtime_cfg: Mapping[str, Any]) -> str:
    return HELP_RESPONSE


DEFAULT_HANDLERS: dict[TelegramIntent, Handler] = {
    TelegramIntent.STATUS: handle_status,
    TelegramIntent.BLOCKED: handle_blocked,
    TelegramIntent.GOVERNANCE: handle_governance,
    TelegramIntent.SUMMARY: handle_summary,
    TelegramIntent.HELP: handle_help,
    TelegramIntent.LAUNCH_RISKS: handle_launch_risks,
}


def dispatch_telegram_operational_request(
    message: str,
    runtime_cfg: Mapping[str, Any] | None = None,
    handlers: Mapping[TelegramIntent, Handler] | None = None,
) -> tuple[IntentRoute, str]:
    runtime_cfg = runtime_cfg or {}
    active_handlers = handlers or DEFAULT_HANDLERS
    route = route_telegram_intent(message)

    if route.fallback or route.intent == TelegramIntent.UNKNOWN:
        return route, FALLBACK_RESPONSE

    handler = active_handlers.get(route.intent)
    if handler is None:
        fallback_route = IntentRoute(route.intent, route.handler_name, route.matched_rule, fallback=True)
        return fallback_route, FALLBACK_RESPONSE

    return route, handler(runtime_cfg)


def process_telegram_operational_message(
    message: str,
    runtime_cfg: Mapping[str, Any] | None = None,
    handlers: Mapping[TelegramIntent, Handler] | None = None,
    log_file: Path | None = None,
) -> str:
    runtime_cfg = runtime_cfg or {}
    resolved_log_file = log_file or _runtime_log_file(runtime_cfg)
    log_event(resolved_log_file, "telegram_message_received", raw_message=message)

    route, response = dispatch_telegram_operational_request(message, runtime_cfg, handlers)
    log_event(
        resolved_log_file,
        "telegram_intent_routed",
        raw_message=message,
        detected_intent=route.intent.value,
        handler_selected=route.handler_name,
        matched_rule=route.matched_rule,
        fallback_triggered=route.fallback,
    )

    if route.fallback:
        log_event(resolved_log_file, "telegram_fallback_triggered", raw_message=message)

    log_event(
        resolved_log_file,
        "telegram_response_delivered",
        detected_intent=route.intent.value,
        handler_selected=route.handler_name,
        response_chars=len(response),
    )
    return response
