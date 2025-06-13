import sys
import os
import glob
import re
import json
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QLineEdit, QComboBox, QSpinBox, QScrollArea, QCheckBox, QTextEdit, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Import the selection menu
from selection_menu import SelectionMenu

# Import crash recovery system
from crash_recovery_system.session_manager import initialize_session_manager, get_session_manager
from crash_recovery_system.task_state_saver import get_recovery_info
import crash_recovery_system.crash_handler as crash_handler  # Initialize crash handler

class BiodataMenu(QMainWindow):
    def __init__(self, next_button_size=1.0, next_button_elevation=1.0, title_font_size=42):
        super().__init__()
        self.setWindowTitle("Custom Tests Battery - Participant Information")
        #self.setGeometry(0, 0, 1370, 960)

        # Center the window on the screen
        screen = QApplication.primaryScreen().geometry()
        window_width, window_height = 1370, 960
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        self.setStyleSheet("background-color: #f6f6f6;")
        
        # Store participant information for passing to next windows
        self.participant_folder_path = None
        self.participant_id = None
        
        # Recovery-related attributes
        self.recovery_mode = False
        self.existing_session_data = None
        
        print(f"=== BIODATA MENU INITIALIZATION ===")
        print("Crash recovery system: ENABLED")
        print("Session management: ACTIVE")
        print("=====================================")
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main vertical layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                background-color: white;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 7px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-button:vertical, QScrollBar::sub-button:vertical {
                border: none;
                background: #d0d0d0;
                height: 15px;
                border-radius: 7px;
                subcontrol-origin: margin;
            }
            QScrollBar::add-button:vertical:hover, QScrollBar::sub-button:vertical:hover {
                background: #b0b0b0;
            }
            QScrollBar::add-button:vertical {
                subcontrol-position: bottom;
            }
            QScrollBar::sub-button:vertical {
                subcontrol-position: top;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f0f0f0;
                height: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                border-radius: 7px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-button:horizontal, QScrollBar::sub-button:horizontal {
                border: none;
                background: #d0d0d0;
                width: 15px;
                border-radius: 7px;
                subcontrol-origin: margin;
            }
            QScrollBar::add-button:horizontal:hover, QScrollBar::sub-button:horizontal:hover {
                background: #b0b0b0;
            }
        """)
        
        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create "Biodata Form" title inside scroll area
        title_label = QLabel("Biodata Form")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setFont(QFont("Arial", title_font_size, QFont.Weight.ExtraBold))
        title_label.setStyleSheet("""
            QLabel {
                color: black;
                font-family: 'Arial', 'Helvetica', sans-serif;
                margin-bottom: 20px;
            }
        """)
        scroll_layout.addWidget(title_label)
        
        # Create grid layout for form fields (3 columns)
        form_grid = QGridLayout()
        form_grid.setSpacing(20)
        form_grid.setColumnStretch(0, 1)
        form_grid.setColumnStretch(1, 1)
        form_grid.setColumnStretch(2, 1)
        
        # Form field styling
        field_style = """
            QLabel {
                color: black;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            QLineEdit, QComboBox, QSpinBox, QTextEdit {
                padding: 8px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                background-color: white;
                font-size: 12px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
                border: 2px solid #3498db;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #e0e0e0;
                border-left-style: solid;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: #f8f8f8;
            }
            QComboBox::drop-down:hover {
                background-color: #e8e8e8;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #666;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                background-color: white;
                selection-background-color: #3498db;
                selection-color: white;
                color: black;
                font-size: 12px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px;
                border: none;
                color: black;
                background-color: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e3f2fd;
                color: black;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #3498db;
                color: white;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 20px;
                border-radius: 4px;
                background-color: #f8f8f8;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #e8e8e8;
            }
            QSpinBox::up-button {
                subcontrol-position: top right;
                border-bottom-width: 0;
            }
            QSpinBox::down-button {
                subcontrol-position: bottom right;
                border-top-width: 0;
            }
            QCheckBox {
                font-size: 12px;
                font-weight: bold;
                color: black;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #3498db;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border: 2px solid #3498db;
                image: none;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #2980b9;
                border: 2px solid #2980b9;
            }
        """
        
        # Create all form fields
        self.form_fields = {}
        
        # Initialize existing participants data
        self.existing_participants = {}
        self.load_existing_participants()
        
        # Define all fields with their types and options
        fields_data = [
            ("Participant ID", "text", None),
            ("Date of Birth or Age", "text", None),
            ("Gender/Sex", "dropdown", ["Select Gender/Sex", "Male", "Female", "Other", "Prefer not to say"]),
            ("Handedness", "dropdown", ["Select Handedness", "Right-handed", "Left-handed", "Ambidextrous"]),
            ("Primary Language", "dropdown", ["Select Primary Language", "English", "Spanish", "French", "Mandarin", "Cantonese", "Hindi", "Arabic", "Russian", "Portuguese", "Bengali", "Other"]),
            ("Education Level", "dropdown", ["Select Education Level", "No formal education", "Primary", "Secondary", "Tertiary", "Postgraduate"]),
            ("Region of Birth", "dropdown", ["Select Region of Birth", "North America", "South America", "Europe", "Africa", "Asia", "Australia/Oceania", "Middle East", "Other"]),
            ("Self-Reported Hearing Loss", "dropdown", ["Select Hearing Status", "None", "Mild", "Moderate", "Severe"]),
            ("History of Neurological Disorders", "dropdown", ["Select Neurological History", "None", "Epilepsy", "Stroke", "Traumatic Brain Injury", "Migraine", "Other"]),
            ("Psychiatric History", "dropdown", ["Select Psychiatric History", "None", "Depression", "Anxiety", "Other", "Prefer not to say"]),
            ("Learning Disabilities", "dropdown", ["Select Learning Disabilities", "None", "Dyslexia", "ADHD", "Other", "Prefer not to say"]),
            ("Current Medications", "text", None),
            ("Smoking Status", "dropdown", ["Select Smoking Status", "Never", "Former", "Current", "Prefer not to say"]),
            ("Alcohol Consumption", "dropdown", ["Select Alcohol Consumption", "Never", "Occasionally", "Regularly", "Prefer not to say"]),
            ("Substance Use", "dropdown", ["Select Substance Use", "Never", "Past", "Current", "Prefer not to say"]),
            ("Color Blindness", "dropdown", ["Select Color Blindness Status", "No", "Yes", "Unsure"]),
            ("Vision Status", "dropdown", ["Select Vision Status", "Normal", "Corrected with glasses/contacts", "Visual impairment"]),
            ("Sleep/Fatigue Status (Recent)", "dropdown", ["Select Sleep/Fatigue Status", "Well rested", "Slightly tired", "Very tired"]),
            ("Consent to Participate", "checkbox", None),
            ("Additional Information/Notes", "textarea", None)
        ]
        
        # Create widgets for each field
        row = 0
        col = 0
        
        for field_name, field_type, options in fields_data:
            # Create container widget for each field
            field_container = QWidget()
            field_layout = QVBoxLayout()
            field_layout.setContentsMargins(5, 5, 5, 5)
            field_layout.setSpacing(5)
            
            # Create label
            label = QLabel(field_name)
            label.setWordWrap(True)
            field_layout.addWidget(label)
            
            # Create appropriate input widget
            if field_name == "Participant ID":
                # Special handling for Participant ID - make it an editable combobox for autofill
                widget = QComboBox()
                widget.setEditable(True)
                widget.addItem("Enter ID")  # First option for entering new ID
                
                # Add existing participant IDs if any were loaded
                if hasattr(self, 'existing_participants'):
                    for participant_id in sorted(self.existing_participants.keys()):
                        widget.addItem(participant_id)
                
                widget.setCurrentIndex(0)
                widget.lineEdit().setPlaceholderText("Enter ID or Select ID")
            elif field_type == "text":
                widget = QLineEdit()
                widget.setPlaceholderText(f"Enter {field_name.lower()}")
            elif field_type == "dropdown":
                widget = QComboBox()
                widget.addItems(options)
            elif field_type == "checkbox":
                widget = QCheckBox("Yes, I consent to participate")
            elif field_type == "textarea":
                widget = QTextEdit()
                widget.setMaximumHeight(80)
                widget.setPlaceholderText("Enter any additional information or notes")
            
            field_layout.addWidget(widget)
            field_container.setLayout(field_layout)
            field_container.setStyleSheet(field_style)
            
            # Store reference to the input widget
            self.form_fields[field_name] = widget
            
            # Add to grid (3 columns per row, but some fields take full width)
            if field_name in ["Additional Information/Notes", "Consent to Participate"]:
                # Full width fields
                form_grid.addWidget(field_container, row, 0, 1, 3)
                row += 1
                col = 0
            else:
                # Regular fields (3 per row)
                form_grid.addWidget(field_container, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
        
        # Add form grid to scroll layout
        scroll_layout.addLayout(form_grid)
        
        # Add some bottom padding
        scroll_layout.addSpacing(30)
        
        # Set the scroll content
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Calculate button dimensions and elevation effects based on parameters (for both buttons)
        next_button_width = int(180 * next_button_size)
        next_button_height = int(60 * next_button_size)
        next_button_radius = int(30 * next_button_size)
        next_button_font_size = int(16 * next_button_size)
        
        # Calculate neumorphism colors based on elevation
        light_color = min(255, int(255 - (10 * (1 - next_button_elevation))))
        dark_color = max(200, int(240 - (40 * next_button_elevation)))
        border_light = max(180, int(224 - (44 * next_button_elevation)))
        border_dark = max(160, int(192 - (32 * next_button_elevation)))
        
        light_hex = f"#{light_color:02x}{light_color:02x}{light_color:02x}"
        dark_hex = f"#{dark_color:02x}{dark_color:02x}{dark_color:02x}"
        border_light_hex = f"#{border_light:02x}{border_light:02x}{border_light:02x}"
        border_dark_hex = f"#{border_dark:02x}{border_dark:02x}{border_dark:02x}"
        
        next_button_border_thickness = max(1, int(2 * next_button_elevation))
        
        # Create horizontal layout for buttons section (Save and Next buttons - outside scroll area)
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 20, 0, 0)
        
        # Add horizontal spacer to center the save button
        left_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        buttons_layout.addItem(left_spacer)
        
        # Calculate save button dimensions (same as next button)
        save_button_width = int(180 * next_button_size)
        save_button_height = int(60 * next_button_size)
        save_button_radius = int(30 * next_button_size)
        save_button_font_size = int(16 * next_button_size)
        
        # Create save button with same neumorphic styling as next button
        self.save_button = QPushButton("Save")
        self.save_button.setFont(QFont("Arial", save_button_font_size, QFont.Weight.Bold))
        self.save_button.setFixedSize(save_button_width, save_button_height)
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 {light_hex}, stop: 1 {dark_hex});
                color: black;
                border: {next_button_border_thickness}px solid {border_light_hex};
                border-radius: {save_button_radius}px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fafafa, stop: 1 {dark_hex});
                border: {next_button_border_thickness}px solid {border_light_hex};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 {dark_hex}, stop: 1 {light_hex});
                border: {next_button_border_thickness}px solid {border_dark_hex};
            }}
            QPushButton:disabled {{
                background: #e0e0e0;
                color: #a0a0a0;
                border: {next_button_border_thickness}px solid #d0d0d0;
            }}
        """)
        self.save_button.clicked.connect(self.save_clicked)
        self.save_button.setEnabled(False)  # Initially disabled
        
        # Add save button to buttons layout (centered)
        buttons_layout.addWidget(self.save_button)
        
        # Add another spacer and then the next button (right aligned)
        middle_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        buttons_layout.addItem(middle_spacer)
        
        # Create next button
        self.next_button = QPushButton("Next")
        self.next_button.setFont(QFont("Arial", next_button_font_size, QFont.Weight.Bold))
        self.next_button.setFixedSize(next_button_width, next_button_height)
        self.next_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 {light_hex}, stop: 1 {dark_hex});
                color: black;
                border: {next_button_border_thickness}px solid {border_light_hex};
                border-radius: {next_button_radius}px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fafafa, stop: 1 {dark_hex});
                border: {next_button_border_thickness}px solid {border_light_hex};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 {dark_hex}, stop: 1 {light_hex});
                border: {next_button_border_thickness}px solid {border_dark_hex};
            }}
            QPushButton:disabled {{
                background: #e0e0e0;
                color: #a0a0a0;
                border: {next_button_border_thickness}px solid #d0d0d0;
            }}
        """)
        self.next_button.clicked.connect(self.next_clicked)
        self.next_button.setEnabled(False)  # Initially disabled
        
        # Add next button to buttons layout
        buttons_layout.addWidget(self.next_button)
        
        # Add buttons layout to main layout
        main_layout.addLayout(buttons_layout)
        
        # Set layout to central widget
        central_widget.setLayout(main_layout)
        
        # Connect participant ID field to enable save button when text is entered
        participant_id_widget = self.form_fields["Participant ID"]
        if isinstance(participant_id_widget, QComboBox):
            participant_id_widget.currentTextChanged.connect(self.on_participant_id_changed)
            participant_id_widget.currentIndexChanged.connect(self.on_participant_selected)
        else:
            participant_id_widget.textChanged.connect(self.on_participant_id_changed)
        
        # Check for existing session manager and recovery info
        QTimer.singleShot(100, self.check_recovery_status)
    
    def check_recovery_status(self):
        """Check if we're in recovery mode and display status."""
        session_manager = get_session_manager()
        if session_manager:
            recovery_info = get_recovery_info()
            if recovery_info.get('recoverable'):
                current_task = recovery_info.get('current_task')
                trials_completed = recovery_info.get('trials_completed', 0)
                self.show_recovery_status(current_task, trials_completed)
    
    def show_recovery_status(self, current_task, trials_completed):
        """Show recovery status in the form."""
        # Add recovery status message at the top of the form
        try:
            # Find the title label and add recovery info after it
            scroll_content = self.findChild(QScrollArea).widget()
            scroll_layout = scroll_content.layout()
            
            # Create recovery status widget
            recovery_widget = QWidget()
            recovery_layout = QVBoxLayout()
            recovery_layout.setContentsMargins(10, 10, 10, 10)
            
            recovery_label = QLabel("🔄 RECOVERY MODE ACTIVE")
            recovery_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            recovery_label.setStyleSheet("""
                QLabel {
                    color: #d35400;
                    background-color: #fdf2e9;
                    border: 2px solid #f39c12;
                    border-radius: 8px;
                    padding: 10px;
                    margin: 5px 0px;
                }
            """)
            recovery_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            recovery_layout.addWidget(recovery_label)
            
            recovery_info_text = f"Previous session found: {current_task} ({trials_completed} trials completed)"
            recovery_info_label = QLabel(recovery_info_text)
            recovery_info_label.setFont(QFont("Arial", 11))
            recovery_info_label.setStyleSheet("""
                QLabel {
                    color: #8e44ad;
                    background-color: #f8f5ff;
                    border: 1px solid #bb8fce;
                    border-radius: 5px;
                    padding: 8px;
                    margin: 2px 0px;
                }
            """)
            recovery_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            recovery_layout.addWidget(recovery_info_label)
            
            recovery_widget.setLayout(recovery_layout)
            
            # Insert recovery widget after title (position 1)
            scroll_layout.insertWidget(1, recovery_widget)
            
            self.recovery_mode = True
            print("Recovery status displayed in biodata form")
            
        except Exception as e:
            print(f"Error showing recovery status: {e}")
    
    def get_biodata(self):
        """Collect all biodata information"""
        biodata = {}
        for field_name, widget in self.form_fields.items():
            if isinstance(widget, QLineEdit):
                biodata[field_name] = widget.text()
            elif isinstance(widget, QComboBox):
                if field_name == "Participant ID":
                    # For participant ID combobox, get the current text
                    biodata[field_name] = widget.currentText()
                else:
                    # For regular dropdowns, get the selected option
                    biodata[field_name] = widget.currentText()
            elif isinstance(widget, QCheckBox):
                biodata[field_name] = widget.isChecked()
            elif isinstance(widget, QTextEdit):
                biodata[field_name] = widget.toPlainText()
        return biodata
    
    def validate_form(self):
        """Comprehensive form validation - checks if all fields are properly filled"""
        errors = []
        
        # Check all fields for meaningful values
        for field_name, widget in self.form_fields.items():
            if isinstance(widget, QLineEdit):
                if not widget.text().strip():
                    errors.append(f"{field_name} is required")
            elif isinstance(widget, QComboBox):
                if field_name == "Participant ID":
                    # Special handling for participant ID combobox
                    current_text = widget.currentText().strip()
                    if not current_text or current_text in ["Enter ID", "Enter ID or Select ID"]:
                        errors.append(f"{field_name} is required")
                else:
                    # Regular dropdown validation
                    if widget.currentIndex() == 0:  # First item is usually "Select..."
                        errors.append(f"Please select {field_name}")
            elif isinstance(widget, QCheckBox):
                if field_name == "Consent to Participate" and not widget.isChecked():
                    errors.append("Consent to participate is required")
            elif isinstance(widget, QTextEdit):
                # Text areas are optional, but if you want them required, uncomment:
                # if not widget.toPlainText().strip():
                #     errors.append(f"{field_name} is required")
                pass
        
        if errors:
            return False, "; ".join(errors)
        return True, ""
    
    def load_existing_participants(self):
        """Load existing participant IDs from saved data files"""
        try:
            documents_path = os.path.expanduser("~/Documents")
            app_data_path = os.path.join(documents_path, "Custom Tests Battery Data")
            
            self.existing_participants = {}  # Store participant_id: file_path mapping
            
            if os.path.exists(app_data_path):
                print(f"Loading existing participants from: {app_data_path}")
                
                # Find all participant folders (folder name = participant ID)
                for folder_name in os.listdir(app_data_path):
                    folder_path = os.path.join(app_data_path, folder_name)
                    if os.path.isdir(folder_path):
                        # Look for metadata_*.txt files in the folder
                        metadata_files = glob.glob(os.path.join(folder_path, "metadata_*.txt"))
                        if metadata_files:
                            # Use the most recent metadata file if multiple exist
                            latest_file = max(metadata_files, key=os.path.getmtime)
                            
                            # Folder name is the participant ID
                            participant_id = folder_name
                            self.existing_participants[participant_id] = latest_file
            
            print(f"Found {len(self.existing_participants)} existing participants")
            
        except Exception as e:
            print(f"Error loading existing participants: {str(e)}")
            self.existing_participants = {}
    
    def parse_participant_data(self, file_path):
        """Parse participant data from saved file"""
        try:
            data = {}
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Find the participant information section
                lines = content.split('\n')
                in_data_section = False
                
                for line in lines:
                    if "PARTICIPANT INFORMATION:" in line:
                        in_data_section = True
                        continue
                    elif line.startswith("=") and in_data_section:
                        break
                    elif in_data_section and ":" in line:
                        # Parse field: value pairs
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            field_name = parts[0].strip()
                            value = parts[1].strip()
                            
                            # Handle different value types
                            if value == "[Not provided]":
                                value = ""
                            elif value in ["Yes", "No"]:
                                value = value == "Yes"
                            
                            data[field_name] = value
            
            return data
            
        except Exception as e:
            print(f"Error parsing participant data: {str(e)}")
            return {}
    
    def autofill_form(self, participant_data):
        """Autofill form fields with participant data"""
        try:
            for field_name, widget in self.form_fields.items():
                if field_name in participant_data:
                    value = participant_data[field_name]
                    
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value) if value else "")
                    elif isinstance(widget, QComboBox):
                        if field_name == "Participant ID":
                            # For participant ID, set the text directly (it's editable)
                            # First, check if the participant ID is already in the dropdown
                            participant_id = str(value) if value else ""
                            index = widget.findText(participant_id)
                            if index >= 0:
                                widget.setCurrentIndex(index)
                            else:
                                # If not found, set it as text (this handles the case where it's being selected)
                                widget.setCurrentText(participant_id)
                        else:
                            # For regular dropdowns, find and set the matching item
                            if isinstance(value, str):
                                index = widget.findText(value)
                                if index >= 0:
                                    widget.setCurrentIndex(index)
                                else:
                                    widget.setCurrentIndex(0)
                    elif isinstance(widget, QCheckBox):
                        widget.setChecked(bool(value))
                    elif isinstance(widget, QTextEdit):
                        widget.setPlainText(str(value) if value else "")
            
            print(f"Autofilled form with data for participant")
            
        except Exception as e:
            print(f"Error autofilling form: {str(e)}")
    
    def on_participant_selected(self, index):
        """Handle participant selection from dropdown"""
        participant_id_widget = self.form_fields["Participant ID"]
        if isinstance(participant_id_widget, QComboBox):
            if index == 0:
                # "Enter ID" option selected - clear the field for text input
                participant_id_widget.lineEdit().clear()
                participant_id_widget.lineEdit().setPlaceholderText("Enter ID or Select ID")
                print("Enter ID mode activated - ready for new participant ID input")
            elif index > 0:
                # Existing participant selected - autofill
                selected_participant = participant_id_widget.currentText()
                
                if selected_participant in self.existing_participants:
                    file_path = self.existing_participants[selected_participant]
                    participant_data = self.parse_participant_data(file_path)
                    
                    if participant_data:
                        self.autofill_form(participant_data)
                        print(f"Autofilled data for participant: {selected_participant}")
                else:
                    print(f"Participant data not found for: {selected_participant}")
    
    def on_participant_id_changed(self, text):
        """Enable save button only when participant ID has text"""
        # Handle both QLineEdit and QComboBox
        participant_id_widget = self.form_fields["Participant ID"]
        
        if isinstance(participant_id_widget, QComboBox):
            # For combobox, get the current text (could be typed or selected)
            current_text = participant_id_widget.currentText().strip()
            # Don't count the placeholder texts as valid input
            if current_text and current_text not in ["Enter ID", "Enter ID or Select ID"]:
                self.save_button.setEnabled(True)
            else:
                self.save_button.setEnabled(False)
        else:
            # For regular text field
            if text.strip():
                self.save_button.setEnabled(True)
            else:
                self.save_button.setEnabled(False)
    
    def generate_filename_timestamp(self):
        """Generate timestamp string for folder and file names"""
        now = datetime.now()
        return now.strftime("%Y%m%d_%H%M%S")
    
    def create_data_folder_and_file(self, participant_id, biodata):
        """Create folder (if needed) and save biodata to metadata file"""
        try:
            # Generate timestamp for filename
            timestamp = self.generate_filename_timestamp()
            
            # Use Documents folder for cross-platform compatibility
            documents_path = os.path.expanduser("~/Documents")
            app_data_path = os.path.join(documents_path, "Custom Tests Battery Data")
            
            # Create the main application data folder if it doesn't exist
            if not os.path.exists(app_data_path):
                os.makedirs(app_data_path)
                print(f"Created application data directory: {app_data_path}")
            
            # Create/use participant folder (folder name = participant ID)
            participant_folder_path = os.path.join(app_data_path, participant_id)
            if not os.path.exists(participant_folder_path):
                os.makedirs(participant_folder_path)
                print(f"Created new participant folder: {participant_folder_path}")
            else:
                print(f"Using existing participant folder: {participant_folder_path}")
            
            # Create metadata filename: metadata_YYYYMMDD_HHMMSS.txt
            file_name = f"metadata_{timestamp}.txt"
            file_path = os.path.join(participant_folder_path, file_name)
            
            # Write biodata to file in structured, readable format
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write("CUSTOM TESTS BATTERY - PARTICIPANT BIODATA\n")
                file.write("=" * 50 + "\n\n")
                file.write(f"Data Collection Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write(f"Storage Location: {app_data_path}\n")
                file.write(f"Participant Folder: {participant_id}\n")
                file.write(f"Metadata File: {file_name}\n")
                file.write(f"Crash Recovery: ENABLED\n")
                file.write(f"Session Management: ACTIVE\n\n")
                file.write("PARTICIPANT INFORMATION:\n")
                file.write("-" * 30 + "\n\n")
                
                # Write each field with proper formatting
                for field_name, value in biodata.items():
                    # Format the value based on type
                    if isinstance(value, bool):
                        formatted_value = "Yes" if value else "No"
                    elif isinstance(value, str):
                        formatted_value = value if value.strip() else "[Not provided]"
                    else:
                        formatted_value = str(value) if value else "[Not provided]"
                    
                    # Write field with proper formatting
                    file.write(f"{field_name:<35}: {formatted_value}\n")
                
                file.write("\n" + "=" * 50 + "\n")
                file.write("End of Biodata Report\n")
                file.write(f"\nGenerated by Custom Tests Battery v1.0\n")
                file.write(f"Executable Location: {os.path.dirname(os.path.abspath(__file__))}\n")
                
            print(f"Metadata file created: {file_path}")
            
            # Verify the file was created and contains data
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                print("File verification successful - data saved correctly")
                print(f"Data saved to: {file_path}")
                return True, participant_folder_path, file_path
            else:
                print("File verification failed")
                return False, None, None
                
        except Exception as e:
            print(f"Error creating folder/file: {str(e)}")
            print(f"Attempted path: {app_data_path if 'app_data_path' in locals() else 'Path not determined'}")
            return False, None, None
    
    def save_clicked(self):
        """Handle save button click with folder and file creation + session manager initialization"""
        # Validate form before saving
        is_valid, error_message = self.validate_form()
        if not is_valid:
            print(f"Form validation error: {error_message}")
            QMessageBox.warning(self, "Form Validation Error", 
                              f"Please complete all required fields:\n\n{error_message}")
            return
        
        # Collect biodata
        biodata = self.get_biodata()
        participant_id = biodata.get("Participant ID", "").strip()
        
        if not participant_id:
            print("Error: Participant ID is required")
            QMessageBox.critical(self, "Missing Participant ID", 
                               "Participant ID is required to save data.")
            return
        
        print("Saving biodata with crash recovery support...")
        print("Collected data:", biodata)
        
        # Create folder and save file
        success, folder_path, file_path = self.create_data_folder_and_file(participant_id, biodata)
        
        if success:
            print(f"SUCCESS: Biodata saved successfully!")
            print(f"Participant Folder: {folder_path}")
            print(f"Metadata File: {file_path}")
            print("All data verification completed successfully")
            
            # Store participant information for passing to next windows
            self.participant_folder_path = folder_path
            self.participant_id = participant_id
            
            # CRITICAL: Initialize session manager for this participant
            try:
                session_manager = initialize_session_manager(participant_id, folder_path)
                
                # Set default task queue for the session
                default_tasks = [
                    "Stroop Colour-Word Task",
                    "Letter Monitoring Task", 
                    "Visual Search Task",
                    "Attention Network Task",
                    "Go/No-Go Task",
                    "Working Memory Task"
                ]
                session_manager.set_task_queue(default_tasks)
                
                print(f"SUCCESS: Session manager initialized for participant: {participant_id}")
                print(f"Default task queue set: {len(default_tasks)} tasks")
                
                # Save session state immediately
                session_manager.save_session_state()
                
            except Exception as e:
                print(f"ERROR: Failed to initialize session manager: {e}")
                QMessageBox.critical(self, "Session Manager Error", 
                                   f"Failed to initialize crash recovery system:\n{str(e)}")
                return
            
            # Debug: Verify the information was stored correctly
            print(f"DEBUG: Stored participant_id = '{self.participant_id}'")
            print(f"DEBUG: Stored participant_folder_path = '{self.participant_folder_path}'")
            print(f"DEBUG: participant_id type = {type(self.participant_id)}")
            print(f"DEBUG: participant_folder_path type = {type(self.participant_folder_path)}")
            
            # Enable the Next button after successful save
            self.next_button.setEnabled(True)
            print("Next button has been activated")
            
            # Show success message with recovery info
            QMessageBox.information(self, "Save Successful", 
                                  f"Biodata saved successfully!\n\n"
                                  f"Participant: {participant_id}\n"
                                  f"Crash recovery: ENABLED\n"
                                  f"Session management: ACTIVE\n\n"
                                  f"Click Next to continue to test selection.")
        else:
            print("ERROR: Failed to save biodata")
            QMessageBox.critical(self, "Save Error", 
                               "Failed to save biodata. Please try again.")
    
    def next_clicked(self):
        # Check if Next button is enabled (should only be enabled after successful save)
        if not self.next_button.isEnabled():
            print("Next button is not yet activated. Please save the form first.")
            QMessageBox.warning(self, "Save Required", 
                              "Please save the biodata form before proceeding.")
            return
        
        # Double-check that participant information is available
        if not hasattr(self, 'participant_id') or not hasattr(self, 'participant_folder_path'):
            print("ERROR: Participant information attributes missing!")
            QMessageBox.critical(self, "Missing Information", 
                               "Participant information is missing. Please save the form first.")
            return
            
        if not self.participant_id or not self.participant_folder_path:
            print("ERROR: Participant information is missing!")
            print(f"Participant ID: {getattr(self, 'participant_id', 'MISSING ATTRIBUTE')}")
            print(f"Participant folder path: {getattr(self, 'participant_folder_path', 'MISSING ATTRIBUTE')}")
            QMessageBox.critical(self, "Missing Information", 
                               "Participant information is incomplete. Please save the form first.")
            return
        
        # Verify session manager is initialized
        session_manager = get_session_manager()
        if not session_manager:
            print("WARNING: Session manager not initialized - attempting to initialize...")
            try:
                session_manager = initialize_session_manager(self.participant_id, self.participant_folder_path)
                print("Session manager initialized successfully")
            except Exception as e:
                print(f"ERROR: Failed to initialize session manager: {e}")
                QMessageBox.warning(self, "Session Manager Warning", 
                                  f"Crash recovery system not available:\n{str(e)}")
        
        print("Next button clicked! Loading test selection menu...")
        print(f"Passing participant ID: {self.participant_id}")
        print(f"Passing participant folder: {self.participant_folder_path}")
        print(f"Session manager: {'ACTIVE' if session_manager else 'INACTIVE'}")
        
        # Verify the folder still exists
        if not os.path.exists(self.participant_folder_path):
            print(f"ERROR: Participant folder no longer exists: {self.participant_folder_path}")
            QMessageBox.critical(self, "Folder Missing", 
                               "Participant folder no longer exists. Please save the form again.")
            return
        
        # Get current window geometry and create selection menu
        # Pass participant information to selection menu
        current_geometry = self.geometry()
        
        try:
            self.selection_menu = SelectionMenu(
                buttons_size=1.0, 
                buttons_elevation=0.5,
                participant_id=self.participant_id,
                participant_folder_path=self.participant_folder_path,
                recovery_mode=self.recovery_mode
            )
            self.selection_menu.setGeometry(current_geometry)
            self.selection_menu.show()
            
            # Hide the biodata window
            self.hide()
            
            print("Successfully transitioned to selection menu with crash recovery support")
            
        except Exception as e:
            print(f"ERROR creating selection menu: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Emergency save if session manager available
            if session_manager:
                try:
                    session_manager.emergency_save()
                    print("Emergency save completed due to error")
                except:
                    print("Emergency save failed")
            
            QMessageBox.critical(self, "Navigation Error", 
                               f"Failed to load test selection menu:\n{str(e)}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up session manager if no tasks started yet
        session_manager = get_session_manager()
        if session_manager:
            current_task = session_manager.session_data.get('current_task')
            if not current_task:
                print("Cleaning up session manager from biodata menu")
                session_manager._cleanup_session()
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Set application properties for crash recovery
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Behavioral Research Lab")
    
    print("=== BIODATA MENU STARTING ===")
    print("Crash recovery system: ENABLED")
    print("Session management: READY")
    print("===============================")
    
    # You can customize these parameters:
    # next_button_size: Controls the size of the next button (default: 1.0)
    # next_button_elevation: Controls how much the neumorphic next button stands out (default: 1.0)
    # title_font_size: Controls the size of "Biodata Form" title (default: 42)
    window = BiodataMenu(next_button_size=1.0, next_button_elevation=0.5, title_font_size=42)
    
    window.show()
    
    try:
        exit_code = app.exec()
        print("Biodata menu closed normally")
        return exit_code
    except Exception as e:
        print(f"Biodata menu crashed: {e}")
        
        # Emergency save
        session_manager = get_session_manager()
        if session_manager:
            try:
                session_manager.emergency_save()
                print("Emergency save completed from biodata menu")
            except:
                print("Emergency save failed from biodata menu")
        
        raise
    finally:
        # Cleanup
        from crash_recovery_system.session_manager import cleanup_session_manager
        cleanup_session_manager()

if __name__ == "__main__":
    main()