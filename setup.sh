#!/bin/bash

# DroneDeploy Email Generation System Setup Script
# This script sets up the development environment and installs all requirements

set -e  # Exit on any error

echo "🚀 Setting up DroneDeploy Email Generation System"
echo "=================================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "🐍 Python version: $PYTHON_VERSION"

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found. Installing core packages..."
    pip install fastapi uvicorn pydantic python-dotenv pandas requests openai python-multipart beautifulsoup4 html5lib
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p in out

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    if [ -f ".env_sample" ]; then
        cp .env_sample .env
        echo "✅ .env file created from .env_sample"
        echo "⚠️  Please edit .env file and add your OpenAI API key"
    else
        echo "⚠️  .env_sample not found. Creating basic .env file..."
        cat > .env << EOF
# API Keys
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
LOG_LEVEL=INFO
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
MAX_SPEAKERS=10

# Sender Information
SENDER_NAME=Your Name
SENDER_TITLE=Sales Representative

# Output Configuration
OUTPUT_DIR=out
INPUT_DIR=in
EOF
        echo "✅ Basic .env file created"
        echo "⚠️  Please edit .env file and add your OpenAI API key"
    fi
else
    echo "✅ .env file already exists"
fi

# Test the installation
echo "🧪 Testing installation..."
python -c "import fastapi, pydantic, pandas, requests, openai, bs4; print('✅ All packages imported successfully')"

# Show next steps
echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your OpenAI API key:"
echo "   OPENAI_API_KEY=your_actual_api_key_here"
echo ""
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo ""
echo "3. Run the FastAPI server:"
echo "   python server.py"
echo ""
echo "4. Access the API documentation:"
echo "   http://localhost:8000/docs"
echo ""

# Check if .env has been configured
if grep -q "your_openai_api_key_here" .env; then
    echo "⚠️  Remember to update your OpenAI API key in the .env file!"
fi

echo "✨ Setup script completed!"
echo
echo "👉 To start working run:"
echo "   source venv/bin/activate"
echo "source venv/bin/activate" | pbcopy
echo "   start command copied to clipboard!"

