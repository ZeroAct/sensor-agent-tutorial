"""Publish dummy vibration readings to MQTT for the classroom plant.

This is not a physics model. Each sensor has a quiet baseline plus noise.
Every ANOMALY_EVERY_SEC seconds, pump-a-de emits a single high RMS spike
so the lab always has something for get_recent_anomalies to show.
"""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
PUBLISH_INTERVAL_SEC = float(os.getenv("PUBLISH_INTERVAL_SEC", "2"))
ANOMALY_EVERY_SEC = float(os.getenv("ANOMALY_EVERY_SEC", "45"))
WARNING_RMS_MM_S = float(os.getenv("WARNING_RMS_MM_S", "4.5"))
ANOMALY_RMS_MM_S = float(os.getenv("ANOMALY_RMS_MM_S", "7.0"))
TOPIC_TEMPLATE = "plant/sensors/{sensor_id}/vibration"

# Classroom assets. IDs are stable so Skills and slides can name them.
SENSORS = (
    {
        "id": "pump-a-de",
        "asset": "Cooling water pump A",
        "location": "drive-end bearing",
        "base_rms": 2.2,
        "base_peak": 0.62,
        "base_temp": 41.0,
    },
    {
        "id": "pump-a-nde",
        "asset": "Cooling water pump A",
        "location": "non-drive-end bearing",
        "base_rms": 1.8,
        "base_peak": 0.48,
        "base_temp": 38.0,
    },
    {
        "id": "fan-b-motor",
        "asset": "HVAC fan B",
        "location": "motor housing",
        "base_rms": 1.4,
        "base_peak": 0.40,
        "base_temp": 36.0,
    },
)


def classify_rms(rms_mm_s: float) -> str:
    """Map RMS to a coarse operational status. Lab thresholds, not ISO grades."""
    if rms_mm_s >= ANOMALY_RMS_MM_S:
        return "anomaly"
    if rms_mm_s >= WARNING_RMS_MM_S:
        return "warning"
    return "normal"


def build_reading(sensor: dict, *, spike: bool = False) -> dict:
    """Return one JSON-serialisable reading for MQTT."""
    if spike:
        rms = round(random.uniform(ANOMALY_RMS_MM_S + 0.4, ANOMALY_RMS_MM_S + 3.5), 2)
        peak = round(random.uniform(3.2, 5.0), 2)
        temp = round(sensor["base_temp"] + random.uniform(6.0, 12.0), 1)
    else:
        rms = round(sensor["base_rms"] + random.uniform(-0.25, 0.35), 2)
        peak = round(sensor["base_peak"] + random.uniform(-0.08, 0.10), 2)
        temp = round(sensor["base_temp"] + random.uniform(-1.5, 2.0), 1)

    rms = max(rms, 0.1)
    peak = max(peak, 0.05)
    return {
        "sensor_id": sensor["id"],
        "asset": sensor["asset"],
        "location": sensor["location"],
        "rms_mm_s": rms,
        "peak_g": peak,
        "temperature_c": temp,
        "status": classify_rms(rms),
        "ts": datetime.now(timezone.utc).isoformat(),
        "dummy": True,
    }


def connect_mqtt() -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="dummy-vibration-sensor",
    )
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            print(f"connected to mqtt://{MQTT_HOST}:{MQTT_PORT}", flush=True)
            return client
        except Exception as exc:  # noqa: BLE001 — keep retrying in class
            print(f"mqtt not ready ({exc}); retry in 2s", flush=True)
            time.sleep(2)


def main() -> None:
    client = connect_mqtt()
    client.loop_start()
    started = time.monotonic()
    last_spike_at = started
    print(
        f"publishing {len(SENSORS)} sensors every {PUBLISH_INTERVAL_SEC}s; "
        f"spike pump-a-de every {ANOMALY_EVERY_SEC}s",
        flush=True,
    )
    while True:
        now = time.monotonic()
        spike_pump = (now - last_spike_at) >= ANOMALY_EVERY_SEC
        if spike_pump:
            last_spike_at = now
        for sensor in SENSORS:
            spike = spike_pump and sensor["id"] == "pump-a-de"
            reading = build_reading(sensor, spike=spike)
            topic = TOPIC_TEMPLATE.format(sensor_id=sensor["id"])
            payload = json.dumps(reading)
            client.publish(topic, payload, qos=0, retain=False)
            if spike:
                print(f"SPIKE {payload}", flush=True)
        time.sleep(PUBLISH_INTERVAL_SEC)


if __name__ == "__main__":
    main()
