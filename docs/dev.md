# Lokale Entwicklung mit Docker

1. `.env` anlegen:
   ```bash
   cp .env.example .env
   ```
2. Container starten:
   ```bash
   docker compose up --build
   ```
3. Healthcheck aufrufen:
   ```bash
   curl http://localhost:5000/api/health
   ```
