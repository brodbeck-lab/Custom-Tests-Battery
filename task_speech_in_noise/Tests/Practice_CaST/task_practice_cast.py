# task_speech_in_noise/Tests/Practice_CaST/task_practice_cast.py
import sys, os, glob
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QStackedLayout, QFrame
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

INSTR_TEXT = (
    "Read this to the participant:\n"
    "In this part of the test, you will hear some audio recordings.\n"
    "After each one, please repeat exactly what you heard.\n"
    "We'll start with a few practice items now."
)

def button_style():
    return """
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
            color: black; border: 2px solid #e0e0e0; border-radius: 35px;
            padding: 10px; font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #fafafa, stop:1 #e8e8e8);
            border: 2px solid #d0d0d0;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #e8e8e8, stop:1 #ffffff);
            border: 2px solid #c0c0c0;
        }
    """

class PracticeCastTask(QWidget):
    """
    Single window with two pages (Instruction <-> Player) via QStackedLayout.
    """
    def __init__(self, participant_id=None, participant_folder_path=None, parent=None):
        super().__init__(parent)
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path

        self.setWindowTitle("Practice CaST")
        self.setStyleSheet("background-color: #f6f6f6;")
        self.resize(1200, 760)

        # Paths
        self.base_dir  = os.path.dirname(__file__)
        self.audio_dir = os.path.join(self.base_dir, "Audio")
        self.text_path = os.path.join(self.base_dir, "Practice_CaST_List.txt")

        self.audio_files = self._collect_audio_files(self.audio_dir)
        self.text_items  = self._read_text_lines(self.text_path)
        self.n = min(len(self.audio_files), len(self.text_items))

        # Stack
        self.stack = QStackedLayout(self)
        self.page_instr  = self._build_instruction_page()
        self.page_player = self._build_player_page()
        self.stack.addWidget(self.page_instr)
        self.stack.addWidget(self.page_player)
        self.stack.setCurrentIndex(0)

    # ---------- Instruction Page ----------
    def _build_instruction_page(self):
        page = QFrame(self)
        root = QVBoxLayout(page)
        root.setContentsMargins(24, 24, 24, 24)
        root.addStretch()

        title = QLabel("Practice CaST", page)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setStyleSheet("color:#2c3e50;")
        root.addWidget(title)

        instr = QLabel(INSTR_TEXT, page)
        instr.setWordWrap(True)
        instr.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        instr.setFont(QFont("Arial", 18))
        instr.setStyleSheet("""
            QLabel {
                color: black; background: white;
                border: 2px solid #e0e0e0; border-radius: 20px;
                padding: 24px; margin: 24px;
            }
        """)
        root.addWidget(instr)

        row = QHBoxLayout()
        back_btn = QPushButton("Back to SiN Menu", page)
        back_btn.setFixedSize(220, 64)
        back_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        back_btn.setStyleSheet(button_style())
        back_btn.clicked.connect(self._go_back_to_sin)

        start_btn = QPushButton("Start", page)
        start_btn.setFixedSize(200, 64)
        start_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        start_btn.setStyleSheet(button_style())
        start_btn.clicked.connect(self._start_practice)

        row.addStretch(); row.addWidget(back_btn); row.addSpacing(20); row.addWidget(start_btn); row.addStretch()
        root.addLayout(row)
        root.addStretch()
        return page

    # ---------- Player Page ----------
    def _build_player_page(self):
        page = QFrame(self)
        self.player_root = QVBoxLayout(page)
        self.player_root.setContentsMargins(24, 24, 24, 24)
        self.player_root.addStretch()

        title = QLabel("Practice CaST", page)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setStyleSheet("color:#2c3e50;")
        self.player_root.addWidget(title)

        self.counter_lbl = QLabel("", page)
        self.counter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.counter_lbl.setStyleSheet("color:#2c3e50;")
        self.player_root.addWidget(self.counter_lbl)

        self.text_lbl = QLabel("", page)
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_lbl.setFont(QFont("Arial", 20))
        self.text_lbl.setStyleSheet("""
            QLabel {
                color: black; background: white;
                border: 2px solid #e0e0e0; border-radius: 20px;
                padding: 28px; margin: 24px;
            }
        """)
        self.player_root.addWidget(self.text_lbl)

        # --- New: status + response timer labels ---
        self.status_lbl = QLabel(" ", page)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color:#2c3e50;")
        self.player_root.addWidget(self.status_lbl)

        self.response_lbl = QLabel("Response time: —", page)
        self.response_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_lbl.setFont(QFont("Arial", 16))
        self.response_lbl.setStyleSheet("color:#2c3e50;")
        self.player_root.addWidget(self.response_lbl)

        # Controls
        ctrl = QHBoxLayout()
        self.btn_back = QPushButton("Back", page)
        self.btn_back.setFixedSize(160, 64)
        self.btn_back.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.btn_back.setStyleSheet(button_style())
        self.btn_back.clicked.connect(self._go_prev)

        self.btn_play = QPushButton("Play", page)
        self.btn_play.setFixedSize(160, 64)
        self.btn_play.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.btn_play.setStyleSheet(button_style())
        self.btn_play.clicked.connect(self._play_current)

        self.btn_stop = QPushButton("Stop", page)
        self.btn_stop.setFixedSize(160, 64)
        self.btn_stop.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.btn_stop.setStyleSheet(button_style())
        self.btn_stop.clicked.connect(self._stop_audio)

        self.btn_next = QPushButton("Next", page)
        self.btn_next.setFixedSize(160, 64)
        self.btn_next.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.btn_next.setStyleSheet(button_style())
        self.btn_next.clicked.connect(self._go_next)

        ctrl.addStretch()
        for b in (self.btn_back, self.btn_play, self.btn_stop, self.btn_next):
            ctrl.addWidget(b); ctrl.addSpacing(16)
        ctrl.addStretch()
        self.player_root.addLayout(ctrl)

        # Bottom: back to SIN menu
        bottom = QHBoxLayout()
        back_menu = QPushButton("Back to SiN Menu", page)
        back_menu.setFixedSize(240, 64)
        back_menu.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        back_menu.setStyleSheet(button_style())
        back_menu.clicked.connect(self._go_back_to_sin)
        bottom.addStretch(); bottom.addWidget(back_menu); bottom.addStretch()
        self.player_root.addLayout(bottom)

        self.player_root.addStretch()

        # Player + audio out
        self.player = QMediaPlayer(page)
        self.audio_out = QAudioOutput(page)
        self.player.setAudioOutput(self.audio_out)
        self.audio_out.setVolume(1.0)

        # Start response timer when playback ends naturally
        self.player.mediaStatusChanged.connect(self._on_media_status)

        # Response timer
        self.response_timer = QTimer(page)
        self.response_timer.setInterval(100)
        self.response_timer.timeout.connect(self._on_response_tick)
        self.response_running = False
        self.response_ms = 0

        # State
        self.idx = 0
        self._refresh_player_ui()
        return page

    # ---------- helpers ----------
    def _collect_audio_files(self, audio_dir):
        files = glob.glob(os.path.join(audio_dir, "*.wav"))
        def key(p):
            name = os.path.basename(p)
            try:
                return int(name.split("_", 1)[0])  # "1_xxx.wav" -> 1
            except Exception:
                return name
        return sorted(files, key=key)

    def _read_text_lines(self, txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                return [ln.strip() for ln in f if ln.strip() != ""]
        except FileNotFoundError:
            return []

    # ---------- navigation / actions ----------
    def _start_practice(self):
        if self.n == 0:
            QMessageBox.warning(self, "Practice CaST", "No audio/text items found.")
            return
        self.stack.setCurrentIndex(1)

    def _go_prev(self):
        self._stop_response_timer()
        if self.idx > 0:
            self.idx -= 1
            self._refresh_player_ui()
        else:
            self._stop_audio()
            self.stack.setCurrentIndex(0)

    def _go_next(self):
        self._stop_response_timer()
        if self.idx < self.n - 1:
            self.idx += 1
            self._refresh_player_ui()
        else:
            QMessageBox.information(self, "Practice CaST", "Practice finished.")

    def _play_current(self):
        if self.n == 0:
            return
        self._reset_response_timer()
        self.status_lbl.setText("Playing…")
        path = self.audio_files[self.idx]
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.setPosition(0)
        self.player.play()

    def _stop_audio(self):
        self.player.stop()
        # stopping manually should not start the response timer
        self.status_lbl.setText("Stopped")
        self._stop_response_timer()

    def _refresh_player_ui(self):
        if self.n == 0:
            self.counter_lbl.setText("No items")
            self.text_lbl.setText("—")
            self.status_lbl.setText(" ")
            self._reset_response_timer()
            return
        self.counter_lbl.setText(f"Item {self.idx+1} of {self.n}")
        self.text_lbl.setText(self.text_items[self.idx])
        self.player.stop()
        self._reset_response_timer()

    def _go_back_to_sin(self):
        self._stop_audio()
        from task_speech_in_noise.sin_menu import SpeechInNoiseMenuWindow
        w = SpeechInNoiseMenuWindow(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.close()

    # ---------- media finish & response timer ----------
    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.status_lbl.setText("Audio finished ✓")
            self._start_response_timer()

    def _start_response_timer(self):
        self.response_ms = 0
        self.response_running = True
        self.response_lbl.setText("Response time: 00:00")
        self.response_timer.start()

    def _on_response_tick(self):
        if not self.response_running:
            return
        self.response_ms += 100
        self.response_lbl.setText(f"Response time: {self._fmt_ms(self.response_ms)}")

    def _stop_response_timer(self):
        if self.response_running:
            self.response_running = False
            self.response_timer.stop()

    def _reset_response_timer(self):
        self._stop_response_timer()
        self.response_ms = 0
        self.response_lbl.setText("Response time: —")
        self.status_lbl.setText(" ")

    def _fmt_ms(self, ms: int) -> str:
        minutes = ms // 60000
        seconds = (ms // 1000) % 60
        millis  = ms % 1000
        return f"{minutes:02}:{seconds:02}.{millis:03}"

# ---------- standalone test ----------
def main():
    app = QApplication(sys.argv)
    w = PracticeCastTask()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
