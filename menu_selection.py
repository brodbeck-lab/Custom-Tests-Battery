import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Import crash recovery system
from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager
from crash_recovery_system.task_state_saver import get_recovery_info, CrashDetector
import crash_recovery_system.crash_handler as crash_handler  # Initialize crash handler


class SelectionMenu(QMainWindow):
    def __init__(self, buttons_size=1.0, buttons_elevation=1.0, participant_id=None, participant_folder_path=None, recovery_mode=False):
        super().__init__()
        self.setWindowTitle("Custom Tests Battery - Test Selection")

        # Center the window on the screen 
        screen = QApplication.primaryScreen().geometry()
        window_width, window_height = 1370, 960
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        self.setStyleSheet("background-color: #f6f6f6;")
        
        # Store participant information
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        self.recovery_mode = recovery_mode
        
        # Recovery-related attributes
        self.recovery_info = {}
        self.current_recoverable_task = None
        self.recovery_status_widget = None
        
        print(f"=== SELECTION MENU INITIALIZATION ===")
        print(f"Received participant_id: '{participant_id}' (type: {type(participant_id)})")
        print(f"Received participant_folder_path: '{participant_folder_path}' (type: {type(participant_folder_path)})")
        print(f"Recovery mode: {'ENABLED' if recovery_mode else 'DISABLED'}")
        print(f"Stored self.participant_id: '{self.participant_id}'")
        print(f"Stored self.participant_folder_path: '{self.participant_folder_path}'")
        print(f"Crash recovery system: ACTIVE")
        print(f"Configuration interface: ENABLED for Stroop and CVC tasks")
        print(f"=====================================")
        
        if not participant_id or not participant_folder_path:
            print("WARNING: Selection menu initialized without complete participant information!")
        else:
            print("SUCCESS: Selection menu initialized with complete participant information")
        
        # Initialize crash detector for this session
        self.crash_detector = CrashDetector(get_session_manager())
        self.crash_detector.start_monitoring()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main vertical layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(50, 50, 50, 50)
        
        # Add recovery status section (will be populated if needed)
        self.recovery_container = QWidget()
        self.recovery_container_layout = QVBoxLayout()
        self.recovery_container_layout.setContentsMargins(0, 0, 0, 0)
        self.recovery_container.setLayout(self.recovery_container_layout)
        main_layout.addWidget(self.recovery_container)
        
        # Add top spacer to center the buttons vertically
        top_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(top_spacer)
        
        # Create grid layout for buttons (2 rows, 3 columns)
        buttons_grid = QGridLayout()
        buttons_grid.setSpacing(30)  # Space between buttons
        
        # Calculate button dimensions and styling based on parameters
        button_width = int(300 * buttons_size)
        button_height = int(100 * buttons_size)
        button_radius = int(25 * buttons_size)
        button_font_size = int(18 * buttons_size)
        
        # Calculate neumorphism colors based on elevation
        light_color = min(255, int(255 - (10 * (1 - buttons_elevation))))
        dark_color = max(200, int(240 - (40 * buttons_elevation)))
        border_light = max(180, int(224 - (44 * buttons_elevation)))
        border_dark = max(160, int(192 - (32 * buttons_elevation)))
        
        light_hex = f"#{light_color:02x}{light_color:02x}{light_color:02x}"
        dark_hex = f"#{dark_color:02x}{dark_color:02x}{dark_color:02x}"
        border_light_hex = f"#{border_light:02x}{border_light:02x}{border_light:02x}"
        border_dark_hex = f"#{border_dark:02x}{border_dark:02x}{border_dark:02x}"
        
        button_border_thickness = max(1, int(3 * buttons_elevation))
        
        # Store button styling for recovery updates
        self.normal_button_style = f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 {light_hex}, stop: 1 {dark_hex});
                color: black;
                border: {button_border_thickness}px solid {border_light_hex};
                border-radius: {button_radius}px;
                padding: 15px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fafafa, stop: 1 {dark_hex});
                border: {button_border_thickness}px solid {border_light_hex};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 {dark_hex}, stop: 1 {light_hex});
                border: {button_border_thickness}px solid {border_dark_hex};
            }}
        """
        
        # Recovery button style (highlighted)
        self.recovery_button_style = f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fff3cd, stop: 1 #ffeaa7);
                color: black;
                border: {button_border_thickness + 1}px solid #f39c12;
                border-radius: {button_radius}px;
                padding: 15px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fff8e1, stop: 1 #ffecb3);
                border: {button_border_thickness + 1}px solid #e67e22;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffeaa7, stop: 1 #fff3cd);
                border: {button_border_thickness + 1}px solid #d35400;
            }}
        """
        
        # Completed button style (disabled/grayed out)
        self.completed_button_style = f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #e8f5e8, stop: 1 #d4edda);
                color: #495057;
                border: {button_border_thickness}px solid #c3e6cb;
                border-radius: {button_radius}px;
                padding: 15px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #f0f8f0, stop: 1 #e2f0e2);
                border: {button_border_thickness}px solid #b8dfb8;
            }}
        """
        
        # Define button texts - UPDATED to include CVC Task
        button_texts = [
            "Stroop Colour-Word Task",
            "CVC Task",  # CHANGED from "Letter Monitoring Task"
            "Visual Search Task",
            "Attention Network Task",
            "Go/No-Go Task",
            "Reading Span Test"
        ]
        
        # Create the six buttons
        self.test_buttons = []
        self.button_info = {}  # Store button info for recovery updates
        
        for i, button_text in enumerate(button_texts):
            button = QPushButton(button_text)
            button.setFont(QFont("Arial", button_font_size, QFont.Weight.Bold))
            button.setFixedSize(button_width, button_height)
            button.setStyleSheet(self.normal_button_style)
            
            # Connect button to its respective handler
            button.clicked.connect(lambda checked, text=button_text: self.test_selected(text))
            
            # Store button info
            self.button_info[button_text] = {
                'button': button,
                'original_text': button_text,
                'status': 'available'  # available, current, completed
            }
            
            # Calculate row and column for grid placement
            row = i // 3  # 0 for first 3 buttons, 1 for last 3 buttons
            col = i % 3   # 0, 1, 2 for each row
            
            # Add button to grid
            buttons_grid.addWidget(button, row, col)
            self.test_buttons.append(button)
        
        # Add the grid to main layout
        main_layout.addLayout(buttons_grid)
        
        # Add bottom spacer
        bottom_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(bottom_spacer)
        
        # Set layout to central widget
        central_widget.setLayout(main_layout)
        
        # Check for recovery after UI setup
        QTimer.singleShot(200, self.check_and_handle_recovery)
    
    def check_and_handle_recovery(self):
        """Check for recovery needs and handle accordingly."""
        session_manager = get_session_manager()
        if not session_manager:
            print("No session manager available - recovery disabled")
            return
        
        # Check if recovery dialog is needed
        if hasattr(session_manager, '_recovery_needed') and session_manager._recovery_needed:
            print("Recovery dialog needed - showing recovery options")
            self.show_recovery_dialog()
        
        # Always check recovery info to update UI
        self.update_recovery_ui()
    
    def show_recovery_dialog(self):
        """Show recovery dialog to user."""
        session_manager = get_session_manager()
        if not session_manager:
            return
        
        try:
            recovery_accepted = session_manager.show_recovery_dialog(self)
            
            if recovery_accepted:
                print("Recovery accepted - updating UI for recovery mode")
                self.recovery_mode = True
                self.update_recovery_ui()
                self.show_recovery_welcome_message()
            else:
                print("Recovery declined - starting fresh")
                self.recovery_mode = False
                # Clear any recovery indicators
                self.clear_recovery_ui()
        
        except Exception as e:
            print(f"Error showing recovery dialog: {e}")
            QMessageBox.warning(self, "Recovery Error", 
                              f"Error handling session recovery:\n{str(e)}")
    
    def update_recovery_ui(self):
        """Update UI to show recovery information and task status."""
        session_manager = get_session_manager()
        if not session_manager:
            return
        
        try:
            # Get current recovery info
            self.recovery_info = get_recovery_info()
            
            if self.recovery_info.get('recoverable'):
                current_task = self.recovery_info.get('current_task')
                trials_completed = self.recovery_info.get('trials_completed', 0)
                self.current_recoverable_task = current_task
                
                print(f"Updating UI for recovery: {current_task} ({trials_completed} trials)")
                
                # Show recovery status banner
                self.show_recovery_status(current_task, trials_completed)
                
                # Update button states
                self.update_button_states(current_task)
            else:
                # No recovery needed - update based on completed tasks
                self.update_button_states_from_session()
        
        except Exception as e:
            print(f"Error updating recovery UI: {e}")
    
    def show_recovery_status(self, current_task, trials_completed):
        """Show recovery status banner at the top."""
        # Clear existing recovery status
        self.clear_recovery_status()
        
        # Create recovery status widget
        self.recovery_status_widget = QWidget()
        recovery_layout = QVBoxLayout()
        recovery_layout.setContentsMargins(10, 10, 10, 10)
        
        # Main recovery message
        recovery_title = QLabel("🔄 SESSION RECOVERY ACTIVE")
        recovery_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        recovery_title.setStyleSheet("""
            QLabel {
                color: #d35400;
                background-color: #fdf2e9;
                border: 3px solid #f39c12;
                border-radius: 10px;
                padding: 15px;
                margin: 5px 0px;
            }
        """)
        recovery_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recovery_layout.addWidget(recovery_title)
        
        # Recovery details
        recovery_details = (
            f"Continuing previous session for {self.participant_id}\n"
            f"Current task: {current_task} ({trials_completed} trials completed)\n"
            f"Click the highlighted task below to continue where you left off"
        )
        
        recovery_info_label = QLabel(recovery_details)
        recovery_info_label.setFont(QFont("Arial", 12))
        recovery_info_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 12px;
                margin: 2px 0px;
                line-height: 1.4;
            }
        """)
        recovery_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recovery_info_label.setWordWrap(True)
        recovery_layout.addWidget(recovery_info_label)
        
        self.recovery_status_widget.setLayout(recovery_layout)
        self.recovery_container_layout.addWidget(self.recovery_status_widget)
        
        print("Recovery status banner displayed")
    
    def show_recovery_welcome_message(self):
        """Show welcome back message after recovery is accepted."""
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Welcome Back!")
            msg.setText("Session Recovery Successful")
            msg.setInformativeText(
                f"Welcome back! Your previous session has been restored.\n\n"
                f"• Participant: {self.participant_id}\n"
                f"• Resuming: {self.current_recoverable_task}\n"
                f"• Progress: {self.recovery_info.get('trials_completed', 0)} trials completed\n\n"
                f"The highlighted task below will continue from where you left off."
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Style the message box
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #f6f6f6;
                    font-family: Arial;
                }
                QMessageBox QLabel {
                    color: black;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 20px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            
            msg.exec()
            
        except Exception as e:
            print(f"Error showing welcome message: {e}")
    
    def update_button_states(self, current_task):
        """Update button states based on recovery information."""
        session_manager = get_session_manager()
        if not session_manager:
            return
        
        try:
            completed_tasks = [task['task_name'] for task in session_manager.session_data.get('completed_tasks', [])]
            
            for task_name, info in self.button_info.items():
                button = info['button']
                
                if task_name == current_task:
                    # Current task - highlight for recovery
                    trials_completed = self.recovery_info.get('trials_completed', 0)
                    button.setText(f"{info['original_text']}\n⏯️ Resume ({trials_completed} trials completed)")
                    button.setStyleSheet(self.recovery_button_style)
                    info['status'] = 'current'
                    print(f"Highlighted recovery task: {task_name}")
                
                elif task_name in completed_tasks:
                    # Completed task - show as completed
                    button.setText(f"{info['original_text']}\n✅ Completed")
                    button.setStyleSheet(self.completed_button_style)
                    info['status'] = 'completed'
                    print(f"Marked as completed: {task_name}")
                
                else:
                    # Available task - normal style
                    button.setText(info['original_text'])
                    button.setStyleSheet(self.normal_button_style)
                    info['status'] = 'available'
        
        except Exception as e:
            print(f"Error updating button states: {e}")
    
    def update_button_states_from_session(self):
        """Update button states based on session data (no recovery)."""
        session_manager = get_session_manager()
        if not session_manager:
            return
        
        try:
            completed_tasks = [task['task_name'] for task in session_manager.session_data.get('completed_tasks', [])]
            
            for task_name, info in self.button_info.items():
                button = info['button']
                
                if task_name in completed_tasks:
                    # Completed task
                    button.setText(f"{info['original_text']}\n✅ Completed")
                    button.setStyleSheet(self.completed_button_style)
                    info['status'] = 'completed'
                else:
                    # Available task
                    button.setText(info['original_text'])
                    button.setStyleSheet(self.normal_button_style)
                    info['status'] = 'available'
        
        except Exception as e:
            print(f"Error updating button states from session: {e}")
    
    def clear_recovery_status(self):
        """Clear the recovery status banner."""
        if self.recovery_status_widget:
            self.recovery_container_layout.removeWidget(self.recovery_status_widget)
            self.recovery_status_widget.deleteLater()
            self.recovery_status_widget = None
    
    def clear_recovery_ui(self):
        """Clear all recovery UI elements."""
        self.clear_recovery_status()
        
        # Reset all buttons to normal state
        for task_name, info in self.button_info.items():
            button = info['button']
            button.setText(info['original_text'])
            button.setStyleSheet(self.normal_button_style)
            info['status'] = 'available'
    
    def test_selected(self, test_name):
        """Handle test selection with recovery support and enhanced error handling."""
        # Clean up test name if it has recovery info
        clean_test_name = test_name.split('\n')[0]  # Remove recovery text
        
        print(f"Test selected: {clean_test_name}")
        print(f"Recovery mode: {self.recovery_mode}")
        print(f"Current recoverable task: {self.current_recoverable_task}")
        
        # Check if this is a completed task
        button_status = self.button_info.get(clean_test_name, {}).get('status', 'available')
        if button_status == 'completed':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Task Already Completed")
            msg.setText(f"{clean_test_name} has already been completed.")
            msg.setInformativeText("Would you like to run it again or select a different task?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.button(QMessageBox.StandardButton.Yes).setText("Run Again")
            msg.button(QMessageBox.StandardButton.No).setText("Select Different Task")
            
            result = msg.exec()
            if result == QMessageBox.StandardButton.No:
                return  # User chose not to run again
            # If Yes, continue with launching the task
        
        # Get current window position for consistent positioning
        current_geometry = self.geometry()
        x_pos = current_geometry.x()
        y_pos = current_geometry.y()
        
        # Verify participant information before launching any test
        if not self.participant_id or not self.participant_folder_path:
            print("ERROR: Missing participant information for test launch")
            QMessageBox.critical(self, "Error", 
                               "Cannot start test!\n\n"
                               "Participant information is missing. "
                               "Please go back and save the biodata form first.")
            return
        
        # Verify session manager is available
        session_manager = get_session_manager()
        if not session_manager:
            print("WARNING: No session manager available - crash recovery disabled")
            QMessageBox.warning(self, "Warning", 
                              "Crash recovery system is not available.\n\n"
                              "The test will run normally, but progress may not be saved "
                              "if the application crashes.")
        
        if clean_test_name == "Stroop Colour-Word Task":
            self.launch_stroop_task(x_pos, y_pos)
        
        elif clean_test_name == "CVC Task":  # CHANGED from "Letter Monitoring Task"
            self.launch_cvc_task(x_pos, y_pos)
            
        elif clean_test_name == "Visual Search Task":
            self.launch_visual_search_task(x_pos, y_pos)
            
        elif clean_test_name == "Attention Network Task":
            self.launch_attention_network_task(x_pos, y_pos)
            
        elif clean_test_name == "Go/No-Go Task":
            self.launch_gonogo_task(x_pos, y_pos)
            
        elif clean_test_name == "Reading Span Test":
            self.launch_reading_span_test(x_pos, y_pos)
        
        else:
            print(f"Unknown test: {clean_test_name}")
            QMessageBox.warning(self, "Unknown Test", f"Test '{clean_test_name}' is not recognized.")
    
    def launch_stroop_task(self, x_pos, y_pos):
        """Launch Stroop Color-Word Task with configuration interface and enhanced error handling."""
        try:
            print(f"Launching Stroop Color-Word task with configuration interface:")
            print(f"  - Participant ID: {self.participant_id}")
            print(f"  - Participant folder: {self.participant_folder_path}")
            print(f"  - Position: x={x_pos}, y={y_pos}")
            print(f"  - Recovery mode: {self.recovery_mode}")
            print(f"  - Session manager: {'AVAILABLE' if get_session_manager() else 'NOT AVAILABLE'}")
            print(f"  - Configuration interface: ENABLED")
            
            # Import the updated StroopColorWordTask with configuration interface
            from task_stroop_colorword.stroop_task import StroopColorWordTask
            
            # Create Stroop Color-Word task with configuration support and recovery
            self.stroop_colorword_task = StroopColorWordTask(
                csv_file=None,
                x_pos=x_pos, 
                y_pos=y_pos,
                participant_id=self.participant_id,
                participant_folder_path=self.participant_folder_path
            )
            
            # Show the task (it will start in configuration mode)
            self.stroop_colorword_task.show()
            print("Stroop Colour-Word Task launched successfully with configuration interface")
            print("User will now configure task parameters before starting")
            
            # Hide the selection menu
            self.hide()
            
        except Exception as e:
            print(f"Error launching Stroop Color-Word Task: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Emergency save if session manager available
            session_manager = get_session_manager()
            if session_manager:
                try:
                    session_manager.emergency_save()
                    print("Emergency save completed due to Stroop launch error")
                except Exception as save_error:
                    print(f"Emergency save failed: {save_error}")
            
            QMessageBox.critical(self, "Launch Error", 
                               f"Failed to launch Stroop Color-Word task!\n\n"
                               f"Error: {str(e)}\n\n"
                               f"Please try again or contact support if the problem persists.")

    def launch_cvc_task(self, x_pos, y_pos):
        """Launch CVC Task with configuration interface and enhanced error handling."""
        try:
            print(f"Launching CVC task with configuration interface:")
            print(f"  - Participant ID: {self.participant_id}")
            print(f"  - Participant folder: {self.participant_folder_path}")
            print(f"  - Position: x={x_pos}, y={y_pos}")
            print(f"  - Recovery mode: {self.recovery_mode}")
            print(f"  - Session manager: {'AVAILABLE' if get_session_manager() else 'NOT AVAILABLE'}")
            print(f"  - Configuration interface: ENABLED")
            
            # Import the CVC task
            from task_cvc.cvc_task import CVCTask
            
            # Create CVC task with configuration support and recovery
            self.cvc_task = CVCTask(
                csv_file=None,
                x_pos=x_pos, 
                y_pos=y_pos,
                participant_id=self.participant_id,
                participant_folder_path=self.participant_folder_path
            )
            
            # Show the task (it will start in configuration mode)
            self.cvc_task.show()
            print("CVC Task launched successfully with configuration interface")
            print("User will now configure task parameters before starting")
            
            # Hide the selection menu
            self.hide()

        except Exception as e:
            print(f"Error launching CVC Task: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Emergency save if session manager available
            session_manager = get_session_manager()
            if session_manager:
                try:
                    session_manager.emergency_save()
                    print("Emergency save completed due to CVC launch error")
                except Exception as save_error:
                    print(f"Emergency save failed: {save_error}")
            
            QMessageBox.critical(self, "Launch Error", 
                               f"Failed to launch CVC task!\n\n"
                               f"Error: {str(e)}\n\n"
                               f"Please try again or contact support if the problem persists.")
    
    def launch_visual_search_task(self, x_pos, y_pos):
        """Launch Visual Search Task (placeholder)."""
        self.show_not_implemented_message("Visual Search Task")
    
    def launch_attention_network_task(self, x_pos, y_pos):
        """Launch Attention Network Task (placeholder)."""
        self.show_not_implemented_message("Attention Network Task")
    
    def launch_gonogo_task(self, x_pos, y_pos):
        """Launch Go/No-Go Task (placeholder)."""
        self.show_not_implemented_message("Go/No-Go Task")
    
    def launch_reading_span_test(self, x_pos, y_pos):
        """Launch Reading Span Test (placeholder)."""
        self.show_not_implemented_message("Reading Span Test")

    def handle_reading_span_result(self):
        """Handle the end of the Reading Span Test."""
        print("Reading Span Test completed.")

        # === Restore original SelectionMenu layout ===
        self.__init__(
            buttons_size=1.0,
            buttons_elevation=1.0,
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path,
            recovery_mode=self.recovery_mode
        )
        
        self.show()  # Bring the selection menu window back

    def show_not_implemented_message(self, task_name):
        """Show standardized message for not-yet-implemented tasks."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Task Not Available")
        msg.setText(f"{task_name}")
        msg.setInformativeText(
            f"{task_name} is not yet implemented.\n\n"
            f"It will be available in a future version.\n\n"
            f"Current available tasks:\n"
            f"• Stroop Colour-Word Task ✅ (with configuration interface)\n"
            f"• CVC Task ✅ (with configuration interface)\n"
            f"• Other tasks: Coming soon..."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Style the message box
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #f6f6f6;
                font-family: Arial;
            }
            QMessageBox QLabel {
                color: black;
                font-size: 12px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        msg.exec()
    
    def closeEvent(self, event):
        """Handle window close event with proper cleanup."""
        print("Selection menu closing - performing cleanup...")
        
        # Stop crash detector
        if hasattr(self, 'crash_detector'):
            self.crash_detector.stop_monitoring()
        
        # Clean up session manager if no tasks have been started
        session_manager = get_session_manager()
        if session_manager:
            current_task = session_manager.session_data.get('current_task')
            if not current_task:
                print("No active task - cleaning up session manager")
                session_manager._cleanup_session()
            else:
                print(f"Active task detected: {current_task} - preserving session")
        
        event.accept()
        print("Selection menu cleanup completed")

def main():
    """Standalone main function for testing selection menu."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")
    
    print("=== SELECTION MENU TESTING (WITH CVC TASK) ===")
    print("Crash recovery system: ENABLED")
    print("Stroop task configuration interface: ENABLED")
    print("CVC task configuration interface: ENABLED")
    print("Testing with sample participant data...")
    
    # Sample participant data for testing
    sample_participant_id = "TEST_PARTICIPANT_001"
    sample_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_PARTICIPANT_001")
    
    # Ensure test folder exists
    os.makedirs(sample_folder, exist_ok=True)
    
    # Initialize session manager for testing
    try:
        session_manager = initialize_session_manager(sample_participant_id, sample_folder)
        default_tasks = [
            "Stroop Colour-Word Task",
            "CVC Task",  # UPDATED to include CVC Task
            "Visual Search Task",
            "Attention Network Task",
            "Go/No-Go Task",
            "Reading Span Test"
        ]
        session_manager.set_task_queue(default_tasks)
        print("Session manager initialized for testing")
    except Exception as e:
        print(f"Error initializing session manager: {e}")
    
    # Create selection menu with CVC task support
    window = SelectionMenu(
        buttons_size=1.0, 
        buttons_elevation=1.0,
        participant_id=sample_participant_id,
        participant_folder_path=sample_folder,
        recovery_mode=False
    )
    
    window.show()
    
    try:
        exit_code = app.exec()
        print("Selection menu closed normally")
        return exit_code
    except Exception as e:
        print(f"Selection menu crashed: {e}")
        
        # Emergency save
        session_manager = get_session_manager()
        if session_manager:
            try:
                session_manager.emergency_save()
                print("Emergency save completed from selection menu")
            except:
                print("Emergency save failed from selection menu")
        
        raise
    finally:
        # Cleanup
        from crash_recovery_system.session_manager import cleanup_session_manager
        cleanup_session_manager()

if __name__ == "__main__":
    main()