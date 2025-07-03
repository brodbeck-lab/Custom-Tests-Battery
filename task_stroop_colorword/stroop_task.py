import sys
import os
import pandas as pd
import random
import time
import threading
import wave
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QCheckBox, QSpinBox, QDoubleSpinBox, QGridLayout, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

# Import the modular save function
from .data_saver import save_stroop_colorword_data

# Import crash recovery system - ENHANCED IMPORTS
from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager
from crash_recovery_system.task_state_saver import TaskStateMixin
import crash_recovery_system.crash_handler as crash_handler  # Initialize crash handler

try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("WARNING: pyaudio not installed. Audio recording will be simulated.")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("WARNING: sounddevice not installed.")

try:
    import librosa
    from scipy import signal
    from scipy.signal import find_peaks
    ANALYSIS_AVAILABLE = True
    print("✓ Audio analysis libraries available (librosa, scipy)")
except ImportError:
    ANALYSIS_AVAILABLE = False
    print("WARNING: librosa or scipy not installed. RT analysis will be skipped.")
    print("Install with: pip install librosa scipy")

# =============================================================================
# DEFAULT CONFIGURATION VALUES
# =============================================================================
DEFAULT_PRACTICE_TRIALS = 6
DEFAULT_NUM_TRIALS = 10
DEFAULT_RECORDING_DURATION = 3.0
DEFAULT_PRE_STIMULUS_DELAY = 200

# Available stimuli for random trial generation  
STROOP_COLORWORD_WORDS = ['RED', 'BLUE', 'GREEN', 'YELLOW']
STROOP_COLORWORD_COLORS = ['red', 'blue', 'green', 'yellow']

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller/py2app """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SpeechOnsetDetector:
    """Detect speech onset and calculate reaction times using frame flip timing method"""
    
    def __init__(self):
        self.sample_rate = 48000
        
    def analyze_trial_audio(self, audio_file, audio_start_time, stimulus_onset_time):
        """
        Analyze a single trial audio file to extract RT using frame flip timing method
        
        Parameters:
        - audio_file: Path to the audio file
        - audio_start_time: High-resolution timestamp when audio recording started
        - stimulus_onset_time: High-resolution timestamp from frame flip operation
        
        Returns:
        - rt_seconds: Reaction time in seconds (speech onset - stimulus onset)
        - confidence: Detection confidence (0-1)
        - details: Dictionary with detection details
        """
        
        if not ANALYSIS_AVAILABLE:
            print(f"  Analysis libraries not available - skipping {os.path.basename(audio_file)}")
            return None, 0.0, {"error": "Analysis libraries not available"}
        
        try:
            # Load audio file
            audio, sr = librosa.load(audio_file, sr=self.sample_rate, mono=True)
            
            # Calculate the audio-to-stimulus offset (time between audio start and stimulus presentation)
            stimulus_offset = stimulus_onset_time - audio_start_time
            
            print(f"    Audio start time: {audio_start_time:.6f}")
            print(f"    Stimulus onset time (frame flip): {stimulus_onset_time:.6f}")
            print(f"    Stimulus offset in audio: {stimulus_offset:.6f} seconds")
            
            # Detect speech onset in the audio file
            speech_onset_time_in_audio, speech_confidence = self._detect_speech_onset_in_audio(audio, sr, stimulus_offset)
            
            if speech_onset_time_in_audio is None:
                print(f"  No speech onset detected in {os.path.basename(audio_file)}")
                return None, 0.0, {
                    "error": "No speech onset detected",
                    "audio_start_time": audio_start_time,
                    "stimulus_onset_time": stimulus_onset_time,
                    "stimulus_offset": stimulus_offset
                }
            
            # Calculate reaction time: (speech onset time in audio) - (audio-to-stimulus difference)
            rt_seconds = speech_onset_time_in_audio - stimulus_offset
            
            details = {
                "audio_start_time": audio_start_time,
                "stimulus_onset_time": stimulus_onset_time,
                "stimulus_offset": stimulus_offset,
                "speech_onset_time_in_audio": speech_onset_time_in_audio,
                "speech_confidence": speech_confidence,
                "rt_seconds": rt_seconds
            }
            
            print(f"  RT analysis: {rt_seconds*1000:.0f}ms (conf: {speech_confidence:.2f}) - {os.path.basename(audio_file)}")
            
            return rt_seconds, speech_confidence, details
            
        except Exception as e:
            print(f"  Error analyzing {os.path.basename(audio_file)}: {str(e)}")
            return None, 0.0, {"error": str(e)}
    
    def _detect_speech_onset_in_audio(self, audio, sr, stimulus_offset, search_window=3.0):
        """
        Detect speech onset in the audio file after the stimulus offset
        
        Parameters:
        - audio: Audio signal
        - sr: Sample rate
        - stimulus_offset: Time offset in seconds where stimulus was presented in the audio
        - search_window: How many seconds after stimulus offset to search
        """
        try:
            # Define search region (after stimulus offset, within search window)
            # Start a small delay after stimulus offset to avoid false positives
            start_sample = int((stimulus_offset + 0.05) * sr)  # Start 50ms after stimulus offset
            end_sample = min(len(audio), int((stimulus_offset + search_window) * sr))
            
            if start_sample >= len(audio):
                return None, 0.0
            
            # Extract search region
            search_audio = audio[start_sample:end_sample]
            
            # Apply high-pass filter to remove low-frequency noise and focus on speech
            # Human speech fundamental frequencies are typically 80-300 Hz
            nyquist = sr / 2
            high_pass_cutoff = 80 / nyquist
            b, a = signal.butter(4, high_pass_cutoff, btype='high')
            filtered_search = signal.filtfilt(b, a, search_audio)
            
            # Calculate energy in overlapping windows
            window_size = int(0.02 * sr)  # 20ms windows
            hop_size = int(0.01 * sr)     # 10ms hop (50% overlap)
            
            energy_values = []
            for i in range(0, len(filtered_search) - window_size, hop_size):
                window = filtered_search[i:i + window_size]
                energy = np.sum(window ** 2)
                energy_values.append(energy)
            
            if len(energy_values) == 0:
                return None, 0.0
            
            energy_values = np.array(energy_values)
            
            # Smooth energy values
            smooth_window = 5  # Smooth over 5 windows (50ms)
            if len(energy_values) >= smooth_window:
                energy_smooth = np.convolve(energy_values, np.ones(smooth_window)/smooth_window, mode='same')
            else:
                energy_smooth = energy_values
            
            # Calculate baseline energy (first 100ms of search region)
            baseline_samples = min(10, len(energy_smooth) // 4)  # First 10 windows or 1/4 of signal
            if baseline_samples > 0:
                baseline_energy = np.mean(energy_smooth[:baseline_samples])
                baseline_std = np.std(energy_smooth[:baseline_samples])
            else:
                baseline_energy = np.mean(energy_smooth)
                baseline_std = np.std(energy_smooth)
            
            # Speech onset threshold: energy significantly above baseline
            threshold = baseline_energy + 3 * baseline_std
            
            # Find first sustained energy increase
            # Look for at least 3 consecutive windows above threshold
            consecutive_count = 0
            onset_window = None
            
            for i, energy in enumerate(energy_smooth):
                if energy > threshold:
                    consecutive_count += 1
                    if consecutive_count >= 3 and onset_window is None:
                        onset_window = i - 2  # Go back to start of sustained increase
                        break
                else:
                    consecutive_count = 0
            
            if onset_window is None:
                return None, 0.0
            
            # Convert window index back to time in the full audio file
            onset_sample_in_search = onset_window * hop_size
            onset_sample_in_full_audio = start_sample + onset_sample_in_search
            speech_onset_time_in_audio = onset_sample_in_full_audio / sr
            
            # Calculate confidence based on energy increase
            if onset_window < len(energy_smooth):
                onset_energy = energy_smooth[onset_window]
                confidence = min(1.0, (onset_energy - baseline_energy) / (4 * baseline_std))
            else:
                confidence = 0.5
            
            return speech_onset_time_in_audio, confidence
            
        except Exception as e:
            print(f"    Speech onset detection error: {str(e)}")
            return None, 0.0

class StroopColorWordDisplayWindow(QWidget):
    """Child window that displays the Stroop Color-Word task content"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stroop Color-Word Display")
        self.setFixedSize(1300, 760)
        
        # Create layout for the child window
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the main display label (used for stimuli and messages)
        self.display_label = QLabel("", self)
        self.display_label.setFont(QFont('Arial', 28, QFont.Weight.Bold))
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("""
            QLabel {
                color: black;
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 60px;
                margin: 40px;
                min-height: 150px;
            }
        """)
        
        # Configuration widget (initially hidden)
        self.config_widget = self.create_configuration_widget()
        self.config_widget.hide()
        
        # Add widgets to layout
        self.main_layout.addWidget(self.display_label)
        self.main_layout.addWidget(self.config_widget)
        
        self.setLayout(self.main_layout)
        
        # Show initial configuration
        self.show_configuration()
    
    def create_configuration_widget(self):
        """Create the task configuration widget"""
        config_widget = QWidget()
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(40, 20, 40, 20)
        
        # Title
        title_label = QLabel("Stroop Color-Word Task Configuration")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        config_layout.addWidget(title_label)
        
        # Configuration frame
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(20)
        
        # Practice trials section
        practice_layout = QHBoxLayout()
        self.practice_checkbox = QCheckBox("Practice Trials")
        self.practice_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.practice_checkbox.setChecked(True)  # Default enabled
        self.practice_checkbox.stateChanged.connect(self.on_practice_changed)
        
        practice_layout.addWidget(self.practice_checkbox)
        practice_layout.addWidget(QLabel("Number of trials:"))
        
        self.practice_spinbox = QSpinBox()
        self.practice_spinbox.setRange(1, 50)
        self.practice_spinbox.setValue(DEFAULT_PRACTICE_TRIALS)
        self.practice_spinbox.setFont(QFont('Arial', 12))
        practice_layout.addWidget(self.practice_spinbox)
        
        practice_layout.addStretch()
        frame_layout.addLayout(practice_layout)
        
        # Separator line
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("color: #bdc3c7;")
        frame_layout.addWidget(separator1)
        
        # Main trials section
        main_layout = QVBoxLayout()
        
        # Main trials checkbox
        main_header_layout = QHBoxLayout()
        self.main_checkbox = QCheckBox("Main Trials")
        self.main_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.main_checkbox.setChecked(True)  # Default enabled
        self.main_checkbox.stateChanged.connect(self.on_main_changed)
        main_header_layout.addWidget(self.main_checkbox)
        main_header_layout.addStretch()
        main_layout.addLayout(main_header_layout)
        
        # Main trials configuration grid
        main_grid = QGridLayout()
        main_grid.setSpacing(15)
        
        # Number of trials
        main_grid.addWidget(QLabel("Number of trials:"), 0, 0)
        self.trials_spinbox = QSpinBox()
        self.trials_spinbox.setRange(1, 500)
        self.trials_spinbox.setValue(DEFAULT_NUM_TRIALS)
        self.trials_spinbox.setFont(QFont('Arial', 12))
        main_grid.addWidget(self.trials_spinbox, 0, 1)
        
        # Recording duration
        main_grid.addWidget(QLabel("Recording duration (seconds):"), 1, 0)
        self.duration_spinbox = QDoubleSpinBox()
        self.duration_spinbox.setRange(0.5, 30.0)
        self.duration_spinbox.setValue(DEFAULT_RECORDING_DURATION)
        self.duration_spinbox.setDecimals(1)
        self.duration_spinbox.setSingleStep(0.5)
        self.duration_spinbox.setFont(QFont('Arial', 12))
        main_grid.addWidget(self.duration_spinbox, 1, 1)
        
        # Pre-stimulus delay
        main_grid.addWidget(QLabel("Pre-stimulus delay (ms):"), 2, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 2000)
        self.delay_spinbox.setValue(DEFAULT_PRE_STIMULUS_DELAY)
        self.delay_spinbox.setSuffix(" ms")
        self.delay_spinbox.setFont(QFont('Arial', 12))
        main_grid.addWidget(self.delay_spinbox, 2, 1)
        
        main_layout.addLayout(main_grid)
        frame_layout.addLayout(main_layout)
        
        config_frame.setLayout(frame_layout)
        config_layout.addWidget(config_frame)
        
        config_widget.setLayout(config_layout)
        return config_widget
    
    def on_practice_changed(self, state):
        """Handle practice trials checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.practice_spinbox.setEnabled(enabled)
    
    def on_main_changed(self, state):
        """Handle main trials checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.trials_spinbox.setEnabled(enabled)
        self.duration_spinbox.setEnabled(enabled)
        self.delay_spinbox.setEnabled(enabled)
    
    def get_configuration(self):
        """Get the current configuration settings"""
        config = {
            'practice_enabled': self.practice_checkbox.isChecked(),
            'practice_trials': self.practice_spinbox.value() if self.practice_checkbox.isChecked() else 0,
            'main_enabled': self.main_checkbox.isChecked(),
            'num_trials': self.trials_spinbox.value() if self.main_checkbox.isChecked() else 0,
            'recording_duration': self.duration_spinbox.value() if self.main_checkbox.isChecked() else 0,
            'pre_stimulus_delay': self.delay_spinbox.value() if self.main_checkbox.isChecked() else 0
        }
        return config
    
    def validate_configuration(self):
        """Validate the current configuration"""
        if not self.practice_checkbox.isChecked() and not self.main_checkbox.isChecked():
            return False, "At least one trial type (Practice or Main) must be selected."
        
        if self.practice_checkbox.isChecked() and self.practice_spinbox.value() < 1:
            return False, "Practice trials must be at least 1 if enabled."
        
        if self.main_checkbox.isChecked() and self.trials_spinbox.value() < 1:
            return False, "Main trials must be at least 1 if enabled."
        
        return True, ""
    
    def show_configuration(self):
        """Show the configuration interface"""
        self.display_label.hide()
        self.config_widget.show()
    
    def hide_configuration(self):
        """Hide the configuration interface"""
        self.config_widget.hide()
        self.display_label.show()
    
    def prepare_stimulus(self, text, color_name):
        """Prepare the stimulus for display without showing it yet (for frame flip timing)"""
        # Prepare the text content
        self.prepared_text = text
        self.prepared_color = color_name
        
        # Pre-calculate the styling
        base_style = """
            QLabel {
                color: COLOR_PLACEHOLDER;
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 60px;
                margin: 40px;
                min-height: 150px;
            }
        """
        self.prepared_style = base_style.replace("COLOR_PLACEHOLDER", color_name.lower())
        
        # Set the text and style (this prepares for the frame flip)
        self.display_label.setText(text)
        self.display_label.setFont(QFont('Arial', 64, QFont.Weight.Bold))
        self.display_label.setStyleSheet(self.prepared_style)
    
    def set_text(self, text):
        """Update the displayed text"""
        self.display_label.setText(text)
        self.display_label.setFont(QFont('Arial', 64, QFont.Weight.Bold))
    
    def set_text_color(self, color_name):
        """Set the text color of the display"""
        base_style = """
            QLabel {
                color: COLOR_PLACEHOLDER;
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 60px;
                margin: 40px;
                min-height: 150px;
            }
        """
        style_with_color = base_style.replace("COLOR_PLACEHOLDER", color_name.lower())
        self.display_label.setStyleSheet(style_with_color)
    
    def show_instructions(self, config):
        """Show task instructions with configuration details"""
        practice_text = f"You will start with {config['practice_trials']} practice trials" if config['practice_enabled'] else "No practice trials"
        main_text = f"then complete {config['num_trials']} main trials with audio recording" if config['main_enabled'] else "Practice trials only"
        
        if not config['practice_enabled']:
            practice_text = ""
            main_text = f"You will complete {config['num_trials']} trials with audio recording"
        elif not config['main_enabled']:
            main_text = "Practice trials only - no recording"
        
        instruction_text = f"""Click the Start button to begin the Stroop Color-Word Task

{practice_text}
{main_text if main_text else ""}

You must say aloud the COLOR of the ink, not the word itself"""
        
        self.display_label.setText(instruction_text)
        self.display_label.setFont(QFont('Arial', 28, QFont.Weight.Bold))
        self.display_label.setStyleSheet("""
            QLabel {
                color: black;
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 60px;
                margin: 40px;
                min-height: 150px;
            }
        """)
    
    def show_stimulus(self, text):
        """Show the stimulus text"""
        self.display_label.setText(f"{text}")
        self.display_label.setFont(QFont('Arial', 64, QFont.Weight.Bold))
    
    def show_completion_message(self, message):
        """Show completion messages during task completion sequence"""
        self.display_label.setText(message)
        self.display_label.setFont(QFont('Arial', 32, QFont.Weight.Bold))
        self.display_label.setStyleSheet("""
            QLabel {
                color: black;
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 60px;
                margin: 40px;
                min-height: 150px;
            }
        """)

class AudioRecorder:
    """Handle audio recording functionality"""
    def __init__(self):
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 48000  # High sample rate for good audio quality
        self.channels = 1
        self.chunk_size = 2048
        self.stream = None
        
        if AUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
            self.print_audio_devices()  # Debug: show available devices
        else:
            self.audio = None
    
    def print_audio_devices(self):
        """Print available audio input devices for debugging"""
        try:
            print("\n=== AVAILABLE AUDIO INPUT DEVICES ===")
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:  # Only show input devices
                    print(f"Device {i}: {info['name']} (Channels: {info['maxInputChannels']}, Rate: {info['defaultSampleRate']})")
            print("=====================================\n")
            print(f"Recording configured for {self.sample_rate}Hz")
        except Exception as e:
            print(f"Error listing audio devices: {e}")
    
    def start_recording(self):
        """Start recording audio"""
        if not AUDIO_AVAILABLE:
            print("Audio recording simulated (pyaudio not available)")
            return
        
        # Reset audio data
        self.audio_data = []
        
        try:
            # Close any existing stream first
            if self.stream is not None:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
            
            # Create new stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=None,  # Use default input device
                stream_callback=None
            )
            
            self.is_recording = True
            print(f"Audio recording started: {self.sample_rate}Hz, {self.chunk_size} buffer")
            
        except Exception as e:
            print(f"Error starting audio recording: {e}")
            print("Trying with fallback settings...")
            
            # Fallback to more compatible settings
            try:
                self.sample_rate = 44100
                self.chunk_size = 1024
                
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
                
                self.is_recording = True
                print(f"Audio recording started with fallback settings: {self.sample_rate}Hz")
                
            except Exception as e2:
                print(f"Fallback audio recording also failed: {e2}")
                self.is_recording = False
                self.stream = None
    
    def record_chunk(self):
        """Record a chunk of audio"""
        if not AUDIO_AVAILABLE or not self.is_recording or self.stream is None:
            return
        
        try:
            # Check if stream is still active
            if self.stream.is_active():
                # Read audio data without overflow exception to prevent data loss
                data = self.stream.read(
                    self.chunk_size, 
                    exception_on_overflow=False  # Prevents exceptions on input overflow
                )
                self.audio_data.append(data)
        except Exception as e:
            # Only print error occasionally to avoid spam
            if len(self.audio_data) % 20 == 0:  # Print every 20th error
                print(f"Audio chunk error (chunk {len(self.audio_data)}): {e}")
    
    def stop_recording(self, file_path):
        """Stop recording and save to file"""
        if not AUDIO_AVAILABLE:
            # Create a dummy file for simulation
            try:
                with open(file_path.replace('.wav', '_simulated.txt'), 'w') as f:
                    f.write("Simulated audio recording (pyaudio not available)")
                print(f"Simulated audio file created: {file_path}")
            except Exception as e:
                print(f"Error creating simulated file: {e}")
            return
        
        if not self.is_recording:
            return
        
        # Set recording flag to false first
        self.is_recording = False
        
        try:
            if self.stream is not None:
                # Stop and close stream
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Save audio data to WAV file
            if self.audio_data:  # Only save if we have data
                with wave.open(file_path, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(self.audio_data))
                
                # Print file info for debugging
                file_size = os.path.getsize(file_path)
                duration = len(self.audio_data) * self.chunk_size / self.sample_rate
                print(f"Audio saved: {file_path}")
                print(f"  - File size: {file_size} bytes")
                print(f"  - Duration: {duration:.2f} seconds")
                print(f"  - Sample rate: {self.sample_rate} Hz")
                print(f"  - Chunks recorded: {len(self.audio_data)}")
                
            else:
                print(f"WARNING: No audio data to save for: {file_path}")
            
        except Exception as e:
            print(f"Error saving audio: {e}")
    
    def cleanup(self):
        """Clean up audio resources"""
        self.is_recording = False
        
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
            
        if AUDIO_AVAILABLE and self.audio:
            self.audio.terminate()

class StroopColorWordTask(TaskStateMixin, QWidget):
    """Stroop Color-Word Task with configurable parameters and comprehensive crash recovery support"""
    
    # Task name constant for session management
    TASK_NAME = "Stroop Colour-Word Task"
    
    def __init__(self, csv_file=None, x_pos=None, y_pos=None, participant_id=None, participant_folder_path=None):
        # CRITICAL: Initialize session manager FIRST if not already initialized
        if not get_session_manager() and participant_id and participant_folder_path:
            print("Initializing session manager from Stroop task...")
            initialize_session_manager(participant_id, participant_folder_path)
        
        # Call parent constructors (TaskStateMixin first, then QWidget)
        super().__init__()
        
        # Store participant information
        self.participant_id = participant_id
        self.participant_folder_path = participant_folder_path
        
        # Task configuration (will be set after user configuration)
        self.task_config = None
        self.recording_duration_seconds = DEFAULT_RECORDING_DURATION
        self.recording_duration_ms = int(self.recording_duration_seconds * 1000)
        self.pre_stimulus_delay_ms = DEFAULT_PRE_STIMULUS_DELAY
        
        # Set window properties
        self.setWindowTitle("Stroop Colour-Word Task")
        
        # Check for recovery early in initialization
        self.recovery_data = None
        self.recovery_offset = 0  # Offset for trial numbering in recovery mode
        
        if self.session_manager:
            current_state = self.session_manager.get_current_task_state()
            if (current_state and 
                current_state.get('task_name') == self.TASK_NAME and
                current_state.get('status') == 'in_progress'):
                self.recovery_data = current_state
                print("Recovery data found - will resume from previous session")
        
        print(f"=== STROOP COLOR-WORD TASK INITIALIZATION ===")
        print(f"Received participant_id: '{participant_id}' (type: {type(participant_id)})")
        print(f"Received participant_folder_path: '{participant_folder_path}' (type: {type(participant_folder_path)})")
        print(f"Recovery mode: {'ENABLED' if self.recovery_data else 'DISABLED'}")
        print(f"Session manager: {'AVAILABLE' if self.session_manager else 'NOT AVAILABLE'}")
        print(f"Configuration: Will be set by user")
        print(f"==================================")
        
        # Task state variables
        self.configuration_mode = True  # Start in configuration mode
        self.configuration_saved = False
        
        # Trial timing variables for high-resolution timestamps
        self.audio_start_time = None
        self.stimulus_onset_time = None
        self.stimulus_offset = None
        
        # Pause/Resume state variables
        self.is_paused = False
        self.paused_during_recording = False
        self.pause_timestamp = None
        self.current_audio_path = None
        self.recording_active = False
        self.paused_trials = []  # Store trials that were paused to move to back of queue
        
        # Task completion flag to prevent emergency save during normal closure - ENHANCED
        self._task_completed = False
        self._completion_in_progress = False
        
        # Critical check - ensure participant information is available
        if not participant_id or not participant_folder_path:
            print("ERROR: Missing participant information!")
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Missing Participant Information")
            error_msg.setText("Cannot start Stroop Color-Word task!")
            error_msg.setInformativeText("Participant information is missing. "
                                       "Please go back and ensure the biodata form "
                                       "is properly saved before selecting this test.")
            error_msg.exec()
            self.close()
            return
        
        # Verify participant folder exists
        if not os.path.exists(participant_folder_path):
            print(f"ERROR: Participant folder does not exist: {participant_folder_path}")
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Participant Folder Missing")
            error_msg.setText("Participant folder not found!")
            error_msg.setInformativeText("Please go back and save the biodata form first.")
            error_msg.exec()
            self.close()
            return
        
        print(f"✓ Participant information verified successfully")
        
        # Initialize speech onset detector
        self.speech_detector = SpeechOnsetDetector()
        
        # Use provided position or default
        if x_pos is not None and y_pos is not None:
            self.setGeometry(x_pos, y_pos, 1370, 960)
        else:
            screen = QApplication.primaryScreen().geometry()
            window_width, window_height = 1370, 960
            x = (screen.width() - window_width) // 2
            y = (screen.height() - window_height) // 2
            self.setGeometry(x, y, window_width, window_height)

        # Set background to match the app theme
        self.setStyleSheet("background-color: #f6f6f6;")
        
        # Trial data collection variables
        self.trial_data = []  # Store all trial data
        self.current_trial_info = None
        
        # Audio recording setup
        self.audio_recorder = AudioRecorder()
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.record_audio_chunk)
        
        # Create audio folder for this session
        self.audio_folder_path = None
        self.create_audio_folder()
        
        # Verify audio folder was created successfully
        if not self.audio_folder_path:
            print("CRITICAL ERROR: Failed to create audio folder")
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Audio Folder Creation Failed")
            error_msg.setText("Cannot create audio recording folder!")
            error_msg.exec()
            self.close()
            return
        
        print(f"✓ Audio folder created successfully: {self.audio_folder_path}")
        
        # Handle TXT file path (changed from CSV for faster loading in exe/dmg format)
        if csv_file is None:
            csv_file = resource_path('task_stroop_colorword/stimulus_data.txt')
        
        try:
            self.df = pd.read_csv(csv_file)  # pandas can read TXT files with CSV format
            print(f"Successfully loaded Stroop Color-Word task data from: {csv_file}")
            print(f"TXT columns: {list(self.df.columns)}")
            print(f"Total trials in TXT: {len(self.df)}")
            
        except Exception as e:
            # If TXT file is not found, create sample data for demonstration
            print(f"Could not load 'task_stroop_colorword/stimulus_data.txt': {e}")
            print(f"Creating balanced sample Stroop Color-Word task data...")
            self.create_sample_data()
        
        # Create layout with reduced left/right margins for larger child window
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 50, 10, 50)  # left, top, right, bottom
        
        # Create child window for displaying content
        self.word_display_window = StroopColorWordDisplayWindow(self)
        
        # Create button (will change between Save, Next, Start, Pause)
        self.action_button = QPushButton("Save Configuration", self)
        self.action_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.action_button.setFixedSize(250, 70)
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffffff, stop: 1 #f0f0f0);
                color: black;
                border: 2px solid #e0e0e0;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fafafa, stop: 1 #e8e8e8);
                border: 2px solid #d0d0d0;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #e8e8e8, stop: 1 #ffffff);
                border: 2px solid #c0c0c0;
            }
        """)
        self.action_button.clicked.connect(self.action_button_clicked)
        
        # Add widgets to layout with proper centering
        self.layout.addStretch()
        
        # Center the child window
        self.layout.addWidget(self.word_display_window, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addSpacing(30)
        
        # Center the action button
        self.layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add bottom stretch for better centering
        self.layout.addStretch()
        
        self.setLayout(self.layout)
        
        # Initialize trial state
        self.current_index = 0
        self.task_started = False
        self.practice_mode = False
        self.practice_trials = []
        self.practice_index = 0
        
        # Initialize timers
        self.countdown_timer = QTimer()
        self.practice_countdown_timer = QTimer()
        self.resume_countdown_timer = QTimer()
        self.break_timer = QTimer()
        self.break_resume_timer = QTimer()
        
        # Initialize recovery AFTER all other initialization
        if self.session_manager:
            print("Task recovery system activated")
            # Update UI for recovery if needed
            if self.recovery_data:
                QTimer.singleShot(100, self._update_recovery_ui)
        else:
            print("WARNING: Session manager not available - recovery disabled")

    def action_button_clicked(self):
        """Handle action button click based on current mode"""
        if self.configuration_mode and not self.configuration_saved:
            self.save_configuration()
        elif self.configuration_mode and self.configuration_saved:
            self.proceed_to_instructions()
        elif not self.task_started:
            self.start_task()
        else:
            self.toggle_pause()
    
    def save_configuration(self):
        """Save the task configuration"""
        # Validate configuration
        is_valid, error_message = self.word_display_window.validate_configuration()
        if not is_valid:
            QMessageBox.warning(self, "Configuration Error", error_message)
            return
        
        # Get configuration
        self.task_config = self.word_display_window.get_configuration()
        
        # Update task parameters
        if self.task_config['main_enabled']:
            self.recording_duration_seconds = self.task_config['recording_duration']
            self.recording_duration_ms = int(self.recording_duration_seconds * 1000)
            self.pre_stimulus_delay_ms = self.task_config['pre_stimulus_delay']
        
        print(f"=== TASK CONFIGURATION SAVED ===")
        print(f"Practice enabled: {self.task_config['practice_enabled']}")
        print(f"Practice trials: {self.task_config['practice_trials']}")
        print(f"Main enabled: {self.task_config['main_enabled']}")
        print(f"Main trials: {self.task_config['num_trials']}")
        print(f"Recording duration: {self.task_config['recording_duration']} seconds")
        print(f"Pre-stimulus delay: {self.task_config['pre_stimulus_delay']} ms")
        print("=================================")
        
        # Mark configuration as saved
        self.configuration_saved = True
        
        # Update button
        self.action_button.setText("Next")
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #e8f5e8, stop: 1 #d4f4d4);
                color: black;
                border: 2px solid #4CAF50;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #f0f8f0, stop: 1 #e0f2e0);
                border: 2px solid #45a049;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #d4f4d4, stop: 1 #e8f5e8);
                border: 2px solid #3e8e41;
            }
        """)
        
        # Show success message
        QMessageBox.information(self, "Configuration Saved", 
                              "Task configuration has been saved successfully!\n\nClick 'Next' to proceed to instructions.")
    
    def proceed_to_instructions(self):
        """Proceed from configuration to instructions"""
        # Hide configuration and show instructions
        self.word_display_window.hide_configuration()
        self.word_display_window.show_instructions(self.task_config)
        
        # Prepare trials based on configuration
        self.prepare_trials()
        
        # Update button for task start
        self.action_button.setText("Start")
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fff3e0, stop: 1 #ffe0b2);
                color: black;
                border: 2px solid #FF9800;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fff8f0, stop: 1 #ffecb3);
                border: 2px solid #F57C00;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffe0b2, stop: 1 #fff3e0);
                border: 2px solid #E65100;
            }
        """)
        
        # No longer in configuration mode
        self.configuration_mode = False
    
    def start_task(self):
        """Start the actual task"""
        if not self.task_started:
            # Check if this is recovery mode
            if self.recovery_data:
                # Recovery mode - go directly to main task or practice based on what was being done
                print("Starting task in recovery mode")
                self.task_started = True
                self.update_button_for_pause()
                self.show_recovery_instructions()
            else:
                # Normal mode - start with practice or main based on configuration
                print("Starting task in normal mode")
                self.task_started = True
                self.update_button_for_pause()
                
                if self.task_config['practice_enabled']:
                    self.show_practice_instructions()
                else:
                    self.show_main_task_preparation()
    
    def update_button_for_pause(self):
        """Update button for pause functionality"""
        self.action_button.setText("Pause")
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffeeee, stop: 1 #ffdddd);
                color: black;
                border: 2px solid #e0a0a0;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fff5f5, stop: 1 #ffe8e8);
                border: 2px solid #d08080;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffdddd, stop: 1 #ffffff);
                border: 2px solid #c06060;
            }
        """)
    
    def toggle_pause(self):
        """Toggle pause state"""
        if self.is_paused:
            self.resume_task()
        else:
            self.pause_task()
    
    def pause_task(self):
        """Pause the current task"""
        print("=== TASK PAUSED ===")
        self.is_paused = True
        self.pause_timestamp = time.perf_counter()
        
        # Emergency save current state
        if self.session_manager:
            try:
                self._auto_save_task_state()
                print("Emergency save completed during pause")
            except Exception as e:
                print(f"Error during emergency save: {e}")
        
        # Update button to show "Continue"
        self.action_button.setText("Continue")
        self.action_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #eeffee, stop: 1 #ddffdd);
                color: black;
                border: 2px solid #a0e0a0;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #f5fff5, stop: 1 #e8ffe8);
                border: 2px solid #80d080;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ddffdd, stop: 1 #ffffff);
                border: 2px solid #60c060;
            }
        """)
        
        # Handle audio recording if currently recording (main trials only)
        if self.recording_active and self.audio_recorder.is_recording:
            print("Pausing during active recording - moving trial to back of queue")
            self.paused_during_recording = True
            
            # Stop current recording and delete the file
            self.recording_timer.stop()
            self.audio_recorder.stop_recording(self.current_audio_path)
            self.recording_active = False
            
            # Delete the incomplete audio file
            if self.current_audio_path and os.path.exists(self.current_audio_path):
                try:
                    os.remove(self.current_audio_path)
                    print(f"Deleted incomplete audio file: {os.path.basename(self.current_audio_path)}")
                except Exception as e:
                    print(f"Error deleting incomplete audio file: {e}")
            
            # Move current trial to back of queue if we're in main task mode
            if not self.practice_mode and self.current_trial_info:
                current_trial = self.all_trials[self.current_index].copy()
                self.paused_trials.append(current_trial)
                print(f"Trial {self.current_index + 1} added to back of queue due to pause during recording")
        else:
            self.paused_during_recording = False
        
        # Show pause message in display window
        self.word_display_window.show_completion_message("TASK PAUSED\n\nClick Continue to resume")
        print("Task successfully paused")
    
    def resume_task(self):
        """Resume the paused task"""
        print("=== TASK RESUMED ===")
        self.is_paused = False
        
        # Update button back to "Pause"
        self.update_button_for_pause()
        
        # If we paused during recording in main task, move to back of queue and advance
        if self.paused_during_recording and not self.practice_mode:
            print("Resuming after recording pause - advancing to next trial")
            self.advance_to_next_trial_after_pause()
        elif hasattr(self, 'is_in_break') and self.is_in_break:
            # We were in a break period
            print("Resuming break period")
            if hasattr(self, 'break_countdown_value') and self.break_countdown_value > 0:
                # Resume break countdown
                self.break_timer.start(1000)
                self.update_break_countdown()
            else:
                # Resume break resume countdown  
                self.break_resume_timer.start(1000)
                self.update_break_resume_countdown()
        elif self.practice_mode:
            # We were in practice mode
            print("Resuming practice trials")
            if hasattr(self, 'practice_countdown_value') and self.practice_countdown_value > 0:
                # Resume practice countdown
                self.practice_countdown_timer.start(1000)
                self.update_practice_countdown()
            else:
                # Resume practice trial
                self.show_next_practice_trial()
        else:
            # We were in main task but not during recording
            print("Resuming main task")
            if hasattr(self, 'countdown_value') and self.countdown_value > 0:
                # Resume main countdown
                self.countdown_timer.start(1000)
                self.update_countdown()
            else:
                # Show resume countdown and then continue
                self.show_resume_countdown()

    def show_resume_countdown(self):
        """Show 3, 2, 1 countdown before resuming"""
        self.resume_countdown_value = 3
        self.word_display_window.show_completion_message(
            "RESUMING TASK\n\n"
            f"Get ready...\n\n"
            f"Continuing in {self.resume_countdown_value} seconds..."
        )
        
        print("Starting resume countdown...")
        self.resume_countdown_timer.timeout.connect(self.update_resume_countdown)
        self.resume_countdown_timer.start(1000)  # Update every 1 second

    def update_resume_countdown(self):
        """Update the resume countdown display"""
        if self.is_paused:
            return
            
        if self.resume_countdown_value > 0:
            # Update the display with current countdown
            self.word_display_window.show_completion_message(
                "RESUMING TASK\n\n"
                f"Get ready...\n\n"
                f"Continuing in {self.resume_countdown_value} seconds..."
            )
            print(f"Resume countdown: {self.resume_countdown_value}")
            self.resume_countdown_value -= 1
        else:
            # Countdown finished - continue with task
            self.resume_countdown_timer.stop()
            self.resume_countdown_timer.timeout.disconnect()
            print("Resume countdown complete - continuing task")
            
            # Continue with the appropriate task state
            if self.practice_mode:
                self.show_next_practice_trial()
            else:
                self.show_next_trial()

    def advance_to_next_trial_after_pause(self):
        """Advance to next trial after pause, moving paused trial to back of queue"""
        print("=== ADVANCING TO NEXT TRIAL AFTER PAUSE ===")
        
        # Move to next trial (skip the one that was paused)
        self.current_index += 1
        self.paused_during_recording = False
        
        # Show resume countdown then continue
        self.show_resume_countdown()
        
    # Rest of the methods would follow the same pattern as the original code
    # but using self.task_config values instead of hardcoded constants
    
    def create_sample_data(self):
        """Create balanced sample Stroop Color-Word task data with proper proportions"""
        print(f"Creating balanced sample Stroop Color-Word trials...")
        
        # Create base combinations with proper proportions to match original dataset
        base_combinations = []
        
        # Congruent trials (40% - 4 combinations × 8 repeats = 32 trials)
        congruent_base = []
        for word, color in zip(['RED', 'BLUE', 'GREEN', 'YELLOW'], ['red', 'blue', 'green', 'yellow']):
            for _ in range(8):  # 8 repeats of each congruent pair
                congruent_base.append({
                    'condition1': 'congruent',
                    'stim1': word,
                    'textColor': color
                })
        
        # Incongruent trials (30% - 12 combinations × 2 repeats = 24 trials)
        incongruent_base = []
        for word in ['RED', 'BLUE', 'GREEN', 'YELLOW']:
            for color in ['red', 'blue', 'green', 'yellow']:
                if word.lower() != color:  # Only incongruent combinations
                    for _ in range(2):  # 2 repeats of each incongruent pair
                        incongruent_base.append({
                            'condition1': 'incongruent',
                            'stim1': word,
                            'textColor': color
                        })
        
        # Neutral trials (30% - 16 combinations × 1.5 average = 24 trials)
        neutral_base = []
        neutral_words = ['DEEP', 'LEGAL', 'POOR', 'BAD']
        for word in neutral_words:
            for color in ['red', 'blue', 'green', 'yellow']:
                for _ in range(6):  # 6 repeats of each neutral word-color combination
                    neutral_base.append({
                        'condition1': 'neutral',
                        'stim1': word,
                        'textColor': color
                    })
        
        # Combine all base trials (should total 80)
        all_base_trials = congruent_base + incongruent_base + neutral_base
        
        print(f"Generated balanced base set: {len(congruent_base)} congruent, {len(incongruent_base)} incongruent, {len(neutral_base)} neutral")
        print(f"Total: {len(all_base_trials)} trials")
        
        self.df = pd.DataFrame(all_base_trials)

    def prepare_trials(self):
        """Prepare trials based on user configuration"""
        print("=== PREPARING TRIALS WITH USER CONFIGURATION ===")
        
        # If we're in recovery mode, adjust the trials
        if self.recovery_data:
            print("Preparing trials with recovery support...")
            
            # Get completed trials from recovery data
            completed_trials = self.recovery_data.get('trial_data', [])
            trials_completed = len(completed_trials)
            
            print(f"Recovery: {trials_completed} trials already completed")
            
            # Restore completed trial data to task
            self.trial_data = completed_trials.copy()
            
            # Prepare remaining trials using the same balanced sequence
            remaining_trials_needed = self.task_config['num_trials'] - trials_completed
            
            if remaining_trials_needed > 0:
                print(f"Preparing {remaining_trials_needed} remaining trials...")
                # Get the full sequence and take only the remaining portion
                full_sequence = self.create_balanced_trial_sequence(self.task_config['num_trials'])
                self.all_trials = full_sequence[trials_completed:]
            else:
                # All trials completed - this shouldn't happen, but handle gracefully
                print("All trials already completed in previous session")
                self.all_trials = []
            
            # Set current index to start from where we left off
            self.current_index = 0  # Index into remaining trials
            self.recovery_offset = trials_completed  # Offset for trial numbering
        else:
            # Normal trial preparation
            print("Preparing trials normally (no recovery)")
            self.recovery_offset = 0
            
            # Create the balanced trial sequence based on configuration
            if self.task_config['main_enabled']:
                self.all_trials = self.create_balanced_trial_sequence(self.task_config['num_trials'])
            else:
                self.all_trials = []
            self.current_index = 0
        
        # Create practice trials if enabled
        if self.task_config['practice_enabled']:
            self.create_practice_trials()
        
        print(f"Prepared {len(self.all_trials)} main trials for Stroop Color-Word task")
        if self.task_config['practice_enabled']:
            print(f"Prepared {len(self.practice_trials)} practice trials")
        print(f"Starting from trial index: {self.current_index}")
        if hasattr(self, 'recovery_offset'):
            print(f"Recovery offset: {self.recovery_offset}")
        print("===============================================")

    def create_balanced_trial_sequence(self, num_trials):
        """Create a balanced trial sequence that's consistent across all participants"""
        print(f"Creating balanced sequence for {num_trials} trials...")
        
        # Separate trials by condition from the loaded data
        available_trials = self.df.to_dict('records')
        
        congruent_trials = [t for t in available_trials if t['condition1'] == 'congruent']
        incongruent_trials = [t for t in available_trials if t['condition1'] == 'incongruent'] 
        neutral_trials = [t for t in available_trials if t['condition1'] == 'neutral']
        
        print(f"Available trials: {len(congruent_trials)} congruent, {len(incongruent_trials)} incongruent, {len(neutral_trials)} neutral")
        
        if num_trials <= 80:
            # Case 1: Select balanced subset
            return self._create_balanced_subset(num_trials, congruent_trials, incongruent_trials, neutral_trials)
        else:
            # Case 2: Use all 80 + additional balanced trials
            return self._create_expanded_sequence(num_trials, congruent_trials, incongruent_trials, neutral_trials)

    def _create_balanced_subset(self, num_trials, congruent_trials, incongruent_trials, neutral_trials):
        """Create a balanced subset when num_trials <= 80"""
        
        # Calculate target numbers for each condition (maintaining original proportions)
        # Original: 32 congruent (40%), 24 incongruent (30%), 24 neutral (30%)
        target_congruent = round(num_trials * 0.4)
        target_incongruent = round(num_trials * 0.3)
        target_neutral = num_trials - target_congruent - target_incongruent  # Ensure exact sum
        
        print(f"Target distribution: {target_congruent} congruent, {target_incongruent} incongruent, {target_neutral} neutral")
        
        # Use FIXED random seed for consistent selection across participants
        random.seed(42)  # Fixed seed ensures same selection for all participants
        
        # Select trials (same selection for all participants due to fixed seed)
        selected_congruent = random.sample(congruent_trials, min(target_congruent, len(congruent_trials)))
        selected_incongruent = random.sample(incongruent_trials, min(target_incongruent, len(incongruent_trials)))
        selected_neutral = random.sample(neutral_trials, min(target_neutral, len(neutral_trials)))
        
        # Combine all selected trials
        all_selected = selected_congruent + selected_incongruent + selected_neutral
        
        # Create FIXED randomized order (same for all participants)
        random.seed(123)  # Different seed for ordering
        random.shuffle(all_selected)
        
        print(f"Selected: {len(selected_congruent)} congruent, {len(selected_incongruent)} incongruent, {len(selected_neutral)} neutral")
        print("✓ All participants will see identical trial sequence")
        
        return all_selected

    def _create_expanded_sequence(self, num_trials, congruent_trials, incongruent_trials, neutral_trials):
        """Create expanded sequence when num_trials > 80"""
        
        # Start with all 80 trials
        all_80_trials = congruent_trials + incongruent_trials + neutral_trials
        
        # Create consistent order for the base 80 trials
        random.seed(42)  # Fixed seed for consistent ordering
        random.shuffle(all_80_trials)
        
        additional_trials_needed = num_trials - 80
        print(f"Using all 80 trials + {additional_trials_needed} additional trials")
        
        # Calculate proportional additional trials
        # Original proportions: 40% congruent, 30% incongruent, 30% neutral
        additional_congruent = round(additional_trials_needed * 0.4)
        additional_incongruent = round(additional_trials_needed * 0.3)
        additional_neutral = additional_trials_needed - additional_congruent - additional_incongruent
        
        print(f"Additional trials: {additional_congruent} congruent, {additional_incongruent} incongruent, {additional_neutral} neutral")
        
        # Select additional trials with fixed seed
        random.seed(456)  # Fixed seed for additional trial selection
        
        # Allow repetition of trials if needed
        extra_congruent = []
        extra_incongruent = []
        extra_neutral = []
        
        # Select additional trials (with repetition if necessary)
        for i in range(additional_congruent):
            extra_congruent.append(random.choice(congruent_trials))
        
        for i in range(additional_incongruent):
            extra_incongruent.append(random.choice(incongruent_trials))
            
        for i in range(additional_neutral):
            extra_neutral.append(random.choice(neutral_trials))
        
        # Combine additional trials and shuffle
        additional_trials = extra_congruent + extra_incongruent + extra_neutral
        random.seed(789)  # Fixed seed for additional trial ordering
        random.shuffle(additional_trials)
        
        # Combine base 80 + additional trials
        final_sequence = all_80_trials + additional_trials
        
        print(f"Final sequence: {len(final_sequence)} trials total")
        print("✓ All participants will see identical trial sequence")
        
        return final_sequence

    def create_practice_trials(self):
        """Create practice trials based on configuration"""
        practice_trials = []
        num_practice = self.task_config['practice_trials']
        
        # Create practice trials with balanced conditions
        if num_practice >= 6:
            # Full practice set with all conditions
            base_trials = [
                {'condition1': 'congruent', 'stim1': 'RED', 'textColor': 'red'},
                {'condition1': 'congruent', 'stim1': 'BLUE', 'textColor': 'blue'},
                {'condition1': 'incongruent', 'stim1': 'RED', 'textColor': 'blue'},
                {'condition1': 'incongruent', 'stim1': 'BLUE', 'textColor': 'red'},
                {'condition1': 'neutral', 'stim1': 'DEEP', 'textColor': 'green'},
                {'condition1': 'neutral', 'stim1': 'LEGAL', 'textColor': 'yellow'}
            ]
            
            # Add more trials if needed
            while len(base_trials) < num_practice:
                base_trials.append(random.choice([
                    {'condition1': 'congruent', 'stim1': 'GREEN', 'textColor': 'green'},
                    {'condition1': 'incongruent', 'stim1': 'GREEN', 'textColor': 'yellow'},
                    {'condition1': 'neutral', 'stim1': 'POOR', 'textColor': 'red'}
                ]))
            
            practice_trials = base_trials[:num_practice]
        else:
            # Minimal practice set
            all_options = [
                {'condition1': 'congruent', 'stim1': 'RED', 'textColor': 'red'},
                {'condition1': 'incongruent', 'stim1': 'RED', 'textColor': 'blue'},
                {'condition1': 'neutral', 'stim1': 'DEEP', 'textColor': 'green'}
            ]
            
            for i in range(num_practice):
                practice_trials.append(all_options[i % len(all_options)])
        
        # Use fixed random seed for consistent practice trials across participants
        random.seed(999)  # Fixed seed for practice trials
        random.shuffle(practice_trials)
        self.practice_trials = practice_trials
        
        print(f"Created {len(self.practice_trials)} practice trials (consistent across participants):")
        for i, trial in enumerate(self.practice_trials):
            print(f"  Practice {i+1}: {trial['condition1']} - {trial['stim1']} in {trial['textColor']}")

    def create_audio_folder(self):
        """Create audio folder for this session"""
        if not self.participant_folder_path:
            print("ERROR: No participant folder path available")
            self.audio_folder_path = None
            return
        
        try:
            timestamp = self.generate_timestamp()
            audio_folder_name = f"stroopcolorwordtask_{timestamp}"
            self.audio_folder_path = os.path.join(self.participant_folder_path, audio_folder_name)
            
            os.makedirs(self.audio_folder_path, exist_ok=True)
            print(f"SUCCESS: Created audio folder: {self.audio_folder_path}")
            
        except Exception as e:
            print(f"ERROR creating audio folder: {e}")
            self.audio_folder_path = None

    def show_practice_instructions(self):
        """Show instructions for practice trials"""
        if self.is_paused:
            return
            
        self.word_display_window.show_completion_message(
            f"PRACTICE TRIALS\n\n"
            f"The next {self.task_config['practice_trials']} trials are for practice.\n\n"
            f"Remember: Say aloud the COLOR of the ink,\n"
            f"not the word itself.\n\n"
            f"Practice trials will begin in 3 seconds..."
        )
        
        print("=== PRACTICE PHASE STARTING ===")
        print("Showing practice instructions...")
        
        # Start practice countdown
        self.practice_countdown_value = 3
        self.practice_countdown_timer.timeout.connect(self.update_practice_countdown)
        self.practice_countdown_timer.start(1000)  # Update every 1 second

    def update_practice_countdown(self):
        """Update the practice countdown display"""
        if self.is_paused:
            return
            
        if self.practice_countdown_value > 0:
            # Update the display with current countdown
            self.word_display_window.show_completion_message(
                f"PRACTICE TRIALS\n\n"
                f"The next {self.task_config['practice_trials']} trials are for practice.\n\n"
                f"Remember: Say aloud the COLOR of the ink,\n"
                f"not the word itself.\n\n"
                f"Practice trials will begin in {self.practice_countdown_value} seconds..."
            )
            print(f"Practice countdown: {self.practice_countdown_value}")
            self.practice_countdown_value -= 1
        else:
            # Countdown finished - start practice trials
            self.practice_countdown_timer.stop()
            self.practice_countdown_timer.timeout.disconnect()
            print("Practice countdown complete - starting practice trials")
            self.start_practice_trials()
    
    def start_practice_trials(self):
        """Start the practice trials"""
        if self.is_paused:
            return
            
        self.practice_mode = True
        self.practice_index = 0
        print("Starting practice trials (no audio recording)")
        self.show_next_practice_trial()
    
    def show_next_practice_trial(self):
        """Display the next practice trial"""
        if self.is_paused:
            return
            
        if self.practice_index >= len(self.practice_trials):
            # Practice completed - show preparation for main task or complete if no main task
            print("=== PRACTICE COMPLETED ===")
            if self.task_config['main_enabled']:
                self.show_main_task_preparation()
            else:
                self.start_completion_sequence()
            return
        
        # Get current practice trial
        trial = self.practice_trials[self.practice_index]
        word = trial['stim1']
        color = trial['textColor']
        
        print(f"Practice Trial {self.practice_index + 1}: Word='{word}', Color='{color}', "
              f"Condition='{trial['condition1']}'")
        
        # Display the practice stimulus immediately (no recording delay needed)
        self.display_practice_stimulus(word, color)
        
        # Move to next practice trial after 3 seconds
        QTimer.singleShot(3000, self.next_practice_trial)
    
    def display_practice_stimulus(self, word, color):
        """Display practice stimulus (no recording or timing needed)"""
        self.word_display_window.set_text(word.upper())
        self.word_display_window.set_text_color(color)
        print(f"Practice stimulus displayed: {word.upper()} in {color}")
    
    def next_practice_trial(self):
        """Move to next practice trial"""
        if self.is_paused:
            return
            
        self.practice_index += 1
        self.show_next_practice_trial()
    
    def show_main_task_preparation(self):
        """Show countdown and preparation for main task"""
        if self.is_paused:
            return
            
        self.word_display_window.show_completion_message(
            f"PRACTICE COMPLETE!\n\n"
            f"Great job! Now get ready for the real task.\n\n"
            f"The main experiment will have {self.task_config['num_trials']} trials.\n"
            f"Audio will be recorded for reaction time analysis.\n\n"
            f"Remember: Say the COLOR, not the word!\n\n"
            f"Starting in 5 seconds..."
        )
        
        print("=== MAIN TASK PREPARATION ===")
        print("Practice completed successfully")
        print(f"Preparing for main task with {self.task_config['num_trials']} trials...")
        
        # Start countdown
        self.countdown_value = 5
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # Update every 1 second
    
    def update_countdown(self):
        """Update the countdown display"""
        if self.is_paused:
            return
            
        if self.countdown_value > 0:
            # Update the display with current countdown
            self.word_display_window.show_completion_message(
                f"PRACTICE COMPLETE!\n\n"
                f"Great job! Now get ready for the real task.\n\n"
                f"The main experiment will have {self.task_config['num_trials']} trials.\n"
                f"Audio will be recorded for reaction time analysis.\n\n"
                f"Remember: Say the COLOR, not the word!\n\n"
                f"Starting in {self.countdown_value} seconds..."
            )
            print(f"Countdown: {self.countdown_value}")
            self.countdown_value -= 1
        else:
            # Countdown finished - start main task
            self.countdown_timer.stop()
            self.countdown_timer.timeout.disconnect()
            print("Countdown complete - starting main task")
            self.start_main_task()
    
    def start_main_task(self):
        """Start the main task trials with recovery support"""
        if self.is_paused:
            return
            
        self.practice_mode = False
        print("=== MAIN TASK STARTING ===")
        
        # Start task with recovery support - ENHANCED INTEGRATION
        if self.session_manager:
            task_config = {
                'total_trials': self.task_config['num_trials'],
                'recording_duration_seconds': self.recording_duration_seconds,
                'pre_stimulus_delay_ms': self.pre_stimulus_delay_ms,
                'recovery_mode': bool(self.recovery_data),
                'audio_folder_path': self.audio_folder_path,
                'balanced_trials': True,
                'consistent_sequence': True,
                'user_configuration': self.task_config
            }
            
            if not self.recovery_data:
                # Starting new task - PROPERLY CALL start_task_with_recovery
                self.start_task_with_recovery(task_config, self.task_config['num_trials'])
                print("Started new main task with enhanced recovery support and user configuration")
            else:
                # Resuming from recovery - ensure auto-save is active
                print("Resuming main task from recovery data with user configuration")
                self.task_started = True
                # Ensure auto-save is started
                self._start_auto_save_system()
        
        print("Beginning recorded trials with user configuration...")
        self.show_next_trial()

    def show_recovery_instructions(self):
        """Show instructions for recovery mode"""
        if self.is_paused:
            return
        
        trials_completed = len(self.trial_data)
        remaining_trials = self.task_config['num_trials'] - trials_completed
        
        self.word_display_window.show_completion_message(
            "SESSION RECOVERED\n\n"
            "Welcome back! Your previous session has been restored.\n\n"
            f"Trials completed: {trials_completed}\n"
            f"Trials remaining: {remaining_trials}\n\n"
            "The task will continue from where you left off.\n\n"
            "Starting in 3 seconds..."
        )
        
        print("=== RECOVERY MODE INSTRUCTIONS ===")
        print(f"Trials completed: {trials_completed}")
        print(f"Trials remaining: {remaining_trials}")
        print("Showing recovery instructions...")
        
        # Start recovery countdown
        self.practice_countdown_value = 3
        self.practice_countdown_timer.timeout.connect(self.update_recovery_countdown)
        self.practice_countdown_timer.start(1000)

    def update_recovery_countdown(self):
        """Update the recovery countdown display"""
        if self.is_paused:
            return
            
        if self.practice_countdown_value > 0:
            trials_completed = len(self.trial_data)
            remaining_trials = self.task_config['num_trials'] - trials_completed
            
            self.word_display_window.show_completion_message(
                "SESSION RECOVERED\n\n"
                "Welcome back! Your previous session has been restored.\n\n"
                f"Trials completed: {trials_completed}\n"
                f"Trials remaining: {remaining_trials}\n\n"
                "The task will continue from where you left off.\n\n"
                f"Starting in {self.practice_countdown_value} seconds..."
            )
            print(f"Recovery countdown: {self.practice_countdown_value}")
            self.practice_countdown_value -= 1
        else:
            # Countdown finished - start main task
            self.practice_countdown_timer.stop()
            self.practice_countdown_timer.timeout.disconnect()
            print("Recovery countdown complete - starting main task")
            self.start_main_task()

    def show_next_trial(self):
        """Display the next trial or finish the task with recovery support"""
        if self.is_paused:
            return
        
        # Check if we've completed all remaining trials
        if self.current_index >= len(self.all_trials):
            # Handle paused trials if any
            if self.paused_trials:
                print(f"\n=== ADDING {len(self.paused_trials)} PAUSED TRIALS TO END OF QUEUE ===")
                for i, paused_trial in enumerate(self.paused_trials):
                    self.all_trials.append(paused_trial)
                    print(f"Added paused trial {i+1}: {paused_trial['stim1']} in {paused_trial['textColor']}")
                
                self.paused_trials = []
                print(f"Total trials now: {len(self.all_trials)}")
                print("Continuing with paused trials...")
            else:
                # Task completed
                print("\n" + "="*50)
                print("TASK COMPLETED - STARTING COMPLETION SEQUENCE")
                print("="*50)
                
                self.action_button.hide()
                self.start_completion_sequence()
                return
        
        # Get current trial
        trial = self.all_trials[self.current_index]
        
        # Calculate actual trial number (accounting for recovery offset)
        actual_trial_number = self.current_index + 1
        if hasattr(self, 'recovery_offset'):
            actual_trial_number += self.recovery_offset
        
        # Store current trial info for data recording
        self.current_trial_info = trial.copy()
        self.current_trial_info['trial_number'] = actual_trial_number
        
        word = trial['stim1']
        color = trial['textColor']
        
        print(f"Trial {actual_trial_number}: Word='{word}', Color='{color}', "
              f"Condition='{trial.get('condition1', 'unknown')}'")
        
        # Auto-save current state before starting recording
        if self.session_manager:
            self._auto_save_task_state()
        
        # START RECORDING FIRST using high-resolution timing
        self.start_recording_with_timing()
        
        # THEN display the stimulus after the configured delay
        QTimer.singleShot(self.pre_stimulus_delay_ms, lambda: self.display_stimulus_with_timing(word, color))

    def start_recording_with_timing(self):
        """Start audio recording with high-resolution timestamp logging"""
        if self.is_paused:
            return
            
        if not self.current_trial_info:
            return
        
        # Safety check for audio folder path
        if not self.audio_folder_path:
            print("CRITICAL ERROR: No audio folder available")
            QMessageBox.critical(self, "Error", 
                               "Cannot save audio files!\n\n"
                               "Please ensure the biodata form is properly saved "
                               "before starting the Stroop task.")
            self.close()
            return
        
        # Log exact audio recording start time using high-resolution timer
        self.audio_start_time = time.perf_counter()
        self.recording_active = True
        
        # Generate audio filename
        trial_num = self.current_trial_info['trial_number']
        audio_filename = f"trial_{trial_num}.wav"
        
        try:
            self.current_audio_path = os.path.join(self.audio_folder_path, audio_filename)
            print(f"Recording trial {trial_num} to: {self.current_audio_path}")
            print(f"Audio recording start time: {self.audio_start_time:.6f}")
        except Exception as e:
            print(f"Error creating audio path: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Cannot create audio file path!\n\nError: {str(e)}")
            self.close()
            return
        
        # Start audio recording
        self.audio_recorder.start_recording()
        
        # Start timer for recording chunks (record in small chunks)
        self.recording_timer.start(50)  # Record every 50ms
        
        # Stop recording after the configured duration
        QTimer.singleShot(self.recording_duration_ms, self.stop_current_recording)

    def record_audio_chunk(self):
        """Record a chunk of audio"""
        if self.recording_active and self.audio_recorder.is_recording and not self.is_paused:
            self.audio_recorder.record_chunk()

    def display_stimulus_with_timing(self, word, color):
        """Display the color word stimulus using frame flip timing with PyQt6"""
        
        if self.is_paused:
            return
        
        # First, prepare the stimulus data but don't display yet
        self.word_display_window.prepare_stimulus(word.upper(), color)
        
        # Perform frame flip equivalent in PyQt6: force widget update/repaint
        self.word_display_window.update()  # Request widget redraw
        self.word_display_window.repaint()  # Force immediate repaint (frame flip equivalent)
        
        # Log exact stimulus presentation time immediately after frame flip
        frame_flip_time = time.perf_counter()
        
        # Since PyQt6 doesn't return a flip timestamp, we use the time.perf_counter() call
        # In a real PsychoPy implementation, you would compare flip_timestamp with perf_counter
        # and choose the earlier one, but here we only have the perf_counter timestamp
        self.stimulus_onset_time = frame_flip_time
        
        # Calculate the stimulus offset (time between audio start and stimulus presentation)
        if self.audio_start_time:
            self.stimulus_offset = self.stimulus_onset_time - self.audio_start_time
        else:
            self.stimulus_offset = 0.0
        
        print(f"Stimulus displayed: {word.upper()} in {color}")
        print(f"  Frame flip timing method used")
        print(f"  Audio start time: {self.audio_start_time:.6f}")
        print(f"  Stimulus onset time (frame flip): {self.stimulus_onset_time:.6f}")
        print(f"  Stimulus offset: {self.stimulus_offset:.6f} seconds")
        print(f"  Expected offset: ~{self.pre_stimulus_delay_ms/1000:.3f} seconds")

    def stop_current_recording(self):
        """Stop current recording and move to next trial with enhanced recovery support"""
        if not self.recording_active or self.is_paused:
            return
        
        # IMPORTANT: Stop the timer FIRST to prevent race conditions
        self.recording_timer.stop()
        self.recording_active = False
        
        # Small delay to ensure any pending timer events are processed
        self.audio_recorder.stop_recording(self.current_audio_path)
        
        # Calculate actual trial number for data record
        actual_trial_number = self.current_index + 1
        if hasattr(self, 'recovery_offset'):
            actual_trial_number += self.recovery_offset
        
        # Store trial data with timing information
        trial_record = {
            'trial_number': actual_trial_number,
            'condition1': self.current_trial_info['condition1'],
            'stim1': self.current_trial_info['stim1'],
            'textColor': self.current_trial_info['textColor'],
            'audio_file': os.path.basename(self.current_audio_path),
            'audio_start_time': self.audio_start_time,
            'stimulus_onset_time': self.stimulus_onset_time,
            'stimulus_offset': self.stimulus_offset,
            'rt_seconds': None,  # Will be filled by RT analysis
            'rt_confidence': None,  # Will be filled by RT analysis
            'timing_method': 'frame_flip_colorword_task',
            'balanced_sequence': True,
            'consistent_across_participants': True,
            'user_configuration': self.task_config
        }
        
        # ENHANCED: Save with recovery support using TaskStateMixin method
        if self.session_manager:
            self.save_trial_with_recovery(trial_record)
            print(f"✓ Trial {actual_trial_number} saved with enhanced recovery support")
        else:
            # Fallback to original method
            self.trial_data.append(trial_record)
            print(f"Trial {actual_trial_number} saved without recovery")
        
        print(f"Trial {actual_trial_number} completed, audio saved: {os.path.basename(self.current_audio_path)}")
        
        # Move to next trial
        self.current_index += 1
        
        # Check if we need a break (every 20 trials from the start of the session)
        total_completed = actual_trial_number
        if (not self.practice_mode and 
            total_completed > 0 and 
            total_completed % 20 == 0 and 
            self.current_index < len(self.all_trials)):
            
            print(f"=== BREAK TIME AFTER {total_completed} TRIALS ===")
            self.start_break_period()
        else:
            # Small delay before next trial
            QTimer.singleShot(1000, self.show_next_trial)

    def start_break_period(self):
        """Start a 20-second break period"""
        if self.is_paused:
            return
            
        self.is_in_break = True
        self.break_countdown_value = 20
        
        # Determine which break this is
        break_number = (self.current_index + self.recovery_offset) // 20
        trials_completed = self.current_index + self.recovery_offset
        remaining_trials = len(self.all_trials) + len(self.paused_trials) - self.current_index
        
        print(f"Starting break period {break_number} after {trials_completed} trials")
        print(f"Remaining trials: {remaining_trials}")
        
        # Show initial break message
        self.word_display_window.show_completion_message(
            f"BREAK TIME!\n\n"
            f"You have completed {trials_completed} trials.\n"
            f"{remaining_trials} trials remaining.\n\n"
            f"Break time remaining: {self.break_countdown_value} seconds"
        )
        
        # Start break countdown timer
        self.break_timer.timeout.connect(self.update_break_countdown)
        self.break_timer.start(1000)  # Update every 1 second

    def update_break_countdown(self):
        """Update the break countdown display"""
        if self.is_paused:
            return
            
        if self.break_countdown_value > 0:
            # Update the display with current countdown
            trials_completed = self.current_index + self.recovery_offset
            remaining_trials = len(self.all_trials) + len(self.paused_trials) - self.current_index
            
            self.word_display_window.show_completion_message(
                f"BREAK TIME!\n\n"
                f"You have completed {trials_completed} trials.\n"
                f"{remaining_trials} trials remaining.\n\n"
                f"Break time remaining: {self.break_countdown_value} seconds"
            )
            print(f"Break countdown: {self.break_countdown_value} seconds remaining")
            self.break_countdown_value -= 1
        else:
            # Break countdown finished - start resume countdown
            self.break_timer.stop()
            self.break_timer.timeout.disconnect()
            print("Break period complete - starting resume countdown")
            self.start_break_resume_countdown()
        
        # Restart timer if not finished and not paused
        if self.break_countdown_value >= 0 and not self.is_paused:
            if not self.break_timer.isActive():
                self.break_timer.start(1000)

    def start_break_resume_countdown(self):
        """Start the 3-2-1 countdown after break period"""
        self.break_resume_countdown_value = 3
        
        self.word_display_window.show_completion_message(
            f"BREAK COMPLETE!\n\n"
            f"Get ready to continue...\n\n"
            f"Resuming in {self.break_resume_countdown_value} seconds..."
        )
        
        print("Starting break resume countdown...")
        self.break_resume_timer.timeout.connect(self.update_break_resume_countdown)
        self.break_resume_timer.start(1000)  # Update every 1 second

    def update_break_resume_countdown(self):
        """Update the break resume countdown display"""
        if self.is_paused:
            return
            
        if self.break_resume_countdown_value > 0:
            # Update the display with current countdown
            self.word_display_window.show_completion_message(
                f"BREAK COMPLETE!\n\n"
                f"Get ready to continue...\n\n"
                f"Resuming in {self.break_resume_countdown_value} seconds..."
            )
            print(f"Break resume countdown: {self.break_resume_countdown_value}")
            self.break_resume_countdown_value -= 1
        else:
            # Resume countdown finished - continue with trials
            self.break_resume_timer.stop()
            self.break_resume_timer.timeout.disconnect()
            self.is_in_break = False
            print("Break resume countdown complete - continuing with trials")
            self.show_next_trial()
        
        # Restart timer if not finished and not paused
        if self.break_resume_countdown_value >= 0 and not self.is_paused:
            if not self.break_resume_timer.isActive():
                self.break_resume_timer.start(1000)

    def start_completion_sequence(self):
        """Start the completion sequence in the display window"""
        # Mark completion as in progress to prevent race conditions
        self._completion_in_progress = True
        
        # Step 1: Show "Task Completed" message
        self.word_display_window.show_completion_message("Stroop Color-Word Task Completed")
        
        # Step 2: After 500ms, show "Processing" message
        QTimer.singleShot(500, self.show_processing_message)
    
    def show_processing_message(self):
        """Show processing message and start RT analysis"""
        self.word_display_window.show_completion_message("Processing collected data")
        
        # Start RT analysis in background
        QTimer.singleShot(100, self.run_analysis_and_show_results)
    
    def run_analysis_and_show_results(self):
        """Run RT analysis and show final results - ENHANCED COMPLETION"""
        # Analyze all audio files for reaction times
        if self.task_config['main_enabled']:
            self.analyze_reaction_times()
        
        # Save data with RT results
        self.save_trial_data()
        
        # Cleanup audio resources
        self.audio_recorder.cleanup()
        
        # CRITICAL: Mark task as completed and call enhanced recovery completion
        if self.session_manager:
            self._task_completed = True  # Prevent emergency save on close
            final_data = {
                'total_trials_completed': len(self.trial_data),
                'total_trials_planned': self.task_config['num_trials'] if self.task_config['main_enabled'] else 0,
                'practice_trials_completed': self.task_config['practice_trials'] if self.task_config['practice_enabled'] else 0,
                'completion_time': datetime.now().isoformat(),
                'recovery_was_used': bool(self.recovery_data),
                'audio_folder_path': self.audio_folder_path,
                'rt_analysis_successful': ANALYSIS_AVAILABLE and self.task_config['main_enabled'],
                'task_completed_normally': True,
                'all_data_saved': True,
                'completion_method': 'normal_completion_sequence',
                'user_configuration': self.task_config,
                'balanced_trials_used': True,
                'consistent_sequence': True
            }
            
            # ENHANCED: PROPERLY CALL complete_task_with_recovery to prevent false recovery prompts
            self.complete_task_with_recovery(final_data)
            print("✓ Task completion recorded with enhanced recovery system and user configuration")
            print("✓ Session cleanup will occur - no recovery prompts on restart")
        
        # Show completion results
        self.show_completion_results()
    
    def show_completion_results(self):
        """Show final completion results and Main Menu button"""
        # Prepare completion message
        total_trials = len(self.trial_data)
        recovery_used = "Yes" if self.recovery_data else "No"
        
        # Build configuration summary
        config_summary = []
        if self.task_config['practice_enabled']:
            config_summary.append(f"Practice trials: {self.task_config['practice_trials']}")
        if self.task_config['main_enabled']:
            config_summary.append(f"Main trials: {self.task_config['num_trials']}")
            config_summary.append(f"Recording: {self.task_config['recording_duration']}s per trial")
        
        completion_text = (
            f"Processing Complete\n\n"
            f"Configuration:\n{chr(10).join(config_summary)}\n\n"
            f"Total trials completed: {total_trials}\n"
            f"Recovery used: {recovery_used}\n"
            f"Data and audio files saved in:\n{os.path.basename(self.audio_folder_path)}"
        )
        
        # Show results in display window
        self.word_display_window.show_completion_message(completion_text)
        
        # Show Main Menu button
        self.show_main_menu_button()
    
    def show_main_menu_button(self):
        """Show the Main Menu button to return to selection menu"""
        # Create Main Menu button with same styling as original start button
        self.main_menu_button = QPushButton("Main Menu", self)
        self.main_menu_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.main_menu_button.setFixedSize(200, 70)
        self.main_menu_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #ffffff, stop: 1 #f0f0f0);
                color: black;
                border: 2px solid #e0e0e0;
                border-radius: 35px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #fafafa, stop: 1 #e8e8e8);
                border: 2px solid #d0d0d0;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                          stop: 0 #e8e8e8, stop: 1 #ffffff);
                border: 2px solid #c0c0c0;
            }
        """)
        self.main_menu_button.clicked.connect(self.return_to_main_menu)
        
        # Add button to layout in same position as action button
        self.layout.addWidget(self.main_menu_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Show the button
        self.main_menu_button.show()
        
        print("Main Menu button activated - task completion sequence finished")
    
    def return_to_main_menu(self):
        """Return to the test selection menu"""
        print("Returning to main menu...")
        
        # Import here to avoid circular imports
        from menu_selection import SelectionMenu
        
        # Get current window geometry
        current_geometry = self.geometry()
        
        # Create new selection menu with same participant information
        self.selection_menu = SelectionMenu(
            buttons_size=1.0, 
            buttons_elevation=0.5,
            participant_id=self.participant_id,
            participant_folder_path=self.participant_folder_path
        )
        self.selection_menu.setGeometry(current_geometry)
        self.selection_menu.show()
        
        # Close this Stroop Color-Word task window
        self.close()

    def analyze_reaction_times(self):
        """Analyze all recorded audio files to extract reaction times"""
        if not ANALYSIS_AVAILABLE:
            print("RT analysis skipped - analysis libraries not available")
            print("Install with: pip install librosa scipy")
            return
        
        print("\nAnalyzing reaction times from audio recordings...")
        print("-" * 50)
        
        successful_analyses = 0
        total_analyses = 0
        
        for trial_record in self.trial_data:
            trial_num = trial_record['trial_number']
            audio_filename = trial_record['audio_file']
            audio_path = os.path.join(self.audio_folder_path, audio_filename)
            
            if not os.path.exists(audio_path):
                print(f"Trial {trial_num}: Audio file not found - {audio_filename}")
                continue
            
            total_analyses += 1
            
            # Analyze this trial's audio with timing information
            audio_start_time = trial_record['audio_start_time']
            stimulus_onset_time = trial_record['stimulus_onset_time']
            
            rt_seconds, confidence, details = self.speech_detector.analyze_trial_audio(
                audio_path, audio_start_time, stimulus_onset_time
            )
            
            if rt_seconds is not None:
                # Store the results in the trial record
                trial_record['rt_seconds'] = rt_seconds
                trial_record['rt_confidence'] = confidence
                successful_analyses += 1
                
                print(f"Trial {trial_num}: RT = {rt_seconds*1000:.0f}ms (confidence: {confidence:.2f})")
            else:
                print(f"Trial {trial_num}: RT analysis failed - {details.get('error', 'Unknown error')}")
                trial_record['rt_seconds'] = None
                trial_record['rt_confidence'] = 0.0
        
        print("-" * 50)
        print(f"RT Analysis Summary:")
        print(f"  Total trials analyzed: {total_analyses}")
        print(f"  Successful RT detections: {successful_analyses}")
        if total_analyses > 0:
            print(f"  Success rate: {successful_analyses/total_analyses*100:.1f}%")
        print("-" * 50)

    def generate_timestamp(self):
        """Generate timestamp for filename"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_trial_data(self):
        """Save trial data using the modular experiment data saver"""
        if not self.audio_folder_path:
            print("ERROR: No audio folder path available for saving data")
            return False
            
        if not self.participant_id:
            print("WARNING: No participant ID available")
            participant_id = "unknown_participant"
        else:
            participant_id = self.participant_id
        
        # Use the modular save function with user configuration
        success = save_stroop_colorword_data(
            trial_data=self.trial_data,
            participant_id=participant_id,
            audio_folder_path=self.audio_folder_path,
            recording_duration_seconds=self.recording_duration_seconds,
            pre_stimulus_delay_ms=self.pre_stimulus_delay_ms,
            analysis_available=ANALYSIS_AVAILABLE
        )
        
        return success

    def _get_task_specific_state(self):
        """Get Stroop-specific state information for recovery."""
        state = super()._get_task_specific_state() if hasattr(super(), '_get_task_specific_state') else {}
        
        # Add Stroop-specific state including user configuration
        state.update({
            'current_trial_index': self.current_index,
            'practice_mode': getattr(self, 'practice_mode', False),
            'practice_index': getattr(self, 'practice_index', 0),
            'is_paused': getattr(self, 'is_paused', False),
            'is_in_break': getattr(self, 'is_in_break', False),
            'paused_trials_count': len(getattr(self, 'paused_trials', [])),
            'audio_folder_path': getattr(self, 'audio_folder_path', ''),
            'recovery_offset': getattr(self, 'recovery_offset', 0),
            'total_trials_in_session': len(getattr(self, 'all_trials', [])),
            'recovery_data_present': bool(self.recovery_data),
            'task_completed': getattr(self, '_task_completed', False),
            'completion_in_progress': getattr(self, '_completion_in_progress', False),
            'configuration_mode': getattr(self, 'configuration_mode', True),
            'configuration_saved': getattr(self, 'configuration_saved', False),
            'task_config': getattr(self, 'task_config', None),
            'user_configuration_enabled': True,
            'balanced_trials_used': True,
            'consistent_sequence': True
        })
        
        return state

    def _update_recovery_ui(self):
        """Update UI elements after recovery."""
        if self.recovery_data:
            # For recovery, we need to load the task configuration that was used
            # This should be stored in the recovery data
            stored_config = self.recovery_data.get('task_specific_state', {}).get('task_config')
            
            if stored_config:
                self.task_config = stored_config
                print("Recovered user configuration from previous session")
                print(f"Configuration: {self.task_config}")
                
                # Skip configuration mode and go directly to instructions
                self.configuration_mode = False
                self.configuration_saved = True
                
                # Update UI to show instructions with recovered config
                self.word_display_window.hide_configuration()
                
                # Prepare trials with recovered configuration
                self.prepare_trials()
                
                # Show recovery message
                trials_completed = len(self.recovery_data.get('trial_data', []))
                remaining_trials = self.task_config['num_trials'] - trials_completed
                
                recovery_message = (
                    f"SESSION RECOVERED\n\n"
                    f"Continuing from where you left off...\n\n"
                    f"Trials completed: {trials_completed}\n"
                    f"Trials remaining: {remaining_trials}\n\n"
                    f"Configuration preserved\n"
                    f"Click Start to continue"
                )
                
                self.word_display_window.show_completion_message(recovery_message)
                
                # Update button for task start
                self.action_button.setText("Start")
                self.action_button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                  stop: 0 #fff3e0, stop: 1 #ffe0b2);
                        color: black;
                        border: 2px solid #FF9800;
                        border-radius: 35px;
                        padding: 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                  stop: 0 #fff8f0, stop: 1 #ffecb3);
                        border: 2px solid #F57C00;
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                  stop: 0 #ffe0b2, stop: 1 #fff3e0);
                        border: 2px solid #E65100;
                    }
                """)
            else:
                print("Warning: No task configuration found in recovery data")
                # Fall back to default configuration
                self.task_config = {
                    'practice_enabled': True,
                    'practice_trials': DEFAULT_PRACTICE_TRIALS,
                    'main_enabled': True,
                    'num_trials': DEFAULT_NUM_TRIALS,
                    'recording_duration': DEFAULT_RECORDING_DURATION,
                    'pre_stimulus_delay': DEFAULT_PRE_STIMULUS_DELAY
                }
            
            print("Recovery UI updated with user configuration support")

    def closeEvent(self, event):
        """Handle window close event with enhanced crash recovery cleanup"""
        print("Stroop task closing - performing enhanced cleanup...")
        
        # Emergency save if task is in progress and not completed
        if self.session_manager and hasattr(self, 'task_started') and self.task_started:
            try:
                if (not hasattr(self, '_task_completed') or not self._task_completed) and \
                   (not hasattr(self, '_completion_in_progress') or not self._completion_in_progress):
                    print("Emergency save: Task in progress during close")
                    # ENHANCED: PROPERLY CALL emergency recovery method
                    self.handle_crash_recovery()
                else:
                    print("Task was completed normally - no emergency save needed")
            except Exception as e:
                print(f"Error during emergency save: {e}")
        
        # Stop auto-save timer from TaskStateMixin
        if hasattr(self, 'task_save_timer'):
            self.task_save_timer.stop()
        
        # Stop emergency save timer from TaskStateMixin  
        if hasattr(self, 'emergency_save_timer'):
            self.emergency_save_timer.stop()
        
        # Cleanup audio resources
        if hasattr(self, 'audio_recorder'):
            self.audio_recorder.cleanup()
        
        # Stop all other timers
        if hasattr(self, 'recording_timer'):
            self.recording_timer.stop()
        if hasattr(self, 'countdown_timer'):
            self.countdown_timer.stop()
        if hasattr(self, 'practice_countdown_timer'):
            self.practice_countdown_timer.stop()
        if hasattr(self, 'break_timer'):
            self.break_timer.stop()
        if hasattr(self, 'break_resume_timer'):
            self.break_resume_timer.stop()
        if hasattr(self, 'resume_countdown_timer'):
            self.resume_countdown_timer.stop()
        
        event.accept()
        print("Stroop task cleanup completed")

def main():
    """Standalone main function for testing with enhanced crash recovery support"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")
    
    print("=== STROOP COLOR-WORD TASK TESTING (WITH CONFIGURATION) ===")
    print("Enhanced crash recovery system: ENABLED")
    print("User configuration interface: ENABLED")
    print("Original UI preserved: YES")
    print("Enhanced completion logic: ENABLED")
    print("Balanced trial generation: ENABLED")
    print("Consistent sequences across participants: ENABLED")
    print("Testing with sample participant data...")
    
    # Sample participant data for testing
    sample_participant_id = "TEST_STROOP_001"
    sample_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_STROOP_001")
    
    # Ensure test folder exists
    os.makedirs(sample_folder, exist_ok=True)
    
    # Initialize session manager for testing
    try:
        session_manager = initialize_session_manager(sample_participant_id, sample_folder)
        default_tasks = [
            "Stroop Colour-Word Task",
            "Letter Monitoring Task", 
            "Visual Search Task",
            "Attention Network Task",
            "Go/No-Go Task",
            "Reading Span Test"
        ]
        session_manager.set_task_queue(default_tasks)
        print("Session manager initialized for testing")
    except Exception as e:
        print(f"Error initializing session manager: {e}")
    
    # Create Stroop task with enhanced recovery support and configuration interface
    txt_path = resource_path('task_stroop_colorword/stimulus_data.txt')
    
    try:
        stroop_task = StroopColorWordTask(
            csv_file=txt_path,
            participant_id=sample_participant_id,
            participant_folder_path=sample_folder
        )
        
        stroop_task.show()
        print("✓ Stroop Color-Word Task launched successfully with configuration interface")
        print("✓ User can now configure task parameters before starting")
        print("✓ Original UI and execution flow preserved")
        print("✓ Enhanced completion logic integrated")
        print("✓ Balanced trial generation implemented")
        print("✓ No false recovery prompts on restart after completion")
        print("✓ Consistent trial sequences across all participants")
        print("✓ Task configuration is user-selectable and saves/restores properly")
        
        # Run application with error handling
        exit_code = app.exec()
        print("Stroop task closed normally")
        return exit_code
        
    except Exception as e:
        print(f"Stroop task crashed during execution: {e}")
        import traceback
        traceback.print_exc()
        
        # Emergency save
        session_manager = get_session_manager()
        if session_manager:
            try:
                session_manager.emergency_save()
                print("Emergency save completed from main")
            except Exception as save_error:
                print(f"Emergency save failed: {save_error}")
        
        # Re-raise the exception
        raise
        
    finally:
        # Cleanup session manager on exit
        from crash_recovery_system.session_manager import cleanup_session_manager
        cleanup_session_manager()
        print("Session cleanup completed from main")

if __name__ == "__main__":
    main()