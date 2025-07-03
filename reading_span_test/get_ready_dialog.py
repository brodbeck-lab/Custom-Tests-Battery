from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout
)
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
from PyQt6.QtCore import Qt

class RSpanGetReadyDialog(QDialog):
    def __init__(self, w=1300, h=760, x=300, y=300, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Get Ready – Reading Span Test")
        self.setFixedSize(w, h)
        self.move(x, y)

        layout = QVBoxLayout()
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Arial", 16))
        layout.addWidget(self.text_area)

        ok_button = QPushButton("OK")
        ok_button.setFont(QFont("Arial", 20))
        ok_button.setStyleSheet("color: black; background-color: #e0e0e0;")
        ok_button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.insert_instructions()

    def insert_instructions(self):
        cursor = self.text_area.textCursor()

        def append_line(text, color="black"):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            fmt.setFontWeight(QFont.Weight.Normal)
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(text + "\n", fmt)

        # Populate the instruction
        append_line("Reading Span Test\n", "black")
        append_line("In this task, sentences will be presented on a screen and it is your task to read all sentences aloud.", "black")
        append_line("After reading a sentence, please press the space bar, after which another sentence will appear on the screen.", "black")
        append_line("Read this sentence aloud as well and after finishing the sentence, press the space bar again.", "black")
        append_line(" ", "black")
        append_line("After a different number of sentences (2, 3, 4, 5, or 6), the word ‘recall’ will appear on the screen.", "black")
        append_line("This is important, because when the word ‘recall’ appears on the screen,", "black")
        append_line("it is your task to mention the sentence-final word of all sentences that you have read before", "black")
        append_line("(e.g. 2, 3, 4, 5, or 6 sentence-final words).", "black")
        append_line("The order in which you mention the sentence-final words of the sentences is free.", "black")
        append_line(" ", "black")
        append_line("Try to read the sentences as fast as possible while reading for content!", "black")
        append_line(" ", "black")
        append_line("Press the space OK to continue.", "black")
