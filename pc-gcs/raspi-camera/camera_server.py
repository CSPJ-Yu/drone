import argparse
import threading
import time

import cv2
from flask import Flask, Response, jsonify


class CameraSource:
    def __init__(self, width: int, height: int, fps: int, usb_device: int) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.frame = None
        self.condition = threading.Condition()
        self.backend = ""
        self.camera = self._open_camera(usb_device)

    def _open_camera(self, usb_device: int):
        try:
            from picamera2 import Picamera2

            camera = Picamera2()
            config = camera.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={"FrameRate": self.fps},
            )
            camera.configure(config)
            camera.start()
            self.backend = "Pi Camera (CSI)"
            return camera
        except (ImportError, RuntimeError):
            camera = cv2.VideoCapture(usb_device)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            camera.set(cv2.CAP_PROP_FPS, self.fps)
            if not camera.isOpened():
                raise RuntimeError("Pi CameraまたはUSBカメラを開けません")
            self.backend = f"USB Camera {usb_device}"
            return camera

    def start(self) -> None:
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _capture_loop(self) -> None:
        interval = 1.0 / self.fps
        while True:
            started = time.monotonic()
            if self.backend.startswith("Pi Camera"):
                image = self.camera.capture_array("main")
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                success = True
            else:
                success, image = self.camera.read()
            if success:
                encoded, jpeg = cv2.imencode(
                    ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80]
                )
                if encoded:
                    with self.condition:
                        self.frame = jpeg.tobytes()
                        self.condition.notify_all()
            delay = interval - (time.monotonic() - started)
            if delay > 0:
                time.sleep(delay)

    def frames(self):
        while True:
            with self.condition:
                self.condition.wait()
                frame = self.frame
            if frame is not None:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"


def create_app(camera: CameraSource) -> Flask:
    app = Flask(__name__)

    @app.get("/video")
    def video():
        return Response(
            camera.frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/status")
    def status():
        return jsonify(online=True, camera=camera.backend)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Raspberry Pi camera MJPEG server")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--usb-device", type=int, default=0)
    args = parser.parse_args()

    camera = CameraSource(args.width, args.height, args.fps, args.usb_device)
    camera.start()
    print(f"Camera: {camera.backend}")
    print(f"Stream: http://<Raspberry-Pi-IP>:{args.port}/video")
    create_app(camera).run(host="0.0.0.0", port=args.port, threaded=True)


if __name__ == "__main__":
    main()
