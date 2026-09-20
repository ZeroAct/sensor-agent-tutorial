"""Unit tests for dummy readings and the in-memory MCP store (no broker required)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SENSOR_FILE = ROOT / "dummy-sensor" / "sensor.py"
STORE_FILE = ROOT / "mcp-server" / "vibration_store.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sensor = _load(SENSOR_FILE, "dummy_sensor")
store = _load(STORE_FILE, "vibration_store")


def test_classify_thresholds_match_between_publisher_and_store():
    assert sensor.classify_rms(2.0) == "normal"
    assert sensor.classify_rms(4.5) == "warning"
    assert sensor.classify_rms(7.0) == "anomaly"
    assert store.classify_rms(2.0) == "normal"
    assert store.classify_rms(4.5) == "warning"
    assert store.classify_rms(7.0) == "anomaly"


def test_quiet_reading_stays_normal():
    pump = next(item for item in sensor.SENSORS if item["id"] == "pump-a-de")
    for _ in range(20):
        row = sensor.build_reading(pump, spike=False)
        assert row["status"] == "normal"
        assert row["dummy"] is True
        assert row["rms_mm_s"] < 4.5


def test_spike_is_anomaly_on_pump_a_de():
    pump = next(item for item in sensor.SENSORS if item["id"] == "pump-a-de")
    row = sensor.build_reading(pump, spike=True)
    assert row["sensor_id"] == "pump-a-de"
    assert row["status"] == "anomaly"
    assert row["rms_mm_s"] >= 7.0


def test_store_ingest_and_latest():
    store._latest.clear()
    store._anomalies.clear()
    store._history.clear()

    quiet = store.ingest(
        {
            "sensor_id": "fan-b-motor",
            "rms_mm_s": 1.5,
            "ts": "2026-01-01T00:00:00+00:00",
        }
    )
    assert quiet is not None
    assert quiet["status"] == "normal"
    assert store.latest_reading("fan-b-motor")["rms_mm_s"] == 1.5

    spike = store.ingest(
        {
            "sensor_id": "pump-a-de",
            "rms_mm_s": 9.1,
            "status": "anomaly",
            "ts": "2026-01-01T00:01:00+00:00",
        }
    )
    assert spike is not None
    anomalies = store.recent_anomalies(5)
    assert anomalies[0]["sensor_id"] == "pump-a-de"
    ids = {row["sensor_id"] for row in store.snapshot_sensors()}
    assert {"pump-a-de", "pump-a-nde", "fan-b-motor"} <= ids


def test_ingest_rejects_empty_sensor_id():
    assert store.ingest({"sensor_id": "  ", "rms_mm_s": 1.0}) is None
    assert store.ingest({"rms_mm_s": 1.0}) is None


def test_health_payload_shape():
    payload = store.health()
    assert payload["ok"] is True
    assert payload["dummy"] is True
    assert "pump-a-de" in payload["known_sensors"]
