import math
import time
from dataclasses import dataclass

from pymavlink import mavutil
from PySide6.QtCore import QThread, Signal


@dataclass
class TelemetryState:
    mode: str = "UNKNOWN"
    armed: bool = False
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    satellites: int | None = None
    gps_fix: int = 0
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    received_at: float = 0.0
    heartbeat_at: float | None = None
    attitude_at: float | None = None
    gps_at: float | None = None
    position_at: float | None = None


class TelemetryWorker(QThread):
    telemetry = Signal(object)
    connection_changed = Signal(bool, str)

    def __init__(self, endpoint: str = "udpin:0.0.0.0:14550", history=None) -> None:
        super().__init__()
        self.endpoint = endpoint
        self.history = history
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.requestInterruption()

    def run(self) -> None:
        state = TelemetryState()
        connected = False
        last_heartbeat = 0.0

        try:
            master = mavutil.mavlink_connection(self.endpoint)
            self.connection_changed.emit(False, "WAITING FOR MAVLINK")

            while self._running and not self.isInterruptionRequested():
                message = master.recv_match(blocking=True, timeout=0.25)
                now = time.monotonic()

                if message is not None:
                    message_type = message.get_type()
                    if message_type == "HEARTBEAT":
                        state.heartbeat_at = now
                        last_heartbeat = now
                        state.mode = mavutil.mode_string_v10(message)
                        state.armed = bool(
                            message.base_mode
                            & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                        )
                    elif message_type == "ATTITUDE":
                        state.attitude_at = now
                        state.roll = math.degrees(message.roll)
                        state.pitch = math.degrees(message.pitch)
                        state.yaw = math.degrees(message.yaw) % 360.0
                    elif message_type == "GPS_RAW_INT":
                        state.gps_at = now
                        state.satellites = (
                            None
                            if message.satellites_visible == 255
                            else int(message.satellites_visible)
                        )
                        state.gps_fix = int(message.fix_type)
                        if message.fix_type >= 3:
                            state.position_at = now
                            state.latitude = message.lat / 10_000_000.0
                            state.longitude = message.lon / 10_000_000.0
                            state.altitude = message.alt / 1000.0
                    elif message_type == "GLOBAL_POSITION_INT":
                        if message.lat != 0 or message.lon != 0:
                            state.position_at = now
                            state.latitude = message.lat / 10_000_000.0
                            state.longitude = message.lon / 10_000_000.0
                            state.altitude = message.alt / 1000.0

                    if message_type in ('HEARTBEAT', 'ATTITUDE', 'GPS_RAW_INT', 'GLOBAL_POSITION_INT'):
                        state.received_at = now
                        snapshot = TelemetryState(**vars(state))
                        if self.history is not None:
                            self.history.add(snapshot)
                        self.telemetry.emit(snapshot)

                is_connected = last_heartbeat > 0 and now - last_heartbeat < 3.0
                if is_connected != connected:
                    connected = is_connected
                    label = "ONLINE" if connected else "SIGNAL LOST"
                    self.connection_changed.emit(connected, label)
        except Exception as exc:
            self.connection_changed.emit(False, f"ERROR: {exc}")
