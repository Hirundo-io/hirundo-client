# Hirundo client

This repo contains the source code for the Hirundo client library

## Usage:

To learn about how to use this library, please visit the [ubiquitous-adventure-g6e391m.pages.github.io](documentation) or see the Google Colab examples.

## Development:

### Install dev dependencies

```bash
pip install -r dev-requirements.txt
```

Note: You can install and use `uv` as a faster drop-in replacement for `pip`. We have it as part of our dev dependencies for this reason.

### Install `git` hooks (optional)

```bash
pre-commit install
```

### Check lint and apply formatting with Ruff (optional; pre-commit hooks run this automatically)

```bash
ruff check
ruff format
```

### Update `requirements.txt` files

```bash
uv pip compile pyproject.toml
uv pip compile --extra dev -o dev-requirements.txt -c requirements.txt pyproject.toml
uv pip compile --extra docs -o docs-requirements.txt -c requirements.txt pyproject.toml
```

### Build process

To build the package, run:
`python -m build`

### Publish documentation & releases

Documentation & releases are published via GitHub Actions on merges to `main`.
