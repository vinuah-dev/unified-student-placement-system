"""Module 2 test cases (REST API + database) and integration test cases (engine + API + database + ESP32 loop).

Every case starts its own server with an empty database, so cases do not depend on each other.
Expected results are taken from the functional requirements (docs/requirements.md).
"""
import contextlib
import io

from app import simulator

from .helpers import TestServer, api_result, frame

M2 = "M2 Dashboard & Control"
INT = "Integration (M1 + M2)"
FAST = {"vacancy_frames": 5, "wait_seconds": 60, "delta_t_threshold": 0.5}


def reading(room="LAB-1", **kw):
    d = frame(**kw)
    d["room_id"] = room
    return d


def seed_vacancy(srv, fans=2, lights=6, drop=True, room="LAB-1"):
    """Occupied for 2 s, then vacant with appliances left on; returns after the AC check finished."""
    srv.call("PUT", "/api/settings", FAST)
    for t in (1, 2):
        srv.call("POST", "/api/readings", reading(room, ts=t, people=6, fans=4, lights=6))
    for t in range(3, 8):
        srv.call("POST", "/api/readings", reading(room, ts=t, fans=fans, lights=lights))
    final = [24.0] * 4 if drop else [25.3] * 4
    srv.call("POST", "/api/readings", reading(room, ts=67, fans=fans, lights=lights, temps=final))


def with_server(fn):
    def run():
        srv = TestServer()
        try:
            return fn(srv)
        finally:
            srv.stop()
    return run


def ack(srv, alert_id=1, operator="R. Kulkarni", remarks=""):
    return api_result(*srv.call("POST", "/api/alerts/%d/ack" % alert_id, {"operator": operator, "remarks": remarks}))


def override(srv, **changes):
    body = {"room_id": "LAB-1", "appliance": "fan", "action": "OFF", "operator": "R. Kulkarni",
            "reason": "Room empty after lecture"}
    body.update(changes)
    return api_result(*srv.call("POST", "/api/override", body))


# ---------------- Module 2 case bodies ----------------

def m2_rooms(srv):
    status, body = srv.call("GET", "/api/rooms")
    return "%d: %d rooms (%s)" % (status, len(body), ", ".join(r["id"] for r in body))


def m2_valid_reading(srv):
    status, body = srv.call("POST", "/api/readings", reading(ts=1, people=5, fans=4, lights=6))
    return "%d: state=%s" % (status, body.get("state"))


def m2_missing_room(srv):
    body = frame(1, people=5)
    return api_result(*srv.call("POST", "/api/readings", body))


def m2_ack_twice(srv):
    seed_vacancy(srv)
    ack(srv)
    return ack(srv)


def m2_command_done(srv):
    override(srv)
    status, _ = srv.call("POST", "/api/commands/1/done", {})
    cmd = srv.call("GET", "/api/commands?room=LAB-1")[1][0]
    return "%d: status=%s" % (status, cmd["status"])


def m2_command_done_twice(srv):
    override(srv)
    srv.call("POST", "/api/commands/1/done", {})
    return api_result(*srv.call("POST", "/api/commands/1/done", {}))


def m2_settings_persist(srv):
    srv.call("PUT", "/api/settings", {"vacancy_frames": 8, "wait_seconds": 90, "delta_t_threshold": 0.8})
    db_path = srv.db_path
    srv.stop(cleanup=False)
    again = TestServer(db_path=db_path)
    try:
        s = again.call("GET", "/api/settings")[1]
        return "vacancy_frames=%s, wait_seconds=%s, delta_t_threshold=%s" % (
            s["vacancy_frames"], s["wait_seconds"], s["delta_t_threshold"])
    finally:
        again.stop()
        srv.tmp.cleanup()
        srv.stop = lambda cleanup=True: None   # already stopped


# ---------------- Integration case bodies ----------------

def int_alerts_stored(srv):
    seed_vacancy(srv)
    alerts = srv.call("GET", "/api/alerts?status=OPEN&room=LAB-1")[1]
    return ", ".join(sorted(a["type"] for a in alerts))


def int_room_status(srv):
    seed_vacancy(srv)
    room = srv.call("GET", "/api/rooms/LAB-1")[1]
    return "state=%s, open_alerts=%d, ac_inferred_on=%s" % (
        room["status"]["state"], room["open_alerts"], room["status"]["ac_inferred_on"])


def int_ack_updates_count(srv):
    seed_vacancy(srv)
    ack(srv, 1)
    room = srv.call("GET", "/api/rooms/LAB-1")[1]
    return "open_alerts=%d, alert 1 status=%s" % (room["open_alerts"], srv.app_alert_status(1))


def int_override_loop(srv):
    """Dashboard sends fan OFF; the ESP32 (emulated here exactly as app/simulator.py does) executes it."""
    seed_vacancy(srv, fans=2, lights=0)
    override(srv, action="OFF")
    pending = srv.call("GET", "/api/commands?status=PENDING&room=LAB-1")[1]
    for cmd in pending:
        srv.call("POST", "/api/commands/%d/done" % cmd["id"], {})
    for t in (68, 69, 70):
        srv.call("POST", "/api/readings", reading(ts=t, fans=0, lights=0, temps=[24.0] * 4))
    cmd = srv.call("GET", "/api/commands?room=LAB-1")[1][0]
    fan_alerts = [a for a in srv.call("GET", "/api/alerts?room=LAB-1")[1] if a["type"] == "FAN_ON_VACANT"]
    return "pending=%d, command status=%s, FAN_ON_VACANT alerts=%d" % (len(pending), cmd["status"], len(fan_alerts))


def int_settings_applied(srv):
    srv.call("PUT", "/api/settings", {"vacancy_frames": 3, "wait_seconds": 60, "delta_t_threshold": 0.5})
    for t, people in ((1, 4), (2, 4), (3, 0), (4, 0), (5, 0)):
        srv.call("POST", "/api/readings", reading(ts=t, people=people))
    return "state=%s" % srv.call("GET", "/api/rooms/LAB-1")[1]["status"]["state"]


def int_readings_stored(srv):
    for t in range(1, 8):
        srv.call("POST", "/api/readings", reading(ts=t, people=2))
    return "readings stored=%d" % srv.server.app.db.reading_count("LAB-1")


def int_simulator(srv):
    srv.call("PUT", "/api/settings", FAST)
    with contextlib.redirect_stdout(io.StringIO()):
        simulator.run(srv.base, "LAB-1", "ac_left_on", seconds=80, speed=5000)
    alerts = srv.call("GET", "/api/alerts?room=LAB-1")[1]
    return ", ".join(sorted(a["type"] for a in alerts))


def _alert_status(self, alert_id):
    return self.server.app.db.alert(alert_id)["status"]


TestServer.app_alert_status = _alert_status

LONG_200 = "A" * 200
LONG_201 = "A" * 201
REASON_100 = "R" * 100
REASON_101 = "R" * 101

CASES = [
    dict(id="TC_M2_01", module=M2, technique="Functional", scenario="List monitored rooms",
         data="GET /api/rooms", expected="200: 2 rooms (CR-201, LAB-1)", run=with_server(m2_rooms)),
    dict(id="TC_M2_02", module=M2, technique="Functional / EP (valid)", scenario="Post a valid reading",
         data="LAB-1, t=1, people=5, fans_on=4, lights_on=6, temps 25.0 x 4",
         expected="200: state=OCCUPIED", run=with_server(m2_valid_reading)),
    dict(id="TC_M2_03", module=M2, technique="EP (invalid)", scenario="Reading for a room that does not exist",
         data="room_id=LAB-9", expected="404: Room LAB-9 not found.",
         run=with_server(lambda s: api_result(*s.call("POST", "/api/readings", reading("LAB-9", ts=1))))),
    dict(id="TC_M2_04", module=M2, technique="Validation", scenario="Reading without room_id",
         data="body without room_id", expected="400: room_id is required.", run=with_server(m2_missing_room)),
    dict(id="TC_M2_05", module=M2, technique="Validation", scenario="Body is not valid JSON",
         data="body = {people: 3", expected="400: Request body must be valid JSON.",
         run=with_server(lambda s: api_result(*s.call("POST", "/api/readings", raw=b"{people: 3")))),
    dict(id="TC_M2_06", module=M2, technique="Validation / BVA", scenario="Region 3 temperature 50.5 deg C",
         data="temps=[25, 25, 50.5, 25]", expected="400: temperature of region 3 must be between 0 and 50 deg C.",
         run=with_server(lambda s: api_result(*s.call("POST", "/api/readings",
                                                       reading(ts=1, temps=[25, 25, 50.5, 25]))))),
    dict(id="TC_M2_07", module=M2, technique="Functional", scenario="Acknowledge an open alert",
         data="alert 1, operator='R. Kulkarni', remarks=''", expected="200: Alert 1 acknowledged by R. Kulkarni.",
         run=with_server(lambda s: (seed_vacancy(s), ack(s))[1])),
    dict(id="TC_M2_08", module=M2, technique="EP (invalid)", scenario="Acknowledge the same alert twice",
         data="alert 1 acknowledged, then again", expected="409: Alert 1 is already acknowledged.",
         run=with_server(m2_ack_twice)),
    dict(id="TC_M2_09", module=M2, technique="EP (invalid)", scenario="Acknowledge an alert that does not exist",
         data="alert 999", expected="404: Alert 999 not found.",
         run=with_server(lambda s: (seed_vacancy(s), ack(s, 999))[1])),
    dict(id="TC_M2_10", module=M2, technique="BVA (min - 1)", scenario="Operator name of 2 characters",
         data="operator='Ra'",
         expected="400: Operator name must be 3 to 40 characters (letters, spaces and dots only).",
         run=with_server(lambda s: (seed_vacancy(s), ack(s, operator="Ra"))[1])),
    dict(id="TC_M2_11", module=M2, technique="BVA (min)", scenario="Operator name of 3 characters",
         data="operator='Ram'", expected="200: Alert 1 acknowledged by Ram.",
         run=with_server(lambda s: (seed_vacancy(s), ack(s, operator="Ram"))[1])),
    dict(id="TC_M2_12", module=M2, technique="BVA (max + 1)", scenario="Remarks of 201 characters",
         data="remarks = 'A' x 201", expected="400: Remarks cannot exceed 200 characters.",
         run=with_server(lambda s: (seed_vacancy(s), ack(s, remarks=LONG_201))[1])),
    dict(id="TC_M2_13", module=M2, technique="BVA (max)", scenario="Remarks of 200 characters",
         data="remarks = 'A' x 200", expected="200: Alert 1 acknowledged by R. Kulkarni.",
         run=with_server(lambda s: (seed_vacancy(s), ack(s, remarks=LONG_200))[1])),
    dict(id="TC_M2_14", module=M2, technique="Functional", scenario="Manual override: switch fans OFF",
         data="LAB-1, fan, OFF, 'R. Kulkarni', 'Room empty after lecture'",
         expected="200: Command 1 queued: switch fan OFF in LAB-1.", run=with_server(lambda s: override(s))),
    dict(id="TC_M2_15", module=M2, technique="EP (invalid)", scenario="Override for an unsupported appliance",
         data="appliance='ac'", expected="400: Appliance must be fan or light.",
         run=with_server(lambda s: override(s, appliance="ac"))),
    dict(id="TC_M2_16", module=M2, technique="EP (invalid)", scenario="Action in lower case",
         data="action='on'", expected="400: Action must be ON or OFF.",
         run=with_server(lambda s: override(s, action="on"))),
    dict(id="TC_M2_17", module=M2, technique="BVA (min - 1)", scenario="Reason of 4 characters",
         data="reason='Idle'", expected="400: Reason must be 5 to 100 characters.",
         run=with_server(lambda s: override(s, reason="Idle"))),
    dict(id="TC_M2_18", module=M2, technique="BVA (min)", scenario="Reason of 5 characters",
         data="reason='Empty'", expected="200: Command 1 queued: switch fan OFF in LAB-1.",
         run=with_server(lambda s: override(s, reason="Empty"))),
    dict(id="TC_M2_19", module=M2, technique="BVA (max)", scenario="Reason of 100 characters",
         data="reason = 'R' x 100", expected="200: Command 1 queued: switch fan OFF in LAB-1.",
         run=with_server(lambda s: override(s, reason=REASON_100))),
    dict(id="TC_M2_20", module=M2, technique="BVA (max + 1)", scenario="Reason of 101 characters",
         data="reason = 'R' x 101", expected="400: Reason must be 5 to 100 characters.",
         run=with_server(lambda s: override(s, reason=REASON_101))),
    dict(id="TC_M2_21", module=M2, technique="Functional", scenario="ESP32 marks a command as done",
         data="POST /api/commands/1/done", expected="200: status=DONE", run=with_server(m2_command_done)),
    dict(id="TC_M2_22", module=M2, technique="EP (invalid)", scenario="Command marked done twice",
         data="POST /api/commands/1/done twice", expected="409: Command 1 is already DONE.",
         run=with_server(m2_command_done_twice)),
    dict(id="TC_M2_23", module=M2, technique="Functional", scenario="Save valid detection settings",
         data="vacancy_frames=8, wait_seconds=90, delta_t_threshold=0.8", expected="200: Settings saved.",
         run=with_server(lambda s: api_result(*s.call("PUT", "/api/settings", {
             "vacancy_frames": 8, "wait_seconds": 90, "delta_t_threshold": 0.8})))),
    dict(id="TC_M2_24", module=M2, technique="Functional (database)", scenario="Settings kept after server restart",
         data="save 8 / 90 / 0.8, restart server on the same database, GET /api/settings",
         expected="vacancy_frames=8, wait_seconds=90, delta_t_threshold=0.8", run=with_server(m2_settings_persist)),

    dict(id="TC_INT_01", module=INT, technique="Integration", scenario="Engine alerts are stored and listed",
         data="2 occupied frames, 5 vacant frames with 2 fans + 6 lights ON, drop 1.0 deg C after 60 s",
         expected="AC_ON_VACANT, FAN_ON_VACANT, LIGHT_ON_VACANT", run=with_server(int_alerts_stored)),
    dict(id="TC_INT_02", module=INT, technique="Integration", scenario="Room status combines engine and database",
         data="same readings as TC_INT_01; GET /api/rooms/LAB-1",
         expected="state=VACANT, open_alerts=3, ac_inferred_on=True", run=with_server(int_room_status)),
    dict(id="TC_INT_03", module=INT, technique="Integration", scenario="Acknowledging an alert updates the room",
         data="TC_INT_01 readings, acknowledge alert 1",
         expected="open_alerts=2, alert 1 status=ACKNOWLEDGED", run=with_server(int_ack_updates_count)),
    dict(id="TC_INT_04", module=INT, technique="Integration", scenario="Override reaches the ESP32 and stops alerts",
         data="vacant with 2 fans ON; send fan OFF; ESP32 executes; 3 more frames with fans_on=0",
         expected="pending=1, command status=DONE, FAN_ON_VACANT alerts=1", run=with_server(int_override_loop)),
    dict(id="TC_INT_05", module=INT, technique="Integration", scenario="New settings apply to the running engine",
         data="vacancy_frames=3; 2 occupied + 3 empty frames", expected="state=CHECKING_AC",
         run=with_server(int_settings_applied)),
    dict(id="TC_INT_06", module=INT, technique="Integration (database)", scenario="Every reading is stored",
         data="7 readings for LAB-1", expected="readings stored=7", run=with_server(int_readings_stored)),
    dict(id="TC_INT_07", module=INT, technique="Integration (end to end)", scenario="Simulator scenario ac_left_on",
         data="simulator: people leave at 10 s, 2 fans + 6 lights + AC left on, 80 s",
         expected="AC_ON_VACANT, FAN_ON_VACANT, LIGHT_ON_VACANT", run=with_server(int_simulator)),
]
