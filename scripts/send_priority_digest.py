# scripts/send_priority_digest.py

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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

    This version preserves task names that contain pipe characters.
    """
    if line == "- None found." or "Assignee:" not in line:
        return line

    text = line.removeprefix("- ").strip()

    # Everything before " | Assignee:" is the real task name.
    task_name = text.split(" | Assignee:", 1)[0].strip()

    assignee = _extract_field(text, "Assignee", "Unassigned")
    due = _extract_field(text, "Due", "No due date")
    section = _extract_field(text, "Section", "No Section")
    status = _extract_field(text, "Status", "No Status")
    priority = _extract_field(text, "Priority", "No Priority")
    work_type = _extract_field(text, "Work Type", "No Work Type")
    target_ship = _extract_field(text, "Target Ship", "No Target Ship")

    timing = f"Due: {due}"
    if target_ship != "No Target Ship":
        timing = f"Target: {target_ship} | {timing}"

    return (
        f"- {task_name}\n"
        f"  {timing} | Owner: {assignee}\n"
        f"  Status: {status} | Priority: {priority} | Type: {work_type} | Section: {section}"
    )


def format_section(title: str, items: List[str]) -> str:
    cleaned = [shorten_task_line(item) for item in items]
    return f"{title}\n" + "\n".join(cleaned)


def filter_items_containing(items: List[str], keywords: List[str], max_items: int = 5) -> List[str]:
    matched = []
    for item in items:
        lower = item.lower()
        if any(keyword.lower() in lower for keyword in keywords):
            matched.append(item)

    return matched[:max_items] if matched else ["- None found."]


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

    message_parts = [
        f"Priority Governor Daily Brief\n{today}",
        "",
        format_section("1. Critical / high-priority active work", critical_active),
        "",
        format_section("2. Active in-progress work", active_display),
        "",
        format_section("3. Due-dated / target ship items", due_display),
        "",
        format_section("4. Ready for QA / review", ready_for_review),
        "",
        format_section("5. Intake needing triage", intake_display),
        "",
        format_section("6. Asana hygiene flags", hygiene_display),
        "",
        "7. Suggested focus for today",
        "- Protect In Progress and QA work before accepting new Intake.",
        "- Review Critical/High priority items first, especially compliance, booking, consent, and launch-related work.",
        "- Use Intake as a triage queue, not an automatic work queue.",
        "- Clean up tasks where Section and Status do not match.",
    ]

    return "\n".join(message_parts)


def send_telegram_message(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")

    if not chat_id:
        raise ValueError("Missing TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    request = Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Telegram send failed with status {response.status}")


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