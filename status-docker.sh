#!/bin/bash

# RAG Healthcare System - Status Check
# Mostra lo stato di tutti i servizi

echo "📊 RAG Healthcare System - Status"
echo "===================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non installato"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker non è in esecuzione"
    exit 1
fi

echo "✅ Docker è attivo"
echo ""

# Check if services are running
if ! docker-compose ps 2>/dev/null | grep -q "Up"; then
    echo "ℹ️  Nessun servizio attivo"
    echo ""
    echo "💡 Avvia i servizi: ./start-docker.sh"
    exit 0
fi

echo "🐳 Container Status:"
echo ""
docker-compose ps
echo ""

echo "🌐 Endpoint Status:"
echo ""

# Check Qdrant
echo -n "   📦 Qdrant (http://localhost:6333): "
if curl -s http://localhost:6333/health &> /dev/null; then
    echo "✅ Online"
else
    echo "❌ Offline"
fi

# Check API
echo -n "   🔧 API (http://localhost:8000): "
if curl -s http://localhost:8000/list-docs?rag_type=cases &> /dev/null; then
    echo "✅ Online"
else
    echo "❌ Offline"
fi

# Check Streamlit
echo -n "   🎨 Streamlit (http://localhost:8501): "
if curl -s http://localhost:8501/_stcore/health &> /dev/null; then
    echo "✅ Online"
else
    echo "❌ Offline"
fi

echo ""
echo "💾 Volumi Docker:"
echo ""
docker volume ls | grep rag

echo ""
echo "📊 Uso Risorse:"
echo ""
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker-compose ps -q) 2>/dev/null || echo "Nessun container attivo"

echo ""
echo "💡 Comandi utili:"
echo ""
echo "   make docker-logs         # Vedi i logs"
echo "   ./stop-docker.sh         # Spegni tutto"
echo ""
