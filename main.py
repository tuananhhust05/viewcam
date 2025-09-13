import sys
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QIcon
import vlc
import os
import time

# --- Đường dẫn VLC nếu cần ---
# vlc_path = r"C:\Program Files\VideoLAN\VLC"
# if os.path.exists(vlc_path):
#     os.add_dll_directory(vlc_path)

LOG_FILE = "failed_cams.txt"

# --- Danh sách camera ---
CAM_LIST = [
    {"url": "rtsp://admin:UNV123456%@192.168.22.100:554/ch01", "area": "Cổng", "name": "Cam Cổng 1"},
    {"url": "rtsp://admin:UNV123456%@192.168.22.46:554/ch01", "area": "Phòng tiếp dân", "name": "Cam Tiếp dân 1"},
    {"url": "rtsp://admin:UNV123456%@192.168.22.61:554/ch01", "area": "Tường rào", "name": "Cam Tường"},
    {"url": "rtsp://admin:UNV123456%@192.168.22.88:554/ch01", "area": "Cổng", "name": "Cam Cổng 2"},
    {"url": "rtsp://admin:123456a$@192.168.22.73:554/ch01", "area": "Phòng tiếp dân", "name": "Cam Tiếp dân 2"},
    {"url": "rtsp://admin:UNV123456%@192.168.22.86:554/ch01", "area": "Tường rào", "name": "Cam Tường rào"},
    {"url": "rtsp://admin:UNV123456%@192.168.22.26:554/ch01", "area": "Cổng", "name": "Cam Cổng 3"},
    {"url": "rtsp://admin:UNV123456%@192.168.22.28:554/ch01", "area": "Phòng tiếp dân", "name": "Cam Tiếp dân 3"}
]

AREAS = ["Tất cả"] + sorted(list({cam["area"] for cam in CAM_LIST}))

APP_STYLE = """
QWidget {
    font-family: "San Francisco", "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 14px;
    background-color: #f5f5f7;
    color: #1d1d1f;
}
QLabel {
    color: #1d1d1f;
    font-weight: 500;
}
QComboBox, QSpinBox {
    border: 1px solid #c7c7cc;
    border-radius: 6px;
    padding: 4px 8px;
    background-color: white;
    min-height: 26px;
}
QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {
    width: 0px;
    border: none;
}
QComboBox::down-arrow, QSpinBox::up-arrow, QSpinBox::down-arrow {
    image: none;
    border: none;
    width: 0;
    height: 0;
}
QFrame#videoframe {
    border-radius: 12px;
    background-color: black;
}
"""

class CameraWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, cam_name=""):
        super().__init__(parent)
        self.cam_name = cam_name
        self.full_window = None

        self.stack_layout = QtWidgets.QStackedLayout(self)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)

        # Video frame
        self.videoframe = QtWidgets.QFrame()
        self.videoframe.setObjectName("videoframe")
        self.stack_layout.addWidget(self.videoframe)

        # Label tên cam
        self.name_label = QtWidgets.QLabel(self.cam_name, self)
        self.name_label.setStyleSheet("color: white; font-size: 13px; background: transparent;")
        self.name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop)
        self.name_label.raise_()

        # Nút fullscreen
        self.full_btn = QtWidgets.QPushButton("⛶", self)
        self.full_btn.setStyleSheet("background: transparent; color: white; font-size: 18px; border: none;")
        self.full_btn.setFixedSize(28, 28)
        self.full_btn.raise_()
        self.full_btn.clicked.connect(self.open_fullscreen)

        # VLC
        vlc_args = ["--network-caching=300", "--rtsp-tcp", "--no-xlib"]
        self.instance = vlc.Instance(vlc_args)
        self.player = self.instance.media_player_new()

    def resizeEvent(self, event):
        btn_size = self.full_btn.size()
        self.full_btn.move(self.width() - btn_size.width() - 5, self.height() - btn_size.height() - 5)
        self.name_label.move(self.width() - self.name_label.width() - 10, 5)
        super().resizeEvent(event)

    def play(self, url: str):
        if not url:
            return
        try:
            media = self.instance.media_new(url)
            self.player.set_media(media)

            if sys.platform.startswith("win"):
                self.player.set_hwnd(int(self.videoframe.winId()))
            elif sys.platform.startswith("linux"):
                self.player.set_xwindow(self.videoframe.winId())
            elif sys.platform.startswith("darwin"):
                self.player.set_nsobject(int(self.videoframe.winId()))

            self.player.play()
            QtCore.QTimer.singleShot(2000, lambda: self.check_stream(url))
        except Exception as e:
            self.log_failed(url, str(e))

    def stop(self):
        self.player.stop()

    def check_stream(self, url):
        state = self.player.get_state()
        if state not in (vlc.State.Playing, vlc.State.Buffering):
            self.log_failed(url, f"VLC state: {state}")

    def log_failed(self, url, reason):
        print(f"[ERROR] Camera failed: {url} - {reason}")
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {url} - {reason}\n")

    def open_fullscreen(self):
        if self.full_window is None:
            self.full_window = FullScreenWindow(self)
        self.full_window.showFullScreen()


class FullScreenWindow(QtWidgets.QMainWindow):
    def __init__(self, cam_widget):
        super().__init__()
        self.cam_widget = cam_widget

        # Frame riêng cho fullscreen
        self.full_videoframe = QtWidgets.QFrame()
        self.full_videoframe.setStyleSheet("background-color: black;")
        self.setCentralWidget(self.full_videoframe)

        # Gán video output sang frame fullscreen
        if sys.platform.startswith("win"):
            self.cam_widget.player.set_hwnd(int(self.full_videoframe.winId()))
        elif sys.platform.startswith("linux"):
            self.cam_widget.player.set_xwindow(self.full_videoframe.winId())
        elif sys.platform.startswith("darwin"):
            self.cam_widget.player.set_nsobject(int(self.full_videoframe.winId()))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            # Trả video output về widget gốc
            if sys.platform.startswith("win"):
                self.cam_widget.player.set_hwnd(int(self.cam_widget.videoframe.winId()))
            elif sys.platform.startswith("linux"):
                self.cam_widget.player.set_xwindow(self.cam_widget.videoframe.winId())
            elif sys.platform.startswith("darwin"):
                self.cam_widget.player.set_nsobject(int(self.cam_widget.videoframe.winId()))
            self.close()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Movis - RTSP Multi-View Player")
        self.setWindowIcon(QIcon("logo.svg"))
        self.resize(1600, 900)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        self.vbox = QtWidgets.QVBoxLayout(central)

        # Thanh điều khiển
        hbox = QtWidgets.QHBoxLayout()
        self.num_cam_spin = QtWidgets.QSpinBox()
        self.num_cam_spin.setRange(1, 8)
        self.num_cam_spin.setValue(8)
        hbox.addWidget(QtWidgets.QLabel("Số camera hiển thị:"))
        hbox.addWidget(self.num_cam_spin)

        self.area_combo = QtWidgets.QComboBox()
        self.area_combo.addItems(AREAS)
        hbox.addStretch()
        hbox.addWidget(QtWidgets.QLabel("Khu vực:"))
        hbox.addWidget(self.area_combo)
        self.vbox.addLayout(hbox)

        # Grid layout
        self.grid = QtWidgets.QGridLayout()
        self.vbox.addLayout(self.grid, stretch=1)
        self.cams = []
        for cam_data in CAM_LIST:
            cam = CameraWidget(self, cam_name=cam_data["name"])
            self.cams.append(cam)
            self.grid.addWidget(cam, 0, 0)

        self.num_cam_spin.valueChanged.connect(self.update_display)
        self.area_combo.currentIndexChanged.connect(self.update_display)

        self.play_all()
        self.update_display()

    def play_all(self):
        for cam, cam_data in zip(self.cams, CAM_LIST):
            cam.play(cam_data["url"])

    def update_display(self):
        num_to_show = self.num_cam_spin.value()
        selected_area = self.area_combo.currentText()
        filtered_indices = [i for i, cam_data in enumerate(CAM_LIST)
                            if selected_area == "Tất cả" or cam_data["area"] == selected_area]
        show_indices = filtered_indices[:num_to_show]

        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            self.grid.removeWidget(widget)

        n = len(show_indices)
        if n == 0:
            return

        if n == 1:
            rows, cols = 1, 1
        elif n == 2:
            rows, cols = 1, 2
        elif n == 3:
            rows, cols = 2, 2
        elif n == 4:
            rows, cols = 2, 2
        elif n <= 6:
            rows, cols = 2, 3
        else:
            rows, cols = 2, 4

        for idx, cam_idx in enumerate(show_indices):
            row = idx // cols
            col = idx % cols
            cam = self.cams[cam_idx]
            self.grid.addWidget(cam, row, col)
            cam.setVisible(True)

        for i, cam in enumerate(self.cams):
            if i not in show_indices:
                cam.setVisible(False)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
