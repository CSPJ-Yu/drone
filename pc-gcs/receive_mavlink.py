from pymavlink import mavutil
import math

print("Waiting for Pixhawk MAVLink on UDP 14550...")

master = mavutil.mavlink_connection("udpin:0.0.0.0:14550")

master.wait_heartbeat()

print("Pixhawk connected!")
print("System ID:", master.target_system)
print("Component ID:", master.target_component)

while True:
    msg = master.recv_match(type="ATTITUDE", blocking=True)

    roll = math.degrees(msg.roll)
    pitch = math.degrees(msg.pitch)
    yaw = math.degrees(msg.yaw)

    print(
        f"\rRoll: {roll:7.2f} deg | "
        f"Pitch: {pitch:7.2f} deg | "
        f"Yaw: {yaw:7.2f} deg",
        end="",
        flush=True
    )