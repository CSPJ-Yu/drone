import math
import os
import socket
import time

from pymavlink import mavutil


DEVICE = "/dev/ttyACM0"
BAUD_RATE = 115200
PC_IP = "192.168.1.5"
PC_PORT = 14550


def fmt(value, unit=""):
    return "N/A" if value is None else f"{value}{unit}"


def main():
    master = mavutil.mavlink_connection(DEVICE, baud=BAUD_RATE)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = {"roll": None, "pitch": None, "yaw": None, "lat": None,
            "lon": None, "alt": None, "relative_alt": None,
            "satellites": None, "gps_fix": None, "voltage": None,
            "battery_remaining": None, "armed": False, "mode": "UNKNOWN"}
    last_heartbeat = 0.0
    last_draw = 0.0
    sent = 0

    print(f"Connecting to Pixhawk: {DEVICE}")
    print(f"Forwarding MAVLink to PC: {PC_IP}:{PC_PORT}")
    master.wait_heartbeat(timeout=30)
    print("Pixhawk connected!")

    for msg_id, interval_us in {30: 100000, 33: 500000, 24: 1000000,
                                1: 1000000, 0: 1000000}.items():
        master.mav.command_long_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
            msg_id, interval_us, 0, 0, 0, 0, 0)

    try:
        while True:
            msg = master.recv_match(blocking=True, timeout=0.1)
            now = time.monotonic()
            if msg is not None and msg.get_type() != "BAD_DATA":
                udp.sendto(bytes(msg.get_msgbuf()), (PC_IP, PC_PORT))
                sent += 1
                kind = msg.get_type()
                if kind == "HEARTBEAT":
                    last_heartbeat = now
                    data["mode"] = mavutil.mode_string_v10(msg)
                    data["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                elif kind == "ATTITUDE":
                    data["roll"] = round(math.degrees(msg.roll), 2)
                    data["pitch"] = round(math.degrees(msg.pitch), 2)
                    data["yaw"] = round(math.degrees(msg.yaw) % 360, 2)
                elif kind == "GPS_RAW_INT":
                    data["satellites"] = None if msg.satellites_visible == 255 else msg.satellites_visible
                    data["gps_fix"] = msg.fix_type
                elif kind == "GLOBAL_POSITION_INT":
                    data["lat"] = round(msg.lat / 1e7, 7)
                    data["lon"] = round(msg.lon / 1e7, 7)
                    data["alt"] = round(msg.alt / 1000, 2)
                    data["relative_alt"] = round(msg.relative_alt / 1000, 2)
                elif kind == "SYS_STATUS":
                    data["voltage"] = None if msg.voltage_battery == 65535 else round(msg.voltage_battery / 1000, 2)
                    data["battery_remaining"] = None if msg.battery_remaining == -1 else msg.battery_remaining

            if now - last_draw < 0.5:
                continue
            last_draw = now
            os.system("clear")
            connected = last_heartbeat and now - last_heartbeat < 3
            print("=== PIXHAWK TELEMETRY + UDP FORWARD ===")
            print(f"Pixhawk    : {'ONLINE' if connected else 'SIGNAL LOST'}")
            print(f"PC target  : {PC_IP}:{PC_PORT}")
            print(f"UDP sent   : {sent} messages")
            print(f"Mode       : {data['mode']}")
            print(f"Armed      : {'YES' if data['armed'] else 'NO'}")
            print(f"Roll/Pitch/Yaw: {fmt(data['roll'],' deg')} / {fmt(data['pitch'],' deg')} / {fmt(data['yaw'],' deg')}")
            print(f"GPS fix/sat: {fmt(data['gps_fix'])} / {fmt(data['satellites'])}")
            print(f"Lat/Lon    : {fmt(data['lat'])} / {fmt(data['lon'])}")
            print(f"Altitude   : {fmt(data['alt'],' m')} (relative {fmt(data['relative_alt'],' m')})")
            print(f"Battery    : {fmt(data['voltage'],' V')} / {fmt(data['battery_remaining'],' %')}")
            print("Ctrl+C to exit")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        udp.close()
        master.close()


if __name__ == "__main__":
    main()
