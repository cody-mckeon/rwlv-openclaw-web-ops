# scripts/send_priority_digest.py

from __future__ import annotations

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from skills.asana.actions.read_subtasks import read_task_subtasks
from shared.config.runtime import (
    get_required_env,
    load_dotenv,
    load_runtime_config,
    validate_runtime_environment,
)
from shared.logging.runtime_logger import log_event
from shared.runtime_health import RuntimeValidationError, validate_runtime_startup
from shared.telemetry import build_snapshot_context, resolve_latest_priorities_file


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PRIORITIES_FILE = WORKSPACE_ROOT / "generated/snapshots/CURRENT_PRIORITIES.generated.md"
DEFAULT_HEARTBEAT_FILE = WORKSPACE_ROOT / "HEARTBEAT.priority_digest.md"
DEFAULT_STATE_FILE = WORKSPACE_ROOT / "generated/logs/priority_digest_state.json"




def extract_section(markdown: str, heading: str, max_items: int) -> List[str]:
    """
    Extract bullet lines from a markdown section by heading.
    Example heading: "P1 / Active In Progress"
    """
    pattern = rf"## {re.escape(heading)}\n(.*?)(?=\n## |\n---|\Z)"
    match = re.search(pattern, markdown, flags=re.DOTALL)

    if not match:
        return ["- Section not found."]

    section_text = match.group(1)
    bullets = [
        line.strip()
        for line in section_text.splitlines()
        if line.strip().startswith("- ")
    ]

    # Remove section explanation bullets if needed, but keep task bullets.
    task_bullets = [
        bullet for bullet in bullets
        if "Assignee:" in bullet or bullet == "- None found."
    ]

    if not task_bullets:
        task_bullets = ["- None found."]

    return task_bullets[:max_items]

def _extract_field(text: str, label: str, default: str) -> str:
    """
    Extract a labeled field from a generated task line.

    Example:
    | Assignee: Cody | Due: No due date | Section: In Progress
    """
    pattern = rf"\| {re.escape(label)}: (.*?)(?= \| [A-Za-z ]+:|$)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else default


def shorten_task_line(line: str) -> str:
    """
    Make generated task lines easier to read in Telegram.

    Preserves task names that contain pipe characters.
    """
    if line == "- None found." or "Assignee:" not in line:
        return line

    text = line.removeprefix("- ").strip()

    task_name = text.split(" | Assignee:", 1)[0].strip()

    assignee = _extract_field(text, "Assignee", "Unassigned")
    due = _extract_field(text, "Due", "No due date")
    section = _extract_field(text, "Section", "No Section")

    health = (
        _extract_field(text, "Health", "")
        or _extract_field(text, "Execution Status", "")
        or "No Health Status"
    )

    priority = _extract_field(text, "Priority", "No Priority")
    work_type = _extract_field(text, "Work Type", "No Work Type")
    release_month = _extract_field(text, "Release Month", "No Release Month")
    vendor = _extract_field(text, "Vendor", "No Vendor")
    ready_for_vendor = _extract_field(text, "Ready for Vendor", "No")
    property_value = _extract_field(text, "Property", "No Property")
    subtasks = _extract_field(text, "Subtasks", "0")

    timing = f"Release: {release_month} | Due: {due}"

    return (
        f"- {task_name}\n"
        f"  {timing} | Assignee: {assignee}\n"
        f"  Health: {health} | Priority: {priority} | Type: {work_type}\n"
        f"  Section: {section} | Vendor: {vendor} | Ready for Vendor: {ready_for_vendor} | Property: {property_value} | Subtasks: {subtasks}"
    )

def extract_task_gid(item: str) -> str:
    return extract_field_from_item(item, "GID", "")

def format_section(title: str, items: List[str]) -> str:
    cleaned = [shorten_task_line(item) for item in items]
    return f"{title}\n" + "\n".join(cleaned)


def filter_items_containing(
    items: List[str],
    keywords: List[str],
    max_items: int = 5,
) -> List[str]:
    matched = []

    for item in items:
        item_text = item.lower()
        if any(keyword.lower() in item_text for keyword in keywords):
            matched.append(item)

    return matched[:max_items] if matched else ["- None found."]


def extract_field_from_item(item: str, label: str, default: str = "") -> str:
    """
    Extract a labeled field from a generated priority item.

    Example:
    | Priority: P1 - Committed | Work Type: New Build
    """
    pattern = rf"\| {re.escape(label)}: (.*?)(?= \| [A-Za-z ]+:|$)"
    match = re.search(pattern, item)
    return match.group(1).strip() if match else default


def normalize_priority(priority: str) -> str:
    """
    Normalize old and new Asana priority values into P-levels.

    Supports transition period from:
    Critical / High / Medium / Low

    To:
    P0 - Interrupt
    P1 - Committed
    P2 - Scheduled
    P3 - Backlog
    P4 - Parking
    """
    value = (priority or "").strip().lower()

    if value.startswith("p0") or value == "critical":
        return "P0"

    if value.startswith("p1") or value == "high":
        return "P1"

    if value.startswith("p2") or value == "medium":
        return "P2"

    if value.startswith("p3") or value == "low":
        return "P3"

    if value.startswith("p4"):
        return "P4"

    return "NO_PRIORITY"


def get_item_priority_level(item: str) -> str:
    priority = extract_field_from_item(item, "Priority", "No Priority")
    return normalize_priority(priority)


def is_p0_interrupt(item: str) -> bool:
    return get_item_priority_level(item) == "P0"


def is_p1_committed(item: str) -> bool:
    return get_item_priority_level(item) == "P1"


def is_active_item(item: str) -> bool:
    section = extract_field_from_item(item, "Section", "")
    status = extract_field_from_item(item, "Status", "")

    combined = f"{section} {status}".lower()

    return (
        "in progress" in combined
        or "ready for work" in combined
        or "ready for qa" in combined
        or "ready for review" in combined
        or "active" in combined
    )


def is_ready_for_review(item: str) -> bool:
    section = extract_field_from_item(item, "Section", "")
    health = (
        extract_field_from_item(item, "Health", "")
        or extract_field_from_item(item, "Execution Status", "")
    )

    combined = f"{section} {health}".lower()

    return (
        "qa" in combined
        or "ready for qa" in combined
        or "ready for review" in combined
        or "waiting approval" in combined
    )


def is_committed_active_work(item: str) -> bool:
    """
    P1 committed work that is active or ready.
    This should be protected from lower-priority intake.
    """
    return is_p1_committed(item) and is_active_item(item)


def is_due_or_targeted(item: str) -> bool:
    due = extract_field_from_item(item, "Due", "No due date")
    target_ship = extract_field_from_item(item, "Target Ship", "No Target Ship")

    # Target Ship is a planning bucket, not urgency by itself.
    # This function only identifies date-visible work for review.
    return due != "No due date" or target_ship != "No Target Ship"


def fallback_if_empty(items: List[str]) -> List[str]:
    cleaned = [
        item for item in items
        if item not in {"- Section not found.", "- None found."}
    ]
    return cleaned if cleaned else ["- None found."]

def filter_items_containing(items, keywords, max_items=None):
    filtered = [
        item
        for item in items
        if any(keyword.lower() in item.lower() for keyword in keywords)
    ]

    if max_items is not None:
        return filtered[:max_items]

    return filtered

def build_digest(markdown: str, top_items_per_section=10) -> str:
    today = datetime.now().strftime("%A, %B %-d, %Y")

    active = extract_section(markdown, "P1 / Active In Progress", max_items=20)
    active_cleanup = extract_section(markdown, "P1 Review / Active but Field Mismatch", max_items=10)
    due = extract_section(markdown, "Due-Dated Tasks", max_items=10)
    ready = extract_section(markdown, "Ready for QA / Review", max_items=10)
    intake = extract_section(markdown, "P2 / Intake Needs Triage", max_items=10)
    hygiene = extract_section(markdown, "Asana Hygiene Flags", max_items=10)

    critical_active = filter_items_containing(
        active + active_cleanup,
        [
            "Priority: Critical",
            "Priority: P0",
            "P0 -",
            "Priority: High",
            "Priority: P1",
            "P1 -",
            "Compliance",
            "Booking",
            "Book Now",
            "Consent",
        ],
        max_items=5,
    )

    ready_for_review = filter_items_containing(
        ready + active + active_cleanup + due,
        ["Status: Ready", "Ready for", "Section: QA", "QA", "Ready to Launch"],
        max_items=5,
    )

    # Keep the displayed digest short.
    active_candidates = [
        item for item in active + active_cleanup if item != "- None found."
    ]
    active_display = active_candidates[:5] if active_candidates else ["- None found."]
    due_display = due[:5]
    intake_display = intake[:5]
    hygiene_display = hygiene[:5]

    interrupt = extract_section(markdown, "P0 / Interrupt Work", max_items=10)
    committed = extract_section(markdown, "P1 / Active Committed Work", max_items=10)
    qa = extract_section(markdown, "QA / Review", max_items=10)
    scheduled = extract_section(markdown, "Scheduled / Ready to Launch", max_items=10)
    triage = extract_section(markdown, "Triage / Ready", max_items=10)
    intake = extract_section(markdown, "Intake", max_items=10)
    blocked = extract_section(markdown, "Blocked / Waiting / At Risk", max_items=10)
    hygiene = extract_section(markdown, "Asana Hygiene Flags", max_items=10)

    message_parts = [
        f"Priority Governor Daily Brief\n{today}",
        "",
        format_section("1. P0 Interrupt work", fallback_if_empty(interrupt)),
        "",
        format_section("2. Blocked / waiting / at risk", fallback_if_empty(blocked)),
        "",
        format_section("3. P1 active committed work", fallback_if_empty(committed)),
        "",
        format_section("4. QA / review", fallback_if_empty(qa)),
        "",
        format_section("5. Scheduled / ready to launch", fallback_if_empty(scheduled)),
        "",
        format_section("6. Triage / ready", fallback_if_empty(triage)),
        "",
        format_section("7. Intake watchlist", fallback_if_empty(intake)),
        "",
        format_section("8. Asana hygiene flags", fallback_if_empty(hygiene)),
        "",
        "9. Suggested operating move",
        "- P0 interrupts current work only when there is real business, guest, revenue, launch, or compliance risk.",
        "- Check Blocked / Waiting / At Risk before accepting new work.",
        "- Protect P1 committed work before pulling from Intake.",
        "- QA and Scheduled / Ready to Launch items should be cleared before starting lower-priority work.",
        "- Use Intake as a capture queue, not an automatic work queue.",
        "- Clean up tasks where Section, Priority, Release Month, Vendor, or Execution Status do not agree.",
    ]

    return "\n".join(message_parts)

def split_message(message: str, max_length: int = 3900) -> List[str]:
    """
    Split a long Telegram message into safe chunks.
    """
    chunks: List[str] = []
    current = ""

    for line in message.splitlines():
        candidate = f"{current}\n{line}" if current else line

        if len(candidate) > max_length:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks

def send_telegram_message(message: str) -> None:
    token = get_required_env("TELEGRAM_BOT_TOKEN")
    chat_id = get_required_env("TELEGRAM_CHAT_ID")

    try:
        token.encode("ascii")
        chat_id.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "Telegram token or chat ID contains a non-ASCII character. "
            "Re-enter TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID without smart quotes."
        ) from exc

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = split_message(message)

    for index, chunk in enumerate(chunks, start=1):
        if len(chunks) > 1:
            chunk = f"{chunk}\n\nPart {index}/{len(chunks)}"

        payload = urlencode(
            {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")

        request = Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"Telegram send failed with status {response.status}"
                    )
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Telegram send failed: HTTP {exc.code} {exc.reason}. "
                f"Response: {error_body}"
            ) from exc


def _load_digest_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_digest_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _evaluate_digest_schedule(cfg: Dict[str, Any], now: datetime, state: Dict[str, Any]) -> Dict[str, Any]:
    schedule = cfg.get("schedule", {}) if isinstance(cfg, dict) else {}
    enabled = bool(schedule.get("enabled", True))
    timezone_name = str(schedule.get("timezone", "UTC"))
    allowed_weekdays = schedule.get("weekdays", [0, 1, 2, 3, 4])
    window_start = str(schedule.get("window_start", "08:30"))
    max_per_day = int(schedule.get("max_sends_per_day", 1))
    cooldown_seconds = int(schedule.get("cooldown_seconds", 21600))

    local_now = now.astimezone(ZoneInfo(timezone_name))
    hh, mm = [int(part) for part in window_start.split(":", 1)]
    scheduled_dt = local_now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    last_sent_at = state.get("last_sent_at")
    last_sent_local = None
    if last_sent_at:
        try:
            last_sent_local = datetime.fromisoformat(last_sent_at).astimezone(ZoneInfo(timezone_name))
        except ValueError:
            last_sent_local = None

    reasons: List[str] = []
    should_send = True

    if not enabled:
        should_send = False
        reasons.append("schedule_disabled")
    if local_now.weekday() not in allowed_weekdays:
        should_send = False
        reasons.append("weekday_not_allowed")
    if local_now < scheduled_dt:
        should_send = False
        reasons.append("before_delivery_window")
    if last_sent_local and last_sent_local.date() == local_now.date() and max_per_day <= 1:
        should_send = False
        reasons.append("max_per_day_reached")
    if last_sent_local:
        elapsed = (local_now - last_sent_local).total_seconds()
        if elapsed < cooldown_seconds:
            should_send = False
            reasons.append("cooldown_active")

    return {
        "should_send": should_send,
        "reasons": reasons or ["window_open"],
        "scheduled_window_local": scheduled_dt.isoformat(),
        "evaluated_at_local": local_now.isoformat(),
        "timezone": timezone_name,
    }



def main() -> None:
    load_dotenv(WORKSPACE_ROOT / ".env")
    runtime_config = load_runtime_config()
    runtime_cfg = runtime_config.get("runtime", {})
    snapshot_ctx = build_snapshot_context(runtime_cfg)
    runtime_log_file = WORKSPACE_ROOT / snapshot_ctx.runtime_log_file
    priorities_file = WORKSPACE_ROOT / resolve_latest_priorities_file(runtime_cfg)

    digest_cfg = runtime_config.get("runtime", {}).get("priority_digest", {})
    top_items_per_section = int(digest_cfg.get("top_items_per_section", 5))
    heartbeat_relative = digest_cfg.get("heartbeat_file", "HEARTBEAT.priority_digest.md")
    heartbeat_file = WORKSPACE_ROOT / str(heartbeat_relative)
    state_file = WORKSPACE_ROOT / str(digest_cfg.get("state_file", str(DEFAULT_STATE_FILE.relative_to(WORKSPACE_ROOT))))

    try:
        validate_runtime_startup(runtime_config, ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"])
        validate_runtime_environment(["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"])
    except RuntimeValidationError as exc:
        log_event(
            runtime_log_file,
            event_type="startup_validation",
            severity="error",
            status="failure",
            action="scripts.send_priority_digest",
            error=str(exc),
        )
        raise

    if not priorities_file.exists():
        message = f"Missing {priorities_file}. Run the Asana priority generator first."
        log_event(
            runtime_log_file,
            event_type="validation_failure",
            severity="error",
            status="failure",
            action="scripts.send_priority_digest",
            error=message,
        )
        raise FileNotFoundError(message)

    markdown = priorities_file.read_text(encoding="utf-8")

    log_event(
        runtime_log_file,
        event_type="runtime_start",
        severity="info",
        action="scripts.send_priority_digest",
        snapshot_date=snapshot_ctx.snapshot_date,
        execution_id=snapshot_ctx.execution_id,
        priorities_file=str(priorities_file),
    )
    state = _load_digest_state(state_file)
    schedule_eval = _evaluate_digest_schedule(digest_cfg, datetime.now(tz=ZoneInfo("UTC")), state)
    log_event(
        runtime_log_file,
        event_type="digest_schedule_evaluated",
        severity="info",
        trigger_reason="scheduler_interval",
        schedule_decision="send" if schedule_eval["should_send"] else "suppress",
        schedule_reasons=schedule_eval["reasons"],
        scheduled_window_local=schedule_eval["scheduled_window_local"],
        evaluated_at_local=schedule_eval["evaluated_at_local"],
        schedule_timezone=schedule_eval["timezone"],
    )
    if not schedule_eval["should_send"]:
        log_event(
            runtime_log_file,
            event_type="telegram_send_suppressed",
            severity="info",
            suppression_reasons=schedule_eval["reasons"],
        )
        return

    try:
        digest = build_digest(markdown, top_items_per_section=top_items_per_section)
    except Exception as exc:
        log_event(
            runtime_log_file,
            event_type="runtime_failure",
            severity="error",
            status="failure",
            action="scripts.send_priority_digest",
            stage="build_digest",
            error=str(exc),
        )
        raise
    log_event(
        runtime_log_file,
        event_type="digest_generation",
        severity="info",
        channel="telegram",
        digest_chars=len(digest),
    )

    try:
        send_telegram_message(digest)
        log_event(
            runtime_log_file,
            event_type="telegram_send",
            severity="info",
            status="success",
        )
    except Exception as exc:
        log_event(
            runtime_log_file,
            event_type="telegram_send",
            severity="error",
            status="failure",
            error=str(exc),
        )
        raise

    heartbeat_file.write_text(
        f"Last priority digest sent: {datetime.now().isoformat()}\n",
        encoding="utf-8",
    )
    _save_digest_state(
        state_file,
        {
            "last_sent_at": datetime.now(tz=ZoneInfo("UTC")).isoformat(),
            "last_schedule_evaluation": schedule_eval,
        },
    )

    print("Sent Priority Governor Daily Brief to Telegram.")


if __name__ == "__main__":
    main()
