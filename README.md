# Custom Tests Battery

A comprehensive psychological testing suite for cognitive assessment and research, built with PyQt6 and featuring advanced crash recovery capabilities.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)](https://pypi.org/project/PyQt6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/yourusername/custom-tests-battery)

## 🧪 Features

- **Comprehensive Test Suite**: Multiple cognitive assessment tasks
- **Advanced Crash Recovery**: Automatic session restoration and data protection
- **Audio Recording**: Real-time speech analysis for reaction time measurements
- **Cross-Platform**: Builds to Windows (.exe) and macOS (.dmg) executables
- **Real-Time Development**: Auto-reload development environment
- **Professional UI**: Modern neumorphic design with responsive layouts
- **Data Integrity**: Multiple backup mechanisms and validation

### Available Tests

- ✅ **Stroop Colour-Word Task** - Cognitive interference assessment
- 🚧 **Letter Monitoring Task** - Attention and vigilance testing (planned)
- 🚧 **Visual Search Task** - Spatial attention assessment (planned)
- 🚧 **Attention Network Task** - Executive attention evaluation (planned)
- 🚧 **Go/No-Go Task** - Response inhibition testing (planned)
- 🚧 **Reading Span Test** - Memory capacity assessment (planned)

## 📋 Requirements

### System Requirements
- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: 3.9 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB free space
- **Audio**: Microphone for speech recording tasks

### Python Dependencies

- PyQt6>=6.4.0
- pandas>=1.5.0
- numpy>=1.21.0
- pyaudio>=0.2.11       
- sounddevice>=0.4.5      
- librosa>=0.9.0           
- scipy>=1.9.0           
- watchdog>=2.1.9       


## 🚀 Quick Start

### For End Users

1. **Download the latest release** from the [Releases](https://github.com/yourusername/custom-tests-battery/releases) page
2. **Windows**: Run the .exe file
3. **macOS**: Open the .dmg file and drag to Applications

### For Developers

## 🛠 Development Setup

### Prerequisites

Ensure you have Python 3.9+ installed:
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **macOS**: Install via Homebrew: brew install python
- **Linux**: Use your package manager: sudo apt install python3

### Installation

1. **Clone the repository**
   - git clone https://github.com/yourusername/custom-tests-battery.git
   - cd custom-tests-battery

2. **Install dependencies**
   - Windows
      - pip install -r requirements-dev.txt
   
   - macOS/Linux  
      - pip3 install -r requirements-dev.txt

3. **Start development mode**
   
   **macOS/Linux:**
   ./dev.sh
   
   **Windows:**
   dev.bat

4. **Start coding!** 
   - Edit any .py file
   - App automatically reloads with changes
   - Test visually in real-time

## 💻 Development Workflow

### Real-Time Development

The development launcher provides instant feedback:

- macOS/Linux
   - ./dev.sh

- Windows
   - dev.bat


**Features:**
- ✅ **Auto-reload** - Changes reflect instantly
- ✅ **Executable simulation** - Tests like real .exe or .dmg
- ✅ **Cross-platform** - Same experience on all systems
- ✅ **Crash recovery** - Test recovery features in development

### Making Changes

1. **Start development mode** using the commands above
2. **Edit any Python file** in your preferred editor
3. **Save the file** (Ctrl+S / Cmd+S)
4. **Watch the app reload automatically** with your changes
5. **Test your changes** visually in the running application

### Testing Individual Components

# Test specific windows directly
- python welcome.py           # Welcome screen
- python menu_biodata.py      # Biodata form
- python selection_menu.py    # Test selection
- python stroop_colorword_task.py  # Stroop task

## 📦 Building Executables

### Windows (.exe)

- Install PyInstaller
   - pip install pyinstaller

- Build executable
   - pyinstaller --onefile --windowed welcome.py

- Output: dist/welcome.exe

### macOS (.dmg)

- Install py2app
   - pip install py2app

- Create setup.py (if not exists)
   - python setup.py py2app

- Output: dist/Custom Tests Battery.app

### Advanced Build Options

- Windows - with icon and additional files
   - pyinstaller --onefile --windowed --icon=icon.ico --add-data "stroop_colorword_list.txt;." welcome.py

- macOS - with app bundle
   - python setup.py py2app --packages=crash_recovery_system

### Core Modules

- **\`welcome.py\`** - Application entry point with recovery detection
- **\`menu_biodata.py\`** - Participant demographics and consent
- **\`selection_menu.py\`** - Test battery selection interface
- **\`stroop_colorword_task.py\`** - Stroop Color-Word cognitive task
- **\`experiment_data_saver.py\`** - Unified data export system

### Crash Recovery System

- **\`crash_handler.py\`** - Global exception handling and monitoring
- **\`session_manager.py\`** - Session state management and recovery dialogs
- **\`task_state_saver.py\`** - Task-level auto-save mixins

## 🎯 Usage

### For Researchers

1. **Start the application**
2. **Enter participant information** in the biodata form
3. **Select desired tests** from the test battery
4. **Run assessments** with automatic data collection
5. **Review results** in the generated data files

### Data Collection

- **Participant data**: Stored in \`~/Documents/Custom Tests Battery Data/\`
- **Audio recordings**: Saved per session with automatic analysis
- **Results**: Exported as structured text files with CSV data
- **Crash recovery**: Automatic session restoration on unexpected closure

## 🔧 Configuration

### Audio Settings

The application automatically detects audio devices. For optimal performance:

- **Sample Rate**: 48kHz (configurable)
- **Channels**: Mono recording
- **Format**: 16-bit WAV files
- **Analysis**: Automatic speech onset detection

### File Locations

- **Windows**: \`C:\\Users\\[Username]\\Documents\\Custom Tests Battery Data\\\`
- **macOS**: \`/Users/[Username]/Documents/Custom Tests Battery Data/\`
- **Linux**: \`/home/[Username]/Documents/Custom Tests Battery Data/\`


## 🤝 Contributing

### Development Process

1. **Fork the repository**
2. **Set up development environment** using the guide above
3. **Create a feature branch**: \`git checkout -b feature-name\`
4. **Make your changes** using the auto-reload development mode
5. **Test thoroughly** across different platforms
6. **Submit a pull request**

### Code Standards

- **Python 3.9+** compatibility
- **PyQt6** for GUI components
- **Type hints** where appropriate
- **Docstrings** for all public methods
- **Error handling** with try-catch blocks
- **Cross-platform** file path handling

### Adding New Tests

1. **Create new task file** following the pattern of \`stroop_colorword_task.py\`
2. **Inherit from \`TaskStateMixin\`** for crash recovery
3. **Add to \`selection_menu.py\`** test options
4. **Implement save function** in \`experiment_data_saver.py\`
5. **Test with development launcher**

## 📊 Technical Details

### Crash Recovery Architecture

The application features a three-tier recovery system:

1. **Global Level** (\`crash_handler.py\`): Catches unhandled exceptions
2. **Session Level** (\`session_manager.py\`): Manages participant sessions
3. **Task Level** (\`task_state_saver.py\`): Auto-saves individual task progress

### Performance Optimizations

- **Lazy loading** of heavy dependencies
- **Efficient audio buffering** for real-time recording
- **Optimized trial generation** with balanced randomization
- **Memory management** for long testing sessions

### Security & Privacy

- **Local data storage** - no cloud transmission
- **Encrypted participant IDs** (when enabled)
- **Secure file permissions** on saved data
- **GDPR compliance** ready with data export tools

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Development Team** - *Initial work* - [YourUsername](https://github.com/yourusername)

## 🙏 Acknowledgments

- **PyQt6** for the excellent GUI framework
- **librosa** for audio analysis capabilities
- **pandas** for data manipulation
- **Contributors** who help improve the testing suite

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/custom-tests-battery/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/custom-tests-battery/discussions)
- **Email**: support@yourdomain.com

---

**Built with ❤️ for psychological research and cognitive assessment**
EOF

echo "✅ README.md created successfully!"
