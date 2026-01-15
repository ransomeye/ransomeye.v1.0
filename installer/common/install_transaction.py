#!/usr/bin/env python3
"""
RansomEye v1.0 Installer Transaction Framework
AUTHORITATIVE: Unified install-time rollback management
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

STATE_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)


def _parse_meta(pairs: List[str]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid meta format (expected key=value): {pair}")
        key, value = pair.split("=", 1)
        meta[key] = value
    return meta


def init_state(state_file: Path, component: str) -> None:
    state = {
        "state_version": STATE_VERSION,
        "component": component,
        "created_at": _now(),
        "steps": []
    }
    _write_state(state_file, state)


def record_step(state_file: Path, action: str, meta: Dict[str, str],
                rollback_action: str, rollback_meta: Dict[str, str]) -> None:
    state = _load_state(state_file)
    if not state:
        raise RuntimeError(f"State file not initialized: {state_file}")
    state["steps"].append({
        "action": action,
        "meta": meta,
        "rollback_action": rollback_action,
        "rollback_meta": rollback_meta,
        "recorded_at": _now()
    })
    _write_state(state_file, state)


def _safe_remove_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file() or path.is_symlink():
        path.unlink(missing_ok=True)
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for filename in files:
            file_path = Path(root) / filename
            file_path.unlink(missing_ok=True)
        for dirname in dirs:
            dir_path = Path(root) / dirname
            try:
                dir_path.rmdir()
            except OSError:
                pass
    try:
        path.rmdir()
    except OSError:
        pass


def _audit_action(action: str, meta: Dict[str, str]) -> None:
    audit_path = os.getenv("RANSOMEYE_ROLLBACK_AUDIT_FILE")
    if not audit_path:
        return
    audit_file = Path(audit_path)
    entries = []
    if audit_file.exists():
        entries = json.loads(audit_file.read_text(encoding="utf-8"))
    entries.append({"action": action, "meta": meta, "timestamp": _now()})
    audit_file.write_text(json.dumps(entries, indent=2, sort_keys=True), encoding="utf-8")


def _run_command(args: List[str], env: Dict[str, str] = None, action: str = None, meta: Dict[str, str] = None) -> None:
    if os.getenv("RANSOMEYE_ROLLBACK_SIMULATE") == "1":
        if action:
            _audit_action(action, meta or {})
        return
    subprocess.run(args, check=True, env=env)


def _rollback_remove_path(meta: Dict[str, str]) -> None:
    path = Path(meta["path"])
    if os.getenv("RANSOMEYE_ROLLBACK_SIMULATE") == "1":
        _audit_action("remove_path", meta)
        return
    if path.is_file() or path.is_symlink():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        _safe_remove_tree(path)


def _rollback_remove_dir(meta: Dict[str, str]) -> None:
    path = Path(meta["path"])
    if os.getenv("RANSOMEYE_ROLLBACK_SIMULATE") == "1":
        _audit_action("remove_dir", meta)
        return
    if path.exists() and path.is_dir():
        try:
            path.rmdir()
        except OSError:
            _safe_remove_tree(path)


def _rollback_remove_tree(meta: Dict[str, str]) -> None:
    if os.getenv("RANSOMEYE_ROLLBACK_SIMULATE") == "1":
        _audit_action("remove_tree", meta)
        return
    _safe_remove_tree(Path(meta["path"]))


def _rollback_remove_user(meta: Dict[str, str]) -> None:
    username = meta["username"]
    system = platform.system().lower()
    if system == "windows":
        _run_command(["net", "user", username, "/delete"])
    else:
        _run_command(["userdel", username])


def _rollback_remove_group(meta: Dict[str, str]) -> None:
    group = meta["group"]
    _run_command(["groupdel", group])


def _rollback_remove_systemd_service(meta: Dict[str, str]) -> None:
    service = meta["service"]
    service_file = meta.get("service_file")
    _run_command(["systemctl", "stop", service], action="remove_systemd_service", meta=meta)
    _run_command(["systemctl", "disable", service], action="remove_systemd_service", meta=meta)
    if service_file:
        Path(service_file).unlink(missing_ok=True)
    _run_command(["systemctl", "daemon-reload"], action="remove_systemd_service", meta=meta)


def _rollback_remove_windows_service(meta: Dict[str, str]) -> None:
    service = meta["service"]
    _run_command(["sc", "stop", service], action="remove_windows_service", meta=meta)
    _run_command(["sc", "delete", service], action="remove_windows_service", meta=meta)
    registry_key = meta.get("registry_key")
    if registry_key:
        _run_command(["reg", "delete", registry_key, "/f"], action="remove_windows_service", meta=meta)


def _rollback_remove_capabilities(meta: Dict[str, str]) -> None:
    binary_path = meta["path"]
    _run_command(["setcap", "-r", binary_path], action="remove_capabilities", meta=meta)


def _rollback_registry_delete(meta: Dict[str, str]) -> None:
    key = meta["key"]
    _run_command(["reg", "delete", key, "/f"], action="remove_registry_key", meta=meta)


def _rollback_migrations(meta: Dict[str, str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = meta["pythonpath"]
    env["RANSOMEYE_DB_HOST"] = meta["db_host"]
    env["RANSOMEYE_DB_PORT"] = meta["db_port"]
    env["RANSOMEYE_DB_NAME"] = meta["db_name"]
    env["RANSOMEYE_DB_USER"] = meta["db_user"]
    env["RANSOMEYE_DB_PASSWORD"] = meta["db_password"]
    migrations_dir = meta["migrations_dir"]
    target = meta.get("target_version", "0")
    _run_command(
        ["python3", "-m", "common.db.migration_runner", "downgrade",
         "--migrations-dir", migrations_dir, "--target-version", target],
        env=env,
        action="rollback_migrations",
        meta=meta
    )


ROLLBACK_HANDLERS = {
    "remove_path": _rollback_remove_path,
    "remove_dir": _rollback_remove_dir,
    "remove_tree": _rollback_remove_tree,
    "remove_user": _rollback_remove_user,
    "remove_group": _rollback_remove_group,
    "remove_systemd_service": _rollback_remove_systemd_service,
    "remove_windows_service": _rollback_remove_windows_service,
    "remove_capabilities": _rollback_remove_capabilities,
    "remove_registry_key": _rollback_registry_delete,
    "rollback_migrations": _rollback_migrations
}


def rollback(state_file: Path) -> int:
    state = _load_state(state_file)
    if not state:
        raise RuntimeError(f"State file not found: {state_file}")
    steps = state.get("steps", [])
    errors: List[str] = []
    for step in reversed(steps):
        action = step.get("rollback_action")
        meta = step.get("rollback_meta", {})
        handler = ROLLBACK_HANDLERS.get(action)
        if not handler:
            errors.append(f"Unknown rollback action: {action}")
            continue
        try:
            handler(meta)
        except Exception as exc:
            errors.append(f"{action} failed: {exc}")
    if errors:
        print("ROLLBACK FAILED:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Installer transaction logger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--state-file", required=True)
    init_parser.add_argument("--component", required=True)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--state-file", required=True)
    record_parser.add_argument("--action", required=True)
    record_parser.add_argument("--rollback-action", required=True)
    record_parser.add_argument("--meta", action="append", default=[])
    record_parser.add_argument("--rollback-meta", action="append", default=[])

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--state-file", required=True)

    args = parser.parse_args()
    state_file = Path(args.state_file)

    if args.command == "init":
        init_state(state_file, args.component)
        if platform.system().lower() != "windows":
            os.chmod(state_file, 0o600)
        return

    if args.command == "record":
        meta = _parse_meta(args.meta)
        rollback_meta = _parse_meta(args.rollback_meta)
        record_step(state_file, args.action, meta, args.rollback_action, rollback_meta)
        return

    if args.command == "rollback":
        exit_code = rollback(state_file)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
