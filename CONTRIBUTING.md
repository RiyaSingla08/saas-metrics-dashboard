# Contributing

Thanks for considering contributing to this project! It started as a learning project, so contributions of all sizes are welcome — from fixing a typo to adding a whole new chart.

## Getting set up

1. Fork the repo and clone your fork
2. Follow the **Quick start** steps in the [README](README.md) to get a working local copy
3. Create a new branch for your change:
   ```bash
   git checkout -b your-feature-name
   ```

## Making a change

- Keep the existing structure: SQL logic in `app/queries.py`, chart-building in `app/charts.py`, layout in `app/layout.py`, interactivity in `app/callbacks.py`. If you're adding a new metric, follow the same pattern — a query function, then a chart function, then wiring in the layout/callbacks.
- If you add or change a SQL query, run `python scripts/test_queries.py` afterward to make sure nothing broke, and consider adding your query to `sql/metrics_queries.sql` as documentation.
- Test your change locally by actually running `python -m app.main` and clicking through the app before opening a pull request.

## Submitting a pull request

1. Push your branch and open a pull request against `main`
2. Describe what the change does and why — a screenshot is very helpful if it's a visual change
3. Keep pull requests focused on one thing where possible; smaller PRs are easier to review

## Reporting bugs or suggesting features

Open a GitHub issue. For bugs, include what you expected to happen, what actually happened, and steps to reproduce. For feature suggestions, a quick explanation of the use case is more useful than a full spec.

## Code style

Nothing enforced by a linter yet (a good first contribution, if you're looking for one!) — just try to match the style of the surrounding code: descriptive function names, docstrings on functions that aren't obvious from their name, and comments explaining *why* for anything non-obvious (especially SQL logic).
