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

### Docker Compose

To start the complete stack (MySQL, backend API and frontend) run:

```bash
docker compose up --build
```

This exposes the backend under [http://localhost:5000](http://localhost:5000) and the workflow canvas frontend under
[http://localhost:5173](http://localhost:5173).

## Continuous Integration

GitHub Actions runs linting (Ruff) and the pytest suite on every push and pull request to ensure code quality.
