# Contributing to Atlas

Thank you for your interest in contributing to OpenGuardrail Atlas. This document provides guidelines and information for contributors.

## Development Setup

```bash
git clone https://github.com/openguardrail/atlas.git
cd atlas
pip install -e ".[dev]"
```

## Development Workflow

1. Create a feature branch from `main`.
2. Implement your changes with appropriate tests.
3. Ensure all tests pass: `pytest`
4. Ensure code passes linting: `ruff check src/ tests/`
5. Submit a pull request with a clear description of the change.

## Code Standards

- Python 3.10+ with type annotations on all public interfaces.
- Follow existing code conventions and module structure.
- Maximum line length: 100 characters.
- Use `ruff` for linting and formatting.

## Testing Requirements

- All new functionality must include unit tests.
- Maintain or improve existing test coverage.
- Tests must pass on Python 3.10, 3.11, and 3.12.
- Use `pytest` and `tmp_path` fixtures for file system tests.

## Adding a New Scanner

To add support for a new AI framework:

1. Create a new scanner in `src/atlas/scanners/` that extends `BaseScanner`.
2. Define the `framework`, `import_patterns`, and `_extract_components` method.
3. Register the scanner in `src/atlas/scanners/__init__.py`.
4. Add corresponding tests in `tests/`.

## Pull Request Guidelines

- Keep PRs focused on a single change or feature.
- Include a description of what the change does and why.
- Reference related issues where applicable.
- Ensure CI checks pass before requesting review.

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests.
- Include reproduction steps, expected behavior, and actual behavior for bugs.
- For security vulnerabilities, see [SECURITY.md](SECURITY.md).

## Code of Conduct

All contributors are expected to conduct themselves professionally and respectfully. Harassment, discrimination, and disruptive behavior will not be tolerated.

## License

By contributing to this project, you agree that your contributions will be licensed under the Apache License 2.0.

