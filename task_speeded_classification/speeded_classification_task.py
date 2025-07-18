from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtGui import QFont

import os
from datetime import datetime
import time

class SpeededClassificationTask(QWidget):
    def __init__(self, x_pos, y_pos, participant_id, participant_folder_path):
        super().__init__()
        self.setWindowTitle("Speeded Classification Task")
        self.setGeometry(x_pos, y_pos, 800, 600)
        self.setStyleSheet("background-color: #f6f6f6;")

        self.current_part = 0
        self.current_index = 0

        # Load stimuli: Replace this with actual structure
        self.parts = [
            {
                "instruction": "Part 1: Press 'B' if the word starts with the /b/ sound (like “ba…”), and 'P' if it starts with the /p/ sound (like “pa…”)",
                "control-phoneme": [
                    "task_speeded_classification/stimuli/baab1M1.wav",
                    "task_speeded_classification/stimuli/paab1M2.wav"
                ]
            },
            {
                "instruction": "Part 2: Press 'Female' if the word is spoken in a female voice, and 'Male' if it iss spoken in a male voice.",
                "control-voice": [
                    "task_speeded_classification/stimuli/paab2F1.wav",
                    "task_speeded_classification/stimuli/paab1M2.wav"
                ]
            }
        ]

        # Log file
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        self.stimulus_onset_time = None
        self.response_time = None
        self.log_state = None
        self.key_pressed = None
        self.condition = None
        self.stimulus = None
        self.choice = None
        self.experiment_log = []

        # Setup UI
        self.layout = QVBoxLayout()
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 20))
        self.label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 40px;
                margin: 20px;
            }
        """)

        self.layout.addWidget(self.label)

        self.ok_button = QPushButton("OK", self)
        self.ok_button.setFont(QFont("Arial", 16))
        self.ok_button.clicked.connect(self.start_part)
        self.layout.addWidget(self.ok_button)

        # response buttons
        self.button_b = QPushButton("B", self)
        self.button_b.setFont(QFont("Arial", 18))
        self.button_b.clicked.connect(lambda: self.register_response("B"))

        self.button_p = QPushButton("P", self)
        self.button_p.setFont(QFont("Arial", 18))
        self.button_p.clicked.connect(lambda: self.register_response("P"))

        self.button_f = QPushButton("Female", self)
        self.button_f.setFont(QFont("Arial", 18))
        self.button_f.clicked.connect(lambda: self.register_response("Female"))

        self.button_m = QPushButton("Male", self)
        self.button_m.setFont(QFont("Arial", 18))
        self.button_m.clicked.connect(lambda: self.register_response("Male"))

        # Hide them initially
        self.button_b.hide()
        self.button_p.hide()
        self.button_f.hide()
        self.button_m.hide()

        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #ffffff, stop:1 #f0f0f0);
                color: black;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 10px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #fafafa, stop:1 #e8e8e8);
                border: 2px solid #d0d0d0;
            }
            """

        self.ok_button.setStyleSheet(button_style)
        self.button_b.setStyleSheet(button_style)
        self.button_p.setStyleSheet(button_style)
        self.button_f.setStyleSheet(button_style)
        self.button_m.setStyleSheet(button_style)


        # Add to layout
        self.layout.addWidget(self.button_b)
        self.layout.addWidget(self.button_p)
        self.layout.addWidget(self.button_f)
        self.layout.addWidget(self.button_m)

        self.setLayout(self.layout)
        self.sound = QSoundEffect()
        self.sound.setVolume(0.9)

        # Focus policy to capture keypresses
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.show_instruction()

    def show_instruction(self):
        self.label.setText(self.parts[self.current_part]["instruction"])
        self.ok_button.setVisible(True)

    def start_part(self):
        self.ok_button.setVisible(False)
        self.current_index = 0
        self.play_next_stimulus()

    def play_next_stimulus(self):
        current = self.parts[self.current_part]

        # Hide all buttons
        self.button_b.hide()
        self.button_p.hide()
        self.button_f.hide()
        self.button_m.hide()

        # Play control-phoneme if present
        if "control-phoneme" in current and self.current_index < len(current["control-phoneme"]):
            self.play_stimuli("control-phoneme")
            self.label.setText("Choose: B or P")
            self.button_b.show()
            self.button_p.show()

        # Play control-voice if present
        elif "control-voice" in current and self.current_index < len(current["control-voice"]):
            self.play_stimuli("control-voice")
            self.label.setText("Choose: Female or Male")
            self.button_f.show()
            self.button_m.show()

        else:
            self.advance_part()

    def play_stimuli(self, condition):
        self.stimulus = self.parts[self.current_part][condition][self.current_index]
        if not os.path.exists(self.stimulus):
                QMessageBox.warning(self, "File Missing", f"Could not find: {self.stimulus}")
                return
        self.stimulus_onset_time = time.perf_counter()
        self.sound.setSource(QUrl.fromLocalFile(self.stimulus))
        self.sound.play()
        self.condition = condition

    def advance_part(self):
        self.current_part += 1
        if self.current_part < len(self.parts):
            self.show_instruction()
        else:
            self.label.setText("✅ Task Complete!")
            self.ok_button.setVisible(False)

            self.finish_experiment()

            # Show Main Menu button
            self.show_main_menu_button()

    # def keyPressEvent(self, event):
    #     key = event.text().lower()
    #     if key in ['b', 'p'] and self.sound.isPlaying() == False:
    #         self.current_index += 1
    #         self.play_next_stimulus()

    def register_response(self, choice):
        self.choice = choice
        self.response_time = time.perf_counter()
        self.writing_log()
        print(f"User clicked: {choice} on stimulus {self.current_index + 1}")
        
        # (Optional: save response to a file here)

        self.button_b.hide()
        self.button_p.hide()
        self.button_f.hide()
        self.button_m.hide()
        self.current_index += 1
        self.play_next_stimulus()
    
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

    def writing_log(self):
        """Write log sentence based on the current state"""
        stim_time = self.stimulus_onset_time
        resp_time = self.response_time
        rt = f"{resp_time - stim_time:.3f}"
        stim_ts = f"{stim_time:.6f}" 
        resp_ts = f"{resp_time:.6f}"
        log_line = f"{self.condition},{self.stimulus},{self.choice},{stim_ts},{resp_ts},{rt}"

        self.experiment_log.append(log_line)
        self.key_pressed = False

    def finish_experiment(self):
        """Write to log file"""
        # self.label.setText("Done!")

        # === Step 1: Build save directory
        save_dir = os.path.expanduser("./")
        os.makedirs(save_dir, exist_ok=True)

        # === Step 2: Build filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"speeded_classification_log_{timestamp}.txt"
        save_path = os.path.join(save_dir, filename)

        # === Step 3: Save log lines
        try:
            with open(save_path, 'w') as f:
                f.write("SPEEDED CLASSIFICATION TEST RESULTS\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Participant ID: {self.participant_id}\n")
                f.write(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\nTrial Format: condition,stimulus,participant's_choice,time_status,onset_time,response_time,RT_seconds\n")
                f.write("-" * 60 + "\n")
                for line in self.experiment_log:
                    f.write(line + '\n')
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"Save completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            print(f"Saved experiment log to: {save_path}")
        except Exception as e:
            print(f"Failed to save experiment log: {e}")


