"""Module 1 test cases - Vacancy and AC-State Detection Engine (unit level).

Expected results are taken from the functional requirements (docs/requirements.md), not from the code.
Default settings for these cases: vacancy confirmed after 5 empty frames, AC check after 60 s,
Delta T threshold 0.5 deg C, unless a case says otherwise.
"""
from app.engine import Settings

from .helpers import check_frame, check_settings, describe, frame, run_frames

MODULE = "M1 Detection Engine"
S = Settings(vacancy_frames=5, wait_seconds=60, delta_t_threshold=0.5)
VALID = frame(100, people=3, fans=2, lights=4, temps=(24.5, 25.0, 24.8, 25.2))
SETTINGS_OK = {"vacancy_frames": 10, "wait_seconds": 120, "delta_t_threshold": 0.5}


def with_(base, **changes):
    d = dict(base)
    d.update(changes)
    return d


def occupied_then_empty(empty, start_temps=(25.0,) * 4, fans=0, lights=0):
    """Two occupied frames followed by `empty` vacant frames, one per second, constant temperatures."""
    frames = [frame(1, people=4, fans=4, lights=6, temps=start_temps), frame(2, people=4, fans=4, lights=6, temps=start_temps)]
    frames += [frame(3 + i, fans=fans, lights=lights, temps=start_temps) for i in range(empty)]
    return frames


def ac_check(final_temps, seconds_after_start=60, start=(25.0,) * 4):
    """Vacancy is confirmed at t=7 (5th empty frame); a last frame is sent `seconds_after_start` later."""
    frames = occupied_then_empty(5, start)
    frames.append(frame(7 + seconds_after_start, temps=final_temps))
    monitor, alerts = run_frames(frames, S)
    st = monitor.status()
    return "state=%s, ac_inferred_on=%s, alerts=[%s]" % (st["state"], st["ac_inferred_on"], ", ".join(alerts))


def sequence(frames, settings=S):
    return describe(*run_frames(frames, settings))


CASES = [
    # ----- frame validation (Validation testing, EP, BVA) -----
    dict(id="TC_M1_01", technique="Validation / EP (valid)", scenario="Valid frame from camera and sensors",
         data="people=3, fans_on=2, lights_on=4, temps=[24.5, 25.0, 24.8, 25.2]",
         expected="accepted", run=lambda: check_frame(VALID)),
    dict(id="TC_M1_02", technique="Validation / EP (invalid)", scenario="Only 3 region temperatures sent",
         data="temps=[24.5, 25.0, 24.8]",
         expected="temps must list exactly 4 region temperatures.",
         run=lambda: check_frame(with_(VALID, temps=[24.5, 25.0, 24.8]))),
    dict(id="TC_M1_03", technique="BVA (max)", scenario="Region temperature at DHT11 upper limit",
         data="temps=[24.5, 50.0, 24.8, 25.2]", expected="accepted",
         run=lambda: check_frame(with_(VALID, temps=[24.5, 50.0, 24.8, 25.2]))),
    dict(id="TC_M1_04", technique="BVA (max + 0.1)", scenario="Region temperature above DHT11 range",
         data="temps=[24.5, 50.1, 24.8, 25.2]",
         expected="temperature of region 2 must be between 0 and 50 deg C.",
         run=lambda: check_frame(with_(VALID, temps=[24.5, 50.1, 24.8, 25.2]))),
    dict(id="TC_M1_05", technique="BVA (min)", scenario="Region temperature at DHT11 lower limit",
         data="temps=[0.0, 25.0, 24.8, 25.2]", expected="accepted",
         run=lambda: check_frame(with_(VALID, temps=[0.0, 25.0, 24.8, 25.2]))),
    dict(id="TC_M1_06", technique="BVA (min - 0.1)", scenario="Region temperature below DHT11 range",
         data="temps=[-0.1, 25.0, 24.8, 25.2]",
         expected="temperature of region 1 must be between 0 and 50 deg C.",
         run=lambda: check_frame(with_(VALID, temps=[-0.1, 25.0, 24.8, 25.2]))),
    dict(id="TC_M1_07", technique="EP (invalid)", scenario="Negative people count",
         data="people=-1", expected="people must be between 0 and 50.",
         run=lambda: check_frame(with_(VALID, people=-1))),
    dict(id="TC_M1_08", technique="EP (invalid)", scenario="People count sent as text",
         data='people="3"', expected="people must be a whole number.",
         run=lambda: check_frame(with_(VALID, people="3"))),
    dict(id="TC_M1_09", technique="EP (invalid)", scenario="Fractional fan count",
         data="fans_on=1.5", expected="fans_on must be a whole number.",
         run=lambda: check_frame(with_(VALID, fans_on=1.5))),
    dict(id="TC_M1_10", technique="Validation", scenario="Frame with the same timestamp as the previous frame",
         data="frames at t=10 and t=10", expected="timestamp must be later than the previous frame.",
         run=lambda: _same_timestamp()),

    # ----- vacancy confirmation (Unit, BVA on vacancy_frames = 5) -----
    dict(id="TC_M1_11", technique="BVA (frames - 1)", scenario="4 consecutive empty frames",
         data="vacancy_frames=5; 2 occupied + 4 empty frames", expected="state=OCCUPIED, alerts=[]",
         run=lambda: sequence(occupied_then_empty(4))),
    dict(id="TC_M1_12", technique="BVA (frames)", scenario="5 consecutive empty frames confirm vacancy",
         data="vacancy_frames=5; 2 occupied + 5 empty frames", expected="state=CHECKING_AC, alerts=[]",
         run=lambda: sequence(occupied_then_empty(5))),
    dict(id="TC_M1_13", technique="Unit (path)", scenario="Person re-enters after 4 empty frames",
         data="4 empty, 1 frame with people=1, 4 empty", expected="state=OCCUPIED, alerts=[]",
         run=lambda: sequence(occupied_then_empty(4) + [frame(7, people=1)] + [frame(8 + i) for i in range(4)])),

    # ----- appliance wastage alerts (Functional, EP) -----
    dict(id="TC_M1_14", technique="Functional / EP", scenario="Fans left ON after everyone leaves",
         data="5 empty frames + 5 more with fans_on=2", expected="state=CHECKING_AC, alerts=[FAN_ON_VACANT]",
         run=lambda: sequence(occupied_then_empty(10, fans=2))),
    dict(id="TC_M1_15", technique="Functional / EP", scenario="Lights left ON after everyone leaves",
         data="10 empty frames with lights_on=6", expected="state=CHECKING_AC, alerts=[LIGHT_ON_VACANT]",
         run=lambda: sequence(occupied_then_empty(10, lights=6))),
    dict(id="TC_M1_16", technique="Functional / EP", scenario="Fans and lights switched off when leaving",
         data="10 empty frames, fans_on=0, lights_on=0", expected="state=CHECKING_AC, alerts=[]",
         run=lambda: sequence(occupied_then_empty(10))),
    dict(id="TC_M1_17", technique="EP (occupied)", scenario="Fans and lights ON while room is occupied",
         data="10 frames with people=4, fans_on=4, lights_on=6", expected="state=OCCUPIED, alerts=[]",
         run=lambda: sequence([frame(1 + i, people=4, fans=4, lights=6) for i in range(10)])),
    dict(id="TC_M1_18", technique="Functional", scenario="Fan switched OFF and ON again during vacancy",
         data="vacant: fans_on 2, 2, 0, 2", expected="state=CHECKING_AC, alerts=[FAN_ON_VACANT, FAN_ON_VACANT]",
         run=lambda: sequence(occupied_then_empty(5, fans=2) + [frame(8, fans=2), frame(9), frame(10, fans=2)])),

    # ----- AC-state inference (Functional, BVA on threshold 0.5 deg C and wait 60 s) -----
    dict(id="TC_M1_19", technique="BVA (threshold)", scenario="Mean temperature drop exactly 0.5 deg C",
         data="start 25.0 in all regions, after 60 s 24.5 in all regions",
         expected="state=VACANT, ac_inferred_on=True, alerts=[AC_ON_VACANT]",
         run=lambda: ac_check([24.5] * 4)),
    dict(id="TC_M1_20", technique="BVA (threshold - 0.01)", scenario="Mean temperature drop 0.49 deg C",
         data="start 25.0, after 60 s 24.51 in all regions",
         expected="state=VACANT, ac_inferred_on=False, alerts=[]",
         run=lambda: ac_check([24.51] * 4)),
    dict(id="TC_M1_21", technique="BVA (threshold - 0.001)", scenario="Mean temperature drop 0.499 deg C",
         data="start 25.0, after 60 s regions 24.501, 24.501, 24.501, 24.501",
         expected="state=VACANT, ac_inferred_on=False, alerts=[]",
         run=lambda: ac_check([24.501] * 4)),
    dict(id="TC_M1_22", technique="Functional", scenario="Different drop in each region (mean above threshold)",
         data="start 25.0; after 60 s 24.0, 24.8, 24.2, 25.0 (mean drop 0.5)",
         expected="state=VACANT, ac_inferred_on=True, alerts=[AC_ON_VACANT]",
         run=lambda: ac_check([24.0, 24.8, 24.2, 25.0])),
    dict(id="TC_M1_23", technique="EP (AC off)", scenario="Room warms up after vacancy (AC off)",
         data="start 25.0, after 60 s 25.3 in all regions",
         expected="state=VACANT, ac_inferred_on=False, alerts=[]",
         run=lambda: ac_check([25.3] * 4)),
    dict(id="TC_M1_24", technique="BVA (wait - 1 s)", scenario="Final reading 59 s after vacancy confirmed",
         data="drop 1.0 deg C at 59 s", expected="state=CHECKING_AC, ac_inferred_on=None, alerts=[]",
         run=lambda: ac_check([24.0] * 4, seconds_after_start=59)),
    dict(id="TC_M1_25", technique="BVA (wait)", scenario="Final reading exactly 60 s after vacancy confirmed",
         data="drop 1.0 deg C at 60 s", expected="state=VACANT, ac_inferred_on=True, alerts=[AC_ON_VACANT]",
         run=lambda: ac_check([24.0] * 4, seconds_after_start=60)),
    dict(id="TC_M1_26", technique="Unit (path)", scenario="Person enters during the AC check",
         data="vacancy at t=7, people=2 at t=30, empty again at t=67 with drop 1.0",
         expected="state=OCCUPIED, ac_inferred_on=None, alerts=[]",
         run=lambda: _enter_during_check()),

    # ----- settings validation (Validation, BVA) -----
    dict(id="TC_M1_27", technique="BVA (min - 1)", scenario="vacancy_frames = 0",
         data="vacancy_frames=0, wait_seconds=120, delta_t_threshold=0.5",
         expected="vacancy_frames must be between 1 and 300.",
         run=lambda: check_settings(with_(SETTINGS_OK, vacancy_frames=0))),
    dict(id="TC_M1_28", technique="BVA (min / max)", scenario="vacancy_frames = 1 and 300",
         data="vacancy_frames=1, then 300", expected="accepted / accepted",
         run=lambda: check_settings(with_(SETTINGS_OK, vacancy_frames=1)) + " / "
         + check_settings(with_(SETTINGS_OK, vacancy_frames=300))),
    dict(id="TC_M1_29", technique="BVA (max + 1)", scenario="vacancy_frames = 301",
         data="vacancy_frames=301", expected="vacancy_frames must be between 1 and 300.",
         run=lambda: check_settings(with_(SETTINGS_OK, vacancy_frames=301))),
    dict(id="TC_M1_30", technique="BVA", scenario="wait_seconds = 29 and 601",
         data="wait_seconds=29, then 601",
         expected="wait_seconds must be between 30 and 600. / wait_seconds must be between 30 and 600.",
         run=lambda: check_settings(with_(SETTINGS_OK, wait_seconds=29)) + " / "
         + check_settings(with_(SETTINGS_OK, wait_seconds=601))),
    dict(id="TC_M1_31", technique="BVA", scenario="delta_t_threshold = 0.09 and 5.1",
         data="delta_t_threshold=0.09, then 5.1",
         expected="delta_t_threshold must be between 0.1 and 5.0. / delta_t_threshold must be between 0.1 and 5.0.",
         run=lambda: check_settings(with_(SETTINGS_OK, delta_t_threshold=0.09)) + " / "
         + check_settings(with_(SETTINGS_OK, delta_t_threshold=5.1))),
    dict(id="TC_M1_32", technique="EP (invalid)", scenario="Non-numeric and fractional settings",
         data='delta_t_threshold="abc"; vacancy_frames=10.5',
         expected="delta_t_threshold must be a number. / vacancy_frames must be a whole number.",
         run=lambda: check_settings(with_(SETTINGS_OK, delta_t_threshold="abc")) + " / "
         + check_settings(with_(SETTINGS_OK, vacancy_frames=10.5))),
]


def _same_timestamp():
    from app.engine import ValidationError
    try:
        run_frames([frame(10), frame(10)], S)
        return "accepted"
    except ValidationError as e:
        return str(e)


def _enter_during_check():
    frames = occupied_then_empty(5) + [frame(30, people=2), frame(67, temps=[24.0] * 4)]
    monitor, alerts = run_frames(frames, S)
    st = monitor.status()
    return "state=%s, ac_inferred_on=%s, alerts=[%s]" % (st["state"], st["ac_inferred_on"], ", ".join(alerts))


for c in CASES:
    c["module"] = MODULE
