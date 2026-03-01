# Changelog

All notable changes to Webis will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Apache 2.0 License file
- MANIFEST.in for package distribution
- Pre-commit hooks for code quality
- Commit message linting configuration
- Comprehensive documentation structure
- Example code for different use cases

## [2.0.0-alpha.1] - 2024-02-XX

### Added
- Initial AI-powered knowledge pipeline
- Plugin-based architecture for data sources, processors, and extractors
- Intelligent crawler agent using LLMs
- RAG-ready capabilities with embedding generation
- Streamlit-based visualizer web interface
- CLI tools for pipeline management
- Support for multiple data sources (Tavily, GitHub, Semantic Scholar, etc.)
- PDF and HTML document processing
- OCR support for image-based documents
- LLM-based structured data extraction
- FastAPI server with REST endpoints
- Celery for background task processing
- Redis integration for message queuing
- Neo4j support for graph-based storage

### Changed
- Migrated to modular plugin system
- Improved pipeline orchestration

## [1.0.0-alpha] - 2024-01-XX

### Added
- Initial release
- Basic web scraping capabilities
- Simple document processing
- RAG pipeline foundation

---

## How to Update the Changelog

When you make a change to the project, add an entry to the "Unreleased" section at the top.

### Format
Use one of the following types:
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security-related fixes

### Example Entry
```markdown
## [Unreleased]

### Added
- New feature description

### Fixed
- Bug description with issue number (#123)
```

### Release Checklist
1. Move all items from "Unreleased" to a new version section
2. Add release date
3. Update version number in pyproject.toml
4. Update version number in src/webis/__init__.py
5. Create a new git tag
6. Publish to PyPI