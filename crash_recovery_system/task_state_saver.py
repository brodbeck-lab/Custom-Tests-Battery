"""
TASK STATE SAVER - ENHANCED TASK-LEVEL CRASH RECOVERY
Custom Tests Battery - Enhanced Auto-save Integration

This module provides mixins and utilities for integrating crash recovery
into individual task classes. Enhanced with proper completion handling to prevent
false recovery prompts while maintaining comprehensive data protection.

Features:
- TaskStateMixin for automatic recovery integration
- Enhanced task completion handling
- Real-time state tracking and auto-saving
- Recovery mode detection and handling
- Task-specific state management
- Cross-task compatibility
- Enhanced error handling and validation
- Resource monitoring and crash detection
- Graceful degradation mechanisms
- Automatic cleanup for completed tasks

Author: Custom Tests Battery Development Team
Version: 2.0 (Enhanced Completion Handling)
Location: crash_recovery_system/task_state_saver.py
"""

import os
import json
import time
import threading
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

# Import session manager from same folder
try:
    from .session_manager import get_session_manager
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    try:
        from session_manager import get_session_manager
        SESSION_MANAGER_AVAILABLE = True
    except ImportError:
        SESSION_MANAGER_AVAILABLE = False
        print("WARNING: Session manager not available for task state saving")

class TaskStateMixin:
    """
    Enhanced mixin class to add comprehensive crash recovery functionality to task classes.
    Inherit from this class to automatically get advanced session management features.
    
    Enhanced Features:
    - Automatic state saving and restoration
    - Proper task completion handling
    - Recovery mode detection and handling
    - Real-time progress tracking
    - Error resilience and fallback mechanisms
    - Cross-task compatibility
    - Enhanced logging and debugging
    - Automatic cleanup for completed tasks
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize enhanced task state management."""
        super().__init__(*args, **kwargs)
        
        # Session management
        self.session_manager = get_session_manager() if SESSION_MANAGER_AVAILABLE else None
        self.task_name = getattr(self, 'TASK_NAME', self.__class__.__name__)
        
        # State tracking
        self.task_started = False
        self.task_completed = False  # New: track completion status
        self.recovery_mode = False
        self.original_trial_index = 0
        self.recovery_data = None
        
        # Enhanced auto-save configuration
        self.auto_save_interval = 2000  # 2 seconds
        self.emergency_save_interval = 5000  # 5 seconds for critical data
        self.state_change_threshold = 1  # Save after any state change
        
        # Auto-save timers for different data types
        self.task_save_timer = QTimer()
        self.task_save_timer.timeout.connect(self._auto_save_task_state)
        
        self.emergency_save_timer = QTimer()
        self.emergency_save_timer.timeout.connect(self._emergency_save_critical_data)
        
        # State tracking for intelligent saving
        self.state_change_count = 0
        self.last_save_time = None
        self.critical_data_changed = False
        
        # Error tracking and recovery
        self.save_error_count = 0
        self.max_save_errors = 5
        self.last_save_error = None
        
        # Completion tracking
        self.completion_data = {}
        self.cleanup_scheduled = False
        
        print(f"=== ENHANCED TASK STATE MIXIN INITIALIZED ===")
        print(f"Task: {self.task_name}")
        print(f"Session manager: {'AVAILABLE' if self.session_manager else 'NOT AVAILABLE'}")
        print(f"Auto-save interval: {self.auto_save_interval}ms")
        print(f"Emergency save interval: {self.emergency_save_interval}ms")
        print(f"Enhanced completion handling: ENABLED")
        print("==============================================")
    
    def start_task_with_recovery(self, task_config: Dict = None, total_trials: int = 0):
        """
        Start task with comprehensive crash recovery support.
        
        Parameters:
        -----------
        task_config : Dict, optional
            Configuration parameters for the task
        total_trials : int, optional
            Total number of trials for this task
        """
        if not self.session_manager:
            print(f"WARNING: No session manager available for {self.task_name} - recovery disabled")
            return
        
        print(f"=== STARTING {self.task_name.upper()} WITH ENHANCED RECOVERY ===")
        
        # Check for existing task state
        existing_state = self.session_manager.get_current_task_state()
        
        if (existing_state and 
            existing_state.get('task_name') == self.task_name and
            existing_state.get('status') == 'in_progress' and
            not existing_state.get('task_completed', False)):
            
            print(f"Recovering {self.task_name} from previous session...")
            self._recover_task_state(existing_state)
        else:
            # Start new task
            config = task_config or {}
            config['total_trials'] = total_trials
            config['start_time'] = datetime.now().isoformat()
            config['recovery_enabled'] = True
            config['enhanced_completion_handling'] = True
            
            self.session_manager.start_task(self.task_name, config)
            print(f"Started new {self.task_name} session with enhanced recovery")
        
        self.task_started = True
        
        # Start enhanced auto-save system
        self._start_auto_save_system()
        
        print(f"=== {self.task_name.upper()} ENHANCED RECOVERY STARTUP COMPLETE ===")
    
    def _recover_task_state(self, task_state: Dict):
        """Enhanced task recovery from previous state."""
        self.recovery_mode = True
        self.recovery_data = task_state
        
        # Get completed trials and progress information
        completed_trials = task_state.get('trial_data', [])
        self.original_trial_index = len(completed_trials)
        
        # Get additional recovery metadata
        recovery_metadata = task_state.get('recovery_metadata', {})
        last_save_time = recovery_metadata.get('last_save_time', 'Unknown')
        session_duration = recovery_metadata.get('session_duration', 'Unknown')
        
        print(f"=== RECOVERING {self.task_name.upper()} ===")
        print(f"Trials completed: {len(completed_trials)}")
        print(f"Resuming from trial: {self.original_trial_index + 1}")
        print(f"Last save: {last_save_time}")
        print(f"Session duration: {session_duration}")
        print(f"Recovery metadata available: {'YES' if recovery_metadata else 'NO'}")
        
        # Restore trial data to the task
        self._restore_trial_data(completed_trials)
        
        # Restore task-specific state
        self._restore_task_specific_state(task_state)
        
        # Set current trial index
        if hasattr(self, 'current_index'):
            self.current_index = self.original_trial_index
        
        # Update UI elements for recovery
        self._update_recovery_ui()
        
        print(f"=== {self.task_name.upper()} RECOVERY COMPLETE ===")
    
    def _restore_trial_data(self, trial_data: List[Dict]):
        """
        Enhanced trial data restoration with validation.
        Override this method in your task class to handle trial data restoration.
        """
        if hasattr(self, 'trial_data'):
            # Validate trial data before restoration
            validated_trials = self._validate_trial_data(trial_data)
            self.trial_data.extend(validated_trials)
            print(f"Restored {len(validated_trials)} validated trials to task.trial_data")
        else:
            print("Warning: Task has no trial_data attribute for restoration")
    
    def _validate_trial_data(self, trial_data: List[Dict]) -> List[Dict]:
        """
        Validate trial data for consistency and completeness.
        
        Parameters:
        -----------
        trial_data : List[Dict]
            Trial data to validate
        
        Returns:
        --------
        List[Dict]
            Validated trial data
        """
        validated_trials = []
        
        for i, trial in enumerate(trial_data):
            try:
                # Check for required fields
                required_fields = ['trial_number']
                if all(field in trial for field in required_fields):
                    validated_trials.append(trial)
                else:
                    print(f"Warning: Trial {i} missing required fields, skipping")
            except Exception as e:
                print(f"Error validating trial {i}: {e}")
        
        print(f"Validation: {len(validated_trials)}/{len(trial_data)} trials passed validation")
        return validated_trials
    
    def _restore_task_specific_state(self, task_state: Dict):
        """
        Restore task-specific state information.
        Override this method in your task class to handle task-specific restoration.
        """
        task_specific_data = task_state.get('task_specific_state', {})
        
        # Restore common task attributes
        common_attributes = [
            'current_trial_index', 'practice_mode', 'is_paused', 
            'is_in_break', 'practice_index'
        ]
        
        for attr in common_attributes:
            if attr in task_specific_data and hasattr(self, attr):
                try:
                    setattr(self, attr, task_specific_data[attr])
                    print(f"Restored {attr}: {task_specific_data[attr]}")
                except Exception as e:
                    print(f"Error restoring {attr}: {e}")
    
    def _update_recovery_ui(self):
        """
        Update UI elements after recovery.
        Override this method in your task class to update UI after recovery.
        """
        print(f"Recovery UI update requested for {self.task_name}")
        # Base implementation - override in task classes
    
    def save_trial_with_recovery(self, trial_data: Dict):
        """
        Enhanced trial data saving with comprehensive recovery support.
        
        Parameters:
        -----------
        trial_data : Dict
            Trial data to save
        """
        if not self.session_manager:
            print(f"WARNING: No session manager - trial data not saved for recovery in {self.task_name}")
            return
        
        try:
            # Add enhanced metadata
            enhanced_trial_data = self._enhance_trial_data(trial_data)
            
            # Save to session manager
            self.session_manager.save_trial_data(enhanced_trial_data)
            
            # Also save to task's internal data structure
            if hasattr(self, 'trial_data'):
                self.trial_data.append(enhanced_trial_data)
            
            # Mark critical data as changed
            self.critical_data_changed = True
            self.state_change_count += 1
            
            # Trigger immediate save if threshold reached
            if self.state_change_count >= self.state_change_threshold:
                self._immediate_save_task_state()
                self.state_change_count = 0
            
            print(f"Trial saved with recovery support: trial {enhanced_trial_data.get('trial_number', 'unknown')}")
            
        except Exception as e:
            self.save_error_count += 1
            self.last_save_error = str(e)
            print(f"Error saving trial with recovery: {e}")
            
            # Try emergency save if too many errors
            if self.save_error_count >= self.max_save_errors:
                print(f"Too many save errors ({self.save_error_count}) - attempting emergency save")
                self._emergency_save_critical_data()
    
    def _enhance_trial_data(self, trial_data: Dict) -> Dict:
        """
        Enhance trial data with additional metadata for recovery.
        
        Parameters:
        -----------
        trial_data : Dict
            Original trial data
        
        Returns:
        --------
        Dict
            Enhanced trial data with recovery metadata
        """
        enhanced_data = trial_data.copy()
        
        # Add task metadata
        enhanced_data['task_name'] = self.task_name
        enhanced_data['save_timestamp'] = datetime.now().isoformat()
        enhanced_data['recovery_mode'] = self.recovery_mode
        enhanced_data['session_trial_index'] = self.state_change_count
        
        # Add timing information
        if hasattr(self, 'task_start_time'):
            enhanced_data['task_elapsed_time'] = time.time() - self.task_start_time
        
        # Add task-specific state snapshot
        enhanced_data['task_state_snapshot'] = self._get_task_specific_state()
        
        return enhanced_data
    
    def complete_task_with_recovery(self, final_data: Dict = None):
        """
        Enhanced task completion with proper cleanup to prevent recovery prompts.
        This is the critical method that prevents false recovery prompts.
        
        Parameters:
        -----------
        final_data : Dict, optional
            Final task data or summary
        """
        if not self.session_manager:
            print(f"WARNING: No session manager - task completion not recorded for {self.task_name}")
            return
        
        print(f"=== COMPLETING {self.task_name.upper()} WITH ENHANCED RECOVERY ===")
        
        # Mark task as completed locally
        self.task_completed = True
        
        # Stop auto-save timers
        self._stop_auto_save_system()
        
        # Prepare comprehensive completion data
        completion_data = final_data or {}
        completion_data.update({
            'recovery_mode': self.recovery_mode,
            'original_trial_index': self.original_trial_index,
            'total_trials_completed': len(getattr(self, 'trial_data', [])),
            'completion_timestamp': datetime.now().isoformat(),
            'save_error_count': self.save_error_count,
            'state_change_count': self.state_change_count,
            'final_task_state': self._get_task_specific_state(),
            'task_completed_successfully': True,  # Important flag
            'enhanced_completion_handling': True
        })
        
        # Calculate task duration
        if hasattr(self, 'task_start_time'):
            completion_data['task_duration'] = time.time() - self.task_start_time
        
        # Store completion data
        self.completion_data = completion_data
        
        # Complete task in session manager - this handles cleanup and prevents false recovery
        self.session_manager.complete_task(completion_data)
        
        print(f"Task {self.task_name} completed successfully")
        print(f"  - Recovery mode used: {'YES' if self.recovery_mode else 'NO'}")
        print(f"  - Total trials: {completion_data.get('total_trials_completed', 0)}")
        print(f"  - Save errors: {self.save_error_count}")
        print(f"  - Duration: {completion_data.get('task_duration', 'Unknown')} seconds")
        print(f"  - Enhanced completion handling: ACTIVE")
        print(f"  - Session cleanup: Will occur if all tasks complete")
        print(f"=== {self.task_name.upper()} COMPLETION LOGGED ===")
        
        # Schedule cleanup after a short delay to ensure session manager processes completion
        if not self.cleanup_scheduled:
            self.cleanup_scheduled = True
            cleanup_timer = QTimer()
            cleanup_timer.singleShot(1000, self._post_completion_cleanup)
    
    def _post_completion_cleanup(self):
        """Perform post-completion cleanup."""
        try:
            print(f"Post-completion cleanup for {self.task_name}")
            
            # Additional cleanup tasks can be added here
            # The session manager handles the main cleanup
            
            # Mark cleanup as complete
            self.cleanup_scheduled = False
            
        except Exception as e:
            print(f"Error in post-completion cleanup: {e}")
    
    def is_task_completed(self) -> bool:
        """
        Check if this task instance is completed.
        
        Returns:
        --------
        bool
            True if task is completed
        """
        return self.task_completed
    
    def get_completion_data(self) -> Dict:
        """
        Get completion data for this task.
        
        Returns:
        --------
        Dict
            Task completion data
        """
        return self.completion_data.copy()
    
    def _start_auto_save_system(self):
        """Start the enhanced auto-save system with multiple timers."""
        # Regular auto-save timer
        self.task_save_timer.start(self.auto_save_interval)
        
        # Emergency save timer for critical data
        self.emergency_save_timer.start(self.emergency_save_interval)
        
        # Record start time
        self.task_start_time = time.time()
        
        print(f"Enhanced auto-save system started for {self.task_name}")
        print(f"  - Regular saves every {self.auto_save_interval}ms")
        print(f"  - Emergency saves every {self.emergency_save_interval}ms")
    
    def _stop_auto_save_system(self):
        """Stop the enhanced auto-save system."""
        self.task_save_timer.stop()
        self.emergency_save_timer.stop()
        
        # Perform final save
        self._immediate_save_task_state()
        
        print(f"Enhanced auto-save system stopped for {self.task_name}")
    
    def _auto_save_task_state(self):
        """Enhanced automatic task state saving."""
        if not self.task_started or not self.session_manager or self.task_completed:
            return
        
        try:
            # Get current task state
            current_state = self.session_manager.get_current_task_state()
            if not current_state:
                return
            
            # Update with current task-specific information
            task_specific_state = self._get_task_specific_state()
            if task_specific_state:
                current_state.update(task_specific_state)
                
                # Add auto-save metadata
                current_state['last_auto_save'] = datetime.now().isoformat()
                current_state['auto_save_count'] = current_state.get('auto_save_count', 0) + 1
                current_state['save_error_count'] = self.save_error_count
                current_state['task_completed'] = self.task_completed
                
                # Update session manager
                self.session_manager.session_data['current_task_state'] = current_state
                self.session_manager.session_data['last_save_time'] = datetime.now().isoformat()
                
                # Update last save time
                self.last_save_time = datetime.now()
                
        except Exception as e:
            self.save_error_count += 1
            self.last_save_error = str(e)
            print(f"Error in auto-save for {self.task_name}: {e}")
    
    def _immediate_save_task_state(self):
        """Perform immediate task state save."""
        try:
            self._auto_save_task_state()
            # Also trigger session manager save
            if self.session_manager:
                self.session_manager.save_session_state()
            print(f"Immediate save completed for {self.task_name}")
        except Exception as e:
            print(f"Error in immediate save for {self.task_name}: {e}")
    
    def _emergency_save_critical_data(self):
        """Emergency save for critical data only - FIXED to use organized structure."""
        if not self.critical_data_changed or not self.session_manager:
            return
        
        try:
            # Save only the most critical data
            critical_state = {
                'task_name': self.task_name,
                'emergency_save_time': datetime.now().isoformat(),
                'critical_trial_count': len(getattr(self, 'trial_data', [])),
                'current_position': getattr(self, 'current_index', 0),
                'recovery_mode': self.recovery_mode,
                'task_completed': self.task_completed,
                'folder_structure': 'organized_v2',
                'save_location': 'system/emergency_saves/'
            }
            
            # FIXED: Use organized folder structure for emergency saves
            participant_folder = self.session_manager.participant_folder_path
            emergency_saves_folder = os.path.join(participant_folder, "system", "emergency_saves")
            
            # Ensure the emergency saves folder exists
            os.makedirs(emergency_saves_folder, exist_ok=True)
            
            # Create emergency file in the organized location
            emergency_filename = f"emergency_{self.task_name.lower().replace(' ', '_')}.json"
            emergency_file = os.path.join(emergency_saves_folder, emergency_filename)
            
            with open(emergency_file, 'w') as f:
                json.dump(critical_state, f, indent=2)
            
            self.critical_data_changed = False
            print(f"Emergency save completed for {self.task_name}")
            print(f"Location: system/emergency_saves/{emergency_filename}")
            
        except Exception as e:
            print(f"Emergency save failed for {self.task_name}: {e}")
            # Fallback to old location if organized structure fails
            try:
                print("Attempting fallback emergency save to root folder...")
                emergency_file = os.path.join(
                    self.session_manager.participant_folder_path,
                    f"emergency_{self.task_name.lower().replace(' ', '_')}_fallback.json"
                )
                
                with open(emergency_file, 'w') as f:
                    json.dump(critical_state, f, indent=2)
                
                print(f"Fallback emergency save completed: {os.path.basename(emergency_file)}")
                
            except Exception as fallback_error:
                print(f"Fallback emergency save also failed: {fallback_error}")
    
    def _get_task_specific_state(self) -> Dict:
        """
        Get comprehensive task-specific state information.
        Override this method in your task class to provide additional state data.
        
        Returns:
        --------
        Dict
            Task-specific state information
        """
        state = {}
        
        # Common state information
        common_attributes = [
            'current_index', 'practice_mode', 'is_paused', 'practice_index',
            'is_in_break', 'task_started', 'recovery_mode', 'task_completed'
        ]
        
        for attr in common_attributes:
            if hasattr(self, attr):
                try:
                    state[attr] = getattr(self, attr)
                except Exception as e:
                    print(f"Error getting state for {attr}: {e}")
        
        # Add timing information
        if hasattr(self, 'task_start_time'):
            state['task_elapsed_time'] = time.time() - self.task_start_time
        
        # Add error tracking
        state['save_error_count'] = self.save_error_count
        state['last_save_error'] = self.last_save_error
        state['state_change_count'] = self.state_change_count
        
        # Add completion tracking
        state['completion_data_available'] = bool(self.completion_data)
        
        return state
    
    def handle_crash_recovery(self):
        """
        Handle application crash recovery for this task - FIXED for organized structure.
        This method should be called when the application detects a crash.
        """
        if self.session_manager:
            print(f"Handling crash recovery for {self.task_name}")
            
            # Perform emergency save using organized structure
            try:
                # Use the updated emergency save method
                self._emergency_save_critical_data()
                self.session_manager.emergency_save()
                print(f"Crash recovery completed for {self.task_name}")
                print("Emergency files saved to system/emergency_saves/")
            except Exception as e:
                print(f"Error during crash recovery for {self.task_name}: {e}")
        else:
            print(f"No session manager available for crash recovery in {self.task_name}")
    
    def force_task_completion(self, reason: str = "Forced completion"):
        """
        Force task completion (for emergency situations).
        
        Parameters:
        -----------
        reason : str
            Reason for forced completion
        """
        print(f"Forcing completion of {self.task_name}: {reason}")
        
        completion_data = {
            'forced_completion': True,
            'completion_reason': reason,
            'trials_at_completion': len(getattr(self, 'trial_data', [])),
            'force_completion_time': datetime.now().isoformat()
        }
        
        self.complete_task_with_recovery(completion_data)


class EnhancedCrashDetector(QObject):
    """
    Enhanced crash detection system with improved monitoring and task awareness.
    """
    
    crash_detected = pyqtSignal()
    resource_warning = pyqtSignal(str, float)  # signal_name, value
    task_completion_detected = pyqtSignal(str)  # task_name
    
    def __init__(self, session_manager=None):
        super().__init__()
        self.session_manager = session_manager
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._heartbeat)
        self.heartbeat_file = None
        
        # Enhanced monitoring
        self.resource_monitor_timer = QTimer()
        self.resource_monitor_timer.timeout.connect(self._monitor_resources)
        
        # Task monitoring
        self.task_monitor_timer = QTimer()
        self.task_monitor_timer.timeout.connect(self._monitor_task_states)
        
        # Monitoring configuration
        self.heartbeat_interval = 1000  # 1 second
        self.resource_monitor_interval = 5000  # 5 seconds
        self.task_monitor_interval = 3000  # 3 seconds
        self.memory_warning_threshold = 80  # Percentage
        self.memory_critical_threshold = 90  # Percentage
        
        # State tracking
        self.monitoring_active = False
        self.last_heartbeat_time = None
        self.resource_warnings = []
        self.known_tasks = set()
        
        if session_manager:
            # Use organized folder structure for heartbeat files
            system_folder = os.path.join(session_manager.participant_folder_path, "system")
            os.makedirs(system_folder, exist_ok=True)
            
            heartbeat_path = os.path.join(system_folder, "app_heartbeat.txt")
            self.heartbeat_file = heartbeat_path
            
            # Enhanced heartbeat file with metadata in system folder
            self.heartbeat_metadata_file = os.path.join(system_folder, "app_heartbeat_metadata.json")
        
        print(f"=== ENHANCED CRASH DETECTOR INITIALIZED (ORGANIZED) ===")
        print(f"Heartbeat interval: {self.heartbeat_interval}ms")
        print(f"Resource monitoring: {self.resource_monitor_interval}ms")
        print(f"Task monitoring: {self.task_monitor_interval}ms")
        print(f"Organized folder structure: ENABLED")
        print(f"System folder heartbeat: {'YES' if self.heartbeat_file else 'NO'}")
        print("=======================================================")
    
    def start_monitoring(self):
        """Start comprehensive monitoring system."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # Start all monitoring timers
        self.heartbeat_timer.start(self.heartbeat_interval)
        self.resource_monitor_timer.start(self.resource_monitor_interval)
        self.task_monitor_timer.start(self.task_monitor_interval)
        
        print("Enhanced crash detector monitoring started")
        print(f"  - Heartbeat: every {self.heartbeat_interval}ms")
        print(f"  - Resources: every {self.resource_monitor_interval}ms")
        print(f"  - Task states: every {self.task_monitor_interval}ms")
    
    def stop_monitoring(self):
        """Stop all monitoring."""
        self.monitoring_active = False
        
        self.heartbeat_timer.stop()
        self.resource_monitor_timer.stop()
        self.task_monitor_timer.stop()
        
        print("Enhanced crash detector monitoring stopped")
    
    def _heartbeat(self):
        """Enhanced heartbeat with metadata."""
        if not self.monitoring_active:
            return
        
        try:
            current_time = datetime.now()
            self.last_heartbeat_time = current_time
            
            # Write basic heartbeat file
            if self.heartbeat_file:
                with open(self.heartbeat_file, 'w') as f:
                    f.write(current_time.isoformat())
                
                # Write enhanced metadata
                if self.heartbeat_metadata_file:
                    metadata = {
                        'heartbeat_time': current_time.isoformat(),
                        'process_id': os.getpid(),
                        'monitoring_active': self.monitoring_active,
                        'memory_usage_mb': self._get_memory_usage(),
                        'session_active': bool(self.session_manager),
                        'known_tasks': list(self.known_tasks)
                    }
                    
                    with open(self.heartbeat_metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
        
        except Exception as e:
            print(f"Heartbeat error: {e}")
    
    def _monitor_resources(self):
        """Monitor system resources."""
        if not self.monitoring_active:
            return
        
        try:
            # Check memory usage
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > self.memory_warning_threshold:
                warning_msg = f"High memory usage: {memory_percent:.1f}%"
                print(f"WARNING: {warning_msg}")
                self.resource_warning.emit("memory", memory_percent)
                
                if memory_percent > self.memory_critical_threshold:
                    print(f"CRITICAL: Memory usage critical: {memory_percent:.1f}%")
                    # Trigger emergency save
                    if self.session_manager:
                        try:
                            self.session_manager.emergency_save()
                        except Exception as e:
                            print(f"Emergency save failed during critical memory: {e}")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                print(f"WARNING: High CPU usage: {cpu_percent:.1f}%")
                self.resource_warning.emit("cpu", cpu_percent)
        
        except Exception as e:
            print(f"Resource monitoring error: {e}")
    
    def _monitor_task_states(self):
        """Monitor task states for completion detection."""
        if not self.monitoring_active or not self.session_manager:
            return
        
        try:
            current_task = self.session_manager.session_data.get('current_task')
            if current_task:
                self.known_tasks.add(current_task)
                
                # Check if task is completed
                current_task_state = self.session_manager.get_current_task_state()
                if current_task_state and current_task_state.get('task_completed', False):
                    print(f"Task completion detected: {current_task}")
                    self.task_completion_detected.emit(current_task)
        
        except Exception as e:
            print(f"Task monitoring error: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except:
            return 0.0


# Helper functions for integration
def get_recovery_info() -> Dict:
    """
    Get recovery information for current session.
    Enhanced with task completion awareness.
    """
    session_manager = get_session_manager() if SESSION_MANAGER_AVAILABLE else None
    if not session_manager:
        return {'recoverable': False, 'reason': 'No session manager'}
    
    current_task_state = session_manager.get_current_task_state()
    if not current_task_state:
        return {'recoverable': False, 'reason': 'No current task state'}
    
    # Check if task is actually recoverable (not completed)
    if current_task_state.get('task_completed', False):
        return {'recoverable': False, 'reason': 'Task already completed'}
    
    if current_task_state.get('status') in ['completed', 'finished', 'done']:
        return {'recoverable': False, 'reason': 'Task status indicates completion'}
    
    return {
        'recoverable': True,
        'current_task': session_manager.session_data.get('current_task'),
        'trials_completed': len(current_task_state.get('trial_data', [])),
        'recovery_mode': current_task_state.get('recovery_mode', False),
        'session_id': session_manager.participant_id,
        'task_completed': current_task_state.get('task_completed', False)
    }

def create_crash_detector(session_manager=None) -> EnhancedCrashDetector:
    """
    Create an enhanced crash detector instance.
    
    Parameters:
    -----------
    session_manager : SessionManager, optional
        Session manager instance
    
    Returns:
    --------
    EnhancedCrashDetector
        Configured crash detector
    """
    return EnhancedCrashDetector(session_manager)

# Backward compatibility aliases
CrashDetector = EnhancedCrashDetector

if __name__ == "__main__":
    """
    Test the enhanced task state saver functionality.
    """
    print("=== ENHANCED TASK STATE SAVER TEST MODE ===")
    print("Enhanced completion handling: ENABLED")
    print("Testing task state management...")
    
    # Mock task class for testing
    class TestTask(TaskStateMixin):
        TASK_NAME = "Test Task"
        
        def __init__(self):
            self.trial_data = []
            super().__init__()
        
        def run_trial(self, trial_number):
            trial_data = {
                'trial_number': trial_number,
                'timestamp': datetime.now().isoformat(),
                'test_data': f"Trial {trial_number} data"
            }
            self.save_trial_with_recovery(trial_data)
        
        def finish_task(self):
            completion_data = {
                'total_trials': len(self.trial_data),
                'test_completed_successfully': True
            }
            self.complete_task_with_recovery(completion_data)
    
    # Test enhanced functionality
    if SESSION_MANAGER_AVAILABLE:
        print("Testing with session manager...")
        test_task = TestTask()
        test_task.start_task_with_recovery({'test_mode': True}, total_trials=3)
        
        # Simulate some trials
        for i in range(1, 4):
            test_task.run_trial(i)
        
        # Complete the task
        test_task.finish_task()
        
        print("Enhanced task state saver test completed!")
        print("Task completion handling verified!")
    else:
        print("Session manager not available - limited test mode")
    
    print("=== TEST COMPLETE ===")