"""Remote GCP instance management for agent tasks.

Wraps ``gcloud`` CLI commands to create, list, monitor, and tear down
GCP Compute instances that run ``eco run`` or ``eco deploy`` tasks.

All GCP interactions are deterministic subprocess calls (P6: Code Before
Prompts). No AI is involved in the deployment pipeline.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RemoteInstance:
    """Represents a running GCP agent task instance."""

    name: str
    zone: str
    status: str  # RUNNING, STAGING, TERMINATED, etc.
    machine_type: str
    created_at: str
    task: str = ""
    issue: Optional[int] = None
    pr: Optional[int] = None
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# GCP interaction layer
# ---------------------------------------------------------------------------

def _run_gcloud(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a gcloud command and return the result."""
    cmd = ["gcloud", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def _instance_name(task: str, issue: int | None, pr: int | None) -> str:
    """Generate a deterministic instance name from task context."""
    if issue:
        return f"agents-task-{issue}"
    if pr:
        return f"agents-pr-{pr}"
    # Fallback: timestamp-based
    ts = int(time.time())
    return f"agents-task-{ts}"


# ---------------------------------------------------------------------------
# Remote operations
# ---------------------------------------------------------------------------

def launch_instance(
    task: str,
    *,
    repo: str,
    branch: str = "main",
    issue: int | None = None,
    pr: int | None = None,
    project: str | None = None,
    zone: str = "us-central1-a",
    machine_type: str = "e2-standard-2",
    timeout_hours: int = 4,
    deploy_mode: bool = False,
    template: str = "agents-task-template",
    dry_run: bool = False,
) -> dict[str, str]:
    """Launch a GCP instance for an agent task.

    Returns a dict with instance details (name, zone, status).
    """
    name = _instance_name(task, issue, pr)

    metadata_items = [
        f"task={task}",
        f"repo={repo}",
        f"branch={branch}",
        f"timeout_hours={timeout_hours}",
        f"deploy_mode={'true' if deploy_mode else 'false'}",
    ]
    if issue:
        metadata_items.append(f"issue={issue}")
    if pr:
        metadata_items.append(f"pr={pr}")

    cmd_args = [
        "compute", "instances", "create", name,
        "--source-instance-template", template,
        "--zone", zone,
        "--machine-type", machine_type,
        "--metadata", ",".join(metadata_items),
    ]
    if project:
        cmd_args.extend(["--project", project])

    cmd_args.append("--format=json")

    if dry_run:
        return {
            "name": name,
            "zone": zone,
            "machine_type": machine_type,
            "task": task,
            "status": "DRY_RUN",
            "command": f"gcloud {' '.join(cmd_args)}",
        }

    result = _run_gcloud(*cmd_args)
    if result.returncode != 0:
        return {
            "name": name,
            "zone": zone,
            "status": "FAILED",
            "error": result.stderr.strip(),
        }

    return {
        "name": name,
        "zone": zone,
        "machine_type": machine_type,
        "task": task,
        "status": "LAUNCHING",
    }


def list_instances(
    *,
    project: str | None = None,
) -> list[RemoteInstance]:
    """List all running agent task instances."""
    cmd_args = [
        "compute", "instances", "list",
        "--filter", "labels.app=agents AND labels.component=remote-task",
        "--format=json",
    ]
    if project:
        cmd_args.extend(["--project", project])

    result = _run_gcloud(*cmd_args)
    if result.returncode != 0:
        return []

    try:
        raw_instances = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return []

    instances = []
    for raw in raw_instances:
        # Extract metadata
        metadata: dict[str, str] = {}
        for item in raw.get("metadata", {}).get("items", []):
            metadata[item["key"]] = item["value"]

        # Extract machine type from full URL
        mt_url = raw.get("machineType", "")
        mt = mt_url.rsplit("/", 1)[-1] if "/" in mt_url else mt_url

        # Extract zone from full URL
        zone_url = raw.get("zone", "")
        zone = zone_url.rsplit("/", 1)[-1] if "/" in zone_url else zone_url

        instances.append(RemoteInstance(
            name=raw.get("name", ""),
            zone=zone,
            status=raw.get("status", "UNKNOWN"),
            machine_type=mt,
            created_at=raw.get("creationTimestamp", ""),
            task=metadata.get("task", ""),
            issue=int(metadata["issue"]) if "issue" in metadata else None,
            pr=int(metadata["pr"]) if "pr" in metadata else None,
            metadata=metadata,
        ))

    return instances


def stream_logs(
    instance: str,
    *,
    zone: str = "us-central1-a",
    project: str | None = None,
    follow: bool = True,
) -> subprocess.Popen[str]:
    """Stream logs from a remote instance via SSH.

    Returns a Popen object. The caller should read from stdout.
    """
    cmd = [
        "gcloud", "compute", "ssh", instance,
        "--zone", zone,
        "--command", "tail -f /var/log/agents-task.log" if follow else "cat /var/log/agents-task.log",
    ]
    if project:
        cmd.extend(["--project", project])

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop_instance(
    instance: str,
    *,
    zone: str = "us-central1-a",
    project: str | None = None,
) -> dict[str, str]:
    """Gracefully stop a remote instance using the teardown script."""
    cmd_args = [
        "compute", "instances", "delete", instance,
        "--zone", zone,
        "--quiet",
    ]
    if project:
        cmd_args.extend(["--project", project])

    result = _run_gcloud(*cmd_args)
    if result.returncode != 0:
        return {
            "instance": instance,
            "status": "FAILED",
            "error": result.stderr.strip(),
        }

    return {
        "instance": instance,
        "status": "DELETED",
    }


def get_repo_url() -> str:
    """Detect the current repo's remote URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def get_current_branch() -> str:
    """Detect the current git branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return "main"
