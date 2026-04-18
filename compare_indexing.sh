#!/bin/bash
# Confronto tra i due sistemi di indexing

echo "=== Confronto Sistemi di Indexing ==="
echo ""
echo "✅ NUOVO: scripts/index_Qdrant.py (attivo)"
echo "   - Pattern singleton con auto-indexing"
echo "   - Indicizza: 176 documenti (16 case_cards + 160 frames)"
echo "   - Indicizza: 9 guideline chunks"
echo "   - Usato da: API, start.sh, multimodal_rag_openai.py"
echo ""
echo "❌ VECCHIO: src/vectorstore_manager.py (deprecato)"
echo "   - Pattern singleton originale"
echo "   - Backup disponibile: scripts/index_Qdrant.py.backup"
echo ""
echo "📝 Differenza chiave:"
echo "   - Entrambi indicizzano case_cards E frames (176 docs)"
echo "   - index_Qdrant usa architettura più pulita"
echo ""
