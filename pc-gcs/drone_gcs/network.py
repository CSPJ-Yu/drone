import socket


def get_local_ipv4() -> str:
    """Return the IPv4 address used for the local network route."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        try:
            addresses = socket.gethostbyname_ex(socket.gethostname())[2]
            return next(ip for ip in addresses if not ip.startswith("127."))
        except (OSError, StopIteration):
            return "取得できません"
    finally:
        probe.close()


def gps_fix_label(fix_type: int) -> str:
    labels = {
        0: "NO GPS",
        1: "NO FIX",
        2: "2D FIX",
        3: "3D FIX",
        4: "DGPS",
        5: "RTK FLOAT",
        6: "RTK FIXED",
        7: "STATIC",
        8: "PPP",
    }
    return labels.get(fix_type, f"FIX {fix_type}")
