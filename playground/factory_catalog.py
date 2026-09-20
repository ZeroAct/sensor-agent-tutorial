"""Dummy-plant catalog: equipment instances + 10 vibration sensors.

Positions are percentages of the factory floor (0–100).
"""

from __future__ import annotations

from typing import Any

PLANT = {
    "id": "dummy-cooling-plant",
    "name": "Dummy Cooling Plant",
    "name_ko": "학습용 냉각 플랜트",
    "view": "top-down",
}

SPIKE_SENSOR_ID = "pump-a-de"
SPIKE_ASSET_ID = "pump-a"

ZONES = (
    {"id": "pump-room", "name": "Pump Room", "name_ko": "펌프실", "x": 4, "y": 16, "w": 28, "h": 44},
    {"id": "compressor", "name": "Compressor Hall", "name_ko": "압축기실", "x": 4, "y": 64, "w": 28, "h": 30},
    {"id": "production", "name": "Production Line", "name_ko": "생산 라인", "x": 36, "y": 16, "w": 38, "h": 78},
    {"id": "hvac", "name": "HVAC", "name_ko": "공조", "x": 78, "y": 16, "w": 18, "h": 30},
    {"id": "cooling", "name": "Cooling Tower", "name_ko": "냉각탑", "x": 78, "y": 50, "w": 18, "h": 44},
)

ASSETS = (
    {
        "id": "pump-a",
        "name": "Cooling water pump A",
        "name_ko": "냉각수 펌프 A",
        "kind": "pump",
        "zone": "pump-room",
        "serial_prefix": "PA",
        "label": "Pump A",
        "x": 8.0,
        "y": 30.0,
        "w": 18.0,
        "h": 14.0,
    },
    {
        "id": "compressor-c",
        "name": "Air compressor C",
        "name_ko": "공기압축기 C",
        "kind": "compressor",
        "zone": "compressor",
        "serial_prefix": "CC",
        "label": "Comp C",
        "x": 8.0,
        "y": 72.0,
        "w": 10.0,
        "h": 16.0,
    },
    {
        "id": "blower-f",
        "name": "Process blower F",
        "name_ko": "공정 블로워 F",
        "kind": "blower",
        "zone": "compressor",
        "serial_prefix": "BF",
        "label": "Blower F",
        "x": 20.0,
        "y": 74.0,
        "w": 8.0,
        "h": 12.0,
    },
    {
        "id": "conveyor-1",
        "name": "Production conveyor 1",
        "name_ko": "생산 컨베이어 1",
        "kind": "conveyor",
        "zone": "production",
        "serial_prefix": "CV",
        "label": "Conv 1",
        "x": 40.0,
        "y": 26.0,
        "w": 30.0,
        "h": 8.0,
    },
    {
        "id": "conveyor-2",
        "name": "Production conveyor 2",
        "name_ko": "생산 컨베이어 2",
        "kind": "conveyor",
        "zone": "production",
        "serial_prefix": "CW",
        "label": "Conv 2",
        "x": 40.0,
        "y": 38.0,
        "w": 30.0,
        "h": 8.0,
    },
    {
        "id": "mixer-d",
        "name": "Batch mixer D",
        "name_ko": "배치 믹서 D",
        "kind": "mixer",
        "zone": "production",
        "serial_prefix": "MD",
        "label": "Mixer D",
        "x": 44.0,
        "y": 52.0,
        "w": 10.0,
        "h": 12.0,
    },
    {
        "id": "press-e",
        "name": "Stamping press E",
        "name_ko": "스탬핑 프레스 E",
        "kind": "press",
        "zone": "production",
        "serial_prefix": "PE",
        "label": "Press E",
        "x": 58.0,
        "y": 54.0,
        "w": 10.0,
        "h": 14.0,
    },
    {
        "id": "fan-b",
        "name": "HVAC fan B",
        "name_ko": "공조 팬 B",
        "kind": "fan",
        "zone": "hvac",
        "serial_prefix": "FB",
        "label": "Fan B",
        "x": 82.0,
        "y": 24.0,
        "w": 10.0,
        "h": 12.0,
    },
    {
        "id": "cooling-tower",
        "name": "Cooling tower",
        "name_ko": "냉각탑",
        "kind": "tower",
        "zone": "cooling",
        "serial_prefix": "CT",
        "label": "Tower",
        "x": 82.0,
        "y": 60.0,
        "w": 10.0,
        "h": 24.0,
    },
)

SENSORS = (
    {
        "id": "pump-a-de",
        "name": "Pump A drive-end bearing",
        "name_ko": "펌프 A 구동측 베어링",
        "asset_id": "pump-a",
        "location": "drive-end bearing",
        "zone": "pump-room",
        "x": 21.5,
        "y": 37.0,
        "base_rms": 2.2,
        "base_peak": 0.62,
        "base_temp": 41.0,
        "spike": True,
    },
    {
        "id": "pump-a-nde",
        "name": "Pump A non-drive-end bearing",
        "name_ko": "펌프 A 비구동측 베어링",
        "asset_id": "pump-a",
        "location": "non-drive-end bearing",
        "zone": "pump-room",
        "x": 12.2,
        "y": 37.0,
        "base_rms": 1.8,
        "base_peak": 0.48,
        "base_temp": 38.0,
        "spike": False,
    },
    {
        "id": "compressor-c",
        "name": "Compressor C crankcase",
        "name_ko": "압축기 C 크랭크케이스",
        "asset_id": "compressor-c",
        "location": "crankcase",
        "zone": "compressor",
        "x": 12.0,
        "y": 78.0,
        "base_rms": 2.4,
        "base_peak": 0.70,
        "base_temp": 52.0,
        "spike": False,
    },
    {
        "id": "blower-f",
        "name": "Blower F housing",
        "name_ko": "블로워 F 하우징",
        "asset_id": "blower-f",
        "location": "housing",
        "zone": "compressor",
        "x": 24.0,
        "y": 80.0,
        "base_rms": 1.9,
        "base_peak": 0.52,
        "base_temp": 44.0,
        "spike": False,
    },
    {
        "id": "conveyor-1-drive",
        "name": "Conveyor 1 drive",
        "name_ko": "컨베이어 1 구동부",
        "asset_id": "conveyor-1",
        "location": "drive pulley",
        "zone": "production",
        "x": 44.0,
        "y": 30.0,
        "base_rms": 1.5,
        "base_peak": 0.42,
        "base_temp": 34.0,
        "spike": False,
    },
    {
        "id": "conveyor-2-drive",
        "name": "Conveyor 2 drive",
        "name_ko": "컨베이어 2 구동부",
        "asset_id": "conveyor-2",
        "location": "drive pulley",
        "zone": "production",
        "x": 62.0,
        "y": 42.0,
        "base_rms": 1.6,
        "base_peak": 0.44,
        "base_temp": 35.0,
        "spike": False,
    },
    {
        "id": "mixer-d-motor",
        "name": "Mixer D motor",
        "name_ko": "믹서 D 모터",
        "asset_id": "mixer-d",
        "location": "motor housing",
        "zone": "production",
        "x": 48.0,
        "y": 58.0,
        "base_rms": 2.0,
        "base_peak": 0.55,
        "base_temp": 47.0,
        "spike": False,
    },
    {
        "id": "press-e-crank",
        "name": "Press E crank",
        "name_ko": "프레스 E 크랭크",
        "asset_id": "press-e",
        "location": "crank bearing",
        "zone": "production",
        "x": 64.0,
        "y": 62.0,
        "base_rms": 2.1,
        "base_peak": 0.58,
        "base_temp": 49.0,
        "spike": False,
    },
    {
        "id": "fan-b-motor",
        "name": "Fan B motor housing",
        "name_ko": "팬 B 모터 하우징",
        "asset_id": "fan-b",
        "location": "motor housing",
        "zone": "hvac",
        "x": 86.0,
        "y": 30.0,
        "base_rms": 1.4,
        "base_peak": 0.40,
        "base_temp": 36.0,
        "spike": False,
    },
    {
        "id": "cooling-tower-fan",
        "name": "Cooling tower fan",
        "name_ko": "냉각탑 팬",
        "asset_id": "cooling-tower",
        "location": "fan deck",
        "zone": "cooling",
        "x": 86.0,
        "y": 72.0,
        "base_rms": 1.7,
        "base_peak": 0.46,
        "base_temp": 32.0,
        "spike": False,
    },
)


def asset_ids() -> list[str]:
    return [item["id"] for item in ASSETS]


def sensor_ids() -> list[str]:
    return [item["id"] for item in SENSORS]


def get_asset(asset_id: str) -> dict[str, Any] | None:
    for item in ASSETS:
        if item["id"] == asset_id:
            return dict(item)
    return None


def get_sensor(sensor_id: str) -> dict[str, Any] | None:
    for item in SENSORS:
        if item["id"] == sensor_id:
            return dict(item)
    return None


def sensors_for_asset(asset_id: str) -> list[dict[str, Any]]:
    return [dict(item) for item in SENSORS if item["asset_id"] == asset_id]


def make_serial(prefix: str, generation: int) -> str:
    return f"{prefix}-{1000 + generation}"
