import json

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView


MAP_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    html, body, #map { height: 100%; width: 100%; margin: 0; background: #08111f; }
    .leaflet-container { font-family: 'Segoe UI', sans-serif; }
    .position-box {
      padding: 8px 10px; color: #e9f0f8; background: rgba(7,16,29,.90);
      border: 1px solid #314761; border-radius: 6px; line-height: 1.45;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map', { zoomControl: true }).setView([35.6812, 139.7671], 5);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    const marker = L.circleMarker([35.6812, 139.7671], {
      radius: 9, color: '#ffffff', weight: 2, fillColor: '#2ce6a6', fillOpacity: 1
    });
    let hasPosition = false;
    function updateDronePosition(lat, lon, alt, satellites, fix) {
      const position = [lat, lon];
      marker.setLatLng(position);
      if (!map.hasLayer(marker)) marker.addTo(map);
      marker.bindPopup(
        '<b>DRONE</b><br>LAT ' + lat.toFixed(7) + '<br>LON ' + lon.toFixed(7) +
        '<br>ALT ' + alt.toFixed(1) + ' m<br>SAT ' + satellites + '<br>' + fix
      );
      if (!hasPosition) {
        map.setView(position, 17);
        hasPosition = true;
      } else {
        map.panTo(position, { animate: true, duration: 0.4 });
      }
    }
  </script>
</body>
</html>"""


class MapWidget(QWebEngineView):
    def __init__(self) -> None:
        super().__init__()
        self._ready = False
        self._pending_position = None
        self.loadFinished.connect(self._on_load_finished)
        self.setHtml(MAP_HTML, QUrl("https://localhost/"))

    def _on_load_finished(self, success: bool) -> None:
        self._ready = success
        if success and self._pending_position is not None:
            self.update_position(*self._pending_position)

    def update_position(
        self,
        latitude: float,
        longitude: float,
        altitude: float,
        satellites: int | None,
        fix: str,
    ) -> None:
        self._pending_position = (
            latitude,
            longitude,
            altitude,
            satellites,
            fix,
        )
        if not self._ready:
            return
        satellite_text = "N/A" if satellites is None else str(satellites)
        script = "updateDronePosition({lat}, {lon}, {alt}, {sat}, {fix});".format(
            lat=json.dumps(latitude),
            lon=json.dumps(longitude),
            alt=json.dumps(altitude),
            sat=json.dumps(satellite_text),
            fix=json.dumps(fix),
        )
        self.page().runJavaScript(script)
