#!/bin/bash
# ═══════════════════════════════════════════════════════
# Jhaveri Financial Intelligence Engine — Setup Script
# Run this once to set up everything
# ═══════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════"
echo "  JHAVERI FIE — SETUP"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check Python
echo "📋 Checking Python..."
python3 --version 2>/dev/null || { echo "❌ Python 3 not found. Install from python.org"; exit 1; }
echo "✅ Python found"

# Create virtual environment
echo ""
echo "📋 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"

# Install dependencies
echo ""
echo "📋 Installing dependencies (this may take 2-3 minutes)..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Setup .env file
echo ""
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📋 Created .env file from template"
    echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   Get your API key from: https://console.anthropic.com"
else
    echo "✅ .env file already exists"
fi

# Create directories
echo ""
echo "📋 Creating directories..."
mkdir -p data database outputs templates
echo "✅ Directories ready"

# Initialize database
echo ""
echo "📋 Initializing database..."
python3 -c "
import sys
sys.path.insert(0, '.')
from database.models import init_db
engine = init_db()
print('✅ Database initialized at database/fie.db')
"

# Build instrument universe
echo ""
echo "📋 Building master instrument universe (fetching AMFI + NSE data)..."
echo "   This will take 1-2 minutes..."
python3 scripts/build_universe.py

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  Next steps:"
echo "  1. Edit .env and add your ANTHROPIC_API_KEY"
echo "  2. Replace data/sample_clients.csv with your real client data"
echo "  3. Replace data/sample_holdings.csv with your real holdings"
echo "  4. Run the dashboard: streamlit run dashboard/app.py"
echo ""
echo "  Quick test commands:"
echo "  • Test NLP Parser:        python3 agents/nlp_parser.py"
echo "  • Test Technical Agent:   python3 agents/technical_signals.py"
echo "  • Build Universe:         python3 scripts/build_universe.py"
echo "  • Start Dashboard:        streamlit run dashboard/app.py"
echo ""
