import argparse
import shutil
import subprocess
import sys


def find_command(*names: str) -> str | None:
    for name in names:
        command = shutil.which(name)
        if command:
            return command
    return None


def stream_csi(args) -> int:
    camera_command = find_command("rpicam-vid", "libcamera-vid")
    if camera_command is None:
        return -1
    camera_args = [
        camera_command, "-t", "0", "--width", str(args.width),
        "--height", str(args.height), "--framerate", str(args.fps),
        "--bitrate", str(args.bitrate), "--codec", "libav",
        "--libav-format", "mpegts", "--nopreview",
        "-o", f"udp://{args.pc_ip}:{args.port}?pkt_size=1316",
    ]
    try:
        return subprocess.run(camera_args, check=False).returncode
    except KeyboardInterrupt:
        return 0


def stream_usb(args) -> int:
    command = [
        "ffmpeg", "-loglevel", "warning", "-f", "v4l2",
        "-framerate", str(args.fps), "-video_size", f"{args.width}x{args.height}",
        "-i", args.device, "-an", "-c:v", "libx264", "-preset", "ultrafast",
        "-tune", "zerolatency", "-b:v", str(args.bitrate), "-g", str(args.fps),
        "-f", "mpegts", f"udp://{args.pc_ip}:{args.port}?pkt_size=1316",
    ]
    try:
        return subprocess.run(command, check=False).returncode
    except KeyboardInterrupt:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Raspberry Pi camera over UDP")
    parser.add_argument("pc_ip", help="Windows GCS IPv4 address")
    parser.add_argument("--port", type=int, default=5600)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--bitrate", type=int, default=4_000_000)
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--usb", action="store_true", help="Force USB camera")
    args = parser.parse_args()
    print(f"Sending video to udp://{args.pc_ip}:{args.port}")
    if not args.usb:
        result = stream_csi(args)
        if result >= 0:
            return result
        print("CSI camera command not found; trying USB camera")
    if shutil.which("ffmpeg") is None:
        print("ffmpeg がありません: sudo apt install -y ffmpeg", file=sys.stderr)
        return 1
    return stream_usb(args)


if __name__ == "__main__":
    raise SystemExit(main())
