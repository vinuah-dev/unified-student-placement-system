"""Module 1: Vacancy and AC-state detection engine (edge decision engine).

Every frame from the classroom carries the YOLO detection counts (people, fans that are on, lights
that are on) and the temperatures of the four regions (one DHT11 sensor per region). The engine
confirms that the room is vacant over consecutive frames, raises an alert when a fan or light is left
on in a vacant room, and infers whether the AC is still running from the temperature drop (Delta T)
measured across the four regions after a waiting period.
"""
from dataclasses import dataclass

REGIONS = 4
TEMP_MIN, TEMP_MAX = 0.0, 50.0          # DHT11 measuring range in deg C
COUNT_MAX = 50                          # upper bound accepted for any detection count

OCCUPIED = "OCCUPIED"
CHECKING_AC = "CHECKING_AC"             # vacancy confirmed, waiting for the final temperatures
VACANT = "VACANT"                       # vacancy confirmed and AC check finished
NO_DATA = "NO_DATA"                     # reported until the room sends its first frame

FAN_ON_VACANT = "FAN_ON_VACANT"
LIGHT_ON_VACANT = "LIGHT_ON_VACANT"
AC_ON_VACANT = "AC_ON_VACANT"


class ValidationError(ValueError):
    """Raised when a frame or a setting is outside its allowed range."""


@dataclass
class Settings:
    vacancy_frames: int = 10            # consecutive empty frames needed to confirm vacancy
    wait_seconds: int = 120             # wait between the initial and final temperature readings
    delta_t_threshold: float = 0.5      # mean temperature drop (deg C) that means the AC is still on

    LIMITS = {"vacancy_frames": (1, 300), "wait_seconds": (30, 600), "delta_t_threshold": (0.1, 5.0)}

    @classmethod
    def from_dict(cls, data):
        """Builds validated settings; raises ValidationError naming the first bad field."""
        values = {}
        for name, (low, high) in cls.LIMITS.items():
            if name not in data:
                raise ValidationError("%s is required." % name)
            value = data[name]
            is_int_field = name != "delta_t_threshold"
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError("%s must be a number." % name)
            if is_int_field and value != int(value):
                raise ValidationError("%s must be a whole number." % name)
            if not low <= value <= high:
                raise ValidationError("%s must be between %s and %s." % (name, low, high))
            values[name] = int(value) if is_int_field else float(value)
        return cls(**values)

    def to_dict(self):
        return {"vacancy_frames": self.vacancy_frames, "wait_seconds": self.wait_seconds,
                "delta_t_threshold": self.delta_t_threshold}


@dataclass
class Frame:
    timestamp: float
    people: int
    fans_on: int
    lights_on: int
    temps: list

    @classmethod
    def from_dict(cls, data):
        """Validates one reading from the camera/sensor node."""
        ts = data.get("timestamp")
        if isinstance(ts, bool) or not isinstance(ts, (int, float)) or ts < 0:
            raise ValidationError("timestamp must be a non-negative number.")
        counts = {}
        for name in ("people", "fans_on", "lights_on"):
            value = data.get(name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError("%s must be a whole number." % name)
            if not 0 <= value <= COUNT_MAX:
                raise ValidationError("%s must be between 0 and %d." % (name, COUNT_MAX))
            counts[name] = value
        temps = data.get("temps")
        if not isinstance(temps, list) or len(temps) != REGIONS:
            raise ValidationError("temps must list exactly %d region temperatures." % REGIONS)
        for i, t in enumerate(temps):
            if isinstance(t, bool) or not isinstance(t, (int, float)):
                raise ValidationError("temperature of region %d must be a number." % (i + 1))
            if not TEMP_MIN <= t <= TEMP_MAX:
                raise ValidationError("temperature of region %d must be between 0 and 50 deg C." % (i + 1))
        return cls(float(ts), counts["people"], counts["fans_on"], counts["lights_on"], [float(t) for t in temps])


class RoomMonitor:
    """Tracks one room frame by frame and returns the alerts each frame produces."""

    def __init__(self, room_id, settings=None):
        self.room_id = room_id
        self.settings = settings or Settings()
        self.state = OCCUPIED
        self.empty_frames = 0
        self.last_timestamp = None
        self.initial_temps = None
        self.check_started = None
        self.fan_alerted = False
        self.light_alerted = False
        self.last_mean_drop = None
        self.ac_inferred_on = None
        self.last_frame = None

    def process(self, frame):
        if self.last_timestamp is not None and frame.timestamp <= self.last_timestamp:
            raise ValidationError("timestamp must be later than the previous frame.")
        self.last_timestamp = frame.timestamp
        self.last_frame = frame
        alerts = []

        if frame.people > 0:
            self._reset_to_occupied()
            return alerts

        self.empty_frames += 1
        if self.state == OCCUPIED and self.empty_frames >= self.settings.vacancy_frames:
            self.state = CHECKING_AC
            self.initial_temps = list(frame.temps)
            self.check_started = frame.timestamp

        if self.state == OCCUPIED:
            return alerts

        alerts += self._appliance_alerts(frame)

        if self.state == CHECKING_AC and frame.timestamp - self.check_started >= self.settings.wait_seconds:
            drops = [start - end for start, end in zip(self.initial_temps, frame.temps)]
            # Compare at full precision (6 decimals only removes float noise); rounding to 2 decimals
            # before comparing turned a 0.499 deg C drop into 0.50 and raised a false AC alert (BUG-02).
            mean_drop = round(sum(drops) / REGIONS, 6)
            self.last_mean_drop = round(mean_drop, 3)
            self.ac_inferred_on = mean_drop >= self.settings.delta_t_threshold
            self.state = VACANT
            if self.ac_inferred_on:
                alerts.append(self._alert(AC_ON_VACANT, frame.timestamp,
                                          "AC appears to be ON in vacant room %s (mean temperature drop %.2f deg C "
                                          "in %d s)." % (self.room_id, self.last_mean_drop, self.settings.wait_seconds),
                                          self.last_mean_drop))
        return alerts

    def _appliance_alerts(self, frame):
        alerts = []
        if frame.fans_on > 0 and not self.fan_alerted:
            alerts.append(self._alert(FAN_ON_VACANT, frame.timestamp,
                                      "%d fan(s) ON in vacant room %s." % (frame.fans_on, self.room_id), frame.fans_on))
        if frame.lights_on > 0 and not self.light_alerted:
            alerts.append(self._alert(LIGHT_ON_VACANT, frame.timestamp,
                                      "%d light(s) ON in vacant room %s." % (frame.lights_on, self.room_id),
                                      frame.lights_on))
        # An appliance switched off and on again during the same vacancy is reported again.
        self.fan_alerted = frame.fans_on > 0
        self.light_alerted = frame.lights_on > 0
        return alerts

    def _reset_to_occupied(self):
        self.state = OCCUPIED
        self.empty_frames = 0
        self.initial_temps = None
        self.check_started = None
        self.fan_alerted = False
        self.light_alerted = False

    def _alert(self, kind, timestamp, message, value):
        return {"room_id": self.room_id, "type": kind, "timestamp": timestamp, "message": message, "value": value}

    def status(self):
        f = self.last_frame
        return {
            "room_id": self.room_id,
            "state": self.state if f else NO_DATA,
            "empty_frames": self.empty_frames,
            "people": f.people if f else None,
            "fans_on": f.fans_on if f else None,
            "lights_on": f.lights_on if f else None,
            "temps": f.temps if f else None,
            "last_timestamp": self.last_timestamp,
            "ac_check_seconds_left": (max(0, round(self.settings.wait_seconds - (self.last_timestamp - self.check_started)))
                                      if self.state == CHECKING_AC else None),
            "mean_temp_drop": self.last_mean_drop,
            "ac_inferred_on": self.ac_inferred_on,
        }
