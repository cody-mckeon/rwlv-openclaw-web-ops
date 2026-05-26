import json
import tempfile
from pathlib import Path

from shared.telemetry import append_telemetry_snapshot, extract_operational_metrics


def field(name, value):
    return {"name": name, "display_value": value}


def task(name, section, priority="P2 - Important", health="On Track", completed=False):
    return {
        "gid": name.lower().replace(" ", "-"),
        "name": name,
        "completed": completed,
        "memberships": [{"section": {"name": section}}],
        "custom_fields": [field("Priority", priority), field("Health / Execution", health)],
    }


def test_extract_operational_metrics_is_deterministic_and_explainable():
    tasks = [
        task("P0 Task", "In Progress", priority="P0 - Critical / Interrupt"),
        task("Blocked QA", "QA", health="Blocked"),
        task("Intake Task", "Intake"),
        task("Scheduled Task", "Scheduled / Ready to Launch"),
        task("Done Task", "Done", completed=True),
    ]

    metrics = extract_operational_metrics(tasks, contradiction_count=3, launch_risk_count=1)

    assert metrics["task_count"] == 5
    assert metrics["open_task_count"] == 4
    assert metrics["p0_count"] == 1
    assert metrics["blocked_count"] == 1
    assert metrics["in_progress_count"] == 1
    assert metrics["intake_count"] == 1
    assert metrics["qa_count"] == 1
    assert metrics["scheduled_launch_count"] == 1
    assert metrics["contradiction_count"] == 3
    assert metrics["launch_risk_count"] == 1


def test_append_telemetry_snapshot_writes_jsonl_record():
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_cfg = {"paths": {"telemetry_dir": str(Path(tmpdir) / "telemetry")}}
        metrics = {"task_count": 10, "p0_count": 2}

        telemetry_file = append_telemetry_snapshot(
            runtime_cfg=runtime_cfg,
            snapshot_date="2026-05-21",
            execution_id="abc123",
            metrics=metrics,
        )

        payload = json.loads(telemetry_file.read_text(encoding="utf-8").strip())
        assert payload["snapshot_date"] == "2026-05-21"
        assert payload["execution_id"] == "abc123"
        assert payload["task_count"] == 10
        assert payload["p0_count"] == 2
