# scripts/send_priority_digest.py

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from skills.asana.actions.read_subtasks import read_task_subtasks


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PRIORITIES_FILE = WORKSPACE_ROOT / "CURRENT_PRIORITIES.generated.md"
HEARTBEAT_FILE = WORKSPACE_ROOT / "HEARTBEAT.priority_digest.md"


def load_env(env_path: Path) -> None:
    """
    Minimal .env loader.
    Supports simple KEY="value" or KEY=value lines.
    """
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def extract_section(markdown: str, heading: str, max_items: int = 5) -> List[str]:
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

def filter_items_containing(items, keywords):
    return [
        item
        for item in items
        if any(keyword.lower() in item.lower() for keyword in keywords)
    ]

def build_digest(markdown: str) -> str:
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
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")

    if not chat_id:
        raise ValueError("Missing TELEGRAM_CHAT_ID")

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



def main() -> None:
    load_env(WORKSPACE_ROOT / ".env")

    if not PRIORITIES_FILE.exists():
        raise FileNotFoundError(
            f"Missing {PRIORITIES_FILE}. Run the Asana priority generator first."
        )

    markdown = PRIORITIES_FILE.read_text(encoding="utf-8")
    digest = build_digest(markdown)

    send_telegram_message(digest)

    HEARTBEAT_FILE.write_text(
        f"Last priority digest sent: {datetime.now().isoformat()}\n",
        encoding="utf-8",
    )

    print("Sent Priority Governor Daily Brief to Telegram.")


if __name__ == "__main__":
    main()