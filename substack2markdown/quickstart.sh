#!/bin/bash
# Quick Start Script for Substack2Markdown
# Run this script to set up the project quickly

echo "=========================================="
echo "   Substack2Markdown Quick Setup"
echo "=========================================="

# Check Python version
echo ""
echo "Checking Python version..."
python_version=$(python3 --version 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    echo "   Download from: https://python.org/downloads/"
    exit 1
fi
echo "✓ Found: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi
echo "✓ Virtual environment created"

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"

# Create .env file from example
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env configuration file..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "=========================================="
    echo "   IMPORTANT: Configure your .env file"
    echo "=========================================="
    echo ""
    echo "Edit the .env file with your Substack URL:"
    echo ""
    echo "  nano .env"
    echo ""
    echo "Set at minimum:"
    echo "  SUBSTACK_URL=https://your-publication.substack.com"
    echo ""
fi

# Display usage instructions
echo ""
echo "=========================================="
echo "   Setup Complete! 🎉"
echo "=========================================="
echo ""
echo "Usage:"
echo ""
echo "  1. Edit .env with your Substack URL:"
echo "     nano .env"
echo ""
echo "  2. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  3. Run the scraper:"
echo "     python main.py              # Download all posts"
echo "     python main.py --list-only  # List available posts"
echo "     python main.py --help       # Show all options"
echo ""
echo "For more details, see README.md"
echo ""
