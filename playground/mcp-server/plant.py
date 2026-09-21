"""In-process dummy plant: SQLite history + live generator.

No MQTT. The MCP process owns equipment instances, sensor readings,
and side-effect actions (power / fail / replace).
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
for _path in (_HERE, _HERE.parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from factory_catalog import (
    ASSETS,
    PLANT,
    SENSORS,
    SPIKE_SENSOR_ID,
    ZONES,
    get_asset,
    make_serial,
    sensors_for_asset,
)

PUBLISH_INTERVAL_SEC = float(os.getenv("PUBLISH_INTERVAL_SEC", "2"))
ANOMALY_EVERY_SEC = float(os.getenv("ANOMALY_EVERY_SEC", "10"))
ANOMALY_HOLD_SEC = float(os.getenv("ANOMALY_HOLD_SEC", "6"))
TRIP_ANOMALY_COUNT = int(os.getenv("TRIP_ANOMALY_COUNT", "5"))
WARNING_RMS_MM_S = float(os.getenv("WARNING_RMS_MM_S", "4.5"))
ANOMALY_RMS_MM_S = float(os.getenv("ANOMALY_RMS_MM_S", "7.0"))
MAX_READINGS_PER_SENSOR = int(os.getenv("MAX_READINGS_PER_SENSOR", "80"))
MAX_EVENTS = int(os.getenv("MAX_EVENTS", "300"))
SPIKE_BIAS = float(os.getenv("SPIKE_BIAS", "0.55"))
RANDOM_ISSUE_EVERY_SEC = float(os.getenv("RANDOM_ISSUE_EVERY_SEC", "35"))
RANDOM_ISSUE_CHANCE = float(os.getenv("RANDOM_ISSUE_CHANCE", "0.45"))

POWER_OFF_REASONS = {
    "ui": "화면에서 전원을 끔",
    "mcp": "MCP set_asset_power(off)",
}
FAIL_REASONS = {
    "mcp": "MCP fail_asset로 고장 처리",
    "trip": "진동 이상 누적 트립",
    "random": "랜덤 이슈 트립",
}
RANDOM_ISSUES = (
    {"id": "seal_leak", "reason": "씰 누설 감지 — 랜덤 이슈"},
    {"id": "overheat", "reason": "권선 과열 트립 — 랜덤 이슈"},
    {"id": "overload", "reason": "과부하 차단 — 랜덤 이슈"},
    {"id": "cavitation", "reason": "캐비테이션 악화 — 랜덤 이슈"},
    {"id": "loose_base", "reason": "기초 볼트 풀림 — 랜덤 이슈"},
)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_db_path = Path(os.getenv("PLANT_DB", str(_HERE.parent / "data" / "plant.db")))
_started_at = datetime.now(timezone.utc).isoformat()
_last_spike_at = time.monotonic()
_active_spike_sensor: str | None = None
_spike_until = 0.0
_last_random_issue_at = time.monotonic()
_feed_started = False


def classify_rms(rms_mm_s: float) -> str:
    if rms_mm_s >= ANOMALY_RMS_MM_S:
        return "anomaly"
    if rms_mm_s >= WARNING_RMS_MM_S:
        return "warning"
    return "normal"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _db_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_db_path), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(_conn)
        _seed_assets(_conn)
    return _conn


def configure(db_path: str | Path) -> None:
    """Tests (and rare reroutes) point the plant at another sqlite file."""
    global _conn, _db_path, _last_spike_at, _active_spike_sensor, _spike_until, _last_random_issue_at
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None
        _db_path = Path(db_path)
        _last_spike_at = time.monotonic()
        _active_spike_sensor = None
        _spike_until = 0.0
        _last_random_issue_at = time.monotonic()
        _connect()


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            generation INTEGER NOT NULL,
            serial TEXT NOT NULL,
            power TEXT NOT NULL,
            health TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_reason TEXT,
            last_reason_at TEXT,
            last_reason_source TEXT
        );
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            rms_mm_s REAL NOT NULL,
            peak_g REAL NOT NULL,
            temperature_c REAL NOT NULL,
            status TEXT NOT NULL,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_readings_sensor_id
            ON readings(sensor_id, id DESC);
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            asset_id TEXT,
            sensor_id TEXT,
            detail TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_asset
            ON events(asset_id, id DESC);
        CREATE TABLE IF NOT EXISTS sensor_anomaly_counts (
            asset_id TEXT NOT NULL,
            sensor_id TEXT NOT NULL,
            generation INTEGER NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (asset_id, sensor_id, generation)
        );
        CREATE TABLE IF NOT EXISTS fix_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            requested_at TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            resolved_at TEXT,
            resolved_by TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_fix_requests_status
            ON fix_requests(status, id DESC);
        """
    )
    cols = _column_names(conn, "assets")
    if "last_reason" not in cols:
        conn.execute("ALTER TABLE assets ADD COLUMN last_reason TEXT")
    if "last_reason_at" not in cols:
        conn.execute("ALTER TABLE assets ADD COLUMN last_reason_at TEXT")
    if "last_reason_source" not in cols:
        conn.execute("ALTER TABLE assets ADD COLUMN last_reason_source TEXT")
    if "last_fix_at" not in cols:
        conn.execute("ALTER TABLE assets ADD COLUMN last_fix_at TEXT")
    conn.commit()


def _seed_assets(conn: sqlite3.Connection) -> None:
    now = _now()
    for asset in ASSETS:
        conn.execute(
            """
            INSERT OR IGNORE INTO assets
                (asset_id, generation, serial, power, health, updated_at)
            VALUES (?, 1, ?, 'on', 'ok', ?)
            """,
            (asset["id"], make_serial(asset["serial_prefix"], 1), now),
        )
    conn.commit()


def _asset_row(conn: sqlite3.Connection, asset_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()


def _add_event(
    conn: sqlite3.Connection,
    kind: str,
    *,
    asset_id: str | None = None,
    sensor_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        "INSERT INTO events (ts, kind, asset_id, sensor_id, detail) VALUES (?, ?, ?, ?, ?)",
        (_now(), kind, asset_id, sensor_id, json.dumps(detail or {}, ensure_ascii=False)),
    )
    conn.execute(
        "DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT ?)",
        (MAX_EVENTS,),
    )


def _trim_readings(conn: sqlite3.Connection, sensor_id: str) -> None:
    conn.execute(
        """
        DELETE FROM readings
        WHERE sensor_id = ?
          AND id NOT IN (
              SELECT id FROM readings WHERE sensor_id = ? ORDER BY id DESC LIMIT ?
          )
        """,
        (sensor_id, sensor_id, MAX_READINGS_PER_SENSOR),
    )


def _fix_row_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "request_id": row["id"],
        "asset_id": row["asset_id"],
        "status": row["status"],
        "note": row["note"] or "",
        "requested_at": row["requested_at"],
        "requested_by": row["requested_by"],
        "resolved_at": row["resolved_at"],
        "resolved_by": row["resolved_by"],
    }


def _pending_fix_public(conn: sqlite3.Connection, asset_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM fix_requests
        WHERE asset_id = ? AND status = 'pending'
        ORDER BY id DESC LIMIT 1
        """,
        (asset_id,),
    ).fetchone()
    return _fix_row_public(row) if row else None


def _close_pending_locked(
    conn: sqlite3.Connection,
    asset_id: str,
    *,
    status: str,
    resolved_by: str,
    request_id: int | None = None,
) -> None:
    now = _now()
    if request_id is not None:
        conn.execute(
            """
            UPDATE fix_requests
            SET status = ?, resolved_at = ?, resolved_by = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status, now, resolved_by, request_id),
        )
        conn.execute(
            """
            UPDATE fix_requests
            SET status = 'superseded', resolved_at = ?, resolved_by = ?
            WHERE asset_id = ? AND status = 'pending' AND id != ?
            """,
            (now, resolved_by, asset_id, request_id),
        )
        return
    conn.execute(
        """
        UPDATE fix_requests
        SET status = ?, resolved_at = ?, resolved_by = ?
        WHERE asset_id = ? AND status = 'pending'
        """,
        (status, now, resolved_by, asset_id),
    )


def _counts_map(conn: sqlite3.Connection, asset_id: str, generation: int) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT sensor_id, count FROM sensor_anomaly_counts
        WHERE asset_id = ? AND generation = ?
        """,
        (asset_id, generation),
    ).fetchall()
    return {row["sensor_id"]: int(row["count"]) for row in rows}


def _bump_anomaly(conn: sqlite3.Connection, sensor: dict[str, Any], asset: sqlite3.Row) -> int:
    conn.execute(
        """
        INSERT INTO sensor_anomaly_counts (asset_id, sensor_id, generation, count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(asset_id, sensor_id, generation)
        DO UPDATE SET count = count + 1
        """,
        (sensor["asset_id"], sensor["id"], asset["generation"]),
    )
    row = conn.execute(
        """
        SELECT count FROM sensor_anomaly_counts
        WHERE asset_id = ? AND sensor_id = ? AND generation = ?
        """,
        (sensor["asset_id"], sensor["id"], asset["generation"]),
    ).fetchone()
    return int(row["count"]) if row else 1


def _event_count(conn: sqlite3.Connection, kind: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM events WHERE kind = ?", (kind,)).fetchone()
    return int(row["n"]) if row else 0


def _choose_spike_sensor(conn: sqlite3.Connection) -> str | None:
    eligible: list[str] = []
    for sensor in SENSORS:
        asset = _asset_row(conn, sensor["asset_id"])
        if asset is not None and asset["power"] == "on" and asset["health"] == "ok":
            eligible.append(sensor["id"])
    if not eligible:
        return None
    if SPIKE_SENSOR_ID in eligible and random.random() < SPIKE_BIAS:
        return SPIKE_SENSOR_ID
    return random.choice(eligible)


def _healthy_asset_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT asset_id FROM assets WHERE power = 'on' AND health = 'ok' ORDER BY asset_id"
    ).fetchall()
    return [row["asset_id"] for row in rows]


def _apply_random_issue(conn: sqlite3.Connection, asset_id: str | None = None) -> str | None:
    """Fail one healthy machine for a non-vibration classroom incident."""
    wanted = (asset_id or "").strip() or None
    if wanted:
        row = _asset_row(conn, wanted)
        if row is None or row["power"] != "on" or row["health"] != "ok":
            return None
        target = wanted
    else:
        choices = _healthy_asset_ids(conn)
        if not choices:
            return None
        target = random.choice(choices)
    issue = random.choice(RANDOM_ISSUES)
    reason = f"{issue['reason']} ({target})"
    _fail_asset_locked(
        conn,
        target,
        source="random",
        reason=reason,
        extra={"issue_id": issue["id"], "issue": issue["reason"]},
    )
    return target


def _set_reason(
    conn: sqlite3.Connection,
    asset_id: str,
    reason: str,
    source: str,
    *,
    at: str | None = None,
) -> None:
    stamp = at or _now()
    conn.execute(
        """
        UPDATE assets
        SET last_reason = ?, last_reason_at = ?, last_reason_source = ?
        WHERE asset_id = ?
        """,
        (reason, stamp, source, asset_id),
    )


def _fail_asset_locked(
    conn: sqlite3.Connection,
    asset_id: str,
    *,
    source: str,
    reason: str,
    sensor_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> sqlite3.Row | None:
    row = _asset_row(conn, asset_id)
    if row is None:
        return None
    now = _now()
    conn.execute(
        """
        UPDATE assets
        SET health = 'failed', power = 'off', updated_at = ?,
            last_reason = ?, last_reason_at = ?, last_reason_source = ?
        WHERE asset_id = ?
        """,
        (now, reason, now, source, asset_id),
    )
    detail = {
        "serial": row["serial"],
        "generation": row["generation"],
        "reason": reason,
        "source": source,
    }
    if extra:
        detail.update(extra)
    _add_event(conn, "fail", asset_id=asset_id, sensor_id=sensor_id, detail=detail)
    return _asset_row(conn, asset_id)


def _reading_for(sensor: dict[str, Any], asset: sqlite3.Row, *, spike: bool) -> dict[str, Any]:
    if asset["health"] == "failed":
        rms, peak, temp, status = 0.0, 0.0, sensor["base_temp"], "failed"
    elif asset["power"] != "on":
        rms, peak, temp, status = 0.0, 0.0, sensor["base_temp"] - 4.0, "offline"
    elif spike:
        rms = round(random.uniform(ANOMALY_RMS_MM_S + 0.4, ANOMALY_RMS_MM_S + 3.5), 2)
        peak = round(random.uniform(3.2, 5.0), 2)
        temp = round(sensor["base_temp"] + random.uniform(6.0, 12.0), 1)
        status = classify_rms(rms)
    else:
        rms = round(max(sensor["base_rms"] + random.uniform(-0.25, 0.35), 0.1), 2)
        peak = round(max(sensor["base_peak"] + random.uniform(-0.08, 0.10), 0.05), 2)
        temp = round(sensor["base_temp"] + random.uniform(-1.5, 2.0), 1)
        status = classify_rms(rms)
    return {
        "sensor_id": sensor["id"],
        "asset_id": sensor["asset_id"],
        "rms_mm_s": rms,
        "peak_g": peak,
        "temperature_c": temp,
        "status": status,
        "ts": _now(),
        "dummy": True,
    }


def tick(
    force_spike_sensor: str | None = None,
    force_random_issue: str | None = None,
) -> None:
    """Write one round of dummy readings. Safe to call from tests."""
    global _last_spike_at, _active_spike_sensor, _spike_until, _last_random_issue_at
    with _lock:
        conn = _connect()
        now = time.monotonic()
        spike_id: str | None = None
        count_this = False

        if force_spike_sensor:
            spike_id = force_spike_sensor
            count_this = True
            _last_spike_at = now
            _active_spike_sensor = None
            _spike_until = 0.0
        elif _active_spike_sensor and now < _spike_until:
            asset = _asset_row(conn, next(
                (s["asset_id"] for s in SENSORS if s["id"] == _active_spike_sensor),
                "",
            ))
            if asset is not None and asset["power"] == "on" and asset["health"] == "ok":
                spike_id = _active_spike_sensor
            else:
                _active_spike_sensor = None
                _spike_until = 0.0
        elif (now - _last_spike_at) >= ANOMALY_EVERY_SEC:
            spike_id = _choose_spike_sensor(conn)
            if spike_id:
                count_this = True
                _last_spike_at = now
                _active_spike_sensor = spike_id
                _spike_until = now + ANOMALY_HOLD_SEC

        trips: dict[str, tuple[str, int, int]] = {}
        for sensor in SENSORS:
            asset = _asset_row(conn, sensor["asset_id"])
            if asset is None:
                continue
            do_spike = (
                spike_id == sensor["id"]
                and asset["power"] == "on"
                and asset["health"] == "ok"
            )
            row = _reading_for(sensor, asset, spike=do_spike)
            conn.execute(
                """
                INSERT INTO readings
                    (sensor_id, asset_id, rms_mm_s, peak_g, temperature_c, status, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["sensor_id"],
                    row["asset_id"],
                    row["rms_mm_s"],
                    row["peak_g"],
                    row["temperature_c"],
                    row["status"],
                    row["ts"],
                ),
            )
            _trim_readings(conn, sensor["id"])
            if row["status"] == "anomaly" and count_this:
                new_count = _bump_anomaly(conn, sensor, asset)
                _add_event(
                    conn,
                    "anomaly",
                    asset_id=sensor["asset_id"],
                    sensor_id=sensor["id"],
                    detail={
                        "rms_mm_s": row["rms_mm_s"],
                        "ts": row["ts"],
                        "count": new_count,
                        "trip_limit": TRIP_ANOMALY_COUNT,
                        "generation": asset["generation"],
                    },
                )
                if new_count >= TRIP_ANOMALY_COUNT:
                    trips[sensor["asset_id"]] = (sensor["id"], new_count, int(asset["generation"]))

        for asset_id, (sensor_id, count, generation) in trips.items():
            reason = (
                f"{sensor_id} 이상 {count}회 누적 (세대 {generation}) — 자동 트립"
            )
            _fail_asset_locked(
                conn,
                asset_id,
                source="trip",
                reason=reason,
                sensor_id=sensor_id,
                extra={"count": count, "trip_limit": TRIP_ANOMALY_COUNT, "generation": generation},
            )
            if _active_spike_sensor:
                owner = next(
                    (s["asset_id"] for s in SENSORS if s["id"] == _active_spike_sensor),
                    None,
                )
                if owner == asset_id:
                    _active_spike_sensor = None
                    _spike_until = 0.0

        do_random = False
        random_target: str | None = None
        if force_random_issue:
            do_random = True
            random_target = force_random_issue
            _last_random_issue_at = now
        elif (
            not force_spike_sensor
            and (now - _last_random_issue_at) >= RANDOM_ISSUE_EVERY_SEC
        ):
            _last_random_issue_at = now
            do_random = random.random() < RANDOM_ISSUE_CHANCE
        if do_random:
            _apply_random_issue(conn, random_target)

        conn.commit()


def start_feed() -> None:
    global _feed_started
    with _lock:
        if _feed_started:
            return
        _feed_started = True
        _connect()

    def _loop() -> None:
        print(f"dummy plant db {_db_path}", flush=True)
        while True:
            try:
                tick()
            except Exception as exc:  # noqa: BLE001
                print(f"plant tick failed ({exc})", flush=True)
            time.sleep(PUBLISH_INTERVAL_SEC)

    threading.Thread(target=_loop, name="plant-feed", daemon=True).start()


def _asset_public(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    catalog = get_asset(row["asset_id"]) or {}
    attached = [item["id"] for item in sensors_for_asset(row["asset_id"])]
    counts = _counts_map(conn, row["asset_id"], int(row["generation"]))
    return {
        "asset_id": row["asset_id"],
        "name": catalog.get("name", row["asset_id"]),
        "name_ko": catalog.get("name_ko", row["asset_id"]),
        "kind": catalog.get("kind", "machine"),
        "zone": catalog.get("zone", "unknown"),
        "label": catalog.get("label", row["asset_id"]),
        "x": catalog.get("x"),
        "y": catalog.get("y"),
        "w": catalog.get("w"),
        "h": catalog.get("h"),
        "serial": row["serial"],
        "generation": row["generation"],
        "power": row["power"],
        "health": row["health"],
        "updated_at": row["updated_at"],
        "last_reason": row["last_reason"],
        "last_reason_at": row["last_reason_at"],
        "last_reason_source": row["last_reason_source"],
        "sensor_ids": attached,
        "anomaly_counts": counts,
        "anomaly_total": sum(counts.values()),
        "trip_anomaly_count": TRIP_ANOMALY_COUNT,
        "pending_fix": _pending_fix_public(conn, row["asset_id"]),
        "last_fix_at": row["last_fix_at"] if "last_fix_at" in row.keys() else None,
    }


def snapshot_assets() -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        rows = conn.execute("SELECT * FROM assets ORDER BY asset_id").fetchall()
        return [_asset_public(conn, row) for row in rows]


def get_asset_state(asset_id: str) -> dict[str, Any] | None:
    wanted = (asset_id or "").strip()
    with _lock:
        conn = _connect()
        row = _asset_row(conn, wanted)
        if row is None:
            return None
        public = _asset_public(conn, row)
        public["events"] = _events_locked(conn, limit=12, asset_id=wanted)
        return public


def snapshot_sensors() -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        assets = {
            row["asset_id"]: row
            for row in conn.execute("SELECT * FROM assets").fetchall()
        }
        latest = {}
        counts_by_asset: dict[str, dict[str, int]] = {}
        for asset_id, asset in assets.items():
            counts_by_asset[asset_id] = _counts_map(conn, asset_id, int(asset["generation"]))
        for sensor in SENSORS:
            row = conn.execute(
                "SELECT * FROM readings WHERE sensor_id = ? ORDER BY id DESC LIMIT 1",
                (sensor["id"],),
            ).fetchone()
            if row is not None:
                latest[sensor["id"]] = row
    rows = []
    for sensor in SENSORS:
        asset = assets.get(sensor["asset_id"])
        last = latest.get(sensor["id"])
        counts = counts_by_asset.get(sensor["asset_id"], {})
        rows.append(
            {
                "sensor_id": sensor["id"],
                "name": sensor["name"],
                "name_ko": sensor["name_ko"],
                "asset_id": sensor["asset_id"],
                "location": sensor["location"],
                "zone": sensor["zone"],
                "x": sensor["x"],
                "y": sensor["y"],
                "last_status": None if last is None else last["status"],
                "last_rms_mm_s": None if last is None else last["rms_mm_s"],
                "last_peak_g": None if last is None else last["peak_g"],
                "last_temperature_c": None if last is None else last["temperature_c"],
                "last_ts": None if last is None else last["ts"],
                "has_reading": last is not None,
                "asset_power": None if asset is None else asset["power"],
                "asset_health": None if asset is None else asset["health"],
                "anomaly_count": counts.get(sensor["id"], 0),
                "trip_anomaly_count": TRIP_ANOMALY_COUNT,
            }
        )
    return rows


def latest_reading(sensor_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM readings WHERE sensor_id = ? ORDER BY id DESC LIMIT 1",
            (sensor_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def _parse_event_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    try:
        item["detail"] = json.loads(item["detail"])
    except (TypeError, ValueError):
        pass
    return item


def _events_locked(
    conn: sqlite3.Connection,
    *,
    limit: int = 10,
    kind: str | None = None,
    asset_id: str | None = None,
) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 80))
    clauses: list[str] = []
    args: list[Any] = []
    if kind:
        clauses.append("kind = ?")
        args.append(kind)
    if asset_id:
        clauses.append("asset_id = ?")
        args.append(asset_id)
    sql = "SELECT * FROM events"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(cap)
    return [_parse_event_row(row) for row in conn.execute(sql, args).fetchall()]


def recent_events(
    limit: int = 10,
    kind: str | None = None,
    asset_id: str | None = None,
) -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        return _events_locked(conn, limit=limit, kind=kind, asset_id=asset_id)


def snapshot_events_by_asset(per_asset: int = 8) -> dict[str, list[dict[str, Any]]]:
    cap = max(1, min(int(per_asset), 20))
    with _lock:
        conn = _connect()
        rows = _events_locked(conn, limit=240)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        aid = item.get("asset_id")
        if not aid:
            continue
        bucket = grouped.setdefault(aid, [])
        if len(bucket) < cap:
            bucket.append(item)
    return grouped


def recent_anomalies(limit: int = 10) -> list[dict[str, Any]]:
    return recent_events(limit=limit, kind="anomaly")


def factory_snapshot() -> dict[str, Any]:
    assets = snapshot_assets()
    sensors = snapshot_sensors()
    with _lock:
        conn = _connect()
        anomaly_total = _event_count(conn, "anomaly")
    live = sum(1 for row in sensors if row.get("last_status") == "anomaly")
    pending = snapshot_fix_requests("pending")
    logs = snapshot_events_by_asset(8)
    by_asset: dict[str, list[dict[str, Any]]] = {}
    for sensor in sensors:
        by_asset.setdefault(sensor["asset_id"], []).append(sensor)
    for asset in assets:
        asset["sensors"] = by_asset.get(asset["asset_id"], [])
        asset["events"] = logs.get(asset["asset_id"], [])
    return {
        "plant": PLANT,
        "zones": [dict(zone) for zone in ZONES],
        "assets": assets,
        "sensors": sensors,
        "anomaly_count": anomaly_total,
        "live_anomaly_count": live,
        "failed_count": sum(1 for row in assets if row.get("health") == "failed"),
        "off_count": sum(1 for row in assets if row.get("power") != "on"),
        "fix_requests": pending,
        "pending_fix_count": len(pending),
        "trip_anomaly_count": TRIP_ANOMALY_COUNT,
        "sensor_count": len(sensors),
        "asset_count": len(assets),
        "thresholds": {
            "warning_rms_mm_s": WARNING_RMS_MM_S,
            "anomaly_rms_mm_s": ANOMALY_RMS_MM_S,
            "anomaly_every_sec": ANOMALY_EVERY_SEC,
            "trip_anomaly_count": TRIP_ANOMALY_COUNT,
        },
        "db": str(_db_path),
        "ts": _now(),
        "dummy": True,
    }


def health() -> dict[str, Any]:
    assets = snapshot_assets()
    sensors = snapshot_sensors()
    return {
        "ok": True,
        "service": "dummy-plant",
        "plant": PLANT["id"],
        "view": PLANT["view"],
        "db": str(_db_path),
        "asset_count": len(assets),
        "sensor_count": len(sensors),
        "sensors_with_readings": sum(1 for row in sensors if row["has_reading"]),
        "failed_assets": [row["asset_id"] for row in assets if row["health"] == "failed"],
        "started_at": _started_at,
        "factory_map": "/",
        "mcp_path": os.getenv("MCP_PATH", "/mcp"),
        "dummy": True,
    }


def set_asset_power(asset_id: str, on: bool, *, source: str = "mcp") -> dict[str, Any]:
    wanted = (asset_id or "").strip()
    catalog = get_asset(wanted)
    if catalog is None:
        return {"ok": False, "error": "unknown asset_id", "known_assets": [a["id"] for a in ASSETS]}
    with _lock:
        conn = _connect()
        row = _asset_row(conn, wanted)
        if row is None:
            return {"ok": False, "error": "asset missing from db", "asset_id": wanted}
        if on and row["health"] == "failed":
            return {
                "ok": False,
                "error": "failed assets cannot be turned on; worker FIX or replace_asset first",
                "asset_id": wanted,
                "health": row["health"],
                "serial": row["serial"],
                "last_reason": row["last_reason"],
            }
        power = "on" if on else "off"
        now = _now()
        conn.execute(
            "UPDATE assets SET power = ?, updated_at = ? WHERE asset_id = ?",
            (power, now, wanted),
        )
        reason = None
        if not on:
            if row["health"] == "failed" and row["last_reason"]:
                reason = row["last_reason"]
            else:
                reason = POWER_OFF_REASONS.get(source, f"{source}에서 전원을 끔")
                _set_reason(conn, wanted, reason, source, at=now)
        _add_event(
            conn,
            "power",
            asset_id=wanted,
            detail={
                "power": power,
                "serial": row["serial"],
                "source": source,
                "reason": reason,
            },
        )
        conn.commit()
        fresh = _asset_row(conn, wanted)
        public = _asset_public(conn, fresh) if fresh else {"asset_id": wanted, "power": power}
    return {
        "ok": True,
        "note": "Dummy plant side effect. Not a real machine.",
        "asset": public,
    }


def fail_asset(asset_id: str, *, source: str = "mcp", reason: str | None = None) -> dict[str, Any]:
    wanted = (asset_id or "").strip()
    if get_asset(wanted) is None:
        return {"ok": False, "error": "unknown asset_id", "known_assets": [a["id"] for a in ASSETS]}
    why = reason or FAIL_REASONS.get(source, FAIL_REASONS["mcp"])
    with _lock:
        conn = _connect()
        row = _asset_row(conn, wanted)
        if row is None:
            return {"ok": False, "error": "asset missing from db", "asset_id": wanted}
        fresh = _fail_asset_locked(conn, wanted, source=source, reason=why)
        conn.commit()
        public = (
            _asset_public(conn, fresh)
            if fresh
            else {"asset_id": wanted, "health": "failed"}
        )
    return {
        "ok": True,
        "note": "Dummy failure. Down until a worker accepts FIX or replace_asset.",
        "asset": public,
    }


def replace_asset(asset_id: str) -> dict[str, Any]:
    wanted = (asset_id or "").strip()
    catalog = get_asset(wanted)
    if catalog is None:
        return {"ok": False, "error": "unknown asset_id", "known_assets": [a["id"] for a in ASSETS]}
    with _lock:
        conn = _connect()
        row = _asset_row(conn, wanted)
        if row is None:
            return {"ok": False, "error": "asset missing from db", "asset_id": wanted}
        if row["health"] != "failed":
            return {
                "ok": False,
                "error": "replace_asset is only for failed instances",
                "asset_id": wanted,
                "health": row["health"],
            }
        generation = int(row["generation"]) + 1
        serial = make_serial(catalog["serial_prefix"], generation)
        now = _now()
        conn.execute(
            """
            UPDATE assets
            SET generation = ?, serial = ?, health = 'ok', power = 'on',
                updated_at = ?, last_reason = NULL, last_reason_at = NULL,
                last_reason_source = NULL
            WHERE asset_id = ?
            """,
            (generation, serial, now, wanted),
        )
        _add_event(
            conn,
            "replace",
            asset_id=wanted,
            detail={"old_serial": row["serial"], "new_serial": serial, "generation": generation},
        )
        conn.commit()
        fresh = _asset_row(conn, wanted)
        public = _asset_public(conn, fresh) if fresh else {"asset_id": wanted, "serial": serial}
    return {
        "ok": True,
        "note": "Dummy swap. New serial is running. This is not a real spare-parts workflow.",
        "asset": public,
        "replaced": {"old_serial": row["serial"], "new_serial": serial},
    }


def snapshot_fix_requests(status: str | None = "pending") -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        if status:
            rows = conn.execute(
                "SELECT * FROM fix_requests WHERE status = ? ORDER BY id DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM fix_requests ORDER BY id DESC LIMIT 20"
            ).fetchall()
        out = []
        for row in rows:
            item = _fix_row_public(row)
            asset = _asset_row(conn, row["asset_id"])
            if asset is not None:
                catalog = get_asset(row["asset_id"]) or {}
                counts = _counts_map(conn, row["asset_id"], int(asset["generation"]))
                item["name_ko"] = catalog.get("name_ko", row["asset_id"])
                item["serial"] = asset["serial"]
                item["health"] = asset["health"]
                item["power"] = asset["power"]
                item["anomaly_total"] = sum(counts.values())
                item["trip_anomaly_count"] = TRIP_ANOMALY_COUNT
            out.append(item)
        return out


def request_fix(asset_id: str, note: str = "", *, source: str = "mcp") -> dict[str, Any]:
    wanted = (asset_id or "").strip()
    catalog = get_asset(wanted)
    if catalog is None:
        return {"ok": False, "error": "unknown asset_id", "known_assets": [a["id"] for a in ASSETS]}
    message = (note or "").strip()
    with _lock:
        conn = _connect()
        row = _asset_row(conn, wanted)
        if row is None:
            return {"ok": False, "error": "asset missing from db", "asset_id": wanted}
        existing = conn.execute(
            """
            SELECT * FROM fix_requests
            WHERE asset_id = ? AND status = 'pending'
            ORDER BY id DESC LIMIT 1
            """,
            (wanted,),
        ).fetchone()
        if existing is not None:
            if message:
                conn.execute(
                    "UPDATE fix_requests SET note = ? WHERE id = ?",
                    (message, existing["id"]),
                )
                conn.commit()
                existing = conn.execute(
                    "SELECT * FROM fix_requests WHERE id = ?",
                    (existing["id"],),
                ).fetchone()
            return {
                "ok": True,
                "already_pending": True,
                "note": "Fix is already waiting on the factory screen. The agent cannot apply it.",
                "request": _fix_row_public(existing),
                "asset": _asset_public(conn, row),
            }
        conn.execute(
            """
            INSERT INTO fix_requests
                (asset_id, status, note, requested_at, requested_by)
            VALUES (?, 'pending', ?, ?, ?)
            """,
            (wanted, message, _now(), source),
        )
        request_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        _add_event(
            conn,
            "fix_request",
            asset_id=wanted,
            detail={"request_id": request_id, "note": message, "source": source},
        )
        conn.commit()
        req = conn.execute("SELECT * FROM fix_requests WHERE id = ?", (request_id,)).fetchone()
        public = _asset_public(conn, _asset_row(conn, wanted) or row)
    return {
        "ok": True,
        "already_pending": False,
        "note": (
            "Requested a worker FIX. It appears on http://localhost:8000 . "
            "The agent does not wrench the machine. Wait for Accept, then re-read the asset."
        ),
        "request": _fix_row_public(req) if req else {"request_id": request_id, "asset_id": wanted},
        "asset": public,
    }


def _apply_fix_locked(
    conn: sqlite3.Connection,
    asset_id: str,
    *,
    source: str,
    request_id: int | None = None,
) -> dict[str, Any]:
    global _active_spike_sensor, _spike_until
    row = _asset_row(conn, asset_id)
    if row is None:
        return {"ok": False, "error": "asset missing from db", "asset_id": asset_id}
    generation = int(row["generation"])
    counts_before = _counts_map(conn, asset_id, generation)
    was_failed = row["health"] == "failed"
    now = _now()
    conn.execute(
        "DELETE FROM sensor_anomaly_counts WHERE asset_id = ? AND generation = ?",
        (asset_id, generation),
    )
    if was_failed:
        conn.execute(
            """
            UPDATE assets
            SET health = 'ok', power = 'on', updated_at = ?,
                last_reason = NULL, last_reason_at = NULL, last_reason_source = NULL,
                last_fix_at = ?
            WHERE asset_id = ?
            """,
            (now, now, asset_id),
        )
    else:
        conn.execute(
            "UPDATE assets SET updated_at = ?, last_fix_at = ? WHERE asset_id = ?",
            (now, now, asset_id),
        )
    _close_pending_locked(
        conn,
        asset_id,
        status="accepted",
        resolved_by=source,
        request_id=request_id,
    )
    _add_event(
        conn,
        "fix",
        asset_id=asset_id,
        detail={
            "source": source,
            "request_id": request_id,
            "was_failed": was_failed,
            "serial": row["serial"],
            "generation": generation,
            "counts_before": counts_before,
        },
    )
    owner = next((s["asset_id"] for s in SENSORS if s["id"] == _active_spike_sensor), None)
    if owner == asset_id:
        _active_spike_sensor = None
        _spike_until = 0.0
    conn.commit()
    fresh = _asset_row(conn, asset_id)
    return {
        "ok": True,
        "note": "Dummy FIX. Anomaly counts reset. Same serial. Not a real work order.",
        "asset": _asset_public(conn, fresh) if fresh else {"asset_id": asset_id},
        "was_failed": was_failed,
        "counts_before": counts_before,
    }


def apply_fix(asset_id: str, *, source: str = "ui", request_id: int | None = None) -> dict[str, Any]:
    wanted = (asset_id or "").strip()
    if get_asset(wanted) is None:
        return {"ok": False, "error": "unknown asset_id", "known_assets": [a["id"] for a in ASSETS]}
    with _lock:
        conn = _connect()
        row = _asset_row(conn, wanted)
        if row is None:
            return {"ok": False, "error": "asset missing from db", "asset_id": wanted}
        return _apply_fix_locked(conn, wanted, source=source, request_id=request_id)


def accept_fix(request_id: int, *, source: str = "ui") -> dict[str, Any]:
    try:
        rid = int(request_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "request_id must be an integer"}
    with _lock:
        conn = _connect()
        req = conn.execute("SELECT * FROM fix_requests WHERE id = ?", (rid,)).fetchone()
        if req is None:
            return {"ok": False, "error": "unknown request_id", "request_id": rid}
        if req["status"] != "pending":
            return {
                "ok": False,
                "error": "request is not pending",
                "request": _fix_row_public(req),
            }
        return _apply_fix_locked(conn, req["asset_id"], source=source, request_id=rid)


def dismiss_fix(request_id: int, *, source: str = "ui") -> dict[str, Any]:
    try:
        rid = int(request_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "request_id must be an integer"}
    with _lock:
        conn = _connect()
        req = conn.execute("SELECT * FROM fix_requests WHERE id = ?", (rid,)).fetchone()
        if req is None:
            return {"ok": False, "error": "unknown request_id", "request_id": rid}
        if req["status"] != "pending":
            return {
                "ok": False,
                "error": "request is not pending",
                "request": _fix_row_public(req),
            }
        conn.execute(
            """
            UPDATE fix_requests
            SET status = 'dismissed', resolved_at = ?, resolved_by = ?
            WHERE id = ?
            """,
            (_now(), source, rid),
        )
        _add_event(
            conn,
            "fix_request",
            asset_id=req["asset_id"],
            detail={"request_id": rid, "status": "dismissed", "source": source},
        )
        conn.commit()
        fresh = conn.execute("SELECT * FROM fix_requests WHERE id = ?", (rid,)).fetchone()
    return {"ok": True, "request": _fix_row_public(fresh) if fresh else {"request_id": rid}}


def reset_plant() -> dict[str, Any]:
    """Wipe SQLite dummy history and reseed healthy equipment. UI sandbox only."""
    global _last_spike_at, _active_spike_sensor, _spike_until, _last_random_issue_at
    with _lock:
        conn = _connect()
        conn.executescript(
            """
            DELETE FROM readings;
            DELETE FROM events;
            DELETE FROM sensor_anomaly_counts;
            DELETE FROM fix_requests;
            DELETE FROM assets;
            """
        )
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
        ).fetchone():
            conn.execute("DELETE FROM sqlite_sequence")
        _seed_assets(conn)
        _last_spike_at = time.monotonic()
        _active_spike_sensor = None
        _spike_until = 0.0
        _last_random_issue_at = time.monotonic()
        conn.commit()
        assets = conn.execute("SELECT COUNT(*) AS n FROM assets").fetchone()["n"]
    return {
        "ok": True,
        "note": "Dummy SQLite wiped and reseeded. Not a real historian reset.",
        "asset_count": int(assets),
        "sensor_count": len(SENSORS),
    }
