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
        "Dummy plant. Call a tool for live numbers; never invent them. "
        "One tool per turn. request_fix asks a worker; Accept is on "
        "http://localhost:8000. Writes affect this sandbox only."
    ),
)


def _num(value: object) -> object:
    if isinstance(value, float):
        return round(value, 2)
    return value


def _dump(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _sensor_brief(row: dict) -> dict:
    return {
        "sensor_id": row["sensor_id"],
        "asset_id": row["asset_id"],
        "rms_mm_s": _num(row.get("last_rms_mm_s")),
        "status": row.get("last_status"),
        "anoms": int(row.get("anomaly_count") or 0),
        "power": row.get("asset_power"),
        "health": row.get("asset_health"),
    }


def _asset_brief(row: dict, *, detail: bool = False) -> dict:
    pending = row.get("pending_fix")
    out = {
        "asset_id": row["asset_id"],
        "serial": row.get("serial"),
        "power": row.get("power"),
        "health": row.get("health"),
        "anoms": int(row.get("anomaly_total") or 0),
        "last_reason": row.get("last_reason"),
        "sensors": row.get("sensor_ids"),
    }
    if pending:
        out["pending_fix"] = {
            "request_id": pending.get("request_id"),
            "note": pending.get("note") or "",
        }
    if detail:
        out["anoms_by_sensor"] = row.get("anomaly_counts") or {}
        if row.get("last_fix_at"):
            out["last_fix_at"] = row["last_fix_at"]
    return out


def _event_brief(row: dict) -> dict:
    return {
        "kind": row.get("kind"),
        "asset_id": row.get("asset_id"),
        "sensor_id": row.get("sensor_id"),
        "ts": row.get("ts"),
        "detail": row.get("detail"),
    }


def _reading_brief(row: dict) -> dict:
    return {
        "sensor_id": row.get("sensor_id"),
        "asset_id": row.get("asset_id"),
        "rms_mm_s": _num(row.get("rms_mm_s")),
        "peak_g": _num(row.get("peak_g")),
        "temp_c": _num(row.get("temperature_c")),
        "status": row.get("status"),
        "ts": row.get("ts"),
    }


def _fix_brief(row: dict) -> dict:
    return {
        "request_id": row.get("request_id"),
        "asset_id": row.get("asset_id"),
        "status": row.get("status"),
        "note": row.get("note") or "",
    }


def _result_brief(result: dict) -> str:
    out = {key: value for key, value in result.items() if key != "note"}
    if isinstance(out.get("asset"), dict):
        out["asset"] = _asset_brief(out["asset"], detail=True)
    if isinstance(out.get("request"), dict):
        out["request"] = _fix_brief(out["request"])
    return _dump(out)


@mcp.tool
def list_assets() -> str:
    """List machines: power, health, serial, reason, anomaly counts."""
    return _dump({"assets": [_asset_brief(row) for row in plant.snapshot_assets()]})


@mcp.tool
def list_sensors() -> str:
    """List sensors with live RMS, status, and parent asset power/health."""
    return _dump({"sensors": [_sensor_brief(row) for row in plant.snapshot_sensors()]})


@mcp.tool
def get_asset(asset_id: str) -> str:
    """One machine: power, health, last_reason, anoms_by_sensor, pending_fix."""
    wanted = (asset_id or "").strip()
    if not wanted:
        return _dump({"error": "asset_id is required", "known_assets": asset_ids()})
    row = plant.get_asset_state(wanted)
    if row is None:
        return _dump({"error": "unknown asset_id", "asset_id": wanted, "known_assets": asset_ids()})
    return _dump(_asset_brief(row, detail=True))


@mcp.tool
def get_vibration_reading(sensor_id: str) -> str:
    """Latest RMS for one sensor. Known ids come from list_sensors."""
    wanted = (sensor_id or "").strip()
    if not wanted:
        return _dump({"error": "sensor_id is required"})
    row = plant.latest_reading(wanted)
    if row is None:
        return _dump({"error": "no reading yet", "sensor_id": wanted, "known_sensors": sensor_ids()})
    return _dump(_reading_brief(row))


@mcp.tool
def get_recent_events(limit: int = 5, kind: str = "", asset_id: str = "") -> str:
    """Recent events. Optional kind=anomaly|power|fail|replace|fix, asset_id=one machine."""
    wanted_kind = (kind or "").strip() or None
    wanted_asset = (asset_id or "").strip() or None
    cap = max(1, min(int(limit or 5), 8))
    rows = plant.recent_events(cap, kind=wanted_kind, asset_id=wanted_asset)
    return _dump({"events": [_event_brief(row) for row in rows]})


@mcp.tool
def set_asset_power(asset_id: str, on: bool) -> str:
    """Turn one dummy machine on or off. Failed units stay off until FIX or replace."""
    wanted = (asset_id or "").strip()
    if not wanted:
        return _dump({"error": "asset_id is required", "known_assets": asset_ids()})
    return _result_brief(plant.set_asset_power(wanted, bool(on), source="mcp"))


@mcp.tool
def fail_asset(asset_id: str) -> str:
    """Mark one dummy machine failed. It stays off until FIX or replace."""
    wanted = (asset_id or "").strip()
    if not wanted:
        return _dump({"error": "asset_id is required", "known_assets": asset_ids()})
    return _result_brief(plant.fail_asset(wanted))


@mcp.tool
def replace_asset(asset_id: str) -> str:
    """Replace a failed dummy machine with a new serial. Health must be failed."""
    wanted = (asset_id or "").strip()
    if not wanted:
        return _dump({"error": "asset_id is required", "known_assets": asset_ids()})
    return _result_brief(plant.replace_asset(wanted))


@mcp.tool
def request_fix(asset_id: str, note: str = "") -> str:
    """Ask a worker to FIX. Does not repair. Worker Accepts on the factory map."""
    wanted = (asset_id or "").strip()
    if not wanted:
        return _dump({"error": "asset_id is required", "known_assets": asset_ids()})
    return _result_brief(plant.request_fix(wanted, note=note or "", source="mcp"))


@mcp.tool
def list_fix_requests(status: str = "pending") -> str:
    """Worker FIX queue. Default pending. Do not claim fixed until accepted."""
    wanted = (status or "").strip() or "pending"
    if wanted == "all":
        wanted = None
    rows = plant.snapshot_fix_requests(wanted)
    return _dump({"requests": [_fix_brief(row) for row in rows]})


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
