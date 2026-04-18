#!/bin/bash
# Script per rigenerare il dataset da zero

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BLUE}=== Rebuild Dataset ===${NC}\n"

# Controlla se esiste già
if [ -f "data/dataset_built/documents.jsonl" ]; then
    echo -e "${YELLOW}Dataset already exists. This will DELETE and REBUILD it.${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    
    echo -e "${GREEN}Removing old dataset...${NC}"
    rm -rf data/dataset_built/documents.jsonl
    rm -rf data/dataset_built/labels.csv
    rm -rf data/dataset_built/images
fi

# Attiva ambiente
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Build
echo -e "${GREEN}Building dataset from DICOM files...${NC}"
python3 scripts/build_dataset.py

# Stats
if [ -f "data/dataset_built/documents.jsonl" ]; then
    docs=$(wc -l < data/dataset_built/documents.jsonl)
    cases=$(grep -c '"document_type": "case_card"' data/dataset_built/documents.jsonl || echo 0)
    frames=$(grep -c '"document_type": "frame"' data/dataset_built/documents.jsonl || echo 0)
    
    echo -e "\n${GREEN}✓ Dataset built successfully!${NC}"
    echo "  Total documents: $docs"
    echo "  Case cards: $cases"
    echo "  Frames: $frames"
    echo "  Images dir: data/dataset_built/images"
    
    # Verify anonymization
    echo -e "\n${GREEN}Verifying anonymization...${NC}"
    python3 scripts/verify_anonymization.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Dataset is safe for public repository${NC}"
    else
        echo -e "${RED}✗ Anonymization issues detected${NC}"
        exit 1
    fi
else
    echo -e "\n${RED}✗ Build failed${NC}"
    exit 1
fi

echo -e "\n${BLUE}Next: restart the backend to re-index the vectorstore${NC}"
