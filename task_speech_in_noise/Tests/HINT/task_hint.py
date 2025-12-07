# task_speech_in_noise/Tests/HINT/task_hint.py
import sys, os, glob, csv, re
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QStackedLayout, QFrame, QGridLayout, QCheckBox, QScrollArea, QWidget as QtWidget
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

INSTR_TEXT = (
    "Read this to the participant:\n"
    "In this part (HINT), you will hear sentences in noise.\n"
    "After each one, please repeat exactly what you heard.\n"
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

class HintTask(QWidget):
    """
    HINT task: one window, two pages (Instruction <-> Player) via QStackedLayout.
    - Reads HINT_List.csv: uses columns (SNR, Sentence, Key Words, Correct Key Words, ...)
    - Plays .wav files from ./Audio (numeric/natural order) unless a filename column exists in CSV.
    - Shows SNR, Sentence, Key Words (checkboxes).
    - Saves checked words into 'Correct Key Words' per item for the current participant.
    """
    def __init__(self, participant_id=None, participant_folder_path=None, parent=None):
        super().__init__(parent)
        self.participant_id = participant_id or "UNKNOWN"
        self.participant_folder_path = participant_folder_path

        self.setWindowTitle("HINT")
        self.setStyleSheet("background-color: #f6f6f6;")
        self.resize(1200, 800)

        # --- paths ---
        self.base_dir  = os.path.dirname(__file__)
        self.audio_dir = os.path.join(self.base_dir, "Audio")
        self.csv_path  = os.path.join(self.base_dir, "HINT_List.csv")

        # --- load data ---
        self.rows, self.headers = self._load_csv_rows(self.csv_path)
        self.audio_files = self._collect_audio_files(self.audio_dir)

        # If CSV has a filename-ish column, use it for exact mapping
        self.filename_col = self._detect_filename_col(self.rows)
        if self.filename_col:
            self.audio_files = self._files_from_csv(self.rows, self.filename_col, self.audio_dir)

        self.n = min(len(self.rows), len(self.audio_files))
        self.idx = 0

        # keyword checkbox state cache: idx -> list[bool]
        self.keyword_states = {}

        # output file path (under participant folder if available)
        self.results_path = self._make_results_path(self.participant_id)

        # --- stack pages ---
        self.stack = QStackedLayout(self)
        self.page_instr  = self._build_instruction_page()
        self.page_player = self._build_player_page()
        self.stack.addWidget(self.page_instr)
        self.stack.addWidget(self.page_player)
        self.stack.setCurrentIndex(0)

    # ==================== Instruction Page ====================
    def _build_instruction_page(self):
        page = QFrame(self)
        root = QVBoxLayout(page)
        root.setContentsMargins(24, 24, 24, 24)
        root.addStretch()

        title = QLabel("HINT", page)
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

    # ==================== Player Page ====================
    def _build_player_page(self):
        page = QFrame(self)
        self.root_player = QVBoxLayout(page)
        self.root_player.setContentsMargins(24, 24, 24, 24)
        self.root_player.addStretch()

        title = QLabel("HINT", page)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setStyleSheet("color:#2c3e50;")
        self.root_player.addWidget(title)

        # --- Top-left area: Skip hint + SNR summary ---
        summary_row = QHBoxLayout()

        # NEW: red boxed skip-hint label (hidden by default)
        self.skip_hint_lbl = QLabel("", page)
        self.skip_hint_lbl.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.skip_hint_lbl.setStyleSheet("""
            QLabel {
                color: #c0392b;
                background: #fdecea;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 6px 10px;
            }
        """)
        self.skip_hint_lbl.hide()

        self.snr_summary_lbl = QLabel("", page)
        self.snr_summary_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.snr_summary_lbl.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.snr_summary_lbl.setStyleSheet("color:#2c3e50;")
        self.snr_summary_lbl.setWordWrap(False)

        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        left_col.addWidget(self.skip_hint_lbl, alignment=Qt.AlignmentFlag.AlignLeft)
        left_col.addWidget(self.snr_summary_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        summary_row.addLayout(left_col)
        summary_row.addStretch()
        self.root_player.addLayout(summary_row)

        self.counter_lbl = QLabel("", page)
        self.counter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.counter_lbl.setStyleSheet("color:#2c3e50;")
        self.root_player.addWidget(self.counter_lbl)

        # --- SNR label ---
        self.snr_lbl = QLabel("", page)
        self.snr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.snr_lbl.setFont(QFont("Arial", 18, QFont.Weight.DemiBold))
        self.snr_lbl.setStyleSheet("color:#2c3e50;")
        self.root_player.addWidget(self.snr_lbl)

        # --- Sentence text (from CSV) ---
        self.sentence_lbl = QLabel("", page)
        self.sentence_lbl.setWordWrap(True)
        self.sentence_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sentence_lbl.setFont(QFont("Arial", 20))
        self.sentence_lbl.setStyleSheet("""
            QLabel {
                color: black; background: white;
                border: 2px solid #e0e0e0; border-radius: 20px;
                padding: 28px; margin: 24px;
            }
        """)
        self.root_player.addWidget(self.sentence_lbl)

        # --- Key Words with checkboxes ---
        self.kw_container = QFrame(page)
        self.kw_container.setStyleSheet("""
            QFrame {
                background: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px;
            }
        """)
        kw_vbox = QVBoxLayout(self.kw_container)

        header = QHBoxLayout()
        kw_title = QLabel("Key Words", self.kw_container)
        kw_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        kw_title.setStyleSheet("color:#2c3e50;")
        header.addWidget(kw_title)
        header.addStretch()
        self.btn_select_all = QPushButton("Select All", self.kw_container)
        self.btn_select_all.setFixedSize(120, 40)
        self.btn_select_all.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_select_all.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
                color: #2c3e50; border: 2px solid #d0d0d0; border-radius: 10px;
                padding: 6px; font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #fafafa, stop:1 #e8e8e8);
                border: 2px solid #bfc6cc;
            }
        """)
        self.btn_select_all.clicked.connect(self._select_all_keywords)
        header.addWidget(self.btn_select_all)
        kw_vbox.addLayout(header)

        self.kw_grid_host = QtWidget(self.kw_container)
        self.kw_grid_host.setStyleSheet("""
            QCheckBox { color: black; font-weight: 600; }
            QCheckBox::indicator { width: 20px; height: 20px; }
            QCheckBox::indicator:unchecked {
                border: 2px solid #7f8c8d; background: #ffffff; border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background: #2c3e50; border: 2px solid #2c3e50; border-radius: 4px;
            }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #34495e; }
            QCheckBox::indicator:checked:hover  { background: #34495e; border: 2px solid #34495e; }
        """)
        self.kw_grid = QGridLayout(self.kw_grid_host)
        self.kw_grid.setContentsMargins(12, 6, 12, 12)
        self.kw_grid.setHorizontalSpacing(24)
        self.kw_grid.setVerticalSpacing(8)
        kw_vbox.addWidget(self.kw_grid_host)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.kw_container)
        scroll.setFixedHeight(180)
        self.root_player.addWidget(scroll)

        # --- status + response timer ---
        self.status_lbl = QLabel(" ", page)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color:#2c3e50;")
        self.root_player.addWidget(self.status_lbl)

        self.response_lbl = QLabel("Response time: —", page)
        self.response_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_lbl.setFont(QFont("Arial", 16))
        self.response_lbl.setStyleSheet("color:#2c3e50;")
        self.root_player.addWidget(self.response_lbl)

        # --- Controls ---
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
        self.root_player.addLayout(ctrl)

        # Bottom
        bottom = QHBoxLayout()
        back_menu = QPushButton("Back to SiN Menu", page)
        back_menu.setFixedSize(280, 64)
        back_menu.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        back_menu.setStyleSheet(button_style())
        back_menu.clicked.connect(self._go_back_to_sin)
        bottom.addStretch(); bottom.addWidget(back_menu); bottom.addStretch()
        self.root_player.addLayout(bottom)

        self.root_player.addStretch()

        # --- player/timer setup ---
        self.player = QMediaPlayer(page)
        self.audio_out = QAudioOutput(page)
        self.player.setAudioOutput(self.audio_out)
        self.audio_out.setVolume(1.0)

        self.player.mediaStatusChanged.connect(self._on_media_status)

        self.response_timer = QTimer(page)
        self.response_timer.setInterval(100)
        self.response_timer.timeout.connect(self._on_response_tick)
        self.response_running = False
        self.response_ms = 0

        # init UI with first item
        self._refresh_ui_for_index()
        return page

    # ==================== data helpers ====================
    def _load_csv_rows(self, csv_path):
        rows = []
        headers = []
        if not os.path.exists(csv_path):
            return rows, headers
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            raw_headers = next(reader, [])
            headers = [("Sentence" if h.strip().lower() == "sentence" else h.strip()) for h in raw_headers]
            idx2h = {i: h for i, h in enumerate(headers)}
            for cells in reader:
                if not any(str(c).strip() for c in cells):
                    continue
                row = {}
                for i, c in enumerate(cells):
                    h = idx2h.get(i, f"col{i}")
                    row[h] = c.strip()
                rows.append(row)
        for r in rows:
            if "Correct Key Words" not in r:
                r["Correct Key Words"] = ""
        if "Correct Key Words" not in headers:
            headers.append("Correct Key Words")
        return rows, headers

    def _detect_filename_col(self, rows):
        if not rows:
            return None
        keys = {k.lower().strip() for k in rows[0].keys()}
        for cand in ["filename", "file", "audio", "wav", "path"]:
            if cand in keys:
                for k in rows[0].keys():
                    if k.lower().strip() == cand:
                        return k
        return None

    def _files_from_csv(self, rows, key, audio_dir):
        out = []
        for r in rows:
            fn = r.get(key, "").strip()
            if not fn:
                out.append(None); continue
            if not os.path.isabs(fn):
                fn = os.path.join(audio_dir, fn)
            out.append(fn)
        return out

    def _collect_audio_files(self, audio_dir):
        files = glob.glob(os.path.join(audio_dir, "*.wav"))
        def key(p):
            name = os.path.basename(p)
            m = re.search(r"\d+", name)
            if m:
                return (int(m.group()), name)
            return (float("inf"), name)
        return sorted(files, key=key)

    # ==================== UI/logic helpers ====================
    def _parse_keywords(self, kw_text):
        if not kw_text:
            return []
        parts = re.split(r"[;,]", kw_text)
        tokens = []
        for t in parts:
            s = t.strip()
            s = re.sub(r"^[\-–—\s]+|[\-–—\s]+$", "", s)
            if s:
                tokens.append(s)
        return tokens

    def _build_keywords_area(self, keywords):
        while self.kw_grid.count():
            item = self.kw_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.keyword_checks = []
        cols = 2
        for i, word in enumerate(keywords):
            chk = QCheckBox(word, self.kw_grid_host)
            chk.setFont(QFont("Arial", 14))
            chk.toggled.connect(self._update_snr_summary)  # live update
            r, c = divmod(i, cols)
            self.kw_grid.addWidget(chk, r, c, Qt.AlignmentFlag.AlignLeft)
            self.keyword_checks.append(chk)

    def _apply_saved_keywords_state(self):
        states = self.keyword_states.get(self.idx)
        if states and len(states) == len(self.keyword_checks):
            for chk, st in zip(self.keyword_checks, states):
                chk.setChecked(st)

    def _save_current_keywords_state(self):
        if not hasattr(self, "keyword_checks"):
            return
        self.keyword_states[self.idx] = [chk.isChecked() for chk in self.keyword_checks]

    def _refresh_ui_for_index(self):
        if self.n == 0:
            self.counter_lbl.setText("No items")
            self.snr_lbl.setText("SNR: —")
            self.sentence_lbl.setText("—")
            self.status_lbl.setText(" ")
            self._reset_response_timer()
            self._build_keywords_area([])
            self._update_snr_summary()
            return

        self.counter_lbl.setText(f"Item {self.idx+1} of {self.n}")
        row = self.rows[self.idx]

        snr_raw = row.get("SNR", "")
        snr_txt = f"SNR: {snr_raw} dB" if str(snr_raw).strip() else "SNR: —"
        self.snr_lbl.setText(snr_txt)

        sentence = row.get("Sentence", row.get("Sentence ", ""))
        self.sentence_lbl.setText(sentence)

        kw_text = row.get("Key Words", "")
        keywords = self._parse_keywords(kw_text)
        self._build_keywords_area(keywords)
        self._apply_saved_keywords_state()

        self.player.stop()
        self._reset_response_timer()
        self._update_snr_summary()

    # Select All handler
    def _select_all_keywords(self):
        if not hasattr(self, "keyword_checks"):
            return
        for chk in self.keyword_checks:
            chk.setChecked(True)
        self._save_current_keywords_state()
        self._update_snr_summary()

    # compute & render SNR summary (up to current item, inclusive)
    def _update_snr_summary(self):
        if self.n == 0:
            self.snr_summary_lbl.setText("")
            self.skip_hint_lbl.hide()
            return

        totals, corrects, order = {}, {}, []

        for i in range(0, self.idx + 1):
            row = self.rows[i]
            snr = str(row.get("SNR", "")).strip() or "—"
            if snr not in totals:
                order.append(snr)
            total_k = len(self._parse_keywords(row.get("Key Words", "")))

            if i < self.idx:
                corr_k = len(self._parse_keywords(row.get("Correct Key Words", "")))
            else:
                corr_k = sum(1 for chk in getattr(self, "keyword_checks", []) if chk.isChecked())

            totals[snr]   = totals.get(snr, 0) + total_k
            corrects[snr] = corrects.get(snr, 0) + corr_k

        lines = []
        for snr in order:
            tot = totals[snr]
            cor = corrects.get(snr, 0)
            pct = int(round((cor / tot) * 100)) if tot > 0 else 0
            lines.append(f"SNR {snr}: {cor}/{tot}\u00A0({pct}%)")
        self.snr_summary_lbl.setText("\n".join(lines))

        # NEW: update skip-hint box for CURRENT SNR
        self._update_skip_hint()

    # NEW: Skip-hint logic for current SNR (first 5 sentences)
    def _update_skip_hint(self):
        if self.n == 0:
            self.skip_hint_lbl.hide()
            return

        current_row = self.rows[self.idx]
        current_snr = str(current_row.get("SNR", "")).strip() or "—"

        # indices of first five sentences for this SNR in the WHOLE list
        first5 = []
        for j, r in enumerate(self.rows):
            snr_j = str(r.get("SNR", "")).strip() or "—"
            if snr_j == current_snr:
                first5.append(j)
                if len(first5) == 5:
                    break

        if len(first5) == 0:
            self.skip_hint_lbl.hide()
            return

        # only show decision AFTER all of those first N (<=5) have been reached
        # i.e., if we haven't reached the last index among first5, hide for now
        if self.idx <= first5[-1]:
            self.skip_hint_lbl.hide()
            return

        # count total correct KEY WORDS across those first5 items (up to current)
        correct_words = 0
        for j in first5:
            if j < self.idx:
                corr_k = len(self._parse_keywords(self.rows[j].get("Correct Key Words", "")))
            elif j == self.idx:
                corr_k = sum(1 for chk in getattr(self, "keyword_checks", []) if chk.isChecked())
            else:
                corr_k = 0
            correct_words += corr_k

        if correct_words < 2:
            self.skip_hint_lbl.setText("You can skip this level")
            self.skip_hint_lbl.show()
        else:
            self.skip_hint_lbl.hide()

    # ==================== saving helpers ====================
    def _sanitize_for_filename(self, s: str) -> str:
        s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
        return re.sub(r"_+", "_", s).strip("_")

    def _make_results_path(self, participant_id: str) -> str:
        # Correct location: Speech_in_Noise/HINT
        base_out = self.participant_folder_path if self.participant_folder_path else self.base_dir
        out_dir = os.path.join(base_out, "Speech_in_Noise", "HINT")
        os.makedirs(out_dir, exist_ok=True)

        safe_id = self._sanitize_for_filename(participant_id or "UNKNOWN")
        return os.path.join(out_dir, f"HINT_List_{safe_id}.csv")


    def _update_correct_keywords_for_current(self):
        if not hasattr(self, "keyword_checks") or self.n == 0:
            return
        checked = [chk.text() for chk in self.keyword_checks if chk.isChecked()]
        row = self.rows[self.idx]
        row["Correct Key Words"] = ", ".join(checked)

    def _write_results(self):
        std = ["SNR", "List Number", "Sentence Number", "Sentence", "Key Words", "Correct Key Words"]
        keys_in_rows = set()
        for r in self.rows[:self.n]:
            keys_in_rows.update(r.keys())
        headers = [h for h in std if h in keys_in_rows] + [h for h in keys_in_rows if h not in std]

        os.makedirs(os.path.dirname(self.results_path), exist_ok=True)
        with open(self.results_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(f"# Participant: {self.participant_id}\n")
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for i in range(self.n):
                r = dict(self.rows[i])
                if "Sentence" not in r and "Sentence " in r:
                    r["Sentence"] = r.pop("Sentence ")
                writer.writerow(r)

    # ==================== actions ====================
    def _start_task(self):
        if self.n == 0:
            QMessageBox.warning(self, "HINT", "No audio/text items found.")
            return
        self.stack.setCurrentIndex(1)

    def _go_prev(self):
        self._save_current_keywords_state()
        self._update_correct_keywords_for_current()
        self._write_results()
        self._update_summary_file()
        self._stop_response_timer()
        if self.idx > 0:
            self.idx -= 1
            self._refresh_ui_for_index()
        else:
            self._stop_audio()
            self.stack.setCurrentIndex(0)

    def _go_next(self):
        self._save_current_keywords_state()
        self._update_correct_keywords_for_current()
        self._write_results()
        self._update_summary_file()
        self._stop_response_timer()
        if self.idx < self.n - 1:
            self.idx += 1
            self._refresh_ui_for_index()
            self._play_current()  # Auto-play next
        else:
            QMessageBox.information(self, "HINT", "Task finished.")

    def _play_current(self):
        if self.n == 0:
            return
        self._reset_response_timer()
        self.status_lbl.setText("Playing…")
        path = self.audio_files[self.idx]
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "HINT", f"Audio file missing for item {self.idx+1}.")
            return
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.setPosition(0)
        self.player.play()

    def _stop_audio(self):
        self.player.stop()
        self.status_lbl.setText("Stopped")
        self._stop_response_timer()

    def _go_back_to_sin(self):
        self._save_current_keywords_state()
        self._update_correct_keywords_for_current()
        self._write_results()
        self._update_summary_file()
        self._stop_audio()
        from task_speech_in_noise.sin_menu import SpeechInNoiseMenuWindow
        w = SpeechInNoiseMenuWindow(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.close()

    # ==================== finish & response timer ====================
    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.status_lbl.setText("Audio finished ✓")
            self._start_response_timer()

    def _start_response_timer(self):
        self.response_ms = 0
        self.response_running = True
        self.response_lbl.setText("Response time: 00:00.000")
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




# =========== Summary File ===================
    def _update_summary_file(self):
        """Update the SIN Summary CSV with total correct keywords per SNR for HINT."""
        if not self.participant_folder_path:
            return

        summary_path = os.path.join(
            self.participant_folder_path,
            "Speech_in_Noise",
            f"{self.participant_id}_SIN_Summary.csv"
        )

        if not os.path.exists(summary_path):
            return

        # ----- count correct keywords per SNR -----
        snr_totals = {}
        for row in self.rows[:self.n]:
            snr = str(row.get("SNR", "")).strip()
            corr = len(self._parse_keywords(row.get("Correct Key Words", "")))
            snr_totals[snr] = snr_totals.get(snr, 0) + corr

        # ----- load summary -----
        import csv
        rows = []
        with open(summary_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            summary_headers = reader.fieldnames
            for r in reader:
                rows.append(r)

        # ensure column exists
        if "HINT" not in summary_headers:
            summary_headers.append("HINT")

        # fill the HINT column
        for r in rows:
            snr = r.get("SNR", "")
            if snr in snr_totals:
                r["HINT"] = snr_totals[snr]

        # write back
        with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=summary_headers)
            writer.writeheader()
            writer.writerows(rows)


# ---------- standalone test ----------
def main():
    app = QApplication(sys.argv)
    w = HintTask()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
