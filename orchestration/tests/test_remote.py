"""Tests for the remote GCP instance management module."""

import json
from unittest.mock import MagicMock, patch

from orchestration.remote import (
    RemoteInstance,
    _instance_name,
    _run_gcloud,
    get_current_branch,
    get_repo_url,
    launch_instance,
    list_instances,
    stop_instance,
    stream_logs,
)


# ---------------------------------------------------------------------------
# Instance naming
# ---------------------------------------------------------------------------

class TestInstanceName:
    def test_name_from_issue(self):
        assert _instance_name("Fix bug", issue=42, pr=None) == "agents-task-42"

    def test_name_from_pr(self):
        assert _instance_name("Fix bug", issue=None, pr=18) == "agents-pr-18"

    def test_name_from_timestamp(self):
        name = _instance_name("Fix bug", issue=None, pr=None)
        assert name.startswith("agents-task-")
        # Timestamp portion is numeric
        ts_part = name.replace("agents-task-", "")
        assert ts_part.isdigit()

    def test_issue_takes_precedence_over_pr(self):
        assert _instance_name("Fix", issue=10, pr=20) == "agents-task-10"


# ---------------------------------------------------------------------------
# RemoteInstance dataclass
# ---------------------------------------------------------------------------

class TestRemoteInstance:
    def test_basic_creation(self):
        inst = RemoteInstance(
            name="agents-task-42",
            zone="us-central1-a",
            status="RUNNING",
            machine_type="e2-standard-2",
            created_at="2026-01-01T00:00:00Z",
        )
        assert inst.name == "agents-task-42"
        assert inst.issue is None
        assert inst.pr is None
        assert inst.metadata == {}

    def test_with_task_context(self):
        inst = RemoteInstance(
            name="agents-task-42",
            zone="us-east1-b",
            status="RUNNING",
            machine_type="e2-standard-4",
            created_at="2026-01-01T00:00:00Z",
            task="Fix the auth bug",
            issue=42,
        )
        assert inst.task == "Fix the auth bug"
        assert inst.issue == 42


# ---------------------------------------------------------------------------
# _run_gcloud
# ---------------------------------------------------------------------------

class TestRunGcloud:
    @patch("orchestration.remote.subprocess.run")
    def test_calls_gcloud_with_args(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = _run_gcloud("compute", "instances", "list")
        mock_run.assert_called_once_with(
            ["gcloud", "compute", "instances", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# launch_instance
# ---------------------------------------------------------------------------

class TestLaunchInstance:
    def test_dry_run_returns_plan(self):
        result = launch_instance(
            "Fix the auth bug",
            repo="https://github.com/user/repo.git",
            issue=42,
            dry_run=True,
        )
        assert result["status"] == "DRY_RUN"
        assert result["name"] == "agents-task-42"
        assert "gcloud" in result["command"]

    def test_dry_run_with_pr(self):
        result = launch_instance(
            "Update PR",
            repo="https://github.com/user/repo.git",
            pr=18,
            dry_run=True,
        )
        assert result["name"] == "agents-pr-18"

    @patch("orchestration.remote._run_gcloud")
    def test_launch_success(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"name": "agents-task-42"}]),
        )
        result = launch_instance(
            "Fix bug",
            repo="https://github.com/user/repo.git",
            issue=42,
        )
        assert result["status"] == "LAUNCHING"
        assert result["name"] == "agents-task-42"

    @patch("orchestration.remote._run_gcloud")
    def test_launch_failure(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(
            returncode=1,
            stderr="Quota exceeded",
        )
        result = launch_instance(
            "Fix bug",
            repo="https://github.com/user/repo.git",
            issue=42,
        )
        assert result["status"] == "FAILED"
        assert "Quota exceeded" in result["error"]

    def test_deploy_mode_in_metadata(self):
        result = launch_instance(
            "Watch comments",
            repo="https://github.com/user/repo.git",
            issue=42,
            deploy_mode=True,
            dry_run=True,
        )
        assert "deploy_mode=true" in result["command"]

    def test_custom_machine_type(self):
        result = launch_instance(
            "Heavy task",
            repo="https://github.com/user/repo.git",
            machine_type="e2-standard-8",
            dry_run=True,
        )
        assert result["machine_type"] == "e2-standard-8"

    def test_custom_zone(self):
        result = launch_instance(
            "Task",
            repo="https://github.com/user/repo.git",
            zone="europe-west1-b",
            dry_run=True,
        )
        assert result["zone"] == "europe-west1-b"

    def test_custom_timeout(self):
        result = launch_instance(
            "Long task",
            repo="https://github.com/user/repo.git",
            timeout_hours=8,
            dry_run=True,
        )
        assert "timeout_hours=8" in result["command"]

    def test_custom_branch(self):
        result = launch_instance(
            "Task",
            repo="https://github.com/user/repo.git",
            branch="feat/new-feature",
            dry_run=True,
        )
        assert "branch=feat/new-feature" in result["command"]

    def test_project_in_command(self):
        result = launch_instance(
            "Task",
            repo="https://github.com/user/repo.git",
            project="my-project",
            dry_run=True,
        )
        assert "my-project" in result["command"]


# ---------------------------------------------------------------------------
# list_instances
# ---------------------------------------------------------------------------

class TestListInstances:
    @patch("orchestration.remote._run_gcloud")
    def test_parses_instance_list(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {
                    "name": "agents-task-42",
                    "zone": "projects/p/zones/us-central1-a",
                    "status": "RUNNING",
                    "machineType": "projects/p/machineTypes/e2-standard-2",
                    "creationTimestamp": "2026-01-01T00:00:00Z",
                    "metadata": {
                        "items": [
                            {"key": "task", "value": "Fix auth"},
                            {"key": "issue", "value": "42"},
                        ]
                    },
                }
            ]),
        )

        instances = list_instances()
        assert len(instances) == 1
        inst = instances[0]
        assert inst.name == "agents-task-42"
        assert inst.zone == "us-central1-a"
        assert inst.status == "RUNNING"
        assert inst.machine_type == "e2-standard-2"
        assert inst.task == "Fix auth"
        assert inst.issue == 42

    @patch("orchestration.remote._run_gcloud")
    def test_empty_on_failure(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(returncode=1, stdout="")
        assert list_instances() == []

    @patch("orchestration.remote._run_gcloud")
    def test_empty_on_invalid_json(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(returncode=0, stdout="not json")
        assert list_instances() == []

    @patch("orchestration.remote._run_gcloud")
    def test_multiple_instances(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {
                    "name": "agents-task-1",
                    "zone": "projects/p/zones/us-central1-a",
                    "status": "RUNNING",
                    "machineType": "e2-standard-2",
                    "creationTimestamp": "2026-01-01T00:00:00Z",
                    "metadata": {"items": []},
                },
                {
                    "name": "agents-pr-5",
                    "zone": "projects/p/zones/us-east1-b",
                    "status": "STAGING",
                    "machineType": "e2-standard-4",
                    "creationTimestamp": "2026-01-02T00:00:00Z",
                    "metadata": {
                        "items": [{"key": "pr", "value": "5"}],
                    },
                },
            ]),
        )

        instances = list_instances()
        assert len(instances) == 2
        assert instances[0].name == "agents-task-1"
        assert instances[1].pr == 5

    @patch("orchestration.remote._run_gcloud")
    def test_project_passed_to_gcloud(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(returncode=0, stdout="[]")
        list_instances(project="my-project")
        call_args = mock_gcloud.call_args[0]
        assert "--project" in call_args
        assert "my-project" in call_args


# ---------------------------------------------------------------------------
# stream_logs
# ---------------------------------------------------------------------------

class TestStreamLogs:
    @patch("orchestration.remote.subprocess.Popen")
    def test_streams_with_follow(self, mock_popen):
        mock_popen.return_value = MagicMock()
        stream_logs("agents-task-42")
        call_args = mock_popen.call_args[0][0]
        assert "tail -f /var/log/agents-task.log" in " ".join(call_args)

    @patch("orchestration.remote.subprocess.Popen")
    def test_streams_without_follow(self, mock_popen):
        mock_popen.return_value = MagicMock()
        stream_logs("agents-task-42", follow=False)
        call_args = mock_popen.call_args[0][0]
        assert "cat /var/log/agents-task.log" in " ".join(call_args)

    @patch("orchestration.remote.subprocess.Popen")
    def test_includes_zone_and_project(self, mock_popen):
        mock_popen.return_value = MagicMock()
        stream_logs("inst", zone="europe-west1-b", project="proj")
        call_args = mock_popen.call_args[0][0]
        assert "--zone" in call_args
        assert "europe-west1-b" in call_args
        assert "--project" in call_args
        assert "proj" in call_args


# ---------------------------------------------------------------------------
# stop_instance
# ---------------------------------------------------------------------------

class TestStopInstance:
    @patch("orchestration.remote._run_gcloud")
    def test_stop_success(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(returncode=0)
        result = stop_instance("agents-task-42")
        assert result["status"] == "DELETED"
        assert result["instance"] == "agents-task-42"

    @patch("orchestration.remote._run_gcloud")
    def test_stop_failure(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(returncode=1, stderr="Not found")
        result = stop_instance("agents-task-99")
        assert result["status"] == "FAILED"
        assert "Not found" in result["error"]

    @patch("orchestration.remote._run_gcloud")
    def test_stop_passes_zone_and_project(self, mock_gcloud):
        mock_gcloud.return_value = MagicMock(returncode=0)
        stop_instance("inst", zone="us-west1-a", project="proj")
        call_args = mock_gcloud.call_args[0]
        assert "us-west1-a" in call_args
        assert "proj" in call_args


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

class TestGitHelpers:
    @patch("orchestration.remote.subprocess.run")
    def test_get_repo_url(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/repo.git\n",
        )
        assert get_repo_url() == "https://github.com/user/repo.git"

    @patch("orchestration.remote.subprocess.run")
    def test_get_repo_url_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert get_repo_url() == ""

    @patch("orchestration.remote.subprocess.run")
    def test_get_current_branch(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="feat/my-feature\n",
        )
        assert get_current_branch() == "feat/my-feature"

    @patch("orchestration.remote.subprocess.run")
    def test_get_current_branch_fallback(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert get_current_branch() == "main"


# ---------------------------------------------------------------------------
# CLI integration (eco remote ...)
# ---------------------------------------------------------------------------

class TestRemoteCLI:
    def test_remote_no_subcommand(self):
        from orchestration.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["remote"])
        assert args.command == "remote"
        assert getattr(args, "remote_command", None) is None

    def test_remote_run_parser(self):
        from orchestration.cli import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "remote", "run", "Fix the auth bug",
            "--issue", "42",
            "--machine-type", "e2-standard-4",
            "--zone", "us-east1-b",
            "--timeout", "8",
            "--deploy",
            "--dry-run",
        ])
        assert args.remote_command == "run"
        assert args.input == "Fix the auth bug"
        assert args.issue == 42
        assert args.machine_type == "e2-standard-4"
        assert args.zone == "us-east1-b"
        assert args.timeout == 8
        assert args.deploy is True
        assert args.dry_run is True

    def test_remote_status_parser(self):
        from orchestration.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["remote", "status", "--format", "json"])
        assert args.remote_command == "status"
        assert args.format == "json"

    def test_remote_logs_parser(self):
        from orchestration.cli import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "remote", "logs", "agents-task-42",
            "--zone", "us-west1-a",
            "--no-follow",
        ])
        assert args.remote_command == "logs"
        assert args.instance == "agents-task-42"
        assert args.zone == "us-west1-a"
        assert args.no_follow is True

    def test_remote_stop_parser(self):
        from orchestration.cli import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "remote", "stop", "agents-task-42",
            "--project", "my-project",
        ])
        assert args.remote_command == "stop"
        assert args.instance == "agents-task-42"
        assert args.project == "my-project"

    @patch("orchestration.remote.launch_instance")
    @patch("orchestration.remote.get_current_branch", return_value="main")
    @patch("orchestration.remote.get_repo_url", return_value="https://github.com/user/repo.git")
    def test_cmd_remote_run_dry_run(self, mock_repo, mock_branch, mock_launch):
        from orchestration.cli import cmd_remote_run, create_parser

        mock_launch.return_value = {
            "name": "agents-task-42",
            "zone": "us-central1-a",
            "machine_type": "e2-standard-2",
            "task": "Fix bug",
            "status": "DRY_RUN",
            "command": "gcloud compute instances create ...",
        }

        parser = create_parser()
        args = parser.parse_args([
            "remote", "run", "Fix bug", "--issue", "42", "--dry-run",
        ])
        rc = cmd_remote_run(args)
        assert rc == 0
        mock_launch.assert_called_once()

    @patch("orchestration.remote.list_instances")
    def test_cmd_remote_status_empty(self, mock_list):
        from orchestration.cli import cmd_remote_status, create_parser

        mock_list.return_value = []
        parser = create_parser()
        args = parser.parse_args(["remote", "status"])
        rc = cmd_remote_status(args)
        assert rc == 0

    @patch("orchestration.remote.stop_instance")
    def test_cmd_remote_stop_success(self, mock_stop):
        from orchestration.cli import cmd_remote_stop, create_parser

        mock_stop.return_value = {"instance": "agents-task-42", "status": "DELETED"}
        parser = create_parser()
        args = parser.parse_args(["remote", "stop", "agents-task-42"])
        rc = cmd_remote_stop(args)
        assert rc == 0

    @patch("orchestration.remote.stop_instance")
    def test_cmd_remote_stop_failure(self, mock_stop):
        from orchestration.cli import cmd_remote_stop, create_parser

        mock_stop.return_value = {"instance": "x", "status": "FAILED", "error": "Not found"}
        parser = create_parser()
        args = parser.parse_args(["remote", "stop", "x"])
        rc = cmd_remote_stop(args)
        assert rc == 1
