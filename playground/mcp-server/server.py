"""Dummy-plant MCP server (Streamable HTTP on :8000).

Read tools:
  - list_assets
  - get_asset
  - list_sensors
  - get_vibration_reading
  - get_recent_events

Write tools (dummy sandbox only):
  - set_asset_power
  - fail_asset
  - replace_asset
  - request_fix  (does NOT apply; worker Accepts on the map)

Read last_reason / anomaly counts / pending FIX via get_asset or list_assets.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse

_HERE = Path(__file__).resolve().parent
for _path in (_HERE, _HERE.parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import plant
from factory_catalog import asset_ids, sensor_ids

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8000"))
PATH = os.getenv("MCP_PATH", "/mcp")
STATIC_DIR = Path(__file__).resolve().parent / "static"

mcp = FastMCP(
    "dummy-plant",
    instructions=(
        "Classroom dummy plant. Always call a tool for live numbers and state. "
        "Never invent RMS, serials, timestamps, or IDs. "
        "Write tools (set_asset_power, fail_asset, replace_asset) change THIS "
        "sandbox only. They are not a real maintenance permit. "
        "request_fix asks a human worker; it does not apply the wrench. "
        "The worker Accepts on http://localhost:8000 . Then re-read the asset. "
        "After a write, read the asset or sensor again to confirm. "
        "If a machine is off or failed, last_reason explains why. "
        "Three vibration anomalies on the same sensor/generation trip the asset. "
        "FIX resets counts (same serial) and can run before a trip."
    ),
)


def _pretty(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool
def list_assets() -> str:
    """List equipment instances: power, health, serial, last_reason, anomaly counts.

    Call this when the user asks which machines exist, what is running,
    which unit failed, or why something turned off.
    """
    return _pretty(
        {
            "note": "Dummy equipment instances. Side effects are recorded in SQLite.",
            "plant": "dummy-cooling-plant",
            "assets": plant.snapshot_assets(),
        }
    )


@mcp.tool
def list_sensors() -> str:
    """List vibration sensors, last RMS, and the parent asset state."""
    return _pretty(
        {
            "note": "Dummy classroom plant. Live values, not invented by the model.",
            "plant": "dummy-cooling-plant",
            "view": "top-down",
            "sensors": plant.snapshot_sensors(),
        }
    )


@mcp.tool
def get_asset(asset_id: str) -> str:
    """Return one equipment instance: power, health, last_reason, anomaly counts.

    Use this to explain why a machine is off or failed. last_reason is
    persisted in SQLite (ui / mcp / trip).
    """
    wanted = (asset_id or "").strip()
    if not wanted:
        return _pretty({"error": "asset_id is required", "known_assets": asset_ids()})
    row = plant.get_asset_state(wanted)
    if row is None:
        return _pretty(
            {
                "error": "unknown asset_id",
                "asset_id": wanted,
                "known_assets": asset_ids(),
            }
        )
    return _pretty({"note": "Dummy equipment instance from SQLite.", "asset": row})


@mcp.tool
def get_vibration_reading(sensor_id: str) -> str:
    """Return the latest vibration reading for one sensor.

    Known ids come from list_sensors. The protagonist spike sensor is pump-a-de.
    """
    wanted = (sensor_id or "").strip()
    if not wanted:
        return _pretty({"error": "sensor_id is required"})
    row = plant.latest_reading(wanted)
    if row is None:
        return _pretty(
            {
                "error": "no reading yet for this sensor_id",
                "sensor_id": wanted,
                "known_sensors": sensor_ids(),
            }
        )
    return _pretty({"note": "Latest dummy reading from SQLite.", "reading": row})


@mcp.tool
def get_recent_events(limit: int = 10, kind: str = "", asset_id: str = "") -> str:
    """Return recent plant events: anomaly, power, fail, replace, fix, fix_request.

    Omit kind for the mixed log. Pass asset_id to read one equipment's log.
    Use kind='anomaly' for vibration alarms only.
    """
    wanted_kind = (kind or "").strip() or None
    wanted_asset = (asset_id or "").strip() or None
    rows = plant.recent_events(limit, kind=wanted_kind, asset_id=wanted_asset)
    return _pretty(
        {
            "note": "Persisted dummy events. Filter with asset_id for one machine.",
            "kind": wanted_kind or "all",
            "asset_id": wanted_asset or "all",
            "count": len(rows),
            "events": rows,
        }
    )


@mcp.tool
def set_asset_power(asset_id: str, on: bool) -> str:
    """Turn one dummy equipment instance on or off.

    Failed instances cannot be turned on; a worker must Accept FIX or call replace_asset.
    Confirm with list_assets afterwards.
    """
    wanted = (asset_id or "").strip()
    if not wanted:
        return _pretty({"error": "asset_id is required", "known_assets": asset_ids()})
    return _pretty(plant.set_asset_power(wanted, bool(on), source="mcp"))


@mcp.tool
def fail_asset(asset_id: str) -> str:
    """Mark one dummy instance as failed. It trips off until FIX or replace."""
    wanted = (asset_id or "").strip()
    if not wanted:
        return _pretty({"error": "asset_id is required", "known_assets": asset_ids()})
    return _pretty(plant.fail_asset(wanted))


@mcp.tool
def replace_asset(asset_id: str) -> str:
    """Swap a failed dummy instance for a new serial and start it.

    Only works when health is failed. Returns the new serial/generation.
    """
    wanted = (asset_id or "").strip()
    if not wanted:
        return _pretty({"error": "asset_id is required", "known_assets": asset_ids()})
    return _pretty(plant.replace_asset(wanted))


@mcp.tool
def request_fix(asset_id: str, note: str = "") -> str:
    """Ask a human worker to FIX one dummy asset. Does not apply the repair.

    The request appears on the factory map. The worker clicks Accept.
    Use this instead of pretending to maintain the machine. FIX may be
    preventive (before 3 anomalies) or after a trip. Same serial; counts reset.
    Re-read list_fix_requests or get_asset after the worker accepts.
    """
    wanted = (asset_id or "").strip()
    if not wanted:
        return _pretty({"error": "asset_id is required", "known_assets": asset_ids()})
    return _pretty(plant.request_fix(wanted, note=note or "", source="mcp"))


@mcp.tool
def list_fix_requests(status: str = "pending") -> str:
    """List worker FIX requests. Default status is pending.

    After request_fix, poll this (or tell the user to Accept on the map)
    until status is accepted. Do not claim the machine was fixed until then.
    """
    wanted = (status or "").strip() or "pending"
    if wanted == "all":
        wanted = None
    rows = plant.snapshot_fix_requests(wanted)
    return _pretty(
        {
            "note": "Dummy work queue. Accept happens on the factory screen, not in this tool.",
            "status": wanted or "all",
            "count": len(rows),
            "requests": rows,
        }
    )


@mcp.custom_route("/", methods=["GET"])
async def factory_root(_request: Request) -> FileResponse:
    return FileResponse(STATIC_DIR / "factory.html")


@mcp.custom_route("/factory", methods=["GET"])
async def factory_page(_request: Request) -> FileResponse:
    return FileResponse(STATIC_DIR / "factory.html")


@mcp.custom_route("/factory/events", methods=["GET"])
async def factory_events(request: Request) -> StreamingResponse:
    async def gen():
        while True:
            if await request.is_disconnected():
                break
            payload = json.dumps(plant.factory_snapshot(), ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse(plant.health())


@mcp.custom_route("/demo/sensors", methods=["GET"])
async def demo_sensors(_request: Request) -> JSONResponse:
    return JSONResponse({"sensors": plant.snapshot_sensors()})


@mcp.custom_route("/demo/assets", methods=["GET"])
async def demo_assets(_request: Request) -> JSONResponse:
    return JSONResponse({"assets": plant.snapshot_assets()})


@mcp.custom_route("/demo/events", methods=["GET"])
async def demo_events(request: Request) -> JSONResponse:
    asset_id = (request.query_params.get("asset_id") or "").strip() or None
    kind = (request.query_params.get("kind") or "").strip() or None
    return JSONResponse({"events": plant.recent_events(20, kind=kind, asset_id=asset_id)})


@mcp.custom_route("/demo/anomalies", methods=["GET"])
async def demo_anomalies(_request: Request) -> JSONResponse:
    return JSONResponse({"anomalies": plant.recent_anomalies(10)})


@mcp.custom_route("/demo/factory", methods=["GET"])
async def demo_factory(_request: Request) -> JSONResponse:
    return JSONResponse(plant.factory_snapshot())


@mcp.custom_route("/demo/power", methods=["POST"])
async def demo_power(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": "JSON body required"}, status_code=400)
    asset_id = str(body.get("asset_id") or "").strip()
    on = bool(body.get("on"))
    if not asset_id:
        return JSONResponse({"ok": False, "error": "asset_id is required"}, status_code=400)
    result = plant.set_asset_power(asset_id, on, source="ui")
    status = 200 if result.get("ok") else 400
    return JSONResponse(result, status_code=status)


@mcp.custom_route("/demo/fix", methods=["POST"])
async def demo_fix(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": "JSON body required"}, status_code=400)
    action = str(body.get("action") or "apply").strip().lower()
    if action == "accept":
        result = plant.accept_fix(body.get("request_id"), source="ui")
    elif action == "dismiss":
        result = plant.dismiss_fix(body.get("request_id"), source="ui")
    else:
        asset_id = str(body.get("asset_id") or "").strip()
        if not asset_id:
            return JSONResponse({"ok": False, "error": "asset_id is required"}, status_code=400)
        result = plant.apply_fix(asset_id, source="ui")
    status = 200 if result.get("ok") else 400
    return JSONResponse(result, status_code=status)


@mcp.custom_route("/demo/reset", methods=["POST"])
async def demo_reset(_request: Request) -> JSONResponse:
    return JSONResponse(plant.reset_plant())


def main() -> None:
    plant.start_feed()
    print(f"factory map     http://{HOST}:{PORT}/", flush=True)
    print(f"mcp streamable-http on http://{HOST}:{PORT}{PATH}", flush=True)
    mcp.run(transport="http", host=HOST, port=PORT, path=PATH)


if __name__ == "__main__":
    main()
