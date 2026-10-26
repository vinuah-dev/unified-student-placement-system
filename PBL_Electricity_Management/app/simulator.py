"""Simulated classroom node: stands in for the CCTV + YOLOv8 detector, the four DHT11 sensors and the
ESP32 relay controller, which are not available for this prototype.

Each simulated second it posts one frame to /api/readings, and it executes pending relay commands from
/api/commands (switching the simulated fans/lights), exactly as the ESP32 would.

    python -m app.simulator --room LAB-1 --scenario ac_left_on --speed 20

Scenarios
    ac_left_on     people leave at t=10 s; 2 fans, 6 lights and the AC stay on (room keeps cooling)
    all_off        people leave at t=10 s and switch everything off (room warms up slowly)
    occupied       people stay in the room for the whole run
"""
import argparse
import json
import time
import urllib.request

SCENARIOS = {
    # people before/after leaving, fans and lights left on, temperature change per second per region
    "ac_left_on": {"leave_at": 10, "people": 12, "fans": 2, "lights": 6, "drift": [-0.010, -0.008, -0.012, -0.009]},
    "all_off": {"leave_at": 10, "people": 12, "fans": 0, "lights": 0, "drift": [0.004, 0.003, 0.005, 0.004]},
    "occupied": {"leave_at": None, "people": 18, "fans": 4, "lights": 6, "drift": [0.0, 0.0, 0.0, 0.0]},
}
START_TEMPS = [24.6, 25.1, 24.2, 25.4]


def call(base, method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())


def run(base, room, scenario, seconds, speed):
    sc = SCENARIOS[scenario]
    fans, lights = 4, 6                                       # everything is on while the class is running
    temps = list(START_TEMPS)
    # Frame timestamps must keep increasing for the room, also across repeated simulator runs.
    last = call(base, "GET", "/api/rooms/" + room)["status"]["last_timestamp"]
    start = max(time.time(), (last or 0) + 1)
    for t in range(seconds):
        leaving = sc["leave_at"] is not None and t >= sc["leave_at"]
        if sc["leave_at"] is not None and t == sc["leave_at"]:
            fans, lights = sc["fans"], sc["lights"]          # what the last person left switched on

        # ESP32: apply pending manual-override commands from the dashboard
        for cmd in reversed(call(base, "GET", "/api/commands?status=PENDING&room=" + room)):
            on = cmd["action"] == "ON"
            if cmd["appliance"] == "fan":
                fans = 4 if on else 0
            else:
                lights = 6 if on else 0
            call(base, "POST", "/api/commands/%d/done" % cmd["id"], {})
            print("  ESP32 executed command #%d: %s %s" % (cmd["id"], cmd["appliance"], cmd["action"]))

        if leaving:
            temps = [round(x + d, 3) for x, d in zip(temps, sc["drift"])]
        frame = {"room_id": room, "timestamp": round(start + t, 1), "people": 0 if leaving else sc["people"],
                 "fans_on": fans, "lights_on": lights, "temps": [round(x, 2) for x in temps]}
        result = call(base, "POST", "/api/readings", frame)
        for a in result["alerts"]:
            print("t=%3ds  ALERT %s: %s" % (t, a["type"], a["message"]))
        if t % 15 == 0:
            print("t=%3ds  state=%s people=%d fans=%d lights=%d temps=%s"
                  % (t, result["state"], frame["people"], fans, lights, frame["temps"]))
        time.sleep(1.0 / speed)


def main():
    parser = argparse.ArgumentParser(description="Simulated camera + DHT11 + ESP32 node")
    parser.add_argument("--server", default="http://127.0.0.1:8090")
    parser.add_argument("--room", default="LAB-1")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="ac_left_on")
    parser.add_argument("--seconds", type=int, default=180, help="simulated seconds to run")
    parser.add_argument("--speed", type=float, default=10, help="simulated seconds per real second")
    args = parser.parse_args()
    run(args.server, args.room, args.scenario, args.seconds, args.speed)


if __name__ == "__main__":
    main()
