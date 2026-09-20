"""In-memory vibration store fed by MQTT.

The MCP process keeps a short ring buffer so list/get/anomaly tools stay
fast and do not need a database. This is classroom state, not a historian.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "plant/sensors/+/vibration")
MAX_READINGS = int(os.getenv("MAX_READINGS", "200"))
WARNING_RMS_MM_S = float(os.getenv("WARNING_RMS_MM_S", "4.5"))
ANOMALY_RMS_MM_S = float(os.getenv("ANOMALY_RMS_MM_S", "7.0"))

# Catalog shown even before the first MQTT message arrives.
KNOWN_SENSORS: dict[str, dict[str, str]] = {
    "pump-a-de": {
        "name": "Pump A drive-end bearing",
        "asset": "Cooling water pump A",
    },
    "pump-a-nde": {
        "name": "Pump A non-drive-end bearing",
        "asset": "Cooling water pump A",
    },
    "fan-b-motor": {
        "name": "Fan B motor housing",
        "asset": "HVAC fan B",
    },
}

_lock = threading.Lock()
_latest: dict[str, dict[str, Any]] = {}
_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_READINGS))
_anomalies: deque = deque(maxlen=MAX_READINGS)
_mqtt_connected = False
_started_at = datetime.now(timezone.utc).isoformat()


def classify_rms(rms_mm_s: float) -> str:
    """Same thresholds as the dummy sensor; re-applied in case a payload omits status."""
    if rms_mm_s >= ANOMALY_RMS_MM_S:
        return "anomaly"
    if rms_mm_s >= WARNING_RMS_MM_S:
        return "warning"
    return "normal"


def ingest(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Validate one reading, store it, and copy anomalies aside. Returns the stored row."""
    sensor_id = payload.get("sensor_id")
    if not isinstance(sensor_id, str) or not sensor_id.strip():
        return None
    try:
        rms = float(payload.get("rms_mm_s", 0.0))
    except (TypeError, ValueError):
        return None

    row = dict(payload)
    row["sensor_id"] = sensor_id
    row["rms_mm_s"] = rms
    row["status"] = row.get("status") or classify_rms(rms)
    if row["status"] not in {"normal", "warning", "anomaly"}:
        row["status"] = classify_rms(rms)
    row["received_at"] = datetime.now(timezone.utc).isoformat()

    with _lock:
        _latest[sensor_id] = row
        _history[sensor_id].append(row)
        if row["status"] == "anomaly":
            _anomalies.append(row)
    return row


def snapshot_sensors() -> list[dict[str, Any]]:
    """Catalog plus last reading, used by list_sensors and GET /demo/sensors."""
    with _lock:
        latest_copy = {k: dict(v) for k, v in _latest.items()}
    rows = []
    ids = list(dict.fromkeys([*KNOWN_SENSORS.keys(), *latest_copy.keys()]))
    for sensor_id in ids:
        meta = KNOWN_SENSORS.get(sensor_id, {"name": sensor_id, "asset": "unknown"})
        last = latest_copy.get(sensor_id)
        rows.append(
            {
                "sensor_id": sensor_id,
                "name": meta.get("name", sensor_id),
                "asset": meta.get("asset", "unknown"),
                "last_status": None if last is None else last.get("status"),
                "last_rms_mm_s": None if last is None else last.get("rms_mm_s"),
                "last_ts": None if last is None else last.get("ts"),
                "has_reading": last is not None,
            }
        )
    return rows


def latest_reading(sensor_id: str) -> dict[str, Any] | None:
    with _lock:
        row = _latest.get(sensor_id)
        return None if row is None else dict(row)


def recent_anomalies(limit: int = 10) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 50))
    with _lock:
        items = list(_anomalies)[-cap:]
    items.reverse()
    return [dict(item) for item in items]


def health() -> dict[str, Any]:
    with _lock:
        n_latest = len(_latest)
        n_anom = len(_anomalies)
        connected = _mqtt_connected
    return {
        "ok": True,
        "service": "vibration-pdm",
        "mqtt_connected": connected,
        "mqtt_host": MQTT_HOST,
        "mqtt_port": MQTT_PORT,
        "sensors_with_readings": n_latest,
        "anomaly_count": n_anom,
        "known_sensors": list(KNOWN_SENSORS.keys()),
        "started_at": _started_at,
        "dummy": True,
    }


def _on_connect(client, userdata, flags, reason_code, properties=None) -> None:  # noqa: ARG001
    global _mqtt_connected
    _mqtt_connected = True
    client.subscribe(MQTT_TOPIC)
    print(f"mqtt subscribed to {MQTT_TOPIC}", flush=True)


def _on_disconnect(client, userdata, flags, reason_code, properties=None) -> None:  # noqa: ARG001
    global _mqtt_connected
    _mqtt_connected = False
    print(f"mqtt disconnected ({reason_code})", flush=True)


def _on_message(client, userdata, msg) -> None:  # noqa: ARG001
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"skip bad mqtt payload: {exc}", flush=True)
        return
    if not isinstance(payload, dict):
        return
    ingest(payload)


def start_mqtt_background() -> None:
    """Retry forever so the MCP container can boot before Mosquitto is ready."""

    def _loop() -> None:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="mcp-vibration-store",
        )
        client.on_connect = _on_connect
        client.on_disconnect = _on_disconnect
        client.on_message = _on_message
        while True:
            try:
                client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
                client.loop_forever()
            except Exception as exc:  # noqa: BLE001
                global _mqtt_connected
                _mqtt_connected = False
                print(f"mqtt not ready ({exc}); retry in 2s", flush=True)
                time.sleep(2)

    thread = threading.Thread(target=_loop, name="mqtt-bridge", daemon=True)
    thread.start()
