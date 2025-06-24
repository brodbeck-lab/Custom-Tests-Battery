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
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

# Import the modular save function
from experiment_data_saver import save_stroop_colorword_data

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
# STROOP COLOR-WORD TASK CONFIGURATION
# =============================================================================
# Control the number of trials to be presented
# Set this to the desired number of random color word trials
# Examples: 12 (short), 24 (medium), 48 (long), 80 (full dataset), 96 (extensive)
NUM_TRIALS = 10  # ← CHANGE THIS VALUE to control how many trials are shown (set to 80 for full dataset)

# Control the audio recording duration per trial (in seconds)
# How long to record audio for each color word trial
RECORDING_DURATION_SECONDS = 3.0  # ← CHANGE THIS VALUE to control recording length

# Control the delay before presenting the color word stimulus (in milliseconds)
# Audio recording starts this many milliseconds before stimulus appears
PRE_STIMULUS_DELAY_MS = 200  # ← CHANGE THIS VALUE to control pre-stimulus recording time

# Available stimuli for random trial generation  
# You can add more words/colors here to increase variety
STROOP_COLORWORD_WORDS = ['RED', 'BLUE', 'GREEN', 'YELLOW']
STROOP_COLORWORD_COLORS = ['red', 'blue', 'green', 'yellow']
# Maximum unique combinations possible: 4 words × 4 colors = 16 combinations

# NOTE: Application now uses 'stroop_colorword_list.txt' instead of 'stroop_colorword_list.csv'
# TXT format loads faster in compiled exe/dmg formats while maintaining CSV structure
# PRACTICE TRIALS: 6 practice trials (2 congruent, 2 incongruent, 2 neutral) run before main task
# NEW: ALL PARTICIPANTS GET IDENTICAL TRIAL SEQUENCES (balanced and consistent)
# =============================================================================

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
    """Child window that displays the Stroop Color-Word task stimuli"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stroop Color-Word Display")
        self.setFixedSize(1300, 760)
        
        # Create layout for the child window
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the label that will display the text
        self.display_label = QLabel("Click the Start button to begin the Stroop Color-Word Task\n\nYou will start with 6 practice trials,\nthen complete 80 main trials with audio recording.\n\nYou must say aloud the COLOR of the ink, not the word itself", self)
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
        
        layout.addWidget(self.display_label)
        self.setLayout(layout)
    
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
    
    def show_instructions(self):
        """Show initial instructions"""
        self.display_label.setText("Click the Start button to begin the Stroop Color-Word Task\n\nYou will start with 6 practice trials,\nthen complete 80 main trials with audio recording.\n\nYou must say aloud the COLOR of the ink, not the word itself")
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
    """Stroop Color-Word Task with comprehensive crash recovery support and balanced trial generation"""
    
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
        
        # Use the configured recording duration from the configuration section
        self.recording_duration_seconds = RECORDING_DURATION_SECONDS
        self.recording_duration_ms = int(self.recording_duration_seconds * 1000)
        
        print(f"=== STROOP COLOR-WORD TASK INITIALIZATION ===")
        print(f"Received participant_id: '{participant_id}' (type: {type(participant_id)})")
        print(f"Received participant_folder_path: '{participant_folder_path}' (type: {type(participant_folder_path)})")
        print(f"Recovery mode: {'ENABLED' if self.recovery_data else 'DISABLED'}")
        print(f"Session manager: {'AVAILABLE' if self.session_manager else 'NOT AVAILABLE'}")
        print(f"Recording duration: {self.recording_duration_seconds} seconds ({self.recording_duration_ms} ms) [from config: RECORDING_DURATION_SECONDS]")
        print(f"Number of main trials configured: {NUM_TRIALS}")
        print(f"Practice trials: 6 (2 congruent, 2 incongruent, 2 neutral) - no recording")
        print(f"Pre-stimulus delay: {PRE_STIMULUS_DELAY_MS}ms [from config: PRE_STIMULUS_DELAY_MS]")
        print(f"Stimulus file: stroop_colorword_list.txt (TXT format for faster exe/dmg loading)")
        print(f"Stimulus onset timing: FRAME FLIP METHOD (PyQt6 update/repaint + time.perf_counter)")
        print(f"Audio recording starts {PRE_STIMULUS_DELAY_MS}ms before stimulus presentation")
        print(f"Frame flip equivalent: widget.update() + widget.repaint() + immediate timestamp")
        print(f"Automatic RT analysis: {'ENABLED' if ANALYSIS_AVAILABLE else 'DISABLED - install librosa and scipy'}")
        print(f"Crash recovery: {'ENABLED' if self.session_manager else 'DISABLED'}")
        print(f"NEW: Balanced trial generation - all participants get identical sequences")
        print(f"==================================")
        
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
        
        # Resume countdown variables
        self.resume_countdown_timer = QTimer()
        self.resume_countdown_value = 3
        
        # Break period variables
        self.break_timer = QTimer()
        self.break_countdown_value = 20
        self.break_resume_timer = QTimer()
        self.break_resume_countdown_value = 3
        self.is_in_break = False
        
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
        # Center the window on the screen (the entire if-else statement)
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
            csv_file = resource_path('stroop_colorword_list.txt')
        
        try:
            self.df = pd.read_csv(csv_file)  # pandas can read TXT files with CSV format
            print(f"Successfully loaded Stroop Color-Word task data from: {csv_file}")
            print(f"TXT columns: {list(self.df.columns)}")
            print(f"Total trials in TXT: {len(self.df)}")
            
        except Exception as e:
            # If TXT file is not found, create sample data for demonstration
            print(f"Could not load 'stroop_colorword_list.txt': {e}")
            print(f"Creating balanced sample Stroop Color-Word task data...")
            self.create_sample_data()
        
        self.prepare_trials()
        
        # Create layout with reduced left/right margins for larger child window
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 50, 10, 50)  # left, top, right, bottom
        
        # Create child window for displaying words (replaces the QLabel)
        self.word_display_window = StroopColorWordDisplayWindow(self)
        
        # Create start button with neumorphic styling to match the app
        self.start_button = QPushButton("Start", self)
        self.start_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.start_button.setFixedSize(200, 70)
        self.start_button.setStyleSheet("""
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
        self.start_button.clicked.connect(self.start_button_clicked)
        
        # Create pause/continue button (initially hidden)
        self.pause_button = QPushButton("Pause", self)
        self.pause_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.pause_button.setFixedSize(200, 70)
        self.pause_button.setStyleSheet("""
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
        self.pause_button.clicked.connect(self.pause_button_clicked)
        self.pause_button.hide()  # Initially hidden
        
        # Add widgets to layout with proper centering
        self.layout.addStretch()
        
        # Center the child window
        self.layout.addWidget(self.word_display_window, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addSpacing(30)
        
        # Center the start button (pause button will replace it)
        self.layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.pause_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add bottom stretch for better centering
        self.layout.addStretch()
        
        self.setLayout(self.layout)
        
        # Initialize trial state
        self.current_index = 0
        self.task_started = False
        self.practice_mode = False
        self.practice_trials = []
        self.practice_index = 0
        self.countdown_timer = QTimer()
        self.countdown_value = 5
        
        # Practice countdown timer
        self.practice_countdown_timer = QTimer()
        self.practice_countdown_value = 3
        
        # Create practice trials
        self.create_practice_trials()
        
        # Initialize recovery AFTER all other initialization
        if self.session_manager:
            print("Task recovery system activated")
            # Update UI for recovery if needed
            if self.recovery_data:
                QTimer.singleShot(100, self._update_recovery_ui)
        else:
            print("WARNING: Session manager not available - recovery disabled")

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
        """Prepare balanced trials with consistent sequence across all participants"""
        print("=== PREPARING BALANCED TRIALS WITH CONSISTENT SEQUENCE ===")
        
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
            remaining_trials_needed = NUM_TRIALS - trials_completed
            
            if remaining_trials_needed > 0:
                print(f"Preparing {remaining_trials_needed} remaining trials...")
                # Get the full sequence and take only the remaining portion
                full_sequence = self.create_balanced_trial_sequence(NUM_TRIALS)
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
            
            # Create the balanced trial sequence
            self.all_trials = self.create_balanced_trial_sequence(NUM_TRIALS)
            self.current_index = 0
        
        print(f"Prepared {len(self.all_trials)} trials for Stroop Color-Word task")
        print(f"Starting from trial index: {self.current_index}")
        if hasattr(self, 'recovery_offset'):
            print(f"Recovery offset: {self.recovery_offset}")
        print("===============================================")

    def create_balanced_trial_sequence(self, num_trials):
        """
        Create a balanced trial sequence that's consistent across all participants.
        
        Rules:
        1. If num_trials <= 80: Select balanced subset
        2. If num_trials > 80: Use all 80 + balanced additional trials
        3. Same sequence for all participants
        """
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
        """Create 6 practice trials: 2 congruent, 2 incongruent, 2 neutral"""
        practice_trials = []
        
        # Create 2 congruent trials
        congruent_options = [
            {'condition1': 'congruent', 'stim1': 'RED', 'textColor': 'red'},
            {'condition1': 'congruent', 'stim1': 'BLUE', 'textColor': 'blue'},
            {'condition1': 'congruent', 'stim1': 'GREEN', 'textColor': 'green'},
            {'condition1': 'congruent', 'stim1': 'YELLOW', 'textColor': 'yellow'}
        ]
        
        # Create 2 incongruent trials  
        incongruent_options = [
            {'condition1': 'incongruent', 'stim1': 'RED', 'textColor': 'blue'},
            {'condition1': 'incongruent', 'stim1': 'BLUE', 'textColor': 'green'},
            {'condition1': 'incongruent', 'stim1': 'GREEN', 'textColor': 'yellow'},
            {'condition1': 'incongruent', 'stim1': 'YELLOW', 'textColor': 'red'}
        ]
        
        # Create 2 neutral trials
        neutral_options = [
            {'condition1': 'neutral', 'stim1': 'DEEP', 'textColor': 'red'},
            {'condition1': 'neutral', 'stim1': 'LEGAL', 'textColor': 'blue'},
            {'condition1': 'neutral', 'stim1': 'POOR', 'textColor': 'green'},
            {'condition1': 'neutral', 'stim1': 'BAD', 'textColor': 'yellow'}
        ]
        
        # Use fixed random seed for consistent practice trials across participants
        random.seed(999)  # Fixed seed for practice trials
        practice_trials.extend(random.sample(congruent_options, 2))
        practice_trials.extend(random.sample(incongruent_options, 2))
        practice_trials.extend(random.sample(neutral_options, 2))
        
        # Randomize the order of all 6 practice trials with fixed seed
        random.shuffle(practice_trials)
        self.practice_trials = practice_trials
        
        print(f"Created 6 practice trials (consistent across participants):")
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

    def start_button_clicked(self):
        """Handle start button click with recovery awareness"""
        if not self.task_started:
            # First click - check if this is recovery mode
            if self.recovery_data:
                # Recovery mode - go directly to main task
                print("Starting task in recovery mode - skipping practice")
                self.task_started = True
                self.start_button.hide()
                self.pause_button.show()
                self.show_recovery_instructions()
            else:
                # Normal mode - start with practice instructions
                print("Starting task in normal mode - beginning with practice")
                self.task_started = True
                self.start_button.hide()
                self.pause_button.show()
                self.show_practice_instructions()

    def show_recovery_instructions(self):
        """Show instructions for recovery mode"""
        if self.is_paused:
            return
        
        trials_completed = len(self.trial_data)
        remaining_trials = NUM_TRIALS - trials_completed
        
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
            remaining_trials = NUM_TRIALS - trials_completed
            
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

    def pause_button_clicked(self):
        """Handle pause/continue button click"""
        if self.is_paused:
            # Currently paused - resume
            self.resume_task()
        else:
            # Currently running - pause
            self.pause_task()

    def pause_task(self):
        """Pause the current task with recovery support"""
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
        self.pause_button.setText("Continue")
        self.pause_button.setStyleSheet("""
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
        
        # Stop any active timers
        if hasattr(self, 'practice_countdown_timer') and self.practice_countdown_timer.isActive():
            self.practice_countdown_timer.stop()
            print("Practice countdown timer paused")
        
        if hasattr(self, 'countdown_timer') and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            print("Main countdown timer paused")
        
        if hasattr(self, 'break_timer') and self.break_timer.isActive():
            self.break_timer.stop()
            print("Break timer paused")
        
        if hasattr(self, 'break_resume_timer') and self.break_resume_timer.isActive():
            self.break_resume_timer.stop()
            print("Break resume timer paused")
        
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
        self.pause_button.setText("Pause")
        self.pause_button.setStyleSheet("""
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
        
        # If we paused during recording in main task, move to back of queue and advance
        if self.paused_during_recording and not self.practice_mode:
            print("Resuming after recording pause - advancing to next trial")
            self.advance_to_next_trial_after_pause()
        elif self.is_in_break:
            # We were in a break period
            print("Resuming break period")
            if self.break_countdown_value > 0:
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
                self.update_practice_countdown()
            else:
                # Resume practice trial
                self.show_next_practice_trial()
        else:
            # We were in main task but not during recording
            print("Resuming main task")
            if hasattr(self, 'countdown_value') and self.countdown_value > 0:
                # Resume main countdown
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

    def show_practice_instructions(self):
        """Show instructions for practice trials"""
        if self.is_paused:
            return
            
        self.word_display_window.show_completion_message(
            "PRACTICE TRIALS\n\n"
            "The next 6 trials are for practice.\n\n"
            "Remember: Say aloud the COLOR of the ink,\n"
            "not the word itself.\n\n"
            "Practice trials will begin in 3 seconds..."
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
                "PRACTICE TRIALS\n\n"
                "The next 6 trials are for practice.\n\n"
                "Remember: Say aloud the COLOR of the ink,\n"
                "not the word itself.\n\n"
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
            # Practice completed - show preparation for main task
            print("=== PRACTICE COMPLETED ===")
            self.show_main_task_preparation()
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
            "PRACTICE COMPLETE!\n\n"
            "Great job! Now get ready for the real task.\n\n"
            f"The main experiment will have {NUM_TRIALS} trials.\n"
            "Audio will be recorded for reaction time analysis.\n\n"
            "Remember: Say the COLOR, not the word!\n\n"
            "Starting in 5 seconds..."
        )
        
        print("=== MAIN TASK PREPARATION ===")
        print("Practice completed successfully")
        print(f"Preparing for main task with {NUM_TRIALS} trials...")
        
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
                "PRACTICE COMPLETE!\n\n"
                "Great job! Now get ready for the real task.\n\n"
                f"The main experiment will have {NUM_TRIALS} trials.\n"
                "Audio will be recorded for reaction time analysis.\n\n"
                "Remember: Say the COLOR, not the word!\n\n"
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
                'total_trials': NUM_TRIALS,
                'recording_duration_seconds': self.recording_duration_seconds,
                'pre_stimulus_delay_ms': PRE_STIMULUS_DELAY_MS,
                'recovery_mode': bool(self.recovery_data),
                'audio_folder_path': self.audio_folder_path,
                'balanced_trials': True,
                'consistent_sequence': True
            }
            
            if not self.recovery_data:
                # Starting new task - PROPERLY CALL start_task_with_recovery
                self.start_task_with_recovery(task_config, NUM_TRIALS)
                print("Started new main task with enhanced recovery support and balanced trials")
            else:
                # Resuming from recovery - ensure auto-save is active
                print("Resuming main task from recovery data with balanced trials")
                self.task_started = True
                # Ensure auto-save is started
                self._start_auto_save_system()
        
        print("Beginning recorded trials with balanced sequence...")
        self.show_next_trial()

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
                
                self.pause_button.hide()
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
        QTimer.singleShot(PRE_STIMULUS_DELAY_MS, lambda: self.display_stimulus_with_timing(word, color))

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
                'total_trials_planned': NUM_TRIALS,
                'completion_time': datetime.now().isoformat(),
                'recovery_was_used': bool(self.recovery_data),
                'audio_folder_path': self.audio_folder_path,
                'rt_analysis_successful': ANALYSIS_AVAILABLE,
                'task_completed_normally': True,
                'all_data_saved': True,
                'completion_method': 'normal_completion_sequence',
                'balanced_trials_used': True,
                'consistent_sequence': True
            }
            
            # ENHANCED: PROPERLY CALL complete_task_with_recovery to prevent false recovery prompts
            self.complete_task_with_recovery(final_data)
            print("✓ Task completion recorded with enhanced recovery system")
            print("✓ Session cleanup will occur - no recovery prompts on restart")
        
        # Show completion results
        self.show_completion_results()
    
    def show_completion_results(self):
        """Show final completion results and Main Menu button"""
        # Prepare completion message
        total_trials = len(self.trial_data)
        recovery_used = "Yes" if self.recovery_data else "No"
        
        completion_text = (
            f"Processing Complete\n\n"
            f"Total trials: {total_trials}\n"
            f"Recovery used: {recovery_used}\n"
            f"Balanced sequence: Consistent across participants\n"
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
        
        # Add button to layout in same position as start button
        self.layout.addWidget(self.main_menu_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Show the button
        self.main_menu_button.show()
        
        print("Main Menu button activated - task completion sequence finished")
    
    def return_to_main_menu(self):
        """Return to the test selection menu"""
        print("Returning to main menu...")
        
        # Import here to avoid circular imports
        from selection_menu import SelectionMenu
        
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
        print(f"  Expected offset: ~0.200 seconds")

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
        
        # Stop recording after the specified duration
        QTimer.singleShot(self.recording_duration_ms, self.stop_current_recording)

    def record_audio_chunk(self):
        """Record a chunk of audio"""
        if self.recording_active and self.audio_recorder.is_recording and not self.is_paused:
            self.audio_recorder.record_chunk()

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
            'consistent_across_participants': True
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
        
        # Use the modular save function
        success = save_stroop_colorword_data(
            trial_data=self.trial_data,
            participant_id=participant_id,
            audio_folder_path=self.audio_folder_path,
            recording_duration_seconds=self.recording_duration_seconds,
            pre_stimulus_delay_ms=PRE_STIMULUS_DELAY_MS,
            analysis_available=ANALYSIS_AVAILABLE
        )
        
        return success

    def _get_task_specific_state(self):
        """Get Stroop-specific state information for recovery."""
        state = super()._get_task_specific_state() if hasattr(super(), '_get_task_specific_state') else {}
        
        # Add Stroop-specific state
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
            'balanced_trials_used': True,
            'consistent_sequence': True
        })
        
        return state

    def _update_recovery_ui(self):
        """Update UI elements after recovery."""
        if self.recovery_data:
            # Show recovery message in display window
            trials_completed = len(self.recovery_data.get('trial_data', []))
            remaining_trials = NUM_TRIALS - trials_completed
            
            recovery_message = (
                f"SESSION RECOVERED\n\n"
                f"Continuing from where you left off...\n\n"
                f"Trials completed: {trials_completed}\n"
                f"Trials remaining: {remaining_trials}\n\n"
                f"Balanced sequence preserved\n"
                f"Click Start to continue"
            )
            
            if hasattr(self, 'word_display_window'):
                self.word_display_window.show_completion_message(recovery_message)
            
            print("Recovery UI updated with balanced trial information")

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
    
    print("=== STROOP COLOR-WORD TASK TESTING ===")
    print("Enhanced crash recovery system: ENABLED")
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
    
    # Create Stroop task with enhanced recovery support
    txt_path = resource_path('stroop_colorword_list.txt')
    
    try:
        stroop_task = StroopColorWordTask(
            csv_file=txt_path,
            participant_id=sample_participant_id,
            participant_folder_path=sample_folder
        )
        
        stroop_task.show()
        print("✓ Stroop Color-Word Task launched successfully")
        print("✓ Original UI and execution flow preserved")
        print("✓ Enhanced completion logic integrated")
        print("✓ Balanced trial generation implemented")
        print("✓ No false recovery prompts on restart after completion")
        print("✓ Consistent trial sequences across all participants")
        
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