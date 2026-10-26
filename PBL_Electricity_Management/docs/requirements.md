# Smart Classroom Electricity Management – Requirements for the two PBL modules

Problem statement (from the Idea Lab project "Electricity Management through Computer Vision & Temperature
Sensing"): lights, fans and air conditioners stay on in classrooms and labs after people leave. The system
uses a CCTV camera with YOLOv8 (people, fans, lights), four DHT11 sensors (one per room region), an ESP32
relay controller and a web dashboard to detect vacancy, flag wasted energy and switch appliances.

Scope of this PBL prototype: the two software modules below. The camera + YOLOv8 detector, the DHT11
sensors and the ESP32 are replaced by a simulator (`app/simulator.py`) that sends the same data.

## Module 1 – Vacancy and AC-State Detection Engine (`app/engine.py`)

| ID | Requirement |
|----|-------------|
| FR-1.1 | Accept one frame at a time: timestamp (s), people count, fans ON count, lights ON count, and the temperatures of exactly 4 regions. |
| FR-1.2 | Counts must be whole numbers from 0 to 50; temperatures must be numbers from 0 to 50 °C (DHT11 range); the timestamp must be later than the previous frame of the room. Messages: `temps must list exactly 4 region temperatures.`, `temperature of region N must be between 0 and 50 deg C.`, `<field> must be a whole number.`, `<field> must be between 0 and 50.`, `timestamp must be later than the previous frame.` |
| FR-1.3 | The room is confirmed vacant when at least `vacancy_frames` consecutive frames have people = 0. Any frame with people > 0 resets the count and the room is OCCUPIED. |
| FR-1.4 | When vacancy is confirmed, the four temperatures are recorded and the room state is CHECKING_AC. |
| FR-1.5 | While the room is vacant, raise FAN_ON_VACANT when fans_on > 0 and LIGHT_ON_VACANT when lights_on > 0, once per occurrence; if the appliance is switched off and on again during the same vacancy, raise the alert again. |
| FR-1.6 | When at least `wait_seconds` have passed since vacancy was confirmed, compute the drop in each region (initial − final) and the mean drop. If the mean drop is greater than or equal to `delta_t_threshold`, the AC is inferred ON and AC_ON_VACANT is raised; otherwise the AC is inferred OFF. The state becomes VACANT. |
| FR-1.7 | If a person is detected during the AC check, the check is cancelled (no AC result) and the room is OCCUPIED. |
| FR-1.8 | Settings: `vacancy_frames` whole number 1–300, `wait_seconds` whole number 30–600, `delta_t_threshold` number 0.1–5.0. Messages: `<field> must be between <min> and <max>.`, `<field> must be a number.`, `<field> must be a whole number.` |

## Module 2 – Monitoring Dashboard and Control (`app/server.py`, `app/db.py`, `app/static/`)

| ID | Requirement |
|----|-------------|
| FR-2.1 | REST API `POST /api/readings` passes each reading to Module 1 and stores the reading and any alerts in the SQLite database. Unknown room: `404: Room <id> not found.`; missing room id: `400: room_id is required.`; body that is not JSON: `400: Request body must be valid JSON.`; frame errors from FR-1.2 are returned with status 400. |
| FR-2.2 | The dashboard shows, for the selected room: state badge, people / fans ON / lights ON, open alert count, AC check result (`AC likely ON (mean drop X °C)`, `AC OFF (mean drop X °C)`, or seconds left), last reading time, and a 2×2 heatmap of the four region temperatures. A room that has not sent any reading shows the badge `NO DATA`. |
| FR-2.3 | The dashboard lists open alerts (newest first) and lets an operator acknowledge one: an alert must be selected (`Please select an alert.`), operator name 3–40 letters, spaces or dots (`Operator name must be 3 to 40 characters (letters, spaces and dots only).`), remarks optional, max 200 characters (`Remarks cannot exceed 200 characters.`). Success: `Alert <id> acknowledged by <name>.` An alert can be acknowledged only once (`409: Alert <id> is already acknowledged.`); unknown alert: `404: Alert <id> not found.` |
| FR-2.4 | Manual override: appliance fan or light (`Appliance must be fan or light.`), action ON or OFF (`Action must be ON or OFF.`), operator name as FR-2.3, reason 5–100 characters (`Reason must be 5 to 100 characters.`). Success: the command is stored as PENDING and `Command <id> queued: switch <appliance> <action> in <room>.` is shown. |
| FR-2.5 | The ESP32 controller reads pending commands (`GET /api/commands?status=PENDING&room=<id>`) and marks each one done (`POST /api/commands/<id>/done`); a command can be completed only once (`409: Command <id> is already DONE.`). |
| FR-2.6 | Detection settings can be edited on the dashboard with the limits of FR-1.8; saved settings are stored in the database, apply immediately to the running engine and are kept after a restart. Success: `Settings saved.` |
| FR-2.7 | Validation messages shown on the dashboard use the field labels shown on the form (e.g. `Empty frames to confirm vacancy must be between 1 and 300.`, `Mean ΔT threshold must be a number.`). |
