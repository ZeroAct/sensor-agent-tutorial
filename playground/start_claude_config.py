"""Merge dummy-plant into Claude Desktop's claude_desktop_config.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER_ID = "dummy-plant"
SCRIPT = ROOT / "start_plant_mcp.py"


def venv_python() -> Path:
    if os.name == "nt":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def config_candidates(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    windows = [
        home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        home
        / "AppData"
        / "Local"
        / "Packages"
        / "Claude_pzs8sxrjxfjjc"
        / "LocalCache"
        / "Roaming"
        / "Claude"
        / "claude_desktop_config.json",
    ]
    mac = [
        home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    ]
    if sys.platform == "darwin":
        return mac
    if os.name == "nt":
        return windows
    return mac + windows


def server_entry() -> dict:
    py = venv_python()
    if not py.exists():
        raise SystemExit(
            "playground/.venv 이 없습니다. 먼저 `uv run plant` 또는 `uv sync` 후 다시 실행하세요."
        )
    return {
        "command": str(py.resolve()),
        "args": [str(SCRIPT)],
        "cwd": str(ROOT),
        "env": {
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "FASTMCP_SHOW_CLI_BANNER": "false",
        },
    }


def config_paths() -> list[Path]:
    paths = config_candidates()
    existing = [path for path in paths if path.parent.exists()]
    return existing or [paths[0]]


def merge_config(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {"mcpServers": {}}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data = loaded
        data.setdefault("mcpServers", {})
    data["mcpServers"][SERVER_ID] = entry
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    entry = server_entry()
    written = []
    for path in config_paths():
        merge_config(path, entry)
        written.append(str(path))
    print("dummy-plant MCP 를 Claude Desktop 설정에 넣었습니다. (stdio)", flush=True)
    print(f"  {entry['command']}", flush=True)
    print(f"  {entry['args'][0]}", flush=True)
    for path in written:
        print(f"  {path}", flush=True)
    if sys.platform == "darwin":
        print("Claude Desktop 을 완전히 종료하세요. 메뉴 막대 Claude → Quit Claude (Cmd+Q).", flush=True)
        print("빨간 점만 누르면 Dock/메뉴에 남아 설정이 안 읽힙니다.", flush=True)
    else:
        print("Claude Desktop 을 트레이까지 종료한 뒤 다시 여세요.", flush=True)
    print("공장 지도는 다른 터미널에서 `uv run plant` 로 켭니다.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
