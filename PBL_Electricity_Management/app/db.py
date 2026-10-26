"""SQLite storage for rooms, readings, alerts, relay commands and settings."""
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    fans    INTEGER NOT NULL,
    lights  INTEGER NOT NULL,
    acs     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS readings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id   TEXT NOT NULL REFERENCES rooms(id),
    ts        REAL NOT NULL,
    people    INTEGER NOT NULL,
    fans_on   INTEGER NOT NULL,
    lights_on INTEGER NOT NULL,
    t1 REAL, t2 REAL, t3 REAL, t4 REAL,
    state     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id     TEXT NOT NULL REFERENCES rooms(id),
    ts          REAL NOT NULL,
    type        TEXT NOT NULL,
    message     TEXT NOT NULL,
    value       REAL,
    status      TEXT NOT NULL DEFAULT 'OPEN',
    ack_by      TEXT,
    ack_remarks TEXT,
    ack_at      REAL
);
CREATE TABLE IF NOT EXISTS commands (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id    TEXT NOT NULL REFERENCES rooms(id),
    appliance  TEXT NOT NULL,
    action     TEXT NOT NULL,
    operator   TEXT NOT NULL,
    reason     TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at REAL NOT NULL,
    done_at    REAL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value REAL NOT NULL
);
"""

DEFAULT_ROOMS = [
    ("LAB-1", "Computer Lab 1 (10 m x 8 m)", 4, 6, 2),
    ("CR-201", "Classroom 201", 4, 8, 1),
]


class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.conn:
            self.conn.executescript(SCHEMA)
            self.conn.executemany("INSERT OR IGNORE INTO rooms VALUES (?, ?, ?, ?, ?)", DEFAULT_ROOMS)

    def _all(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def _one(self, sql, args=()):
        rows = self._all(sql, args)
        return rows[0] if rows else None

    def _write(self, sql, args=()):
        with self.lock, self.conn:
            return self.conn.execute(sql, args).lastrowid

    # ----- rooms -----
    def rooms(self):
        return self._all("SELECT * FROM rooms ORDER BY id")

    def room(self, room_id):
        return self._one("SELECT * FROM rooms WHERE id = ?", (room_id,))

    # ----- readings -----
    def add_reading(self, room_id, frame, state):
        t = frame.temps
        return self._write(
            "INSERT INTO readings (room_id, ts, people, fans_on, lights_on, t1, t2, t3, t4, state) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (room_id, frame.timestamp, frame.people, frame.fans_on, frame.lights_on, t[0], t[1], t[2], t[3], state))

    def reading_count(self, room_id):
        return self._one("SELECT COUNT(*) AS n FROM readings WHERE room_id = ?", (room_id,))["n"]

    # ----- alerts -----
    def add_alert(self, alert):
        return self._write("INSERT INTO alerts (room_id, ts, type, message, value) VALUES (?, ?, ?, ?, ?)",
                           (alert["room_id"], alert["timestamp"], alert["type"], alert["message"], alert["value"]))

    def alerts(self, room_id=None, status=None):
        sql, args = "SELECT * FROM alerts WHERE 1 = 1", []
        if room_id:
            sql += " AND room_id = ?"
            args.append(room_id)
        if status:
            sql += " AND status = ?"
            args.append(status)
        return self._all(sql + " ORDER BY id DESC", args)

    def alert(self, alert_id):
        return self._one("SELECT * FROM alerts WHERE id = ?", (alert_id,))

    def acknowledge_alert(self, alert_id, operator, remarks):
        self._write("UPDATE alerts SET status = 'ACKNOWLEDGED', ack_by = ?, ack_remarks = ?, ack_at = ? WHERE id = ?",
                    (operator, remarks, time.time(), alert_id))

    # ----- relay commands (picked up by the ESP32 controller) -----
    def add_command(self, room_id, appliance, action, operator, reason):
        return self._write("INSERT INTO commands (room_id, appliance, action, operator, reason, created_at) "
                           "VALUES (?, ?, ?, ?, ?, ?)", (room_id, appliance, action, operator, reason, time.time()))

    def commands(self, room_id=None, status=None):
        sql, args = "SELECT * FROM commands WHERE 1 = 1", []
        if room_id:
            sql += " AND room_id = ?"
            args.append(room_id)
        if status:
            sql += " AND status = ?"
            args.append(status)
        return self._all(sql + " ORDER BY id DESC", args)

    def command(self, command_id):
        return self._one("SELECT * FROM commands WHERE id = ?", (command_id,))

    def complete_command(self, command_id):
        self._write("UPDATE commands SET status = 'DONE', done_at = ? WHERE id = ?", (time.time(), command_id))

    # ----- settings -----
    def load_settings(self):
        return {r["key"]: r["value"] for r in self._all("SELECT key, value FROM settings")}

    def save_settings(self, values):
        with self.lock, self.conn:
            self.conn.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", list(values.items()))
