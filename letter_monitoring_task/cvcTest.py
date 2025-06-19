from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QFont, QKeyEvent, QMouseEvent
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

import os
from datetime import datetime

class CvcTestWidget(QWidget):
    experiment_finished = pyqtSignal(list)  # Emits the experiment log when done

    def __init__(self, char_sequence, presentation_time=2000, practice_count=2, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CVC Test")
        self.setStyleSheet("background-color: black;")
        self.setWindowState(Qt.WindowState.WindowFullScreen)

        self.char_sequence = char_sequence  # list of tuples (char, is_cvc)
        self.presentation_time = presentation_time
        self.practice_count = practice_count
        self.trial_number = 1
        self.stimuli_presented = 0
        self.experiment_log = ['Trial_Number, Character, Response, Assessment']

        # Trial state
        self.user_has_responded = False
        self.waiting_for_response = False

        # Performance counters
        self.hits = 0
        self.misses = 0
        self.false_positives = 0
        self.non_words = 0

        # Display
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 128))
        self.label.setStyleSheet("color: white;")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        QTimer.singleShot(1000, self.start_trial)

        # Properly delete the old test widget
        if hasattr(self, "cvc_test_widget"):
            self.cvc_test_widget.setParent(None)
            self.cvc_test_widget.deleteLater()
            del self.cvc_test_widget

    def start_trial(self):
        if self.stimuli_presented >= len(self.char_sequence):
            return self.finish_experiment()

        self.user_has_responded = False
        self.waiting_for_response = True

        self.current_char, self.current_is_cvc = self.char_sequence[self.stimuli_presented]
        self.label.setText(self.current_char)
        self.update()

        QTimer.singleShot(self.presentation_time, self.end_trial)

    def end_trial(self):
        self.waiting_for_response = False
        self.evaluate_response()
        self.stimuli_presented += 1
        self.trial_number += 1
        QTimer.singleShot(500, self.start_trial)

    def keyPressEvent(self, event: QKeyEvent):
        if self.waiting_for_response and event.key() == Qt.Key.Key_Space:
            self.user_has_responded = True

    def mousePressEvent(self, event: QMouseEvent):
        if self.waiting_for_response and event.button() == Qt.MouseButton.LeftButton:
            self.user_has_responded = True

    def evaluate_response(self):
        practice = self.trial_number <= self.practice_count
        tag = "(PRACTICE)" if practice else ""

        if self.current_is_cvc:
            if self.user_has_responded:
                self.hits += 1
                result = f"Correct {tag}"
            else:
                self.misses += 1
                result = f"Incorrect: missed {tag}"
        else:
            if self.user_has_responded:
                self.false_positives += 1
                result = f"Incorrect: false positive {tag}"
            else:
                self.non_words += 1
                result = f"Correct rejection {tag}"

        response = "Yes" if self.user_has_responded else "No"
        log_line = f"{self.trial_number},{self.current_char},{response},{result}"
        self.experiment_log.append(log_line)
        print(log_line)

    # def finish_experiment(self):
    #     self.label.setText("Done!")
    #     QTimer.singleShot(1000, lambda: self.experiment_finished.emit(self.experiment_log))

    def finish_experiment(self):

        self.label.setText("Done!")

        # === Step 1: Build save directory
        save_dir = os.path.expanduser("./")
        os.makedirs(save_dir, exist_ok=True)

        # === Step 2: Build filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cvc_log_{timestamp}.txt"
        save_path = os.path.join(save_dir, filename)

        # === Step 3: Save log lines
        try:
            with open(save_path, 'w') as f:
                for line in self.experiment_log:
                    f.write(line + '\n')
                    # print(f"***************")
            print(f"Saved experiment log to: {save_path}")
        except Exception as e:
            print(f"Failed to save experiment log: {e}")

        # === Step 4: Emit signal as before
        QTimer.singleShot(1000, lambda: self.experiment_finished.emit(self.experiment_log))

