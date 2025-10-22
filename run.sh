#!/bin/bash

echo "Starting Trading Bot..."
echo

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the web interface
echo "Starting web interface..."
echo "Open your browser and go to: http://localhost:5000"
echo "Press Ctrl+C to stop the bot"
echo
python main.py web
