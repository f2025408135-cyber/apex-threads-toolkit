#!/bin/bash
set -e

echo "Building APEX-HARNESS Native Application..."

# Make sure all dependencies are installed
pip install -r requirements.txt

# Clean previous builds
rm -rf build/ dist/ *.spec

# Build with PyInstaller
# --noconfirm: Overwrite existing build
# --onedir: Create a folder containing the executable and dependencies
# --windowed: Run the application without a console window (native GUI)
# --add-data: Include the web UI templates so they are found by Flask
# --hidden-import: Ensure dynamic imports are captured
# --name: The application name

pyinstaller --noconfirm \
    --onedir \
    --windowed \
    --add-data "templates:templates" \
    --hidden-import "engineio.async_drivers.threading" \
    --hidden-import "flask_socketio" \
    --name "APEX-HARNESS" \
    desktop_app.py

echo "Build complete! Check the 'dist/APEX-HARNESS' directory."
