"""Unit tests for the dummy plant catalog and SQLite store (no Docker)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp-server"))

import factory_catalog as catalog
import plant


def test_catalog_assets_and_sensors_line_up():
    assert len(catalog.ASSETS) == 9
    assert len(catalog.SENSORS) == 10
    asset_ids = set(catalog.asset_ids())
    assert len(asset_ids) == 9
    for sensor in catalog.SENSORS:
        assert sensor["asset_id"] in asset_ids
        assert 0 <= sensor["x"] <= 100
        assert 0 <= sensor["y"] <= 100
    spiked = [item["id"] for item in catalog.SENSORS if item["spike"]]
    assert spiked == ["pump-a-de"]
    assert catalog.SPIKE_ASSET_ID == "pump-a"


def test_classify_thresholds():
    assert plant.classify_rms(2.0) == "normal"
    assert plant.classify_rms(4.5) == "warning"
    assert plant.classify_rms(7.0) == "anomaly"


def test_tick_and_latest(tmp_path):
    plant.configure(tmp_path / "plant.db")
    plant.tick()
    row = plant.latest_reading("pump-a-de")
    assert row is not None
    assert row["status"] == "normal"
    assert row["rms_mm_s"] < 4.5
    ids = {item["sensor_id"] for item in plant.snapshot_sensors()}
    assert len(ids) == 10
    health = plant.health()
    assert health["ok"] is True
    assert health["asset_count"] == 9
    assert health["dummy"] is True


def test_power_off_makes_sensors_offline(tmp_path):
    plant.configure(tmp_path / "plant.db")
    result = plant.set_asset_power("fan-b", False)
    assert result["ok"] is True
    plant.tick()
    row = plant.latest_reading("fan-b-motor")
    assert row["status"] == "offline"
    assert row["rms_mm_s"] == 0.0
    events = plant.recent_events(kind="power")
    assert events[0]["asset_id"] == "fan-b"
    fan_only = plant.recent_events(asset_id="fan-b")
    assert fan_only and all(row["asset_id"] == "fan-b" for row in fan_only)
    snap = plant.factory_snapshot()
    assets = {row["asset_id"]: row for row in snap["assets"]}
    assert any(ev["kind"] == "power" for ev in assets["fan-b"]["events"])


def test_fail_blocks_power_on_until_replace(tmp_path):
    plant.configure(tmp_path / "plant.db")
    failed = plant.fail_asset("pump-a")
    assert failed["ok"] is True
    blocked = plant.set_asset_power("pump-a", True)
    assert blocked["ok"] is False
    plant.tick()
    assert plant.latest_reading("pump-a-de")["status"] == "failed"
    swapped = plant.replace_asset("pump-a")
    assert swapped["ok"] is True
    assert swapped["replaced"]["new_serial"] != swapped["replaced"]["old_serial"]
    plant.tick()
    assert plant.latest_reading("pump-a-de")["status"] == "normal"
    assets = {row["asset_id"]: row for row in plant.snapshot_assets()}
    assert assets["pump-a"]["health"] == "ok"
    assert assets["pump-a"]["generation"] == 2


def test_replace_rejects_healthy_asset(tmp_path):
    plant.configure(tmp_path / "plant.db")
    result = plant.replace_asset("mixer-d")
    assert result["ok"] is False


def test_unknown_asset(tmp_path):
    plant.configure(tmp_path / "plant.db")
    assert plant.fail_asset("no-such")["ok"] is False
    assert plant.set_asset_power("no-such", True)["ok"] is False


def test_pump_a_sensors_sit_on_the_pump():
    pump = catalog.get_asset("pump-a")
    assert pump is not None
    for sid in ("pump-a-de", "pump-a-nde"):
        sensor = catalog.get_sensor(sid)
        assert sensor is not None
        assert pump["x"] <= sensor["x"] <= pump["x"] + pump["w"]
        assert pump["y"] <= sensor["y"] <= pump["y"] + pump["h"]
    de = catalog.get_sensor("pump-a-de")
    nde = catalog.get_sensor("pump-a-nde")
    assert nde["x"] < de["x"]


def test_anomaly_count_stays_after_the_spike_ends(tmp_path):
    plant.configure(tmp_path / "plant.db")
    plant.tick()
    plant.tick(force_spike_sensor="pump-a-de")
    plant.tick()
    snap = plant.factory_snapshot()
    assert snap["anomaly_count"] == 1
    assert snap["live_anomaly_count"] in (0, 1)
    sensors = {row["sensor_id"]: row for row in snap["sensors"]}
    assert sensors["pump-a-de"]["anomaly_count"] == 1
    assets = {row["asset_id"]: row for row in snap["assets"]}
    assert assets["pump-a"]["anomaly_total"] == 1
    assert plant.latest_reading("pump-a-de")["status"] == "normal"


def test_three_anomalies_trip_the_asset(tmp_path):
    plant.configure(tmp_path / "plant.db")
    for _ in range(3):
        plant.tick(force_spike_sensor="pump-a-de")
    plant.tick()
    assets = {row["asset_id"]: row for row in plant.snapshot_assets()}
    pump = assets["pump-a"]
    assert pump["health"] == "failed"
    assert pump["power"] == "off"
    assert pump["anomaly_total"] == 3
    assert pump["last_reason_source"] == "trip"
    assert "pump-a-de" in pump["last_reason"]
    assert "3회" in pump["last_reason"]
    events = plant.recent_events(kind="fail")
    assert events[0]["detail"]["source"] == "trip"
    assert plant.latest_reading("pump-a-de")["status"] == "failed"
    loaded = plant.get_asset_state("pump-a")
    assert loaded["last_reason"] == pump["last_reason"]


def test_ui_power_off_records_reason(tmp_path):
    plant.configure(tmp_path / "plant.db")
    result = plant.set_asset_power("fan-b", False, source="ui")
    assert result["ok"] is True
    asset = plant.get_asset_state("fan-b")
    assert asset["power"] == "off"
    assert asset["last_reason_source"] == "ui"
    assert "화면" in asset["last_reason"]
    events = plant.recent_events(kind="power")
    assert events[0]["detail"]["source"] == "ui"
    assert events[0]["detail"]["reason"] == asset["last_reason"]


def test_request_fix_does_not_apply(tmp_path):
    plant.configure(tmp_path / "plant.db")
    plant.tick(force_spike_sensor="pump-a-de")
    asked = plant.request_fix("pump-a", note="이상 1회, 예방")
    assert asked["ok"] is True
    assert asked["already_pending"] is False
    asset = plant.get_asset_state("pump-a")
    assert asset["anomaly_total"] == 1
    assert asset["pending_fix"]["note"] == "이상 1회, 예방"
    pending = plant.snapshot_fix_requests("pending")
    assert len(pending) == 1
    assert pending[0]["asset_id"] == "pump-a"


def test_fix_before_trip_resets_counts(tmp_path):
    plant.configure(tmp_path / "plant.db")
    plant.tick(force_spike_sensor="pump-a-de")
    plant.tick(force_spike_sensor="pump-a-de")
    assert plant.get_asset_state("pump-a")["anomaly_total"] == 2
    result = plant.apply_fix("pump-a", source="ui")
    assert result["ok"] is True
    asset = plant.get_asset_state("pump-a")
    assert asset["health"] == "ok"
    assert asset["anomaly_total"] == 0
    assert asset["generation"] == 1


def test_accept_fix_restores_failed_same_serial(tmp_path):
    plant.configure(tmp_path / "plant.db")
    for _ in range(3):
        plant.tick(force_spike_sensor="pump-a-de")
    before = plant.get_asset_state("pump-a")
    assert before["health"] == "failed"
    serial = before["serial"]
    asked = plant.request_fix("pump-a", note="트립 후 현장 조치")
    rid = asked["request"]["request_id"]
    accepted = plant.accept_fix(rid, source="ui")
    assert accepted["ok"] is True
    asset = plant.get_asset_state("pump-a")
    assert asset["health"] == "ok"
    assert asset["power"] == "on"
    assert asset["serial"] == serial
    assert asset["anomaly_total"] == 0
    assert asset["pending_fix"] is None
    assert plant.snapshot_fix_requests("pending") == []


def test_reset_plant_wipes_history(tmp_path):
    plant.configure(tmp_path / "plant.db")
    plant.tick(force_spike_sensor="pump-a-de")
    plant.fail_asset("fan-b")
    plant.request_fix("mixer-d", note="예방")
    wiped = plant.reset_plant()
    assert wiped["ok"] is True
    assert wiped["asset_count"] == 9
    assert wiped["sensor_count"] == 10
    assert plant.latest_reading("pump-a-de") is None
    assert plant.recent_events() == []
    assert plant.snapshot_fix_requests("pending") == []
    plant.tick()
    assets = {row["asset_id"]: row for row in plant.snapshot_assets()}
    assert assets["fan-b"]["health"] == "ok"
    assert assets["fan-b"]["generation"] == 1
    assert assets["pump-a"]["anomaly_total"] == 0
    assert plant.factory_snapshot()["sensor_count"] == 10


def test_mcp_list_payloads_are_compact(tmp_path):
    plant.configure(tmp_path / "plant.db")
    plant.tick()
    import server

    sensors = server._dump(
        {"sensors": [server._sensor_brief(row) for row in plant.snapshot_sensors()]}
    )
    assets = server._dump(
        {"assets": [server._asset_brief(row) for row in plant.snapshot_assets()]}
    )
    sensor_row = json.loads(sensors)["sensors"][0]
    assert set(sensor_row) <= {
        "sensor_id",
        "asset_id",
        "rms_mm_s",
        "status",
        "anoms",
        "power",
        "health",
    }
    assert len(sensors) < 1400
    assert len(assets) < 1800
    assert "\n" not in sensors
    reading = json.loads(server._dump(server._reading_brief(plant.latest_reading("pump-a-de"))))
    assert "rms_mm_s" in reading
    assert "id" not in reading


def test_pyproject_exposes_plant_and_claude_scripts():
    import tomllib

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["scripts"]["plant"] == "start_plant:main"
    assert pyproject["project"]["scripts"]["plant-mcp"] == "start_plant_mcp:main"
    assert pyproject["project"]["scripts"]["claude-config"] == "start_claude_config:main"
    assert all("open-webui" not in dep for dep in pyproject["project"]["dependencies"])


MCP_TOOL_NAMES = [
    "list_assets",
    "list_sensors",
    "get_asset",
    "get_vibration_reading",
    "get_recent_events",
    "list_fix_requests",
    "request_fix",
    "set_asset_power",
    "fail_asset",
    "replace_asset",
]


def test_factory_map_lists_mcp_tools():
    html = (ROOT / "mcp-server" / "static" / "factory.html").read_text(encoding="utf-8")
    assert "Open WebUI" not in html
    for name in MCP_TOOL_NAMES:
        assert name in html
    readme = (ROOT.parent / "README.md").read_text(encoding="utf-8")
    assert "claude_desktop_config.json" in readme
    assert "plant-mcp" in readme
    assert "uv run claude-config" in readme


def test_claude_desktop_entry_uses_uv_and_playground(monkeypatch):
    import start_claude_config

    monkeypatch.setattr(start_claude_config.shutil, "which", lambda _name: r"C:\fake\uv.exe")
    entry = start_claude_config.server_entry()
    assert entry["command"].endswith("uv.exe")
    assert entry["args"][:3] == ["run", "--directory", str(ROOT)]
    assert entry["args"][-1] == "plant-mcp"
