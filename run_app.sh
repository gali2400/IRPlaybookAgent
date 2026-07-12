#!/bin/bash
# IRPlaybookAgent — Quick Start Script

echo ""
echo "============================================"
echo "  IRPlaybookAgent — Incident Response Agent"
echo "============================================"

# Check for .env
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "   Edit .env and add your GEMINI_API_KEY or GROQ_API_KEY before continuing."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Download frameworks
echo "⬇️  Setting up framework data..."
python scripts/download_frameworks.py

# Launch app
echo ""
echo "🚀 Launching IRPlaybookAgent..."
echo "   Open http://localhost:8501 in your browser"
echo ""
streamlit run app/streamlit_app.py
