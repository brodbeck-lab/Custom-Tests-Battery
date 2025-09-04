# Custom Tests Battery

A comprehensive psychological testing suite for cognitive assessment and research, built with PyQt6 and featuring advanced crash recovery capabilities.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)](https://pypi.org/project/PyQt6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/yourusername/custom-tests-battery)

## Overview

The Custom Tests Battery is a professional-grade application designed for psychological researchers and cognitive assessment specialists. It provides a comprehensive suite of standardized cognitive tasks with advanced features including automatic crash recovery, real-time audio analysis, and cross-platform executable distribution.

## Features

### Core Capabilities
- **Comprehensive Test Suite**: Multiple validated cognitive assessment tasks
- **Advanced Crash Recovery**: Three-tier recovery system with automatic session restoration
- **Audio Recording and Analysis**: Real-time speech analysis for precise reaction time measurements
- **Cross-Platform Distribution**: Builds to Windows (.exe) and macOS (.dmg) executables
- **Professional UI**: Modern interface with responsive layouts and accessibility features
- **Data Integrity**: Multiple backup mechanisms and comprehensive data validation
- **Real-Time Development**: Auto-reload development environment for rapid testing

### Research Features
- **Standardized Protocols**: Validated cognitive assessment procedures
- **Precise Timing**: Millisecond-accurate stimulus presentation and response recording
- **Flexible Configuration**: Customizable trial parameters for each task
- **Comprehensive Data Export**: Structured data files with detailed performance metrics
- **Session Management**: Automatic participant tracking and progress monitoring

## Available Tests

### Implemented Tasks
- **Stroop Colour-Word Task** - Cognitive interference assessment with audio recording
- **CVC Task (Consonant-Vowel-Consonant)** - Reading and letter recognition assessment
- **Reading Span Task** - Working memory capacity evaluation
- **Speeded Classification Task** - Rapid categorization with phoneme and voice discrimination
- **Auditory Stroop Task** - Voice gender identification with interference paradigm

### Planned Tasks
- **Letter Monitoring Task** - Sustained attention and vigilance testing
- **Visual Search Task** - Spatial attention and visual processing assessment
- **Attention Network Task** - Executive attention network evaluation
- **Go/No-Go Task** - Response inhibition and impulse control testing

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: 3.12 or higher (for development)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB free space
- **Audio**: Microphone required for speech recording tasks
- **Display**: 1024x768 minimum resolution

### Recommended Configuration
- **RAM**: 8GB or higher for optimal performance
- **Audio Interface**: Dedicated audio interface for research-grade recording
- **Display**: 1920x1080 or higher for optimal task presentation
- **Storage**: SSD recommended for faster data writing

## Quick Start

### For End Users

**Download and Run**
1. Download the latest release from the [Releases](https://github.com/yourusername/custom-tests-battery/releases) page
2. **Windows**: Run the .exe file directly
3. **macOS**: Open the .dmg file, drag to Applications, and launch

**Basic Usage**
1. Launch the application
2. Complete the biodata form with participant information
3. Select desired tests from the battery menu
4. Follow on-screen instructions for each assessment
5. Data is automatically saved to your Documents folder

### For Developers

**Prerequisites**
- Python 3.12 or higher
- Git for version control
- Text editor or IDE (VS Code recommended)

**Installation**
```bash
# Clone the repository
git clone https://github.com/yourusername/custom-tests-battery.git
cd custom-tests-battery

# Install dependencies
pip install -r requirements-dev.txt

# Start development mode
# Windows:
dev.bat
# macOS/Linux:
./dev.sh
```

## Development Workflow

### Real-Time Development Environment

The development launcher provides instant feedback with automatic code reloading:

**Features:**
- Auto-reload on file changes
- Executable simulation environment
- Cross-platform development support
- Integrated crash recovery testing

**Usage:**
```bash
# Start development mode (auto-reloads on changes)
./dev.sh          # macOS/Linux
dev.bat           # Windows

# Test individual components
python welcome.py                    # Welcome screen
python menu_biodata.py              # Biodata form  
python menu_selection.py            # Test selection
python task_stroop_colorword/stroop_task.py  # Stroop task
```

### Making Changes
1. Start development mode using the commands above
2. Edit Python files in your preferred editor
3. Save the file - the app automatically reloads
4. Test changes visually in the running application
5. Commit changes using standard Git workflow

## Building Executables

The project uses GitHub Actions workflows to automatically build executables for both Windows and macOS:

### Automated Build Triggers
- **Push to main/development**: Automatically triggers builds for both platforms
- **Pull Requests**: Builds are created for testing and validation
- **Manual trigger**: Use "Run workflow" button in the Actions tab
- **Nightly builds**: Automatic builds when changes are detected in the last 24 hours

### Build Outputs
- **Windows**: `Custom-Tests-Battery.exe` (single executable file)
- **macOS**: `Custom-Tests-Battery.dmg` (installer with app bundle)

### Accessing Built Executables
1. Navigate to the **Actions** tab in the GitHub repository
2. Select the most recent successful build workflow
3. Download artifacts from the workflow run:
   - `windows-executable` - Windows .exe file
   - `macos-dmg` - macOS .dmg installer

### Build Features
- **Complete Integration**: All task audio files, data files, and Python modules included
- **Verification Steps**: Automated checks ensure all required files are present
- **Cross-Platform**: Consistent functionality across Windows and macOS
- **Retention**: Release builds kept for 30 days, nightly builds for 7 days

## Technical Architecture

### Core Components
- **welcome.py** - Application entry point with recovery detection
- **menu_biodata.py** - Participant demographics and consent management
- **menu_selection.py** - Test battery selection interface
- **Task modules** - Individual cognitive assessment implementations

### Crash Recovery System
- **Global Level** (crash_handler.py): Catches unhandled exceptions
- **Session Level** (session_manager.py): Manages participant sessions and recovery
- **Task Level** (task_state_saver.py): Auto-saves individual task progress.

### Data Management
- **Modular Data Savers**: Each task has its own data export module
- **Structured Output**: Comprehensive CSV and text file exports
- **Automatic Backup**: Multiple redundant save mechanisms
- **Folder Organization**: Organized participant data structure

### Audio System
- **Real-time Recording**: PyAudio and SoundDevice integration
- **Speech Analysis**: Librosa-based reaction time detection
- **Multiple Formats**: Support for WAV recording with configurable parameters
- **Quality Assurance**: Automatic audio validation and error handling

## Usage Guide

### For Researchers

**Session Setup**
1. Launch the Custom Tests Battery application
2. Complete the biodata form with participant information
3. Select appropriate tests from the battery based on research protocol
4. Configure task parameters if needed (practice trials, timing, etc.)

**Running Assessments**
1. Follow standardized instructions for each task
2. Monitor participant during testing
3. Ensure audio recording is functioning for applicable tasks
4. Allow for breaks between tasks as needed

**Data Collection**
- Data is automatically saved to `~/Documents/Custom Tests Battery Data/`
- Each participant gets a unique folder with organized subfolders
- Audio recordings are saved with automatic analysis
- Summary files include performance metrics and timing data

### Data Organization

**Folder Structure**
```
~/Documents/Custom Tests Battery Data/
└── [Participant_ID]/
    ├── biodata/
    │   └── participant_biodata.txt
    ├── system/
    │   └── session_state.json (during active sessions)
    ├── stroopcolorwordtask_[timestamp]/
    │   ├── audio_files/
    │   └── stroop_colorword_results.txt
    └── [other_task_folders]/
```

**File Types**
- **Biodata**: Participant demographics and consent information
- **Results**: Comprehensive performance data with trial-by-trial details
- **Audio**: WAV recordings with automatic analysis results
- **Session**: Recovery data for interrupted sessions

## Configuration

### Audio Settings
- **Sample Rate**: 48kHz (configurable)
- **Channels**: Mono recording for optimal analysis
- **Format**: 16-bit WAV files
- **Analysis**: Automatic speech onset detection with confidence scores

### Task Customization
Each task supports configuration of:
- Number of practice and main trials
- Timing parameters and delays
- Stimulus presentation parameters
- Response collection methods

### File Locations
- **Windows**: `C:\Users\[Username]\Documents\Custom Tests Battery Data\`
- **macOS**: `/Users/[Username]/Documents/Custom Tests Battery Data/`
- **Linux**: `/home/[Username]/Documents/Custom Tests Battery Data/`

## Contributing

### Development Process
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes using the real-time development environment
4. Test thoroughly across different platforms
5. Submit a pull request with detailed description

### Code Standards
- **Python 3.12** compatibility required
- **PyQt6** for all GUI components
- **Type hints** where appropriate
- **Comprehensive docstrings** for all public methods
- **Error handling** with proper exception management
- **Cross-platform** file path handling using os.path

### Adding New Tasks
1. Create new task folder following the pattern: `task_[name]/`
2. Implement main task file inheriting from `TaskStateMixin`
3. Create corresponding `data_saver.py` module
4. Add task to `menu_selection.py` with proper launcher method
5. Update build configurations to include new task resources
6. Add emergency save function to `crash_handler.py`

## Performance Optimization

### System Optimizations
- **Lazy Loading**: Heavy dependencies loaded only when needed
- **Efficient Audio Buffering**: Real-time recording with minimal latency
- **Memory Management**: Automatic cleanup for long testing sessions
- **Optimized Trial Generation**: Balanced randomization with consistent sequences

### Research Considerations
- **Timing Accuracy**: Millisecond precision for stimulus presentation
- **Response Recording**: High-resolution timing for reaction time measurements
- **Audio Quality**: Research-grade recording and analysis
- **Data Integrity**: Multiple validation layers and backup mechanisms

## Security and Privacy

### Data Protection
- **Local Storage Only**: No cloud transmission or external data sharing
- **Secure File Permissions**: Restricted access to participant data
- **GDPR Compliance**: Ready with data export and deletion tools
- **Participant Privacy**: Configurable anonymization options

### Research Ethics
- **Informed Consent**: Built-in consent management
- **Data Minimization**: Only necessary data collection
- **Secure Storage**: Encrypted participant identifiers when enabled
- **Audit Trail**: Comprehensive logging for research compliance

## Troubleshooting

### Common Issues
- **Audio Not Recording**: Check microphone permissions and device selection
- **Task Not Loading**: Verify all data files are present in executable
- **Performance Issues**: Ensure sufficient RAM and close other applications
- **Crash Recovery**: Follow on-screen prompts to restore interrupted sessions

### Development Issues
- **Build Failures**: Check that all task audio and data files are committed to Git
- **Missing Dependencies**: Run `pip install -r requirements-dev.txt`
- **Import Errors**: Verify Python path and module structure

## Support and Documentation

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/yourusername/custom-tests-battery/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/custom-tests-battery/discussions)
- **Documentation**: Check the project wiki for detailed guides

### Reporting Bugs
When reporting bugs, please include:
- Operating system and version
- Python version (if running from source)
- Steps to reproduce the issue
- Error messages or logs
- Expected vs actual behavior

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

### Technology Stack
- **PyQt6** for the robust GUI framework
- **librosa** for advanced audio analysis capabilities
- **pandas** for efficient data manipulation and export
- **NumPy/SciPy** for numerical computing and signal processing

### Research Community
- Built for psychological research and cognitive assessment
- Designed with input from behavioral research laboratories
- Continuously improved based on researcher feedback and requirements

---

**Built for psychological research and cognitive assessment**

*Custom Tests Battery v2.0 - Professional cognitive assessment software with advanced crash recovery and real-time audio analysis*
