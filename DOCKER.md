# Docker Setup Guide

Questo progetto è completamente containerizzato con Docker per garantire isolamento e riproducibilità.

## 🏗️ Architettura

Il sistema è composto da 3 container separati:

1. **qdrant** - Vector database (immagine ufficiale)
2. **api** - Backend FastAPI (porta 8000)
3. **streamlit** - Frontend Streamlit (porta 8501)

Tutti i container comunicano attraverso una rete Docker privata `rag-network`.

## 🚀 Quick Start

### 1. Configurazione

Crea un file `.env` dalla template:

```bash
cp .env.example .env
```

Modifica `.env` e inserisci la tua `OPENAI_API_KEY`.

### 2. Avvio

```bash
# Build e start di tutti i servizi
make docker-up-build

# Oppure manualmente
docker-compose up -d --build
```

### 3. Accesso

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Streamlit**: http://localhost:8501
- **Qdrant**: http://localhost:6333/dashboard

### 4. Logs

```bash
# Tutti i servizi
make docker-logs

# Solo API
make docker-logs-api

# Solo Streamlit
make docker-logs-streamlit
```

## 🛠️ Comandi Utili

```bash
# Build immagini
make docker-build

# Start servizi
make docker-up

# Stop servizi
make docker-down

# Restart servizi
make docker-down && make docker-up

# Pulire tutto (container, volumi, immagini)
make docker-clean

# Development mode (con hot reload)
make docker-dev

# Shell nei container
make docker-shell-api
make docker-shell-streamlit
```

## 🔧 Development Mode

Per sviluppo con hot reload:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Questo monta i volumi in modalità read-only e abilita il reload automatico.

## 📦 Immagini Docker

Le immagini usano **multi-stage build** per ottimizzare le dimensioni:

- **Builder stage**: Installa dipendenze con compilatori
- **Final stage**: Solo runtime Python slim + applicazione

### Tag delle Immagini

```bash
# Local build
rag-healthcare-api:latest
rag-healthcare-streamlit:latest

# GitHub Container Registry (quando pushate)
ghcr.io/<username>/rag-healthcare-api:latest
ghcr.io/<username>/rag-healthcare-streamlit:latest
```

## 🔐 GitHub Container Registry

Le immagini vengono automaticamente buildare e pushate su GitHub Container Registry (GHCR) quando:

- Push su branch `main`
- Creazione di tag `v*.*.*`

Per usare le immagini da GHCR:

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull
docker pull ghcr.io/<username>/rag-healthcare-api:latest
docker pull ghcr.io/<username>/rag-healthcare-streamlit:latest

# Run
docker-compose up -d
```

## 📊 Health Checks

Ogni container ha health check configurati:

- **Qdrant**: `curl http://localhost:6333/health`
- **API**: `python check http://localhost:8000/list-docs`
- **Streamlit**: `curl http://localhost:8501/_stcore/health`

Verifica stato:

```bash
docker-compose ps
make docker-ps
```

## 🔍 Troubleshooting

### Container non parte

```bash
# Controlla logs
docker-compose logs api

# Verifica network
docker network ls
docker network inspect rag-system-4-healthcare_rag-network
```

### Qdrant non connette

```bash
# Verifica health
curl http://localhost:6333/health

# Rebuild container
docker-compose up -d --force-recreate qdrant
```

### Hot reload non funziona

```bash
# Usa docker-compose.dev.yml
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Pulire e ripartire da zero

```bash
make docker-clean
make docker-up-build
```

## 🧪 Testing con Docker

```bash
# Build immagini per test
docker-compose build

# Test health di tutti i servizi
docker-compose up -d
sleep 30
curl http://localhost:8000/list-docs?rag_type=cases
curl http://localhost:8501/_stcore/health

# Stop
docker-compose down -v
```

## 🔒 Security Scanning

Le pipeline CI/CD includono:

- **Trivy**: Vulnerability scanning delle immagini
- **Docker Bench**: Best practices check
- **SARIF Upload**: Risultati su GitHub Security

## 📐 Volumi e Persistenza

```yaml
volumes:
  qdrant_storage:  # Dati Qdrant persistenti
  
  # Mount locali (development)
  ./data:/app/data  # Dataset DICOM
```

### Backup Qdrant

```bash
# Backup
docker run --rm -v rag-system-4-healthcare_qdrant_storage:/data \
  -v $(pwd)/backups:/backup alpine tar czf /backup/qdrant-backup.tar.gz /data

# Restore
docker run --rm -v rag-system-4-healthcare_qdrant_storage:/data \
  -v $(pwd)/backups:/backup alpine tar xzf /backup/qdrant-backup.tar.gz -C /
```

## 🌐 Production Deployment

Per deployment in produzione:

1. Modifica `docker-compose.yml`:
   - Rimuovi volumi di development
   - Configura `restart: always`
   - Usa secrets per API keys
   - Abilita HTTPS con reverse proxy

2. Usa variabili ambiente:
   ```bash
   ENVIRONMENT=production docker-compose up -d
   ```

3. Configura reverse proxy (nginx/traefik):
   ```nginx
   location /api {
       proxy_pass http://localhost:8000;
   }
   location / {
       proxy_pass http://localhost:8501;
   }
   ```

## 📚 Risorse

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
