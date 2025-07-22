#!/usr/bin/env python3
"""
READING SPAN TASK - WITH FULL CRASH RECOVERY SYSTEM IMPLEMENTATION
Fixed sentence loading, block progression, recall interface, and COMPLETE crash recovery
"""

import sys
import os
import pandas as pd
import random
import time
from datetime import datetime

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFrame, QCheckBox,
                               QSpinBox, QGridLayout, QMessageBox, QScrollArea, 
                               QSizePolicy, QSpacerItem, QLineEdit, QTextEdit)
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QPixmap, QPalette, QBrush, QKeyEvent, QMouseEvent
    print("✓ PyQt6 imports successful")
except ImportError as e:
    print(f"⚠ PyQt6 import error: {e}")
    sys.exit(1)

# Import crash recovery system
try:
    from crash_recovery_system.session_manager import get_session_manager, initialize_session_manager
    from crash_recovery_system.task_state_saver import TaskStateMixin, CrashDetector
    RECOVERY_SYSTEM_AVAILABLE = True
    print("✓ Reading Span Task: Crash recovery system loaded successfully")
except ImportError as e:
    RECOVERY_SYSTEM_AVAILABLE = False
    print(f"⚠ Reading Span Task: Crash recovery system not available - {e}")

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class ReadingSpanDisplayWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(1350, 860)

        # Main layout (no extra top-margin so card sits up high)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Display label (for later)
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.display_label)

        # Configuration widget
        self.config_widget = self.create_configuration_widget()
        self.layout.addWidget(self.config_widget)

        # Recall widget (for later)
        self.recall_widget = self.create_recall_widget()
        self.layout.addWidget(self.recall_widget)

        # Wire up checkboxes → handlers
        self.practice_checkbox.stateChanged.connect(self.on_practice_changed)
        self.main_checkbox    .stateChanged.connect(self.on_main_changed)

        # Initialize enable/disable based on default-checked
        self.practice_checkbox.setChecked(True)
        self.main_checkbox.setChecked(True)
        self.on_practice_changed(self.practice_checkbox.checkState())
        self.on_main_changed    (self.main_checkbox.checkState())

        # Hide until needed
        self.display_label.hide()
        self.recall_widget.hide()
        self.config_widget.hide()
        self.setLayout(self.layout)


    def create_configuration_widget(self):
        """Create the configuration interface widget with CVC-style UI features"""
        config_widget = QWidget()
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(40, 20, 40, 20)

        # Header
        title_label = QLabel("Reading Span Task Configuration")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(title_label)

        # Card container
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

        # Practice Trials
        practice_header = QHBoxLayout()
        self.practice_checkbox = QCheckBox("Practice Trials")
        self.practice_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        practice_header.addWidget(self.practice_checkbox)
        practice_header.addStretch()
        frame_layout.addLayout(practice_header)

        practice_grid = QGridLayout()
        practice_grid.setSpacing(15)
        # Number of practice sets
        lbl_ps = QLabel("Number of practice sets:")
        lbl_ps.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        practice_grid.addWidget(lbl_ps, 0, 0)
        self.practice_sets_spinbox = QSpinBox()
        self.practice_sets_spinbox.setRange(1, 2)
        self.practice_sets_spinbox.setValue(2)
        practice_grid.addWidget(self.practice_sets_spinbox, 0, 1)
        # Sentence duration
        lbl_pd = QLabel("Sentence duration (ms):")
        lbl_pd.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        practice_grid.addWidget(lbl_pd, 1, 0)
        self.practice_duration_spinbox = QSpinBox()
        self.practice_duration_spinbox.setRange(1000, 8000)
        self.practice_duration_spinbox.setValue(4000)
        practice_grid.addWidget(self.practice_duration_spinbox, 1, 1)
        frame_layout.addLayout(practice_grid)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #bdc3c7; margin: 10px 0px;")
        frame_layout.addWidget(sep)

        # Main Trials
        main_header = QHBoxLayout()
        self.main_checkbox = QCheckBox("Main Trials")
        self.main_checkbox.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        main_header.addWidget(self.main_checkbox)
        main_header.addStretch()
        frame_layout.addLayout(main_header)

        main_grid = QGridLayout()
        main_grid.setSpacing(15)
        # Number of series
        lbl_ms = QLabel("Number of series:")
        lbl_ms.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        main_grid.addWidget(lbl_ms, 0, 0)
        self.main_series_spinbox = QSpinBox()
        self.main_series_spinbox.setRange(1, 5)
        self.main_series_spinbox.setValue(5)
        main_grid.addWidget(self.main_series_spinbox, 0, 1)
        # Sentence duration
        lbl_md = QLabel("Sentence duration (ms):")
        lbl_md.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        main_grid.addWidget(lbl_md, 1, 0)
        self.main_duration_spinbox = QSpinBox()
        self.main_duration_spinbox.setRange(1000, 8000)
        self.main_duration_spinbox.setValue(5000)
        main_grid.addWidget(self.main_duration_spinbox, 1, 1)
        frame_layout.addLayout(main_grid)

        config_frame.setLayout(frame_layout)
        config_layout.addWidget(config_frame)
        config_widget.setLayout(config_layout)
        return config_widget


    def on_practice_changed(self, state):
        """Enable/disable practice spinboxes based on checkbox"""
        enabled = self.practice_checkbox.isChecked()
        self.practice_sets_spinbox.setEnabled(enabled)
        self.practice_duration_spinbox.setEnabled(enabled)

    def on_main_changed(self, state):
        """Enable/disable main spinboxes based on checkbox"""
        enabled = self.main_checkbox.isChecked()
        self.main_series_spinbox.setEnabled(enabled)
        self.main_duration_spinbox.setEnabled(enabled)


    def create_recall_widget(self):
        """Create the word selection recall interface"""
        recall_widget = QWidget()
        recall_layout = QVBoxLayout()
        recall_layout.setContentsMargins(40, 20, 40, 20)
        
        # Recall instructions
        self.recall_instruction_label = QLabel()
        self.recall_instruction_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.recall_instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recall_instruction_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                padding: 20px;
                margin: 10px;
            }
        """)
        recall_layout.addWidget(self.recall_instruction_label)
        
        # Selected words display
        self.selected_words_label = QLabel("Selected words: ")
        self.selected_words_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.selected_words_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_words_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #ffffff;
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
        """)
        recall_layout.addWidget(self.selected_words_label)
        
        # Word selection grid
        self.word_selection_layout = QGridLayout()
        recall_layout.addLayout(self.word_selection_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        # Clear selection button
        self.clear_selection_button = QPushButton("Clear Selection")
        self.clear_selection_button.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.clear_selection_button.setFixedSize(160, 50)
        self.clear_selection_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: 2px solid #e67e22;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
                border: 2px solid #d35400;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
        """)
        self.clear_selection_button.clicked.connect(self.clear_word_selection)
        button_layout.addWidget(self.clear_selection_button)
        
        button_layout.addStretch()
        
        # Submit recall button
        self.submit_recall_button = QPushButton("Submit Recall")
        self.submit_recall_button.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.submit_recall_button.setFixedSize(160, 50)
        self.submit_recall_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: 2px solid #229954;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
                border: 2px solid #1e8449;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
                border: 2px solid #7f8c8d;
            }
        """)
        self.submit_recall_button.setEnabled(False)
        button_layout.addWidget(self.submit_recall_button)
        
        recall_layout.addLayout(button_layout)
        recall_widget.setLayout(recall_layout)
        return recall_widget
    
    def word_button_clicked(self, word):
        """Handle word button click"""
        if word not in self.selected_words:
            self.selected_words.append(word)
            
            # Update button appearance
            for button in self.word_buttons:
                if button.text() == word:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #3498db;
                            color: white;
                            border: 2px solid #2980b9;
                            border-radius: 8px;
                            padding: 8px;
                            font-weight: bold;
                        }
                    """)
                    button.setEnabled(False)
                    break
            
            # Update display and check if we can submit
            self.update_selected_words_display()
            if len(self.selected_words) == self.expected_word_count:
                self.submit_recall_button.setEnabled(True)
    
    def clear_word_selection(self):
        """Clear all selected words"""
        self.selected_words = []
        
        # Reset all buttons
        for button in self.word_buttons:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    border: 2px solid #bdc3c7;
                    border-radius: 8px;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                    border: 2px solid #85929e;
                }
                QPushButton:pressed {
                    background-color: #aeb6bf;
                }
            """)
            button.setEnabled(True)
        
        # Update display and disable submit button
        self.update_selected_words_display()
        self.submit_recall_button.setEnabled(False)
    
    def update_selected_words_display(self):
        """Update the display of selected words"""
        if self.selected_words:
            words_text = " → ".join(self.selected_words)
            display_text = f"Selected words ({len(self.selected_words)}/{self.expected_word_count}): {words_text}"
        else:
            display_text = f"Selected words (0/{self.expected_word_count}): None"
        
        self.selected_words_label.setText(display_text)
    
    def get_recall_response(self):
        """Get and process recall response from word selection"""
        user_words = self.selected_words.copy()
        expected_words = [word.lower() for word in self.expected_words]
        
        # Calculate accuracy
        correct_count = 0
        correct_positions = 0
        
        for i, user_word in enumerate(user_words):
            if i < len(expected_words):
                if user_word.lower() == expected_words[i]:
                    correct_positions += 1
                if user_word.lower() in expected_words:
                    correct_count += 1
        
        return user_words, correct_count, correct_positions
    
    def show_instructions(self, config):
        """Show task instructions"""
        self.recall_widget.hide()
        self.display_label.show()
        
        practice_text = f"practice with {config['practice_sets']} sets, then " if config['practice_enabled'] else ""
        main_text = f"complete {config['main_series']} series of trials" if config['main_enabled'] else ""
        
        instruction_text = f"""Reading Span Task Instructions

    You will {practice_text}{main_text}.

    Your task:
    1. Read each sentence carefully
    2. Remember the FINAL WORD of each sentence
    3. After all sentences in a block, SELECT the final words IN ORDER

    Each series contains 5 blocks with different numbers of sentences (2-6 sentences per block).

    During recall:
    • Click words in the order they appeared
    • Use "Clear Selection" to start over
    • Take your time - there is no time limit
    • Submit when you have selected the correct number of words

    Configuration:
    • Sentence duration: {config.get('main_sentence_duration', 5000)}ms

    Click Start when ready."""
        
        self.display_label.setText(instruction_text)
        self.display_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
    
    def show_completion_message(self, message):
        """Display completion message"""
        self.recall_widget.hide()
        self.display_label.show()
        self.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.display_label.setText(message)
    
    def create_word_selection_buttons(self, target_words):
        """Create clickable word buttons with targets and distractors"""
        # Clear existing buttons
        for i in reversed(range(self.word_selection_layout.count())):
            child = self.word_selection_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Generate distractor words
        all_words = self.generate_distractor_words(target_words)
        
        # Create buttons in a grid layout
        buttons_per_row = 4
        for i, word in enumerate(all_words):
            row = i // buttons_per_row
            col = i % buttons_per_row
            
            button = QPushButton(word)
            button.setFont(QFont('Arial', 12, QFont.Weight.Bold))
            button.setFixedSize(140, 50)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    border: 2px solid #bdc3c7;
                    border-radius: 8px;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                    border: 2px solid #85929e;
                }
                QPushButton:pressed {
                    background-color: #aeb6bf;
                }
            """)
            
            # Connect button click
            button.clicked.connect(lambda checked, w=word: self.word_button_clicked(w))
            
            self.word_selection_layout.addWidget(button, row, col)
            self.word_buttons.append(button)
    
    def generate_distractor_words(self, target_words):
        """Generate distractor words along with target words"""
        # Predefined distractor pool - common words that could appear in sentences
        distractor_pool = [
            'house', 'table', 'chair', 'book', 'door', 'window', 'car', 'tree',
            'flower', 'water', 'fire', 'light', 'sound', 'music', 'voice', 'hand',
            'foot', 'head', 'face', 'heart', 'mind', 'time', 'day', 'night',
            'sun', 'moon', 'star', 'cloud', 'rain', 'wind', 'snow', 'ice',
            'cat', 'dog', 'bird', 'fish', 'horse', 'cow', 'pig', 'sheep',
            'red', 'blue', 'green', 'yellow', 'black', 'white', 'brown', 'gray',
            'big', 'small', 'long', 'short', 'high', 'low', 'fast', 'slow',
            'hot', 'cold', 'warm', 'cool', 'soft', 'hard', 'smooth', 'rough',
            'happy', 'sad', 'angry', 'calm', 'loud', 'quiet', 'bright', 'dark',
            'new', 'old', 'young', 'clean', 'dirty', 'full', 'empty', 'open'
        ]
        
        # Remove target words from distractor pool to avoid duplicates
        available_distractors = [word for word in distractor_pool 
                               if word.lower() not in [tw.lower() for tw in target_words]]
        
        # Calculate number of distractors needed
        total_buttons = 16  # 4x4 grid
        num_distractors = total_buttons - len(target_words)
        
        # Select random distractors
        if len(available_distractors) >= num_distractors:
            selected_distractors = random.sample(available_distractors, num_distractors)
        else:
            selected_distractors = available_distractors
        
        # Combine target words and distractors
        all_words = target_words + selected_distractors
        
        # Shuffle the order
        random.shuffle(all_words)
        
        return all_words
    
    def hide_configuration(self):
        """Hide the configuration interface"""
        self.config_widget.hide()
        self.display_label.show()
    
    def show_configuration(self):
        """Show the configuration interface"""
        self.display_label.hide()
        self.recall_widget.hide()
        self.config_widget.show()
    
    def show_sentence(self, sentence):
        """Display a sentence during the task"""
        self.recall_widget.hide()
        self.display_label.show()
        self.display_label.setFont(QFont('Arial', 24))
        self.display_label.setText(sentence)
    
    def show_recall_interface(self, block_info, expected_words):
        """Show the word selection recall interface"""
        self.display_label.hide()
        self.recall_widget.show()
        
        # Set instruction text
        instruction_text = f"SELECT FINAL WORDS IN ORDER\n\nSeries {block_info['series']}, Block {block_info['block']}\n({len(expected_words)} words expected)\n\nClick words in the order they appeared:"
        self.recall_instruction_label.setText(instruction_text)
        
        # Store expected words and reset selection
        self.expected_words = expected_words
        self.expected_word_count = len(expected_words)
        self.selected_words = []
        self.word_buttons = []
        
        # Generate distractor words and create selection interface
        self.create_word_selection_buttons(expected_words)
        
        # Update display
        self.update_selected_words_display()
        self.submit_recall_button.setEnabled(False)


class ReadingSpanTask(TaskStateMixin, QMainWindow):
    """Main Reading Span Task with COMPLETE crash recovery system implementation"""
    
    TASK_NAME = "Reading Span Task"
    
    # Define the correct block structure for each series
    SERIES_BLOCK_LENGTHS = {
        1: [2, 4, 3, 5, 6],  # Series 1: blocks with 2,4,3,5,6 sentences
        2: [5, 2, 4, 6, 3],  # Series 2: blocks with 5,2,4,6,3 sentences  
        3: [6, 3, 5, 4, 2],  # Series 3: blocks with 6,3,5,4,2 sentences
        4: [4, 6, 2, 3, 5],  # Series 4: blocks with 4,6,2,3,5 sentences
        5: [3, 5, 6, 2, 4]   # Series 5: blocks with 3,5,6,2,4 sentences
    }
    
    def __init__(self, sentence_file=None, x_pos=100, y_pos=100, 
                 participant_id=None, participant_folder_path=None):
        
        # CRITICAL: Initialize session manager FIRST if not already initialized
        if not get_session_manager() and participant_id and participant_folder_path:
            print("Initializing session manager from Reading Span task...")
            initialize_session_manager(participant_id, participant_folder_path)
        
        # Call parent constructors (TaskStateMixin first, then QMainWindow)
        super().__init__()
        
        # Store participant information
        self.participant_id = participant_id or "TEST_PARTICIPANT"
        self.participant_folder_path = participant_folder_path or os.path.expanduser("~/Desktop")
        
        # Task state variables
        self.task_config = {}
        self.configuration_mode = True
        self.configuration_saved = False
        self.task_started = False
        self.current_phase = "configuration"
        self.practice_mode = False
        self._task_completed = False
        
        # Recovery support variables
        self.recovery_data = None
        
        # Check for recovery mode BEFORE setting up UI
        if self.session_manager:
            current_task_state = self.session_manager.get_current_task_state()
            if current_task_state and not current_task_state.get('task_completed', False):
                self.recovery_data = current_task_state
                # Skip configuration mode if we have recovery data
                self.configuration_mode = False
                self.configuration_saved = True
                self.task_config = self.recovery_data.get('task_config', {})
                print("✓ Recovery mode detected - skipping configuration")
        
        # Main trial tracking
        self.current_series = 1
        self.current_block = 1
        self.current_sentence_in_block = 0
        self.current_block_sentences = []
        self.current_block_final_words = []
        self.waiting_for_recall = False
        
        # Trial data
        self.trial_data = []
        self.recall_data = []
        
        # Sentence data structure
        self.sentence_data = {}  # {series: {block: [sentences]}}
        self.practice_sentences = {}
        
        # Load sentence data
        self.load_sentence_data(sentence_file)
        
        # Setup UI
        self.setup_ui(x_pos, y_pos)
        
        print(f"✓ Reading Span Task initialized with COMPLETE crash recovery system")
    
    def load_sentence_data(self, sentence_file):
        """Load and organize sentence data correctly from CSV"""
        # Create practice sentences
        self.practice_sentences = {
            1: [
                {'sentence': 'The cat sat on the warm mat.', 'target_word': 'mat'},
                {'sentence': 'Birds fly high in the blue sky.', 'target_word': 'sky'}
            ],
            2: [
                {'sentence': 'The sun shines brightly every morning.', 'target_word': 'morning'},
                {'sentence': 'Water flows gently down the river.', 'target_word': 'river'},
                {'sentence': 'Children play happily in the park.', 'target_word': 'park'}
            ]
        }
        
        # Find CSV file
        if sentence_file is None:
            possible_files = [
                resource_path('task_reading_span/sentence_dictionary.csv'),
                resource_path('sentence_dictionary.csv'),
                'task_reading_span/sentence_dictionary.csv',
                'sentence_dictionary.csv'
            ]
            
            sentence_file = None
            for possible_file in possible_files:
                if os.path.exists(possible_file):
                    sentence_file = possible_file
                    break
            
            if sentence_file is None:
                print("⚠ Could not find sentence_dictionary.csv - creating sample data")
                self.create_sample_data()
                return
        
        try:
            # Load CSV file
            df = pd.read_csv(sentence_file)
            print(f"✓ Loaded sentence data from: {sentence_file}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Total rows: {len(df)}")
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Organize data by series and block
            self.sentence_data = {}
            
            for _, row in df.iterrows():
                try:
                    series_num = int(row['series'])
                    sentence_text = str(row['sentence']).strip()
                    target_word = str(row['target_word']).strip()
                    
                    # Parse series number: first digit = series, second = block, third = sentence
                    series_str = str(series_num).zfill(3)
                    series_id = int(series_str[0])
                    block_id = int(series_str[1])
                    sentence_pos = int(series_str[2])
                    
                    # Only process series 1-5
                    if 1 <= series_id <= 5:
                        if series_id not in self.sentence_data:
                            self.sentence_data[series_id] = {}
                        if block_id not in self.sentence_data[series_id]:
                            self.sentence_data[series_id][block_id] = {}
                        
                        self.sentence_data[series_id][block_id][sentence_pos] = {
                            'sentence': sentence_text,
                            'target_word': target_word,
                            'series_number': series_num
                        }
                
                except (ValueError, KeyError) as e:
                    print(f"  Skipping row due to parsing error: {e}")
                    continue
            
            # Convert to ordered lists
            organized_data = {}
            for series_id in sorted(self.sentence_data.keys()):
                organized_data[series_id] = {}
                for block_id in sorted(self.sentence_data[series_id].keys()):
                    # Sort sentences by position and create ordered list
                    block_sentences = []
                    sentence_dict = self.sentence_data[series_id][block_id]
                    for pos in sorted(sentence_dict.keys()):
                        block_sentences.append(sentence_dict[pos])
                    
                    if block_sentences:
                        organized_data[series_id][block_id] = block_sentences
                        expected_length = self.SERIES_BLOCK_LENGTHS[series_id][block_id - 1]
                        actual_length = len(block_sentences)
                        print(f"  Series {series_id}, Block {block_id}: {actual_length} sentences (expected: {expected_length})")
            
            self.sentence_data = organized_data
            print(f"✓ Organized {len(self.sentence_data)} series from CSV")
            
        except Exception as e:
            print(f"⚠ Error loading CSV: {e}")
            self.create_sample_data()
    
    def create_sample_data(self):
        """Create sample data for testing"""
        print("Creating sample sentence data...")
        self.sentence_data = {
            1: {
                1: [  # Block 1: 2 sentences
                    {'sentence': 'The dog ran quickly through the yard.', 'target_word': 'yard', 'series_number': 111},
                    {'sentence': 'Books are placed neatly on the shelf.', 'target_word': 'shelf', 'series_number': 112}
                ],
                2: [  # Block 2: 4 sentences  
                    {'sentence': 'Music plays softly in the room.', 'target_word': 'room', 'series_number': 121},
                    {'sentence': 'Cars drive slowly on the road.', 'target_word': 'road', 'series_number': 122},
                    {'sentence': 'Rain falls gently on the roof.', 'target_word': 'roof', 'series_number': 123},
                    {'sentence': 'Wind blows strongly through the trees.', 'target_word': 'trees', 'series_number': 124}
                ]
            }
        }
        print("✓ Sample data created for testing")
    
    def setup_ui(self, x_pos, y_pos):
        """Setup the main user interface"""
        self.setWindowTitle("Reading Span Task")
        
        if x_pos is not None and y_pos is not None:
            self.setGeometry(x_pos, y_pos, 1370, 960)
        else:
            screen = QApplication.primaryScreen().geometry()
            window_width, window_height = 1370, 960
            x = (screen.width() - window_width) // 2
            y = (screen.height() - window_height) // 2
            self.setGeometry(x, y, window_width, window_height)
        
        self.setStyleSheet("background-color: #f6f6f6;")
        
        # Create layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 50, 10, 50)
        
        # Create child window for displaying content
        self.display_window = ReadingSpanDisplayWindow(self)
        
        # Connect recall submit button
        self.display_window.submit_recall_button.clicked.connect(self.handle_recall_submission)
        
        # Create action button
        if self.configuration_mode:
            button_text = "Save Configuration"
            button_style = """
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
            """
        else:
            # Recovery mode - show resume button
            button_text = "Resume Task"
            button_style = """
                QPushButton {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                              stop: 0 #fff3e0, stop: 1 #ffe0b2);
                    color: black;
                    border: 2px solid #FF9800;
                    border-radius: 35px;
                    padding: 10px;
                    font-weight: bold;
                }
            """
        
        self.action_button = QPushButton(button_text, self)
        self.action_button.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        self.action_button.setFixedSize(250, 70)
        self.action_button.setStyleSheet(button_style)
        self.action_button.clicked.connect(self.action_button_clicked)
        
        # Add widgets to layout with proper centering
        self.layout.addStretch()
        
        # Center the child window
        self.layout.addWidget(self.display_window, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addSpacing(30)
        
        # Center the action button
        self.layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add bottom stretch for better centering
        self.layout.addStretch()
        
        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)
        
        # Set initial display based on mode
        if self.configuration_mode:
            # Show configuration interface
            self.display_window.config_widget.show()
            self.display_window.display_label.hide()
            self.display_window.recall_widget.hide()
        else:
            # Recovery mode - show recovery message
            self.display_window.config_widget.hide()
            self.display_window.recall_widget.hide()
            self.display_window.display_label.show()
            self.display_window.display_label.setText("Reading Span Task - Session Recovery\n\nResuming from previous session...\n\nClick Resume Task to continue where you left off.")
            self.display_window.display_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
    
    def action_button_clicked(self):
        """Handle action button clicks"""
        if self.configuration_mode:
            self.save_configuration()
        elif not self.task_started:
            # This handles both normal start and recovery resume
            self.start_task()
        else:
            print("Action button clicked during task - no action defined")
    
    def save_configuration(self):
        """Save configuration and proceed to instructions"""
        # Get configuration from UI
        self.task_config = {
            'practice_enabled': self.display_window.practice_checkbox.isChecked(),
            'practice_sets': self.display_window.practice_sets_spinbox.value(),
            'practice_sentence_duration': self.display_window.practice_duration_spinbox.value(),
            'main_enabled': self.display_window.main_checkbox.isChecked(),
            'main_series': self.display_window.main_series_spinbox.value(),
            'main_sentence_duration': self.display_window.main_duration_spinbox.value()
        }
        
        # Validate configuration
        is_valid, error_message = self.validate_configuration()
        if not is_valid:
            QMessageBox.warning(self, "Configuration Error", error_message)
            return
        
        self.configuration_saved = True
        print("✓ Configuration saved:", self.task_config)
        
        # Proceed to instructions
        self.proceed_to_instructions()
    
    def validate_configuration(self):
        """Validate task configuration"""
        if not self.task_config['practice_enabled'] and not self.task_config['main_enabled']:
            return False, "At least one phase (Practice or Main) must be enabled."
        
        return True, ""
    
    def proceed_to_instructions(self):
        """Show instructions"""
        self.display_window.hide_configuration()
        self.display_window.show_instructions(self.task_config)
        self.configuration_mode = False
        
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
        """)
    
    def start_task(self):
        """Start the Reading Span task with FULL crash recovery support"""
        if not self.task_started:
            self.task_started = True
            self.action_button.hide()
            
            # Start with recovery support using TaskStateMixin
            if self.session_manager:
                task_config = {
                    'practice_enabled': self.task_config.get('practice_enabled', True),
                    'practice_sets': self.task_config.get('practice_sets', 2),
                    'practice_sentence_duration': self.task_config.get('practice_sentence_duration', 4000),
                    'main_enabled': self.task_config.get('main_enabled', True),
                    'main_series': self.task_config.get('main_series', 5),
                    'main_sentence_duration': self.task_config.get('main_sentence_duration', 5000),
                    'recovery_mode': bool(self.recovery_data),
                    'word_selection_interface': True,
                    'comprehensive_configuration': True,
                    'user_configuration': self.task_config
                }
                
                if not self.recovery_data:
                    # Calculate total trials for progress tracking (normal start)
                    total_trials = 0
                    if self.task_config.get('practice_enabled', True):
                        for i in range(1, self.task_config.get('practice_sets', 2) + 1):
                            if i in self.practice_sentences:
                                total_trials += len(self.practice_sentences[i])
                    
                    if self.task_config.get('main_enabled', True):
                        for series in range(1, self.task_config.get('main_series', 5) + 1):
                            if series in self.sentence_data:
                                for block in self.sentence_data[series]:
                                    total_trials += len(self.sentence_data[series][block])
                    
                    self.start_task_with_recovery(task_config, total_trials)
                else:
                    # Recovery mode - start with existing progress
                    completed_trials = len(self.recovery_data.get('trial_data', []))
                    self.start_task_with_recovery(task_config, completed_trials)
            
            # Check for recovery mode
            if self.recovery_data:
                print("=== RESUMING READING SPAN TASK FROM RECOVERY ===")
                self.restore_from_recovery()
            else:
                print("=== STARTING READING SPAN TASK (FRESH START) ===")
                # Start with practice if enabled
                if self.task_config.get('practice_enabled', True):
                    self.practice_mode = True
                    self.current_phase = "practice"
                    self.start_practice_trials()
                else:
                    self.practice_mode = False
                    self.current_phase = "main"
                    self.start_main_trials()
    
    def restore_from_recovery(self):
        """Restore task state from recovery data with intelligent block restart"""
        if not self.recovery_data:
            return
        
        print("Restoring Reading Span task from recovery data...")
        
        # Restore basic task state
        self.current_phase = self.recovery_data.get('current_phase', 'practice')
        self.practice_mode = self.recovery_data.get('practice_mode', True)
        self.current_series = self.recovery_data.get('current_series', 1)
        self.current_block = self.recovery_data.get('current_block', 1)
        self.waiting_for_recall = self.recovery_data.get('waiting_for_recall', False)
        
        # Restore completed data (trials and recalls from previous blocks)
        self.trial_data = self.recovery_data.get('trial_data', [])
        self.recall_data = self.recovery_data.get('recall_data', [])
        
        print(f"Recovery state: Phase={self.current_phase}, Series={self.current_series}, Block={self.current_block}")
        print(f"Restored {len(self.trial_data)} trials and {len(self.recall_data)} recall records")
        
        if self.waiting_for_recall:
            # If we crashed during recall, restore the recall interface exactly as it was
            self.current_block_sentences = self.recovery_data.get('current_block_sentences', [])
            self.current_block_final_words = self.recovery_data.get('current_block_final_words', [])
            
            print("✓ Resuming during recall phase - restoring recall interface")
            block_info = {
                'series': self.current_series,
                'block': self.current_block,
                'phase': self.current_phase
            }
            self.display_window.show_recall_interface(block_info, self.current_block_final_words)
        else:
            # If we crashed during sentence presentation, restart the current block from beginning
            print("✓ Crashed during sentence presentation - restarting current block for data integrity")
            
            # Remove any partial trial data from the current block to avoid duplicates
            # Keep only trials from completed blocks
            current_block_key = f"{self.current_phase}_{self.current_series}_{self.current_block}"
            filtered_trials = []
            
            for trial in self.trial_data:
                trial_block_key = f"{trial.get('phase', '')}_{trial.get('series', '')}_{trial.get('block', '')}"
                if trial_block_key != current_block_key:
                    # Keep trials from other blocks
                    filtered_trials.append(trial)
                else:
                    print(f"  Removing partial trial from current block: {trial.get('trial_number', 'N/A')}")
            
            self.trial_data = filtered_trials
            
            # Reset current block state to start fresh
            self.current_sentence_in_block = 0
            self.current_block_sentences = []
            self.current_block_final_words = []
            
            print(f"  Restarting {self.current_phase} series {self.current_series}, block {self.current_block} from beginning")
            print(f"  Remaining clean trials: {len(self.trial_data)}")
            
            # Start presenting sentences from the beginning of this block
            self.present_next_sentence()
    
    def start_practice_trials(self):
        """Start practice trials"""
        print("Starting practice trials...")
        self.current_series = 1  # Use practice set 1
        self.current_block = 1
        self.current_sentence_in_block = 0
        self.present_next_sentence()
    
    def start_main_trials(self):
        """Start main trials with correct structure"""
        print("Starting main trials...")
        self.practice_mode = False
        self.current_series = 1
        self.current_block = 1
        self.current_sentence_in_block = 0
        self.present_next_sentence()
    
    def present_next_sentence(self):
        """Present the next sentence following the correct block structure"""
        # Get current sentences based on phase
        if self.practice_mode:
            current_sentences = self.practice_sentences.get(self.current_series, [])
        else:
            current_sentences = self.sentence_data.get(self.current_series, {}).get(self.current_block, [])
        
        # Check if we have sentences to present
        if not current_sentences or self.current_sentence_in_block >= len(current_sentences):
            # Start recall phase for this block
            self.start_recall_phase()
            return
        
        # Get current sentence
        sentence_info = current_sentences[self.current_sentence_in_block]
        sentence_text = sentence_info['sentence']
        target_word = sentence_info['target_word']
        
        # Store sentence and target word for current block
        self.current_block_sentences.append(sentence_text)
        self.current_block_final_words.append(target_word)
        
        # Show sentence
        self.display_window.show_sentence(sentence_text)
        
        # Record trial data
        trial_record = {
            'trial_number': len(self.trial_data) + 1,
            'phase': 'practice' if self.practice_mode else 'main',
            'series': self.current_series,
            'block': self.current_block,
            'sentence_in_block': self.current_sentence_in_block + 1,
            'sentence': sentence_text,
            'target_word': target_word,
            'sentence_duration_ms': self.task_config.get('practice_sentence_duration' if self.practice_mode else 'main_sentence_duration', 5000),
            'presentation_time': datetime.now().isoformat()
        }
        
        self.trial_data.append(trial_record)
        
        # Save trial with recovery support
        if hasattr(self, 'save_trial_with_recovery'):
            self.save_trial_with_recovery(trial_record)
        
        print(f"Presented sentence {self.current_sentence_in_block + 1}/{len(current_sentences)} in {self.current_phase} series {self.current_series}, block {self.current_block}")
        
        # Set timer to advance to next sentence
        sentence_duration = self.task_config.get('practice_sentence_duration' if self.practice_mode else 'main_sentence_duration', 5000)
        QTimer.singleShot(sentence_duration, self.advance_to_next_sentence)
    
    def advance_to_next_sentence(self):
        """Advance to the next sentence in the block"""
        self.current_sentence_in_block += 1
        self.present_next_sentence()
    
    def start_recall_phase(self):
        """Start the recall phase for the current block"""
        if not self.current_block_final_words:
            print("No words to recall - moving to next block")
            self.move_to_next_block()
            return
        
        self.waiting_for_recall = True
        
        # Prepare block info
        block_info = {
            'series': self.current_series,
            'block': self.current_block,
            'phase': self.current_phase
        }
        
        print(f"Starting recall for {len(self.current_block_final_words)} words: {self.current_block_final_words}")
        
        # Show recall interface
        self.display_window.show_recall_interface(block_info, self.current_block_final_words)
    
    def handle_recall_submission(self):
        """Handle recall submission from the interface"""
        # Get recall response from display window
        user_words, correct_count, correct_positions = self.display_window.get_recall_response()
        
        # Calculate accuracy
        total_words = len(self.current_block_final_words)
        accuracy = correct_positions / total_words if total_words > 0 else 0
        
        # Create recall record
        recall_record = {
            'series': self.current_series,
            'block': self.current_block,
            'phase': self.current_phase,
            'expected_words': self.current_block_final_words.copy(),
            'user_selected_words': user_words,
            'selection_order': list(range(1, len(user_words) + 1)),
            'correct_count': correct_count,
            'correct_positions': correct_positions,
            'total_words': total_words,
            'accuracy': accuracy,
            'positional_accuracy': correct_positions / max(len(user_words), len(self.current_block_final_words)) if self.current_block_final_words else 0,
            'recall_time': datetime.now().isoformat()
        }
        
        self.recall_data.append(recall_record)
        
        # Save with recovery support
        if hasattr(self, 'save_trial_with_recovery'):
            # Update current task state with recall data
            state_update = {
                'recall_data': self.recall_data,
                'current_recall_record': recall_record
            }
            self.save_trial_with_recovery(state_update)
        
        print(f"✓ Recall completed: {correct_positions}/{len(self.current_block_final_words)} correct")
        
        # Reset block state
        self.waiting_for_recall = False
        self.current_block_sentences = []
        self.current_block_final_words = []
        
        # Move to next block
        self.move_to_next_block()
    
    def move_to_next_block(self):
        """Move to the next block or complete phase"""
        self.current_block += 1
        self.current_sentence_in_block = 0
        
        if self.practice_mode:
            # Practice phase
            if self.current_block > self.task_config['practice_sets']:
                # Practice complete
                if self.task_config['main_enabled']:
                    self.start_countdown_to_main()
                else:
                    self.complete_task()
            else:
                # Next practice block
                if self.current_block <= len(self.practice_sentences):
                    self.current_series = self.current_block
                self.present_next_sentence()
        else:
            # Main phase
            if self.current_block > 5:  # Each series has 5 blocks
                # Move to next series
                self.current_series += 1
                self.current_block = 1
                
                if self.current_series > self.task_config['main_series']:
                    # All series complete
                    self.complete_task()
                else:
                    # Start next series
                    self.present_next_sentence()
            else:
                # Next block in current series
                self.present_next_sentence()
    
    def start_countdown_to_main(self):
        """Show countdown before main trials"""
        self.practice_mode = False
        self.current_phase = "main"
        self.current_series = 1
        self.current_block = 1
        self.current_sentence_in_block = 0
        
        self.display_window.show_completion_message("Practice Complete!\n\nPreparing main trials...")
        QTimer.singleShot(2000, self.start_main_trials)
    
    def complete_task(self):
        """Complete the task with full recovery support"""
        print("=== READING SPAN TASK COMPLETION ===")
        
        # Mark task as completed
        self._task_completed = True
        
        # Show completion message
        self.display_window.show_completion_message("Reading Span Task Completed!\n\nProcessing data...")
        
        # Save final data
        QTimer.singleShot(1000, self.finalize_task_completion)
    
    def finalize_task_completion(self):
        """Finalize task completion with FORCED session cleanup"""
        # Save data using the data saver module
        success = self.save_trial_data()
        
        if success:
            completion_message = "Reading Span Task Completed Successfully!\n\nData has been saved."
        else:
            completion_message = "Reading Span Task Completed!\n\nWarning: There was an issue saving data."
        
        # FORCED SESSION CLEANUP - Multiple approaches to ensure cleanup
        if hasattr(self, 'session_manager') and self.session_manager:
            print("=== FORCED SESSION CLEANUP FOR READING SPAN COMPLETION ===")
            
            try:
                # Method 1: Use TaskStateMixin completion
                if hasattr(self, 'complete_task_with_recovery'):
                    final_data = {
                        'total_trials_completed': len(self.trial_data),
                        'total_recalls_completed': len(self.recall_data),
                        'completion_time': datetime.now().isoformat(),
                        'recovery_was_used': bool(self.recovery_data),
                        'task_completed_normally': True,
                        'all_data_saved': success,
                        'completion_method': 'normal_completion_sequence',
                        'user_configuration': self.task_config,
                        'word_selection_interface': True,
                        'task_completed': True,  # EXPLICIT FLAG
                        'cleanup_required': True
                    }
                    self.complete_task_with_recovery(final_data)
                
                # Method 2: DIRECT session manager cleanup
                print("Performing DIRECT session manager cleanup...")
                self.session_manager.session_data['current_task'] = None
                self.session_manager.session_data['current_task_state'] = None
                self.session_manager.session_data['session_active'] = False
                self.session_manager.session_data['reading_span_completed'] = True
                self.session_manager.session_data['task_completed'] = True
                self.session_manager.session_data['completion_time'] = datetime.now().isoformat()
                self.session_manager.session_data['cleanup_timestamp'] = datetime.now().isoformat()
                
                # Method 3: Force save the cleaned state
                self.session_manager.save_session_state()
                print("✓ Session state forcibly cleaned and saved")
                
                # Method 4: Verify cleanup worked
                current_task_state = self.session_manager.get_current_task_state()
                if current_task_state:
                    print("WARNING: Task state still exists after cleanup - forcing removal")
                    # Nuclear option - completely remove the task state
                    if hasattr(self.session_manager, '_task_states'):
                        self.session_manager._task_states.clear()
                    if hasattr(self.session_manager, 'task_states'):
                        self.session_manager.task_states.clear()
                    self.session_manager.save_session_state()
                else:
                    print("✓ Task state successfully cleared")
                
            except Exception as e:
                print(f"Error during session cleanup: {e}")
                # Last resort - try to at least clear the current task
                try:
                    self.session_manager.session_data['current_task'] = None
                    self.session_manager.session_data['current_task_state'] = None
                    self.session_manager.save_session_state()
                    print("✓ Minimal cleanup completed")
                except Exception as final_error:
                    print(f"Fatal: Could not perform any cleanup: {final_error}")
        
        # Show final message
        self.display_window.show_completion_message(completion_message)
        
        # Return to selection menu after delay
        QTimer.singleShot(3000, self.return_to_selection_menu)
    
    def save_trial_data(self):
        """Save trial data using the modular data saver"""
        try:
            # Import the Reading Span data saver
            from task_reading_span.data_saver import save_reading_span_data
            
            # Create folder for this task
            reading_span_folder_path = os.path.join(self.participant_folder_path, "reading_span_task")
            os.makedirs(reading_span_folder_path, exist_ok=True)
            
            # Save data using the modular save function
            success = save_reading_span_data(
                trial_data=self.trial_data,
                recall_data=self.recall_data,
                participant_id=self.participant_id,
                reading_span_folder_path=reading_span_folder_path,
                task_config=self.task_config,
                emergency_save=False
            )
            
            return success
            
        except Exception as e:
            print(f"Error saving Reading Span data: {e}")
            return False
    
    def _get_task_specific_state(self):
        """Get Reading Span specific state information for recovery (TaskStateMixin method)"""
        return {
            'current_phase': self.current_phase,
            'practice_mode': self.practice_mode,
            'current_series': self.current_series,
            'current_block': self.current_block,
            'current_sentence_in_block': self.current_sentence_in_block,
            'waiting_for_recall': self.waiting_for_recall,
            'current_block_sentences': self.current_block_sentences,
            'current_block_final_words': self.current_block_final_words,
            'recall_data': self.recall_data,
            'task_config': self.task_config,
            'configuration_saved': self.configuration_saved
        }
    
    def return_to_selection_menu(self):
        """Return to selection menu with NUCLEAR cleanup if needed"""
        try:
            # FINAL VERIFICATION AND NUCLEAR CLEANUP
            if self._task_completed and hasattr(self, 'session_manager') and self.session_manager:
                print("=== FINAL VERIFICATION BEFORE RETURNING TO MENU ===")
                
                # Check if cleanup worked
                current_task_state = self.session_manager.get_current_task_state()
                if current_task_state:
                    print("CRITICAL: Session state still exists after completion - NUCLEAR CLEANUP")
                    
                    # NUCLEAR OPTION: Completely wipe session state
                    try:
                        # Clear all task-related data
                        keys_to_clear = [
                            'current_task', 'current_task_state', 'task_states', '_task_states',
                            'session_active', 'reading_span_session_active', 'current_task_data'
                        ]
                        
                        for key in keys_to_clear:
                            if key in self.session_manager.session_data:
                                self.session_manager.session_data[key] = None
                                print(f"  Cleared: {key}")
                        
                        # Set explicit completion flags
                        self.session_manager.session_data['task_completed'] = True
                        self.session_manager.session_data['reading_span_completed'] = True
                        self.session_manager.session_data['no_recovery_needed'] = True
                        self.session_manager.session_data['nuclear_cleanup_performed'] = True
                        self.session_manager.session_data['cleanup_timestamp'] = datetime.now().isoformat()
                        
                        # Force save
                        self.session_manager.save_session_state()
                        print("✓ NUCLEAR cleanup completed")
                        
                        # Final verification
                        post_cleanup_state = self.session_manager.get_current_task_state()
                        if post_cleanup_state:
                            print("FATAL: Session state STILL exists - manually deleting session file")
                            # Last resort: try to delete the session file
                            try:
                                session_file = os.path.join(self.session_manager.system_folder_path, "session_data.json")
                                if os.path.exists(session_file):
                                    os.remove(session_file)
                                    print("✓ Session file deleted")
                            except Exception as delete_error:
                                print(f"Could not delete session file: {delete_error}")
                        else:
                            print("✓ Session state finally cleared")
                            
                    except Exception as nuclear_error:
                        print(f"Nuclear cleanup failed: {nuclear_error}")
                else:
                    print("✓ Session state properly cleared - no further cleanup needed")
            
            from menu_selection import SelectionMenu
            current_geometry = self.geometry()
            
            self.selection_menu = SelectionMenu(
                buttons_size=1.0,
                buttons_elevation=0.5,
                participant_id=self.participant_id,
                participant_folder_path=self.participant_folder_path
            )
            self.selection_menu.setGeometry(current_geometry)
            self.selection_menu.show()
            self.close()
            
        except Exception as e:
            print(f"Error returning to menu: {e}")
            self.close()
    
    def closeEvent(self, event):
        """Handle window close event with crash recovery support"""
        # Only perform emergency save if task was started but not completed
        if self.task_started and not self._task_completed and hasattr(self, 'session_manager') and self.session_manager:
            print("Reading Span task closing unexpectedly - performing emergency save...")
            try:
                # Perform emergency save using TaskStateMixin
                self.emergency_save()
            except Exception as e:
                print(f"Emergency save failed: {e}")
        elif self._task_completed:
            print("Reading Span task closing after normal completion - no emergency save needed")
            # Ensure cleanup for completed task
            try:
                if hasattr(self, 'session_manager') and self.session_manager:
                    self.session_manager.session_data['current_task_completed'] = True
                    self.session_manager.session_data['reading_span_completed'] = True
                    self.session_manager.save_session_state()
            except Exception as e:
                print(f"Warning: Could not finalize completion state: {e}")
        
        # Stop any active timers
        for timer in self.findChildren(QTimer):
            if timer.isActive():
                timer.stop()
        
        event.accept()
        print("Reading Span task cleanup completed")


def main():
    """Standalone main function for testing with full crash recovery support"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Custom Tests Battery")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Behavioral Research Lab")
    
    print("=== READING SPAN TASK TESTING (WITH FULL CRASH RECOVERY) ===")
    print("Full crash recovery system: ENABLED")
    print("User configuration interface: ENABLED")
    print("TaskStateMixin inheritance: ENABLED")
    print("Auto-save functionality: ENABLED")
    print("Recovery mode detection: ENABLED")
    print("Enhanced completion logic: ENABLED")
    print("Testing with sample participant data...")
    
    # Sample participant data for testing
    sample_participant_id = "TEST_READING_001"
    sample_folder = os.path.expanduser("~/Documents/Custom Tests Battery Data/TEST_READING_001")
    
    # Ensure test folder exists
    os.makedirs(sample_folder, exist_ok=True)
    
    # Initialize session manager for testing
    if RECOVERY_SYSTEM_AVAILABLE:
        try:
            session_manager = initialize_session_manager(sample_participant_id, sample_folder)
            default_tasks = [
                "Stroop Colour-Word Task",
                "CVC Task",
                "Visual Search Task",
                "Attention Network Task",
                "Go/No-Go Task",
                "Reading Span Task"
            ]
            session_manager.set_task_queue(default_tasks)
            print("Session manager initialized for testing")
        except Exception as e:
            print(f"Error initializing session manager: {e}")
    
    # Create Reading Span task with full crash recovery support
    task = ReadingSpanTask(
        sentence_file=None,
        participant_id=sample_participant_id,
        participant_folder_path=sample_folder
    )
    
    task.show()
    
    try:
        exit_code = app.exec()
        print("Reading Span task closed normally")
        return exit_code
    except Exception as e:
        print(f"Reading Span task crashed: {e}")
        
        # Emergency save
        if RECOVERY_SYSTEM_AVAILABLE:
            session_manager = get_session_manager()
            if session_manager:
                try:
                    session_manager.emergency_save()
                    print("Emergency save completed from Reading Span task")
                except:
                    print("Emergency save failed from Reading Span task")
        
        raise
    finally:
        # Cleanup
        if RECOVERY_SYSTEM_AVAILABLE:
            from crash_recovery_system.session_manager import cleanup_session_manager
            cleanup_session_manager()


if __name__ == "__main__":
    main()