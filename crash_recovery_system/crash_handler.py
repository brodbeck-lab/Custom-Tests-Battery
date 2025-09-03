"""
CRASH HANDLER - GLOBAL CRASH DETECTION AND EMERGENCY SAVE
Custom Tests Battery - Universal Crash Recovery System

This module provides comprehensive crash detection, emergency saving, and error handling
for the entire Custom Tests Battery application. It monitors for various types of 
crashes and system failures, automatically saving critical data before termination.

Features:
- Global exception handling and crash detection
- Automatic emergency saves for all tasks
- System signal handling (SIGINT, SIGTERM, etc.)
- Memory and resource monitoring
- Crash report generation
- Recovery preparation for next session
- Multiple crash scenario handling
- Graceful degradation mechanisms

Author: Custom Tests Battery Development Team
Version: 2.0 (Enhanced Crash Recovery - Updated for Modular Data Savers)
"""

import sys
import os
import signal
import traceback
import threading
import time
import psutil
import json
import atexit
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

# Import crash recovery system components
try:
    from crash_recovery_system.session_manager import get_session_manager, cleanup_session_manager
    # Import task-specific emergency save functions from the new data_saver modules
    from task_cvc.data_saver import emergency_save_cvc_task
    from task_stroop_colorword.data_saver import emergency_save_stroop_task
    from task_speeded_classification.data_saver import emergency_save_speeded_classification_task
    # TODO: Add other task emergency save imports as you create more data_saver.py files:
    # from letter_monitoring_task.data_saver import emergency_save_letter_monitoring_task
    # from visual_search_task.data_saver import emergency_save_visual_search_task
    # from attention_network_task.data_saver import emergency_save_attention_network_task
    # from gonogo_task.data_saver import emergency_save_gonogo_task
    # from reading_span_task.data_saver import emergency_save_reading_span_task
    RECOVERY_SYSTEM_AVAILABLE = True
except ImportError:
    RECOVERY_SYSTEM_AVAILABLE = False
    print("WARNING: Crash recovery system components not fully available")

class CrashHandler:
    """
    Global crash handler for the Custom Tests Battery application.
    Provides comprehensive crash detection and emergency save capabilities.
    """
    
    def __init__(self, enable_monitoring=True):
        """
        Initialize the crash handler with comprehensive monitoring.
        
        Parameters:
        -----------
        enable_monitoring : bool, optional
            Whether to enable resource monitoring (default: True)
        """
        self.enable_monitoring = enable_monitoring
        self.original_excepthook = sys.excepthook
        self.crash_callbacks = []
        self.monitoring_active = False
        self.monitoring_thread = None
        self.crash_detected = False
        
        # Crash statistics
        self.crash_count = 0
        self.last_crash_time = None
        self.crash_history = []
        
        # Resource monitoring
        self.memory_threshold = 90  # Percentage
        self.cpu_threshold = 95     # Percentage
        self.monitoring_interval = 5.0  # Seconds
        
        # Emergency save configuration
        self.emergency_save_enabled = True
        self.max_emergency_save_time = 30  # Seconds
        
        print("=== CRASH HANDLER INITIALIZATION ===")
        print(f"Recovery system: {'AVAILABLE' if RECOVERY_SYSTEM_AVAILABLE else 'LIMITED'}")
        print(f"Resource monitoring: {'ENABLED' if enable_monitoring else 'DISABLED'}")
        print(f"Emergency save: {'ENABLED' if self.emergency_save_enabled else 'DISABLED'}")
        print(f"Process ID: {os.getpid()}")
        print("=====================================")
        
        # Set up crash detection
        self._setup_crash_detection()
        
        # Start resource monitoring if enabled
        if enable_monitoring:
            self.start_monitoring()
    
    def _setup_crash_detection(self):
        """Set up comprehensive crash detection mechanisms."""
        try:
            # Replace system exception hook
            sys.excepthook = self.handle_exception
            
            # Register cleanup function
            atexit.register(self._cleanup_on_exit)
            
            # Set up signal handlers for different termination signals
            self._setup_signal_handlers()
            
            print("Crash detection mechanisms activated")
            
        except Exception as e:
            print(f"Warning: Could not set up all crash detection mechanisms: {e}")
    
    def _setup_signal_handlers(self):
        """Set up handlers for various system signals."""
        signals_to_handle = []
        
        # Add available signals based on platform
        if hasattr(signal, 'SIGINT'):
            signals_to_handle.append(('SIGINT', signal.SIGINT))
        if hasattr(signal, 'SIGTERM'):
            signals_to_handle.append(('SIGTERM', signal.SIGTERM))
        if hasattr(signal, 'SIGABRT'):
            signals_to_handle.append(('SIGABRT', signal.SIGABRT))
        
        # Windows-specific signals
        if sys.platform == 'win32':
            if hasattr(signal, 'SIGBREAK'):
                signals_to_handle.append(('SIGBREAK', signal.SIGBREAK))
        
        # Unix-specific signals
        else:
            if hasattr(signal, 'SIGHUP'):
                signals_to_handle.append(('SIGHUP', signal.SIGHUP))
            if hasattr(signal, 'SIGQUIT'):
                signals_to_handle.append(('SIGQUIT', signal.SIGQUIT))
        
        # Register signal handlers
        for signal_name, signal_num in signals_to_handle:
            try:
                signal.signal(signal_num, self._signal_handler)
                print(f"Signal handler registered: {signal_name}")
            except (OSError, ValueError) as e:
                print(f"Could not register {signal_name} handler: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals that indicate forced termination."""
        signal_name = self._get_signal_name(signum)
        
        print(f"\n{'='*50}")
        print(f"SIGNAL RECEIVED: {signal_name} ({signum})")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Process ID: {os.getpid()}")
        print(f"{'='*50}")
        
        # Perform emergency save
        self._perform_emergency_save(f"Signal {signal_name}")
        
        # Clean up resources
        self._cleanup_resources()
        
        print(f"Signal {signal_name} handling completed")
        
        # Exit gracefully
        sys.exit(0)
    
    def _get_signal_name(self, signum):
        """Get human-readable signal name."""
        signal_names = {
            getattr(signal, 'SIGINT', None): 'SIGINT (Interrupt)',
            getattr(signal, 'SIGTERM', None): 'SIGTERM (Terminate)',
            getattr(signal, 'SIGABRT', None): 'SIGABRT (Abort)',
            getattr(signal, 'SIGHUP', None): 'SIGHUP (Hangup)',
            getattr(signal, 'SIGQUIT', None): 'SIGQUIT (Quit)',
            getattr(signal, 'SIGBREAK', None): 'SIGBREAK (Break)',
        }
        return signal_names.get(signum, f'Unknown Signal ({signum})')
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions with comprehensive crash recovery.
        
        Parameters:
        -----------
        exc_type : type
            The exception type
        exc_value : Exception
            The exception instance
        exc_traceback : traceback
            The traceback object
        """
        if self.crash_detected:
            # Prevent infinite recursion if crash handler itself crashes
            print("CRITICAL: Crash handler recursion detected - forcing exit")
            self.original_excepthook(exc_type, exc_value, exc_traceback)
            os._exit(1)
        
        self.crash_detected = True
        self.crash_count += 1
        self.last_crash_time = datetime.now()
        
        # Create crash information
        crash_info = self._create_crash_info(exc_type, exc_value, exc_traceback)
        
        print(f"\n{'='*60}")
        print("APPLICATION CRASH DETECTED")
        print(f"{'='*60}")
        print(f"Exception Type: {crash_info['exception_type']}")
        print(f"Exception Message: {crash_info['exception_message']}")
        print(f"Crash Time: {crash_info['timestamp']}")
        print(f"Process ID: {crash_info['process_id']}")
        print(f"Crash Count: {self.crash_count}")
        print(f"{'='*60}")
        
        # Add to crash history
        self.crash_history.append(crash_info)
        
        try:
            # Perform emergency save
            emergency_save_success = self._perform_emergency_save("Application Exception")
            
            # Generate crash report
            crash_report_success = self._generate_crash_report(crash_info)
            
            # Notify crash callbacks
            self._notify_crash_callbacks(crash_info)
            
            # Clean up resources
            self._cleanup_resources()
            
            print(f"Crash handling completed:")
            print(f"  - Emergency save: {'SUCCESS' if emergency_save_success else 'FAILED'}")
            print(f"  - Crash report: {'SUCCESS' if crash_report_success else 'FAILED'}")
            print(f"  - Resource cleanup: COMPLETED")
            
        except Exception as cleanup_error:
            print(f"CRITICAL: Error during crash cleanup: {cleanup_error}")
            # Try to at least save basic information
            self._last_resort_save(crash_info)
        
        print(f"{'='*60}")
        
        # Call original exception handler for final processing
        self.original_excepthook(exc_type, exc_value, exc_traceback)
    
    def _create_crash_info(self, exc_type, exc_value, exc_traceback):
        """Create comprehensive crash information dictionary."""
        crash_info = {
            'timestamp': datetime.now().isoformat(),
            'exception_type': exc_type.__name__ if exc_type else 'Unknown',
            'exception_message': str(exc_value) if exc_value else 'No message',
            'traceback': ''.join(traceback.format_tb(exc_traceback)) if exc_traceback else 'No traceback',
            'process_id': os.getpid(),
            'crash_count': self.crash_count,
            'application': 'Custom Tests Battery',
            'version': '2.0'
        }
        
        # Add system information
        try:
            crash_info.update({
                'python_version': sys.version,
                'platform': sys.platform,
                'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024,  # MB
                'cpu_percent': psutil.Process().cpu_percent(),
                'working_directory': os.getcwd(),
                'command_line': ' '.join(sys.argv)
            })
        except Exception as e:
            crash_info['system_info_error'] = str(e)
        
        # Add session information if available
        if RECOVERY_SYSTEM_AVAILABLE:
            try:
                session_manager = get_session_manager()
                if session_manager:
                    crash_info.update({
                        'participant_id': session_manager.session_data.get('participant_id', 'Unknown'),
                        'current_task': session_manager.session_data.get('current_task', 'None'),
                        'session_start_time': session_manager.session_data.get('session_start_time', 'Unknown'),
                        'trials_completed': len(session_manager.session_data.get('current_task_state', {}).get('trial_data', []))
                    })
            except Exception as e:
                crash_info['session_info_error'] = str(e)
        
        return crash_info
    
    def _perform_emergency_save(self, crash_reason):
        """
        Perform emergency save of all critical data.
        Updated to use task-specific data savers.
        """
        if not self.emergency_save_enabled:
            print("Emergency save disabled - skipping")
            return False
        
        print(f"=== PERFORMING EMERGENCY SAVE ===")
        print(f"Reason: {crash_reason}")
        print(f"Max save time: {self.max_emergency_save_time} seconds")
        
        emergency_save_success = False
        
        # Set timeout for emergency save
        save_start_time = time.time()
        
        try:
            if RECOVERY_SYSTEM_AVAILABLE:
                # Use the modular emergency save system
                session_manager = get_session_manager()
                if session_manager:
                    emergency_save_success = emergency_save_all_tasks(session_manager)
                else:
                    print("No session manager available - creating basic emergency save")
                    emergency_save_success = self._basic_emergency_save(crash_reason)
            else:
                print("Recovery system not available - creating basic emergency save")
                emergency_save_success = self._basic_emergency_save(crash_reason)
            
            save_duration = time.time() - save_start_time
            print(f"Emergency save completed in {save_duration:.2f} seconds")
            
        except Exception as e:
            save_duration = time.time() - save_start_time
            print(f"Emergency save failed after {save_duration:.2f} seconds: {e}")
            
            # Last resort save
            try:
                emergency_save_success = self._basic_emergency_save(crash_reason)
            except Exception as final_error:
                print(f"Final emergency save attempt failed: {final_error}")
        
        return emergency_save_success
    
    def _basic_emergency_save(self, crash_reason):
        """
        Create basic emergency save when full recovery system is not available.
        Fixed to use participant-specific system folder.
        """
        try:
            # Get session manager to find participant folder
            session_manager = get_session_manager() if SESSION_MANAGER_AVAILABLE else None
            
            if session_manager and hasattr(session_manager, 'participant_folder_path'):
                # Use participant-specific system folder
                participant_folder = session_manager.participant_folder_path
                emergency_folder = os.path.join(participant_folder, "system", "emergency_saves")
                participant_id = session_manager.participant_id
            else:
                # Fallback: try to determine participant from current working directory or use generic
                documents_path = os.path.expanduser("~/Documents")
                app_data_path = os.path.join(documents_path, "Custom Tests Battery Data")
                
                # Create a generic emergency participant folder if no session manager
                participant_id = f"EMERGENCY_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                participant_folder = os.path.join(app_data_path, participant_id)
                emergency_folder = os.path.join(participant_folder, "system", "emergency_saves")
            
            # Ensure the emergency folder exists
            os.makedirs(emergency_folder, exist_ok=True)
            
            # Create basic emergency save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            emergency_file = os.path.join(emergency_folder, f"BASIC_EMERGENCY_SAVE_{timestamp}.txt")
            
            with open(emergency_file, 'w', encoding='utf-8') as f:
                f.write("BASIC EMERGENCY SAVE - CUSTOM TESTS BATTERY\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Emergency save time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Crash reason: {crash_reason}\n")
                f.write(f"Process ID: {os.getpid()}\n")
                f.write(f"Participant ID: {participant_id}\n")
                f.write(f"Recovery system: {'AVAILABLE' if SESSION_MANAGER_AVAILABLE else 'NOT AVAILABLE'}\n")
                f.write(f"Folder structure: ORGANIZED (participant/system/emergency_saves/)\n")
                f.write("\nThis emergency save is participant-specific and stored in the correct location.\n")
            
            print(f"Basic emergency save created for participant {participant_id}: {emergency_file}")
            return True
            
        except Exception as e:
            print(f"Basic emergency save failed: {e}")
            return False
    
    def _generate_crash_report(self, crash_info):
        """
        Generate detailed crash report for debugging and analysis.
        Updated to use organized folder structure.
        """
        try:
            # Create crash reports folder in organized structure
            documents_path = os.path.expanduser("~/Documents")
            crash_reports_folder = os.path.join(documents_path, "Custom Tests Battery Data", "system", "crash_reports")
            os.makedirs(crash_reports_folder, exist_ok=True)
            
            # Generate crash report file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(crash_reports_folder, f"CRASH_REPORT_{timestamp}.json")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(crash_info, f, indent=2, default=str)
            
            print(f"Crash report generated: system/crash_reports/{os.path.basename(report_file)}")
            return True
            
        except Exception as e:
            print(f"Could not generate crash report: {e}")
            return False
    
    def _notify_crash_callbacks(self, crash_info):
        """Notify all registered crash callbacks."""
        for callback in self.crash_callbacks:
            try:
                callback(crash_info)
            except Exception as e:
                print(f"Error in crash callback {callback.__name__}: {e}")
    
    def _cleanup_resources(self):
        """Clean up system resources and session managers."""
        try:
            # Stop monitoring
            self.stop_monitoring()
            
            # Clean up session manager
            if RECOVERY_SYSTEM_AVAILABLE:
                cleanup_session_manager()
            
            print("Resource cleanup completed")
            
        except Exception as e:
            print(f"Error during resource cleanup: {e}")
    
    def _cleanup_on_exit(self):
        """Cleanup function called on normal exit."""
        if self.monitoring_active:
            self.stop_monitoring()
    
    def _last_resort_save(self, crash_info):
        """Absolute last resort save when everything else fails."""
        try:
            # Try to save to current directory as last resort
            emergency_file = f"LAST_RESORT_SAVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(emergency_file, 'w', encoding='utf-8') as f:
                f.write("LAST RESORT EMERGENCY SAVE\n")
                f.write("=" * 30 + "\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"Exception: {crash_info.get('exception_type', 'Unknown')}\n")
                f.write(f"Message: {crash_info.get('exception_message', 'Unknown')}\n")
                f.write(f"PID: {crash_info.get('process_id', 'Unknown')}\n")
            
            print(f"Last resort save created: {emergency_file}")
            
        except:
            print("CRITICAL: All save mechanisms failed")
    
    def start_monitoring(self):
        """Start resource monitoring in background thread."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitoring_thread.start()
        print("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        if self.monitoring_active:
            self.monitoring_active = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2)
            print("Resource monitoring stopped")
    
    def _monitor_resources(self):
        """Monitor system resources for potential issues."""
        while self.monitoring_active:
            try:
                # Monitor memory usage
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > self.memory_threshold:
                    print(f"WARNING: High memory usage detected: {memory_percent:.1f}%")
                
                # Monitor CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > self.cpu_threshold:
                    print(f"WARNING: High CPU usage detected: {cpu_percent:.1f}%")
                
                # Monitor process-specific resources
                try:
                    process = psutil.Process()
                    process_memory = process.memory_info().rss / 1024 / 1024  # MB
                    if process_memory > 1000:  # 1GB threshold
                        print(f"WARNING: Application memory usage: {process_memory:.1f} MB")
                except:
                    pass
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                print(f"Error in resource monitoring: {e}")
                time.sleep(self.monitoring_interval)
    
    def register_crash_callback(self, callback: Callable):
        """
        Register a callback function to be called when a crash occurs.
        
        Parameters:
        -----------
        callback : Callable
            Function to call with crash_info as parameter
        """
        self.crash_callbacks.append(callback)
        print(f"Crash callback registered: {callback.__name__}")
    
    def test_crash_handler(self):
        """Test the crash handler by raising a test exception."""
        print("Testing crash handler...")
        raise Exception("This is a test crash to verify the crash handler works correctly")
    
    def get_crash_statistics(self):
        """Get crash statistics and history."""
        return {
            'crash_count': self.crash_count,
            'last_crash_time': self.last_crash_time.isoformat() if self.last_crash_time else None,
            'crash_history': self.crash_history,
            'monitoring_active': self.monitoring_active,
            'recovery_system_available': RECOVERY_SYSTEM_AVAILABLE
        }


# =============================================================================
# EMERGENCY SAVE FUNCTIONS (MOVED FROM experiment_data_saver.py)
# =============================================================================

def emergency_save_all_tasks(session_manager):
    """
    Emergency save function for all active tasks.
    Called during application crashes or critical errors.
    
    MOVED FROM: experiment_data_saver.py
    UPDATED TO: Use task-specific data_saver modules
    
    Parameters:
    -----------
    session_manager : SessionManager
        The session manager instance
    
    Returns:
    --------
    bool
        True if emergency save was successful
    """
    if not session_manager:
        print("No session manager available for emergency save")
        return False
    
    try:
        print("=== EMERGENCY SAVE FOR ALL TASKS ===")
        
        current_task = session_manager.session_data.get('current_task')
        current_task_state = session_manager.session_data.get('current_task_state', {})
        
        if current_task and current_task_state:
            trial_data = current_task_state.get('trial_data', [])
            
            if current_task == "Stroop Colour-Word Task":
                return emergency_save_stroop_task(session_manager, trial_data)
            elif current_task == "CVC Task":
                return emergency_save_cvc_task(session_manager, trial_data)
            elif current_task == "Letter Monitoring Task":
                # TODO: Create letter_monitoring_task/data_saver.py and import emergency_save_letter_monitoring_task
                return emergency_save_generic_task(session_manager, current_task, trial_data)
            elif current_task == "Speeded Classification Task":
                return emergency_save_speeded_classification_task(session_manager, trial_data)

            elif current_task == "Visual Search Task":
                # TODO: Create visual_search_task/data_saver.py and import emergency_save_visual_search_task
                return emergency_save_generic_task(session_manager, current_task, trial_data)
            elif current_task == "Attention Network Task":
                # TODO: Create attention_network_task/data_saver.py and import emergency_save_attention_network_task
                return emergency_save_generic_task(session_manager, current_task, trial_data)
            elif current_task == "Go/No-Go Task":
                # TODO: Create gonogo_task/data_saver.py and import emergency_save_gonogo_task
                return emergency_save_generic_task(session_manager, current_task, trial_data)
            elif current_task == "Reading Span Test":
                # TODO: Create reading_span_task/data_saver.py and import emergency_save_reading_span_task
                return emergency_save_generic_task(session_manager, current_task, trial_data)
            else:
                return emergency_save_generic_task(session_manager, current_task, trial_data)
        
        print("No active task found for emergency save")
        return True
        
    except Exception as e:
        print(f"Critical error during emergency save: {e}")
        return False


def emergency_save_generic_task(session_manager, task_name, trial_data):
    """
    Generic emergency save for tasks that don't have specific data_saver modules yet.
    
    MOVED FROM: experiment_data_saver.py
    
    Parameters:
    -----------
    session_manager : SessionManager
        The session manager instance
    task_name : str
        Name of the task
    trial_data : list
        Trial data to save
        
    Returns:
    --------
    bool
        True if emergency save was successful
    """
    try:
        participant_id = session_manager.session_data.get('participant_id', 'EMERGENCY_PARTICIPANT')
        participant_folder = getattr(session_manager, 'participant_folder_path', None)
        
        if not participant_folder:
            # Create emergency folder with organized structure
            documents_path = os.path.expanduser("~/Documents")
            participant_folder = os.path.join(documents_path, "Custom Tests Battery Data", participant_id)
            os.makedirs(participant_folder, exist_ok=True)
        
        # Use organized system/emergency_saves folder
        emergency_folder = os.path.join(participant_folder, "system", "emergency_saves")
        os.makedirs(emergency_folder, exist_ok=True)
        
        # Generic emergency save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        emergency_file = os.path.join(emergency_folder, f"EMERGENCY_{task_name.replace(' ', '_')}_{timestamp}.json")
        
        emergency_data = {
            'task_name': task_name,
            'participant_id': participant_id,
            'emergency_save_time': datetime.now().isoformat(),
            'trial_data': trial_data,
            'session_data': session_manager.session_data,
            'folder_structure': 'organized_v2',
            'save_location': 'system/emergency_saves/'
        }
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            json.dump(emergency_data, f, indent=2, default=str)
        
        print(f"Generic emergency save completed in organized structure: system/emergency_saves/{os.path.basename(emergency_file)}")
        return True
        
    except Exception as e:
        print(f"Generic emergency save failed: {e}")
        return False


# =============================================================================
# GLOBAL CRASH HANDLER MANAGEMENT
# =============================================================================

# Global crash handler instance
_crash_handler = None

def initialize_crash_handler(enable_monitoring=True):
    """
    Initialize the global crash handler.
    
    Parameters:
    -----------
    enable_monitoring : bool, optional
        Whether to enable resource monitoring (default: True)
    
    Returns:
    --------
    CrashHandler
        The initialized crash handler instance
    """
    global _crash_handler
    if _crash_handler is None:
        _crash_handler = CrashHandler(enable_monitoring=enable_monitoring)
        print("Global crash handler initialized")
    return _crash_handler

def get_crash_handler():
    """Get the global crash handler instance."""
    return _crash_handler

def cleanup_crash_handler():
    """Clean up the global crash handler."""
    global _crash_handler
    if _crash_handler:
        _crash_handler.stop_monitoring()
        _crash_handler = None
        print("Global crash handler cleaned up")

# Auto-initialize crash handler when module is imported
_crash_handler = initialize_crash_handler()

if __name__ == "__main__":
    """
    Test the crash handler functionality.
    """
    print("=== CRASH HANDLER TEST MODE ===")
    print("Testing crash detection and recovery...")
    
    # Initialize crash handler
    crash_handler = initialize_crash_handler(enable_monitoring=True)
    
    # Register test callback
    def test_callback(crash_info):
        print(f"Test callback received crash: {crash_info['exception_type']}")
    
    crash_handler.register_crash_callback(test_callback)
    
    # Display crash statistics
    stats = crash_handler.get_crash_statistics()
    print(f"Initial crash statistics: {stats}")
    
    # Test crash handler (uncomment to actually test)
    # print("Triggering test crash in 3 seconds...")
    # time.sleep(3)
    # crash_handler.test_crash_handler()
    
    print("Crash handler test completed!")
    print("(Uncomment test_crash_handler() call to actually test crash detection)")