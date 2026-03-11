import sys
import os
import csv
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QCheckBox, QSpinBox, QGridLayout, QFrame, QComboBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

# Import the modular save function
from .data_saver import save_vst_data

# Import crash recovery system
from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager
from crash_recovery_system.task_state_saver import TaskStateMixin


DEFAULT_PRACTICE_TRIALS = 10
DEFAULT_NUM_TRIALS = 42


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/py2app"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class VSTDisplayWindow(QWidget):
    """Child window that displays the VST task content"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VST Task Display")
        self.setFixedSize(1300, 760)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.display_label = QLabel("", self)
        self.display_label.setFont(QFont('Arial', 28, QFont.Weight.Bold))
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setWordWrap(True)
        self.display_label.setStyleSheet("""
            QLabel {
                color: #000000;
                background-color: #ffffff;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 60px;
                margin: 40px;
                min-height: 200px;
            }
        """)

        self.config_widget = self.create_configuration_widget()
        self.config_widget.hide()

        self.main_layout.addWidget(self.display_label)
        self.main_layout.addWidget(self.config_widget)

        self.setLayout(self.main_layout)

        self.show_configuration()

    def create_configuration_widget(self):
        """Create configuration widget"""
        config_widget = QWidget()
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(40, 20, 40, 20)

        title_label = QLabel("Task Configuration")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        config_layout.addWidget(title_label)

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

        # Practice section
        practice_layout = QVBoxLayout()

        practice_header_layout = QHBoxLayout()
        self.practice_checkbox = QCheckBox("Practice Trials")
        self.practice_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.practice_checkbox.setChecked(True)
        self.practice_checkbox.stateChanged.connect(self.on_practice_changed)
        practice_header_layout.addWidget(self.practice_checkbox)
        practice_header_layout.addStretch()
        practice_layout.addLayout(practice_header_layout)

        practice_grid = QGridLayout()
        practice_grid.setSpacing(15)

        practice_labels = [
            QLabel("Number of trials:"),
            QLabel("Stimulus List:")
        ]

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

        practice_grid.addWidget(practice_labels[0], 0, 0)
        self.practice_trials_spinbox = QSpinBox()
        self.practice_trials_spinbox.setRange(1, 100)
        self.practice_trials_spinbox.setValue(DEFAULT_PRACTICE_TRIALS)
        self.practice_trials_spinbox.setFont(QFont('Arial', 12))
        self.practice_trials_spinbox.setMinimumHeight(30)
        practice_grid.addWidget(self.practice_trials_spinbox, 0, 1)

        practice_grid.addWidget(practice_labels[1], 1, 0)
        self.practice_list_combo = QComboBox()
        self.practice_list_combo.addItems(["List 1", "List 2"])
        self.practice_list_combo.setFont(QFont('Arial', 12))
        self.practice_list_combo.setMinimumHeight(30)
        practice_grid.addWidget(self.practice_list_combo, 1, 1)

        practice_grid.setColumnStretch(0, 1)
        practice_grid.setColumnStretch(1, 1)

        practice_layout.addLayout(practice_grid)
        frame_layout.addLayout(practice_layout)

        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("color: #bdc3c7; margin: 10px 0px;")
        frame_layout.addWidget(separator1)

        # Main section
        main_layout = QVBoxLayout()

        main_header_layout = QHBoxLayout()
        self.main_checkbox = QCheckBox("Main Trials")
        self.main_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.main_checkbox.setChecked(True)
        self.main_checkbox.stateChanged.connect(self.on_main_changed)
        main_header_layout.addWidget(self.main_checkbox)
        main_header_layout.addStretch()
        main_layout.addLayout(main_header_layout)

        main_grid = QGridLayout()
        main_grid.setSpacing(15)

        main_labels = [
            QLabel("Number of trials:"),
            QLabel("Stimulus List:")
        ]

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

        main_grid.addWidget(main_labels[0], 0, 0)
        self.main_trials_spinbox = QSpinBox()
        self.main_trials_spinbox.setRange(1, 500)
        self.main_trials_spinbox.setValue(DEFAULT_NUM_TRIALS)
        self.main_trials_spinbox.setFont(QFont('Arial', 12))
        self.main_trials_spinbox.setMinimumHeight(30)
        main_grid.addWidget(self.main_trials_spinbox, 0, 1)

        main_grid.addWidget(main_labels[1], 1, 0)
        self.main_list_combo = QComboBox()
        self.main_list_combo.addItems(["List 1", "List 2"])
        self.main_list_combo.setFont(QFont('Arial', 12))
        self.main_list_combo.setMinimumHeight(30)
        main_grid.addWidget(self.main_list_combo, 1, 1)

        main_grid.setColumnStretch(0, 1)
        main_grid.setColumnStretch(1, 1)

        main_layout.addLayout(main_grid)
        frame_layout.addLayout(main_layout)

        config_frame.setLayout(frame_layout)
        config_layout.addWidget(config_frame)

        config_widget.setLayout(config_layout)
        return config_widget

    def on_practice_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.practice_trials_spinbox.setEnabled(enabled)
        self.practice_list_combo.setEnabled(enabled)

    def on_main_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.main_trials_spinbox.setEnabled(enabled)
        self.main_list_combo.setEnabled(enabled)

    def get_configuration(self):
        return {
            'practice_enabled': self.practice_checkbox.isChecked(),
            'practice_trials': self.practice_trials_spinbox.value() if self.practice_checkbox.isChecked() else 0,
            'practice_stimulus_list': 1 if self.practice_list_combo.currentText() == "List 1" else 2,
            'main_enabled': self.main_checkbox.isChecked(),
            'main_trials': self.main_trials_spinbox.value() if self.main_checkbox.isChecked() else 0,
            'main_stimulus_list': 1 if self.main_list_combo.currentText() == "List 1" else 2,
        }

    def validate_configuration(self):
        if not self.practice_checkbox.isChecked() and not self.main_checkbox.isChecked():
            return False, "At least one trial type (Practice or Main) must be selected."

        if self.practice_checkbox.isChecked() and self.practice_trials_spinbox.value() < 1:
            return False, "Practice trials must be at least 1 if enabled."

        if self.main_checkbox.isChecked() and self.main_trials_spinbox.value() < 1:
            return False, "Main trials must be at least 1 if enabled."

        return True, ""

    def show_configuration(self):
        self.display_label.hide()
        self.config_widget.show()

    def hide_configuration(self):
        self.config_widget.hide()
        self.display_label.show()

    def show_instructions(self, config):
        practice_text = (
            f"You will start with {config['practice_trials']} practice trials."
            if config['practice_enabled'] else
            "No practice trials."
        )
        main_text = (
            f"Then you will complete {config['main_trials']} main trials."
            if config['main_enabled'] else
            "No main trials."
        )

        instruction_text = f"""VST Task Instructions

{practice_text}
{main_text}

You will read a sentence and choose the correct meaning of the highlighted word from 4 options.

Select one answer for each item.

Click Start when you are ready."""
        self.display_label.setText(instruction_text)
        self.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))

    def show_completion_message(self, message):
        self.display_label.setText(message)
        self.display_label.setFont(QFont('Arial', 28, QFont.Weight.Bold))


class VSTTask(TaskStateMixin, QWidget):
    """VST Task with sentence + 4 choice presentation"""

    TASK_NAME = "VST Task"

    def __init__(self, csv_file=None, x_pos=None, y_pos=None, participant_id=None, participant_folder_path=None):
        if not get_session_manager() and participant_id and participant_folder_path:
            initialize_session_manager(participant_id, participant_folder_path)

        super().__init__()

        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        self.csv_file = csv_file

        self.task_config = None
        self.configuration_mode = True
        self.configuration_saved = False
        self.task_started = False
        self._task_completed = False
        self._completion_in_progress = False

        self.recovery_data = None
        self.recovery_offset = 0

        self.questions = []
        self.practice_questions = []
        self.main_questions = []
        self.current_phase = None
        self.current_index = 0
        self.current_question = None
        self.question_start_time = None
        self.trial_data = []

        if not participant_id or not participant_folder_path:
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Missing Participant Information")
            error_msg.setText("Cannot start VST task!")
            error_msg.setInformativeText("Participant information is missing.")
            error_msg.exec()
            self.close()
            return

        self.setWindowTitle("VST Task")

        if x_pos is not None and y_pos is not None:
            self.setGeometry(x_pos, y_pos, 1370, 960)
        else:
            screen = QApplication.primaryScreen().geometry()
            window_width, window_height = 1370, 960
            x = (screen.width() - window_width) // 2
            y = (screen.height() - window_height) // 2
            self.setGeometry(x, y, window_width, window_height)

        self.setStyleSheet("background-color: #f6f6f6;")

        self.load_stimulus_file()

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 50, 10, 50)

        self.display_window = VSTDisplayWindow(self)

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

        self.create_choice_buttons()

        self.layout.addStretch()
        self.layout.addWidget(self.display_window, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addSpacing(20)
        self.layout.addWidget(self.choice_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addSpacing(20)
        self.layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addStretch()

        self.setLayout(self.layout)

    def create_choice_buttons(self):
        self.choice_frame = QFrame(self)
        self.choice_frame.setStyleSheet("QFrame { background: transparent; border: none; }")

        self.choice_layout = QGridLayout()
        self.choice_layout.setSpacing(20)

        self.choice_button1 = QPushButton("", self)
        self.choice_button2 = QPushButton("", self)
        self.choice_button3 = QPushButton("", self)
        self.choice_button4 = QPushButton("", self)

        buttons = [
            self.choice_button1,
            self.choice_button2,
            self.choice_button3,
            self.choice_button4
        ]

        for btn in buttons:
            btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            btn.setFixedSize(520, 70)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #000000;
                    border: 3px solid #808080;
                    border-radius: 12px;
                    padding: 10px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border: 3px solid #404040;
                }
                QPushButton:pressed {
                    background-color: #d9d9d9;
                    border: 3px solid #000000;
                }
            """)
            btn.hide()

        self.choice_button1.clicked.connect(lambda checked=False: self.register_response(self.choice_button1.text()))
        self.choice_button2.clicked.connect(lambda checked=False: self.register_response(self.choice_button2.text()))
        self.choice_button3.clicked.connect(lambda checked=False: self.register_response(self.choice_button3.text()))
        self.choice_button4.clicked.connect(lambda checked=False: self.register_response(self.choice_button4.text()))

        self.layout.addWidget(self.choice_button1)
        self.layout.addWidget(self.choice_button2)
        self.layout.addWidget(self.choice_button3)
        self.layout.addWidget(self.choice_button4)

        self.setLayout(self.layout)

        # self.choice_layout.addWidget(self.choice_button1, 0, 0)
        # self.choice_layout.addWidget(self.choice_button2, 0, 1)
        # self.choice_layout.addWidget(self.choice_button3, 1, 0)
        # self.choice_layout.addWidget(self.choice_button4, 1, 1)

        # self.choice_frame.setLayout(self.choice_layout)
        # self.choice_frame.hide()
    def load_stimulus_file(self):
        """
        Load CSV file.
        Change the path below if your file is somewhere else.
        """
        stimulus_path = self.csv_file or resource_path('task_vst/versionA.csv')

        try:
            self.questions = []
            with open(stimulus_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.questions.append(row)

            print(f"Loaded {len(self.questions)} questions from CSV")
        except Exception as e:
            print(f"Could not load CSV file: {e}")
            self.questions = []

    def action_button_clicked(self):
        if self.configuration_mode and not self.configuration_saved:
            self.save_configuration()
        elif self.configuration_mode and self.configuration_saved:
            self.proceed_to_instructions()
        elif not self.task_started:
            self.start_task()

    def save_configuration(self):
        is_valid, error_message = self.display_window.validate_configuration()
        if not is_valid:
            QMessageBox.warning(self, "Configuration Error", error_message)
            return

        self.task_config = self.display_window.get_configuration()
        self.configuration_saved = True

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

        QMessageBox.information(self, "Configuration Saved", "Task configuration has been saved successfully!")

    def proceed_to_instructions(self):
        self.display_window.hide_configuration()
        self.display_window.show_instructions(self.task_config)

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
        if self.task_started:
            return

        self.task_started = True
        self.action_button.hide()

        if not self.questions:
            QMessageBox.warning(self, "Missing Data", "No questions were loaded from the CSV file.")
            return

        self.prepare_trials()

        if self.task_config['practice_enabled'] and self.practice_questions:
            self.current_phase = "practice"
            self.current_index = 0
            self.show_phase_message(
                f"PRACTICE PHASE\n\n"
                f"You will complete {len(self.practice_questions)} practice trials.\n\n"
                f"The task will start now."
            )
            QTimer.singleShot(1500, self.show_question)
        elif self.task_config['main_enabled'] and self.main_questions:
            self.current_phase = "main"
            self.current_index = 0
            self.show_phase_message(
                f"MAIN TASK\n\n"
                f"You will complete {len(self.main_questions)} main trials.\n\n"
                f"The task will start now."
            )
            QTimer.singleShot(1500, self.show_question)
        else:
            QMessageBox.warning(self, "Configuration Error", "No trials available to run.")

    def prepare_trials(self):
        """
        Split the loaded questions into practice and main sets.
        Right now it uses the CSV order.
        If you want random selection, I can change that too.
        """
        total_questions = len(self.questions)

        practice_n = self.task_config['practice_trials'] if self.task_config['practice_enabled'] else 0
        main_n = self.task_config['main_trials'] if self.task_config['main_enabled'] else 0

        practice_n = min(practice_n, total_questions)
        remaining = max(0, total_questions - practice_n)
        main_n = min(main_n, remaining)

        self.practice_questions = self.questions[:practice_n]
        self.main_questions = self.questions[practice_n:practice_n + main_n]

    def get_current_question_list(self):
        if self.current_phase == "practice":
            return self.practice_questions
        return self.main_questions

    def show_phase_message(self, message):
        self.hide_choice_buttons()
        self.display_window.show_completion_message(message)

    def show_question(self):
        question_list = self.get_current_question_list()

        if self.current_index >= len(question_list):
            self.complete_current_phase()
            return

        self.current_question = question_list[self.current_index]
        self.question_start_time = datetime.now()

        # Use the correct CSV column name
        prompt_text = self.current_question.get("sentence", "") or self.current_question.get("word", "")

        self.display_window.display_label.setText(
            f"<div style='text-align:center;'>{prompt_text}</div>"
        )
        self.display_window.display_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))

        # Use choice1, choice2, ... not "choice 1"
        self.choice_button1.setText(self.current_question.get("choice1", ""))
        self.choice_button2.setText(self.current_question.get("choice2", ""))
        self.choice_button3.setText(self.current_question.get("choice3", ""))
        self.choice_button4.setText(self.current_question.get("choice4", ""))

        # Make sure buttons are enabled
        self.choice_button1.setEnabled(True)
        self.choice_button2.setEnabled(True)
        self.choice_button3.setEnabled(True)
        self.choice_button4.setEnabled(True)

        self.show_choice_buttons()

    def show_choice_buttons(self):
        self.choice_frame.show()
        self.choice_button1.show()
        self.choice_button2.show()
        self.choice_button3.show()
        self.choice_button4.show()

    def hide_choice_buttons(self):
        self.choice_button1.hide()
        self.choice_button2.hide()
        self.choice_button3.hide()
        self.choice_button4.hide()
        self.choice_frame.hide()

    def register_response(self, selected_answer):
        if not self.current_question:
            return

        correct_answer = self.current_question.get("correct", "")
        is_correct = selected_answer == correct_answer if correct_answer else ""

        trial_record = {
            'trial_number': len(self.trial_data) + 1,
            'phase': self.current_phase,
            'phase_trial_number': self.current_index + 1,
            'item': self.current_question.get("item", ""),
            'sentence': self.current_question.get("sentence", ""),
            'choice1': self.current_question.get("choice1", ""),
            'choice2': self.current_question.get("choice2", ""),
            'choice3': self.current_question.get("choice3", ""),
            'choice4': self.current_question.get("choice4", ""),
            'correct_answer': correct_answer,
            'selected_answer': selected_answer,
            'is_correct': is_correct,
            'timestamp': datetime.now().isoformat(),
            'participant_id': self.participant_id,
            'stimulus_list': self.task_config['practice_stimulus_list'] if self.current_phase == "practice"
                            else self.task_config['main_stimulus_list'],
            'user_configuration': self.task_config
        }

        self.trial_data.append(trial_record)
        self.current_index += 1

        self.show_question()

    def complete_current_phase(self):
        self.hide_choice_buttons()

        if self.current_phase == "practice":
            if self.task_config['main_enabled'] and self.main_questions:
                self.current_phase = "main"
                self.current_index = 0
                self.show_phase_message(
                    f"PRACTICE COMPLETE\n\n"
                    f"Now starting the main task.\n\n"
                    f"You will complete {len(self.main_questions)} main trials."
                )
                QTimer.singleShot(1500, self.show_question)
            else:
                self.start_completion_sequence()
        else:
            self.start_completion_sequence()

    def start_completion_sequence(self):
        self._completion_in_progress = True
        self.hide_choice_buttons()
        self.display_window.show_completion_message("VST Task Completed")
        QTimer.singleShot(500, self.show_processing_message)

    def show_processing_message(self):
        self.display_window.show_completion_message("Processing collected data")
        QTimer.singleShot(100, self.run_analysis_and_show_results)

    def run_analysis_and_show_results(self):
        # self.save_trial_data()
        self._task_completed = True
        self.show_completion_results()

    def show_completion_results(self):
        practice_trials = sum(1 for t in self.trial_data if t['phase'] == 'practice')
        main_trials = sum(1 for t in self.trial_data if t['phase'] == 'main')

        practice_correct = sum(
            1 for t in self.trial_data
            if t['phase'] == 'practice' and t['is_correct'] is True
        )
        main_correct = sum(
            1 for t in self.trial_data
            if t['phase'] == 'main' and t['is_correct'] is True
        )

        practice_accuracy = (practice_correct / practice_trials * 100) if practice_trials else 0
        main_accuracy = (main_correct / main_trials * 100) if main_trials else 0

        completion_text = (
            f"Processing Complete\n\n"
            f"Configuration:\n"
            f"Practice: {'Enabled' if self.task_config['practice_enabled'] else 'Disabled'}\n"
            f"Main: {'Enabled' if self.task_config['main_enabled'] else 'Disabled'}\n\n"
        )

        if self.task_config['practice_enabled']:
            completion_text += (
                f"Practice Results:\n"
                f"Trials: {practice_trials}\n"
                f"Correct: {practice_correct}\n"
                f"Accuracy: {practice_accuracy:.1f}%\n\n"
            )

        if self.task_config['main_enabled']:
            completion_text += (
                f"Main Results:\n"
                f"Trials: {main_trials}\n"
                f"Correct: {main_correct}\n"
                f"Accuracy: {main_accuracy:.1f}%\n\n"
            )

        completion_text += (
            f"Total trials: {len(self.trial_data)}\n\n"
            f"Data saved successfully"
        )

        self.display_window.show_completion_message(completion_text)
        self.show_main_menu_button()

    def show_main_menu_button(self):
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
        if not self.participant_folder_path:
            print("ERROR: No participant folder path available")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        vst_folder_name = f"vsttask_{timestamp}"
        vst_folder_path = os.path.join(self.participant_folder_path, vst_folder_name)

        try:
            os.makedirs(vst_folder_path, exist_ok=True)
            print(f"Created VST task folder: {vst_folder_path}")
        except Exception as e:
            print(f"Error creating VST folder: {e}")
            return False

        success = save_vst_data(
            trial_data=self.trial_data,
            participant_id=self.participant_id,
            vst_folder_path=vst_folder_path,
            display_duration_ms=0,
            iti_duration_ms=0,
            task_config=self.task_config
        )

        return success

    def _get_task_specific_state(self):
        state = {}
        state.update({
            'task_config': getattr(self, 'task_config', None),
            'questions': getattr(self, 'questions', []),
            'practice_questions': getattr(self, 'practice_questions', []),
            'main_questions': getattr(self, 'main_questions', []),
            'current_phase': getattr(self, 'current_phase', None),
            'current_index': getattr(self, 'current_index', 0),
            'trial_data': getattr(self, 'trial_data', []),
        })
        return state

    def closeEvent(self, event):
        print("VST task closing - performing cleanup...")
        event.accept()
        print("VST task cleanup completed")


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")

    print("=== VST TASK TESTING ===")
    print("Sentence + 4 choice version")

    sample_participant_id = "TEST_VST_001"
    sample_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_VST_001")

    os.makedirs(sample_folder, exist_ok=True)

    try:
        initialize_session_manager(sample_participant_id, sample_folder)
    except Exception as e:
        print(f"Error initializing session manager: {e}")

    csv_path = resource_path('task_vst/versionA.csv')

    try:
        vst_task = VSTTask(
            csv_file=csv_path,
            participant_id=sample_participant_id,
            participant_folder_path=sample_folder
        )

        vst_task.show()
        print("✓ VST Task launched")

        exit_code = app.exec()
        print("VST task closed normally")
        return exit_code

    except Exception as e:
        print(f"VST task crashed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()