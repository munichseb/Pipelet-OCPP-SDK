# Pipelet OCPP SDK Backend

This repository contains the initial Flask/SQLAlchemy backend scaffolding for the Pipelet OCPP SDK. The service exposes a healthcheck endpoint, basic database models for Pipelets, Workflows and execution logs, and continuous integration checks for linting and tests.

## Getting started

1. Create a Python 3.11 virtual environment and install the dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure the database connection (optional). The default points to a MySQL instance:

   ```bash
   export DATABASE_URL="mysql+pymysql://app:app@localhost:3306/pipelet_sandbox"
   ```

3. Run the development server:

   ```bash
   flask --app backend/wsgi.py run
   ```

4. Run the test suite:

   ```bash
   pytest
   ```

## Continuous Integration

GitHub Actions runs linting (Ruff) and the pytest suite on every push and pull request to ensure code quality.
