# Drone GCS v0.1

## 映像・MAVLinkのPC時刻対応付け

CAMERAとYOLO下部に、元フレーム番号、PC取得UTC時刻、Mode/Armed、姿勢、GPS/MSL高度と各データの経過時間を表示します。
MAVLinkはメッセージ受信直後、映像はデコードされたフレームを取得した時点の `time.monotonic()` を用います。
フレーム時刻以前の最新MAVLinkスナップショットを紐づけ、YOLO推論完了後も同じスナップショットを保持します。
GPSは3D Fix以上かつ位置・Fix更新から2秒以内、姿勢は1秒以内、Heartbeatは3秒以内を有効とし、それ以外はN/A/STALEです。
各ageはフレーム取得時点でのデータの古さであり、映像遅延の実測値ではありません。UTCは表示用、対応付けは単調時計を使います。
撮影時刻同期、通信遅延の補正、補間、ログ保存はこの段階では行いません。右側のテレメトリ欄は引き続き最新の受信値です。

## YOLOタブ

CAMERAの隣のYOLOタブで、同じUDP映像をYOLO11sに通して物体名・信頼度・検出枠を表示します。
モデルは `models/yolo11s.pt`（入力サイズ416、信頼度0.35）。YOLOタブを表示中のみ推論し、PAUSE/RESUMEで一時停止できます。
未処理フレームは最新1枚だけ保持します。表示されるmsは推論・描画処理時間で、カメラからの総遅延ではありません。
CUDAが利用可能ならGPU、そうでなければCPUを自動使用します。GPU名はタブ上部に表示します。
NVIDIA用環境の再構築は `venv\Scripts\python.exe -m pip install -r requirements-gpu.txt` の後に通常のrequirementsをインストールしてください。

Pixhawk の MAVLink テレメトリを UDP 14550 で受信する Windows 用 GCS GUI です。
Mode、Armed、姿勢、GPS捕捉衛星数、GPS Fix、およびRaspberry Piの転送先に使うPCのIPv4アドレスを表示します。
`MAP` タブではGPSの緯度・経度・高度をOpenStreetMap上の機体マーカーとして表示します。地図タイルの読み込みにはインターネット接続が必要です。

## Raspberry Pi camera

### UDP video（推奨）

Raspberry PiでH.264映像をMPEG-TSに格納し、PCのUDP 5600へ送信します。

```bash
sudo apt update
sudo apt install -y ffmpeg
cd ~/raspi-camera
python3 udp_camera_stream.py PCのIPv4アドレス
```

USBカメラを明示する場合：

```bash
python3 udp_camera_stream.py PCのIPv4アドレス --usb --device /dev/video0
```

GCSの `CAMERA` タブはUDP 5600を自動で待ち受けます。ポートを変更した場合はRaspberry Piの `--port` とCAMERAタブのポートを一致させてください。

### HTTP MJPEG（予備）

Raspberry Piへ `raspi-camera` フォルダをコピーし、OSパッケージとPython依存関係を準備します。

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-flask
cd ~/raspi-camera
python3 camera_server.py
```

USBカメラの場合も同じコマンドで自動検出します。GCSの `CAMERA` タブに `http://Raspberry-PiのIP:5000/video` を入力して `CONNECT` を押します。Raspberry Piのホスト名が `goofy` なら初期値の `http://goofy.local:5000/video` をそのまま利用できます。

## 起動

```powershell
cd C:\drone-research\pc-gcs
.\venv\Scripts\Activate.ps1
python app.py
```

Raspberry Pi 側の `mavlink-router` は、このPCのIPアドレスの UDP 14550 に転送してください。GUIはハートビートを3秒以上受信できない場合に `SIGNAL LOST` を表示します。
