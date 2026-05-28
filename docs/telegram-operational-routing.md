# Telegram Natural Language Operational Routing

ForgePod's Telegram layer supports natural language operational requests without turning the interface into a generic chatbot.

## Philosophy

Operators should not need to memorize slash commands during operational work. They should be able to ask plain questions such as:

- `what is blocked?`
- `how are we doing today?`
- `why are we overloaded?`
- `show me launch risks`
- `what changed?`
- `what needs attention?`

The system still preserves deterministic operational trust: natural language is used only to select an existing operational retrieval handler. The response content comes from generated telemetry, governance, and priority artifacts.

## Routing Architecture

```text
Telegram message
→ deterministic intent router
→ deterministic operational handler
→ explainable operational response
```

The router uses this order:

1. Slash command matching.
2. Supported phrase matching.
3. Supported keyword matching.
4. Safe fallback response.

There is no LLM intent classifier in the default path.

## Supported Intents

| Intent | Slash command | Example natural language requests | Handler source |
| --- | --- | --- | --- |
| Status | `/status` | `how are we doing today?`, `status`, `what is the state?` | Latest telemetry metrics plus deterministic governance health model |
| Blocked | `/blocked` | `what is blocked?`, `what is waiting?`, `what should I follow up on?`, `what needs attention?` | Latest generated `CURRENT_PRIORITIES` snapshot section |
| Governance | `/governance` | `why are we overloaded?`, `governance`, `what rules triggered?` | Telemetry metrics, governance health model, escalation routing model |
| Summary | `/summary` | `summary`, `daily summary`, `what changed?`, `give me the summary` | Generated daily operational trends artifact |
| Launch risks | `/launch_risks` | `show me launch risks`, `launch risks`, `what could block launch?` | Generated launch-risk telemetry/debug artifacts |
| Help | `/help` | `help`, `what can you do?`, `what can I ask?` | Static capability guidance |

## Fallback Behavior

If the router cannot determine a supported intent, it returns a safe prompt rather than improvising:

```text
I can help with status, blocked work, governance, summary, or launch risks. Try asking: 'what is blocked?' or 'how are we doing today?'
```

This keeps unsupported requests from producing hallucinated operational claims.

## Runtime Logging

Each processed Telegram operational message writes structured runtime events:

- `telegram_message_received` with the raw message.
- `telegram_intent_routed` with detected intent, matched rule, handler selected, and fallback state.
- `telegram_fallback_triggered` when no deterministic route is available.
- `telegram_response_delivered` with response size and selected route metadata.

The default log path is `generated/logs/telegram_operational_interface.jsonl`.

## Why This Is Not a Generic Chatbot

This layer does not:

- answer arbitrary questions;
- infer facts that are not in operational artifacts;
- use personality-driven dialogue;
- autonomously decide actions;
- call an LLM classifier by default.

It only routes known operator phrases to deterministic retrieval handlers. If the requested operation is not recognized, the fallback explains the supported operational retrieval options.
