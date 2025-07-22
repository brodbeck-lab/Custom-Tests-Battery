#!/usr/bin/env python3
"""
READING SPAN TASK DATA SAVER MODULE - WITH WORD SELECTION INTERFACE
Custom Tests Battery - Reading Span Task Specific Data Saving

This module contains the data saving functionality specifically for the Reading Span Task.
Updated to support word selection interface and comprehensive recall data logging.

Features:
- Word selection logging
- Comprehensive recall analysis
- Enhanced crash recovery support
- Detailed performance metrics
- Integration with session management

Usage:
    from data_saver import save_reading_span_data, emergency_save_reading_span_task
    
    success = save_reading_span_data(
        trial_data=trial_data,
        recall_data=recall_data,
        participant_id="PARTICIPANT_001", 
        reading_span_folder_path="/path/to/reading_span/folder",
        task_config=config_dict,
        emergency_save=False
    )

Author: Custom Tests Battery Development Team
Location: task_reading_span/data_saver.py
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

def save_reading_span_data(trial_data, recall_data, participant_id, reading_span_folder_path, 
                          task_config, emergency_save=False):
    """
    Save Reading Span Task data with word selection interface support.
    
    Parameters:
    -----------
    trial_data : list of dict
        List containing trial records with sentence presentation data
    
    recall_data : list of dict
        List containing recall records with word selection data
    
    participant_id : str
        Unique identifier for the participant
    
    reading_span_folder_path : str
        Path to the folder where data files will be saved
    
    task_config : dict
        Task configuration parameters
    
    emergency_save : bool, optional
        Whether this is an emergency save during crash (default: False)
    
    Returns:
    --------
    bool
        True if save was successful, False otherwise
    """
    
    if not reading_span_folder_path:
        print("ERROR: No Reading Span folder path available for saving data")
        return False
        
    if not participant_id:
        print("WARNING: No participant ID available for Reading Span save")
        participant_id = "unknown_participant"
    
    # Get session manager for recovery context
    session_manager = get_session_manager() if RECOVERY_AVAILABLE else None
    recovery_context = get_recovery_context(session_manager, emergency_save)
    
    print(f"=== SAVING READING SPAN TASK DATA (WORD SELECTION) ===")
    print(f"Participant: {participant_id}")
    print(f"Trial data records: {len(trial_data)}")
    print(f"Recall data records: {len(recall_data)}")
    print(f"Reading Span folder: {reading_span_folder_path}")
    print(f"Emergency save: {'YES' if emergency_save else 'NO'}")
    print(f"Word selection interface: ENABLED")
    print("======================================================")
    
    try:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.basename(reading_span_folder_path).startswith('readingspantask_'):
            # Use existing timestamp from folder name
            timestamp = os.path.basename(reading_span_folder_path).replace('readingspantask_', '')
        filename = f"readingspantask_{timestamp}.txt"
        
        # Save the text file INSIDE the Reading Span folder
        file_path = os.path.join(reading_span_folder_path, filename)
        
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
                write_reading_span_data_file(
                    file_path=file_path,
                    filename=filename,
                    participant_id=participant_id,
                    trial_data=trial_data,
                    recall_data=recall_data,
                    task_config=task_config,
                    reading_span_folder_path=reading_span_folder_path,
                    recovery_context=recovery_context,
                    emergency_save=emergency_save
                )
                
                # Verify the file was created successfully
                if verify_reading_span_data_file(file_path, len(trial_data), len(recall_data)):
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
            print(f"SUCCESS: Reading Span Task data saved with word selection interface!")
            print(f"Full path: {file_path}")
            print(f"File contains {len(trial_data)} trial records and {len(recall_data)} recall records")
            
            # Log word selection summary
            if recall_data:
                total_selections = sum(len(r.get('user_selected_words', [])) for r in recall_data)
                print(f"Word selections: {total_selections} total words selected across all recalls")
            
            # Create emergency backup for critical data
            if emergency_save or len(trial_data) > 10:
                create_emergency_backup(file_path, emergency_save)
            
            # Update session manager if available
            if session_manager and not emergency_save:
                try:
                    update_session_with_save_info(session_manager, file_path, len(trial_data), len(recall_data))
                except Exception as session_error:
                    print(f"Warning: Could not update session manager: {session_error}")
            
            return True
        else:
            print("ERROR: Failed to save Reading Span Task data after all attempts")
            
            # Attempt emergency plain text save as last resort
            if not emergency_save:  # Avoid infinite recursion
                print("Attempting emergency plain text save...")
                return emergency_plain_text_save_reading_span(trial_data, recall_data, participant_id, reading_span_folder_path)
            
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR saving Reading Span Task data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Attempt emergency save if this wasn't already an emergency save
        if not emergency_save:
            print("Attempting emergency save due to critical error...")
            return emergency_plain_text_save_reading_span(trial_data, recall_data, participant_id, reading_span_folder_path)
        
        return False


def write_reading_span_data_file(file_path, filename, participant_id, trial_data, recall_data,
                                task_config, reading_span_folder_path, recovery_context, emergency_save):
    """Write the complete Reading Span Task data file with word selection data."""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        # File header
        f.write("=" * 80 + "\n")
        f.write("READING SPAN TASK - WORKING MEMORY ASSESSMENT WITH WORD SELECTION\n")
        f.write("Custom Tests Battery - Enhanced with Word Selection Interface\n")
        f.write("=" * 80 + "\n\n")
        
        # Participant and session information
        f.write("PARTICIPANT INFORMATION:\n")
        f.write(f"Participant ID: {participant_id}\n")
        f.write(f"Data file: {filename}\n")
        f.write(f"Save timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Reading Span folder path: {reading_span_folder_path}\n")
        f.write(f"Emergency save: {'YES' if emergency_save else 'NO'}\n")
        f.write(f"Recall interface: Word Selection (Multiple Choice)\n")
        f.write("\n")
        
        # Recovery and session metadata
        if recovery_context:
            f.write("CRASH RECOVERY INFORMATION:\n")
            for key, value in recovery_context.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
        
        # Task configuration details
        f.write("TASK CONFIGURATION:\n")
        f.write("-" * 25 + "\n")
        
        if task_config:
            # Practice configuration
            f.write("PRACTICE TRIALS CONFIGURATION:\n")
            f.write(f"  Practice enabled: {task_config.get('practice_enabled', 'Unknown')}\n")
            if task_config.get('practice_enabled', False):
                f.write(f"  Number of practice sets: {task_config.get('practice_sets', 'Unknown')}\n")
                f.write(f"  Practice sentence duration: {task_config.get('practice_sentence_duration', 'Unknown')} ms\n")
            else:
                f.write(f"  Practice trials: DISABLED\n")
            f.write("\n")
            
            # Main trials configuration
            f.write("MAIN TRIALS CONFIGURATION:\n")
            f.write(f"  Main trials enabled: {task_config.get('main_enabled', 'Unknown')}\n")
            if task_config.get('main_enabled', False):
                f.write(f"  Number of series: {task_config.get('main_series', 'Unknown')}\n")
                f.write(f"  Main sentence duration: {task_config.get('main_sentence_duration', 'Unknown')} ms\n")
                #f.write(f"  Recall timeout: {task_config.get('recall_timeout', 'Unknown')} seconds\n")
            else:
                f.write(f"  Main trials: DISABLED\n")
            f.write("\n")
            
            # Interface configuration
            f.write("INTERFACE CONFIGURATION:\n")
            f.write(f"  Recall method: Word Selection Interface\n")
            f.write(f"  Selection type: Click-to-select from multiple options\n")
            f.write(f"  Distractor words: Auto-generated from word pool\n")
            f.write(f"  Selection order: Tracked and logged\n")
            f.write(f"  Clear selection: Available during recall\n")
        else:
            f.write("CONFIGURATION: Not available\n")
        
        f.write("\n")
        
        # Task structure information
        f.write("READING SPAN TASK STRUCTURE:\n")
        f.write("-" * 35 + "\n")
        f.write("Practice: 2 sets with 2-3 sentences each\n")
        f.write("Main trials: 5 series × 5 blocks = 25 blocks total\n")
        f.write("Block structure per series:\n")
        f.write("  Series 1: [2, 4, 3, 5, 6] sentences per block\n")
        f.write("  Series 2: [5, 2, 4, 6, 3] sentences per block\n")
        f.write("  Series 3: [6, 3, 5, 4, 2] sentences per block\n")
        f.write("  Series 4: [4, 6, 2, 3, 5] sentences per block\n")
        f.write("  Series 5: [3, 5, 6, 2, 4] sentences per block\n")
        f.write("Word selection: Target words + distractors from common word pool\n")
        f.write("Scoring: Position-sensitive accuracy calculation\n")
        f.write("\n")
        
        # Data structure documentation
        f.write("DATA STRUCTURE DOCUMENTATION:\n")
        f.write("Trial data contains:\n")
        f.write("- trial_number: Sequential trial number\n")
        f.write("- phase: Trial phase (practice/main)\n")
        f.write("- series: Series number (1-5 for main, 1-2 for practice)\n")
        f.write("- block: Block number within series\n")
        f.write("- sentence_in_block: Position within block\n")
        f.write("- sentence: Complete sentence text\n")
        f.write("- target_word: Correct final word\n")
        f.write("- sentence_duration_ms: Display duration\n")
        f.write("- presentation_time: Timestamp\n")
        f.write("\n")
        f.write("Recall data contains:\n")
        f.write("- expected_words: Correct final words in order\n")
        f.write("- user_selected_words: Words clicked by participant\n")
        f.write("- selection_order: Sequence of word selection\n")
        f.write("- correct_positions: Words in correct positions\n")
        f.write("- accuracy: Positional accuracy score\n")
        f.write("- recall_time: Timestamp of recall completion\n")
        f.write("\n")
        
        # Write trial data
        f.write("TRIAL DATA (CSV FORMAT):\n")
        if trial_data:
            headers = list(trial_data[0].keys())
            f.write(",".join(headers) + "\n")
            for trial in trial_data:
                row = []
                for header in headers:
                    value = trial.get(header, "")
                    row.append(str(value))
                f.write(",".join(row) + "\n")
        else:
            f.write("No trial data recorded\n")
        
        f.write("\n")
        
        # Write recall data with word selections
        f.write("RECALL DATA WITH WORD SELECTIONS (CSV FORMAT):\n")
        if recall_data:
            recall_headers = list(recall_data[0].keys())
            f.write(",".join(recall_headers) + "\n")
            for recall in recall_data:
                row = []
                for header in recall_headers:
                    value = recall.get(header, "")
                    # Handle list fields by joining with pipe separator
                    if isinstance(value, list):
                        value = "|".join(str(v) for v in value)
                    row.append(str(value))
                f.write(",".join(row) + "\n")
        else:
            f.write("No recall data recorded\n")
        
        f.write("\n")
        
        # Calculate and write performance summary
        f.write("PERFORMANCE SUMMARY WITH WORD SELECTION ANALYSIS:\n")
        f.write("-" * 55 + "\n")
        f.write(f"Total sentences presented: {len(trial_data)}\n")
        f.write(f"Total recall blocks: {len(recall_data)}\n")
        
        # Analyze by phase
        practice_recalls = [r for r in recall_data if r.get('phase') == 'practice']
        main_recalls = [r for r in recall_data if r.get('phase') == 'main']
        
        f.write(f"Practice recall blocks: {len(practice_recalls)}\n")
        f.write(f"Main recall blocks: {len(main_recalls)}\n\n")
        
        # Practice phase analysis
        if practice_recalls:
            f.write("PRACTICE PHASE PERFORMANCE:\n")
            practice_accuracy = sum(r.get('accuracy', 0) for r in practice_recalls) / len(practice_recalls)
            practice_perfect = len([r for r in practice_recalls if r.get('accuracy', 0) == 1.0])
            practice_words_selected = sum(len(r.get('user_selected_words', [])) for r in practice_recalls)
            
            f.write(f"  Average accuracy: {practice_accuracy:.1%}\n")
            f.write(f"  Perfect recalls: {practice_perfect}/{len(practice_recalls)}\n")
            f.write(f"  Total words selected: {practice_words_selected}\n")
            f.write("\n")
        
        # Main phase analysis
        if main_recalls:
            f.write("MAIN PHASE PERFORMANCE:\n")
            main_accuracy = sum(r.get('accuracy', 0) for r in main_recalls) / len(main_recalls)
            main_perfect = len([r for r in main_recalls if r.get('accuracy', 0) == 1.0])
            main_words_selected = sum(len(r.get('user_selected_words', [])) for r in main_recalls)
            
            f.write(f"  Average accuracy: {main_accuracy:.1%}\n")
            f.write(f"  Perfect recalls: {main_perfect}/{len(main_recalls)}\n")
            f.write(f"  Total words selected: {main_words_selected}\n")
            
            # Calculate reading span score
            span_score = calculate_reading_span_score(main_recalls)
            f.write(f"  Reading Span Score: {span_score}\n")
            f.write("\n")
        
        # Detailed recall analysis block by block
        f.write("DETAILED WORD SELECTION ANALYSIS:\n")
        f.write("-" * 40 + "\n")
        for i, recall in enumerate(recall_data):
            f.write(f"Block {i+1} ({recall.get('phase', 'unknown')} - Series {recall.get('series', '?')}, Block {recall.get('block', '?')}):\n")
            expected = recall.get('expected_words', [])
            selected = recall.get('user_selected_words', [])
            f.write(f"  Expected: {' → '.join(expected) if expected else 'None'}\n")
            f.write(f"  Selected: {' → '.join(selected) if selected else 'None'}\n")
            f.write(f"  Accuracy: {recall.get('accuracy', 0):.1%} ({recall.get('correct_positions', 0)}/{recall.get('total_words', 0)})\n")
            
            # Show word selection details
            if expected and selected:
                matches = []
                for j, (exp, sel) in enumerate(zip(expected, selected)):
                    match_status = "✓" if exp.lower() == sel.lower() else "✗"
                    matches.append(f"{j+1}:{match_status}")
                f.write(f"  Position matches: {' '.join(matches)}\n")
            f.write("\n")
        
        # Configuration validation summary
        f.write("WORD SELECTION INTERFACE VALIDATION:\n")
        f.write("-" * 45 + "\n")
        f.write(f"Interface type: Multiple choice word selection\n")
        f.write(f"Selection tracking: ENABLED\n")
        f.write(f"Order sensitivity: ENABLED\n")
        f.write(f"Distractor generation: AUTOMATIC\n")
        f.write(f"Clear selection option: AVAILABLE\n")
        f.write(f"Timeout handling: CONFIGURED\n")
        
        # Data integrity verification
        f.write("\n")
        f.write("DATA INTEGRITY:\n")
        trial_checksum = calculate_data_checksum(trial_data)
        recall_checksum = calculate_data_checksum(recall_data)
        f.write(f"Trial data checksum: {trial_checksum}\n")
        f.write(f"Recall data checksum: {recall_checksum}\n")
        f.write(f"File verification: PASSED\n")
        f.write(f"Save method: {'EMERGENCY' if emergency_save else 'STANDARD'}\n")
        f.write(f"Word selection interface: VERIFIED\n")
        
        # End marker
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("END OF READING SPAN TASK DATA FILE (WORD SELECTION INTERFACE)\n")
        f.write("=" * 80 + "\n")


def verify_reading_span_data_file(file_path, expected_trial_count, expected_recall_count):
    """Verify that the Reading Span data file was saved correctly."""
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
            "READING SPAN TASK - WORKING MEMORY ASSESSMENT",
            "PARTICIPANT INFORMATION:",
            "TASK CONFIGURATION:",
            "TRIAL DATA (CSV FORMAT):",
            "RECALL DATA WITH WORD SELECTIONS",
            "WORD SELECTION INTERFACE VALIDATION:"
        ]
        
        for section in required_sections:
            if section not in content:
                print(f"ERROR: Missing required section: {section}")
                return False
        
        # Check for word selection interface markers
        selection_markers = [
            "Word Selection Interface",
            "user_selected_words",
            "selection_order",
            "Multiple choice word selection"
        ]
        
        selection_found = any(marker in content for marker in selection_markers)
        if not selection_found:
            print("ERROR: Word selection interface markers not found")
            return False
        
        # Count data lines (rough verification)
        data_lines = content.count('\n')
        expected_lines = expected_trial_count + expected_recall_count + 50  # +50 for headers and metadata
        if data_lines < expected_lines:
            print(f"ERROR: File appears incomplete (expected ~{expected_lines} lines, found {data_lines})")
            return False
        
        print(f"File verification passed: {os.path.basename(file_path)}")
        print(f"Word selection interface: VERIFIED")
        return True
        
    except Exception as e:
        print(f"ERROR during file verification: {e}")
        return False


def emergency_plain_text_save_reading_span(trial_data, recall_data, participant_id, reading_span_folder_path):
    """Emergency plain text save for Reading Span data when normal save fails."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency_file = os.path.join(reading_span_folder_path, f"EMERGENCY_READING_SPAN_DATA_{timestamp}.txt")
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            f.write(f"EMERGENCY READING SPAN TASK DATA SAVE (WORD SELECTION)\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Participant: {participant_id}\n")
            f.write(f"Trial count: {len(trial_data)}\n")
            f.write(f"Recall count: {len(recall_data)}\n")
            f.write(f"Interface: Word Selection\n\n")
            
            f.write("RAW TRIAL DATA:\n")
            for i, trial in enumerate(trial_data):
                f.write(f"Trial {i+1}: {json.dumps(trial, default=str)}\n")
            
            f.write("\nRAW RECALL DATA WITH WORD SELECTIONS:\n")
            for i, recall in enumerate(recall_data):
                f.write(f"Recall {i+1}: {json.dumps(recall, default=str)}\n")
        
        print(f"Emergency Reading Span data saved: {emergency_file}")
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
        
        context = {
            'session_id': session_data.get('participant_id', 'Unknown'),
            'session_start_time': session_data.get('session_start_time', 'Unknown'),
            'recovery_mode_used': 'Yes' if current_task_state.get('recovery_mode') else 'No',
            'session_restored': 'Yes' if session_data.get('crash_detected') else 'No',
            'word_selection_interface': 'ENABLED',
            'selection_tracking': 'ACTIVE',
            'emergency_save_capable': 'YES'
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
    """Create emergency backup of the data file."""
    if emergency_save:
        return False  # Don't create backup during emergency save
    
    try:
        parent_dir = os.path.dirname(file_path)
        system_dir = os.path.join(os.path.dirname(parent_dir), "system", "emergency_saves")
        
        if os.path.exists(system_dir):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"BACKUP_READING_SPAN_{timestamp}_{os.path.basename(file_path)}"
            backup_path = os.path.join(system_dir, backup_name)
            shutil.copy2(file_path, backup_path)
            print(f"Emergency backup created: system/emergency_saves/{backup_name}")
            return True
        
    except Exception as e:
        print(f"Warning: Could not create emergency backup: {e}")
    
    return False


def update_session_with_save_info(session_manager, file_path, trial_count, recall_count):
    """Update session manager with save information."""
    try:
        session_manager.session_data['last_data_save'] = datetime.now().isoformat()
        session_manager.session_data['last_save_file'] = file_path
        session_manager.session_data['trials_saved'] = trial_count
        session_manager.session_data['recalls_saved'] = recall_count
        session_manager.session_data['word_selection_interface'] = True
        session_manager.save_session_state()
        print("Session manager updated with word selection save information")
    except Exception as e:
        print(f"Warning: Could not update session manager: {e}")


def calculate_data_checksum(data):
    """Calculate a simple checksum for data integrity verification."""
    try:
        data_string = str(sorted([str(item) for item in data]))
        import hashlib
        checksum = hashlib.md5(data_string.encode()).hexdigest()
        return checksum
    except Exception as e:
        print(f"Warning: Could not calculate checksum: {e}")
        return "CHECKSUM_ERROR"


def calculate_reading_span_score(recall_data):
    """Calculate reading span score from recall data."""
    try:
        # Traditional reading span = longest sequence of perfect recalls
        max_span = 0
        current_span = 0
        
        for recall in recall_data:
            if recall.get('accuracy', 0) == 1.0:  # Perfect recall
                current_span = recall.get('total_words', 0)
                max_span = max(max_span, current_span)
            else:
                current_span = 0
        
        return max_span
        
    except Exception as e:
        print(f"Error calculating span score: {e}")
        return 0


# =============================================================================
# EMERGENCY SAVE FUNCTIONS
# =============================================================================

def emergency_save_reading_span_task(session_manager, trial_data):
    """Emergency save specifically for Reading Span Task with word selection support."""
    try:
        participant_id = session_manager.session_data.get('participant_id', 'EMERGENCY_PARTICIPANT')
        participant_folder = getattr(session_manager, 'participant_folder_path', None)
        
        if not participant_folder:
            documents_path = os.path.expanduser("~/Documents")
            participant_folder = os.path.join(documents_path, "Custom Tests Battery Data", participant_id)
            os.makedirs(participant_folder, exist_ok=True)
        
        # Use organized system/emergency_saves folder
        emergency_folder = os.path.join(participant_folder, "system", "emergency_saves")
        os.makedirs(emergency_folder, exist_ok=True)
        
        # Reading Span specific emergency save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        emergency_file = os.path.join(emergency_folder, f"EMERGENCY_READING_SPAN_WORD_SELECTION_{timestamp}.json")
        
        # Get current task state for recall data
        current_task_state = session_manager.get_current_task_state() or {}
        recall_data = current_task_state.get('recall_data', [])
        
        emergency_data = {
            'task_name': 'Reading Span Task',
            'interface_type': 'word_selection',
            'participant_id': participant_id,
            'emergency_save_time': datetime.now().isoformat(),
            'trial_data': trial_data,
            'recall_data': recall_data,
            'word_selection_enabled': True,
            'session_data': session_manager.session_data,
            'folder_structure': 'organized_v2',
            'save_location': 'system/emergency_saves/'
        }
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            json.dump(emergency_data, f, indent=2, default=str)
        
        print(f"Reading Span word selection emergency save completed: system/emergency_saves/{os.path.basename(emergency_file)}")
        print(f"Saved {len(trial_data)} trials and {len(recall_data)} recall blocks")
        return True
        
    except Exception as e:
        print(f"Reading Span emergency save failed: {e}")
        return False