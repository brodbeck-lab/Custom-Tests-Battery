"""
Modular data saver for Speeded Classification Task
Handles all data saving operations with organized folder structure and comprehensive logging.

Author: Behavioral Research Lab
Version: 2.0
"""

import os
import json
import csv
import pandas as pd
from datetime import datetime

def save_speeded_classification_data(trial_data, participant_id, task_folder_path, task_config):
    """
    Save Speeded Classification task data to organized folder structure.
    
    Parameters:
    -----------
    trial_data : list
        List of trial dictionaries containing all trial information
    participant_id : str
        Participant identifier
    task_folder_path : str
        Path to the task-specific folder
    task_config : dict
        Task configuration parameters
        
    Returns:
    --------
    bool
        True if save was successful, False otherwise
    """
    try:
        print(f"=== SAVING SPEEDED CLASSIFICATION DATA ===")
        print(f"Participant: {participant_id}")
        print(f"Task folder: {task_folder_path}")
        print(f"Total trials: {len(trial_data)}")
        
        # Ensure task folder exists
        os.makedirs(task_folder_path, exist_ok=True)
        
        # Generate timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive trial data as TXT
        txt_success = save_trial_data_txt(trial_data, task_folder_path, participant_id, timestamp)
        
        # Save task configuration
        config_success = save_task_configuration(task_config, task_folder_path, participant_id, timestamp)
        
        # Save performance summary
        summary_success = save_performance_summary(trial_data, task_folder_path, participant_id, timestamp, task_config)
        
        # Save raw data as JSON backup
        json_success = save_raw_data_json(trial_data, task_config, task_folder_path, participant_id, timestamp)
        
        # Create analysis-ready data file
        analysis_success = save_analysis_ready_data(trial_data, task_folder_path, participant_id, timestamp)
        
        # All saves must succeed
        overall_success = all([txt_success, config_success, summary_success, json_success, analysis_success])
        
        if overall_success:
            print("✓ All Speeded Classification data files saved successfully")
            print(f"✓ Data location: {task_folder_path}")
        else:
            print("✗ Some data files failed to save")
        
        return overall_success
        
    except Exception as e:
        print(f"Critical error in Speeded Classification data saving: {e}")
        return False

def save_trial_data_txt(trial_data, task_folder_path, participant_id, timestamp):
    """Save detailed trial data as TXT file"""
    try:
        txt_filename = f"speeded_classification_trials_{timestamp}.txt"
        txt_path = os.path.join(task_folder_path, txt_filename)
        
        if not trial_data:
            print("Warning: No trial data to save")
            return True
        
        # Write detailed trial data to TXT file
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("SPEEDED CLASSIFICATION TASK - DETAILED TRIAL DATA\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Participant ID: {participant_id}\n")
            f.write(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Trials: {len(trial_data)}\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("TRIAL DATA FORMAT:\n")
            f.write("Trial | Phase | Stimulus | Correct | Response | Accuracy | RT(ms) | Timestamp\n")
            f.write("-" * 80 + "\n\n")
            
            # Write each trial
            for i, trial in enumerate(trial_data, 1):
                stimulus_name = trial.get('stimulus_file', 'unknown')
                if stimulus_name != 'unknown':
                    stimulus_name = os.path.basename(stimulus_name)
                
                phase = trial.get('phase', '')
                correct_resp = trial.get('correct_response', '')
                participant_resp = trial.get('response', '')
                accuracy = "CORRECT" if trial.get('is_correct', False) else "INCORRECT"
                rt = trial.get('reaction_time_ms', 0)
                timestamp = trial.get('timestamp', '')
                
                # Format the line for readability
                f.write(f"{i:5d} | {phase:15s} | {stimulus_name:12s} | {correct_resp:7s} | {participant_resp:8s} | {accuracy:8s} | {rt:6.1f} | {timestamp}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("DETAILED TRIAL BREAKDOWN:\n")
            f.write("-" * 40 + "\n\n")
            
            # Write detailed breakdown for each trial
            for i, trial in enumerate(trial_data, 1):
                f.write(f"TRIAL {i}:\n")
                f.write(f"  Participant ID: {trial.get('participant_id', '')}\n")
                f.write(f"  Phase: {trial.get('phase', '')}\n")
                f.write(f"  Trial Number: {trial.get('trial_number', i)}\n")
                f.write(f"  Stimulus File: {trial.get('stimulus_file', '')}\n")
                f.write(f"  Stimulus Type: {classify_stimulus_type(trial.get('stimulus_file', ''))}\n")
                f.write(f"  Correct Response: {trial.get('correct_response', '')}\n")
                f.write(f"  Participant Response: {trial.get('response', '')}\n")
                f.write(f"  Accuracy: {'CORRECT' if trial.get('is_correct', False) else 'INCORRECT'}\n")
                f.write(f"  Reaction Time: {trial.get('reaction_time_ms', 0):.2f} ms\n")
                f.write(f"  Stimulus Onset: {trial.get('stimulus_onset_time', '')}\n")
                f.write(f"  Response Time: {trial.get('timestamp', '')}\n")
                f.write(f"  Block Type: {'Practice' if 'practice' in trial.get('phase', '') else 'Main'}\n")
                f.write(f"  Valid Response: {'Yes' if trial.get('reaction_time_ms', 10000) < 10000 else 'No'}\n")
                f.write("\n")
            
            f.write("=" * 60 + "\n")
            f.write(f"Data export completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"✓ Trial data TXT saved: {txt_filename}")
        return True
        
    except Exception as e:
        print(f"Error saving trial data TXT: {e}")
        return False

def save_task_configuration(task_config, task_folder_path, participant_id, timestamp):
    """Save task configuration parameters"""
    try:
        config_filename = f"speeded_classification_config_{timestamp}.json"
        config_path = os.path.join(task_folder_path, config_filename)
        
        # Create comprehensive configuration record
        full_config = {
            'participant_id': participant_id,
            'task_name': 'Speeded Classification Task',
            'task_version': '2.0',
            'save_timestamp': datetime.now().isoformat(),
            'configuration_parameters': task_config,
            'data_structure_version': '2.0',
            'file_format': 'JSON',
            'notes': 'Comprehensive task configuration with all user-selected parameters'
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(full_config, f, indent=2, default=str)
        
        print(f"✓ Configuration saved: {config_filename}")
        return True
        
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

def save_performance_summary(trial_data, task_folder_path, participant_id, timestamp, task_config):
    """Save human-readable performance summary"""
    try:
        summary_filename = f"speeded_classification_summary_{timestamp}.txt"
        summary_path = os.path.join(task_folder_path, summary_filename)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("SPEEDED CLASSIFICATION TASK - PERFORMANCE SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Participant ID: {participant_id}\n")
            f.write(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Task Version: 2.0\n\n")
            
            # Task Configuration Summary
            f.write("TASK CONFIGURATION:\n")
            f.write("-" * 30 + "\n")
            if task_config:
                f.write(f"Practice Phoneme Trials: {task_config.get('practice_phoneme_trials', 'N/A')}\n")
                f.write(f"Practice Voice Trials: {task_config.get('practice_voice_trials', 'N/A')}\n")
                f.write(f"Main Phoneme Trials: {task_config.get('main_phoneme_trials', 'N/A')}\n")
                f.write(f"Main Voice Trials: {task_config.get('main_voice_trials', 'N/A')}\n")
                f.write(f"Inter-trial Interval: {task_config.get('iti_duration_ms', 'N/A')} ms\n")
                f.write(f"Audio Volume: {task_config.get('audio_volume', 'N/A')}\n")
            f.write("\n")
            
            if not trial_data:
                f.write("No trial data available.\n")
                return True
            
            # Performance Analysis by Phase
            phases = ['practice_phoneme', 'practice_voice', 'main_phoneme', 'main_voice']
            phase_names = ['Practice Phoneme (B/P)', 'Practice Voice (M/F)', 
                          'Main Phoneme (B/P)', 'Main Voice (M/F)']
            
            f.write("PERFORMANCE BY PHASE:\n")
            f.write("-" * 30 + "\n")
            
            overall_stats = {
                'total_trials': len(trial_data),
                'total_correct': sum(1 for t in trial_data if t.get('is_correct', False)),
                'total_responses': len([t for t in trial_data if t.get('response', '') != 'NO_RESPONSE']),
                'overall_rt': []
            }
            
            for phase, phase_name in zip(phases, phase_names):
                phase_trials = [t for t in trial_data if t.get('phase') == phase]
                
                if phase_trials:
                    correct_trials = [t for t in phase_trials if t.get('is_correct', False)]
                    response_trials = [t for t in phase_trials if t.get('response', '') != 'NO_RESPONSE']
                    
                    accuracy = len(correct_trials) / len(phase_trials) * 100 if phase_trials else 0
                    response_rate = len(response_trials) / len(phase_trials) * 100 if phase_trials else 0
                    
                    # Calculate RT statistics for responded trials only
                    rt_data = [t['reaction_time_ms'] for t in response_trials if t.get('reaction_time_ms', 0) < 10000]
                    overall_stats['overall_rt'].extend(rt_data)
                    
                    f.write(f"{phase_name}:\n")
                    f.write(f"  Total Trials: {len(phase_trials)}\n")
                    f.write(f"  Accuracy: {accuracy:.1f}% ({len(correct_trials)}/{len(phase_trials)})\n")
                    f.write(f"  Response Rate: {response_rate:.1f}%\n")
                    
                    if rt_data:
                        f.write(f"  Average RT: {sum(rt_data)/len(rt_data):.0f} ms\n")
                        f.write(f"  Median RT: {sorted(rt_data)[len(rt_data)//2]:.0f} ms\n")
                        f.write(f"  RT Range: {min(rt_data):.0f} - {max(rt_data):.0f} ms\n")
                    f.write("\n")
            
            # Overall Statistics
            f.write("OVERALL PERFORMANCE:\n")
            f.write("-" * 30 + "\n")
            overall_accuracy = overall_stats['total_correct'] / overall_stats['total_trials'] * 100 if overall_stats['total_trials'] > 0 else 0
            overall_response_rate = overall_stats['total_responses'] / overall_stats['total_trials'] * 100 if overall_stats['total_trials'] > 0 else 0
            
            f.write(f"Total Trials Completed: {overall_stats['total_trials']}\n")
            f.write(f"Overall Accuracy: {overall_accuracy:.1f}%\n")
            f.write(f"Overall Response Rate: {overall_response_rate:.1f}%\n")
            
            if overall_stats['overall_rt']:
                f.write(f"Overall Average RT: {sum(overall_stats['overall_rt'])/len(overall_stats['overall_rt']):.0f} ms\n")
            
            # Error Analysis
            f.write("\nERROR ANALYSIS:\n")
            f.write("-" * 30 + "\n")
            
            incorrect_trials = [t for t in trial_data if not t.get('is_correct', False) and t.get('response', '') != 'NO_RESPONSE']
            no_response_trials = [t for t in trial_data if t.get('response', '') == 'NO_RESPONSE']
            
            f.write(f"Incorrect Responses: {len(incorrect_trials)}\n")
            f.write(f"No Response Trials: {len(no_response_trials)}\n")
            
            if incorrect_trials:
                f.write("\nMost Common Errors:\n")
                error_types = {}
                for trial in incorrect_trials:
                    error_key = f"{trial.get('correct_response', 'Unknown')} → {trial.get('response', 'Unknown')}"
                    error_types[error_key] = error_types.get(error_key, 0) + 1
                
                sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
                for error, count in sorted_errors[:5]:  # Top 5 errors
                    f.write(f"  {error}: {count} times\n")
            
            f.write(f"\n{'=' * 60}\n")
            f.write(f"Summary generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"✓ Performance summary saved: {summary_filename}")
        return True
        
    except Exception as e:
        print(f"Error saving performance summary: {e}")
        return False

def save_raw_data_json(trial_data, task_config, task_folder_path, participant_id, timestamp):
    """Save raw data as JSON backup"""
    try:
        json_filename = f"speeded_classification_raw_{timestamp}.json"
        json_path = os.path.join(task_folder_path, json_filename)
        
        raw_data = {
            'metadata': {
                'participant_id': participant_id,
                'task_name': 'Speeded Classification Task',
                'task_version': '2.0',
                'save_timestamp': datetime.now().isoformat(),
                'total_trials': len(trial_data),
                'data_format': 'Raw JSON backup'
            },
            'task_configuration': task_config,
            'trial_data': trial_data
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, default=str)
        
        print(f"✓ Raw data JSON saved: {json_filename}")
        return True
        
    except Exception as e:
        print(f"Error saving raw JSON data: {e}")
        return False

def save_analysis_ready_data(trial_data, task_folder_path, participant_id, timestamp):
    """Save analysis-ready data in multiple formats"""
    try:
        # Save as analysis-ready CSV with computed variables
        analysis_filename = f"speeded_classification_analysis_{timestamp}.csv"
        analysis_path = os.path.join(task_folder_path, analysis_filename)
        
        if not trial_data:
            return True
        
        # Prepare data with additional analysis variables
        analysis_data = []
        for i, trial in enumerate(trial_data):
            analysis_trial = {
                'participant': participant_id,
                'trial_id': i + 1,
                'phase': trial.get('phase', ''),
                'block_type': 'practice' if 'practice' in trial.get('phase', '') else 'main',
                'task_type': 'phoneme' if 'phoneme' in trial.get('phase', '') else 'voice',
                'stimulus': os.path.basename(trial.get('stimulus_file', '')),
                'stimulus_category': classify_stimulus_type(trial.get('stimulus_file', '')),
                'correct_answer': trial.get('correct_response', ''),
                'participant_answer': trial.get('response', ''),
                'accuracy': 1 if trial.get('is_correct', False) else 0,
                'response_given': 1 if trial.get('response', '') != 'NO_RESPONSE' else 0,
                'reaction_time': trial.get('reaction_time_ms', ''),
                'rt_valid': 1 if trial.get('reaction_time_ms', 10000) < 10000 else 0,
                'timestamp': trial.get('timestamp', ''),
                'trial_in_phase': trial.get('trial_number', '')
            }
            analysis_data.append(analysis_trial)
        
        # Create DataFrame and save
        df = pd.DataFrame(analysis_data)
        df.to_csv(analysis_path, index=False)
        
        print(f"✓ Analysis-ready data saved: {analysis_filename}")
        return True
        
    except Exception as e:
        print(f"Error saving analysis-ready data: {e}")
        return False

def classify_stimulus_type(stimulus_file):
    """Classify stimulus based on filename"""
    if not stimulus_file:
        return 'unknown'
    
    filename = os.path.basename(stimulus_file)
    
    # Extract phoneme (B or P)
    phoneme = 'B' if filename.startswith('baab') else 'P' if filename.startswith('paab') else 'unknown'
    
    # Extract gender (M or F) - handles M1, M2, F1, F2
    if 'M' in filename:
        gender = 'M'
    elif 'F' in filename:
        gender = 'F'
    else:
        gender = 'unknown'
    
    return f"{phoneme}_{gender}"

def emergency_save_speeded_classification_task(session_manager, trial_data):
    """
    Emergency save function for Speeded Classification task.
    Called by crash recovery system.
    
    Parameters:
    -----------
    session_manager : SessionManager
        The session manager instance
    trial_data : list
        Current trial data to save
        
    Returns:
    --------
    bool
        True if emergency save was successful
    """
    try:
        participant_id = session_manager.session_data.get('participant_id', 'EMERGENCY_PARTICIPANT')
        participant_folder = getattr(session_manager, 'participant_folder_path', None)
        
        if not participant_folder:
            # Create emergency folder
            documents_path = os.path.expanduser("~/Documents")
            participant_folder = os.path.join(documents_path, "Custom Tests Battery Data", participant_id)
            os.makedirs(participant_folder, exist_ok=True)
        
        # Create emergency saves folder
        emergency_folder = os.path.join(participant_folder, "system", "emergency_saves")
        os.makedirs(emergency_folder, exist_ok=True)
        
        # Emergency save with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        emergency_file = os.path.join(emergency_folder, f"EMERGENCY_speeded_classification_{timestamp}.json")
        
        # Get current task state from session manager
        current_task_state = session_manager.session_data.get('current_task_state', {})
        task_specific_state = current_task_state.get('task_specific_state', {})
        
        emergency_data = {
            'task_name': 'Speeded Classification Task',
            'participant_id': participant_id,
            'emergency_save_time': datetime.now().isoformat(),
            'trial_data': trial_data,
            'task_state': task_specific_state,
            'session_data': session_manager.session_data,
            'recovery_instructions': 'This is an emergency save from Speeded Classification Task crash',
            'folder_structure': 'organized_v2'
        }
        
        with open(emergency_file, 'w', encoding='utf-8') as f:
            json.dump(emergency_data, f, indent=2, default=str)
        
        print(f"Emergency save completed: {os.path.basename(emergency_file)}")
        return True
        
    except Exception as e:
        print(f"Emergency save failed for Speeded Classification task: {e}")
        return False

# Export the emergency save function for the crash handler
__all__ = ['save_speeded_classification_data', 'emergency_save_speeded_classification_task']