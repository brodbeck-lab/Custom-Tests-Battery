from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

import random

class ReadingSpanWidget(QWidget):
    experiment_finished = pyqtSignal()

    def __init__(self, sentences, participant_id, participant_folder_path, recovery_mode=False, parent=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

        self.sentences = sentences
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        self.recovery_mode = recovery_mode

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("")
        self.label.setFont(QFont("Arial", 24))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: black;") 
        self.layout.addWidget(self.label)

        self.recall_input = QTextEdit()
        self.recall_input.setPlaceholderText("Type the final words here, space-separated...")
        self.recall_input.setFont(QFont("Arial", 18))
        self.recall_input.hide()
        self.layout.addWidget(self.recall_input)

        self.submit_button = QPushButton("Submit")
        self.submit_button.setFont(QFont("Arial", 18))
        self.submit_button.clicked.connect(self.check_response)
        self.submit_button.hide()
        self.layout.addWidget(self.submit_button)

        self.current_trial = []
        self.final_words = []
        self.sentence_index = 0

        self.start_new_trial()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and self.recall_input.isHidden():
            self.show_next_sentence()

    def start_new_trial(self):
        self.recall_input.hide()
        self.submit_button.hide()
        self.recall_input.clear()
        self.current_trial = random.sample(self.sentences, random.randint(2, 6))
        self.final_words = [s.strip().split()[-1].replace(".", "").lower() for s in self.current_trial]
        self.sentence_index = 0
        self.show_next_sentence()

    def show_next_sentence(self):
        if self.sentence_index < len(self.current_trial):
            self.label.setText(self.current_trial[self.sentence_index])
            self.sentence_index += 1
        else:
            self.prompt_recall()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and self.recall_input.isHidden():
            self.show_next_sentence()

    def prompt_recall(self):
        self.label.setText("Recall: Please type the final words of the sentences.")
        self.recall_input.show()
        self.submit_button.show()

    def check_response(self):
        # Do nothing with the response; just return to menu
        self.close()
        parent = self.parent()
        if parent:
            parent.__init__(
                buttons_size=1.0,
                buttons_elevation=1.0,
                participant_id=parent.participant_id,
                participant_folder_path=parent.participant_folder_path,
                recovery_mode=parent.recovery_mode
            )
            parent.show()

