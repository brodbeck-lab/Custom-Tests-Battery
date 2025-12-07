# task_speech_in_noise/sin_menu.py
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QGridLayout, QHBoxLayout, QMessageBox
)


BUTTONS = [
    ("Practice CaST",      "practice_cast"),
    ("Practice Sentence",  "practice_sentence"),
    ("CaST Non-word",      "cast_nonword"),
    ("HINT",               "hint"),
    ("CaST Word",          "cast_word"),
    ("CST",                "cst"),
]

def button_style():
    return """
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
            color: black; border: 2px solid #e0e0e0; border-radius: 20px;
            padding: 14px; font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #fafafa, stop:1 #e8e8e8);
            border: 2px solid #d0d0d0;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #e8e8e8, stop:1 #ffffff);
            border: 2px solid #c0c0c0;
        }
    """

class SpeechInNoiseMenuWindow(QWidget):
    def __init__(self, participant_id=None, participant_folder_path=None, parent=None):
        super().__init__(parent)
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path

        self.setWindowTitle("Speech in Noise Task")
        self.setStyleSheet("background-color: #f6f6f6;")
        screen = QApplication.primaryScreen().geometry()
        window_width, window_height = 1300, 760
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.addStretch()

        title = QLabel("Speech in Noise Task", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 26, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        root.addWidget(title)

        grid = QGridLayout()
        self.setStyleSheet("background-color: #f6f6f6;")
        grid.setHorizontalSpacing(80)
        grid.setVerticalSpacing(70)
        grid.setContentsMargins(60, 30, 60, 30)

        # 2 columns x 3 rows
        for i, (label, slot_name) in enumerate(BUTTONS):
            btn = QPushButton(label, self)
            self.style_task_button(btn)
            btn.clicked.connect(getattr(self, f"on_{slot_name}"))
            grid.addWidget(btn, i // 2, i % 2)

        root.addLayout(grid)

        row = QHBoxLayout()
        back = QPushButton("Back to Menu", self)
        back.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        back.setFixedSize(220, 64)
        back.setStyleSheet(button_style())
        back.clicked.connect(self.go_back)
        row.addStretch()
        row.addWidget(back)
        row.addStretch()
        root.addLayout(row)

        root.addStretch()

    def _todo(self, name: str):
        QMessageBox.information(self, "Not implemented", f"{name} is not implemented yet.")

    def on_practice_cast(self):
        from task_speech_in_noise.Tests.Practice_CaST.task_practice_cast import PracticeCastTask
        w = PracticeCastTask(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.child_window = w

    def on_practice_sentence(self):
        try:
            from task_speech_in_noise.Tests.Practice_Sentence.task_practice_sentence import PracticeSentenceTask
        except Exception as e:
            QMessageBox.critical(self, "Practice Sentence", f"Could not load Practice Sentence task:\n{e}")
            return

        w = PracticeSentenceTask(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.child_window = w


    def on_cast_nonword(self):
        try:
            from task_speech_in_noise.Tests.CaST_nonword.task_cast_nonword import CaSTNonwordTask
        except Exception as e:
            QMessageBox.critical(self, "CaST Non-word", f"Could not load CaST Non-word task:\n{e}")
            return

        w = CaSTNonwordTask(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.child_window = w


    def on_hint(self):
        from task_speech_in_noise.Tests.HINT.task_hint import HintTask
        w = HintTask(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.child_window = w

    def on_cast_word(self):
        from task_speech_in_noise.Tests.CaST_word.task_cast_word import CaSTWordTask
        w = CaSTWordTask(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.child_window = w


    def on_cst(self):
        from task_speech_in_noise.Tests.CST.task_cst import CSTTask
        w = CSTTask(
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        w.setGeometry(self.geometry())
        w.show()
        self.child_window = w


    def style_task_button(self, btn):
        """Match menu_selection.py look-and-feel."""
        btn.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        btn.setFixedSize(480, 120)
        btn.setStyleSheet("""
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
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                            stop: 0 #e8e8e8, stop: 1 #ffffff);
                border: 2px solid #c0c0c0;
            }
        """)

    def go_back(self):
        from menu_selection import SelectionMenu  # delayed import to avoid circular
        m = SelectionMenu(
            buttons_size=1.0,
            buttons_elevation=0.5,
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path,
        )
        m.setGeometry(self.geometry())
        m.show()
        self.close()

def main():
    app = QApplication(sys.argv)
    w = SpeechInNoiseMenuWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
