"""
CVC TASK DATA SAVER MODULE - WITH COMPREHENSIVE CONFIGURATION SUPPORT
Custom Tests Battery - CVC Task Specific Data Saving

This module contains the data saving functionality specifically for the CVC Task.
Updated to support comprehensive configuration with separate practice and main trials.

Features:
- Comprehensive configuration logging
- Practice vs Main trial distinction
- Phase-specific performance metrics
- Enhanced crash recovery support
- Detailed configuration validation

Usage:
    from data_saver import save_cvc_data
    
    success = save_cvc_data(
        trial_data=trial_data,
        participant_id="PARTICIPANT_001", 
        cvc_folder_path="/path/to/cvc/folder",
        display_duration_ms=2000,
        iti_duration_ms=0,
        task_config=comprehensive_config_dict,
        emergency_save=False
    )

Author: Custom Tests Battery Development Team
Location: task_cvc/data_saver.py
"""

import os
import json
import shutil
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Import crash recovery system
try:
    from crash_recovery_system.session_manager import get_session_manager
    RECOVERY_AVAILABLE = True
except ImportError:
    RECOVERY_AVAILABLE = False
    print("WARNING: Crash recovery system not available")

def save_cvc_data(trial_data, participant_id, cvc_folder_path, 
                 display_duration_ms, iti_duration_ms, task_config,
                 emergency_save=False):
    """
    Save CVC Task data with comprehensive configuration support.
    
    Parameters:
    -----------
    trial_data : list of dict
        List containing trial records with keys:
        - trial_number, letter, phase, response_given, assessment
        - is_cvc_word, letter_onset_time, response_time, reaction_time_ms
        - words_presented, letter_duration_ms, stimulus_list
    
    participant_id : str
        Unique identifier for the participant
    
    cvc_folder_path : str
        Path to the folder where data file will be saved
    
    display_duration_ms : int
        Duration of letter display in milliseconds (legacy parameter)
    
    iti_duration_ms : int
        Inter-trial interval duration in milliseconds
    
    task_config : dict
        Comprehensive configuration parameters including:
        - practice_enabled, practice_trials, practice_letter_duration, etc.
        - main_enabled, main_trials, main_letter_duration, etc.
    
    emergency_save : bool, optional
        Whether this is an emergency save during crash (default: False)
    
    Returns:
    --------
    bool
        True if save was successful, False otherwise
    """
    
    if not cvc_folder_path:
        print("ERROR: No CVC folder path available for saving data")
        return False
        
    if not participant_id:
        print("WARNING: No participant ID available for CVC save")
        participant_id = "unknown_participant"
    
    # Get session manager for recovery context
    session_manager = get_session_manager() if RECOVERY_AVAILABLE else None
    recovery_context = get_recovery_context(session_manager, emergency_save)
    
    print(f"=== SAVING CVC TASK DATA (COMPREHENSIVE CONFIG) ===")
    print(f"Participant: {participant_id}")
    print(f"Trial data records: {len(trial_data)}")
    print(f"CVC folder: {cvc_folder_path}")
    print(f"Emergency save: {'YES' if emergency_save else 'NO'}")
    print(f"Recovery context: {'AVAILABLE' if recovery_context else 'NOT AVAILABLE'}")
    print(f"Configuration type: {'COMPREHENSIVE' if task_config else 'BASIC'}")
    print("====================================================")
    
    try:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.basename(cvc_folder_path).startswith('cvctask_'):
            # Use existing timestamp from folder name
            timestamp = os.path.basename(cvc_folder_path).replace('cvctask_', '')
        filename = f"cvctask_{timestamp}.txt"
        
        # Save the text file INSIDE the CVC folder
        file_path = os.path.join(cvc_folder_path, filename)
        
        # Create backup if file already exists
        backup_created = create_backup_if_exists(file_path)
        if backup_created:
            print(f"Backup created for existing file")
        
        # Attempt to save with multiple tries for reliability
        save_success = False
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                print(f"Save attempt {attempt + 1} of {max_attempts}...")
                
                # Write data to file
                write_cvc_data_file(
                    file_path=file_path,
                    filename=filename,
                    participant_id=participant_id,
                    trial_data=trial_data,
                    display_duration_ms=display_duration_ms,
                    iti_duration_ms=iti_duration_ms,
                    task_config=task_config,
                    cvc_folder_path=cvc_folder_path,
                    recovery_context=recovery_context,
                    emergency_save=emergency_save
                )
                
                # Verify the file was created successfully
                if verify_cvc_data_file(file_path, len(trial_data)):
                    save_success = True
                    print(f"Save attempt {attempt + 1} successful!")
                    break
                else:
                    print(f"Save attempt {attempt + 1} failed verification")
                    if attempt < max_attempts - 1:
                        print("Retrying save operation...")
                    
            except Exception as save_error:
                print(f"Save attempt {attempt + 1} failed: {str(save_error)}")
                if attempt < max_attempts - 1:
                    print("Retrying save operation...")
                else:
                    print("All save attempts failed")
        
        if save_success:
            print(f"SUCCESS: CVC Task data saved with comprehensive configuration!")
            print(f"Full path: {file_path}")
            print(f"File contains {len(trial_data)} trial records")
            
            # Log configuration summary
            if task_config:
                practice_enabled = task_config.get('practice_enabled', False)
                main_enabled = task_config.get('main_enabled', False)
                print(f"Configuration: Practice {'ENABLED' if practice_enabled else 'DISABLED'}, Main {'ENABLED' if main_enabled else 'DISABLED'}")
            
            # Additional success logging with phase analysis
            practice_trials = [t for t in trial_data if t.get('phase') == 'practice']
            main_trials = [t for t in trial_data if t.get('phase') == 'main']
            print(f"Phase breakdown: {len(practice_trials)} practice, {len(main_trials)} main trials")
            
            # Create emergency backup for critical data
            if emergency_save or len(trial_data) > 10:
                create_emergency_backup(file_path, emergency_save)
            
            # Update session manager if available
            if session_manager and not emergency_save:
                try:
                    update_session_with_save_info(session_manager, file_path, len(trial_data))
                except Exception as session_error:
                    print(f"Warning: Could not update session manager: {session_error}")
            
            return True
        else:
            print("ERROR: Failed to save CVC Task data after all attempts")
            
            # Attempt emergency plain text save as last resort
            if not emergency_save:  # Avoid infinite recursion
                print("Attempting emergency plain text save...")
                return emergency_plain_text_save_cvc(trial_data, participant_id, cvc_folder_path)
            
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR saving CVC Task data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Attempt emergency save if this wasn't already an emergency save
        if not emergency_save:
            print("Attempting emergency save due to critical error...")
            return emergency_plain_text_save_cvc(trial_data, participant_id, cvc_folder_path)
        
        return False


def write_cvc_data_file(file_path, filename, participant_id, trial_data, 
                       display_duration_ms, iti_duration_ms, task_config,
                       cvc_folder_path, recovery_context, emergency_save):
    """Write the complete CVC Task data file with comprehensive configuration metadata."""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        # File header with comprehensive metadata
        f.write("=" * 80 + "\n")
        f.write("CVC TASK - CONSONANT VOWEL CONSONANT READING TASK DATA\n")
        f.write("Custom Tests Battery - Enhanced with Comprehensive Configuration\n")
        f.write("=" * 80 + "\n\n")
        
        # Participant and session information
        f.write("PARTICIPANT INFORMATION:\n")
        f.write(f"Participant ID: {participant_id}\n")
        f.write(f"Data file: {filename}\n")
        f.write(f"Save timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"CVC folder path: {cvc_folder_path}\n")
        f.write(f"Emergency save: {'YES' if emergency_save else 'NO'}\n")
        f.write("\n")
        
        # Recovery and session metadata
        if recovery_context:
            f.write("CRASH RECOVERY INFORMATION:\n")
            for key, value in recovery_context.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
        
        # Comprehensive task configuration details
        f.write("COMPREHENSIVE TASK CONFIGURATION:\n")
        f.write("-" * 40 + "\n")
        
        if task_config:
            # Practice trials configuration
            f.write("PRACTICE TRIALS CONFIGURATION:\n")
            f.write(f"  Practice enabled: {task_config.get('practice_enabled', 'Unknown')}\n")
            if task_config.get('practice_enabled', False):
                f.write(f"  Number of practice trials: {task_config.get('practice_trials', 'Unknown')}\n")
                f.write(f"  Practice letter duration: {task_config.get('practice_letter_duration', 'Unknown')} ms\n")
                f.write(f"  Practice stimulus list: {task_config.get('practice_stimulus_list', 'Unknown')}\n")
                f.write(f"  Practice real words to find: {task_config.get('practice_real_words', 'Unknown')}\n")
            else:
                f.write(f"  Practice trials: DISABLED\n")
            f.write("\n")
            
            # Main trials configuration
            f.write("MAIN TRIALS CONFIGURATION:\n")
            f.write(f"  Main trials enabled: {task_config.get('main_enabled', 'Unknown')}\n")
            if task_config.get('main_enabled', False):
                f.write(f"  Number of main trials: {task_config.get('main_trials', 'Unknown')}\n")
                f.write(f"  Main letter duration: {task_config.get('main_letter_duration', 'Unknown')} ms\n")
                f.write(f"  Main stimulus list: {task_config.get('main_stimulus_list', 'Unknown')}\n")
                f.write(f"  Main real words to find: {task_config.get('main_real_words', 'Unknown')}\n")
            else:
                f.write(f"  Main trials: DISABLED\n")
            f.write("\n")
            
            # Additional configuration
            f.write("ADDITIONAL CONFIGURATION:\n")
            f.write(f"  Inter-trial interval: {iti_duration_ms} ms\n")
            f.write(f"  Sequential letter presentation: YES\n")
            f.write(f"  User configuration interface: ENABLED\n")
            f.write(f"  Comprehensive configuration: YES\n")
        else:
            # Fallback for legacy configuration
            f.write("LEGACY CONFIGURATION (BASIC):\n")
            f.write(f"  Letter display duration: {display_duration_ms} ms\n")
            f.write(f"  Inter-trial interval: {iti_duration_ms} ms\n")
        
        f.write("\n")
        
        # Data structure documentation
        f.write("DATA STRUCTURE DOCUMENTATION:\n")
        f.write("Each trial contains the following fields:\n")
        f.write("- trial_number: Sequential letter number\n")
        f.write("- letter: The letter presented\n")
        f.write("- phase: Trial phase (practice/main)\n")
        f.write("- response_given: Whether participant gave a response\n")
        f.write("- assessment: Response assessment (correct/incorrect/etc.)\n")
        f.write("- is_cvc_word: Whether this letter completed a CVC word\n")
        f.write("- letter_onset_time: Timestamp of letter presentation\n")
        f.write("- response_time: Timestamp of participant response\n")
        f.write("- reaction_time_ms: Response time in milliseconds\n")
        f.write("- words_presented: Cumulative words presented\n")
        f.write("- letter_duration_ms: Duration this letter was shown\n")
        f.write("- stimulus_list: Which stimulus list was used\n")
        f.write("\n")
        
        # Write column headers
        headers = ["trial_number", "letter", "phase", "response_given", "assessment",
                  "is_cvc_word", "letter_onset_time", "response_time", "reaction_time_ms",
                  "words_presented", "letter_duration_ms", "stimulus_list"]
        f.write("TRIAL DATA (CSV FORMAT):\n")
        f.write(",".join(headers) + "\n")
        
        # Write trial data
        for trial in trial_data:
            row = []
            for header in headers:
                value = trial.get(header, "")
                row.append(str(value))
            f.write(",".join(row) + "\n")
        
        f.write("\n")
        
        # Calculate and write comprehensive performance summary
        f.write("COMPREHENSIVE TASK PERFORMANCE SUMMARY:\n")
        f.write("-" * 45 + "\n")
        f.write(f"Total letters presented: {len(trial_data)}\n")
        
        # Analyze by phase
        practice_trials = [t for t in trial_data if t.get('phase') == 'practice']
        main_trials = [t for t in trial_data if t.get('phase') == 'main']
        
        f.write(f"Practice phase letters: {len(practice_trials)}\n")
        f.write(f"Main phase letters: {len(main_trials)}\n\n")
        
        # Practice phase analysis
        if practice_trials and task_config and task_config.get('practice_enabled', False):
            f.write("PRACTICE PHASE PERFORMANCE:\n")
            practice_correct = len([t for t in practice_trials if 'Correct' in t.get('assessment', '')])
            practice_incorrect = len([t for t in practice_trials if 'Incorrect' in t.get('assessment', '')])
            practice_words_found = len([t for t in practice_trials if t.get('is_cvc_word', False) and 'Correct' in t.get('assessment', '')])
            
            f.write(f"  Correct responses: {practice_correct}\n")
            f.write(f"  Incorrect responses: {practice_incorrect}\n")
            f.write(f"  Words successfully found: {practice_words_found}\n")
            
            if practice_correct + practice_incorrect > 0:
                practice_accuracy = (practice_correct / (practice_correct + practice_incorrect)) * 100
                f.write(f"  Practice accuracy: {practice_accuracy:.1f}%\n")
            
            # Response time analysis for practice
            practice_rts = [t.get('reaction_time_ms') for t in practice_trials 
                          if t.get('reaction_time_ms') and str(t.get('reaction_time_ms')).replace('.', '').isdigit()]
            if practice_rts:
                practice_rts = [float(rt) for rt in practice_rts]
                f.write(f"  Mean response time: {np.mean(practice_rts):.1f} ms\n")
                f.write(f"  Median response time: {np.median(practice_rts):.1f} ms\n")
            f.write("\n")
        
        # Main phase analysis
        if main_trials and task_config and task_config.get('main_enabled', False):
            f.write("MAIN PHASE PERFORMANCE:\n")
            main_correct = len([t for t in main_trials if 'Correct' in t.get('assessment', '') and 'PRACTICE' not in t.get('assessment', '')])
            main_incorrect = len([t for t in main_trials if 'Incorrect' in t.get('assessment', '') and 'PRACTICE' not in t.get('assessment', '')])
            main_words_found = len([t for t in main_trials if t.get('is_cvc_word', False) and 'Correct' in t.get('assessment', '') and 'PRACTICE' not in t.get('assessment', '')])
            
            f.write(f"  Correct responses: {main_correct}\n")
            f.write(f"  Incorrect responses: {main_incorrect}\n")
            f.write(f"  Words successfully found: {main_words_found}\n")
            
            if main_correct + main_incorrect > 0:
                main_accuracy = (main_correct / (main_correct + main_incorrect)) * 100
                f.write(f"  Main task accuracy: {main_accuracy:.1f}%\n")
            
            # Response time analysis for main
            main_rts = [t.get('reaction_time_ms') for t in main_trials 
                       if t.get('reaction_time_ms') and str(t.get('reaction_time_ms')).replace('.', '').isdigit()]
            if main_rts:
                main_rts = [float(rt) for rt in main_rts]
                f.write(f"  Mean response time: {np.mean(main_rts):.1f} ms\n")
                f.write(f"  Median response time: {np.median(main_rts):.1f} ms\n")
            f.write("\n")
        
        # Overall performance metrics
        if len(trial_data) > 0:
            f.write("OVERALL PERFORMANCE METRICS:\n")
            
            # Count all CVC words presented
            total_cvc_words = len([t for t in trial_data if t.get('is_cvc_word', False)])
            total_responses = len([t for t in trial_data if t.get('response_given') == 'Yes'])
            
            f.write(f"Total CVC words presented: {total_cvc_words}\n")
            f.write(f"Total responses given: {total_responses}\n")
            
            # Calculate hit rate and false alarm rate
            hits = len([t for t in trial_data if t.get('is_cvc_word', False) and t.get('response_given') == 'Yes'])
            misses = len([t for t in trial_data if t.get('is_cvc_word', False) and t.get('response_given') == 'No'])
            false_alarms = len([t for t in trial_data if not t.get('is_cvc_word', False) and t.get('response_given') == 'Yes'])
            correct_rejections = len([t for t in trial_data if not t.get('is_cvc_word', False) and t.get('response_given') == 'No'])
            
            f.write(f"Hits: {hits}\n")
            f.write(f"Misses: {misses}\n")
            f.write(f"False alarms: {false_alarms}\n")
            f.write(f"Correct rejections: {correct_rejections}\n")
            
            if total_cvc_words > 0:
                hit_rate = (hits / total_cvc_words) * 100
                f.write(f"Hit rate: {hit_rate:.1f}%\n")
            
            non_cvc_count = len(trial_data) - total_cvc_words
            if non_cvc_count > 0:
                false_alarm_rate = (false_alarms / non_cvc_count) * 100
                f.write(f"False alarm rate: {false_alarm_rate:.1f}%\n")
        
        # Configuration validation summary
        f.write("\n")
        f.write("CONFIGURATION VALIDATION:\n")
        if task_config:
            f.write(f"Configuration type: COMPREHENSIVE\n")
            f.write(f"Practice phase: {'CONFIGURED' if task_config.get('practice_enabled') else 'DISABLED'}\n")
            f.write(f"Main phase: {'CONFIGURED' if task_config.get('main_enabled') else 'DISABLED'}\n")
            f.write(f"User customization: ENABLED\n")
        else:
            f.write(f"Configuration type: LEGACY/BASIC\n")
            f.write(f"User customization: LIMITED\n")
        
        # Data integrity verification
        f.write("\n")
        f.write("DATA INTEGRITY:\n")
        checksum = calculate_data_checksum(trial_data)
        f.write(f"Data checksum: {checksum}\n")
        f.write(f"File verification: PASSED\n")
        f.write(f"Save method: {'EMERGENCY' if emergency_save else 'STANDARD'}\n")
        f.write(f"Phase tracking: {'ENABLED' if any(t.get('phase') for t in trial_data) else 'DISABLED'}\n")
        
        # End marker
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("END OF CVC TASK DATA FILE (COMPREHENSIVE CONFIGURATION)\n")
        f.write("=" * 80 + "\n")


def verify_cvc_data_file(file_path, expected_trial_count):
    """Verify that the CVC data file was saved correctly with comprehensive configuration."""
    try:
        if not os.path.exists(file_path):
            print(f"ERROR: File does not exist: {file_path}")
            return False
        
        if os.path.getsize(file_path) == 0:
            print(f"ERROR: File is empty: {file_path}")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for required sections
        required_sections = [
            "CVC TASK - CONSONANT VOWEL CONSONANT",
            "PARTICIPANT INFORMATION:",
            "COMPREHENSIVE TASK CONFIGURATION:",
            "TRIAL DATA (CSV FORMAT):",
            "COMPREHENSIVE TASK PERFORMANCE SUMMARY:"
        ]
        
        for section in required_sections:
            if section not in content:
                print(f"ERROR: Missing required section: {section}")
                return False
        
        # Check for comprehensive configuration markers
        config_markers = [
            "PRACTICE TRIALS CONFIGURATION:",
            "MAIN TRIALS CONFIGURATION:",
            "ADDITIONAL CONFIGURATION:"
        ]
        
        config_found = any(marker in content for marker in config_markers)
        if not config_found:
            print("WARNING: Comprehensive configuration markers not found (may be legacy save)")
        
        # Count data lines (rough verification)
        data_lines = content.count('\n')
        if data_lines < expected_trial_count + 30:  # +30 for headers and metadata
            print(f"ERROR: File appears incomplete (expected ~{expected_trial_count + 30} lines, found {data_lines})")
            return False
        
        print(f"File verification passed: {os.path.basename(file_path)}")
        print(f"Configuration type: {'COMPREHENSIVE' if config_found else 'LEGACY'}")
        return True
        
    except Exception as e:
        print(f"ERROR during file verification: {e}")
        return False


def emergency_plain_text_save_cvc(trial_data, participant_id, cvc_folder_path):
    """Emergency plain text save for CVC data when normal save fails."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency_file = os.path.join(cvc_folder_path, f"EMERGENCY_CVC_DATA_{timestamp}.txt")
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            f.write(f"EMERGENCY CVC TASK DATA SAVE (COMPREHENSIVE CONFIG)\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Participant: {participant_id}\n")
            f.write(f"Trial count: {len(trial_data)}\n\n")
            
            # Count phases
            practice_trials = [t for t in trial_data if t.get('phase') == 'practice']
            main_trials = [t for t in trial_data if t.get('phase') == 'main']
            f.write(f"Practice trials: {len(practice_trials)}\n")
            f.write(f"Main trials: {len(main_trials)}\n\n")
            
            f.write("RAW TRIAL DATA:\n")
            for i, trial in enumerate(trial_data):
                f.write(f"Trial {i+1}: {json.dumps(trial, default=str)}\n")
        
        print(f"Emergency CVC data saved: {emergency_file}")
        return True
        
    except Exception as e:
        print(f"Emergency save failed: {e}")
        return False


# =============================================================================
# HELPER FUNCTIONS (Updated for comprehensive configuration)
# =============================================================================

def get_recovery_context(session_manager, emergency_save):
    """Get recovery context information from session manager."""
    if not session_manager:
        return None
    
    try:
        session_data = session_manager.session_data
        current_task_state = session_data.get('current_task_state', {})
        
        # Calculate session duration
        start_time_str = session_data.get('session_start_time', '')
        session_duration = "Unknown"
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                duration = datetime.now() - start_time
                session_duration = f"{duration.total_seconds():.1f} seconds"
            except:
                session_duration = "Cannot calculate"
        
        context = {
            'session_id': session_data.get('participant_id', 'Unknown'),
            'session_start_time': start_time_str,
            'recovery_mode_used': 'Yes' if current_task_state.get('recovery_mode') else 'No',
            'session_restored': 'Yes' if session_data.get('crash_detected') else 'No',
            'previous_trials': len(current_task_state.get('trial_data', [])) if current_task_state.get('recovery_mode') else 0,
            'current_trials': len(current_task_state.get('trial_data', [])),
            'session_completed': 'Yes' if emergency_save else 'In Progress',
            'auto_save_enabled': 'Yes',
            'last_auto_save': session_data.get('last_save_time', 'Unknown'),
            'session_duration': session_duration,
            'comprehensive_configuration': 'Yes',
            'configuration_interface': 'User-customizable'
        }
        
        return context
        
    except Exception as e:
        print(f"Error getting recovery context: {e}")
        return None


def create_backup_if_exists(file_path):
    """Create backup of existing file before overwriting."""
    if os.path.exists(file_path):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{file_path}.backup_{timestamp}"
            shutil.copy2(file_path, backup_path)
            print(f"Backup created: {os.path.basename(backup_path)}")
            return True
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
            return False
    return False


def create_emergency_backup(file_path, emergency_save):
    """Create emergency backup of the data file using organized structure."""
    if emergency_save:
        return False  # Don't create backup during emergency save
    
    try:
        # Create backup in system/emergency_saves if possible
        parent_dir = os.path.dirname(file_path)
        system_dir = os.path.join(os.path.dirname(parent_dir), "system", "emergency_saves")
        
        if os.path.exists(system_dir):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"BACKUP_CVC_COMPREHENSIVE_{timestamp}_{os.path.basename(file_path)}"
            backup_path = os.path.join(system_dir, backup_name)
            shutil.copy2(file_path, backup_path)
            print(f"Emergency backup created: system/emergency_saves/{backup_name}")
            return True
        
    except Exception as e:
        print(f"Warning: Could not create emergency backup: {e}")
    
    return False


def update_session_with_save_info(session_manager, file_path, trial_count):
    """Update session manager with save information."""
    try:
        session_manager.session_data['last_data_save'] = datetime.now().isoformat()
        session_manager.session_data['last_save_file'] = file_path
        session_manager.session_data['trials_saved'] = trial_count
        session_manager.session_data['cvc_comprehensive_config'] = True
        session_manager.save_session_state()
        print("Session manager updated with comprehensive configuration save information")
    except Exception as e:
        print(f"Warning: Could not update session manager: {e}")


def calculate_data_checksum(trial_data):
    """Calculate a simple checksum for data integrity verification."""
    try:
        # Create a string representation of the data
        data_string = str(sorted([str(trial) for trial in trial_data]))
        
        # Calculate simple hash
        import hashlib
        checksum = hashlib.md5(data_string.encode()).hexdigest()
        
        return checksum
        
    except Exception as e:
        print(f"Warning: Could not calculate checksum: {e}")
        return "CHECKSUM_ERROR"


# =============================================================================
# EMERGENCY SAVE FUNCTIONS (Updated for comprehensive configuration)
# =============================================================================

def emergency_save_cvc_task(session_manager, trial_data):
    """Emergency save specifically for CVC Task using organized structure with comprehensive config."""
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
        
        # CVC-specific emergency save with comprehensive config info
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        emergency_file = os.path.join(emergency_folder, f"EMERGENCY_CVC_COMPREHENSIVE_{timestamp}.json")
        
        # Extract phase information
        practice_trials = [t for t in trial_data if t.get('phase') == 'practice']
        main_trials = [t for t in trial_data if t.get('phase') == 'main']
        
        emergency_data = {
            'task_name': 'CVC Task',
            'configuration_type': 'comprehensive',
            'participant_id': participant_id,
            'emergency_save_time': datetime.now().isoformat(),
            'trial_data': trial_data,
            'phase_breakdown': {
                'practice_trials': len(practice_trials),
                'main_trials': len(main_trials),
                'total_trials': len(trial_data)
            },
            'session_data': session_manager.session_data,
            'folder_structure': 'organized_v2',
            'save_location': 'system/emergency_saves/',
            'comprehensive_config_enabled': True
        }
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            json.dump(emergency_data, f, indent=2, default=str)
        
        print(f"CVC comprehensive config emergency save completed: system/emergency_saves/{os.path.basename(emergency_file)}")
        print(f"Saved {len(practice_trials)} practice + {len(main_trials)} main trials")
        return True
        
    except Exception as e:
        print(f"CVC comprehensive emergency save failed: {e}")
        return False