from shared.intelligence.models import OperationalSignal

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