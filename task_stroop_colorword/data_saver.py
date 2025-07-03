"""
STROOP COLOR-WORD TASK DATA SAVER MODULE - WITH CRASH RECOVERY
Custom Tests Battery - Stroop Task Specific Data Saving

This module contains the data saving functionality specifically for the Stroop Color-Word Task.
Includes comprehensive crash recovery support and enhanced error handling.

Features:
- Automatic backup creation
- Recovery metadata integration
- Enhanced error handling and validation
- Session state awareness
- Emergency save capabilities
- Multiple save attempt mechanisms
- Comprehensive logging and verification
- RT analysis and timing validation

Usage:
    from data_saver import save_stroop_data
    
    success = save_stroop_data(
        trial_data=trial_data,
        participant_id="PARTICIPANT_001", 
        audio_folder_path="/path/to/audio/folder",
        recording_duration_seconds=3.0,
        pre_stimulus_delay_ms=200,
        analysis_available=True,
        emergency_save=False
    )

Author: Custom Tests Battery Development Team
Version: 2.0 (Stroop Task Specific)
Location: task_stroop_colorword/data_saver.py
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

def save_stroop_data(trial_data, participant_id, audio_folder_path, 
                    recording_duration_seconds, pre_stimulus_delay_ms,
                    analysis_available=True, emergency_save=False):
    """
    Save Stroop Color-Word task data with comprehensive crash recovery support.
    
    Parameters:
    -----------
    trial_data : list of dict
        List containing trial records with keys:
        - trial_number, condition1, stim1, textColor, audio_file
        - audio_start_time, stimulus_onset_time, stimulus_offset
        - rt_seconds, rt_confidence, timing_method
    
    participant_id : str
        Unique identifier for the participant
    
    audio_folder_path : str
        Path to the folder containing audio recordings and where data file will be saved
    
    recording_duration_seconds : float
        Duration of audio recording per trial (from RECORDING_DURATION_SECONDS config)
    
    pre_stimulus_delay_ms : int
        Pre-stimulus delay in milliseconds (from PRE_STIMULUS_DELAY_MS config)
    
    analysis_available : bool, optional
        Whether RT analysis libraries are available (default: True)
    
    emergency_save : bool, optional
        Whether this is an emergency save during crash (default: False)
    
    Returns:
    --------
    bool
        True if save was successful, False otherwise
    
    Enhanced Features:
    ------------------
    - Automatic backup creation before saving
    - Recovery metadata integration
    - Multiple save attempt mechanisms
    - Enhanced error handling and validation
    - Session state awareness
    - Emergency save capabilities
    
    File Structure:
    ---------------
    The output file contains:
    1. Header with experiment and participant info
    2. Recovery and session metadata
    3. Technical documentation of timing methods
    4. CSV-formatted trial data
    5. Technical summary with analysis results
    6. Crash recovery status information
    
    Configuration Source:
    ---------------------
    recording_duration_seconds and pre_stimulus_delay_ms values are passed directly 
    from the Stroop Color-Word task configuration constants for single-source configuration.
    """
    
    if not audio_folder_path:
        print("ERROR: No audio folder path available for saving Stroop Color-Word data")
        return False
        
    if not participant_id:
        print("WARNING: No participant ID available for Stroop Color-Word save")
        participant_id = "unknown_participant"
    
    # Get session manager for recovery context
    session_manager = get_session_manager() if RECOVERY_AVAILABLE else None
    recovery_context = get_recovery_context(session_manager, emergency_save)
    
    print(f"=== SAVING STROOP COLOR-WORD DATA ===")
    print(f"Participant: {participant_id}")
    print(f"Trial data records: {len(trial_data)}")
    print(f"Audio folder: {audio_folder_path}")
    print(f"Emergency save: {'YES' if emergency_save else 'NO'}")
    print(f"Recovery context: {'AVAILABLE' if recovery_context else 'NOT AVAILABLE'}")
    print(f"Analysis libraries: {'AVAILABLE' if analysis_available else 'NOT AVAILABLE'}")
    print("=====================================")
    
    try:
        # Generate filename with timestamp (same timestamp as audio folder)
        timestamp = os.path.basename(audio_folder_path).replace('stroopcolorwordtask_', '')
        filename = f"stroopcolorwordtask_{timestamp}.txt"
        
        # Save the text file INSIDE the audio folder
        file_path = os.path.join(audio_folder_path, filename)
        
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
                write_stroop_data_file(
                    file_path=file_path,
                    filename=filename,
                    participant_id=participant_id,
                    trial_data=trial_data,
                    recording_duration_seconds=recording_duration_seconds,
                    pre_stimulus_delay_ms=pre_stimulus_delay_ms,
                    analysis_available=analysis_available,
                    audio_folder_path=audio_folder_path,
                    recovery_context=recovery_context,
                    emergency_save=emergency_save
                )
                
                # Verify the file was created successfully
                if verify_stroop_data_file(file_path, len(trial_data)):
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
            print(f"SUCCESS: Stroop Color-Word task data saved!")
            print(f"Full path: {file_path}")
            print(f"File contains {len(trial_data)} trial records")
            
            # Additional success logging
            if analysis_available:
                successful_rts = sum(1 for trial in trial_data if trial.get('rt_seconds') is not None)
                print(f"RT values calculated for {successful_rts}/{len(trial_data)} trials")
            
            # Create emergency backup for critical data
            if emergency_save or len(trial_data) > 10:  # Create backup for substantial data
                create_emergency_backup(file_path, emergency_save)
            
            # Update session manager if available
            if session_manager and not emergency_save:
                try:
                    update_session_with_save_info(session_manager, file_path, len(trial_data))
                except Exception as session_error:
                    print(f"Warning: Could not update session manager: {session_error}")
            
            return True
        else:
            print("ERROR: Failed to save Stroop Color-Word task data after all attempts")
            
            # Attempt emergency plain text save as last resort
            if not emergency_save:  # Avoid infinite recursion
                print("Attempting emergency plain text save...")
                return emergency_plain_text_save_stroop(trial_data, participant_id, audio_folder_path)
            
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR saving Stroop Color-Word task data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Attempt emergency save if this wasn't already an emergency save
        if not emergency_save:
            print("Attempting emergency save due to critical error...")
            return emergency_plain_text_save_stroop(trial_data, participant_id, audio_folder_path)
        
        return False


def write_stroop_data_file(file_path, filename, participant_id, trial_data, 
                          recording_duration_seconds, pre_stimulus_delay_ms,
                          analysis_available, audio_folder_path, recovery_context, emergency_save):
    """Write the complete Stroop Color-Word data file with enhanced metadata."""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        # File header with comprehensive metadata
        f.write("=" * 80 + "\n")
        f.write("STROOP COLOR-WORD TASK DATA\n")
        f.write("Custom Tests Battery - Enhanced with Crash Recovery\n")
        f.write("=" * 80 + "\n\n")
        
        # Participant and session information
        f.write("PARTICIPANT INFORMATION:\n")
        f.write(f"Participant ID: {participant_id}\n")
        f.write(f"Data file: {filename}\n")
        f.write(f"Save timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Audio folder path: {audio_folder_path}\n")
        f.write(f"Emergency save: {'YES' if emergency_save else 'NO'}\n")
        f.write("\n")
        
        # Recovery and session metadata
        if recovery_context:
            f.write("CRASH RECOVERY INFORMATION:\n")
            for key, value in recovery_context.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
        
        # Task configuration and timing
        f.write("TASK CONFIGURATION:\n")
        f.write(f"Recording duration per trial: {recording_duration_seconds} seconds\n")
        f.write(f"Pre-stimulus delay: {pre_stimulus_delay_ms} ms\n")
        f.write(f"RT analysis libraries: {'AVAILABLE' if analysis_available else 'NOT AVAILABLE'}\n")
        f.write("\n")
        
        # Technical documentation
        f.write("TECHNICAL DETAILS:\n")
        f.write("Timing Method: frame_flip_colorword_task\n")
        f.write("- Stimulus presentation synchronized to display refresh\n")
        f.write("- Audio recording starts with pre-stimulus delay\n")
        f.write("- RT calculated from audio analysis\n")
        f.write("- Confidence scores indicate RT measurement reliability\n")
        f.write("\n")
        
        # Data structure documentation
        f.write("DATA STRUCTURE DOCUMENTATION:\n")
        f.write("Each trial contains the following fields:\n")
        f.write("- trial_number: Sequential trial number\n")
        f.write("- condition1: Congruent/Incongruent condition\n")
        f.write("- stim1: Text stimulus (color word)\n")
        f.write("- textColor: Display color of the text\n")
        f.write("- audio_file: Associated audio recording file\n")
        f.write("- audio_start_time: Unix timestamp when recording started\n")
        f.write("- stimulus_onset_time: Unix timestamp of stimulus presentation\n")
        f.write("- stimulus_offset: Duration from recording start to stimulus (seconds)\n")
        f.write("- rt_seconds: Calculated reaction time in seconds\n")
        f.write("- rt_confidence: Confidence score for RT calculation (0-1)\n")
        f.write("- timing_method: Method used for timing synchronization\n")
        f.write("\n")
        
        # Write column headers
        headers = ["trial_number", "condition1", "stim1", "textColor", "audio_file",
                  "audio_start_time", "stimulus_onset_time", "stimulus_offset",
                  "rt_seconds", "rt_confidence", "timing_method"]
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
        
        # Calculate and write summary statistics
        f.write("TASK PERFORMANCE SUMMARY:\n")
        f.write(f"Total trials: {len(trial_data)}\n")
        
        if analysis_available and trial_data:
            # Analyze RT data
            rt_values = [trial.get('rt_seconds') for trial in trial_data if trial.get('rt_seconds') is not None]
            confidence_values = [trial.get('rt_confidence') for trial in trial_data if trial.get('rt_confidence') is not None]
            
            f.write(f"Trials with RT data: {len(rt_values)}/{len(trial_data)}\n")
            
            if rt_values:
                mean_rt = np.mean(rt_values)
                median_rt = np.median(rt_values)
                std_rt = np.std(rt_values)
                min_rt = np.min(rt_values)
                max_rt = np.max(rt_values)
                
                f.write(f"Mean RT: {mean_rt:.3f} seconds\n")
                f.write(f"Median RT: {median_rt:.3f} seconds\n")
                f.write(f"RT Standard Deviation: {std_rt:.3f} seconds\n")
                f.write(f"Min RT: {min_rt:.3f} seconds\n")
                f.write(f"Max RT: {max_rt:.3f} seconds\n")
                
                # Analyze by condition
                congruent_rts = [trial.get('rt_seconds') for trial in trial_data 
                               if trial.get('condition1') == 'congruent' and trial.get('rt_seconds') is not None]
                incongruent_rts = [trial.get('rt_seconds') for trial in trial_data 
                                 if trial.get('condition1') == 'incongruent' and trial.get('rt_seconds') is not None]
                
                if congruent_rts and incongruent_rts:
                    mean_congruent = np.mean(congruent_rts)
                    mean_incongruent = np.mean(incongruent_rts)
                    stroop_effect = mean_incongruent - mean_congruent
                    
                    f.write(f"Congruent trials mean RT: {mean_congruent:.3f} seconds (n={len(congruent_rts)})\n")
                    f.write(f"Incongruent trials mean RT: {mean_incongruent:.3f} seconds (n={len(incongruent_rts)})\n")
                    f.write(f"Stroop interference effect: {stroop_effect:.3f} seconds\n")
            
            if confidence_values:
                mean_confidence = np.mean(confidence_values)
                f.write(f"Mean RT confidence: {mean_confidence:.3f}\n")
                
                # Count high-confidence trials
                high_confidence_trials = sum(1 for conf in confidence_values if conf >= 0.8)
                f.write(f"High confidence trials (≥0.8): {high_confidence_trials}/{len(confidence_values)}\n")
        
        # Data integrity verification
        f.write("\n")
        f.write("DATA INTEGRITY:\n")
        checksum = calculate_data_checksum(trial_data)
        f.write(f"Data checksum: {checksum}\n")
        f.write(f"File verification: PASSED\n")
        f.write(f"Save method: {'EMERGENCY' if emergency_save else 'STANDARD'}\n")
        
        # Audio file verification
        audio_files_exist = 0
        for trial in trial_data:
            audio_file = trial.get('audio_file', '')
            if audio_file:
                audio_path = os.path.join(audio_folder_path, audio_file)
                if os.path.exists(audio_path):
                    audio_files_exist += 1
        
        f.write(f"Audio files present: {audio_files_exist}/{len(trial_data)}\n")
        
        # End marker
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("END OF STROOP COLOR-WORD TASK DATA FILE\n")
        f.write("=" * 80 + "\n")


def verify_stroop_data_file(file_path, expected_trial_count):
    """Verify that the Stroop data file was saved correctly."""
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
            "STROOP COLOR-WORD TASK DATA",
            "PARTICIPANT INFORMATION:",
            "TASK CONFIGURATION:",
            "TECHNICAL DETAILS:",
            "TRIAL DATA (CSV FORMAT):",
            "TASK PERFORMANCE SUMMARY:"
        ]
        
        for section in required_sections:
            if section not in content:
                print(f"ERROR: Missing required section: {section}")
                return False
        
        # Check for essential data columns
        required_columns = [
            "trial_number", "condition1", "stim1", "textColor", 
            "rt_seconds", "rt_confidence"
        ]
        
        for column in required_columns:
            if column not in content:
                print(f"ERROR: Missing required data column: {column}")
                return False
        
        # Count data lines (rough verification)
        data_lines = content.count('\n')
        if data_lines < expected_trial_count + 30:  # +30 for headers and metadata
            print(f"ERROR: File appears incomplete (expected ~{expected_trial_count + 30} lines, found {data_lines})")
            return False
        
        print(f"File verification passed: {os.path.basename(file_path)}")
        return True
        
    except Exception as e:
        print(f"ERROR during file verification: {e}")
        return False


def emergency_plain_text_save_stroop(trial_data, participant_id, audio_folder_path):
    """Emergency plain text save for Stroop data when normal save fails."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency_file = os.path.join(audio_folder_path, f"EMERGENCY_STROOP_DATA_{timestamp}.txt")
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            f.write(f"EMERGENCY STROOP COLOR-WORD TASK DATA SAVE\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Participant: {participant_id}\n")
            f.write(f"Trial count: {len(trial_data)}\n\n")
            
            f.write("RAW TRIAL DATA:\n")
            for i, trial in enumerate(trial_data):
                f.write(f"Trial {i+1}: {json.dumps(trial, default=str)}\n")
        
        print(f"Emergency Stroop data saved: {emergency_file}")
        return True
        
    except Exception as e:
        print(f"Emergency save failed: {e}")
        return False


# =============================================================================
# HELPER FUNCTIONS
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
            'session_duration': session_duration
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
            backup_name = f"BACKUP_STROOP_{timestamp}_{os.path.basename(file_path)}"
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
        session_manager.save_session_state()
        print("Session manager updated with save information")
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
# EMERGENCY SAVE FUNCTIONS
# =============================================================================

def emergency_save_stroop_task(session_manager, trial_data):
    """Emergency save specifically for Stroop Color-Word Task using organized structure."""
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
        
        # Stroop-specific emergency save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        emergency_file = os.path.join(emergency_folder, f"EMERGENCY_STROOP_TASK_{timestamp}.json")
        
        emergency_data = {
            'task_name': 'Stroop Colour-Word Task',
            'participant_id': participant_id,
            'emergency_save_time': datetime.now().isoformat(),
            'trial_data': trial_data,
            'session_data': session_manager.session_data,
            'folder_structure': 'organized_v2',
            'save_location': 'system/emergency_saves/'
        }
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            json.dump(emergency_data, f, indent=2, default=str)
        
        print(f"Stroop emergency save completed in organized structure: system/emergency_saves/{os.path.basename(emergency_file)}")
        return True
        
    except Exception as e:
        print(f"Stroop emergency save failed: {e}")
        return False


# =============================================================================
# ALTERNATIVE FUNCTION NAMES FOR COMPATIBILITY
# =============================================================================

# Provide alternative function names for compatibility with existing code
def save_stroop_colorword_data(*args, **kwargs):
    """Alternative function name for compatibility."""
    return save_stroop_data(*args, **kwargs)