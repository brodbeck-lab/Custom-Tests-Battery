#!/bin/bash
echo "🍎 macOS Development Mode"
echo "Starting development launcher..."
echo
python3 dev_tools/dev_launcher.py
if [ $? -ne 0 ]; then
    echo
    echo "❌ Error: Make sure Python 3 is installed"
    echo "❌ Also ensure you've installed requirements: pip3 install -r requirements-dev.txt"
    read -p "Press Enter to continue..."
fi