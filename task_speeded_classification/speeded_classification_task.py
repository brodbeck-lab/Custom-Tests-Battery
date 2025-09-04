import sys
import os
import random
import time
import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QCheckBox, QSpinBox, QDoubleSpinBox, QGridLayout, QFrame,
    QLineEdit, QComboBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QProcess
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtGui import QFont, QKeySequence, QShortcut

# Import the modular save function
from .data_saver import save_speeded_classification_data

# Import crash recovery system
from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager
from crash_recovery_system.task_state_saver import TaskStateMixin
import crash_recovery_system.crash_handler as crash_handler

# Default configuration values
DEFAULT_PRACTICE_TRIALS_PHONEME = 1
DEFAULT_PRACTICE_TRIALS_VOICE = 1
DEFAULT_MAIN_TRIALS_PHONEME = 2
DEFAULT_MAIN_TRIALS_VOICE = 2
DEFAULT_ITI_DURATION = 1000  # milliseconds between trials

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/py2app"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def check_required_audio_files():
    """Check that all required audio files exist - DO NOT CREATE ANY FILES"""
    stimuli_dir = resource_path("task_speeded_classification/stimuli")
    
    # Required audio files - EXACT names provided by user
    required_files = [
        "baab1M1.wav", 
        "baab2F2.wav", 
        "paab1M2.wav", 
        "paab2F1.wav"
    ]
    
    missing_files = []
    
    for filename in required_files:
        filepath = os.path.join(stimuli_dir, filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)
    
    if missing_files:
        error_message = f"MISSING AUDIO FILES:\n{', '.join(missing_files)}\n\nRequired directory: {stimuli_dir}"
        print(f"ERROR: {error_message}")
        return False, error_message
    
    print("All required audio files found")
    return True, stimuli_dir

class SpeededClassificationTask(TaskStateMixin, QWidget):
    def __init__(self, x_pos, y_pos, participant_id, participant_folder_path):
        # Initialize session manager FIRST if not already initialized
        if not get_session_manager() and participant_id and participant_folder_path:
            print("Initializing session manager from Speeded Classification task...")
            initialize_session_manager(participant_id, participant_folder_path)
        super().__init__()

        # Store participant information
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path

        # Window setup
        self.setWindowTitle("Speeded Classification Task")
        screen = QApplication.primaryScreen().geometry()
        window_width, window_height = 1370, 960
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        self.setStyleSheet("""
            QWidget { background: #f8f9fa; color: #495057; }
        """)

        # Task state variables
        self.current_phase = "configuration"
        self.current_trial = 0
        self.trial_data = []
        self.task_config = {}
        self.stimulus_onset_time = None
        self.response_time = None
        self._task_completed = False
        self._completion_in_progress = False
        self.current_response_mode = None  # 'phoneme' or 'voice'

        # Memory management - track objects for cleanup
        self.active_shortcuts = []  # kept for compatibility; not used now
        self.active_timers = []
        self.sound_effects = []

        # Audio system
        self.sound = None
        self.initialize_audio_system()

        # Timers
        self.iti_timer = QTimer()
        self.iti_timer.setSingleShot(True)
        self.iti_timer.timeout.connect(self.start_next_trial)
        self.active_timers.append(self.iti_timer)

        # --- Shared response timeout timer (patch) ---
        self.response_timer = QTimer()
        self.response_timer.setSingleShot(True)
        self.response_timer.timeout.connect(self.handle_no_response)
        self.active_timers.append(self.response_timer)
        # ---------------------------------------------

        # Verify audio files BEFORE setting up UI - NO FILE CREATION
        files_exist, result = check_required_audio_files()
        if not files_exist:
            QMessageBox.critical(None, "Missing Audio Files",
                                 f"Required audio files are missing!\n\n{result}\n\n"
                                 "Please add the missing files and restart the task.")
            sys.exit(1)
        self.stimuli_dir = result

        # UI
        self.setup_main_interface()
        self.setup_stimulus_paths()

        # Recovery
        self.check_recovery()

    def initialize_audio_system(self):
        try:
            self.sound = QSoundEffect()
            self.sound_effects.append(self.sound)
            print("Audio system initialized successfully")
        except Exception as e:
            print(f"Error initializing audio system: {e}")
            self.sound = None

    def setup_stimulus_paths(self):
        self.stimuli = {
            "practice_phoneme": [
                os.path.join(self.stimuli_dir, "baab1M1.wav"),
                os.path.join(self.stimuli_dir, "baab2F2.wav"),
                os.path.join(self.stimuli_dir, "paab1M2.wav"),
                os.path.join(self.stimuli_dir, "paab2F1.wav"),
            ],
            "practice_voice": [
                os.path.join(self.stimuli_dir, "baab1M1.wav"),
                os.path.join(self.stimuli_dir, "paab1M2.wav"),
                os.path.join(self.stimuli_dir, "baab2F2.wav"),
                os.path.join(self.stimuli_dir, "paab2F1.wav"),
            ],
            "main_phoneme": [
                os.path.join(self.stimuli_dir, "baab1M1.wav"),
                os.path.join(self.stimuli_dir, "baab2F2.wav"),
                os.path.join(self.stimuli_dir, "paab1M2.wav"),
                os.path.join(self.stimuli_dir, "paab2F1.wav"),
            ],
            "main_voice": [
                os.path.join(self.stimuli_dir, "baab1M1.wav"),
                os.path.join(self.stimuli_dir, "paab1M2.wav"),
                os.path.join(self.stimuli_dir, "baab2F2.wav"),
                os.path.join(self.stimuli_dir, "paab2F1.wav"),
            ],
        }
        print("Stimulus file paths setup completed")

    # ---------- UI helpers for on-screen controls ----------
    def set_action_button(self, label, handler):
        self.action_button.setText(label)
        self.action_button.setEnabled(True)
        try:
            self.action_button.clicked.disconnect()
        except TypeError:
            pass
        self.action_button.clicked.connect(handler)
        self.action_button.show()

    def set_response_mode(self, mode):
        self.current_response_mode = mode
        self.button_B.hide(); self.button_P.hide()
        self.button_Male.hide(); self.button_Female.hide()
        if mode == 'phoneme':
            self.button_B.show(); self.button_P.show()
        else:
            self.button_Male.show(); self.button_Female.show()
        self.response_widget.show()
        self.set_response_buttons_enabled(False)

    def set_response_buttons_enabled(self, enabled: bool):
        for btn in (self.button_B, self.button_P, self.button_Male, self.button_Female):
            if btn.isVisible():
                btn.setEnabled(enabled)

    # --- timer helper (patch) ---
    def stop_response_timer(self):
        try:
            if hasattr(self, 'response_timer') and self.response_timer.isActive():
                self.response_timer.stop()
        except RuntimeError:
            pass
    # ----------------------------

    def cleanup_shortcuts(self):
        print(f"Cleaning up {len(self.active_shortcuts)} shortcuts...")
        for shortcut in self.active_shortcuts[:]:
            if shortcut is not None:
                try:
                    shortcut.setEnabled(False)
                    shortcut.deleteLater()
                except RuntimeError:
                    pass
            self.active_shortcuts.remove(shortcut)
        self.active_shortcuts.clear()
        print("Shortcuts cleaned up")

    def cleanup_timers(self):
        print(f"Cleaning up {len(self.active_timers)} timers...")
        for timer in self.active_timers:
            if timer is not None:
                try:
                    timer.stop()
                    timer.deleteLater()
                except RuntimeError:
                    pass
        self.active_timers.clear()
        print("Timers cleaned up")

    def cleanup_audio(self):
        print(f"Cleaning up {len(self.sound_effects)} audio objects...")
        for sound_effect in self.sound_effects:
            if sound_effect is not None:
                try:
                    sound_effect.stop()
                    sound_effect.deleteLater()
                except RuntimeError:
                    pass
        self.sound_effects.clear()
        self.sound = None
        print("Audio resources cleaned up")

    def setup_main_interface(self):
        layout = QVBoxLayout(); layout.setContentsMargins(30, 30, 30, 30)

        title_label = QLabel("Speeded Classification Task")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50; background: #ffffff; border: 2px solid #dee2e6;
                border-radius: 12px; padding: 15px; margin: 10px; font-weight: bold;
            }
        """)
        layout.addWidget(title_label)

        self.display_label = QLabel("Configure your task parameters below, then click Start.")
        self.display_label.setFont(QFont('Arial', 16))
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("""
            QLabel {
                color: #495057; background: #ffffff; border: 1px solid #dee2e6;
                border-radius: 8px; padding: 20px; margin: 10px; min-height: 80px;
            }
        """)
        layout.addWidget(self.display_label)

        # Response buttons row
        self.response_widget = QWidget()
        rb_layout = QHBoxLayout(); rb_layout.setContentsMargins(0, 0, 0, 0); rb_layout.setSpacing(12)

        def make_btn(text, handler):
            btn = QPushButton(text)
            btn.setStyleSheet(self.get_control_button_style())
            btn.setMinimumHeight(48)
            btn.clicked.connect(handler)
            return btn

        self.button_B = make_btn("B", lambda: self.record_response('B'))
        self.button_P = make_btn("P", lambda: self.record_response('P'))
        self.button_Male = make_btn("Male", lambda: self.record_response('Male'))
        self.button_Female = make_btn("Female", lambda: self.record_response('Female'))

        for b in (self.button_B, self.button_P, self.button_Male, self.button_Female):
            rb_layout.addWidget(b)
        self.response_widget.setLayout(rb_layout)
        self.response_widget.hide()
        layout.addWidget(self.response_widget)

        # Action (Start/Continue/Main Menu) button
        self.action_button = QPushButton("Start")
        self.action_button.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        self.action_button.setStyleSheet("""
            QPushButton {
                background: #007bff; color: white; border: none; border-radius: 8px;
                padding: 12px 24px; font-weight: bold; margin: 10px auto; min-height: 20px;
            }
            QPushButton:hover { background: #0056b3; }
            QPushButton:pressed { background: #004085; }
        """)
        self.action_button.hide()
        layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Config + Status
        self.config_widget = self.create_configuration_widget(); layout.addWidget(self.config_widget)
        self.status_widget = self.create_status_widget(); self.status_widget.hide(); layout.addWidget(self.status_widget)

        self.setLayout(layout)

    def create_configuration_widget(self):
        config_widget = QWidget(); config_layout = QVBoxLayout()
        config_layout.setContentsMargins(20, 10, 20, 10)

        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame { background: #ffffff; border: 1px solid #ced4da; border-radius: 8px; padding: 20px; margin: 5px; }
        """)
        frame_layout = QGridLayout(); frame_layout.setSpacing(15)

        practice_header = QLabel("Practice Phase:")
        practice_header.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        practice_header.setStyleSheet("color: #007bff; margin-bottom: 10px;")
        frame_layout.addWidget(practice_header, 0, 0, 1, 2)

        label_font = QFont('Arial', 12)

        practice_phoneme_label = QLabel("Practice Phoneme Trials (B/P):")
        practice_phoneme_label.setFont(label_font)
        frame_layout.addWidget(practice_phoneme_label, 1, 0)
        self.practice_phoneme_spin = QSpinBox(); self.practice_phoneme_spin.setRange(0, 20)
        self.practice_phoneme_spin.setValue(DEFAULT_PRACTICE_TRIALS_PHONEME)
        self.practice_phoneme_spin.setStyleSheet(self.get_simple_spinbox_style())
        frame_layout.addWidget(self.practice_phoneme_spin, 1, 1)

        practice_voice_label = QLabel("Practice Voice Trials (M/F):")
        practice_voice_label.setFont(label_font)
        frame_layout.addWidget(practice_voice_label, 2, 0)
        self.practice_voice_spin = QSpinBox(); self.practice_voice_spin.setRange(0, 20)
        self.practice_voice_spin.setValue(DEFAULT_PRACTICE_TRIALS_VOICE)
        self.practice_voice_spin.setStyleSheet(self.get_simple_spinbox_style())
        frame_layout.addWidget(self.practice_voice_spin, 2, 1)

        main_header = QLabel("Main Task:")
        main_header.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        main_header.setStyleSheet("color: #007bff; margin: 15px 0px 10px 0px;")
        frame_layout.addWidget(main_header, 3, 0, 1, 2)

        main_phoneme_label = QLabel("Main Phoneme Trials (B/P):")
        main_phoneme_label.setFont(label_font)
        frame_layout.addWidget(main_phoneme_label, 4, 0)
        self.main_phoneme_spin = QSpinBox(); self.main_phoneme_spin.setRange(0, 100)
        self.main_phoneme_spin.setValue(DEFAULT_MAIN_TRIALS_PHONEME)
        self.main_phoneme_spin.setStyleSheet(self.get_simple_spinbox_style())
        frame_layout.addWidget(self.main_phoneme_spin, 4, 1)

        main_voice_label = QLabel("Main Voice Trials (M/F):")
        main_voice_label.setFont(label_font)
        frame_layout.addWidget(main_voice_label, 5, 0)
        self.main_voice_spin = QSpinBox(); self.main_voice_spin.setRange(0, 100)
        self.main_voice_spin.setValue(DEFAULT_MAIN_TRIALS_VOICE)
        self.main_voice_spin.setStyleSheet(self.get_simple_spinbox_style())
        frame_layout.addWidget(self.main_voice_spin, 5, 1)

        timing_header = QLabel("Timing Settings:")
        timing_header.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        timing_header.setStyleSheet("color: #007bff; margin: 15px 0px 10px 0px;")
        frame_layout.addWidget(timing_header, 6, 0, 1, 2)

        iti_label = QLabel("Inter-trial Interval (ms):")
        iti_label.setFont(label_font)
        frame_layout.addWidget(iti_label, 7, 0)
        self.iti_spin = QSpinBox(); self.iti_spin.setRange(500, 3000)
        self.iti_spin.setValue(DEFAULT_ITI_DURATION)
        self.iti_spin.setStyleSheet(self.get_simple_spinbox_style())
        frame_layout.addWidget(self.iti_spin, 7, 1)

        volume_label = QLabel("Audio Volume:")
        volume_label.setFont(label_font)
        frame_layout.addWidget(volume_label, 8, 0)
        self.volume_spin = QDoubleSpinBox(); self.volume_spin.setRange(0.1, 1.0)
        self.volume_spin.setSingleStep(0.1); self.volume_spin.setValue(0.7)
        self.volume_spin.setStyleSheet(self.get_simple_spinbox_style())
        frame_layout.addWidget(self.volume_spin, 8, 1)

        config_frame.setLayout(frame_layout); config_layout.addWidget(config_frame)

        self.start_button = QPushButton("Start Speeded Classification Task")
        self.start_button.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        self.start_button.setStyleSheet("""
            QPushButton {
                background: #007bff; color: white; border: none; border-radius: 8px;
                padding: 15px 30px; font-weight: bold; margin: 15px; min-height: 20px;
            }
            QPushButton:hover { background: #0056b3; }
            QPushButton:pressed { background: #004085; }
        """)
        self.start_button.clicked.connect(self.start_task_from_config)
        config_layout.addWidget(self.start_button)

        config_widget.setLayout(config_layout)
        return config_widget

    def create_status_widget(self):
        status_widget = QWidget(); layout = QVBoxLayout()

        self.status_label = QLabel("Status: Ready")
        self.status_label.setFont(QFont('Arial', 14))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel { color: #495057; background: #f8f9fa; border: 1px solid #dee2e6;
                     border-radius: 6px; padding: 10px; margin: 5px; }
        """)
        layout.addWidget(self.status_label)

        self.progress_label = QLabel("Progress: Ready to start")
        self.progress_label.setFont(QFont('Arial', 12))
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("""
            QLabel { color: #6c757d; background: #ffffff; border: 1px solid #ced4da;
                     border-radius: 4px; padding: 8px; margin: 2px; }
        """)
        layout.addWidget(self.progress_label)

        button_layout = QHBoxLayout()
        self.pause_button = QPushButton("Pause Task")
        self.pause_button.clicked.connect(self.pause_task)
        self.pause_button.setStyleSheet(self.get_control_button_style())
        button_layout.addWidget(self.pause_button)

        self.emergency_save_button = QPushButton("Emergency Save")
        self.emergency_save_button.clicked.connect(self.emergency_save)
        self.emergency_save_button.setStyleSheet(self.get_control_button_style())
        button_layout.addWidget(self.emergency_save_button)

        layout.addLayout(button_layout); status_widget.setLayout(layout)
        return status_widget

    def get_simple_spinbox_style(self):
        return """
            QSpinBox, QDoubleSpinBox {
                background: white; border: 1px solid #ced4da; border-radius: 4px;
                padding: 8px; font-size: 14px; min-width: 100px; min-height: 16px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #007bff; }
        """

    def get_control_button_style(self):
        return """
            QPushButton {
                background: #ffffff; border: 2px solid #6c757d; border-radius: 6px;
                padding: 8px 16px; color: #495057; font-weight: bold; min-width: 100px;
            }
            QPushButton:hover { background: #f8f9fa; border: 2px solid #495057; }
            QPushButton:pressed { background: #e9ecef; }
        """

    def start_task_from_config(self):
        self.task_config = {
            'practice_phoneme_trials': self.practice_phoneme_spin.value(),
            'practice_voice_trials': self.practice_voice_spin.value(),
            'main_phoneme_trials': self.main_phoneme_spin.value(),
            'main_voice_trials': self.main_voice_spin.value(),
            'iti_duration_ms': self.iti_spin.value(),
            'audio_volume': self.volume_spin.value(),
            'task_start_time': datetime.now().isoformat(),
        }
        if self.sound:
            self.sound.setVolume(self.task_config['audio_volume'])

        self.config_widget.hide()
        self.status_widget.show()

        self.current_phase = "practice_phoneme"
        self.current_trial = 0
        self.update_status("Starting Practice Phase - Phoneme Recognition (B/P)")
        self.start_practice_phoneme()

    def start_practice_phoneme(self):
        self.display_label.setText(
            "Practice Phase: Phoneme Recognition\n\n"
            "You will hear words starting with either /b/ or /p/ sounds.\n"
            "Click **B** if you hear a /b/ sound (like 'ba...')\n"
            "Click **P** if you hear a /p/ sound (like 'pa...')\n\n"
            "Click the button below when ready to start."
        )
        self.display_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        self.display_label.setStyleSheet("""
            QLabel {
                color: #2c3e50; background: #ffffff; border: 2px solid #28a745;
                border-radius: 10px; padding: 25px; margin: 15px; min-height: 120px;
            }
        """)

        self.setFocus(); self.activateWindow(); self.raise_()
        self.response_widget.hide()
        self.set_action_button("Start", self.start_practice_trials)
        print("Action button set up for practice phoneme phase")

    def start_practice_trials(self):
        print("Start clicked - starting practice phoneme trials")
        self.begin_trials("practice_phoneme")

    def begin_trials(self, phase):
        print(f"Beginning trials for phase: {phase}")
        self.current_phase = phase
        self.current_trial = 0
        if "phoneme" in phase:
            self.set_response_mode('phoneme')
        else:
            self.set_response_mode('voice')
        self.action_button.hide()
        self.start_next_trial()

    # Keyboard shortcut stubs (not used)
    def setup_phoneme_shortcuts(self): print("Keyboard shortcuts disabled.")
    def setup_voice_shortcuts(self): print("Keyboard shortcuts disabled.")

    def start_next_trial(self):
        # patch: clear any lingering timer
        self.stop_response_timer()
        self.stimulus_onset_time = None

        max_trials = self.get_max_trials_for_phase(self.current_phase)
        if self.current_trial >= max_trials:
            self.advance_to_next_phase(); return

        stimulus_list = self.stimuli[self.current_phase]
        stimulus_file = random.choice(stimulus_list)

        if "phoneme" in self.current_phase:
            self.display_label.setText(
                f"Trial {self.current_trial + 1} of {max_trials}\n\n"
                "Listen carefully and respond quickly:\n"
                "Click 'B' for /b/ sounds\n"
                "Click 'P' for /p/ sounds\n\n"
                "Get ready..."
            )
        else:
            self.display_label.setText(
                f"Trial {self.current_trial + 1} of {max_trials}\n\n"
                "Listen carefully and respond quickly:\n"
                "Click 'Male' for Male voice\n"
                "Click 'Female' for Female voice\n\n"
                "Get ready..."
            )

        self.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.display_label.setStyleSheet("""
            QLabel {
                color: #2c3e50; background: #ffffff; border: 2px solid #dee2e6;
                border-radius: 10px; padding: 30px; margin: 15px; min-height: 150px;
            }
        """)
        self.update_progress(f"{self.current_phase.replace('_', ' ').title()}: {self.current_trial + 1}/{max_trials}")
        self.set_response_buttons_enabled(False)

        QTimer.singleShot(1500, lambda: self.play_stimulus(stimulus_file))

    def play_stimulus(self, stimulus_file):
        try:
            if not os.path.exists(stimulus_file):
                print(f"ERROR: Verified file is missing: {stimulus_file}")
                self.skip_trial(); return
            if not self.sound:
                print("Warning: Audio system not available!"); self.skip_trial(); return

            self.stimulus_onset_time = time.perf_counter()
            self.current_stimulus = stimulus_file

            self.sound.setSource(QUrl.fromLocalFile(os.path.abspath(stimulus_file)))
            self.sound.play()

            self.display_label.setText("Listen and respond as quickly as possible!")
            self.display_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
            self.display_label.setStyleSheet("""
                QLabel {
                    color: #007bff; background: #ffffff; border: 2px solid #007bff;
                    border-radius: 10px; padding: 30px; margin: 15px; min-height: 150px;
                }
            """)

            self.set_response_buttons_enabled(True)
            self.stop_response_timer()
            self.response_timer.start(10000)  # 10s timeout

        except Exception as e:
            print(f"Error playing stimulus: {e}")
            self.skip_trial()

    def record_response(self, response):
        self.stop_response_timer()  # patch: stop timer on click
        if not hasattr(self, 'stimulus_onset_time') or self.stimulus_onset_time is None:
            return
        self.set_response_buttons_enabled(False)

        response_time = time.perf_counter()
        rt_ms = (response_time - self.stimulus_onset_time) * 1000

        correct_response = self.get_correct_response(self.current_stimulus)
        is_correct = response.lower() == correct_response.lower()

        trial_data = {
            'participant_id': self.participant_id,
            'phase': self.current_phase,
            'trial_number': self.current_trial + 1,
            'stimulus_file': self.current_stimulus,
            'stimulus_onset_time': self.stimulus_onset_time,
            'response': response,
            'correct_response': correct_response,
            'is_correct': is_correct,
            'reaction_time_ms': round(rt_ms, 2),
            'timestamp': datetime.now().isoformat(),
        }
        self.trial_data.append(trial_data)

        feedback_color = "#28a745" if is_correct else "#dc3545"
        feedback_text = "Correct!" if is_correct else f"Incorrect (should be {correct_response})"
        self.display_label.setStyleSheet(f"""
            QLabel {{
                color: {feedback_color}; background: #ffffff; border: 2px solid {feedback_color};
                border-radius: 10px; padding: 30px; margin: 15px; min-height: 150px; font-weight: bold;
            }}
        """)
        self.display_label.setText(f"{feedback_text}\n\nResponse Time: {rt_ms:.0f} ms")
        self.display_label.setFont(QFont('Arial', 20, QFont.Weight.Bold))

        self.stimulus_onset_time = None
        self.current_trial += 1
        self.iti_timer.start(self.task_config['iti_duration_ms'])

    def get_correct_response(self, stimulus_file):
        filename = os.path.basename(stimulus_file)
        if self.current_phase.endswith("phoneme"):
            if filename.startswith('baab'): return 'B'
            elif filename.startswith('paab'): return 'P'
        else:
            if 'M' in filename: return 'Male'
            elif 'F' in filename: return 'Female'
        return 'Unknown'

    def get_max_trials_for_phase(self, phase):
        phase_trial_map = {
            'practice_phoneme': self.task_config.get('practice_phoneme_trials', DEFAULT_PRACTICE_TRIALS_PHONEME),
            'practice_voice': self.task_config.get('practice_voice_trials', DEFAULT_PRACTICE_TRIALS_VOICE),
            'main_phoneme': self.task_config.get('main_phoneme_trials', DEFAULT_MAIN_TRIALS_PHONEME),
            'main_voice': self.task_config.get('main_voice_trials', DEFAULT_MAIN_TRIALS_VOICE),
        }
        return phase_trial_map.get(phase, 10)

    def advance_to_next_phase(self):
        self.stop_response_timer()  # patch
        phase_sequence = ['practice_phoneme', 'practice_voice', 'main_phoneme', 'main_voice', 'completed']
        current_index = phase_sequence.index(self.current_phase)
        if current_index < len(phase_sequence) - 1:
            next_phase = phase_sequence[current_index + 1]
            if next_phase == 'completed':
                self.complete_task()
            else:
                self.current_phase = next_phase
                self.current_trial = 0
                self.show_phase_transition(next_phase)
        else:
            self.complete_task()

    def show_phase_transition(self, next_phase):
        self.stop_response_timer()  # patch
        phase_descriptions = {
            'practice_voice': ("Practice Phase: Voice Recognition",
                               "Now you will hear the same types of words.\n"
                               "This time, respond to the speaker's gender:\n"
                               "Click 'Male' for Male voice\n"
                               "Click 'Female' for Female voice\n\n"
                               "Click Continue when ready to continue."),
            'main_phoneme': ("Main Task: Phoneme Recognition",
                             "Now we'll begin the main task.\n"
                             "Respond to the first sound of each word:\n"
                             "Click 'B' for /b/ sounds\n"
                             "Click 'P' for /p/ sounds\n\n"
                             "Click Continue when ready to start."),
            'main_voice': ("Final Phase: Voice Recognition",
                           "Final phase! Respond to the speaker's gender:\n"
                           "Click 'Male' for Male voice\n"
                           "Click 'Female' for Female voice\n\n"
                           "Click Continue when ready to start."),
        }
        title, description = phase_descriptions[next_phase]
        self.display_label.setStyleSheet("""
            QLabel {
                color: #2c3e50; background: #ffffff; border: 2px solid #007bff;
                border-radius: 10px; padding: 25px; margin: 15px; min-height: 120px;
            }
        """)
        self.display_label.setText(f"{title}\n\n{description}")
        self.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.response_widget.hide()
        self.set_action_button("Continue", lambda: self.begin_trials(next_phase))
        self.update_status(f"Transitioning to {title}")
        print(f"Action button set for phase transition to: {next_phase}")

    def complete_task(self):
        self.stop_response_timer()  # patch
        self._completion_in_progress = True

        self.calculate_and_display_summary()
        success = self.save_final_data()

        if success:
            self.update_status("Task completed successfully! Data saved.")
            self.display_label.setText(
                "Speeded Classification Task Complete!\n\n"
                "Thank you for your participation.\n"
                "Your data has been saved successfully.\n\n"
                "You may now close this window."
            )
            self.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
            self.display_label.setStyleSheet("""
                QLabel {
                    color: #2c3e50; background: #ffffff; border: 2px solid #28a745;
                    border-radius: 10px; padding: 25px; margin: 15px; min-height: 120px;
                }
            """)
            # NEW: hide response buttons and show Main Menu button
            self.response_widget.hide()
            self.set_action_button("Main Menu", self.open_main_menu)
        else:
            self.update_status("Task completed but there was an error saving data.")
            QMessageBox.warning(self, "Save Error",
                                "The task completed but there was an error saving your data. "
                                "Please contact the experimenter.")

        self._task_completed = True
        self._completion_in_progress = False
        self.status_widget.hide()
        self.cleanup_all_resources()
        print("Speeded Classification Task completed successfully")

    def open_main_menu(self):
        """
        Open the main menu without creating a second QApplication.
        1) Prefer importing and showing SelectionMenu in this process.
        2) Fallback: spawn a new process to run menu_selection (which calls main()).
        """
        try:
            import menu_selection as ms
            from PyQt6.QtWidgets import QWidget

            # Preferred path: use SelectionMenu class directly (no new QApplication)
            if hasattr(ms, "SelectionMenu"):
                try:
                    self._main_menu_window = ms.SelectionMenu(
                        participant_id=getattr(self, "participant_id", None),
                        participant_folder_path=getattr(self, "participant_folder_path", None),
                        recovery_mode=False
                    )
                except TypeError:
                    # Constructor signature mismatch; try no-args
                    self._main_menu_window = ms.SelectionMenu()

                if isinstance(self._main_menu_window, QWidget):
                    self._main_menu_window.show()
                    self.close()
                    return

            # Fallback: run menu_selection as a separate process (will hit its main())
            from PyQt6.QtCore import QProcess
            import sys
            self._menu_proc = QProcess(self)
            self._menu_proc.start(sys.executable, ["-m", "menu_selection"])
            if not self._menu_proc.waitForStarted(2000):
                # Last resort: run by file path
                script_path = resource_path("menu_selection.py")
                self._menu_proc.start(sys.executable, [script_path])
            self.close()

        except Exception as e:
            QMessageBox.warning(
                self, "Main Menu",
                f"Couldn't open the main menu automatically.\n\nError: {e}\n\n"
                "Please run menu_selection manually."
            )

    def calculate_and_display_summary(self):
        if not self.trial_data:
            return
        practice_phoneme = [t for t in self.trial_data if t['phase'] == 'practice_phoneme']
        practice_voice = [t for t in self.trial_data if t['phase'] == 'practice_voice']
        main_phoneme = [t for t in self.trial_data if t['phase'] == 'main_phoneme']
        main_voice = [t for t in self.trial_data if t['phase'] == 'main_voice']

        summary = "PERFORMANCE SUMMARY\n" + "=" * 30 + "\n\n"
        for phase_data, phase_name in [(practice_phoneme, "Practice Phoneme"),
                                       (practice_voice, "Practice Voice"),
                                       (main_phoneme, "Main Phoneme"),
                                       (main_voice, "Main Voice")]:
            if phase_data:
                accuracy = sum(1 for t in phase_data if t['is_correct']) / len(phase_data) * 100
                avg_rt = sum(t['reaction_time_ms'] for t in phase_data) / len(phase_data)
                summary += f"{phase_name}:\n"
                summary += f"  Accuracy: {accuracy:.1f}%\n"
                summary += f"  Average RT: {avg_rt:.0f} ms\n"
                summary += f"  Trials: {len(phase_data)}\n\n"
        print(summary)

    def save_final_data(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_folder_name = f"speeded_classification_task_{timestamp}"
            task_folder_path = os.path.join(self.participant_folder_path, task_folder_name)
            os.makedirs(task_folder_path, exist_ok=True)
            print(f"Created Speeded Classification task folder: {task_folder_path}")
            success = save_speeded_classification_data(
                trial_data=self.trial_data,
                participant_id=self.participant_id,
                task_folder_path=task_folder_path,
                task_config=self.task_config
            )
            return success
        except Exception as e:
            print(f"Error saving Speeded Classification task data: {e}")
            return False

    def handle_no_response(self):
        self.stop_response_timer()  # patch
        if self.stimulus_onset_time is not None:
            self.set_response_buttons_enabled(False)
            trial_data = {
                'participant_id': self.participant_id,
                'phase': self.current_phase,
                'trial_number': self.current_trial + 1,
                'stimulus_file': getattr(self, 'current_stimulus', 'unknown'),
                'stimulus_onset_time': self.stimulus_onset_time,
                'response': 'NO_RESPONSE',
                'correct_response': self.get_correct_response(getattr(self, 'current_stimulus', '')),
                'is_correct': False,
                'reaction_time_ms': 10000,
                'timestamp': datetime.now().isoformat(),
            }
            self.trial_data.append(trial_data)
            self.display_label.setText("No response detected!\n\nPlease try to respond more quickly.")
            self.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
            self.display_label.setStyleSheet("""
                QLabel {
                    color: #dc3545; background: #ffffff; border: 2px solid #dc3545;
                    border-radius: 10px; padding: 25px; margin: 15px; min-height: 120px;
                }
            """)
            self.stimulus_onset_time = None
            self.current_trial += 1
            QTimer.singleShot(2000, self.start_next_trial)

    def skip_trial(self):
        self.stop_response_timer()  # patch
        self.current_trial += 1
        QTimer.singleShot(2000, self.start_next_trial)

    def pause_task(self):
        self.stop_response_timer()  # patch
        self.iti_timer.stop()
        self.update_status("Task paused")
        self.display_label.setText("Task Paused\n\nClick 'Resume' to continue.")
        self.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.display_label.setStyleSheet("""
            QLabel {
                color: #ffc107; background: #ffffff; border: 2px solid #ffc107;
                border-radius: 10px; padding: 25px; margin: 15px; min-height: 120px;
            }
        """)

    def emergency_save(self):
        try:
            if hasattr(self, 'trial_data') and self.trial_data:
                session_manager = get_session_manager()
                if session_manager:
                    session_manager.emergency_save()
            QMessageBox.information(self, "Emergency Save", "Emergency save completed successfully!")
        except Exception as e:
            print(f"Emergency save failed: {e}")
            QMessageBox.warning(self, "Emergency Save Error", f"Emergency save failed: {str(e)}")

    def cleanup_all_resources(self):
        print("Cleaning up all resources...")
        self.cleanup_timers()
        self.cleanup_audio()
        print("All resources cleaned up successfully")

    def update_status(self, message):
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"Status: {message}")

    def update_progress(self, message):
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(f"Progress: {message}")

    def check_recovery(self):
        try:
            session_manager = get_session_manager()
            if session_manager:
                recovery_data = session_manager.session_data.get('current_task_state')
                if recovery_data and recovery_data.get('task_name') == 'Speeded Classification Task':
                    print("Found recovery data for Speeded Classification Task")
                    self.recovery_data = recovery_data
                    self._update_recovery_ui()
                else:
                    print("No recovery data found - starting fresh")
            else:
                print("No session manager available for recovery check")
        except Exception as e:
            print(f"Error during recovery check: {e}")

    def _get_task_specific_state(self):
        return {
            'current_phase': getattr(self, 'current_phase', 'configuration'),
            'current_trial': getattr(self, 'current_trial', 0),
            'task_config': getattr(self, 'task_config', {}),
            'stimulus_onset_time': getattr(self, 'stimulus_onset_time', None),
            'current_stimulus': getattr(self, 'current_stimulus', None),
            'comprehensive_configuration': True,
            'task_version': '2.0',
        }

    def _update_recovery_ui(self):
        if hasattr(self, 'recovery_data') and self.recovery_data:
            stored_config = self.recovery_data.get('task_specific_state', {}).get('task_config')
            if stored_config:
                self.task_config = stored_config
                print("Recovered Speeded Classification configuration from previous session")

    def closeEvent(self, event):
        try:
            if (not getattr(self, '_task_completed', False)) and (not getattr(self, '_completion_in_progress', False)):
                print("Emergency save: task in progress during close")
                session_manager = get_session_manager()
                if session_manager:
                    session_manager.emergency_save()
            else:
                print("Task was completed normally - no emergency save needed")
        except Exception as e:
            print(f"Error during emergency save: {e}")
        self.cleanup_all_resources()
        event.accept()
        print("Speeded Classification task cleanup completed")




def main():
    """Standalone main function for testing"""
    app = QApplication(sys.argv)
    
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")
    
    print("=== SPEEDED CLASSIFICATION TASK (NO PLACEHOLDERS) ===")
    print("Placeholder creation: DISABLED")
    print("Audio file verification: ENABLED")
    print("Memory management: ENABLED")
    print("Crash recovery system: ENABLED")
    
    # Sample participant data
    sample_participant_id = "TEST_SPEEDED_001"
    sample_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_SPEEDED_001")
    
    os.makedirs(sample_folder, exist_ok=True)
    
    # Initialize session manager
    try:
        session_manager = initialize_session_manager(sample_participant_id, sample_folder)
        default_tasks = ["Speeded Classification Task"]
        session_manager.set_task_queue(default_tasks)
        print("Session manager initialized for testing")
    except Exception as e:
        print(f"Error initializing session manager: {e}")
    
    try:
        speeded_task = SpeededClassificationTask(
            x_pos=100,
            y_pos=100,
            participant_id=sample_participant_id,
            participant_folder_path=sample_folder
        )
        
        speeded_task.show()
        print("Speeded Classification Task launched (NO PLACEHOLDER VERSION)")
        print("Required audio files verified before launch")
        
        exit_code = app.exec()
        print("Speeded Classification task closed normally")
        return exit_code
        
    except Exception as e:
        print(f"Speeded Classification task crashed: {e}")
        import traceback
        traceback.print_exc()
        
        # Emergency save
        session_manager = get_session_manager()
        if session_manager:
            try:
                session_manager.emergency_save()
                print("Emergency save completed from main")
            except Exception as save_error:
                print(f"Emergency save failed: {save_error}")
        
        raise
    finally:
        from crash_recovery_system.session_manager import cleanup_session_manager
        cleanup_session_manager()
        print("Session cleanup completed")

if __name__ == "__main__":
    main()