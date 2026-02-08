# Changelog

All notable changes to the Axiomeer Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-02-08

### Changed
- First public release on PyPI
- Fixed build configuration for clean wheel generation
- Updated license format for modern setuptools compatibility

### Installation
```bash
pip install axiomeer
```

---

## [0.1.0] - 2026-02-08

### Added
- Initial release of Axiomeer Python SDK
- Natural language tool discovery with `shop()` method
- Tool execution with `execute()` method
- Marketplace browsing with `list_apps()` method
- Health check with `health()` method
- Full authentication support (API Key + JWT)
- Comprehensive error handling with custom exception types
- Type hints and dataclasses for better IDE support
- Complete documentation and code examples
- Production-ready with mandatory authentication
- Rate limiting support

### Features
- **Natural Language Shopping**: Find tools using plain English queries
- **Direct Execution**: Execute tools by app_id with parameters
- **Tool Chaining**: Chain multiple tool executions together
- **Error Recovery**: Automatic retry on rate limit with backoff
- **Type Safety**: Full Python type annotations for better IDE support

### Documentation
- Complete README with installation and usage instructions
- API reference with method signatures and examples
- Basic usage examples demonstrating common patterns
- Advanced usage examples with error handling and chaining
- Real output examples with screenshots

### Security
- Mandatory authentication (no anonymous access)
- API key validation before requests
- SHA-256 hashing for API key storage
- Rate limiting enforcement by tier
- Secure credential management via environment variables

### Dependencies
- `requests>=2.31.0` - HTTP client library

### Compatibility
- Python 3.8+
- Windows, macOS, Linux

---

## [Unreleased]

### Planned for v0.2.0
- Async/await support for non-blocking operations
- Streaming responses for long-running executions
- Webhook support for asynchronous notifications
- Request/response logging for debugging
- Retry with exponential backoff
- Connection pooling for better performance

### Planned for v0.3.0
- LangChain integration plugin
- CrewAI tool wrapper
- AutoGPT plugin
- Haystack node implementation

### Planned for v1.0.0
- Production stable release
- Full test coverage (95%+)
- Performance optimizations
- Comprehensive documentation site
- Enterprise support options

---

## Version History

- **0.1.1** (2026-02-08) - First PyPI release (`pip install axiomeer`)
- **0.1.0** (2026-02-08) - Initial development release

---

## Links

- **PyPI**: https://pypi.org/project/axiomeer/
- **Documentation**: https://docs.axiomeer.com
- **Repository**: https://github.com/axiomeer/axiomeer-sdk-python
- **Issues**: https://github.com/axiomeer/axiomeer-sdk-python/issues
- **Changelog**: https://github.com/axiomeer/axiomeer-sdk-python/blob/main/CHANGELOG.md
