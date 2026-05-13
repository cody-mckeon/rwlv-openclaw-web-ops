# scripts/send_priority_digest.py

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


WORKSPACE_ROOT = Path("/Users/cody.mckeon/.openclaw/workspace")
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


def shorten_task_line(line: str) -> str:
    """
    Make generated task lines easier to read in Telegram.
    Original:
    - Task name | Assignee: Name | Due: Date | Section: X | Status: Y | Priority: Z | Work Type: A
    """
    if line == "- None found." or "Assignee:" not in line:
        return line

    text = line.removeprefix("- ").strip()
    parts = [part.strip() for part in text.split("|")]

    task_name = parts[0] if parts else text

    due = "No due date"
    assignee = "Unassigned"
    status = "No Status"
    priority = "No Priority"
    work_type = "No Work Type"

    for part in parts[1:]:
        if part.startswith("Due:"):
            due = part.replace("Due:", "").strip()
        elif part.startswith("Assignee:"):
            assignee = part.replace("Assignee:", "").strip()
        elif part.startswith("Status:"):
            status = part.replace("Status:", "").strip()
        elif part.startswith("Priority:"):
            priority = part.replace("Priority:", "").strip()
        elif part.startswith("Work Type:"):
            work_type = part.replace("Work Type:", "").strip()

    return f"- {task_name}\n  Due: {due} | Assignee: {assignee} | Status: {status} | Priority: {priority} | Type: {work_type}"


def format_section(title: str, items: List[str]) -> str:
    cleaned = [shorten_task_line(item) for item in items]
    return f"{title}\n" + "\n".join(cleaned)


def build_digest(markdown: str) -> str:
    today = datetime.now().strftime("%A, %B %-d, %Y")

    active = extract_section(markdown, "P1 / Active In Progress", max_items=5)
    due = extract_section(markdown, "Due-Dated Tasks", max_items=5)
    intake = extract_section(markdown, "P2 / Intake Needs Triage", max_items=5)
    hygiene = extract_section(markdown, "Asana Hygiene Flags", max_items=5)

    message_parts = [
        f"Priority Governor Daily Brief\n{today}",
        "",
        format_section("1. Active in-progress work", active),
        "",
        format_section("2. Due-dated tasks", due),
        "",
        format_section("3. Intake items needing triage", intake),
        "",
        format_section("4. Asana hygiene flags", hygiene),
        "",
        "5. Suggested focus for today",
        "- Protect active in-progress work before accepting new intake.",
        "- Review due-dated tasks for anything that needs a tradeoff decision.",
        "- Clarify vague intake items before they become execution work.",
        "- Fix Asana field mismatches when section/status/priority do not agree.",
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
            f"Missing {PRIORITIES_FILE}. Run update_priorities.sh first."
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