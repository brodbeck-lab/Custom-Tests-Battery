from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from reading_span_test.sentence_loader import load_sentences


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
        QTimer.singleShot(100, self.show_sentence)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.state == "sentence" and self.sentence_active:
                self.sentence_timer.stop()
                self.advance_sentence()
            elif self.state == "recall":
                self.state = "sentence"
                self.show_sentence()
            elif self.state == "done":
                self.close()  # Colse the ReadingSpanWidget window
                self.test_completed.emit()  # Notify parent to restore menu
                return

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
                self.sentence_timer.start(6500)  # 6.5 seconds

        else:
            self.show_recall()

    def advance_sentence(self):
        """Advance to the next sentence in the block."""
        if not self.sentence_active:
            return  # Prevent multiple advances
        self.sentence_active = False
        self.sentence_index += 1
        self.show_sentence()

    def show_recall(self):
        """Display the RECALL screen and advance to the next block after spacebar."""
        self.label.setText("RECALL\n\nSay aloud the last word of each sentence in any order.")
        self.sentence_index = 0
        self.block_index += 1
        self.state = "recall"
        if self.block_index < len(self.blocks):
            self.current_block = self.blocks[self.block_index]
        else:
            self.label.setText("TEST COMPLETE\n\nThank you!")
            self.state = "done"
            # self.test_completed.emit()
            # return

        # Wait for spacebar to move to the next block
        self.sentence_timer.stop()

    def mousePressEvent(self, event):
        """Allow mouse click to behave like spacebar."""
        self.keyPressEvent(event)
