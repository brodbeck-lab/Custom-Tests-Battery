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
Version: 2.0 (Enhanced Crash Recovery)
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
    from experiment_data_saver import emergency_save_all_tasks
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
        
        Parameters:
        -----------
        crash_reason : str
            Reason for the emergency save
        
        Returns:
        --------
        bool
            True if emergency save was successful
        """
        print(f"PERFORMING EMERGENCY SAVE - Reason: {crash_reason}")
        
        try:
            # Set timeout for emergency save
            emergency_save_success = False
            
            if RECOVERY_SYSTEM_AVAILABLE:
                session_manager = get_session_manager()
                if session_manager:
                    print("Session manager found - performing comprehensive emergency save")
                    
                    # Mark as crash in session data
                    session_manager.session_data['crash_detected'] = True
                    session_manager.session_data['crash_reason'] = crash_reason
                    session_manager.session_data['crash_time'] = datetime.now().isoformat()
                    
                    # Perform emergency save
                    session_manager.emergency_save()
                    
                    # Save all task data
                    emergency_save_success = emergency_save_all_tasks(session_manager)
                    
                    print("Comprehensive emergency save completed")
                else:
                    print("No active session manager - limited emergency save")
                    emergency_save_success = True  # No data to save
            else:
                print("Recovery system not available - basic emergency save")
                emergency_save_success = self._basic_emergency_save(crash_reason)
            
            return emergency_save_success
            
        except Exception as e:
            print(f"CRITICAL: Emergency save failed: {e}")
            return False
    
    def _basic_emergency_save(self, crash_reason):
        """
        Basic emergency save when recovery system is not available.
        
        Parameters:
        -----------
        crash_reason : str
            Reason for the emergency save
        
        Returns:
        --------
        bool
            True if basic emergency save was successful
        """
        try:
            # Create emergency save in Documents folder
            documents_path = os.path.expanduser("~/Documents")
            emergency_folder = os.path.join(documents_path, "Custom Tests Battery Data", "EMERGENCY_SAVES")
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
                f.write(f"Recovery system: NOT AVAILABLE\n")
                f.write("\nThis is a basic emergency save created when the full recovery system was not available.\n")
                f.write("Data may be limited. Check for session files in participant folders.\n")
            
            print(f"Basic emergency save created: {emergency_file}")
            return True
            
        except Exception as e:
            print(f"Basic emergency save failed: {e}")
            return False
    
    def _generate_crash_report(self, crash_info):
        """
        Generate detailed crash report for debugging and analysis.
        
        Parameters:
        -----------
        crash_info : dict
            Crash information dictionary
        
        Returns:
        --------
        bool
            True if crash report was generated successfully
        """
        try:
            # Determine crash report location
            crash_report_folder = self._get_crash_report_folder()
            
            if not crash_report_folder:
                print("Could not determine crash report folder")
                return False
            
            # Create crash report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            crash_report_file = os.path.join(crash_report_folder, f"crash_report_{timestamp}.json")
            
            # Add additional debugging information
            crash_info['crash_report_file'] = crash_report_file
            crash_info['crash_report_generation_time'] = datetime.now().isoformat()
            
            # Write comprehensive crash report
            with open(crash_report_file, 'w', encoding='utf-8') as f:
                json.dump(crash_info, f, indent=2, default=str)
            
            # Also create human-readable version
            readable_report_file = crash_report_file.replace('.json', '.txt')
            with open(readable_report_file, 'w', encoding='utf-8') as f:
                f.write("CUSTOM TESTS BATTERY - CRASH REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("CRASH SUMMARY:\n")
                f.write("-" * 15 + "\n")
                f.write(f"Time: {crash_info['timestamp']}\n")
                f.write(f"Exception: {crash_info['exception_type']}\n")
                f.write(f"Message: {crash_info['exception_message']}\n")
                f.write(f"Process ID: {crash_info['process_id']}\n")
                f.write(f"Crash Count: {crash_info['crash_count']}\n\n")
                
                f.write("SYSTEM INFORMATION:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Platform: {crash_info.get('platform', 'Unknown')}\n")
                f.write(f"Python Version: {crash_info.get('python_version', 'Unknown')}\n")
                f.write(f"Memory Usage: {crash_info.get('memory_usage', 'Unknown')} MB\n")
                f.write(f"CPU Usage: {crash_info.get('cpu_percent', 'Unknown')}%\n")
                f.write(f"Working Directory: {crash_info.get('working_directory', 'Unknown')}\n\n")
                
                if 'participant_id' in crash_info:
                    f.write("SESSION INFORMATION:\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Participant: {crash_info['participant_id']}\n")
                    f.write(f"Current Task: {crash_info.get('current_task', 'None')}\n")
                    f.write(f"Trials Completed: {crash_info.get('trials_completed', 0)}\n")
                    f.write(f"Session Start: {crash_info.get('session_start_time', 'Unknown')}\n\n")
                
                f.write("STACK TRACE:\n")
                f.write("-" * 12 + "\n")
                f.write(crash_info.get('traceback', 'No traceback available'))
                f.write("\n\nEnd of Crash Report\n")
            
            print(f"Crash report generated:")
            print(f"  - JSON format: {os.path.basename(crash_report_file)}")
            print(f"  - Text format: {os.path.basename(readable_report_file)}")
            
            return True
            
        except Exception as e:
            print(f"Failed to generate crash report: {e}")
            return False
    
    def _get_crash_report_folder(self):
        """Get the appropriate folder for crash reports."""
        try:
            # Try to use participant folder if available
            if RECOVERY_SYSTEM_AVAILABLE:
                session_manager = get_session_manager()
                if session_manager and hasattr(session_manager, 'participant_folder_path'):
                    crash_folder = os.path.join(session_manager.participant_folder_path, "crash_reports")
                    os.makedirs(crash_folder, exist_ok=True)
                    return crash_folder
            
            # Fallback to Documents folder
            documents_path = os.path.expanduser("~/Documents")
            crash_folder = os.path.join(documents_path, "Custom Tests Battery Data", "crash_reports")
            os.makedirs(crash_folder, exist_ok=True)
            return crash_folder
            
        except Exception as e:
            print(f"Error creating crash report folder: {e}")
            return None
    
    def _last_resort_save(self, crash_info):
        """Last resort save when all other mechanisms fail."""
        try:
            # Try to save to current directory as last resort
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            last_resort_file = f"LAST_RESORT_CRASH_SAVE_{timestamp}.txt"
            
            with open(last_resort_file, 'w', encoding='utf-8') as f:
                f.write("LAST RESORT CRASH SAVE\n")
                f.write("=" * 25 + "\n\n")
                f.write(f"All crash recovery mechanisms failed.\n")
                f.write(f"This is a minimal save attempt.\n\n")
                f.write(f"Crash time: {crash_info['timestamp']}\n")
                f.write(f"Exception: {crash_info['exception_type']}\n")
                f.write(f"Message: {crash_info['exception_message']}\n")
                f.write(f"Process ID: {crash_info['process_id']}\n")
            
            print(f"Last resort save created: {last_resort_file}")
            
        except Exception as e:
            print(f"CRITICAL: Last resort save failed: {e}")
    
    def _notify_crash_callbacks(self, crash_info):
        """Notify registered crash callbacks."""
        for callback in self.crash_callbacks:
            try:
                callback(crash_info)
            except Exception as e:
                print(f"Crash callback failed: {e}")
    
    def _cleanup_resources(self):
        """Clean up application resources."""
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
        if not self.crash_detected:
            print("Application exiting normally - performing cleanup")
            self.stop_monitoring()
            
            # Normal shutdown - no emergency save needed
            if RECOVERY_SYSTEM_AVAILABLE:
                session_manager = get_session_manager()
                if session_manager:
                    session_manager._cleanup_session()
    
    def start_monitoring(self):
        """Start resource monitoring in background thread."""
        if not self.enable_monitoring or self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        print("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2.0)
        print("Resource monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop running in background thread."""
        while self.monitoring_active:
            try:
                # Check memory usage
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > self.memory_threshold:
                    print(f"WARNING: High memory usage detected: {memory_percent:.1f}%")
                
                # Check CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > self.cpu_threshold:
                    print(f"WARNING: High CPU usage detected: {cpu_percent:.1f}%")
                
                # Sleep before next check
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                break
    
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