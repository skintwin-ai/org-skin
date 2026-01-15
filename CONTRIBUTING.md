# Contributing to Org-Skin

Thank you for your interest in contributing to Org-Skin! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)

### Suggesting Features

1. Check existing issues and discussions
2. Create a new issue with the "enhancement" label
3. Describe the feature and its use case
4. Explain how it fits with the project's goals

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/org-skin.git
cd org-skin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks (optional)
pre-commit install
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=org_skin

# Run specific test file
pytest tests/test_graphql.py
```

## Code Style

We use `ruff` for linting and formatting:

```bash
# Check linting
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Style Guidelines

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small
- Use meaningful variable and function names

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs in the body

Example:
```
Add AIML pattern matching for repository queries

- Implement pattern matching engine
- Add support for wildcards
- Include tests for edge cases

Fixes #123
```

## Project Structure

```
org-skin/
├── src/org_skin/       # Main source code
│   ├── graphql/        # GraphQL client and queries
│   ├── aiml/           # AIML encoding system
│   ├── mapper/         # Organization mapping
│   ├── chatbot/        # Intelligent chatbot
│   ├── aggregator/     # Feature aggregation
│   └── db/             # Data persistence
├── tests/              # Test files
├── docs/               # Documentation
└── examples/           # Usage examples
```

## Adding New Features

### Adding a New GraphQL Query

1. Add the query to `src/org_skin/graphql/queries.py`
2. Add a method to the client if needed
3. Write tests in `tests/test_graphql.py`
4. Update documentation

### Adding a New AIML Pattern

1. Add the pattern to `src/org_skin/aiml/templates.py`
2. Update the encoder if needed
3. Write tests for pattern matching
4. Document the new pattern

### Adding a New CLI Command

1. Add the command to `src/org_skin/cli.py`
2. Implement the handler function
3. Write tests for the command
4. Update README with usage

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions
- Update ARCHITECTURE.md for structural changes
- Include examples where helpful

## Review Process

1. All PRs require at least one review
2. Address review comments promptly
3. Ensure CI passes before requesting review
4. Squash commits if requested

## Questions?

Feel free to open an issue for any questions about contributing. We're happy to help!
