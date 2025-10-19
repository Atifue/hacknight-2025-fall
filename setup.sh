#!/bin/bash
# ============================================
# ReVoice Practice - Quick Setup Script
# ============================================

echo "🎤 ReVoice Practice Setup"
echo "========================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg not found. Installing with Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Homebrew not found. Please install ffmpeg manually:"
        echo "   Visit: https://ffmpeg.org/download.html"
        exit 1
    fi
else
    echo "✅ ffmpeg found"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "revoice-env" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv revoice-env
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source revoice-env/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip3 install --upgrade pip

# Install Python requirements
echo ""
echo "📥 Installing Python packages..."
pip3 install -r requirements.txt

# Check if .env file exists
if [ ! -f "detection-Files/.env" ]; then
    echo ""
    echo "⚠️  No .env file found in detection-Files/"
    echo "📝 Creating template .env file..."
    cat > detection-Files/.env << EOF
# Add your API keys here:
GEMINI_API_KEY=your-gemini-api-key-here
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
EOF
    echo "✅ Template .env file created at detection-Files/.env"
    echo "⚠️  IMPORTANT: Edit detection-Files/.env and add your real API keys!"
else
    echo "✅ .env file exists"
fi

# Check if frontend node_modules exists
echo ""
if [ ! -d "revoice-frontend/node_modules" ]; then
    echo "📥 Installing frontend dependencies..."
    cd revoice-frontend
    npm install
    cd ..
    echo "✅ Frontend dependencies installed"
else
    echo "✅ Frontend dependencies already installed"
fi

echo ""
echo "============================================"
echo "✅ Setup Complete!"
echo "============================================"
echo ""
echo "🚀 To run ReVoice Practice:"
echo ""
echo "Terminal 1 (Backend):"
echo "  source revoice-env/bin/activate"
echo "  python3 backend_api.py"
echo ""
echo "Terminal 2 (Frontend):"
echo "  cd revoice-frontend"
echo "  npm start"
echo ""
echo "⚠️  Don't forget to add your API keys to detection-Files/.env!"
echo ""

