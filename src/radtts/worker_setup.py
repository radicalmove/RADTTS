"""Cross-platform helper to register and auto-start a RADTTS worker."""

from __future__ import annotations

import argparse
import json
import os
import platform
import plistlib
import shlex
import socket
import subprocess
import sys
from pathlib import Path

import requests


def normalize_platform(value: str) -> str:
    raw = value.strip().lower()
    if raw == "auto":
        name = platform.system().lower()
        if "windows" in name:
            return "windows"
        if "darwin" in name or "mac" in name:
            return "macos"
        return "linux"
    if raw in {"windows", "linux", "macos"}:
        return raw
    raise ValueError(f"Unsupported platform: {value}")


def build_worker_command_args(
    *,
    python_exe: Path,
    server_url: str,
    config_path: Path,
    poll_seconds: int,
) -> list[str]:
    return [
        str(python_exe),
        "-m",
        "radtts.worker_client",
        "--server-url",
        server_url.rstrip("/"),
        "--config-path",
        str(config_path),
        "--poll-seconds",
        str(max(1, int(poll_seconds))),
    ]


def linux_service_unit_text(
    *,
    python_exe: Path,
    server_url: str,
    config_path: Path,
    poll_seconds: int,
) -> str:
    command = shlex.join(
        build_worker_command_args(
            python_exe=python_exe,
            server_url=server_url,
            config_path=config_path,
            poll_seconds=poll_seconds,
        )
    )
    return (
        "[Unit]\n"
        "Description=RADTTS Worker (user)\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={command}\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def macos_launch_agent_payload(
    *,
    label: str,
    python_exe: Path,
    server_url: str,
    config_path: Path,
    poll_seconds: int,
) -> dict[str, object]:
    logs_dir = config_path.parent
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / "worker.log"
    stderr_path = logs_dir / "worker.err.log"
    return {
        "Label": label,
        "ProgramArguments": build_worker_command_args(
            python_exe=python_exe,
            server_url=server_url,
            config_path=config_path,
            poll_seconds=poll_seconds,
        ),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(stdout_path),
        "StandardErrorPath": str(stderr_path),
    }


def windows_task_command(
    *,
    python_exe: Path,
    server_url: str,
    config_path: Path,
    poll_seconds: int,
) -> str:
    args = build_worker_command_args(
        python_exe=python_exe,
        server_url=server_url,
        config_path=config_path,
        poll_seconds=poll_seconds,
    )
    return subprocess.list2cmdline(args)


def _run_command(cmd: list[str], *, required: bool) -> bool:
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        if required:
            raise RuntimeError(f"Command not found: {cmd[0]}") from None
        return False

    if result.returncode != 0:
        if required:
            message = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise RuntimeError(f"Command failed ({' '.join(cmd)}): {message}")
        return False
    return True


def _register_worker_if_needed(
    *,
    server_url: str,
    invite_token: str | None,
    worker_name: str,
    config_path: Path,
) -> str:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists() and not invite_token:
        existing = json.loads(config_path.read_text(encoding="utf-8"))
        if existing.get("worker_id") and existing.get("api_key"):
            return "Reused existing worker credentials."

    if not invite_token:
        raise RuntimeError(
            "Worker is not registered yet. Provide --invite-token for first-time setup."
        )

    response = requests.post(
        f"{server_url.rstrip('/')}/workers/register",
        json={
            "invite_token": invite_token,
            "worker_name": worker_name,
            "capabilities": ["synthesize"],
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Worker registration failed: {response.status_code} {response.text[:400]}")

    payload = response.json()
    worker_id = payload.get("worker_id")
    api_key = payload.get("api_key")
    if not worker_id or not api_key:
        raise RuntimeError("Worker registration response missing worker_id/api_key")

    config_path.write_text(
        json.dumps(
            {
                "server_url": server_url.rstrip("/"),
                "worker_id": worker_id,
                "api_key": api_key,
                "worker_name": worker_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return "Registered a new worker and saved credentials."


def _install_linux_autostart(
    *,
    python_exe: Path,
    server_url: str,
    config_path: Path,
    poll_seconds: int,
) -> str:
    service_path = Path.home() / ".config" / "systemd" / "user" / "radtts-worker.service"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    service_path.write_text(
        linux_service_unit_text(
            python_exe=python_exe,
            server_url=server_url,
            config_path=config_path,
            poll_seconds=poll_seconds,
        ),
        encoding="utf-8",
    )
    _run_command(["systemctl", "--user", "daemon-reload"], required=False)
    _run_command(["systemctl", "--user", "enable", "--now", "radtts-worker.service"], required=False)
    return f"Installed user service: {service_path}"


def _install_macos_autostart(
    *,
    python_exe: Path,
    server_url: str,
    config_path: Path,
    poll_seconds: int,
) -> str:
    label = "com.radtts.worker"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    payload = macos_launch_agent_payload(
        label=label,
        python_exe=python_exe,
        server_url=server_url,
        config_path=config_path,
        poll_seconds=poll_seconds,
    )
    with plist_path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)

    uid = str(os.getuid())
    _run_command(["launchctl", "bootout", f"gui/{uid}", str(plist_path)], required=False)
    _run_command(["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)], required=False)
    _run_command(["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"], required=False)
    return f"Installed LaunchAgent: {plist_path}"


def _install_windows_autostart(
    *,
    python_exe: Path,
    server_url: str,
    config_path: Path,
    poll_seconds: int,
) -> str:
    task_name = "RADTTS Worker"
    command = windows_task_command(
        python_exe=python_exe,
        server_url=server_url,
        config_path=config_path,
        poll_seconds=poll_seconds,
    )
    _run_command(
        [
            "schtasks",
            "/Create",
            "/F",
            "/TN",
            task_name,
            "/SC",
            "ONLOGON",
            "/TR",
            command,
            "/RL",
            "LIMITED",
        ],
        required=False,
    )
    _run_command(["schtasks", "/Run", "/TN", task_name], required=False)
    return f"Installed Scheduled Task: {task_name}"


def _format_command_for_display(args: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(args)
    return shlex.join(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register RADTTS worker and install OS autostart background service.",
    )
    parser.add_argument("--server-url", required=True, help="RADTTS server base URL")
    parser.add_argument("--invite-token", help="Required for first-time registration")
    parser.add_argument("--worker-name", default=socket.gethostname())
    parser.add_argument(
        "--config-path",
        default=str(Path.home() / ".radtts" / "worker.json"),
        help="Worker credential cache path",
    )
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument(
        "--platform",
        default="auto",
        choices=["auto", "windows", "macos", "linux"],
        help="Target platform for autostart install",
    )
    parser.add_argument(
        "--python-exe",
        default=sys.executable,
        help="Python executable used by autostart process",
    )
    parser.add_argument(
        "--skip-autostart",
        action="store_true",
        help="Only register worker; do not install startup service",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    server_url = args.server_url.rstrip("/")
    config_path = Path(args.config_path).expanduser()
    python_exe = Path(args.python_exe).expanduser()
    selected_platform = normalize_platform(args.platform)

    registration_message = _register_worker_if_needed(
        server_url=server_url,
        invite_token=args.invite_token,
        worker_name=args.worker_name,
        config_path=config_path,
    )
    print(registration_message)

    if args.skip_autostart:
        print("Skipped autostart install.")
    elif selected_platform == "linux":
        print(
            _install_linux_autostart(
                python_exe=python_exe,
                server_url=server_url,
                config_path=config_path,
                poll_seconds=args.poll_seconds,
            )
        )
    elif selected_platform == "macos":
        print(
            _install_macos_autostart(
                python_exe=python_exe,
                server_url=server_url,
                config_path=config_path,
                poll_seconds=args.poll_seconds,
            )
        )
    elif selected_platform == "windows":
        print(
            _install_windows_autostart(
                python_exe=python_exe,
                server_url=server_url,
                config_path=config_path,
                poll_seconds=args.poll_seconds,
            )
        )
    else:  # pragma: no cover
        raise RuntimeError(f"Unsupported platform: {selected_platform}")

    manual_command = _format_command_for_display(
        build_worker_command_args(
            python_exe=python_exe,
            server_url=server_url,
            config_path=config_path,
            poll_seconds=args.poll_seconds,
        )
    )
    print(f"Manual start command: {manual_command}")


if __name__ == "__main__":
    main()
