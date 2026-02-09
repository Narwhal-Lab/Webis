# Contributing to Webis

First off, thanks for taking the time to contribute! 🎉

This project and everyone participating in it is governed by the [Webis Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Table of Contents

1. [How Can I Contribute?](#how-can-i-contribute)
2. [Development Setup](#development-setup)
3. [Coding Standards](#coding-standards)
4. [Submiting Changes](#submiting-changes)
5. [Documentation](#documentation)
6. [Testing](#testing)

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for Webis. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

#### Before Submitting

1. **Check existing issues** - Search to see if the issue has already been reported
2. **Check recent changes** - Ensure you're on the latest version
3. **Prepare minimal reproduction** - Create a minimal, reproducible example

#### Submitting a Bug Report

When submitting a bug report, please include:

- **A clear, descriptive title**
- **Exact steps to reproduce** - As detailed as possible
- **Expected behavior** - What you expected to happen
- **Actual behavior** - What actually happened
- **Environment details**:
  - Webis version
  - Python version
  - Operating system
  - Configuration details
- **Possible solutions** - If you've found one
- **Additional context** - Screenshots, logs, error messages

#### Bug Report Template

```markdown
## Bug Report

**Description:**
[A clear and concise description of what the bug is]

**Steps to Reproduce:**
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

**Expected Behavior:**
[What you expected to happen]

**Actual Behavior:**
[What actually happened]

**Environment:**
- Webis Version: [e.g., 2.0.0-alpha.1]
- Python Version: [e.g., 3.10]
- OS: [e.g., Ubuntu 20.04, macOS 14]
- Configuration: [e.g., using OpenAI API, PostgreSQL database]

**Logs/Error Messages:**
[Paste any relevant error messages or logs here]

**Additional Information:**
[Any other relevant information]
```

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for Webis.

#### Submitting an Enhancement

When submitting an enhancement:

- **Use a clear title** - Identify the suggestion
- **Provide detailed description** - As much detail as possible
- **Explain the use case** - Why this enhancement would be useful
- **Consider alternatives** - Have you considered other solutions?
- **Include examples** - Mockups, wireframes, or example code

#### Enhancement Template

```markdown
## Enhancement Suggestion

**Title:**
[Brief, clear title]

**Problem Statement:**
[What problem does this enhancement solve?]

**Proposed Solution:**
[How should the enhancement work?]

**Use Case:**
[Who would benefit from this enhancement? How?]

**Alternatives Considered:**
[What other approaches have you considered? Why did you choose this one?]

**Examples:**
[Any mockups, wireframes, or example code]

**Additional Context:**
[Any other relevant information]
```

### Pull Requests

We welcome pull requests!

#### Before Submitting

1. **Fork the repository** and create your branch
2. **Set up development environment** (see below)
3. **Write tests** for your changes
4. **Update documentation** if you change APIs or add features
5. **Run tests** and ensure they pass
6. **Update CHANGELOG** - Add entry for your changes
7. **Commit with clear messages** - See [Commit Messages](#commit-messages)

#### Submitting a Pull Request

1. **Push to your fork**
2. **Create pull request** against `main` branch
3. **Fill out the PR template** - Describe your changes clearly
4. **Reference related issues** - Link to any related issues
5. **Be responsive** - Address feedback quickly

#### Pull Request Template

```markdown
## Description

[Brief description of changes]

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues

Fixes #<issue_number>
Related to #<issue_number>

## Changes Made

- [ ] List changes here
- [ ] Another change

## Testing

[ ] Added tests for new features
[ ] All existing tests pass
[ ] Tested on Python 3.9
[ ] Tested on Python 3.10
[ ] Tested on Python 3.11

## Checklist

- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where appropriate
- [ ] I have updated documentation accordingly
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix works
```

## Development Setup

### Prerequisites

- Python 3.9+
- Git
- pip or uv
- Docker (optional, for local testing)

### Fork and Clone

```bash
# Fork the repository on GitHub, then:

git clone https://github.com/YOUR_USERNAME/webis.git
cd webis

# Add upstream repository
git remote add upstream https://github.com/Narwhal-Lab/Webis.git

# Create a branch
git checkout -b feature/your-feature-name
```

### Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=webis --cov-report=html

# Run specific test file
pytest tests/test_core.py
```

### Run Linting

```bash
# Check code style
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy src/webis
```

## Coding Standards

### Python Styleguide

- We use `ruff` for linting and formatting
- We use `mypy` for static type checking
- All new code should have type hints
- Follow PEP 8 style guide
- Use meaningful variable and function names
- Write docstrings for all public functions

### Docstrings

Docstrings should follow the Google Python Style Guide:

```python
def search_documents(query: str, limit: int = 10) -> List[WebisDocument]:
    """Search for documents matching a query.

    This function searches multiple data sources and returns
    documents that match the given query.

    Args:
        query: Search query string
        limit: Maximum number of results to return. Defaults to 10.

    Returns:
        List of WebisDocument objects matching the query.

    Raises:
        ValueError: If query is empty
        APIError: If search API fails

    Examples:
        >>> docs = search_documents("AI news", limit=5)
        >>> len(docs)
        5
    """
    # Implementation...
```

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes
- `revert`: Reverting a previous commit

#### Examples

```
feat(sources): add Reddit data source plugin

Add new Reddit source plugin that allows users to search and
collect data from Reddit discussions and posts.

Fixes #123
```

```
fix(pipeline): handle empty result sets

Previously, pipeline would crash if no documents were found.
Now returns empty list instead.

Closes #456
```

## Submiting Changes

### Pull Request Process

1. **Update your fork**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your changes**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create PR**
   - Go to GitHub
   - Click "New Pull Request"
   - Fill in the PR template
   - Link to related issues

### Review Process

- Maintainers will review your PR
- Address feedback in a timely manner
- Keep the PR focused - avoid scope creep
- Ensure all checks pass before merging

## Documentation

### When to Update Documentation

Update documentation when you:
- Add a new feature
- Change an API
- Fix a bug
- Deprecate functionality
- Change configuration options

### Documentation Standards

- Use clear, concise language
- Include examples for complex features
- Add diagrams for architectures
- Keep it up-to-date with code
- Use consistent formatting

### Writing Documentation

```markdown
## Feature Name

Brief description of the feature.

### Usage

```python
# Example code
from webis import WebisClient

client = WebisClient()
result = client.run("query")
```

### Configuration

| Parameter | Type | Default | Description |
|---|---|---|---|
| param1 | string | "default" | Description |

### Examples

- Example 1: Description
- Example 2: Description

### See Also

- [Related Feature](link)
- [Another Feature](link)
```

## Testing

### Writing Tests

- Write tests for all new features
- Use pytest for testing
- Mock external dependencies
- Test edge cases
- Keep tests independent

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from webis.core.plugin import MyPlugin

@pytest.fixture
def sample_config():
    return {"param1": "value1", "param2": 100}

def test_plugin_initialization(sample_config):
    """Test plugin initialization"""
    plugin = MyPlugin(config=sample_config)

    assert plugin.name == "my_plugin"
    assert plugin.config.param1 == "value1"

def test_plugin_processing(sample_config):
    """Test document processing"""
    plugin = MyPlugin(config=sample_config)
    input_data = ["doc1", "doc2"]

    result = plugin.process(input_data)

    assert len(result) == 2
    assert all(item.get("processed") for item in result)

async def test_async_functionality(sample_config):
    """Test async functions"""
    plugin = MyPlugin(config=sample_config)

    result = await plugin.async_process(["input"])

    assert result is not None
    assert isinstance(result, list)

@pytest.mark.integration
def test_plugin_with_real_api():
    """Integration test with real API"""
    # Skip if no API key
    pytest.skipif(not os.getenv("API_KEY"), reason="No API key")

    plugin = MyPlugin()
    # Real API test...
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=webis --cov-report=html

# Run specific test
pytest tests/test_plugin.py::test_plugin_initialization

# Run tests matching pattern
pytest -k "plugin"
```

## Getting Help

- 📚 [Documentation](https://narwhal-lab.github.io/webis)
- 💬 [Discussions](https://github.com/Narwhal-Lab/Webis/discussions)
- 🐛 [Issue Tracker](https://github.com/Narwhal-Lab/Webis/issues)
- 📧 [Email](mailto:contact@webis.dev)

## License

By contributing, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).

---

Thank you for contributing to Webis! 🙏