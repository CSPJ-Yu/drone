"""PC monotonic-time association; NOT capture-time synchronization."""
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import Lock


@dataclass(frozen=True)
class FrameContext:
    sequence: int
    available_at: float
    utc: str
    telemetry: object = None


@dataclass(frozen=True)
class VideoFrame:
    image: object
    context: FrameContext


class TelemetryHistory:
    def __init__(self):
        self.lock = Lock()
        self.states = deque(maxlen=4096)

    def add(self, state):
        with self.lock:
            self.states.append(replace(state))
            while self.states and state.received_at - self.states[0].received_at > 15:
                self.states.popleft()

    def match(self, timestamp):
        # Use only data available at/before this frame, never future telemetry.
        with self.lock:
            for state in reversed(self.states):
                if state.received_at <= timestamp:
                    return replace(state)
        return None

    def frame(self, image, sequence, timestamp):
        return VideoFrame(image, FrameContext(
            sequence, timestamp, datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            self.match(timestamp)))


def describe(context):
    text = f'Frame {context.sequence} | PC available UTC {context.utc}'
    s = context.telemetry
    if s is None:
        return text + '\nMAVLink: UNMATCHED (no earlier data)'
    t = context.available_at
    def fresh(stamp, limit):
        return stamp is not None and 0 <= t - stamp <= limit
    def age(stamp):
        return 'N/A' if stamp is None else f'{(t-stamp)*1000:.0f} ms'
    flight = (f'{s.mode} / Armed {s.armed}' if fresh(s.heartbeat_at, 3) else 'STALE / N/A')
    attitude = (f'R {s.roll:+.1f} P {s.pitch:+.1f} Y {s.yaw:.1f} deg'
                if fresh(s.attitude_at, 1) else 'STALE / N/A')
    position = 'NO FIX / STALE / N/A'
    if (fresh(s.position_at, 2) and fresh(s.gps_at, 2) and s.gps_fix >= 3
            and s.latitude is not None and s.longitude is not None):
        position = f'{s.latitude:.7f}, {s.longitude:.7f} | MSL {s.altitude:.1f} m'
    return (text + f'\nFlight: {flight} | HB age {age(s.heartbeat_at)}'
            + f'\nAttitude: {attitude} | age {age(s.attitude_at)}'
            + f'\nGPS: {position} | position age {age(s.position_at)}'
            + '\nPC availability association only; capture delay not corrected')
