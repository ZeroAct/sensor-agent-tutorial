"""Merge dummy-plant into Claude Desktop's claude_desktop_config.json."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER_ID = "dummy-plant"


def uv_executable() -> str:
    found = shutil.which("uv")
    if found:
        return str(Path(found).resolve())
    local = Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")
    if local.exists():
        return str(local.resolve())
    raise SystemExit("uv 를 찾지 못했습니다. 새 터미널에서 `uv --version` 후 다시 실행하세요.")


def server_entry() -> dict:
    return {
        "command": uv_executable(),
        "args": ["run", "--directory", str(ROOT), "plant-mcp"],
    }


def config_paths() -> list[Path]:
    home = Path.home()
    paths = [
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
        home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    ]
    existing_dirs = [path for path in paths if path.parent.exists()]
    if existing_dirs:
        return existing_dirs
    return [paths[0]]


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
    print("dummy-plant MCP 를 Claude Desktop 설정에 넣었습니다.", flush=True)
    for path in written:
        print(f"  {path}", flush=True)
    print("Claude Desktop 을 트레이까지 종료한 뒤 다시 여세요.", flush=True)
    print("공장 지도는 다른 터미널에서 `uv run plant` 로 켭니다.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
