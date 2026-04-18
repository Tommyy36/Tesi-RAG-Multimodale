#!/bin/bash

# RAG Healthcare System - Startup Script
# Avvia automaticamente tutti i servizi Docker

set -e

echo "🚀 RAG Healthcare System - Startup"
echo "===================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non trovato. Installa Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker non è in esecuzione. Avvia Docker Desktop."
    exit 1
fi

echo "✅ Docker è attivo"

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose non trovato"
    exit 1
fi

echo "✅ docker-compose trovato"

# Check .env file
if [ ! -f .env ]; then
    echo "⚠️  File .env non trovato. Creo da template..."
    cp .env.example .env
    echo ""
    echo "📝 IMPORTANTE: Modifica il file .env e inserisci la tua OPENAI_API_KEY"
    echo "   Esegui: nano .env"
    echo ""
    read -p "Premi INVIO dopo aver configurato .env, o CTRL+C per uscire..."
fi

echo "✅ File .env presente"
echo ""

# Stop existing containers
echo "🧹 Pulizia container esistenti..."
docker-compose down 2>/dev/null || true
echo ""

# Build images
echo "🏗️  Building Docker images..."
docker-compose build --no-cache
echo ""

# Start services
echo "🚀 Avvio servizi..."
docker-compose up -d
echo ""

# Wait for services to be healthy
echo "⏳ Attendo che i servizi siano pronti..."
echo ""

MAX_WAIT=120
WAITED=0

# Wait for Qdrant
echo -n "   📦 Qdrant: "
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:6333/health &> /dev/null; then
        echo "✅ Pronto"
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Timeout"
    echo "Vedi i logs: docker-compose logs qdrant"
    exit 1
fi

# Wait for API
WAITED=0
echo -n "   🔧 API Backend: "
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/list-docs?rag_type=cases &> /dev/null; then
        echo "✅ Pronto"
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Timeout"
    echo "Vedi i logs: docker-compose logs api"
    exit 1
fi

# Wait for Streamlit
WAITED=0
echo -n "   🎨 Streamlit Frontend: "
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8501/_stcore/health &> /dev/null; then
        echo "✅ Pronto"
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Timeout"
    echo "Vedi i logs: docker-compose logs streamlit"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ Tutti i servizi sono attivi!"
echo "============================================"
echo ""
echo "📍 Accedi ai servizi:"
echo ""
echo "   🎨 Streamlit UI:    http://localhost:8501"
echo "   🔧 API Backend:     http://localhost:8000"
echo "   📚 API Docs:        http://localhost:8000/docs"
echo "   📦 Qdrant DB:       http://localhost:6333/dashboard"
echo ""
echo "💡 Comandi utili:"
echo ""
echo "   make docker-logs         # Vedi i logs"
echo "   make docker-ps           # Vedi lo stato"
echo "   ./stop-docker.sh         # Spegni tutto"
echo ""
echo "============================================"
