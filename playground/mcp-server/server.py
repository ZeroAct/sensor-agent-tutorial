"""Vibration PdM MCP server (Streamable HTTP on :8000).

Tools (the only three the lab chatbot should see):
  - list_sensors
  - get_vibration_reading
  - get_recent_anomalies

Also exposes inspectable HTTP routes so the class can continue when the
free LLM rate-limits:
  GET /health
  GET /demo/sensors
  GET /demo/anomalies
"""

from __future__ import annotations

import json
import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

import vibration_store as store

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8000"))
PATH = os.getenv("MCP_PATH", "/mcp")

mcp = FastMCP(
    "vibration-pdm",
    instructions=(
        "Classroom dummy-plant vibration tools. "
        "Always call a tool for live numbers. Never invent RMS, timestamps, "
        "or sensor IDs. Never tell the user to start or stop equipment; "
        "maintenance decisions stay with a human."
    ),
)


def _pretty(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool
def list_sensors() -> str:
    """List plant vibration sensors, last RMS, and health status.

    Call this first when the user asks which machines or sensors exist.
    """
    return _pretty(
        {
            "note": "Dummy classroom plant. Values come from MQTT, not from the model.",
            "sensors": store.snapshot_sensors(),
        }
    )


@mcp.tool
def get_vibration_reading(sensor_id: str) -> str:
    """Return the latest vibration reading for one sensor.

    Known sensor_id values: pump-a-de, pump-a-nde, fan-b-motor.
    """
    wanted = (sensor_id or "").strip()
    if not wanted:
        return _pretty({"error": "sensor_id is required"})
    row = store.latest_reading(wanted)
    if row is None:
        known = [item["sensor_id"] for item in store.snapshot_sensors()]
        return _pretty(
            {
                "error": "no reading yet for this sensor_id",
                "sensor_id": wanted,
                "known_sensors": known,
            }
        )
    return _pretty({"note": "Latest MQTT reading. Dummy data.", "reading": row})


@mcp.tool
def get_recent_anomalies(limit: int = 10) -> str:
    """Return the most recent vibration anomalies across all sensors.

    Use when the user asks what is wrong, which alarms fired, or whether
    the plant looks healthy. Does not start or stop equipment.
    """
    rows = store.recent_anomalies(limit)
    return _pretty(
        {
            "note": "Anomaly = RMS at or above the lab threshold. Dummy spikes are injected on pump-a-de.",
            "count": len(rows),
            "anomalies": rows,
        }
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse(store.health())


@mcp.custom_route("/demo/sensors", methods=["GET"])
async def demo_sensors(_request: Request) -> JSONResponse:
    return JSONResponse({"sensors": store.snapshot_sensors()})


@mcp.custom_route("/demo/anomalies", methods=["GET"])
async def demo_anomalies(_request: Request) -> JSONResponse:
    return JSONResponse({"anomalies": store.recent_anomalies(10)})


def main() -> None:
    store.start_mqtt_background()
    print(f"mcp streamable-http on http://{HOST}:{PORT}{PATH}", flush=True)
    mcp.run(transport="http", host=HOST, port=PORT, path=PATH)


if __name__ == "__main__":
    main()
