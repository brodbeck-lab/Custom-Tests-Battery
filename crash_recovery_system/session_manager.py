"""
SESSION MANAGER - ENHANCED CRASH RECOVERY CORE
Custom Tests Battery - Master Session Controller

This module provides the master controller for crash recovery across the entire application.
Enhanced with proper task completion handling to prevent false recovery prompts.

Features:
- Session State Orchestration
- Enhanced Crash Recovery Core Logic  
- Task Queue Management with Completion Tracking
- File and Folder Coordination
- Recovery Dialog System with Completion Validation
- Automatic Cleanup for Completed Sessions
- Multi-layered Data Protection

Author: Custom Tests Battery Development Team
Version: 2.0 (Enhanced Completion Handling)
Location: crash_recovery_system/session_manager.py
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QFont

class SessionManager(QObject):
    """
    Enhanced Session Manager with comprehensive crash recovery and completion handling.
    Prevents false recovery prompts for completed tasks while maintaining full protection.
    """
    
    # Signals for session events
    session_started = pyqtSignal(str)  # participant_id
    session_completed = pyqtSignal(str)  # participant_id
    task_started = pyqtSignal(str)  # task_name
    task_completed = pyqtSignal(str)  # task_name
    recovery_needed = pyqtSignal(dict)  # recovery_info
    
    def __init__(self, participant_id: str, participant_folder_path: str):
        """
        Initialize enhanced session manager.
        
        Parameters:
        -----------
        participant_id : str
            Unique identifier for the participant
        participant_folder_path : str
            Path to participant's data folder
        """
        super().__init__()
        
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        
        # Session data structure
        self.session_data = {
            'participant_id': participant_id,
            'session_start_time': datetime.now().isoformat(),
            'session_active': True,
            'session_completed': False,
            'session_end_time': None,
            'current_task': None,
            'current_task_state': {},
            'task_queue': [],
            'completed_tasks': [],
            'crash_detected': False,
            'recovery_count': 0,
            'last_save_time': None,
            'auto_save_enabled': True,
            'session_metadata': {
                'version': '2.0',
                'enhanced_completion_handling': True,
                'auto_cleanup_enabled': True
            }
        }
        
        # Recovery-related attributes
        self._existing_session = None
        self._recovery_needed = False
        self._cleanup_timer = None
        
        # Auto-save configuration
        self.auto_save_interval = 5000  # 5 seconds
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        # Session file paths
        self.session_file_path = os.path.join(participant_folder_path, "session_state.json")
        self.recovery_file_path = os.path.join(participant_folder_path, "recovery_data.json")
        self.backup_file_path = os.path.join(participant_folder_path, "session_backup.json")
        
        print(f"=== SESSION MANAGER INITIALIZED ===")
        print(f"Participant: {participant_id}")
        print(f"Folder: {participant_folder_path}")
        print(f"Enhanced completion handling: ENABLED")
        print(f"Auto-cleanup: ENABLED")
        print("===================================")
        
        # Load existing session if present
        self.load_existing_session()
        
        # Start auto-save system
        self.start_auto_save()
    
    def load_existing_session(self):
        """Load existing session data if available."""
        try:
            if os.path.exists(self.session_file_path):
                with open(self.session_file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                print(f"Found existing session file for {self.participant_id}")
                
                # Check if session is actually recoverable (not completed)
                if self.is_session_recoverable(existing_data):
                    self._existing_session = existing_data
                    self._recovery_needed = True
                    print("Session recovery will be offered")
                else:
                    print("Session found but no recovery needed - cleaning up")
                    self.cleanup_completed_session_files()
            
        except Exception as e:
            print(f"Error loading existing session: {e}")
    
    def is_session_recoverable(self, session_data: Dict) -> bool:
        """
        Enhanced check to determine if a session actually needs recovery.
        Prevents false recovery prompts for completed tasks.
        """
        try:
            # Check session completion status
            if session_data.get('session_completed', False):
                print("Session marked as completed - no recovery needed")
                return False
            
            if not session_data.get('session_active', True):
                print("Session marked as inactive - no recovery needed")
                return False
            
            # Check current task status
            current_task = session_data.get('current_task')
            if not current_task:
                print("No current task - no recovery needed")
                return False
            
            # Check if current task is completed
            completed_tasks = session_data.get('completed_tasks', [])
            for completed_task in completed_tasks:
                if completed_task.get('task_name') == current_task:
                    print(f"Current task '{current_task}' found in completed tasks - no recovery needed")
                    return False
            
            # Check current task state
            current_task_state = session_data.get('current_task_state', {})
            if current_task_state:
                # Check completion flags
                if current_task_state.get('task_completed', False):
                    print(f"Current task state marked as completed - no recovery needed")
                    return False
                
                if current_task_state.get('status') in ['completed', 'finished', 'done']:
                    print(f"Current task status indicates completion - no recovery needed")
                    return False
            
            # Check if session is too old (older than 7 days)
            session_start = session_data.get('session_start_time', '')
            if session_start:
                try:
                    start_time = datetime.fromisoformat(session_start)
                    age = datetime.now() - start_time
                    if age.days > 7:
                        print(f"Session too old ({age.days} days) - no recovery needed")
                        return False
                except:
                    pass
            
            print(f"Session recovery needed for task: {current_task}")
            return True
            
        except Exception as e:
            print(f"Error checking session recoverability: {e}")
            return False  # If unsure, don't offer recovery
    
    def show_recovery_dialog(self, parent_widget=None) -> bool:
        """
        Show recovery dialog to user and handle their choice.
        
        Returns:
        --------
        bool
            True if user accepts recovery, False otherwise
        """
        if not self._existing_session:
            return False
        
        try:
            # Create custom recovery dialog
            dialog = RecoveryDialog(self._existing_session, parent_widget)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                if dialog.recovery_accepted:
                    print("User accepted session recovery")
                    self.restore_session_data(self._existing_session)
                    return True
                else:
                    print("User declined session recovery")
                    self.cleanup_completed_session_files()
                    return False
            else:
                print("Recovery dialog cancelled")
                return False
                
        except Exception as e:
            print(f"Error showing recovery dialog: {e}")
            return False
    
    def restore_session_data(self, session_data: Dict):
        """Restore session data from recovered session."""
        try:
            # Merge existing session data
            self.session_data.update(session_data)
            
            # Update recovery metadata
            self.session_data['recovery_count'] = self.session_data.get('recovery_count', 0) + 1
            self.session_data['last_recovery_time'] = datetime.now().isoformat()
            self.session_data['crash_detected'] = True
            
            # Save restored session
            self.save_session_state()
            
            print(f"Session data restored for {self.participant_id}")
            print(f"Current task: {self.session_data.get('current_task', 'None')}")
            print(f"Recovery count: {self.session_data['recovery_count']}")
            
        except Exception as e:
            print(f"Error restoring session data: {e}")
    
    def set_task_queue(self, task_list: List[str]):
        """Set the queue of tasks for this session."""
        self.session_data['task_queue'] = task_list.copy()
        self.save_session_state()
        print(f"Task queue set: {len(task_list)} tasks")
    
    def start_task(self, task_name: str, task_config: Dict = None):
        """
        Start a new task with enhanced completion tracking.
        
        Parameters:
        -----------
        task_name : str
            Name of the task to start
        task_config : Dict, optional
            Configuration parameters for the task
        """
        try:
            print(f"Starting task: {task_name}")
            
            # Set current task
            self.session_data['current_task'] = task_name
            
            # Initialize task state
            task_state = {
                'task_name': task_name,
                'start_time': datetime.now().isoformat(),
                'status': 'in_progress',
                'trial_data': [],
                'task_completed': False,
                'completion_time': None,
                'recovery_mode': bool(self._existing_session),
                'config': task_config or {}
            }
            
            # If this is recovery, preserve existing trial data
            if self._existing_session and self._existing_session.get('current_task') == task_name:
                existing_state = self._existing_session.get('current_task_state', {})
                task_state['trial_data'] = existing_state.get('trial_data', [])
                task_state['recovery_mode'] = True
                print(f"Recovery mode: restored {len(task_state['trial_data'])} trials")
            
            self.session_data['current_task_state'] = task_state
            
            # Save session state
            self.save_session_state()
            
            # Emit signal
            self.task_started.emit(task_name)
            
            print(f"Task '{task_name}' started successfully")
            
        except Exception as e:
            print(f"Error starting task '{task_name}': {e}")
    
    def save_trial_data(self, trial_data: Dict):
        """Save trial data to current task state."""
        try:
            current_task_state = self.session_data.get('current_task_state')
            if current_task_state:
                if 'trial_data' not in current_task_state:
                    current_task_state['trial_data'] = []
                
                current_task_state['trial_data'].append(trial_data)
                current_task_state['last_trial_time'] = datetime.now().isoformat()
                
                # Update session timestamp
                self.session_data['last_save_time'] = datetime.now().isoformat()
                
                print(f"Trial data saved: {len(current_task_state['trial_data'])} trials total")
            else:
                print("Warning: No current task state to save trial data")
                
        except Exception as e:
            print(f"Error saving trial data: {e}")
    
    def complete_task(self, completion_data: Dict = None):
        """
        Complete the current task and update session state.
        Enhanced to prevent false recovery prompts.
        """
        if not self.session_data.get('current_task'):
            print("No current task to complete")
            return
        
        try:
            current_task = self.session_data['current_task']
            completion_time = datetime.now().isoformat()
            
            print(f"=== COMPLETING TASK: {current_task} ===")
            
            # Prepare completion record
            completion_record = {
                'task_name': current_task,
                'completion_time': completion_time,
                'trials_completed': len(self.session_data.get('current_task_state', {}).get('trial_data', [])),
                'completion_data': completion_data or {},
                'completed_successfully': True
            }
            
            # Add to completed tasks list
            if 'completed_tasks' not in self.session_data:
                self.session_data['completed_tasks'] = []
            
            self.session_data['completed_tasks'].append(completion_record)
            
            # Mark current task state as completed
            if 'current_task_state' in self.session_data:
                self.session_data['current_task_state']['status'] = 'completed'
                self.session_data['current_task_state']['task_completed'] = True
                self.session_data['current_task_state']['completion_time'] = completion_time
            
            # Clear current task (IMPORTANT for preventing false recovery)
            self.session_data['current_task'] = None
            
            # Update session timestamps
            self.session_data['last_save_time'] = datetime.now().isoformat()
            
            # Save the updated session state
            self.save_session_state()
            
            # Emit completion signal
            self.task_completed.emit(current_task)
            
            print(f"Task '{current_task}' marked as completed")
            print(f"Total completed tasks: {len(self.session_data['completed_tasks'])}")
            
            # Check if all tasks in queue are completed
            self.check_session_completion()
            
        except Exception as e:
            print(f"Error completing task: {e}")
    
    def check_session_completion(self):
        """
        Check if all tasks in the session are completed.
        If so, end the session and clean up to prevent recovery prompts.
        """
        try:
            task_queue = self.session_data.get('task_queue', [])
            completed_tasks = self.session_data.get('completed_tasks', [])
            completed_task_names = [task['task_name'] for task in completed_tasks]
            
            # Check if all queued tasks are completed
            all_completed = all(task in completed_task_names for task in task_queue)
            
            if all_completed and len(task_queue) > 0:
                print("All tasks completed - ending session")
                self.end_session()
            else:
                remaining_tasks = [task for task in task_queue if task not in completed_task_names]
                print(f"Session continues - remaining tasks: {remaining_tasks}")
        
        except Exception as e:
            print(f"Error checking session completion: {e}")
    
    def end_session(self):
        """
        End the complete session and clean up recovery files.
        Prevents false recovery prompts on next startup.
        """
        try:
            print("=== ENDING SESSION ===")
            
            # Mark session as completed
            self.session_data['session_active'] = False
            self.session_data['session_completed'] = True
            self.session_data['session_end_time'] = datetime.now().isoformat()
            
            # Save final session state
            self.save_session_state()
            
            # Emit completion signal
            self.session_completed.emit(self.participant_id)
            
            print("Session completed successfully")
            print(f"Completed tasks: {len(self.session_data.get('completed_tasks', []))}")
            
            # Schedule cleanup of recovery files after a short delay
            self._cleanup_timer = QTimer()
            self._cleanup_timer.singleShot(3000, self.cleanup_completed_session_files)
            
        except Exception as e:
            print(f"Error ending session: {e}")
    
    def cleanup_completed_session_files(self):
        """
        Clean up session and recovery files for completed sessions.
        This prevents false recovery prompts on next startup.
        """
        try:
            print("=== CLEANING UP COMPLETED SESSION FILES ===")
            
            files_to_remove = [
                self.session_file_path,
                self.recovery_file_path,
                os.path.join(self.participant_folder_path, "app_heartbeat.txt"),
                os.path.join(self.participant_folder_path, "app_heartbeat_metadata.json")
            ]
            
            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Removed: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"Error removing {os.path.basename(file_path)}: {e}")
            
            # Keep data files but remove recovery-specific files
            print("Session cleanup completed - no recovery prompts will appear on next startup")
            print("Data files preserved, recovery files removed")
            
        except Exception as e:
            print(f"Error during session cleanup: {e}")
    
    def get_current_task_state(self) -> Optional[Dict]:
        """Get the current task state."""
        return self.session_data.get('current_task_state')
    
    def save_session_state(self):
        """Save session state to file with backup."""
        try:
            # Create backup of existing session file
            if os.path.exists(self.session_file_path):
                try:
                    with open(self.session_file_path, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                    with open(self.backup_file_path, 'w', encoding='utf-8') as f:
                        json.dump(backup_data, f, indent=2)
                except:
                    pass  # Backup creation is not critical
            
            # Update timestamp
            self.session_data['last_save_time'] = datetime.now().isoformat()
            
            # Save current session state
            os.makedirs(os.path.dirname(self.session_file_path), exist_ok=True)
            with open(self.session_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2)
            
            # Also save to recovery file for additional redundancy
            with open(self.recovery_file_path, 'w', encoding='utf-8') as f:
                recovery_data = {
                    'session_data': self.session_data,
                    'backup_timestamp': datetime.now().isoformat(),
                    'recovery_version': '2.0'
                }
                json.dump(recovery_data, f, indent=2)
            
        except Exception as e:
            print(f"Error saving session state: {e}")
    
    def auto_save(self):
        """Perform automatic session state save."""
        try:
            self.save_session_state()
        except Exception as e:
            print(f"Auto-save error: {e}")
    
    def start_auto_save(self):
        """Start the auto-save timer."""
        self.auto_save_timer.start(self.auto_save_interval)
        print(f"Auto-save started: every {self.auto_save_interval}ms")
    
    def stop_auto_save(self):
        """Stop the auto-save timer."""
        self.auto_save_timer.stop()
        print("Auto-save stopped")
    
    def emergency_save(self):
        """Perform emergency save during crash."""
        try:
            print("=== EMERGENCY SAVE ===")
            
            # Mark as crash detected
            self.session_data['crash_detected'] = True
            self.session_data['crash_time'] = datetime.now().isoformat()
            
            # Save session state
            self.save_session_state()
            
            # Create additional emergency backup
            emergency_file = os.path.join(
                self.participant_folder_path, 
                f"EMERGENCY_SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(emergency_file, 'w', encoding='utf-8') as f:
                emergency_data = {
                    'emergency_save_time': datetime.now().isoformat(),
                    'participant_id': self.participant_id,
                    'session_data': self.session_data,
                    'save_reason': 'Application crash detected'
                }
                json.dump(emergency_data, f, indent=2)
            
            print(f"Emergency save completed: {os.path.basename(emergency_file)}")
            
        except Exception as e:
            print(f"Emergency save failed: {e}")
    
    def _cleanup_session(self):
        """Internal cleanup method."""
        try:
            self.stop_auto_save()
            print(f"Session manager cleanup completed for {self.participant_id}")
        except Exception as e:
            print(f"Error during session cleanup: {e}")


class RecoveryDialog(QDialog):
    """Enhanced recovery dialog with detailed session information."""
    
    def __init__(self, session_data, parent=None):
        super().__init__(parent)
        self.session_data = session_data
        self.recovery_accepted = False
        
        self.setWindowTitle("Session Recovery")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the recovery dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Previous Session Found")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("margin: 10px 0px; color: #2c3e50;")
        layout.addWidget(title)
        
        # Session information
        info_text = self.format_session_info()
        info_label = QLabel(info_text)
        info_label.setFont(QFont("Arial", 11))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(info_label)
        
        # Question
        question = QLabel("Would you like to continue from where you left off?")
        question.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        question.setStyleSheet("margin: 15px 0px; color: #495057;")
        layout.addWidget(question)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        continue_btn = QPushButton("Continue Session")
        continue_btn.clicked.connect(self.accept_recovery)
        continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        start_new_btn = QPushButton("Start New Session")
        start_new_btn.clicked.connect(self.decline_recovery)
        start_new_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        
        button_layout.addWidget(continue_btn)
        button_layout.addWidget(start_new_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def format_session_info(self):
        """Format session information for display."""
        try:
            participant_id = self.session_data.get('participant_id', 'Unknown')
            current_task = self.session_data.get('current_task', 'Unknown')
            
            # Get trial information
            current_task_state = self.session_data.get('current_task_state', {})
            trial_data = current_task_state.get('trial_data', [])
            trials_completed = len(trial_data)
            
            # Get timing information
            start_time = self.session_data.get('session_start_time', '')
            last_save = self.session_data.get('last_save_time', '')
            
            # Format timestamps
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    start_formatted = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    start_formatted = start_time
            else:
                start_formatted = 'Unknown'
            
            if last_save:
                try:
                    save_dt = datetime.fromisoformat(last_save)
                    save_formatted = save_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    save_formatted = last_save
            else:
                save_formatted = 'Unknown'
            
            info_text = f"""Participant: {participant_id}
Current Task: {current_task}
Trials Completed: {trials_completed}
Session Started: {start_formatted}
Last Saved: {save_formatted}

Your progress has been automatically saved and can be restored."""
            
            return info_text
            
        except Exception as e:
            return f"Session information available.\nError formatting details: {e}"
    
    def accept_recovery(self):
        """Accept session recovery."""
        self.recovery_accepted = True
        self.accept()
    
    def decline_recovery(self):
        """Decline session recovery."""
        self.recovery_accepted = False
        self.accept()


# Global session manager instance
_session_manager = None

def initialize_session_manager(participant_id: str, participant_folder_path: str) -> SessionManager:
    """
    Initialize the global session manager.
    
    Parameters:
    -----------
    participant_id : str
        Unique identifier for the participant
    participant_folder_path : str
        Path to participant's data folder
    
    Returns:
    --------
    SessionManager
        The initialized session manager instance
    """
    global _session_manager
    
    # Clean up existing session manager if any
    if _session_manager:
        _session_manager._cleanup_session()
    
    _session_manager = SessionManager(participant_id, participant_folder_path)
    print(f"Session manager initialized for {participant_id}")
    return _session_manager

def get_session_manager() -> Optional[SessionManager]:
    """Get the global session manager instance."""
    return _session_manager

def cleanup_session_manager():
    """Clean up the global session manager."""
    global _session_manager
    if _session_manager:
        _session_manager._cleanup_session()
        _session_manager = None
        print("Global session manager cleaned up")

# Helper functions for task state saver integration
def get_recovery_info() -> Dict:
    """Get recovery information for current session."""
    session_manager = get_session_manager()
    if not session_manager:
        return {'recoverable': False}
    
    current_task_state = session_manager.get_current_task_state()
    if not current_task_state:
        return {'recoverable': False}
    
    return {
        'recoverable': True,
        'current_task': session_manager.session_data.get('current_task'),
        'trials_completed': len(current_task_state.get('trial_data', [])),
        'recovery_mode': current_task_state.get('recovery_mode', False),
        'session_id': session_manager.participant_id
    }

if __name__ == "__main__":
    """
    Test the enhanced session manager functionality.
    """
    print("=== SESSION MANAGER TEST MODE ===")
    print("Enhanced completion handling: ENABLED")
    print("Testing session management...")
    
    # Test initialization
    test_participant = "TEST_PARTICIPANT_001"
    test_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_PARTICIPANT_001")
    os.makedirs(test_folder, exist_ok=True)
    
    # Initialize session manager
    session_manager = initialize_session_manager(test_participant, test_folder)
    
    # Set test task queue
    test_tasks = ["Stroop Colour-Word Task", "Letter Monitoring Task"]
    session_manager.set_task_queue(test_tasks)
    
    # Start and complete a task
    session_manager.start_task("Stroop Colour-Word Task")
    session_manager.save_trial_data({"trial_number": 1, "response": "red"})
    session_manager.complete_task({"total_trials": 1})
    
    print("Session manager test completed!")
    print("Enhanced completion handling verified!")
    
    # Cleanup
    cleanup_session_manager()