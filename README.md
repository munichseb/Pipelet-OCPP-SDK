# Pipelet OCPP SDK

This repository bundles the Flask backend and a Vite/React frontend used to orchestrate workflows composed of Pipelets. The
backend exposes REST endpoints for pipelets, workflow storage and log inspection; the frontend renders a workflow canvas based on
Rete.js that allows authoring and persisting workflow diagrams.

## Local development

### Backend (Flask)

1. Create a Python 3.11 virtual environment and install the dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure the database connection if necessary. By default the application expects a MySQL instance:

   ```bash
   export DATABASE_URL="mysql+pymysql://app:app@localhost:3306/pipelet_sandbox"
   ```

3. Start the development server:

   ```bash
   flask --app backend/wsgi.py run
   ```

4. Run the backend test suite:

   ```bash
   pytest
   ```

### Frontend (Vite + React)

1. Install dependencies:

   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite dev server (defaults to port 5173):

   ```bash
   npm run dev -- --host
   ```

   The application expects the backend API under the `VITE_API_BASE` environment variable (defaults to the same origin). During
   local development you can export `VITE_API_BASE=http://localhost:5000`.

3. Build the production bundle:

   ```bash
   npm run build
   ```

## Authentication & security

All non-health API routes require a Bearer token. Tokens are managed via the new `/api/auth/tokens` endpoints and carry a
role:

- `admin` tokens can create, update and delete resources and issue or revoke other tokens.
- `readonly` tokens may call read-only endpoints (e.g. list pipelets/logs) but are blocked from mutating operations.

The frontend exposes a **TokenPanel** in the palette column that lets administrators generate new tokens (the plaintext value
is only shown once), revoke existing ones and persist the token for subsequent API calls in the browser's local storage. Paste
an issued token into the "Aktives Token" input to apply it globally; the setting is stored locally and used for WebSocket
connections and AJAX requests.

Sensitive endpoints such as pipelet test runs and the streaming log feed are rate-limited per token/IP (10 test executions per
minute; the log stream only accepts 20 requests per second) to mitigate accidental overload.

### Docker Compose

To start the complete stack (MySQL, backend API and frontend) run:

```bash
docker compose up --build
```

This exposes the backend under [http://localhost:5000](http://localhost:5000) and the workflow canvas frontend under
[http://localhost:5173](http://localhost:5173).

## Simulator dashboard & live logs

The frontend includes a simulator dashboard that bundles charge point controls, connection status indicators and the
streaming log console:

1. The **Charge Point Simulator** panel lets you choose a custom CP-ID (defaults to `CP_1`), trigger connect/disconnect,
   send RFID tokens and start/stop transactions or periodic heartbeats. All interactions call the matching REST endpoints
   under `/api/sim/*`.
2. The status bars display the connectivity of the central system (WebSocket listener on `:9000`) and the currently
   selected charge point. They refresh every few seconds and show the timestamp of the latest event.
3. The live log viewer subscribes to the server-sent events stream, supports source filters, full-text search with
   highlighting, auto-scroll toggles and a "Nur letzte N" cap. Use the *Clear* button to reset the local view or
   *Download* to fetch an NDJSON snapshot via `/api/logs/download`.

## Continuous Integration

GitHub Actions runs linting (Ruff) and the pytest suite on every push and pull request to ensure code quality.

## Built-in pipelets

The backend ships with a curated set of built-in pipelet templates that cover common tasks such as routing decisions, conditional
filtering, structured logging and integrations (HTTP webhook, MQTT stub). Their source can be found under
`backend/app/pipelets/builtins`. Each template defines a `run` function and is available in the UI palette as soon as it exists in
the database.

Use the seed script below to populate the database with the latest versions of all built-in definitions.

## Export & import

Complete configurations consisting of pipelets and workflows can be exported as JSON and later restored. The API exposes two
endpoints:

- `GET /api/export` – returns the current snapshot with lists of pipelets and workflows.
- `POST /api/import` – accepts the same structure and recreates or updates the stored definitions. Passing `?overwrite=true`
  updates entries with matching names; without the flag the import fails if duplicates are encountered.

The JSON structure has the shape:

```json
{
  "version": 1,
  "pipelets": [{"name": "…", "event": "…", "code": "…"}],
  "workflows": [{"name": "…", "event": "…", "graph_json": "…"}]
}
```

## Seed example data

Run the seed script to insert the built-in pipelets and an example workflow (`Debug Template -> Start Meter Transformer -> HTTP
Webhook`) bound to the `StartTransaction` event:

```bash
python backend/scripts/seed.py
```

The script is idempotent – it updates existing entries to the shipped defaults.
