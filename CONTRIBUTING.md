# Contributing

Thank you for investing time in improving the Pipelet OCPP SDK! The following guidelines help keep the project maintainable and
delightful for everyone.

## Getting started

1. Fork the repository and clone your fork locally.
2. Install the development dependencies by following the steps in the [README quickstart](README.md#quickstart).
3. Create a feature branch from `main` (e.g. `feat/<topic>` or `fix/<bug>`).

We encourage (but do not mandate) [Conventional Commits](https://www.conventionalcommits.org/) to keep the history tidy. Use
imperative commit subjects and describe the *what* and *why*.

## Pull requests

- Sync your fork with upstream before opening a pull request to avoid conflicts.
- Provide a clear description of the change, including screenshots or GIFs for UI updates.
- Ensure that documentation and tests are updated alongside code changes.
- Reference related issues (e.g. `Closes #123`).
- Keep PRs focused — prefer multiple small PRs over a single massive one.

### Checklist

Before requesting a review:

- [ ] `make test` runs successfully.
- [ ] `make seed` still completes without errors (if you changed pipelets/workflows).
- [ ] Documentation is updated (`README`, `docs/`, API collection, etc.).
- [ ] New scripts are executable and documented.
- [ ] Added or updated diagrams are checked in as `.puml` sources.

## Issue reports

When filing an issue, please include:

- Environment details (OS, Docker version, Python/node versions if developing locally).
- Steps to reproduce the behaviour and the expected result.
- Logs or stack traces, if available.
- Screenshots for UI glitches.

Security vulnerabilities should be reported privately to the maintainers. Avoid filing public issues for potential security
problems.
