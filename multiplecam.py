#!/usr/bin/env python3
"""
Fixed 6-Cam custom layout (A = 2x2 tiles, others 1x1)
- Base grid: 3 cols x 3 rows of tiles.
  tile_w_base = 512, tile_h_base = 288 -> baseW=1536, baseH=864
- A (cam index 0) spans cols 0..1 and rows 0..1 => 1024x576 at base
- Other cams fill remaining 1x1 tiles
- No gaps: boundaries computed and rounded so sum pixels == screen size
- Ctrl+F toggles fullscreen for the 6-cam window

Requirements:
    pip install PyQt6 python-vlc
"""
import sys
import os
import time
from PyQt6 import QtWidgets, QtCore
import vlc

# ---------- Cameras ----------
CAM_LIST = [
    {"id": 1, "url": "rtsp://192.168.22.5:38554/6385209cf41a711973ddb2bf_origin", "name": "A"},
    {"id": 2, "url": "rtsp://192.168.22.5:38554/3f21870fc1e0a77d5e6abf9e_origin", "name": "B"},
    {"id": 3, "url": "rtsp://192.168.22.5:38554/7966fe4435980970850a41e3_origin", "name": "C"},
    {"id": 4, "url": "rtsp://admin:UNV123456%@192.168.22.88:554/ch01", "name": "D"},
    {"id": 5, "url": "rtsp://192.168.22.5:38554/7d7da2895a68c864ec6ff55d_origin", "name": "E"},
    {"id": 6, "url": "rtsp://192.168.22.5:38554/8ababce1f3b51c3b12d017f0_origin", "name": "F"},
]

# VLC options (you can add :autoscale :aspect-ratio=0 if you want stretch)
VLC_OPTS = ":no-video-title-show :no-sub-autodetect-file :no-osd :network-caching=300"

# Windows dll directory helper
if sys.platform == "win32":
    base_path = os.path.dirname(os.path.abspath(__file__))
    try:
        os.add_dll_directory(base_path)
    except Exception:
        pass


# ---------- Helpers ----------
def compute_boundaries(total_pixels: int, segments: int):
    """
    return integer boundary list length segments+1 such that:
      boundaries[0]=0, boundaries[-1]=total_pixels
    using round(i * total_pixels / segments)
    ensures sum of segment widths == total_pixels (no pixel loss).
    """
    return [int(round(i * total_pixels / segments)) for i in range(segments + 1)]


def set_player_window_for_platform(player: vlc.MediaPlayer, frame: QtWidgets.QFrame):
    try:
        winid = int(frame.winId())
        if sys.platform.startswith("linux"):
            player.set_xwindow(winid)
        elif sys.platform == "win32":
            player.set_hwnd(winid)
        elif sys.platform == "darwin":
            try:
                player.set_nsobject(winid)
            except Exception:
                player.set_nsobject(int(winid))
    except Exception as e:
        print("[WARN] set_player_window failed:", e)


# ---------- Single-camera window (unchanged) ----------
class CamWindow(QtWidgets.QMainWindow):
    RECONNECT_INTERVAL = 5  # seconds

    def __init__(self, cam_info: dict, vlc_instance: vlc.Instance, parent=None, show_full=True):
        super().__init__(parent)
        self.cam_info = cam_info
        self.vlc_instance = vlc_instance
        self.player = self.vlc_instance.media_player_new()
        self.setWindowTitle(f"[{cam_info['id']}] {cam_info.get('name','')}")
        self.setWindowFlags(QtCore.Qt.WindowType.Window)

        self.video_frame = QtWidgets.QFrame(self)
        self.setCentralWidget(self.video_frame)

        self.overlay = QtWidgets.QLabel(self.video_frame)
        self.overlay.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay.setStyleSheet("background: rgba(0,0,0,0.35); color: white; padding: 6px;")
        self.overlay.setText(f"ID {cam_info['id']} — {cam_info.get('name','')}")
        self.overlay.adjustSize()
        self.overlay.move(8, 8)

        self._last_play_attempt = 0.0
        self._fullscreen = show_full

        self.watch_timer = QtCore.QTimer(self)
        self.watch_timer.setInterval(2000)
        self.watch_timer.timeout.connect(self._monitor)
        self.watch_timer.start()

        if show_full:
            QtCore.QTimer.singleShot(50, self._show_fullscreen)
        else:
            QtCore.QTimer.singleShot(50, self.show)

        QtCore.QTimer.singleShot(150, self.start_playback)

    def _show_fullscreen(self):
        self.show()
        self.showFullScreen()
        self._fullscreen = True

    def start_playback(self):
        url = self.cam_info.get("url", "")
        if not url:
            return
        now = time.time()
        if now - self._last_play_attempt < 1.0:
            return
        self._last_play_attempt = now
        try:
            media = self.vlc_instance.media_new(url, VLC_OPTS)
            self.player.set_media(media)
            set_player_window_for_platform(self.player, self.video_frame)
            self.player.play()
        except Exception as e:
            print(f"{self.cam_info.get('name','cam')} playback failed: {e}")

    def _monitor(self):
        if not self.player:
            return
        state = self.player.get_state()
        if state not in (vlc.State.Playing, vlc.State.Paused):
            now = time.time()
            if now - self._last_play_attempt > self.RECONNECT_INTERVAL:
                self.start_playback()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Q):
            self.close()
        elif key == QtCore.Qt.Key.Key_F:
            if self._fullscreen:
                self.showNormal()
                self._fullscreen = False
            else:
                self.showFullScreen()
                self._fullscreen = True
        elif not self._fullscreen and key in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
            self.resize(int(self.width() * 1.2), int(self.height() * 1.2))
        elif not self._fullscreen and key == QtCore.Qt.Key.Key_Minus:
            self.resize(max(200, int(self.width() * 0.8)), max(150, int(self.height() * 0.8)))
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        try:
            if self.player:
                self.player.stop()
                time.sleep(0.05)
        except Exception:
            pass
        event.accept()


# ---------- Custom 6-cam layout window ----------
class CustomLayoutWindow(QtWidgets.QMainWindow):
    """
    The custom 6-cam window using a 3x3 tile grid (tile base = 512x288).
    Tile mapping (col,row indices):
      - cam 0 (A): col 0..1, row 0..1 (span 2x2)
      - cam 1 (B): col 2, row 0
      - cam 2 (C): col 2, row 1
      - cam 3 (D): col 2, row 2
      - cam 4 (E): col 0, row 2
      - cam 5 (F): col 1, row 2
    """

    def __init__(self, cams, vlc_instance: vlc.Instance, parent=None):
        super().__init__(parent)
        self.setWindowTitle("6 Camera Custom Layout")
        self.setWindowFlags(QtCore.Qt.WindowType.Window)

        self.cams = cams
        self.vlc_instance = vlc_instance
        self.frames = []   # list of (frame, label, cam)
        self.players = []  # vlc players (index-aligned to frames)

        central = QtWidgets.QWidget()
        central.setContentsMargins(0, 0, 0, 0)
        central.setStyleSheet("background: black;")
        self.setCentralWidget(central)

        # create frames (child of central) and overlay labels
        for cam in cams:
            f = QtWidgets.QFrame(central)
            f.setStyleSheet("background: black; border: 0px;")
            lbl = QtWidgets.QLabel(f)
            lbl.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            lbl.setStyleSheet("background: rgba(0,0,0,0.32); color: white; padding: 4px;")
            lbl.setText(f"[{cam['id']}] {cam.get('name','')}")
            lbl.adjustSize()
            lbl.move(8, 8)
            self.frames.append((f, lbl, cam))

        # mapping in tile coordinates (col_start, row_start, col_end, row_end)
        # col_end and row_end are *exclusive* indices into the boundaries array
        self.tile_map = {
            0: (0, 0, 2, 2),  # A: spans cols 0-1, rows 0-1
            1: (2, 0, 3, 1),  # B
            2: (2, 1, 3, 2),  # C
            3: (2, 2, 3, 3),  # D
            4: (0, 2, 1, 3),  # E
            5: (1, 2, 2, 3),  # F
        }

        # show fullscreen initially
        QtCore.QTimer.singleShot(50, self.showFullScreen)
        # perform initial layout after shown
        QtCore.QTimer.singleShot(80, self._layout_and_attach)

        self._fullscreen = True

    def _layout_and_attach(self):
        """
        Compute integer boundaries for 3 segments (columns) and 3 segments (rows),
        set geometry for each frame accordingly, then (re)attach players.
        """
        screen = self.windowHandle().screen() if self.windowHandle() else QtWidgets.QApplication.primaryScreen()
        geom = screen.geometry()
        sw, sh = geom.width(), geom.height()

        # compute integer boundaries so total sums exactly to sw/sh
        x_bounds = compute_boundaries(sw, 3)  # length 4
        y_bounds = compute_boundaries(sh, 3)  # length 4

        # set geometry for each frame based on tile_map
        for idx, (frame, lbl, cam) in enumerate(self.frames):
            if idx not in self.tile_map:
                # hide any extra frames (shouldn't happen)
                frame.setGeometry(0, 0, 0, 0)
                continue
            cs, rs, ce, re = self.tile_map[idx]
            x = x_bounds[cs]
            y = y_bounds[rs]
            w = x_bounds[ce] - x
            h = y_bounds[re] - y
            # make sure ints and non-negative
            w = max(0, int(w))
            h = max(0, int(h))
            frame.setGeometry(int(x), int(y), w, h)
            lbl.raise_()

        # attach or reassign players
        if not self.players:
            # create players first time
            for (frame, _, cam) in self.frames:
                try:
                    player = self.vlc_instance.media_player_new()
                    media = self.vlc_instance.media_new(cam["url"], VLC_OPTS)
                    player.set_media(media)
                    set_player_window_for_platform(player, frame)
                    player.play()
                    self.players.append(player)
                except Exception as e:
                    print(f"[ERROR] attach player failed for {cam.get('name')}: {e}")
                    self.players.append(None)
        else:
            # just reassign existing players to new frame winIds
            for i, player in enumerate(self.players):
                if i < len(self.frames) and player:
                    frame, _, _ = self.frames[i]
                    set_player_window_for_platform(player, frame)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # relayout on resize (keeps no gaps)
        QtCore.QTimer.singleShot(10, self._layout_and_attach)

    def showEvent(self, event):
        super().showEvent(event)
        QtCore.QTimer.singleShot(40, self._layout_and_attach)

    def keyPressEvent(self, event):
        # Ctrl+F toggles fullscreen for this window
        if (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier) and event.key() == QtCore.Qt.Key.Key_F:
            if self._fullscreen:
                self.showNormal()
                self._fullscreen = False
            else:
                self.showFullScreen()
                self._fullscreen = True
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        for p in self.players:
            try:
                if p:
                    p.stop()
            except Exception:
                pass
        event.accept()


# ---------- Main ----------
def main():
    app = QtWidgets.QApplication(sys.argv)
    vlc_args = ["--no-xlib"] if sys.platform.startswith("linux") else []
    vlc_instance = vlc.Instance(*vlc_args)

    # open 6 single cam windows (as you had before)
    windows = [CamWindow(cam, vlc_instance) for cam in CAM_LIST]

    # open the custom-layout 6-cam window (the one that must follow your format)
    custom = CustomLayoutWindow(CAM_LIST, vlc_instance)
    custom.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
