# task_speech_in_noise/CaST_word/task_cast_word.py
import sys, os, csv, re
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QStackedLayout, QFrame, QCheckBox
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


INSTR_TEXT = (
    "Read this to the participant:\n"
    "In this part (CaST Word), you will hear single words in noise.\n"
    "After each one, please repeat what you heard."
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


class CaSTWordTask(QWidget):

    def __init__(self, participant_id=None, participant_folder_path=None, parent=None):
        super().__init__(parent)
        self.participant_id = participant_id or "UNKNOWN"
        self.participant_folder_path = participant_folder_path

        # GUI
        self.setWindowTitle("CaST Word")
        self.setStyleSheet("background-color: #f6f6f6;")
        self.resize(1100, 720)

        # Paths
        self.base_dir = os.path.dirname(__file__)
        self.csv_path = os.path.join(self.base_dir, "CaST_word_list.csv")
        self.audio_dir = os.path.join(self.base_dir, "Audio")

        # Load CSV
        self.rows, self.csv_fieldnames = self._load_csv_rows(self.csv_path)
        self.n = len(self.rows)
        self.idx = 0

        # Audio
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.audio_out.setVolume(1.0)
        self.player.mediaStatusChanged.connect(self._on_media_status)

        # Timer
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick_response)
        self.response_running = False
        self.response_ms = 0

        # Result path
        self.results_path = self._make_results_path(self.participant_id)

        # Layout pages
        self.stack = QStackedLayout(self)
        self.page_instr = self._build_instruction_page()
        self.page_player = self._build_player_page()
        self.stack.addWidget(self.page_instr)
        self.stack.addWidget(self.page_player)
        self.stack.setCurrentIndex(0)

    # ---------------- INSTRUCTION PAGE ----------------
    def _build_instruction_page(self):
        page = QFrame(self)
        root = QVBoxLayout(page)
        root.addStretch()

        title = QLabel("CaST Word", page)
        title.setStyleSheet("color:#2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        root.addWidget(title)

        instr = QLabel(INSTR_TEXT, page)
        instr.setWordWrap(True)
        instr.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        instr.setFont(QFont("Arial", 18))
        instr.setStyleSheet("""
            QLabel {
                color:#2c3e50;
                background:white;
                border-radius:20px;
                border:2px solid #e0e0e0;
                padding:24px;
            }
        """)

        root.addWidget(instr)

        row = QHBoxLayout()
        back_btn = QPushButton("Back to SiN Menu", page)
        back_btn.setFixedSize(280, 64)
        back_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        back_btn.setStyleSheet(button_style())
        back_btn.clicked.connect(self._go_back_to_sin)

        start_btn = QPushButton("Start", page)
        start_btn.setFixedSize(200, 64)
        start_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        start_btn.setStyleSheet(button_style())
        start_btn.clicked.connect(self._start_task)

        row.addStretch()
        row.addWidget(back_btn)
        row.addSpacing(20)
        row.addWidget(start_btn)
        row.addStretch()
        root.addLayout(row)

        root.addStretch()
        return page

    # ---------------- PLAYER PAGE ----------------
    def _build_player_page(self):
        page = QFrame(self)
        root = QVBoxLayout(page)
        root.addStretch()

        title = QLabel("CaST Word", page)
        title.setStyleSheet("color:#2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        root.addWidget(title)

        # SNR summary
        top_row = QHBoxLayout()
        self.snr_summary_lbl = QLabel("", page)
        self.snr_summary_lbl.setStyleSheet("color:#2c3e50;")
        self.snr_summary_lbl.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        top_row.addWidget(self.snr_summary_lbl)
        top_row.addStretch()
        root.addLayout(top_row)

        # Counter
        self.counter_lbl = QLabel("", page)
        self.counter_lbl.setStyleSheet("color:#2c3e50;")
        self.counter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        root.addWidget(self.counter_lbl)

        # SNR label
        self.snr_lbl = QLabel("", page)
        self.snr_lbl.setStyleSheet("color:#2c3e50;")
        self.snr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.snr_lbl.setFont(QFont("Arial", 18, QFont.Weight.DemiBold))
        root.addWidget(self.snr_lbl)

        # Word display
        self.word_lbl = QLabel("—", page)
        self.word_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_lbl.setWordWrap(True)
        self.word_lbl.setFont(QFont("Arial", 28))
        self.word_lbl.setStyleSheet("""
            QLabel {
                color:#2c3e50;
                background:white;
                border-radius:20px;
                border:2px solid #e0e0e0;
                padding:28px; margin:24px;
            }
        """)
        root.addWidget(self.word_lbl)

        # Checkbox
        row = QHBoxLayout()
        row.addStretch()
        self.word_check = QCheckBox("Correct", page)
        self.word_check.setStyleSheet("color:#2c3e50;")
        self.word_check.setFont(QFont("Arial", 16))
        self.word_check.stateChanged.connect(self._on_check_toggled)
        self.word_check.stateChanged.connect(self._update_snr_summary)
        row.addWidget(self.word_check)
        row.addStretch()
        root.addLayout(row)

        # Status + timer
        self.status_lbl = QLabel(" ", page)
        self.status_lbl.setStyleSheet("color:#2c3e50;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        root.addWidget(self.status_lbl)

        self.response_lbl = QLabel("Response time: —", page)
        self.response_lbl.setStyleSheet("color:#2c3e50;")
        self.response_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_lbl.setFont(QFont("Arial", 16))
        root.addWidget(self.response_lbl)

        # Buttons
        ctrl = QHBoxLayout()
        self.btn_back = QPushButton("Back", page)
        self.btn_play = QPushButton("Play", page)
        self.btn_stop = QPushButton("Stop", page)
        self.btn_next = QPushButton("Play Next", page)

        for b in (self.btn_back, self.btn_play, self.btn_stop, self.btn_next):
            b.setFixedSize(160, 64)
            b.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            b.setStyleSheet(button_style())
            ctrl.addWidget(b)
            ctrl.addSpacing(16)

        self.btn_back.clicked.connect(self._go_prev)
        self.btn_play.clicked.connect(self._play_current)
        self.btn_stop.clicked.connect(self._stop_audio)
        self.btn_next.clicked.connect(self._go_next)

        root.addLayout(ctrl)

        # Back to menu
        bottom = QHBoxLayout()
        back_menu = QPushButton("Back to SiN Menu", page)
        back_menu.setFixedSize(280, 64)
        back_menu.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        back_menu.setStyleSheet(button_style())
        back_menu.clicked.connect(self._go_back_to_sin)
        bottom.addStretch()
        bottom.addWidget(back_menu)
        bottom.addStretch()
        root.addLayout(bottom)

        root.addStretch()

        self._refresh_ui_for_index()
        return page

    # ---------------- LOAD CSV ----------------
    def _load_csv_rows(self, csv_path):
        if not os.path.exists(csv_path):
            QMessageBox.critical(self, "CaST Word", f"CSV not found:\n{csv_path}")
            return [], []

        rows = []
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            for r in reader:
                row = {k.strip(): (v or "").strip() for k, v in r.items()}
                fn = row.get("File Name", "")
                row["File Name"] = fn
                rows.append(row)

        return rows, fieldnames

    # ---------------- AUDIO ----------------
    def _resolve_audio_path(self, row):
        fn = (row.get("File Name") or "").strip()
        if not fn:
            return ""
        if not fn.lower().endswith(".wav"):
            fn += ".wav"
        return os.path.join(self.audio_dir, fn)

    # ---------------- UI UPDATE ----------------
    def _refresh_ui_for_index(self):
        if self.n == 0:
            return

        row = self.rows[self.idx]

        self.counter_lbl.setText(f"Item {self.idx+1} of {self.n}")

        snr = row.get("SNR", "")
        self.snr_lbl.setText(f"SNR: {snr} dB")

        word = row.get("Word", "—")
        self.word_lbl.setText(word)

        checked = (row.get("Correct/Wrong", "").lower() == "1")
        self.word_check.blockSignals(True)
        self.word_check.setChecked(checked)
        self.word_check.blockSignals(False)

        self.player.stop()
        self._reset_timer()
        self._update_snr_summary()

    def _on_check_toggled(self, _):
        self.rows[self.idx]["Correct/Wrong"] = "1" if self.word_check.isChecked() else "0"

    # --------- SNR summary ----------
    def _update_snr_summary(self):
        totals, corrects = {}, {}

        for r in self.rows:
            snr = r.get("SNR", "").strip()
            if not snr:
                continue
            totals[snr] = totals.get(snr, 0) + 1
            if r.get("Correct/Wrong", "").strip() == "1":
                corrects[snr] = corrects.get(snr, 0) + 1

        lines = []
        for snr in sorted(totals.keys(), key=int, reverse=True):
            cor = corrects.get(snr, 0)
            tot = totals[snr]
            pct = int((cor / tot) * 100)
            lines.append(f"SNR {snr}: {cor}/{tot} ({pct}%)")

        self.snr_summary_lbl.setText("\n".join(lines))

    # ---------------- Actions ----------------
    def _start_task(self):
        if self.n == 0:
            QMessageBox.warning(self, "CaST Word", "No items found.")
            return
        self.stack.setCurrentIndex(1)

    def _go_prev(self):
        self._write_results()
        self._stop_audio()
        if self.idx > 0:
            self.idx -= 1
            self._refresh_ui_for_index()
        else:
            self.stack.setCurrentIndex(0)

    def _go_next(self):
        self._write_results()
        self._stop_audio()
        if self.idx < self.n - 1:
            self.idx += 1
            self._refresh_ui_for_index()
            self._play_current()
        else:
            QMessageBox.information(self, "CaST Word", "Task finished.")

    def _play_current(self):
        path = self._resolve_audio_path(self.rows[self.idx])
        if not os.path.exists(path):
            QMessageBox.warning(self, "CaST Word", f"Audio not found:\n{path}")
            return
        self._reset_timer()
        self.status_lbl.setText("Playing…")
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.setPosition(0)
        self.player.play()

    def _stop_audio(self):
        self.player.stop()
        self.status_lbl.setText("Stopped")
        self._stop_timer()

    # ---------------- Timer ----------------
    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.status_lbl.setText("Audio finished ✓")
            self._start_timer()

    def _start_timer(self):
        self.response_ms = 0
        self.response_running = True
        self.response_lbl.setText("Response time: 00:00.000")
        self.timer.start()

    def _tick_response(self):
        if not self.response_running:
            return
        self.response_ms += 100
        m = self.response_ms // 60000
        s = (self.response_ms // 1000) % 60
        ms = self.response_ms % 1000
        self.response_lbl.setText(f"Response time: {m:02}:{s:02}.{ms:03}")

    def _stop_timer(self):
        self.response_running = False
        self.timer.stop()

    def _reset_timer(self):
        self._stop_timer()
        self.response_ms = 0
        self.response_lbl.setText("Response time: —")

    # ---------------- Result Paths ----------------
    def _sanitize_for_filename(self, s):
        s = re.sub(r"[^\w\-]+", "_", s)
        return re.sub(r"_+", "_", s).strip("_")

    def _make_results_path(self, participant_id):
        base = self.participant_folder_path if self.participant_folder_path else self.base_dir
        sn_folder = os.path.join(base, "Speech_in_Noise")
        os.makedirs(sn_folder, exist_ok=True)

        task_folder = os.path.join(sn_folder, "CaST_word")
        os.makedirs(task_folder, exist_ok=True)

        safe = self._sanitize_for_filename(participant_id)
        return os.path.join(task_folder, f"CaST_word_{safe}.csv")

    # ---------------- Save Results ----------------
    def _write_results(self):

        # update current row
        self.rows[self.idx]["Correct/Wrong"] = "1" if self.word_check.isChecked() else "0"

        # write per-item file
        with open(self.results_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(f"# Participant: {self.participant_id}\n")
            writer = csv.DictWriter(f, fieldnames=self.csv_fieldnames)
            writer.writeheader()

            for r in self.rows:
                writer.writerow({k: r.get(k, "") for k in self.csv_fieldnames})

        # update summary
        self._update_word_summary()

    # ---------------- SUMMARY FILE ----------------
    def _get_sin_folder(self):
        base = self.participant_folder_path if self.participant_folder_path else self.base_dir
        sn_folder = os.path.join(base, "Speech_in_Noise")
        os.makedirs(sn_folder, exist_ok=True)
        return sn_folder

    def _get_summary_file(self):
        safe_id = self._sanitize_for_filename(self.participant_id)
        return os.path.join(self._get_sin_folder(), f"{safe_id}_SIN_Summary.csv")

    def _update_word_summary(self):

        # count correct words for each SNR
        counts = {}
        for r in self.rows:
            snr = r.get("SNR", "")
            if not snr:
                continue
            if r.get("Correct/Wrong", "") == "1":
                counts[snr] = counts.get(snr, 0) + 1

        summary_path = self._get_summary_file()
        snr_list = ["25", "20", "15", "10", "5", "0"]
        fieldnames = ["SNR", "Non-words", "Words", "HINT", "CST"]
        rows = []

        # load if exists
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))

        # ensure all rows exist
        existing = {row["SNR"]: row for row in rows}
        for snr in snr_list:
            if snr not in existing:
                new_row = {fn: "" for fn in fieldnames}
                new_row["SNR"] = snr
                rows.append(new_row)
                existing[snr] = new_row

        # update Words column only
        for snr in snr_list:
            existing[snr]["Words"] = str(counts.get(snr, 0))

        # save file
        with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    # ---------------- Back to menu ----------------
    def _go_back_to_sin(self):
        self._write_results()
        self._stop_audio()
        try:
            from task_speech_in_noise.sin_menu import SpeechInNoiseMenuWindow
            w = SpeechInNoiseMenuWindow(
                participant_id=self.participant_id,
                participant_folder_path=self.participant_folder_path
            )
            w.setGeometry(self.geometry())
            w.show()
            self.close()
        except Exception:
            self.close()


# Standalone test
def main():
    app = QApplication(sys.argv)
    w = CaSTWordTask()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
