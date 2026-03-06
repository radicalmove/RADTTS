from __future__ import annotations

from pathlib import Path

from radtts.worker_setup import (
    build_worker_command_args,
    linux_service_unit_text,
    normalize_platform,
    windows_task_command,
)


def test_normalize_platform_auto_resolves_known_targets():
    value = normalize_platform("auto")
    assert value in {"linux", "macos", "windows"}


def test_build_worker_command_args_contains_required_flags():
    args = build_worker_command_args(
        python_exe=Path("/opt/radtts/.venv/bin/python"),
        server_url="https://example.com/",
        config_path=Path("/home/user/.radtts/worker.json"),
        poll_seconds=3,
    )
    assert args[0] == "/opt/radtts/.venv/bin/python"
    assert args[1:3] == ["-m", "radtts.worker_client"]
    assert "--server-url" in args
    assert "https://example.com" in args
    assert "--config-path" in args
    assert "/home/user/.radtts/worker.json" in args


def test_linux_service_unit_contains_execstart_and_restart():
    text = linux_service_unit_text(
        python_exe=Path("/opt/radtts/.venv/bin/python"),
        server_url="http://127.0.0.1:8011",
        config_path=Path("/home/user/.radtts/worker.json"),
        poll_seconds=5,
    )
    assert "Description=RADTTS Worker (user)" in text
    assert "ExecStart=" in text
    assert "radtts.worker_client" in text
    assert "Restart=always" in text


def test_windows_task_command_references_worker_module_and_flags():
    command = windows_task_command(
        python_exe=Path(r"C:\radtts\.venv\Scripts\python.exe"),
        server_url="https://worker.example.com",
        config_path=Path(r"C:\Users\demo\.radtts\worker.json"),
        poll_seconds=7,
    )
    assert "radtts.worker_client" in command
    assert "--server-url" in command
    assert "https://worker.example.com" in command
    assert "--config-path" in command
    assert "worker.json" in command
