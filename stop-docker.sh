#!/bin/bash

# RAG Healthcare System - Shutdown Script
# Spegne automaticamente tutti i servizi Docker

set -e

echo "🛑 RAG Healthcare System - Shutdown"
echo "===================================="
echo ""

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "ℹ️  Nessun servizio attivo"
    exit 0
fi

echo "🔍 Servizi attivi:"
docker-compose ps
echo ""

# Ask for confirmation
read -p "⚠️  Vuoi spegnere tutti i servizi? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Annullato"
    exit 0
fi

echo ""
echo "🛑 Spegnimento servizi..."
echo ""

# Stop containers
docker-compose stop

echo ""
echo "🗑️  Rimozione container..."
docker-compose down

echo ""
echo "============================================"
echo "✅ Tutti i servizi sono stati spenti"
echo "============================================"
echo ""
echo "💡 I dati sono stati preservati nei volumi Docker"
echo ""
echo "   Per riavviare:          ./start-docker.sh"
echo "   Per pulire tutto:       make docker-clean"
echo ""
