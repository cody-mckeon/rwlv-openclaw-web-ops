from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class TelegramIntent(str, Enum):
    STATUS = "status"
    BLOCKED = "blocked"
    GOVERNANCE = "governance"
    SUMMARY = "summary"
    HELP = "help"
    LAUNCH_RISKS = "launch_risks"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentRoute:
    intent: TelegramIntent
    handler_name: str | None
    matched_rule: str | None
    fallback: bool = False


SLASH_COMMANDS: dict[str, TelegramIntent] = {
    "/status": TelegramIntent.STATUS,
    "/blocked": TelegramIntent.BLOCKED,
    "/governance": TelegramIntent.GOVERNANCE,
    "/summary": TelegramIntent.SUMMARY,
    "/help": TelegramIntent.HELP,
    "/launch_risks": TelegramIntent.LAUNCH_RISKS,
    "/launch-risks": TelegramIntent.LAUNCH_RISKS,
}

INTENT_HANDLER_NAMES: dict[TelegramIntent, str] = {
    TelegramIntent.STATUS: "status",
    TelegramIntent.BLOCKED: "blocked",
    TelegramIntent.GOVERNANCE: "governance",
    TelegramIntent.SUMMARY: "summary",
    TelegramIntent.HELP: "help",
    TelegramIntent.LAUNCH_RISKS: "launch_risks",
}

PHRASE_RULES: tuple[tuple[TelegramIntent, tuple[str, ...]], ...] = (
    (
        TelegramIntent.BLOCKED,
        (
            "what is blocked",
            "what's blocked",
            "what is waiting",
            "what's waiting",
            "what should i follow up on",
            "what needs follow up",
            "what needs attention",
            "blocked work",
            "waiting work",
            "follow up",
        ),
    ),
    (
        TelegramIntent.STATUS,
        (
            "how are we doing",
            "how are we doing today",
            "what is the state",
            "what's the state",
            "current state",
            "status",
            "state of things",
        ),
    ),
    (
        TelegramIntent.GOVERNANCE,
        (
            "why are we overloaded",
            "why overloaded",
            "governance",
            "what rules triggered",
            "rules triggered",
            "execution pressure",
            "operational pressure",
        ),
    ),
    (
        TelegramIntent.LAUNCH_RISKS,
        (
            "show me launch risks",
            "launch risks",
            "launch risk",
            "ready to launch risks",
            "what could block launch",
        ),
    ),
    (
        TelegramIntent.SUMMARY,
        (
            "summary",
            "daily summary",
            "what changed",
            "give me the summary",
            "trend summary",
            "operational summary",
        ),
    ),
    (
        TelegramIntent.HELP,
        (
            "help",
            "what can you do",
            "commands",
            "what can i ask",
        ),
    ),
)

KEYWORD_RULES: tuple[tuple[TelegramIntent, tuple[str, ...]], ...] = (
    (TelegramIntent.BLOCKED, ("blocked", "waiting", "follow up", "attention")),
    (TelegramIntent.GOVERNANCE, ("overloaded", "governance", "rules", "pressure")),
    (TelegramIntent.LAUNCH_RISKS, ("launch risk", "launch risks")),
    (TelegramIntent.SUMMARY, ("summary", "changed", "changes", "trends")),
    (TelegramIntent.STATUS, ("status", "state")),
    (TelegramIntent.HELP, ("help", "commands")),
)


def _normalize_message(message: str) -> str:
    normalized = message.strip().lower()
    normalized = re.sub(r"[!?.,;:]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _first_token(message: str) -> str:
    return message.strip().split(maxsplit=1)[0].lower() if message.strip() else ""


def _contains_any(normalized: str, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in normalized:
            return candidate
    return None


def route_telegram_intent(message: str) -> IntentRoute:
    """Route Telegram text to a deterministic operational intent.

    This deliberately uses slash-command, phrase, and keyword matching only. It
    does not perform LLM classification and does not infer operational facts.
    """
    command = _first_token(message)
    if command in SLASH_COMMANDS:
        intent = SLASH_COMMANDS[command]
        return IntentRoute(
            intent=intent,
            handler_name=INTENT_HANDLER_NAMES[intent],
            matched_rule=f"slash:{command}",
        )

    normalized = _normalize_message(message)
    if not normalized:
        return IntentRoute(intent=TelegramIntent.UNKNOWN, handler_name=None, matched_rule=None, fallback=True)

    for intent, phrases in PHRASE_RULES:
        match = _contains_any(normalized, phrases)
        if match:
            return IntentRoute(
                intent=intent,
                handler_name=INTENT_HANDLER_NAMES[intent],
                matched_rule=f"phrase:{match}",
            )

    for intent, keywords in KEYWORD_RULES:
        match = _contains_any(normalized, keywords)
        if match:
            return IntentRoute(
                intent=intent,
                handler_name=INTENT_HANDLER_NAMES[intent],
                matched_rule=f"keyword:{match}",
            )

    return IntentRoute(intent=TelegramIntent.UNKNOWN, handler_name=None, matched_rule=None, fallback=True)
