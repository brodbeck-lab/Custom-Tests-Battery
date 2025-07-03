import sys
import os
import pandas as pd
import random
import time
import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QCheckBox, QSpinBox, QDoubleSpinBox, QGridLayout, QFrame,
    QLineEdit, QComboBox
)
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTimer, QEvent

# Import the modular save function
from .data_saver import save_cvc_data

# Import crash recovery system
from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager
from crash_recovery_system.task_state_saver import TaskStateMixin
import crash_recovery_system.crash_handler as crash_handler

# Default configuration values
DEFAULT_PRACTICE_TRIALS = 10
DEFAULT_NUM_TRIALS = 50
DEFAULT_DISPLAY_DURATION = 2000  # milliseconds per letter
DEFAULT_ITI_DURATION = 500  # milliseconds between letters

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/py2app"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CVCDisplayWindow(QWidget):
    """Child window that displays the CVC task content"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CVC Task Display")
        self.setFixedSize(1300, 760)
        
        # Create layout for the child window
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the main display label (used for letters and messages)
        self.display_label = QLabel("", self)
        self.display_label.setFont(QFont('Arial', 120, QFont.Weight.Bold))  # Large font for single letters
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("""
            QLabel {
                color: black;
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 60px;
                margin: 40px;
                min-height: 200px;
            }
        """)
        
        # Configuration widget (initially hidden)
        self.config_widget = self.create_configuration_widget()
        self.config_widget.hide()
        
        # Add widgets to layout
        self.main_layout.addWidget(self.display_label)
        self.main_layout.addWidget(self.config_widget)
        
        self.setLayout(self.main_layout)
        
        # Show initial configuration
        self.show_configuration()
    
    def create_configuration_widget(self):
        """Create the comprehensive task configuration widget"""
        config_widget = QWidget()
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(40, 20, 40, 20)
        
        # Title
        title_label = QLabel("CVC Task Configuration")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        config_layout.addWidget(title_label)
        
        # Configuration frame
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(20)
        
        # Practice trials section
        practice_layout = QVBoxLayout()
        
        # Practice trials header
        practice_header_layout = QHBoxLayout()
        self.practice_checkbox = QCheckBox("Practice Trials")
        self.practice_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.practice_checkbox.setChecked(True)  # Default enabled
        self.practice_checkbox.stateChanged.connect(self.on_practice_changed)
        practice_header_layout.addWidget(self.practice_checkbox)
        practice_header_layout.addStretch()
        practice_layout.addLayout(practice_header_layout)
        
        # Practice trials configuration grid
        practice_grid = QGridLayout()
        practice_grid.setSpacing(15)
        
        # Create practice labels with proper styling
        practice_labels = [
            QLabel("Number of trials:"),
            QLabel("Letter display duration (ms):"),
            QLabel("Stimulus List:"),
            QLabel("Real words to present:")
        ]
        
        # Style all practice labels
        for label in practice_labels:
            label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
            label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    background-color: transparent;
                    padding: 5px;
                    margin: 2px;
                }
            """)
        
        # Number of practice trials
        practice_grid.addWidget(practice_labels[0], 0, 0)
        self.practice_trials_spinbox = QSpinBox()
        self.practice_trials_spinbox.setRange(1, 100)
        self.practice_trials_spinbox.setValue(DEFAULT_PRACTICE_TRIALS)
        self.practice_trials_spinbox.setFont(QFont('Arial', 12))
        self.practice_trials_spinbox.setMinimumHeight(30)
        practice_grid.addWidget(self.practice_trials_spinbox, 0, 1)
        
        # Practice letter display duration
        practice_grid.addWidget(practice_labels[1], 1, 0)
        self.practice_duration_spinbox = QSpinBox()
        self.practice_duration_spinbox.setRange(500, 5000)
        self.practice_duration_spinbox.setValue(DEFAULT_DISPLAY_DURATION)
        self.practice_duration_spinbox.setSuffix(" ms")
        self.practice_duration_spinbox.setFont(QFont('Arial', 12))
        self.practice_duration_spinbox.setMinimumHeight(30)
        practice_grid.addWidget(self.practice_duration_spinbox, 1, 1)
        
        # Practice stimulus list selection
        practice_grid.addWidget(practice_labels[2], 2, 0)
        self.practice_list_combo = QComboBox()
        self.practice_list_combo.addItems(["List 1", "List 2"])
        self.practice_list_combo.setFont(QFont('Arial', 12))
        self.practice_list_combo.setMinimumHeight(30)
        practice_grid.addWidget(self.practice_list_combo, 2, 1)
        
        # Practice real words to present
        practice_grid.addWidget(practice_labels[3], 3, 0)
        self.practice_real_words_spinbox = QSpinBox()
        self.practice_real_words_spinbox.setRange(1, 50)
        self.practice_real_words_spinbox.setValue(5)  # Default: half of 10
        self.practice_real_words_spinbox.setFont(QFont('Arial', 12))
        self.practice_real_words_spinbox.setMinimumHeight(30)
        practice_grid.addWidget(self.practice_real_words_spinbox, 3, 1)
        
        # Set column stretch to make labels more visible
        practice_grid.setColumnStretch(0, 1)
        practice_grid.setColumnStretch(1, 1)
        
        practice_layout.addLayout(practice_grid)
        frame_layout.addLayout(practice_layout)
        
        # Separator line
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("color: #bdc3c7; margin: 10px 0px;")
        frame_layout.addWidget(separator1)
        
        # Main trials section
        main_layout = QVBoxLayout()
        
        # Main trials header
        main_header_layout = QHBoxLayout()
        self.main_checkbox = QCheckBox("Main Trials")
        self.main_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.main_checkbox.setChecked(True)  # Default enabled
        self.main_checkbox.stateChanged.connect(self.on_main_changed)
        main_header_layout.addWidget(self.main_checkbox)
        main_header_layout.addStretch()
        main_layout.addLayout(main_header_layout)
        
        # Main trials configuration grid
        main_grid = QGridLayout()
        main_grid.setSpacing(15)
        
        # Create main labels with proper styling
        main_labels = [
            QLabel("Number of trials:"),
            QLabel("Letter display duration (ms):"),
            QLabel("Stimulus List:"),
            QLabel("Real words to present:")
        ]
        
        # Style all main labels
        for label in main_labels:
            label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
            label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    background-color: transparent;
                    padding: 5px;
                    margin: 2px;
                }
            """)
        
        # Number of main trials
        main_grid.addWidget(main_labels[0], 0, 0)
        self.main_trials_spinbox = QSpinBox()
        self.main_trials_spinbox.setRange(1, 500)
        self.main_trials_spinbox.setValue(DEFAULT_NUM_TRIALS)
        self.main_trials_spinbox.setFont(QFont('Arial', 12))
        self.main_trials_spinbox.setMinimumHeight(30)
        main_grid.addWidget(self.main_trials_spinbox, 0, 1)
        
        # Main letter display duration
        main_grid.addWidget(main_labels[1], 1, 0)
        self.main_duration_spinbox = QSpinBox()
        self.main_duration_spinbox.setRange(500, 5000)
        self.main_duration_spinbox.setValue(DEFAULT_DISPLAY_DURATION)
        self.main_duration_spinbox.setSuffix(" ms")
        self.main_duration_spinbox.setFont(QFont('Arial', 12))
        self.main_duration_spinbox.setMinimumHeight(30)
        main_grid.addWidget(self.main_duration_spinbox, 1, 1)
        
        # Main stimulus list selection
        main_grid.addWidget(main_labels[2], 2, 0)
        self.main_list_combo = QComboBox()
        self.main_list_combo.addItems(["List 1", "List 2"])
        self.main_list_combo.setFont(QFont('Arial', 12))
        self.main_list_combo.setMinimumHeight(30)
        main_grid.addWidget(self.main_list_combo, 2, 1)
        
        # Main real words to present
        main_grid.addWidget(main_labels[3], 3, 0)
        self.main_real_words_spinbox = QSpinBox()
        self.main_real_words_spinbox.setRange(1, 250)
        self.main_real_words_spinbox.setValue(25)  # Default: half of 50
        self.main_real_words_spinbox.setFont(QFont('Arial', 12))
        self.main_real_words_spinbox.setMinimumHeight(30)
        main_grid.addWidget(self.main_real_words_spinbox, 3, 1)
        
        # Set column stretch to make labels more visible
        main_grid.setColumnStretch(0, 1)
        main_grid.setColumnStretch(1, 1)
        
        main_layout.addLayout(main_grid)
        frame_layout.addLayout(main_layout)
        
        config_frame.setLayout(frame_layout)
        config_layout.addWidget(config_frame)
        
        config_widget.setLayout(config_layout)
        return config_widget
    
    def on_practice_changed(self, state):
        """Handle practice trials checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.practice_trials_spinbox.setEnabled(enabled)
        self.practice_duration_spinbox.setEnabled(enabled)
        self.practice_list_combo.setEnabled(enabled)
        self.practice_real_words_spinbox.setEnabled(enabled)
    
    def on_main_changed(self, state):
        """Handle main trials checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.main_trials_spinbox.setEnabled(enabled)
        self.main_duration_spinbox.setEnabled(enabled)
        self.main_list_combo.setEnabled(enabled)
        self.main_real_words_spinbox.setEnabled(enabled)
    
    def get_configuration(self):
        """Get the current configuration settings"""
        config = {
            'practice_enabled': self.practice_checkbox.isChecked(),
            'practice_trials': self.practice_trials_spinbox.value() if self.practice_checkbox.isChecked() else 0,
            'practice_letter_duration': self.practice_duration_spinbox.value() if self.practice_checkbox.isChecked() else DEFAULT_DISPLAY_DURATION,
            'practice_stimulus_list': 1 if self.practice_list_combo.currentText() == "List 1" else 2,
            'practice_real_words': self.practice_real_words_spinbox.value() if self.practice_checkbox.isChecked() else 0,
            
            'main_enabled': self.main_checkbox.isChecked(),
            'main_trials': self.main_trials_spinbox.value() if self.main_checkbox.isChecked() else 0,
            'main_letter_duration': self.main_duration_spinbox.value() if self.main_checkbox.isChecked() else DEFAULT_DISPLAY_DURATION,
            'main_stimulus_list': 1 if self.main_list_combo.currentText() == "List 1" else 2,
            'main_real_words': self.main_real_words_spinbox.value() if self.main_checkbox.isChecked() else 0
        }
        return config
    
    def validate_configuration(self):
        """Validate the current configuration"""
        if not self.practice_checkbox.isChecked() and not self.main_checkbox.isChecked():
            return False, "At least one trial type (Practice or Main) must be selected."
        
        if self.practice_checkbox.isChecked():
            if self.practice_trials_spinbox.value() < 1:
                return False, "Practice trials must be at least 1 if enabled."
            if self.practice_real_words_spinbox.value() > self.practice_trials_spinbox.value():
                return False, "Practice real words cannot exceed total practice trials."
        
        if self.main_checkbox.isChecked():
            if self.main_trials_spinbox.value() < 1:
                return False, "Main trials must be at least 1 if enabled."
            if self.main_real_words_spinbox.value() > self.main_trials_spinbox.value():
                return False, "Main real words cannot exceed total main trials."
        
        return True, ""
    
    def show_configuration(self):
        """Show the configuration interface"""
        self.display_label.hide()
        self.config_widget.show()
    
    def hide_configuration(self):
        """Hide the configuration interface"""
        self.config_widget.hide()
        self.display_label.show()
    
    def set_letter(self, letter):
        """Display a single letter"""
        self.display_label.setText(letter.upper())
        self.display_label.setFont(QFont('Arial', 120, QFont.Weight.Bold))
    
    def show_instructions(self, config):
        """Show task instructions with configuration details"""
        practice_text = f"You will start with {config['practice_trials']} practice trials" if config['practice_enabled'] else "No practice trials"
        main_text = f"then complete {config['main_trials']} main trials" if config['main_enabled'] else "Practice trials only"
        
        if not config['practice_enabled']:
            practice_text = ""
            main_text = f"You will complete {config['main_trials']} trials"
        elif not config['main_enabled']:
            main_text = "Practice trials only"
        
        instruction_text = f"""CVC Task Instructions

{practice_text}
{main_text if main_text else ""}

Letters will appear ONE LETTER AT A TIME in a continuous stream.

Your task is to identify each time 3 consecutive letters make up a known 3-letter (consonant-vowel-consonant) word, for example P-E-N.

Press the SPACE BAR or LEFT MOUSE BUTTON to identify a word.

Example:
B - U - P - E - N - O - M
         ↑ P-E-N is a word!

Configuration:
Practice: {config['practice_letter_duration']}ms per letter, {config['practice_real_words']} words to find
Main: {config['main_letter_duration']}ms per letter, {config['main_real_words']} words to find

Press SPACE or LEFT MOUSE to start when ready."""
        
        self.display_label.setText(instruction_text)
        self.display_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
    
    def show_blank(self):
        """Show blank screen"""
        self.display_label.setText("")
    
    def show_completion_message(self, message):
        """Show completion/instruction messages"""
        self.display_label.setText(message)
        self.display_label.setFont(QFont('Arial', 28, QFont.Weight.Bold))

class CVCTask(TaskStateMixin, QWidget):
    """CVC Task with sequential letter presentation and comprehensive configuration"""
    
    TASK_NAME = "CVC Task"
    
    def __init__(self, csv_file=None, x_pos=None, y_pos=None, participant_id=None, participant_folder_path=None):
        # Initialize session manager FIRST if not already initialized
        if not get_session_manager() and participant_id and participant_folder_path:
            print("Initializing session manager from CVC task...")
            initialize_session_manager(participant_id, participant_folder_path)
        
        super().__init__()
        
        # Store participant information
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        
        # Task configuration (will be set after user configuration)
        self.task_config = None
        self.letter_duration_ms = DEFAULT_DISPLAY_DURATION
        
        # CVC-specific variables for sequential presentation
        self.stimulus_file = None
        self.current_letter = ""
        self.is_cvc_word = False
        self.letter_count = 0
        self.words_presented = 0
        
        # Task phase tracking
        self.practice_mode = False
        self.practice_completed = False
        self.main_mode = False
        
        # Performance tracking (separate for practice and main)
        self.practice_hits = 0
        self.practice_misses = 0
        self.practice_false_positives = 0
        self.practice_correct_rejections = 0
        
        self.main_hits = 0
        self.main_misses = 0
        self.main_false_positives = 0
        self.main_correct_rejections = 0
        
        # Set window properties
        self.setWindowTitle("CVC Task")
        
        # Check for recovery
        self.recovery_data = None
        self.recovery_offset = 0
        
        if self.session_manager:
            current_state = self.session_manager.get_current_task_state()
            if (current_state and 
                current_state.get('task_name') == self.TASK_NAME and
                current_state.get('status') == 'in_progress'):
                self.recovery_data = current_state
                print("Recovery data found - will resume from previous session")
        
        print(f"=== CVC TASK INITIALIZATION (COMPREHENSIVE CONFIG) ===")
        print(f"Participant ID: '{participant_id}'")
        print(f"Participant folder: '{participant_folder_path}'")
        print(f"Recovery mode: {'ENABLED' if self.recovery_data else 'DISABLED'}")
        print("Configuration: Practice + Main trials with full customization")
        print("=======================================================")
        
        # Task state variables
        self.configuration_mode = True
        self.configuration_saved = False
        
        # Task timing variables
        self.letter_onset_time = None
        self.response_time = None
        self.response_given = False
        
        # Pause/Resume state
        self.is_paused = False
        self.pause_timestamp = None
        
        # Task completion tracking
        self._task_completed = False
        self._completion_in_progress = False
        
        # Verify participant information
        if not participant_id or not participant_folder_path:
            print("ERROR: Missing participant information!")
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Missing Participant Information")
            error_msg.setText("Cannot start CVC task!")
            error_msg.setInformativeText("Participant information is missing.")
            error_msg.exec()
            self.close()
            return
        
        # Set window position
        if x_pos is not None and y_pos is not None:
            self.setGeometry(x_pos, y_pos, 1370, 960)
        else:
            screen = QApplication.primaryScreen().geometry()
            window_width, window_height = 1370, 960
            x = (screen.width() - window_width) // 2
            y = (screen.height() - window_height) // 2
            self.setGeometry(x, y, window_width, window_height)

        self.setStyleSheet("background-color: #f6f6f6;")
        
        # Trial data collection
        self.trial_data = []
        self.current_trial_info = None
        
        # Load stimulus data
        self.load_stimulus_file()
        
        # Create layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 50, 10, 50)
        
        # Create child window for display
        self.display_window = CVCDisplayWindow(self)
        
        # Create action button
        self.action_button = QPushButton("Save Configuration", self)
        self.action_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.action_button.setFixedSize(250, 70)
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffffff, stop: 1 #f0f0f0);
                color: black;
                border: 2px solid #e0e0e0;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fafafa, stop: 1 #e8e8e8);
                border: 2px solid #d0d0d0;
            }
        """)
        self.action_button.clicked.connect(self.action_button_clicked)
        
        # Add widgets to layout
        self.layout.addStretch()
        self.layout.addWidget(self.display_window, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addSpacing(30)
        self.layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addStretch()
        
        self.setLayout(self.layout)
        
        # Initialize trial state
        self.task_started = False
        
        # Initialize timers
        self.letter_timer = QTimer()
        self.letter_timer.timeout.connect(self.next_letter)
        
        # Set up keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Initialize recovery if needed
        if self.session_manager:
            print("Task recovery system activated")
            if self.recovery_data:
                QTimer.singleShot(100, self._update_recovery_ui)
    
    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for responses"""
        # Space bar shortcut
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self.handle_response)
        self.space_shortcut.setEnabled(False)  # Initially disabled
    
    def mousePressEvent(self, event):
        """Handle mouse clicks as responses"""
        if event.button() == Qt.MouseButton.LeftButton and self.space_shortcut.isEnabled():
            self.handle_response()
        super().mousePressEvent(event)
    
    def handle_response(self):
        """Handle participant response (space or left click)"""
        if not hasattr(self, 'awaiting_response') or not self.awaiting_response:
            return
        
        # Check if we're waiting for the start signal
        if hasattr(self, 'awaiting_start') and self.awaiting_start:
            print("Start signal received - beginning letter sequence")
            self.awaiting_response = False
            self.awaiting_start = False
            self.start_letter_sequence()
            return
        
        # Handle responses during letter presentation
        if not self.response_given:
            self.response_time = time.perf_counter()
            self.response_given = True
            print(f"Response detected at {self.response_time:.6f}")
    
    def load_stimulus_file(self):
        """Load the vmtcvc.txt stimulus file"""
        stimulus_path = resource_path('task_cvc/vmtcvc.txt')
        
        try:
            self.stimulus_lines = []
            with open(stimulus_path, 'r') as f:
                self.stimulus_lines = f.readlines()
            
            print(f"Loaded {len(self.stimulus_lines)} stimulus lines from vmtcvc.txt")
            
        except Exception as e:
            print(f"Could not load stimulus file: {e}")
            # Create minimal test data
            self.stimulus_lines = [
                "M,0,G,0\n", "U,0,A,0\n", "D,-1,T,-1\n",  # MUD word
                "A,0,E,0\n", "S,0,I,0\n", "T,-1,B,0\n"   # AST not a word, but marked
            ]
    
    def action_button_clicked(self):
        """Handle action button click based on current mode"""
        if self.configuration_mode and not self.configuration_saved:
            self.save_configuration()
        elif self.configuration_mode and self.configuration_saved:
            self.proceed_to_instructions()
        elif not self.task_started:
            self.start_task()
        else:
            self.toggle_pause()
    
    def save_configuration(self):
        """Save the task configuration"""
        is_valid, error_message = self.display_window.validate_configuration()
        if not is_valid:
            QMessageBox.warning(self, "Configuration Error", error_message)
            return
        
        self.task_config = self.display_window.get_configuration()
        
        print("=== CVC TASK CONFIGURATION SAVED ===")
        print(f"Practice enabled: {self.task_config['practice_enabled']}")
        print(f"Practice trials: {self.task_config['practice_trials']}")
        print(f"Practice letter duration: {self.task_config['practice_letter_duration']} ms")
        print(f"Practice stimulus list: {self.task_config['practice_stimulus_list']}")
        print(f"Practice real words: {self.task_config['practice_real_words']}")
        print(f"Main enabled: {self.task_config['main_enabled']}")
        print(f"Main trials: {self.task_config['main_trials']}")
        print(f"Main letter duration: {self.task_config['main_letter_duration']} ms")
        print(f"Main stimulus list: {self.task_config['main_stimulus_list']}")
        print(f"Main real words: {self.task_config['main_real_words']}")
        print("=====================================")
        
        self.configuration_saved = True
        
        # Update button
        self.action_button.setText("Next")
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #e8f5e8, stop: 1 #d4f4d4);
                color: black;
                border: 2px solid #4CAF50;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
        """)
        
        QMessageBox.information(self, "Configuration Saved", 
                              "Task configuration has been saved successfully!")
    
    def proceed_to_instructions(self):
        """Proceed to instructions"""
        self.display_window.hide_configuration()
        self.display_window.show_instructions(self.task_config)
        
        # Update button for task start
        self.action_button.setText("Start")
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fff3e0, stop: 1 #ffe0b2);
                color: black;
                border: 2px solid #FF9800;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
        """)
        
        self.configuration_mode = False
    
    def start_task(self):
        """Start the task with comprehensive configuration support"""
        if not self.task_started:
            self.task_started = True
            self.update_button_for_pause()
            
            # Start with recovery support
            if self.session_manager:
                task_config = {
                    'practice_enabled': self.task_config['practice_enabled'],
                    'practice_trials': self.task_config['practice_trials'],
                    'practice_letter_duration': self.task_config['practice_letter_duration'],
                    'practice_stimulus_list': self.task_config['practice_stimulus_list'],
                    'practice_real_words': self.task_config['practice_real_words'],
                    'main_enabled': self.task_config['main_enabled'],
                    'main_trials': self.task_config['main_trials'],
                    'main_letter_duration': self.task_config['main_letter_duration'],
                    'main_stimulus_list': self.task_config['main_stimulus_list'],
                    'main_real_words': self.task_config['main_real_words'],
                    'recovery_mode': bool(self.recovery_data),
                    'sequential_letters': True,
                    'comprehensive_configuration': True,
                    'user_configuration': self.task_config
                }
                
                if not self.recovery_data:
                    total_trials = 0
                    if self.task_config['practice_enabled']:
                        total_trials += self.task_config['practice_trials']
                    if self.task_config['main_enabled']:
                        total_trials += self.task_config['main_trials']
                    
                    self.start_task_with_recovery(task_config, total_trials)
            
            print("Starting CVC task with comprehensive configuration")
            
            # Determine what to start with based on configuration
            if self.task_config['practice_enabled'] and not self.practice_completed:
                self.start_practice_phase()
            elif self.task_config['main_enabled']:
                self.start_main_phase()
            else:
                print("No trials enabled - completing task")
                self.start_completion_sequence()
    
    def start_practice_phase(self):
        """Start the practice phase"""
        self.practice_mode = True
        self.main_mode = False
        self.words_presented = 0
        self.letter_count = 0
        
        # Set letter duration for practice
        self.letter_duration_ms = self.task_config['practice_letter_duration']
        
        print(f"=== STARTING PRACTICE PHASE ===")
        print(f"Practice trials: {self.task_config['practice_trials']}")
        print(f"Practice letter duration: {self.task_config['practice_letter_duration']} ms")
        print(f"Practice real words: {self.task_config['practice_real_words']}")
        print(f"Practice stimulus list: {self.task_config['practice_stimulus_list']}")
        
        self.show_practice_ready_prompt()
    
    def start_main_phase(self):
        """Start the main phase"""
        self.practice_mode = False
        self.main_mode = True
        self.words_presented = 0
        self.letter_count = 0
        
        # Set letter duration for main
        self.letter_duration_ms = self.task_config['main_letter_duration']
        
        print(f"=== STARTING MAIN PHASE ===")
        print(f"Main trials: {self.task_config['main_trials']}")
        print(f"Main letter duration: {self.task_config['main_letter_duration']} ms")
        print(f"Main real words: {self.task_config['main_real_words']}")
        print(f"Main stimulus list: {self.task_config['main_stimulus_list']}")
        
        if self.practice_completed:
            self.show_main_ready_prompt()
        else:
            self.show_main_only_ready_prompt()
    
    def show_practice_ready_prompt(self):
        """Show ready prompt for practice phase"""
        self.display_window.show_completion_message(
            f"PRACTICE PHASE\n\n"
            f"Press SPACE or LEFT MOUSE BUTTON to start practice\n\n"
            f"Practice settings:\n"
            f"• {self.task_config['practice_real_words']} words to find\n"
            f"• {self.task_config['practice_letter_duration']}ms per letter\n"
            f"• List {self.task_config['practice_stimulus_list']}"
        )
        
        # Enable response for starting
        self.space_shortcut.setEnabled(True)
        self.awaiting_start = True
        self.awaiting_response = True
    
    def show_main_ready_prompt(self):
        """Show ready prompt for main phase (after practice)"""
        self.display_window.show_completion_message(
            f"PRACTICE COMPLETE!\n\n"
            f"Now starting the main task.\n\n"
            f"Press SPACE or LEFT MOUSE BUTTON to start\n\n"
            f"Main settings:\n"
            f"• {self.task_config['main_real_words']} words to find\n"
            f"• {self.task_config['main_letter_duration']}ms per letter\n"
            f"• List {self.task_config['main_stimulus_list']}"
        )
        
        # Enable response for starting
        self.space_shortcut.setEnabled(True)
        self.awaiting_start = True
        self.awaiting_response = True
    
    def show_main_only_ready_prompt(self):
        """Show ready prompt for main phase only (no practice)"""
        self.display_window.show_completion_message(
            f"MAIN TASK\n\n"
            f"Press SPACE or LEFT MOUSE BUTTON to start\n\n"
            f"Task settings:\n"
            f"• {self.task_config['main_real_words']} words to find\n"
            f"• {self.task_config['main_letter_duration']}ms per letter\n"
            f"• List {self.task_config['main_stimulus_list']}"
        )
        
        # Enable response for starting
        self.space_shortcut.setEnabled(True)
        self.awaiting_start = True
        self.awaiting_response = True
    
    def start_letter_sequence(self):
        """Start the letter sequence presentation"""
        print(f"Starting letter sequence for {'practice' if self.practice_mode else 'main'} phase...")
        
        # Show blank screen briefly
        self.display_window.show_blank()
        
        # Wait 2 seconds then start presenting letters
        QTimer.singleShot(2000, self.next_letter)
    
    def get_next_letter(self):
        """Get the next letter from stimulus file based on current phase"""
        if self.letter_count >= len(self.stimulus_lines):
            return False
        
        line = self.stimulus_lines[self.letter_count].strip()
        if line:
            chars = line.split(',')
            
            # Get letter for selected list based on current phase
            if self.practice_mode:
                list_index = self.task_config['practice_stimulus_list']
            else:
                list_index = self.task_config['main_stimulus_list']
            
            letter_index = (list_index - 1) * 2  # 0 for list 1, 2 for list 2
            flag_index = (list_index * 2) - 1     # 1 for list 1, 3 for list 2
            
            self.current_letter = chars[letter_index]
            
            # Check if this letter completes a CVC word
            if int(chars[flag_index]) == -1:
                self.is_cvc_word = True
            else:
                self.is_cvc_word = False
            
            self.letter_count += 1
            return True
        
        return False
    
    def next_letter(self):
        """Present the next letter in sequence"""
        if self.is_paused:
            return
        
        # Check if we've presented enough words for current phase
        target_words = self.task_config['practice_real_words'] if self.practice_mode else self.task_config['main_real_words']
        
        if self.words_presented >= target_words:
            print(f"Target number of words reached for {'practice' if self.practice_mode else 'main'} phase")
            self.complete_current_phase()
            return
        
        # Get next letter
        if not self.get_next_letter():
            print("End of stimulus file reached")
            self.complete_current_phase()
            return
        
        # Reset response tracking for this letter
        self.response_given = False
        self.response_time = None
        self.awaiting_response = True
        
        # Display the letter
        self.display_window.set_letter(self.current_letter)
        self.letter_onset_time = time.perf_counter()
        
        print(f"Letter {self.letter_count}: {self.current_letter} (CVC: {self.is_cvc_word}) [{'Practice' if self.practice_mode else 'Main'}]")
        
        # Record trial data for the previous letter (if any)
        if self.letter_count > 1:
            self.record_trial_data()
        
        # Schedule next letter after duration
        self.letter_timer.start(self.letter_duration_ms)
    
    def complete_current_phase(self):
        """Complete the current phase and move to next or finish"""
        if self.practice_mode:
            print("=== PRACTICE PHASE COMPLETED ===")
            self.practice_completed = True
            self.practice_mode = False
            
            # Record final trial data for practice
            if hasattr(self, 'current_letter') and self.current_letter:
                self.record_trial_data()
            
            # Move to main phase if enabled
            if self.task_config['main_enabled']:
                QTimer.singleShot(1000, self.start_main_phase)
            else:
                self.start_completion_sequence()
        else:
            print("=== MAIN PHASE COMPLETED ===")
            self.main_mode = False
            
            # Record final trial data for main
            if hasattr(self, 'current_letter') and self.current_letter:
                self.record_trial_data()
            
            self.start_completion_sequence()
    
    def record_trial_data(self):
        """Record trial data for this letter with phase tracking"""
        assessment = self.check_response()
        
        trial_record = {
            'trial_number': self.letter_count,
            'letter': self.current_letter,
            'phase': 'practice' if self.practice_mode else 'main',
            'response_given': "Yes" if self.response_given else "No",
            'assessment': assessment,
            'is_cvc_word': self.is_cvc_word,
            'letter_onset_time': self.letter_onset_time,
            'response_time': self.response_time if self.response_time else "",
            'reaction_time_ms': (self.response_time - self.letter_onset_time) * 1000 if self.response_time else "",
            'words_presented': self.words_presented,
            'letter_duration_ms': self.letter_duration_ms,
            'stimulus_list': self.task_config['practice_stimulus_list'] if self.practice_mode else self.task_config['main_stimulus_list'],
            'user_configuration': self.task_config
        }
        
        # Save with recovery support
        if self.session_manager:
            self.save_trial_with_recovery(trial_record)
        else:
            self.trial_data.append(trial_record)
        
        print(f"Letter {self.letter_count}: {self.current_letter} - {assessment} [{'Practice' if self.practice_mode else 'Main'}]")
    
    def check_response(self):
        """Check if the response was appropriate with phase-specific tracking"""
        if self.letter_count < 3:
            # Not enough letters for a word yet
            if self.response_given:
                if self.practice_mode:
                    self.practice_false_positives += 1
                else:
                    self.main_false_positives += 1
                return "Incorrect (not enough characters)"
            else:
                return "---"
        else:
            if self.is_cvc_word:
                # This letter completes a CVC word
                self.words_presented += 1
                
                if self.response_given:
                    if self.practice_mode:
                        self.practice_hits += 1
                        return "Correct (PRACTICE)"
                    else:
                        self.main_hits += 1
                        return "Correct"
                else:
                    if self.practice_mode:
                        self.practice_misses += 1
                        return "Incorrect: word missed (PRACTICE)"
                    else:
                        self.main_misses += 1
                        return "Incorrect: word missed"
            else:
                # Not a CVC word
                if self.response_given:
                    if self.practice_mode:
                        self.practice_false_positives += 1
                        return "Incorrect: false positive (PRACTICE)"
                    else:
                        self.main_false_positives += 1
                        return "Incorrect: false positive"
                else:
                    if self.practice_mode:
                        self.practice_correct_rejections += 1
                    else:
                        self.main_correct_rejections += 1
                    return "---"
    
    def update_button_for_pause(self):
        """Update button for pause functionality"""
        self.action_button.setText("Pause")
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffeeee, stop: 1 #ffdddd);
                color: black;
                border: 2px solid #e0a0a0;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
        """)
    
    def toggle_pause(self):
        """Toggle pause state"""
        if self.is_paused:
            self.resume_task()
        else:
            self.pause_task()
    
    def pause_task(self):
        """Pause the task"""
        self.is_paused = True
        self.letter_timer.stop()
        self.space_shortcut.setEnabled(False)
        
        # Emergency save
        if self.session_manager:
            try:
                self._auto_save_task_state()
                print("Emergency save completed during pause")
            except Exception as e:
                print(f"Error during emergency save: {e}")
        
        # Update button
        self.action_button.setText("Continue")
        self.display_window.show_completion_message("TASK PAUSED\n\nClick Continue to resume")
    
    def resume_task(self):
        """Resume the task"""
        self.is_paused = False
        self.update_button_for_pause()
        self.space_shortcut.setEnabled(True)
        
        # Continue with next letter
        self.next_letter()
    
    def start_completion_sequence(self):
        """Start task completion sequence"""
        self._completion_in_progress = True
        self.letter_timer.stop()
        self.space_shortcut.setEnabled(False)
        
        # Hide action button
        self.action_button.hide()
        
        # Show completion message
        self.display_window.show_completion_message("CVC Task Completed")
        
        # Continue with data saving
        QTimer.singleShot(500, self.show_processing_message)
    
    def show_processing_message(self):
        """Show processing message and save data"""
        self.display_window.show_completion_message("Processing collected data")
        QTimer.singleShot(100, self.run_analysis_and_show_results)
    
    def run_analysis_and_show_results(self):
        """Save data and show final results"""
        # Record trial data for the last letter
        if hasattr(self, 'current_letter') and self.current_letter:
            self.record_trial_data()
        
        # Save data
        self.save_trial_data()
        
        # Mark task as completed
        if self.session_manager:
            self._task_completed = True
            final_data = {
                'total_letters_presented': self.letter_count,
                'practice_completed': self.practice_completed,
                'practice_hits': self.practice_hits,
                'practice_misses': self.practice_misses,
                'practice_false_positives': self.practice_false_positives,
                'practice_correct_rejections': self.practice_correct_rejections,
                'main_hits': self.main_hits,
                'main_misses': self.main_misses,
                'main_false_positives': self.main_false_positives,
                'main_correct_rejections': self.main_correct_rejections,
                'completion_time': datetime.now().isoformat(),
                'recovery_was_used': bool(self.recovery_data),
                'task_completed_normally': True,
                'comprehensive_configuration': True,
                'user_configuration': self.task_config
            }
            
            self.complete_task_with_recovery(final_data)
        
        # Show completion results
        self.show_completion_results()
    
    def show_completion_results(self):
        """Show final completion results with phase breakdown"""
        # Calculate performance metrics
        practice_accuracy = 0
        main_accuracy = 0
        
        if self.practice_hits + self.practice_misses > 0:
            practice_accuracy = (self.practice_hits / (self.practice_hits + self.practice_misses)) * 100
        
        if self.main_hits + self.main_misses > 0:
            main_accuracy = (self.main_hits / (self.main_hits + self.main_misses)) * 100
        
        completion_text = (
            f"Processing Complete\n\n"
            f"Configuration:\n"
            f"Practice: {'Enabled' if self.task_config['practice_enabled'] else 'Disabled'}\n"
            f"Main: {'Enabled' if self.task_config['main_enabled'] else 'Disabled'}\n\n"
        )
        
        if self.task_config['practice_enabled']:
            completion_text += (
                f"Practice Results:\n"
                f"Hits: {self.practice_hits}, Misses: {self.practice_misses}\n"
                f"False positives: {self.practice_false_positives}\n"
                f"Accuracy: {practice_accuracy:.1f}%\n\n"
            )
        
        if self.task_config['main_enabled']:
            completion_text += (
                f"Main Results:\n"
                f"Hits: {self.main_hits}, Misses: {self.main_misses}\n"
                f"False positives: {self.main_false_positives}\n"
                f"Accuracy: {main_accuracy:.1f}%\n\n"
            )
        
        completion_text += (
            f"Total letters: {self.letter_count}\n"
            f"Recovery used: {'Yes' if self.recovery_data else 'No'}\n\n"
            f"Data saved successfully"
        )
        
        self.display_window.show_completion_message(completion_text)
        
        # Show Main Menu button
        self.show_main_menu_button()
    
    def show_main_menu_button(self):
        """Show Main Menu button"""
        self.main_menu_button = QPushButton("Main Menu", self)
        self.main_menu_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.main_menu_button.setFixedSize(200, 70)
        self.main_menu_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffffff, stop: 1 #f0f0f0);
                color: black;
                border: 2px solid #e0e0e0;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
        """)
        self.main_menu_button.clicked.connect(self.return_to_main_menu)
        
        self.layout.addWidget(self.main_menu_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_menu_button.show()
    
    def return_to_main_menu(self):
        """Return to the test selection menu"""
        from menu_selection import SelectionMenu
        
        current_geometry = self.geometry()
        
        self.selection_menu = SelectionMenu(
            buttons_size=1.0,
            buttons_elevation=0.5,
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        self.selection_menu.setGeometry(current_geometry)
        self.selection_menu.show()
        
        self.close()
    
    def save_trial_data(self):
        """Save trial data using modular experiment data saver"""
        if not self.participant_folder_path:
            print("ERROR: No participant folder path available")
            return False
        
        # Create CVC task folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cvc_folder_name = f"cvctask_{timestamp}"
        cvc_folder_path = os.path.join(self.participant_folder_path, cvc_folder_name)
        
        try:
            os.makedirs(cvc_folder_path, exist_ok=True)
            print(f"Created CVC task folder: {cvc_folder_path}")
        except Exception as e:
            print(f"Error creating CVC folder: {e}")
            return False
        
        # Use the existing data saver with enhanced configuration
        success = save_cvc_data(
            trial_data=self.trial_data,
            participant_id=self.participant_id,
            cvc_folder_path=cvc_folder_path,
            display_duration_ms=self.letter_duration_ms,
            iti_duration_ms=0,  # No ITI in sequential presentation
            task_config=self.task_config
        )
        
        return success
    
    def _get_task_specific_state(self):
        """Get CVC-specific state information for recovery"""
        state = super()._get_task_specific_state() if hasattr(super(), '_get_task_specific_state') else {}
        
        state.update({
            'letter_count': getattr(self, 'letter_count', 0),
            'words_presented': getattr(self, 'words_presented', 0),
            'practice_mode': getattr(self, 'practice_mode', False),
            'practice_completed': getattr(self, 'practice_completed', False),
            'main_mode': getattr(self, 'main_mode', False),
            'practice_hits': getattr(self, 'practice_hits', 0),
            'practice_misses': getattr(self, 'practice_misses', 0),
            'practice_false_positives': getattr(self, 'practice_false_positives', 0),
            'practice_correct_rejections': getattr(self, 'practice_correct_rejections', 0),
            'main_hits': getattr(self, 'main_hits', 0),
            'main_misses': getattr(self, 'main_misses', 0),
            'main_false_positives': getattr(self, 'main_false_positives', 0),
            'main_correct_rejections': getattr(self, 'main_correct_rejections', 0),
            'task_config': getattr(self, 'task_config', None),
            'letter_duration_ms': self.letter_duration_ms,
            'sequential_presentation': True,
            'comprehensive_configuration': True
        })
        
        return state
    
    def _update_recovery_ui(self):
        """Update UI elements after recovery"""
        if self.recovery_data:
            # Restore task configuration from recovery data
            stored_config = self.recovery_data.get('task_specific_state', {}).get('task_config')
            
            if stored_config:
                self.task_config = stored_config
                print("Recovered comprehensive CVC configuration from previous session")
                print(f"Configuration: {self.task_config}")
                
                # Skip configuration mode and go directly to instructions
                self.configuration_mode = False
                self.configuration_saved = True
                
                # Update UI to show instructions with recovered config
                self.display_window.hide_configuration()
                
                # Show recovery message
                trials_completed = len(self.recovery_data.get('trial_data', []))
                
                recovery_message = (
                    f"SESSION RECOVERED\n\n"
                    f"Continuing CVC task from where you left off...\n\n"
                    f"Letters completed: {trials_completed}\n\n"
                    f"Comprehensive configuration preserved\n"
                    f"Click Start to continue"
                )
                
                self.display_window.show_completion_message(recovery_message)
                
                # Update button for task start
                self.action_button.setText("Start")
                self.action_button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                  stop: 0 #fff3e0, stop: 1 #ffe0b2);
                        color: black;
                        border: 2px solid #FF9800;
                        border-radius: 35px;
                        padding: 10px;
                        font-weight: bold;
                    }
                """)
            else:
                print("Warning: No comprehensive task configuration found in recovery data")
                # Fall back to default configuration
                self.task_config = {
                    'practice_enabled': True,
                    'practice_trials': DEFAULT_PRACTICE_TRIALS,
                    'practice_letter_duration': DEFAULT_DISPLAY_DURATION,
                    'practice_stimulus_list': 1,
                    'practice_real_words': 5,
                    'main_enabled': True,
                    'main_trials': DEFAULT_NUM_TRIALS,
                    'main_letter_duration': DEFAULT_DISPLAY_DURATION,
                    'main_stimulus_list': 1,
                    'main_real_words': 25
                }
            
            print("Recovery UI updated with comprehensive configuration support")
    
    def closeEvent(self, event):
        """Handle window close event"""
        print("CVC task closing - performing cleanup...")
        
        # Emergency save if task is in progress
        if self.session_manager and hasattr(self, 'task_started') and self.task_started:
            try:
                if (not hasattr(self, '_task_completed') or not self._task_completed) and \
                   (not hasattr(self, '_completion_in_progress') or not self._completion_in_progress):
                    print("Emergency save: CVC task in progress during close")
                    self.handle_crash_recovery()
                else:
                    print("CVC task was completed normally - no emergency save needed")
            except Exception as e:
                print(f"Error during emergency save: {e}")
        
        # Stop timers
        if hasattr(self, 'letter_timer'):
            self.letter_timer.stop()
        
        event.accept()
        print("CVC task cleanup completed")

def main():
    """Standalone main function for testing"""
    app = QApplication(sys.argv)
    
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")
    
    print("=== CVC TASK TESTING (COMPREHENSIVE CONFIGURATION) ===")
    print("Practice + Main trials with full customization")
    print("Testing with sample participant data...")
    
    # Sample participant data
    sample_participant_id = "TEST_CVC_001"
    sample_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_CVC_001")
    
    os.makedirs(sample_folder, exist_ok=True)
    
    # Initialize session manager
    try:
        session_manager = initialize_session_manager(sample_participant_id, sample_folder)
        default_tasks = ["CVC Task"]
        session_manager.set_task_queue(default_tasks)
        print("Session manager initialized for testing")
    except Exception as e:
        print(f"Error initializing session manager: {e}")
    
    # Create CVC task
    txt_path = resource_path('task_cvc/vmtcvc.txt')
    
    try:
        cvc_task = CVCTask(
            csv_file=txt_path,
            participant_id=sample_participant_id,
            participant_folder_path=sample_folder
        )
        
        cvc_task.show()
        print("✓ CVC Task launched with comprehensive configuration interface")
        print("✓ Practice and Main trials fully configurable")
        print("✓ Separate performance tracking for each phase")
        
        exit_code = app.exec()
        print("CVC task closed normally")
        return exit_code
        
    except Exception as e:
        print(f"CVC task crashed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        from crash_recovery_system.session_manager import cleanup_session_manager
        cleanup_session_manager()
        print("Session cleanup completed")

if __name__ == "__main__":
    main()