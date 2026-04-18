#!/bin/bash
# Script di avvio per RAG Healthcare System

set -e

# Colori per output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== RAG Healthcare System - Startup ===${NC}\n"

# 1. Check Python environment
echo -e "${GREEN}[1/5] Checking Python environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${RED}Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "✓ Virtual environment activated"

# 2. Install dependencies
echo -e "\n${GREEN}[2/5] Checking dependencies...${NC}"
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# 3. Build dataset from raw DICOM files
echo -e "\n${GREEN}[3/5] Building dataset from DICOM files...${NC}"
if [ ! -f "data/dataset_built/documents.jsonl" ]; then
    echo "documents.jsonl not found. Building from raw DICOM files..."
    python3 scripts/build_dataset.py
    echo "✓ Dataset built"
else
    echo "✓ Dataset already exists (data/dataset_built/documents.jsonl)"
    echo "  To rebuild, delete the file and restart"
fi

# 4. Check environment variables
echo -e "\n${GREEN}[4/5] Checking environment variables...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}WARNING: .env file not found${NC}"
    echo "Copy .env.example to .env and set your OPENAI_API_KEY:"
    echo "  cp .env.example .env"
    echo "  Then edit .env and set your OpenAI API key"
else
    echo "✓ .env file found"
    # Check if OPENAI_API_KEY is set in .env
    if grep -q "^OPENAI_API_KEY=" .env 2>/dev/null; then
        echo "✓ OPENAI_API_KEY configured in .env"
    else
        echo -e "${RED}WARNING: OPENAI_API_KEY not found in .env${NC}"
    fi
fi

# 5. Test vectorstore (auto-indexing)
echo -e "\n${GREEN}[5/5] Initializing vectorstore (auto-indexing)...${NC}"
python3 -c "from scripts.index_Qdrant import get_vectorstore; get_vectorstore(); print('✓ Vectorstore ready')"

# 6. Start both FastAPI backend and Streamlit
echo -e "\n${BLUE}=== Starting Services ===${NC}"
echo "Backend API: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo "Streamlit UI: http://localhost:8501"
echo -e "\nPress Ctrl+C to stop all services\n"

# Start FastAPI in background
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

# Give API time to start
sleep 2

# Start Streamlit (will run in foreground)
# Disable email prompt and telemetry for automated startup
STREAMLIT_SERVER_HEADLESS=true streamlit run app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &
STREAMLIT_PID=$!

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Stopping services...${NC}"
    kill $API_PID 2>/dev/null || true
    kill $STREAMLIT_PID 2>/dev/null || true
    echo "✓ Services stopped"
    exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
