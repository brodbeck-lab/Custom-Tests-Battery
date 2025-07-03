import sys
import os
import json
import glob
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QDialog, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Import the biodata menu
from menu_biodata import BiodataMenu

# Import crash recovery system
from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager
from crash_recovery_system.task_state_saver import CrashDetector
import crash_recovery_system.crash_handler as crash_handler  # Initialize crash handler

class RecoverySelectionDialog(QDialog):
    """Dialog for selecting which session to recover when multiple sessions are found."""
    
    def __init__(self, recoverable_sessions, parent=None):
        super().__init__(parent)
        self.recoverable_sessions = recoverable_sessions
        self.selected_session = None
        self.setWindowTitle("Multiple Sessions Found")
        self.setFixedSize(600, 400)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Multiple Incomplete Sessions Found")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("Select a session to recover:")
        instructions.setFont(QFont("Arial", 12))
        instructions.setStyleSheet("margin: 10px 0px;")
        layout.addWidget(instructions)
        
        # Session list
        self.session_list = QListWidget()
        self.session_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                background-color: white;
                padding: 5px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        
        for session in self.recoverable_sessions:
            item_text = (
                f"Participant: {session['participant_id']}\n"
                f"Last saved: {session['last_save']}\n"
                f"Current task: {session.get('current_task', 'Unknown')}"
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, session)
            self.session_list.addItem(item)
        
        layout.addWidget(self.session_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        recover_button = QPushButton("Recover Selected Session")
        recover_button.clicked.connect(self.recover_selected)
        recover_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        start_new_button = QPushButton("Start New Session")
        start_new_button.clicked.connect(self.start_new)
        start_new_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #9e9e9e;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        
        button_layout.addWidget(recover_button)
        button_layout.addWidget(start_new_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def recover_selected(self):
        """Recover the selected session."""
        current_item = self.session_list.currentItem()
        if current_item:
            self.selected_session = current_item.data(Qt.ItemDataRole.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a session to recover.")
    
    def start_new(self):
        """Start a new session (clear all recoverable sessions)."""
        self.selected_session = None
        self.accept()

class WelcomeWindow(QMainWindow):
    def __init__(self, title_font_size=36, description_font_size=16, next_button_size=1.0, next_button_elevation=1.0):
        super().__init__()
        self.setWindowTitle("Custom Tests Battery")
        #self.setGeometry(0, 0, 1370, 960)

        # center the window on the screen (5 lines)
        screen = QApplication.primaryScreen().geometry()
        window_width, window_height = 1370, 960
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        self.setStyleSheet("background-color: #f6f6f6;")
        
        # Initialize crash detector
        self.crash_detector = CrashDetector()
        
        # Recovery-related attributes
        self.recovery_sessions = []
        self.selected_recovery_session = None
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main vertical layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Add top spacer to center the content vertically
        top_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(top_spacer)
        
        # Create title label - "Custom Tests Battery"
        title_label = QLabel("Custom Tests Battery")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setFont(QFont("Arial", title_font_size, QFont.Weight.ExtraBold))
        title_label.setStyleSheet("""
            QLabel {
                color: black;
                font-family: 'Arial', 'Helvetica', sans-serif;
            }
        """)
        main_layout.addWidget(title_label)
        
        # Create description text with 6 words per line
        description_text = "Comprehensive psychological testing suite for cognitive\nassessment and research including Stroop Colour-Word\nTask Letter Monitoring Task and more"
        description_label = QLabel(description_text)
        description_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        description_label.setFont(QFont("Arial", description_font_size, QFont.Weight.Normal))
        description_label.setStyleSheet("""
            QLabel {
                color: black;
                margin-top: 10px;
            }
        """)
        main_layout.addWidget(description_label)
        
        # Add bottom spacer
        bottom_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(bottom_spacer)
        
        # Create horizontal layout for bottom section
        bottom_layout = QHBoxLayout()
        
        # Add horizontal spacer to push button to the right
        horizontal_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        bottom_layout.addItem(horizontal_spacer)
        
        # Calculate next button dimensions and elevation effects based on parameters
        next_button_width = int(180 * next_button_size)
        next_button_height = int(60 * next_button_size)
        next_button_radius = int(30 * next_button_size)
        next_button_font_size = int(16 * next_button_size)
        
        # Calculate neumorphism colors based on elevation
        # Higher elevation = more contrast, more pronounced effect
        light_color = min(255, int(255 - (10 * (1 - next_button_elevation))))  # Gets darker with less elevation
        dark_color = max(200, int(240 - (40 * next_button_elevation)))  # Gets much darker with more elevation
        border_light = max(180, int(224 - (44 * next_button_elevation)))  # Border gets darker with elevation
        border_dark = max(160, int(192 - (32 * next_button_elevation)))   # Pressed border
        
        light_hex = f"#{light_color:02x}{light_color:02x}{light_color:02x}"
        dark_hex = f"#{dark_color:02x}{dark_color:02x}{dark_color:02x}"
        border_light_hex = f"#{border_light:02x}{border_light:02x}{border_light:02x}"
        border_dark_hex = f"#{border_dark:02x}{border_dark:02x}{border_dark:02x}"
        
        # Calculate border thickness based on elevation
        next_button_border_thickness = max(1, int(2 * next_button_elevation))
        
        # Create next button
        next_button = QPushButton("Next")
        next_button.setFont(QFont("Arial", next_button_font_size, QFont.Weight.Bold))
        next_button.setFixedSize(next_button_width, next_button_height)
        next_button.setStyleSheet(f"""
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
        """)
        next_button.clicked.connect(self.next_clicked)
        
        # Add button to bottom layout
        bottom_layout.addWidget(next_button)
        
        # Add bottom layout to main layout
        main_layout.addLayout(bottom_layout)
        
        # Set layout to central widget
        central_widget.setLayout(main_layout)
        
        # Check for recoverable sessions after UI is set up
        QTimer.singleShot(500, self.check_for_recoverable_sessions)
    

    def check_for_recoverable_sessions(self):
        """
        Check if there are any recoverable sessions from previous crashes.
        Updated to handle organized folder structure (biodata/, system/).
        """
        try:
            documents_path = os.path.expanduser("~/Documents")
            app_data_path = os.path.join(documents_path, "Custom Tests Battery Data")
            
            if not os.path.exists(app_data_path):
                print("No application data directory found")
                return
            
            print(f"Checking for recoverable sessions in organized structure: {app_data_path}")
            
            recoverable_sessions = []
            
            # Look for session files in participant system folders
            for participant_folder in os.listdir(app_data_path):
                folder_path = os.path.join(app_data_path, participant_folder)
                if not os.path.isdir(folder_path):
                    continue
                
                # Check for organized structure first (system/session_state.json)
                system_folder = os.path.join(folder_path, "system")
                session_file = None
                
                if os.path.exists(system_folder):
                    # New organized structure
                    session_file = os.path.join(system_folder, "session_state.json")
                    print(f"Checking organized structure for {participant_folder}: system/")
                else:
                    # Legacy structure (session_state.json in root)
                    session_file = os.path.join(folder_path, "session_state.json")
                    print(f"Checking legacy structure for {participant_folder}: root/")
                
                if not os.path.exists(session_file):
                    continue
                
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    # Check if session is active and recent
                    if session_data.get('session_active', False):
                        last_save_str = session_data.get('last_save_time', '')
                        if last_save_str:
                            try:
                                last_save = datetime.fromisoformat(last_save_str)
                                time_diff = datetime.now() - last_save
                                
                                # If last save was within 24 hours, check if recovery is actually needed
                                if time_diff.total_seconds() < 86400:  # 24 hours
                                    current_task = session_data.get('current_task', '')
                                    
                                    # Check if current task is actually incomplete
                                    needs_recovery = self.check_if_recovery_needed(session_data, current_task)
                                    
                                    if needs_recovery:
                                        current_task_state = session_data.get('current_task_state', {})
                                        trials_completed = 0
                                        
                                        if current_task_state:
                                            # Count actual trials completed, not just current index
                                            trial_data = current_task_state.get('trial_data', [])
                                            trials_completed = len(trial_data)
                                        
                                        # Determine structure type
                                        structure_type = "organized" if os.path.exists(system_folder) else "legacy"
                                        
                                        recoverable_sessions.append({
                                            'participant_id': participant_folder,
                                            'session_file': session_file,
                                            'folder_path': folder_path,
                                            'last_save': last_save_str,
                                            'current_task': current_task,
                                            'trials_completed': trials_completed,
                                            'session_data': session_data,
                                            'structure_type': structure_type
                                        })
                                        
                                        print(f"Found recoverable session: {participant_folder} - {current_task} ({trials_completed} trials) [{structure_type}]")
                                    else:
                                        print(f"Session found but no recovery needed: {participant_folder} - task completed")
                                        # Clean up completed session
                                        self.cleanup_completed_session(session_file, folder_path, structure_type)
                            except ValueError:
                                print(f"Invalid date format in session file: {session_file}")
                            
                except Exception as e:
                    print(f"Error reading session file {session_file}: {e}")
            
            self.recovery_sessions = recoverable_sessions
            
            if recoverable_sessions:
                print(f"Found {len(recoverable_sessions)} recoverable sessions")
                self.show_recovery_notification()
            else:
                print("No recoverable sessions found")
                
        except Exception as e:
            print(f"Error checking for recoverable sessions: {e}")
    
    def check_if_recovery_needed(self, session_data, current_task):
        """
        Check if recovery is actually needed for the current task.
        
        Returns False if:
        - Current task is already completed
        - No current task is set
        - Current task state indicates completion
        - Session is marked as completed
        """
        try:
            # Check if session is marked as completed
            if session_data.get('session_completed', False):
                print("Session marked as completed - no recovery needed")
                return False
            
            # Check if session is marked as inactive
            if not session_data.get('session_active', True):
                print("Session marked as inactive - no recovery needed")
                return False
            
            # Check if no current task is set
            if not current_task:
                print("No current task - no recovery needed")
                return False
            
            # Check if current task is in completed tasks list
            completed_tasks = session_data.get('completed_tasks', [])
            for completed_task in completed_tasks:
                task_name = completed_task.get('task_name', '')
                if task_name == current_task:
                    print(f"Task '{current_task}' found in completed tasks - no recovery needed")
                    return False
            
            # Check current task state for completion indicators
            current_task_state = session_data.get('current_task_state', {})
            if current_task_state:
                # Check if task status indicates completion
                task_status = current_task_state.get('status', '')
                if task_status in ['completed', 'finished', 'done']:
                    print(f"Task '{current_task}' status is '{task_status}' - no recovery needed")
                    return False
                
                # Check if task has completion metadata
                task_completed = current_task_state.get('task_completed', False)
                if task_completed:
                    print(f"Task '{current_task}' marked as completed - no recovery needed")
                    return False
                
                # Check if all trials are completed (task-specific logic)
                if self.check_task_completion(current_task, current_task_state):
                    print(f"All trials completed for '{current_task}' - no recovery needed")
                    return False
            
            # If we get here, recovery is needed
            print(f"Recovery needed for task '{current_task}'")
            return True
            
        except Exception as e:
            print(f"Error checking recovery need: {e}")
            # If unsure, err on the side of offering recovery
            return True
    
    def check_task_completion(self, task_name, task_state):
        """
        Check if a specific task is actually completed based on task-specific logic.
        """
        try:
            # Generic completion check - can be extended for specific tasks
            trial_data = task_state.get('trial_data', [])
            current_trial = task_state.get('current_trial', 0)
            total_trials = task_state.get('total_trials', 0)
            
            # If we have trial data and current trial >= total trials, task is done
            if total_trials > 0 and current_trial >= total_trials:
                print(f"Task completion detected: {current_trial}/{total_trials} trials")
                return True
            
            # Task-specific completion checks
            if task_name == "Stroop Colour-Word Task":
                # Stroop typically has a fixed number of trials (usually 20-40)
                # Check if we have all expected trials completed
                if len(trial_data) >= 20:  # Assuming minimum 20 trials for Stroop
                    # Check if task was properly concluded
                    completion_time = task_state.get('completion_time')
                    if completion_time:
                        print(f"Stroop task completion detected: {len(trial_data)} trials, completion time set")
                        return True
                    
                    # Check if current index matches trial count (task finished)
                    current_index = task_state.get('current_index', 0)
                    if current_index >= len(trial_data) and len(trial_data) > 0:
                        print(f"Stroop task completion detected: reached end of trials")
                        return True
            
            elif task_name == "Letter Monitoring Task":
                # Add Letter Monitoring specific completion checks
                if len(trial_data) >= 30:  # Assuming minimum trials
                    completion_time = task_state.get('completion_time')
                    if completion_time:
                        return True
            
            elif task_name == "Visual Search Task":
                # Add Visual Search specific completion checks
                if len(trial_data) >= 25:  # Assuming minimum trials
                    completion_time = task_state.get('completion_time')
                    if completion_time:
                        return True
            
            # Add other task-specific completion checks here as tasks are implemented
            
            return False
            
        except Exception as e:
            print(f"Error checking task completion: {e}")
            return False
    
    def cleanup_completed_session(self, session_file, folder_path, structure_type="organized"):
        """
        Clean up session files for completed tasks to prevent false recovery offers.
        Updated to handle both organized and legacy folder structures.
        """
        try:
            print(f"Cleaning up completed session files in: {folder_path} [{structure_type}]")
            
            if structure_type == "organized":
                # Organized structure: files are in system/ folder
                system_folder = os.path.join(folder_path, "system")
                
                files_to_remove = [
                    os.path.join(system_folder, "session_state.json"),
                    os.path.join(system_folder, "recovery_data.json"),
                    os.path.join(system_folder, "app_heartbeat.txt"),
                    os.path.join(system_folder, "app_heartbeat_metadata.json")            
                ]
                
                for file_path in files_to_remove:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed: system/{os.path.basename(file_path)}")
                
                print("Completed session cleanup - organized structure")
                print("Data files preserved in biodata/ and task folders, recovery files removed from system/")
                
            else:
                # Legacy structure: files are in root folder
                files_to_remove = [
                    session_file,
                    os.path.join(folder_path, "recovery_data.json"),
                    os.path.join(folder_path, "app_heartbeat.txt"),
                    os.path.join(folder_path, "app_heartbeat_metadata.json")
                ]
                
                for file_path in files_to_remove:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed: {os.path.basename(file_path)}")
                
                print("Completed session cleanup - legacy structure")
                print("Data files preserved, recovery files removed")
            
        except Exception as e:
            print(f"Error during session cleanup: {e}")
    
    def show_recovery_notification(self):
        """Show notification about recoverable sessions."""
        if len(self.recovery_sessions) == 1:
            # Single session - show simple dialog
            session = self.recovery_sessions[0]
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Session Recovery Available")
            msg.setText(f"A previous incomplete session was found:")
            msg.setInformativeText(
                f"Participant: {session['participant_id']}\n"
                f"Task: {session['current_task']}\n"
                f"Trials completed: {session['trials_completed']}\n"
                f"Last saved: {session['last_save']}\n\n"
                f"Would you like to continue from where you left off?"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            # Custom button styling
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #f6f6f6;
                    font-family: Arial;
                    font-size: 12px;
                }
                QMessageBox QLabel {
                    color: black;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    border: 2px solid #c0c0c0;
                    border-radius: 5px;
                    padding: 8px 15px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
            """)
            
            result = msg.exec()
            
            if result == QMessageBox.StandardButton.Yes:
                self.selected_recovery_session = session
                self.load_participant_for_recovery()
            else:
                self.clear_selected_session()
        
        elif len(self.recovery_sessions) > 1:
            # Multiple sessions - show selection dialog
            dialog = RecoverySelectionDialog(self.recovery_sessions, self)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                if dialog.selected_session:
                    self.selected_recovery_session = dialog.selected_session
                    self.load_participant_for_recovery()
                else:
                    # User chose to start new session - clear all
                    self.clear_all_recovery_sessions()
    
    def load_participant_for_recovery(self):
        """Load participant biodata and go directly to recovery."""
        if not self.selected_recovery_session:
            return
        
        session = self.selected_recovery_session
        participant_id = session['participant_id']
        participant_folder_path = session['folder_path']
        
        print(f"Loading participant {participant_id} for recovery...")
        
        try:
            # Initialize session manager with existing data
            session_manager = initialize_session_manager(participant_id, participant_folder_path)
            
            # Restore the session data
            session_manager.session_data = session['session_data'].copy()
            session_manager.session_data['last_save_time'] = datetime.now().isoformat()
            session_manager.save_session_state()
            
            # Mark that recovery is needed
            session_manager._existing_session = session['session_data']
            session_manager._recovery_needed = True
            
            print(f"Session manager initialized for recovery: {participant_id}")
            
            # Go directly to selection menu with recovery
            from menu_selection import SelectionMenu
            current_geometry = self.geometry()
            
            self.selection_menu = SelectionMenu(
                buttons_size=1.0,
                buttons_elevation=0.5,
                participant_id=participant_id,
                participant_folder_path=participant_folder_path,
                recovery_mode=True
            )
            self.selection_menu.setGeometry(current_geometry)
            self.selection_menu.show()
            self.hide()
            
        except Exception as e:
            print(f"Error loading participant for recovery: {e}")
            QMessageBox.critical(self, "Recovery Error", 
                               f"Failed to load recovery session:\n{str(e)}")
    
    def clear_selected_session(self):
        """Clear the selected session files."""
        if not self.selected_recovery_session:
            return
        
        try:
            session_file = self.selected_recovery_session['session_file']
            folder_path = self.selected_recovery_session['folder_path']
            
            self.cleanup_completed_session(session_file, folder_path)
            
        except Exception as e:
            print(f"Error clearing session files: {e}")
    
    def clear_all_recovery_sessions(self):
        """Clear all recovery session files."""
        for session in self.recovery_sessions:
            try:
                session_file = session['session_file']
                folder_path = session['folder_path']
                
                self.cleanup_completed_session(session_file, folder_path)
                
                print(f"Cleared all recovery files for: {session['participant_id']}")
                
            except Exception as e:
                print(f"Error clearing recovery files for {session['participant_id']}: {e}")
        
        print("All recovery sessions cleared - starting fresh")
    
    def format_description_text(self, text, words_per_line=6):
        """Helper function to format text with specified words per line"""
        words = text.split()
        lines = []
        for i in range(0, len(words), words_per_line):
            line = ' '.join(words[i:i + words_per_line])
            lines.append(line)
        return '\n'.join(lines)
    
    def next_clicked(self):
        print("Next button clicked! Loading biodata menu...")
        
        # Get current window geometry (position and size)
        current_geometry = self.geometry()
        
        # Create and show the biodata menu
        self.biodata_menu = BiodataMenu(next_button_size=1.0, next_button_elevation=0.5, title_font_size=42)
        
        # Set the biodata menu to the same position as current window
        self.biodata_menu.setGeometry(current_geometry)
        self.biodata_menu.show()
        
        # Hide the welcome window
        self.hide()
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop crash detector
        if hasattr(self, 'crash_detector'):
            self.crash_detector.stop_monitoring()
        
        # Clean up session manager if no active session
        session_manager = get_session_manager()
        if session_manager and not session_manager.session_data.get('current_task'):
            session_manager._cleanup_session()
        
        event.accept()

def main():
    """Main function with crash recovery support."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")
    
    print("=== CUSTOM TESTS BATTERY STARTING ===")
    print("Crash recovery system: ENABLED")
    print("Enhanced recovery logic: ACTIVE")
    print("Completed task detection: ENABLED")
    print("Checking for previous sessions...")
    
    # You can customize these parameters:
    # title_font_size: Controls the size of "Custom Tests Battery" title (default: 36)
    # description_font_size: Controls the size of the description text (default: 16)
    # next_button_size: Controls the size of the next button (default: 1.0, use 1.5 for bigger, 0.8 for smaller)
    # next_button_elevation: Controls how much the neumorphic next button stands out (default: 1.0, use 2.0 for more raised, 0.5 for subtle)
    
    # Create and show the welcome window
    # When Next is clicked, it will load the biodata menu, then the sel ection menu
    window = WelcomeWindow(title_font_size=56, description_font_size=36, next_button_size=1.0, next_button_elevation=0.5)
    
    window.show()
    
    # Run application with error handling
    try:
        exit_code = app.exec()
        print("Application closed normally")
        return exit_code
    except Exception as e:
        print(f"Application crashed during execution: {e}")
        
        # Try to perform emergency save
        session_manager = get_session_manager()
        if session_manager:
            try:
                session_manager.emergency_save()
                print("Emergency save completed")
            except Exception as save_error:
                print(f"Emergency save failed: {save_error}")
        
        # Re-raise the exception
        raise
    finally:
        # Cleanup session manager on exit
        from crash_recovery_system.session_manager import cleanup_session_manager
        cleanup_session_manager()
        print("Session cleanup completed")

if __name__ == "__main__":
    main()