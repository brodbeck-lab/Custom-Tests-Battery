from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from reading_span_test.sentence_loader import load_sentences

import os
from datetime import datetime
import time


class ReadingSpanWidget(QWidget):
    test_completed = pyqtSignal()
    def __init__(self, participant_id, participant_folder_path, recovery_mode, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Reading Span Test")
        self.setStyleSheet("background-color: white;")

        # Load the sentence blocks (each block ends in a recall)
        self.blocks = load_sentences()
        self.block_index = 0
        self.sentence_index = 0
        self.current_block = self.blocks[self.block_index]
        self.state = "sentence"  # could be: sentence, recall, done
        self.sentence_active = False  

        # Set up timer
        self.sentence_timer = QTimer(self)
        self.sentence_timer.setSingleShot(True)
        self.sentence_timer.timeout.connect(self.advance_sentence)
        self.presentation_time = 6500

        # Log file
        self.participant_id = participant_id
        self.stimulus_onset_time = None
        self.response_time = None
        self.log_state = None
        self.key_pressed = None
        self.experiment_log = []

        # UI setup
        self.layout = QVBoxLayout()
        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 24))
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: black; background-color: white;")
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()

        # Start first sentence
        # self.stimulus_onset_time = time.perf_counter()
        QTimer.singleShot(100, self.show_sentence)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.key_pressed = True
            if self.state == "sentence" and self.sentence_active:
                self.sentence_timer.stop()
                self.advance_sentence()
            elif self.state == "recall":
                self.writing_log()
                self.state = "sentence"
                self.show_sentence()
            elif self.state == "done":
                self.close()  # Colse the ReadingSpanWidget window
                self.test_completed.emit()  # Notify parent to restore menu
                return

    def writing_log(self):
        """Write log sentence based on the current state"""
        stim_time = self.stimulus_onset_time
        resp_time = self.response_time
        rt = f"{resp_time - stim_time:.3f}"
        stim_ts = f"{stim_time:.6f}" 
        resp_ts = f"{resp_time:.6f}"
        time_status = "key pressed" if self.key_pressed else "timeout"
        log_line = f"{self.log_state},{time_status},{stim_ts},{resp_ts},{rt}"

        self.experiment_log.append(log_line)
        self.key_pressed = False

    def show_sentence(self):
        """Display the current sentence."""
        self.state = "sentence"
        self.sentence_active = True  # Allow advancing
        if self.sentence_index < len(self.current_block):
            sentence = self.current_block[self.sentence_index]
            print(f"Showing sentence {self.sentence_index} in block {self.block_index}")
            print("Sentence content:", sentence)
            self.label.setText(sentence.encode("utf-8").decode("unicode_escape"))
            if not sentence.startswith("The start of the experiment:"):
                self.sentence_timer.start(self.presentation_time)  # 6.5 seconds
                self.stimulus_onset_time = time.perf_counter()
                self.log_state = "sentence " + sentence
            else:
                self.log_state = "instruction 2"

        else:
            self.show_recall()

    def advance_sentence(self):
        """Advance to the next sentence in the block."""
        if not self.sentence_active:
            return  # Prevent multiple advances
        self.sentence_active = False
        self.sentence_index += 1
        self.response_time = time.perf_counter()
        self.writing_log()
        self.show_sentence()

    def show_recall(self):
        """Display the RECALL screen and advance to the next block after spacebar."""
        self.stimulus_onset_time = time.perf_counter()
        self.label.setText("RECALL\n\nSay aloud the last word of each sentence in any order.")
        self.sentence_index = 0
        self.block_index += 1
        self.state = "recall"
        self.log_state = self.state
        if self.block_index < len(self.blocks):
            self.current_block = self.blocks[self.block_index]
        else:
            self.label.setText("TEST COMPLETE\n\nThank you!")
            self.state = "done"
            self.log_state = self.state 
            self.finish_experiment()
            # self.test_completed.emit()
            # return

        # Wait for spacebar to move to the next block
        self.sentence_timer.stop()

    def mousePressEvent(self, event):
        """Allow mouse click to behave like spacebar."""
        self.keyPressEvent(event)

    def finish_experiment(self):
        """Write to log file"""
        # self.label.setText("Done!")

        # === Step 1: Build save directory
        save_dir = os.path.expanduser("./")
        os.makedirs(save_dir, exist_ok=True)

        # === Step 2: Build filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reading_span_log_{timestamp}.txt"
        save_path = os.path.join(save_dir, filename)

        # === Step 3: Save log lines
        try:
            with open(save_path, 'w') as f:
                f.write("READING SPAN TEST RESULTS\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Participant ID: {self.participant_id}\n")
                f.write(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Presentation Time per sentence: {self.presentation_time} ms\n")
                f.write("\nTrial Format: state,time_status,onset_time,response_time,RT_seconds\n")
                f.write("-" * 60 + "\n")
                for line in self.experiment_log:
                    f.write(line + '\n')
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"Save completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            print(f"Saved experiment log to: {save_path}")
        except Exception as e:
            print(f"Failed to save experiment log: {e}")
