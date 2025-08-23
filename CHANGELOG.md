# Changelog

All notable changes to the Mechanical Integrity Management System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete session isolation for background calculations using "Session per task" pattern
- Production-safe configuration defaults with safety validation
- Comprehensive input sanitization for equipment tags and extracted data
- Redis and Ollama health checks with graceful degradation
- Database schema validation for complete mechanical integrity schema (4 tables)
- Safety-critical validation preventing DEBUG=True in production environment
- Multi-layer security validation against SQL injection, XSS, path traversal attacks
- Comprehensive audit trail for regulatory compliance requirements

### Changed
- **BREAKING**: API579Service constructor now requires sessionmaker instead of Session instance
- Production environment defaults changed from development to production-safe values
- Background task processing now uses independent database sessions per operation
- Health check endpoint now validates all required database tables
- Confidence level calculation updated to be dynamic based on thickness reading count

### Fixed
- Session isolation issues causing test failures and production threading problems
- Async/sync mismatch in application startup health checks
- Background calculation task session conflicts
- Database connection conflicts in concurrent operations
- Input sanitization vulnerabilities for extracted equipment data

### Security
- Added comprehensive input sanitization functions for petroleum industry naming conventions
- Implemented detection and blocking of injection attacks (SQL, XSS, path traversal, command injection)
- Added validation for thickness values, corrosion rates, and confidence scores
- Implemented length limits and content filtering for safety-critical data inputs

### Performance
- Improved concurrent background task processing with proper session isolation
- Enhanced database connection pool management for production environments
- Optimized health check system with service-specific error handling

### Technical Debt
- Resolved 5 high-priority safety-critical TODOs
- Updated session management patterns across API endpoints
- Improved error handling and logging in background tasks
- Enhanced test coverage with session isolation fixes

## [0.1.0] - Initial Release

### Added
- Initial mechanical integrity management system
- API 579 fitness-for-service calculations
- Equipment registry and inspection tracking
- Vue.js frontend with inspection forms
- PostgreSQL database with Alembic migrations
- Ollama LLM integration for document processing
- Comprehensive test suite for safety-critical calculations