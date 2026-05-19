from shared.intelligence.models import OperationalSignal


BLOCKED_HEALTH_KEYWORDS = (
    "blocked",
    "waiting",
    "at risk",
    "at_risk",
)


def _custom_field_value(task: Dict[str, Any], field_names: Sequence[str]) -> str | None:
    targets = {name.strip().lower() for name in field_names}

    for field in task.get("custom_fields", []) or []:
        name = (field.get("name") or "").strip().lower()
        if name not in targets:
            continue

        display_value = field.get("display_value")
        if display_value:
            return str(display_value)

        enum_value = field.get("enum_value") or {}
        if enum_value.get("name"):
            return str(enum_value["name"])

        for value_key in ("text_value", "number_value"):
            value = field.get(value_key)
            if value is not None:
                return str(value)

    return None


def task_name(task: Dict[str, Any]) -> str:
    return task.get("name") or "Untitled task"


def task_gid(task: Dict[str, Any]) -> str | None:
    gid = task.get("gid")
    return str(gid) if gid else None


def due_value(task: Dict[str, Any]) -> str | None:
    due = task.get("due_on") or task.get("due_at")
    return str(due) if due else None


def raw_priority(task: Dict[str, Any]) -> str:
    return _custom_field_value(task, ["Priority"]) or "No Priority"


def raw_health(task: Dict[str, Any]) -> str:
    return (
        _custom_field_value(
            task,
            [
                "Health and Execution Status",
                "Field Health and Execution Status",
                "Health / Execution Status",
                "Health / Execution",
                "Execution Status",
                "Health",
                "Status",
            ],
        )
        or "No Health Status"
    )


def section_names(task: Dict[str, Any]) -> List[str]:
    sections: List[str] = []

    for membership in task.get("memberships", []) or []:
        section = membership.get("section") or {}
        name = section.get("name")
        if name:
            sections.append(str(name))

    return sections or ["No Section"]


def normalize_priority(value: str | None) -> str:
    value = (value or "").strip().lower()

    if value.startswith("p0") or value == "critical":
        return "p0"
    if value.startswith("p1") or value == "high":
        return "p1"
    if value.startswith("p2") or value == "medium":
        return "p2"
    if value.startswith("p3") or value == "low":
        return "p3"
    if value.startswith("p4"):
        return "p4"

    return "no_priority"


def normalize_section(value: str | None) -> str:
    value = (value or "").strip().lower()
    compact = value.replace(" ", "")

    if value == "in progress":
        return "in_progress"
    if value in {"scheduled / ready to launch", "scheduled", "ready to launch"}:
        return "scheduled"
    if value == "qa" or "review" in value:
        return "qa_review"
    if compact in {"triage/ready", "triage-ready"} or value == "triage ready":
        return "triage_ready"
    if value == "intake":
        return "intake"
    if value == "done":
        return "done"
    if value == "canceled":
        return "canceled"
    if value == "no section":
        return "no_section"

    return value.replace(" ", "_").replace("/", "_") or "no_section"


def normalized_sections(task: Dict[str, Any]) -> Tuple[str, ...]:
    return tuple(normalize_section(section) for section in section_names(task))


def primary_normalized_section(task: Dict[str, Any]) -> str:
    sections = normalized_sections(task)

    for section in (
        "in_progress",
        "scheduled",
        "qa_review",
        "triage_ready",
        "intake",
        "done",
        "canceled",
    ):
        if section in sections:
            return section

    return sections[0] if sections else "no_section"


def normalized_health(task: Dict[str, Any]) -> str:
    return raw_health(task).strip().lower().replace(" ", "_")


def has_blocked_health(task: Dict[str, Any]) -> bool:
    health = raw_health(task).strip().lower()
    return any(keyword in health for keyword in BLOCKED_HEALTH_KEYWORDS)


def classify_operational_task(task: Dict[str, Any]) -> Dict[str, Any]:
    section = primary_normalized_section(task)
    priority = normalize_priority(raw_priority(task))
    classifications: List[str] = []

    if section != "no_section":
        classifications.append(f"section:{section}")
    if priority != "no_priority":
        classifications.append(f"priority:{priority}")
    if due_value(task):
        classifications.append("has_due_date")
    else:
        classifications.append("missing_due_date")
    if has_blocked_health(task):
        classifications.append("health:blocked_like")

    return {
        "task_name": task_name(task),
        "task_gid": task_gid(task),
        "normalized_section": section,
        "normalized_sections": normalized_sections(task),
        "normalized_priority": priority,
        "normalized_health": normalized_health(task),
        "raw_health": raw_health(task),
        "due": due_value(task),
        "classifications": tuple(classifications),
    }


def _signal(
    task: Dict[str, Any],
    *,
    signal_type: str,
    severity: str,
    rule_name: str,
    message: str,
) -> OperationalSignal:
    facts = classify_operational_task(task)
    return OperationalSignal(
        signal_type=signal_type,
        severity=severity,
        task_name=facts["task_name"],
        task_gid=facts["task_gid"],
        message=message,
        rule_name=rule_name,
        normalized_section=facts["normalized_section"],
        normalized_priority=facts["normalized_priority"],
        classifications=facts["classifications"],
        details={
            "normalized_health": facts["normalized_health"],
            "raw_health": facts["raw_health"],
            "due": facts["due"],
            "normalized_sections": facts["normalized_sections"],
        },
    )


def detect_p4_in_progress(task: Dict[str, Any]) -> List[OperationalSignal]:
    facts = classify_operational_task(task)

    if facts["normalized_priority"] != "p4":
        return []
    if facts["normalized_section"] != "in_progress":
        return []

    return [
        _signal(
            task,
            signal_type="workflow_contradiction",
            severity="medium",
            rule_name="detect_p4_in_progress",
            message="P4 task currently in progress.",
        )
    ]


def detect_workflow_contradictions(tasks: Iterable[Dict[str, Any]]) -> List[OperationalSignal]:
    signals: List[OperationalSignal] = []

    for task in tasks:
        signals.extend(detect_p4_in_progress(task))
def detect_p4_in_progress(tasks):
    findings = []

    for task in tasks:
        priority = task.get("normalized_priority")
        section = task.get("normalized_section")

        if priority == "p4" and section == "in_progress":
            findings.append(
                OperationalSignal(
                    signal_type="workflow_contradiction",
                    severity="medium",
                    task_name=task["name"],
                    message="P4 task currently in progress."
                )
            )

    return findings