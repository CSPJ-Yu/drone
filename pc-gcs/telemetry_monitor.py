from pymavlink import mavutil
import math
import os
import time

print("Waiting for MAVLink from Raspberry Pi...")

master = mavutil.mavlink_connection(
    "udpin:0.0.0.0:14550"
)

master.wait_heartbeat()

print("Pixhawk connected!")
time.sleep(1)

data = {
    "mode": "UNKNOWN",
    "armed": False,

    "roll": None,
    "pitch": None,
    "yaw": None,

    "lat": None,
    "lon": None,
    "alt": None,
    "relative_alt": None,

    "satellites": None,
    "gps_fix": None,

    "voltage": None,
    "battery": None,
}

last_draw = 0


def fmt(value, unit=""):
    if value is None:
        return "N/A"
    return f"{value}{unit}"


while True:

    msg = master.recv_match(blocking=True, timeout=1)

    if msg:
        msg_type = msg.get_type()

        # -------------------------
        # Heartbeat
        # -------------------------

        if msg_type == "HEARTBEAT":

            data["armed"] = bool(
                msg.base_mode
                & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            )

            data["mode"] = mavutil.mode_string_v10(msg)

        # -------------------------
        # Attitude
        # -------------------------

        elif msg_type == "ATTITUDE":

            data["roll"] = round(
                math.degrees(msg.roll), 2
            )

            data["pitch"] = round(
                math.degrees(msg.pitch), 2
            )

            data["yaw"] = round(
                math.degrees(msg.yaw), 2
            )

        # -------------------------
        # GPS
        # -------------------------

        elif msg_type == "GPS_RAW_INT":

            data["satellites"] = msg.satellites_visible
            data["gps_fix"] = msg.fix_type

        # -------------------------
        # Position
        # -------------------------

        elif msg_type == "GLOBAL_POSITION_INT":

            data["lat"] = round(
                msg.lat / 1e7, 7
            )

            data["lon"] = round(
                msg.lon / 1e7, 7
            )

            data["alt"] = round(
                msg.alt / 1000.0, 2
            )

            data["relative_alt"] = round(
                msg.relative_alt / 1000.0, 2
            )

        # -------------------------
        # Battery
        # -------------------------

        elif msg_type == "SYS_STATUS":

            if msg.voltage_battery != 65535:

                data["voltage"] = round(
                    msg.voltage_battery / 1000.0,
                    2
                )

            if msg.battery_remaining != -1:

                data["battery"] = (
                    msg.battery_remaining
                )

    # Update screen at 5 Hz
    now = time.time()

    if now - last_draw >= 0.2:

        last_draw = now

        os.system("cls")

        print("========================================")
        print("             DRONE GCS")
        print("========================================")
        print()

        print("[ CONNECTION ]")
        print("Pixhawk     : ONLINE")
        print("Raspberry Pi: ONLINE")
        print()

        print("[ FLIGHT ]")
        print(f"Mode        : {data['mode']}")
        print(
            f"Armed       : "
            f"{'YES' if data['armed'] else 'NO'}"
        )
        print()

        print("[ ATTITUDE ]")
        print(
            f"Roll        : "
            f"{fmt(data['roll'], ' deg')}"
        )
        print(
            f"Pitch       : "
            f"{fmt(data['pitch'], ' deg')}"
        )
        print(
            f"Yaw         : "
            f"{fmt(data['yaw'], ' deg')}"
        )
        print()

        print("[ GPS ]")
        print(
            f"Fix Type    : "
            f"{fmt(data['gps_fix'])}"
        )
        print(
            f"Satellites  : "
            f"{fmt(data['satellites'])}"
        )
        print(
            f"Latitude    : "
            f"{fmt(data['lat'])}"
        )
        print(
            f"Longitude   : "
            f"{fmt(data['lon'])}"
        )
        print()

        print("[ ALTITUDE ]")
        print(
            f"MSL Alt     : "
            f"{fmt(data['alt'], ' m')}"
        )
        print(
            f"Relative Alt: "
            f"{fmt(data['relative_alt'], ' m')}"
        )
        print()

        print("[ BATTERY ]")
        print(
            f"Voltage     : "
            f"{fmt(data['voltage'], ' V')}"
        )
        print(
            f"Remaining   : "
            f"{fmt(data['battery'], ' %')}"
        )

        print()
        print("Ctrl+C to exit")