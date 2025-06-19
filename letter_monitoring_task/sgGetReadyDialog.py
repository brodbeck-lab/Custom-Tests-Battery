from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout
)
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
from PyQt6.QtCore import Qt

class CvcGetReadyDialog(QDialog):
    def __init__(self, w=800, h=600, x=300, y=300, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Get Ready – CVC Test")
        self.resize(w, h)
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

        # Now populate the text just like the original sg version
        append_line("Consonant Vowel Consonant Test\n", "black")
        append_line("The letters will appear ONE LETTER AT A TIME as consonant - vowel - consonant - vowel...")
        append_line("Your task is to identify each time 3 letters make up a known 3 letter (consonant-vowel-consonant [CVC]) word, for example P-E-N. Press the space bar or click the left mouse button to identify a word.")
        append_line("B - U - ", "black")
        append_line("P - E - N", "red")
        append_line(" - O - M - B - ", "black")
        append_line("N - U - T", "red")
        append_line(" ", "black")
        append_line("It will never be the case that two words will run into each other, so this will never happen:")
        append_line("G - O - P - U - ", "black")
        append_line("M - A - T - A - N", "red")
        append_line(" ", "black")
        append_line("Press OK to start.", "black")
