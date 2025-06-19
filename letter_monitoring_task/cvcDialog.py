from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt

class CvcDialog(QDialog):
    def __init__(self, monitors=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CVC Test Configuration")
        self.setMinimumWidth(500)

        # self.pid = None
        self.presentation_time = None
        self.list_id = None
        self.n_stimuli = None
        self.monitor_index = None

        layout = QVBoxLayout()

        # # PID
        # self.pid_input = QLineEdit()
        # layout.addLayout(self._row("Participant ID:", self.pid_input))

        # Presentation Time
        self.time_input = QLineEdit("2000")
        layout.addLayout(self._row("Time to display letters (ms):", self.time_input))

        # List Number
        self.list_input = QLineEdit("1")
        layout.addLayout(self._row("List Number:", self.list_input))

        # Number of Stimuli
        self.n_stimuli_input = QLineEdit("10")
        layout.addLayout(self._row("Number of stimuli to present:", self.n_stimuli_input))

        # Monitor
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItems([str(i + 1) for i in range(monitors)])
        self.monitor_combo.setCurrentIndex(monitors - 1)
        layout.addLayout(self._row("Show experiment on monitor:", self.monitor_combo))

        # OK Button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.validate_and_accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_button)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.setStyleSheet("""
            QLabel, QLineEdit, QComboBox {
                color: black;
                font-size: 16px;
            }
            QLineEdit, QComboBox {
                background-color: white;
            }
            QPushButton {
                color: black;
                background-color: #f0f0f0;
                font-size: 18px;
                padding: 6px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #dcdcdc;
            }
        """)

    def _row(self, label_text, widget):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(200)
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

    def validate_and_accept(self):
        try:
            # self.pid = self.pid_input.text().strip()
            self.presentation_time = int(self.time_input.text())
            self.list_id = int(self.list_input.text())
            self.n_stimuli = int(self.n_stimuli_input.text())
            self.monitor_index = self.monitor_combo.currentIndex()
            # if not self.pid:
            #     raise ValueError("Missing PID")
            self.accept()
        except Exception:
            QMessageBox.warning(self, "Input Error", "Please enter all values correctly.")
