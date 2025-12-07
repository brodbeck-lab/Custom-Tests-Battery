# task_speech_in_noise/CaST_nonword/task_cast_nonword.py
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
    "In this part (CaST Non-word), you will hear single non-words in noise.\n"
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

class CaSTNonwordTask(QWidget):
    """
    CaST Non-word task:
    - Plays audio files in the CSV row order.
    - Audio filename is read from column 'File Name'. '.wav' is auto-appended if missing.
    - Non-word text is read from 'Non-word' and shown with a single checkbox to mark correctness.
    - Per-SNR summary is shown and updated live.
    """

    def __init__(self, participant_id=None, participant_folder_path=None, parent=None):
        super().__init__(parent)
        self.participant_id = participant_id or "UNKNOWN"
        self.participant_folder_path = participant_folder_path

        # Window / style
        self.setWindowTitle("CaST Non-word")
        self.setStyleSheet("background-color: #f6f6f6;")
        self.resize(1100, 720)

        # Paths
        self.base_dir  = os.path.dirname(__file__)
        self.csv_path  = os.path.join(self.base_dir, "CaST_nonword_list.csv")
        self.audio_dir = os.path.join(self.base_dir, "Audio")

        # Data
        self.rows, self.csv_fieldnames = self._load_csv_rows(self.csv_path)
        self.n = len(self.rows)
        self.idx = 0

        # Audio (create before building pages)
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.audio_out.setVolume(1.0)
        self.player.mediaStatusChanged.connect(self._on_media_status)

        # Response timer (create before building pages)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick_response)
        self.response_running = False
        self.response_ms = 0

        # Results path
        self.results_path = self._make_results_path(self.participant_id)

        # Pages
        self.stack = QStackedLayout(self)
        self.page_instr  = self._build_instruction_page()
        self.page_player = self._build_player_page()
        self.stack.addWidget(self.page_instr)
        self.stack.addWidget(self.page_player)
        self.stack.setCurrentIndex(0)

    # ============== Instruction Page ==============
    def _build_instruction_page(self):
        page = QFrame(self)
        root = QVBoxLayout(page)
        root.setContentsMargins(24, 24, 24, 24)
        root.addStretch()

        title = QLabel("CaST Non-word", page)
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
        back_btn.setFixedSize(280, 64)
        back_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        back_btn.setStyleSheet(button_style())
        back_btn.clicked.connect(self._go_back_to_sin)

        start_btn = QPushButton("Start", page)
        start_btn.setFixedSize(200, 64)
        start_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        start_btn.setStyleSheet(button_style())
        start_btn.clicked.connect(self._start_task)

        row.addStretch(); row.addWidget(back_btn); row.addSpacing(20); row.addWidget(start_btn); row.addStretch()
        root.addLayout(row)
        root.addStretch()
        return page

    # ============== Player Page ==============
    def _build_player_page(self):
        page = QFrame(self)
        root = QVBoxLayout(page)
        root.setContentsMargins(24, 24, 24, 24)
        root.addStretch()

        title = QLabel("CaST Non-word", page)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setStyleSheet("color:#2c3e50;")
        root.addWidget(title)

        # Top row: SNR summary only
        top_row = QHBoxLayout()
        self.snr_summary_lbl = QLabel("", page)
        self.snr_summary_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.snr_summary_lbl.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.snr_summary_lbl.setStyleSheet("color:#2c3e50;")
        self.snr_summary_lbl.setWordWrap(False)
        top_row.addWidget(self.snr_summary_lbl, alignment=Qt.AlignmentFlag.AlignLeft)
        top_row.addStretch()
        root.addLayout(top_row)

        # Counter
        self.counter_lbl = QLabel("", page)
        self.counter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.counter_lbl.setStyleSheet("color:#2c3e50;")
        root.addWidget(self.counter_lbl)

        # SNR label (per-item)
        self.snr_lbl = QLabel("", page)
        self.snr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.snr_lbl.setFont(QFont("Arial", 18, QFont.Weight.DemiBold))
        self.snr_lbl.setStyleSheet("color:#2c3e50;")
        root.addWidget(self.snr_lbl)

        # Non-word area
        self.word_lbl = QLabel("—", page)
        self.word_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_lbl.setWordWrap(True)
        self.word_lbl.setFont(QFont("Arial", 28))
        self.word_lbl.setStyleSheet("""
            QLabel {
                color: black; background: white;
                border: 2px solid #e0e0e0; border-radius: 20px;
                padding: 28px; margin: 24px;
            }
        """)
        root.addWidget(self.word_lbl)

        # Single checkbox
        row = QHBoxLayout()
        row.addStretch()
        self.word_check = QCheckBox("Correct", page)
        self.word_check.setFont(QFont("Arial", 16))
        self.word_check.setStyleSheet("""
            QCheckBox { color: black; font-weight: 600; }
            QCheckBox::indicator { width: 22px; height: 22px; }
            QCheckBox::indicator:unchecked {
                border: 2px solid #2c3e50; background: #ffffff; border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background: #2c3e50; border: 2px solid #2c3e50; border-radius: 4px;
            }
        """)
        self.word_check.stateChanged.connect(self._on_check_toggled)
        self.word_check.stateChanged.connect(self._update_snr_summary)  # live summary update
        row.addWidget(self.word_check)
        row.addStretch()
        root.addLayout(row)

        # Status + Response
        self.status_lbl = QLabel(" ", page)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color:#2c3e50;")
        root.addWidget(self.status_lbl)

        self.response_lbl = QLabel("Response time: —", page)
        self.response_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_lbl.setFont(QFont("Arial", 16))
        self.response_lbl.setStyleSheet("color:#2c3e50;")
        root.addWidget(self.response_lbl)

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

        self.btn_next = QPushButton("Play Next", page)
        self.btn_next.setFixedSize(160, 64)
        self.btn_next.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.btn_next.setStyleSheet(button_style())
        self.btn_next.clicked.connect(self._go_next)

        ctrl.addStretch()
        for b in (self.btn_back, self.btn_play, self.btn_stop, self.btn_next):
            ctrl.addWidget(b); ctrl.addSpacing(16)
        ctrl.addStretch()
        root.addLayout(ctrl)

        # Back to menu
        bottom = QHBoxLayout()
        back_menu = QPushButton("Back to SiN Menu", page)
        back_menu.setFixedSize(280, 64)
        back_menu.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        back_menu.setStyleSheet(button_style())
        back_menu.clicked.connect(self._go_back_to_sin)
        bottom.addStretch(); bottom.addWidget(back_menu); bottom.addStretch()
        root.addLayout(bottom)

        root.addStretch()

        # Initialize first item view
        self._refresh_ui_for_index()
        return page

    # ============== Data helpers ==============
    def _load_csv_rows(self, csv_path):
        """
        Load rows preserving order.
        Expect columns like: 'SNR', 'Number', 'Non-word', 'File Name', 'Correct/Wrong'.
        Do NOT normalize header names to keep them identical to the original file.
        """
        if not os.path.exists(csv_path):
            QMessageBox.critical(self, "CaST Non-word", f"CSV not found:\n{csv_path}")
            return [], []

        rows = []
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            for r in reader:
                # strip whitespace from keys and values, but keep header text exactly
                row = {}
                for k, v in r.items():
                    key = (k or "").strip()
                    val = (v or "").strip()
                    row[key] = val

                # ensure File Name is populated consistently
                fn = row.get("File Name") or row.get("Filename") or row.get("File") \
                     or row.get("Audio") or row.get("Wav") or row.get("Path") or ""
                row["File Name"] = fn.strip()

                rows.append(row)

        return rows, fieldnames

    def _resolve_audio_path(self, row):
        """Resolve audio path using 'File Name' under Audio/ (auto add .wav if missing)."""
        fn = (row.get("File Name") or "").strip()
        if not fn:
            return ""  # nothing provided in CSV
        if not fn.lower().endswith(".wav"):
            fn = fn + ".wav"
        if os.path.isabs(fn):
            return fn
        return os.path.join(self.audio_dir, fn)

    # ============== UI / logic ==============
    def _refresh_ui_for_index(self):
        if self.n == 0:
            self.counter_lbl.setText("No items")
            self.snr_lbl.setText("SNR: —")
            self.word_lbl.setText("—")
            self.word_check.setChecked(False)
            self.status_lbl.setText(" ")
            self._reset_timer()
            self._update_snr_summary()
            return

        self.counter_lbl.setText(f"Item {self.idx+1} of {self.n}")
        row = self.rows[self.idx]

        snr_raw = row.get("SNR", "") or row.get("Snr", "")
        snr_txt = f"SNR: {snr_raw} dB" if str(snr_raw).strip() else "SNR: —"
        self.snr_lbl.setText(snr_txt)

        word = row.get("Non-word", "") or row.get("Nonword", "") or "—"
        self.word_lbl.setText(word)

        checked_val = (row.get("Correct/Wrong", "") or "").strip().lower()
        checked = checked_val in {"1", "true", "yes", "y", "t"}
        self.word_check.blockSignals(True)
        self.word_check.setChecked(checked)
        self.word_check.blockSignals(False)

        self.player.stop()
        self._reset_timer()
        self._update_snr_summary()

    def _on_check_toggled(self, _state):
        if self.n == 0:
            return
        self.rows[self.idx]["Correct/Wrong"] = "1" if self.word_check.isChecked() else "0"

    def _update_snr_summary(self):
        """Aggregate per-SNR correctness up to current index (each item = 1)."""
        if self.n == 0:
            self.snr_summary_lbl.setText("")
            return

        totals, corrects, order = {}, {}, []

        for i in range(0, self.idx + 1):
            row = self.rows[i]
            snr = str(row.get("SNR", "") or row.get("Snr", "")).strip() or "—"
            if snr not in totals:
                order.append(snr)
            totals[snr] = totals.get(snr, 0) + 1

            if i < self.idx:
                corr_val = (row.get("Correct/Wrong", "") or "").strip().lower()
                corr = corr_val in {"1", "true", "yes", "y", "t"}
            else:
                corr = self.word_check.isChecked()

            corrects[snr] = corrects.get(snr, 0) + (1 if corr else 0)

        lines = []
        for snr in order:
            tot = totals[snr]
            cor = corrects.get(snr, 0)
            pct = int(round((cor / tot) * 100)) if tot > 0 else 0
            lines.append(f"SNR {snr}: {cor}/{tot}\u00A0({pct}%)")
        self.snr_summary_lbl.setText("\n".join(lines))

    # ============== Actions ==============
    def _start_task(self):
        if self.n == 0:
            QMessageBox.warning(self, "CaST Non-word", "No items found.")
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
            self._play_current()  # auto-play next
        else:
            QMessageBox.information(self, "CaST Non-word", "Task finished.")

    def _play_current(self):
        if self.n == 0:
            return
        path = self._resolve_audio_path(self.rows[self.idx])
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "CaST Non-word", f"Audio not found:\n{path or '(empty filename)'}")
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

    # ============== Timer ==============
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
        minutes = self.response_ms // 60000
        seconds = (self.response_ms // 1000) % 60
        millis  = self.response_ms % 1000
        self.response_lbl.setText(f"Response time: {minutes:02}:{seconds:02}.{millis:03}")

    def _stop_timer(self):
        if self.response_running:
            self.response_running = False
        self.timer.stop()

    def _reset_timer(self):
        self._stop_timer()
        self.response_ms = 0
        self.response_lbl.setText("Response time: —")

    # ============== Results ==============
    def _sanitize_for_filename(self, s: str) -> str:
        s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
        return re.sub(r"_+", "_", s).strip("_")

    def _make_results_path(self, participant_id: str) -> str:
        base = self.participant_folder_path if self.participant_folder_path else self.base_dir

        sn_folder = os.path.join(base, "Speech_in_Noise")
        os.makedirs(sn_folder, exist_ok=True)

        task_folder = os.path.join(sn_folder, "CaST_nonword")
        os.makedirs(task_folder, exist_ok=True)

        safe_id = self._sanitize_for_filename(participant_id or "UNKNOWN")
        return os.path.join(task_folder, f"CaST_nonword_{safe_id}.csv")

    def _write_results(self):
        if self.n == 0:
            return

        # update current item response according to checkbox
        self.rows[self.idx]["Correct/Wrong"] = "1" if self.word_check.isChecked() else "0"

        # write output CSV with identical header names as original
        os.makedirs(os.path.dirname(self.results_path), exist_ok=True)
        with open(self.results_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(f"# Participant: {self.participant_id}\n")
            writer = csv.DictWriter(f, fieldnames=self.csv_fieldnames)
            writer.writeheader()

            for r in self.rows:
                # make sure we don't pass extra keys beyond original headers
                filtered = {k: r.get(k, "") for k in self.csv_fieldnames}
                writer.writerow(filtered)

        
        # Summary File
        self._update_nonword_summary()



    # =============Summary File================
    def _get_sin_folder(self):
        """Common Speech_in_Noise folder."""
        base = self.participant_folder_path if self.participant_folder_path else self.base_dir
        sn_folder = os.path.join(base, "Speech_in_Noise")
        os.makedirs(sn_folder, exist_ok=True)
        return sn_folder

    def _get_summary_file(self):
        """Path for <ParticipantID>_SIN_Summary.csv"""
        safe_id = self._sanitize_for_filename(self.participant_id or "UNKNOWN")
        return os.path.join(self._get_sin_folder(), f"{safe_id}_SIN_Summary.csv")

    def _update_nonword_summary(self):
        """
        Update only the Non-words column in the SIN summary file.
        The file has rows for SNR = 25,20,15,10,5,0
        """
        # --- Step 1: count correct answers per SNR ---
        counts = {}
        for r in self.rows:
            snr = (r.get("SNR") or "").strip()
            if snr == "":
                continue
            correct = (r.get("Correct/Wrong", "").strip().lower() in {"1", "true", "yes", "y", "t"})
            if correct:
                counts[snr] = counts.get(snr, 0) + 1

        # --- Step 2: load or create summary file ---
        summary_path = self._get_summary_file()
        snr_list = ["25", "20", "15", "10", "5", "0"]
        fieldnames = ["SNR", "Non-words", "Words", "HINT", "CST"]
        rows = []

        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = [{k: v for k, v in row.items()} for row in reader]

        # ensure all SNR rows exist
        existing = {row["SNR"]: row for row in rows}
        for snr in snr_list:
            if snr not in existing:
                new_row = {fn: "" for fn in fieldnames}
                new_row["SNR"] = snr
                rows.append(new_row)
                existing[snr] = new_row

        # --- Step 3: update ONLY Non-words column ---
        for snr in snr_list:
            existing[snr]["Non-words"] = str(counts.get(snr, 0))

        # --- Step 4: write back ---
        with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)




    # ============== Back to menu ==============
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

# ---------- Standalone test ----------
def main():
    app = QApplication(sys.argv)
    w = CaSTNonwordTask()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
