import os
import random
import time
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QFrame, QGridLayout, QSpinBox, QDoubleSpinBox
)

# ---- Crash recovery integration ----
from crash_recovery_system.task_state_saver import TaskStateMixin
from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager

# ---- Modular data saver (separate file) ----
try:
    from .data_saver import save_auditory_stroop_data
except Exception:
    try:
        from task_auditory_stroop.data_saver import save_auditory_stroop_data
    except Exception:
        save_auditory_stroop_data = None


# ---------------- Defaults for configuration ----------------
DEFAULT_PRACTICE_TRIALS = 6
DEFAULT_MAIN_TRIALS = 24
DEFAULT_ITI_MS = 1000
DEFAULT_VOLUME = 0.9


class AuditoryStroopTask(TaskStateMixin, QWidget):
    """
    Auditory Stroop Task:
      - Participant identifies the VOICE GENDER (Male/Female) while ignoring the spoken word.
      - Two parts: Practice, then Main.
      - Stimuli are WAV files named with tokens like: daad1M2.wav, maam1F2.wav, etc.
        We infer the expected gender from 'M'/'F' in the filename.
    """

    # ---- Stimulus pool (update if you add/remove files) ----
    BASE_STIMULI = [
        "task_auditory_stroop/stimuli/daad1M2.wav",
        "task_auditory_stroop/stimuli/daad2F1.wav",
        "task_auditory_stroop/stimuli/maam1F2.wav",
        "task_auditory_stroop/stimuli/maam1M1.wav",
        "task_auditory_stroop/stimuli/nooz1F1.wav",
        "task_auditory_stroop/stimuli/nooz2M2.wav",
    ]

    def __init__(self, x_pos, y_pos, participant_id, participant_folder_path, recovery_mode=False):
        # Ensure a session manager exists BEFORE super().__init__ to keep the mixin happy
        if not get_session_manager() and participant_id and participant_folder_path:
            initialize_session_manager(participant_id, participant_folder_path)

        # Single MRO-safe init: TaskStateMixin -> QWidget
        super().__init__()

        # ---- Guard: participant info ----
        if not participant_id or not participant_folder_path:
            QMessageBox.critical(self, "Missing Participant Information",
                                 "Cannot start Auditory Stroop task.\n\n"
                                 "Please go back and save the biodata form.")
            self.close()
            return
        if not os.path.exists(participant_folder_path):
            QMessageBox.critical(self, "Participant Folder Missing",
                                 "Participant folder not found.\n\n"
                                 "Please go back and save the biodata form first.")
            self.close()
            return

        # ---- Window size & style (match Selection Menu: 1370 × 960) ----
        try:
            from PyQt6.QtWidgets import QApplication
            if x_pos is None or y_pos is None:
                screen = QApplication.primaryScreen().geometry()
                w, h = 1370, 960
                x_pos = (screen.width() - w) // 2
                y_pos = (screen.height() - h) // 2
            self.setGeometry(x_pos, y_pos, 1370, 960)
        except Exception:
            self.resize(1370, 960)

        self.setWindowTitle("Auditory Stroop Task")
        self.setStyleSheet("background-color: #f6f6f6;")

        # ---- Session / recovery registration ----
        session_manager = get_session_manager()
        if session_manager:
            session_manager.session_data['current_task'] = 'Auditory Stroop Task'

        # ---- Core state ----
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        self.recovery_mode = recovery_mode

        self.trial_data = []
        self.current_part = 0          # 0 = practice, 1 = main
        self.current_index = 0
        self.task_completed = False

        self.stimulus_onset_time = None
        self.response_time = None
        self.stimulus = None

        self.parts = None               # built after configuration
        self.task_config = {}           # filled by configuration UI

        # ---- Build shell UI & audio ----
        self._build_ui_shell()
        self.sound = QSoundEffect()
        self.sound.setVolume(DEFAULT_VOLUME)

        # ---- Recovery path or configuration ----
        self.recovery_data = None
        if recovery_mode and session_manager:
            st = session_manager.session_data.get('current_task_state', {}).get('task_specific_state', {})
            if st:
                self.recovery_data = st

        if self.recovery_data and self.recovery_data.get('stimuli_parts'):
            # Rehydrate from recovery
            self.parts = self.recovery_data['stimuli_parts']
            self.current_part = self.recovery_data.get('current_part', 0)
            self.current_index = self.recovery_data.get('current_index', 0)
            self.task_completed = self.recovery_data.get('task_completed', False)
            self.trial_data = self.recovery_data.get('trial_data', [])
            self._show_recovery_banner()
        else:
            self._show_configuration()   # << configuration first

    # ========================== UI Construction ==========================

    def _build_ui_shell(self):
        self.layout = QVBoxLayout()

        # Main display label (shared across screens)
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 20))
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)  # enable HTML (for bold, breaks, etc.)
        self.label.setStyleSheet("""
            QLabel {
                color: #2c3e50; background: white; border: 2px solid #e0e0e0;
                border-radius: 20px; padding: 40px; margin: 20px;
            }
        """)
        self.layout.addWidget(self.label)

        # Flow/Action button (instructions / start / continue)
        self.ok_button = QPushButton("OK", self)
        self.ok_button.setFont(QFont("Arial", 16))
        self._style_button(self.ok_button)
        self.ok_button.clicked.connect(self.start_part)
        self.layout.addWidget(self.ok_button)

        # Response buttons
        self.button_f = QPushButton("Female", self)
        self.button_m = QPushButton("Male", self)
        for b in (self.button_f, self.button_m):
            b.setFont(QFont("Arial", 18))
            self._style_button(b)
            b.hide()
        self.button_f.clicked.connect(lambda: self.register_response("Female"))
        self.button_m.clicked.connect(lambda: self.register_response("Male"))
        self.layout.addWidget(self.button_f)
        self.layout.addWidget(self.button_m)

        self.setLayout(self.layout)

    def _style_button(self, btn: QPushButton):
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffffff, stop:1 #f0f0f0);
                color: black; border: 2px solid #e0e0e0; border-radius: 20px;
                padding: 15px; font-size: 18px; font-weight: bold; min-width: 120px; min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #fafafa, stop:1 #e8e8e8);
                border: 2px solid #d0d0d0;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #e8e8e8, stop:1 #d8d8d8);
            }
        """)

    # ========================== Configuration ===========================

    def _show_configuration(self):
        """Config panel: practice/main counts, ITI (ms), volume."""
        self.label.setText(
            """
            <div style="text-align:center">
              <span style="font-weight:600;">Auditory Stroop - Configuration</span><br><br>
              You will identify the <b>voice gender</b> (Male/Female) while ignoring<br>
              the spoken word. Set the number of trials and timing below.
            </div>
            """
        )
        self.ok_button.hide()
        self.button_f.hide()
        self.button_m.hide()

        self.config_frame = QFrame()
        self.config_frame.setStyleSheet("""
            QFrame { background: #ffffff; border: 1px solid #ced4da; border-radius: 8px; padding: 20px; }
        """)
        grid = QGridLayout(); grid.setSpacing(14)

        # Practice/Main counts
        lbl = QLabel("Practice Trials:"); lbl.setFont(QFont("Arial", 12)); grid.addWidget(lbl, 0, 0)
        self.spin_practice = QSpinBox(); self.spin_practice.setRange(0, 200); self.spin_practice.setValue(DEFAULT_PRACTICE_TRIALS)
        grid.addWidget(self.spin_practice, 0, 1)

        lbl = QLabel("Main Trials:"); lbl.setFont(QFont("Arial", 12)); grid.addWidget(lbl, 1, 0)
        self.spin_main = QSpinBox(); self.spin_main.setRange(1, 1000); self.spin_main.setValue(DEFAULT_MAIN_TRIALS)
        grid.addWidget(self.spin_main, 1, 1)

        # Timing
        lbl = QLabel("Inter-trial Interval (ms):"); lbl.setFont(QFont("Arial", 12)); grid.addWidget(lbl, 2, 0)
        self.spin_iti = QSpinBox(); self.spin_iti.setRange(300, 5000); self.spin_iti.setValue(DEFAULT_ITI_MS)
        grid.addWidget(self.spin_iti, 2, 1)

        # Volume
        lbl = QLabel("Audio Volume:"); lbl.setFont(QFont("Arial", 12)); grid.addWidget(lbl, 3, 0)
        self.spin_vol = QDoubleSpinBox(); self.spin_vol.setRange(0.1, 1.0); self.spin_vol.setSingleStep(0.1); self.spin_vol.setValue(DEFAULT_VOLUME)
        grid.addWidget(self.spin_vol, 3, 1)

        self.config_frame.setLayout(grid)
        self.layout.addWidget(self.config_frame)

        # Start button
        self.start_button = QPushButton("Start Auditory Stroop")
        self.start_button.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self._style_button(self.start_button)
        self.start_button.clicked.connect(self._apply_config_and_begin)
        self.layout.addWidget(self.start_button)

    def _apply_config_and_begin(self):
        """Read config values, build trial lists, and show instructions."""
        self.task_config = {
            "practice_trials": int(self.spin_practice.value()),
            "main_trials": int(self.spin_main.value()),
            "iti_ms": int(self.spin_iti.value()),
            "audio_volume": float(self.spin_vol.value()),
            "task_start_time": datetime.now().isoformat(),
        }
        self.sound.setVolume(self.task_config["audio_volume"])

        # Build trial lists by sampling with replacement from the base pool
        def sample_trials(n):
            return [random.choice(self.BASE_STIMULI) for _ in range(n)]

        practice_list = sample_trials(self.task_config["practice_trials"])
        main_list = sample_trials(self.task_config["main_trials"])

        # Two parts: practice then main (HTML so bold renders)
        self.parts = [
            {
                "instruction": (
                    "Practice - Identify the <b>voice gender</b> (ignore the word).<br>"
                    "Click 'Male' if the voice is a man's; 'Female' if it's a woman's."
                ),
                "test": practice_list,
            },
            {
                "instruction": (
                    "Main Task - Keep identifying the <b>voice gender</b> (ignore the word).<br>"
                    "Respond as quickly and accurately as possible."
                ),
                "test": main_list,
            },
        ]

        # Clean configuration UI away
        self.start_button.hide()
        self.config_frame.hide()

        # Reset counters and show first instruction
        self.current_part = 0
        self.current_index = 0
        self.show_instruction()

    # ============================ Recovery ==============================

    def _show_recovery_banner(self):
        recovered = len(self.trial_data)
        self.label.setText(
            f"<div style='text-align:center'>"
            f"<b>Session Restored!</b><br><br>"
            f"Recovered {recovered} completed trials.<br>"
            f"Click <b>Continue</b> to resume."
            f"</div>"
        )
        self.ok_button.setText("Continue")
        self.ok_button.show()
        self.button_f.hide()
        self.button_m.hide()

    def _get_task_specific_state(self):
        """TaskStateMixin hook: return serializable state for recovery."""
        return {
            'current_part': self.current_part,
            'current_index': self.current_index,
            'task_completed': self.task_completed,
            'trial_data': self.trial_data,
            'current_stimulus': getattr(self, 'stimulus', None),
            'stimulus_onset_time': self.stimulus_onset_time,
            'participant_id': self.participant_id,
            'participant_folder_path': self.participant_folder_path,
            'stimuli_parts': self.parts,
            'last_save_time': datetime.now().isoformat(),
            'recovery_enabled': True,
            'task_type': 'auditory_stroop'
        }

    def _safe_auto_save(self):
        """Call mixin's auto-save if available (defensive)."""
        try:
            if hasattr(self, "auto_save_state"):
                self.auto_save_state()
        except Exception:
            pass

    # ============================ Task flow =============================

    def show_instruction(self):
        self.label.setText(self.parts[self.current_part]["instruction"])
        self.ok_button.setText("Start")
        self.ok_button.show()
        self.button_f.hide()
        self.button_m.hide()

    def start_part(self):
        self.ok_button.hide()
        self.current_index = 0
        self.play_next_stimulus()

    def play_next_stimulus(self):
        self._safe_auto_save()
        if self.current_index < len(self.parts[self.current_part]["test"]):
            self.play_stimulus()
            self.label.setText("<div style='text-align:center'>Choose: <b>Female</b> or <b>Male</b></div>")
            self.button_f.show()
            self.button_m.show()
        else:
            self.advance_part()

    def play_stimulus(self):
        self.stimulus = self.parts[self.current_part]["test"][self.current_index]
        if not os.path.exists(self.stimulus):
            QMessageBox.warning(self, "File Missing", f"Could not find: {self.stimulus}")
            # Skip to next to avoid deadlock
            self.current_index += 1
            QTimer.singleShot(300, self.play_next_stimulus)
            return
        self.stimulus_onset_time = time.perf_counter()
        self.sound.setSource(QUrl.fromLocalFile(self.stimulus))
        self.sound.play()

    def register_response(self, response):
        if self.stimulus_onset_time is None:
            return

        self.response_time = time.perf_counter()
        rt = (self.response_time - self.stimulus_onset_time)

        rec = {
            'trial_number': len(self.trial_data) + 1,
            'part': self.current_part,
            'trial_in_part': self.current_index,
            'stimulus_file': os.path.basename(self.stimulus),
            'stimulus_path': self.stimulus,
            'stimulus_onset_time': self.stimulus_onset_time,
            'response_time': self.response_time,
            'reaction_time_seconds': rt,
            'reaction_time_ms': rt * 1000,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'participant_id': self.participant_id,
            'expected_gender': self._extract_gender_from_filename(self.stimulus),
            'correct_response': self._is_response_correct(self.stimulus, response),
        }
        self.trial_data.append(rec)
        self.button_f.hide()
        self.button_m.hide()
        self.current_index += 1

        iti = int(self.task_config.get("iti_ms", DEFAULT_ITI_MS))
        QTimer.singleShot(iti, self.play_next_stimulus)

    # ---------------------- Parsing helpers ----------------------

    def _extract_gender_from_filename(self, filename):
        base = os.path.basename(filename)
        if 'M' in base:
            return 'Male'
        if 'F' in base:
            return 'Female'
        return 'Unknown'

    def _is_response_correct(self, stimulus_file, response):
        return response == self._extract_gender_from_filename(stimulus_file)

    # -------------------- Part transitions -----------------------

    def advance_part(self):
        self.current_part += 1
        if self.current_part < len(self.parts):
            self.current_index = 0
            self.show_instruction()
        else:
            self.task_completed = True
            self._safe_auto_save()
            self.show_completion()

    # ===================== Completion & Save =====================

    def show_completion(self):
        total = len(self.trial_data)
        correct = sum(1 for t in self.trial_data if t['correct_response'])
        acc = (correct / total * 100) if total else 0.0
        avg_rt = (sum(t['reaction_time_ms'] for t in self.trial_data) / total) if total else 0.0

        saved = self.save_trial_data()

        text = (
            "<div style='text-align:center'>"
            "<b>Auditory Stroop Task Complete!</b><br><br>"
            f"Total trials: {total}<br>"
            f"Correct responses: {correct}/{total}<br>"
            f"Accuracy: {acc:.1f}%<br>"
            f"Average reaction time: {avg_rt:.0f} ms<br><br>"
            f"{'Data saved successfully.' if saved else '<span style=\"color:#c00\">WARNING: Data save failed.</span>'}"
            "</div>"
        )
        self.label.setText(text)

        # Hide response buttons on completion
        self.button_f.hide()
        self.button_m.hide()

        self.show_main_menu_button()

    def save_trial_data(self):
        if not self.participant_folder_path or save_auditory_stroop_data is None:
            return False

        cfg = dict(self.task_config)
        cfg.update({
            'task_version': '2.0',
            'total_stimuli_available': len(self.BASE_STIMULI),
            'parts_completed': self.current_part,
            'window_size': '1370x960',
            'response_method': 'button_clicks',
            'timing_method': 'perf_counter',
            'crash_recovery_enabled': True,
            'recovery_used': bool(self.recovery_data)
        })
        return save_auditory_stroop_data(
            trial_data=self.trial_data,
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path,
            task_config=cfg
        )

    # ======================== Main Menu =========================

    def show_main_menu_button(self):
        self.main_menu_button = QPushButton("Main Menu", self)
        self.main_menu_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.main_menu_button.setFixedSize(200, 70)
        self.main_menu_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffffff, stop:1 #f0f0f0);
                color:black; border:2px solid #e0e0e0; border-radius:35px;
                padding:10px; font-weight:bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #fafafa, stop:1 #e8e8e8);
                border:2px solid #d0d0d0;
            }
        """)
        self.main_menu_button.clicked.connect(self.return_to_main_menu)
        self.layout.addWidget(self.main_menu_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_menu_button.show()

    def return_to_main_menu(self):
        try:
            from menu_selection import SelectionMenu
            geom = self.geometry()
            self.selection_menu = SelectionMenu(
                buttons_size=1.0,
                buttons_elevation=0.5,
                participant_id=self.participant_id,
                participant_folder_path=self.participant_folder_path
            )
            self.selection_menu.setGeometry(geom)
            self.selection_menu.show()
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "Main Menu", f"Couldn't open the main menu.\n\nError: {e}")

    # ===================== Emergency / Close =====================

    def get_emergency_save_data(self):
        """Optional hook used by your crash handler."""
        return {
            'trial_data': self.trial_data,
            'current_part': self.current_part,
            'current_index': self.current_index,
            'task_completed': self.task_completed,
            'participant_id': self.participant_id,
            'stimuli_parts': self.parts,
        }

    def closeEvent(self, event):
        """Clear session flags when closing after completion."""
        session_manager = get_session_manager()
        if session_manager and self.task_completed:
            if session_manager.session_data.get('current_task') == 'Auditory Stroop Task':
                session_manager.session_data['current_task'] = None
                session_manager.session_data['current_task_state'] = {}
        event.accept()


# ---------------------- Back-compat alias & exports ----------------------

# If older code imports the misspelled class name, keep it working:
AudioryStroopTask = AuditoryStroopTask
__all__ = ["AuditoryStroopTask", "AudioryStroopTask", "main"]


# ---------------------------- Standalone run ----------------------------

def main():
    """
    Run the task standalone for testing:
    python -m task_auditory_stroop.auditory_stroop_task
    """
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")

    # Sample participant
    participant_id = "TEST_STROOP_001"
    sample_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_STROOP_001")
    os.makedirs(sample_folder, exist_ok=True)

    # Ensure session manager exists
    if not get_session_manager():
        initialize_session_manager(participant_id, sample_folder)

    w = AuditoryStroopTask(None, None, participant_id, sample_folder, recovery_mode=False)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
