# Mechanical Integrity AI System

AI-powered mechanical integrity management system for industrial equipment inspection and API 579 fitness-for-service analysis.

## Overview

This system provides safety-critical analysis for petroleum industry equipment, ensuring compliance with API 579, ASME, and industry standards. It combines AI-powered document processing with precise engineering calculations for equipment fitness assessments.

## Key Features

- **API 579 Compliance**: Fitness-for-service calculations with regulatory precision
- **Document Analysis**: AI-powered inspection report processing using local LLMs
- **Equipment Registry**: Comprehensive asset management with specification tracking and CRUD operations
- **Risk Assessment**: Remaining life and strength factor calculations
- **Corrosion Rate Analysis**: Statistical trend analysis with confidence intervals per `/api/v1/analysis/`
- **Risk-Based Inspection**: Automated interval calculations following API 580/581 per `/api/v1/rbi/`
- **Equipment Management Frontend**: Professional Vue.js interface with advanced filtering and export capabilities
- **Audit Trail**: Complete traceability for all safety-critical calculations
- **Session Isolation**: Production-safe background task processing with independent database sessions
- **Security Hardening**: Comprehensive input sanitization against injection attacks
- **Health Monitoring**: Real-time service health checks for Redis, Ollama, and PostgreSQL

## Safety-Critical Design

- **Zero tolerance for approximations** in calculations
- **Float64 precision** for all numerical operations
- **Conservative estimates** with appropriate safety factors
- **Human review required** for RSF < 0.9 or remaining life < 2 years
- **Complete audit logging** for regulatory compliance
- **Production-safe defaults** with explicit validation preventing debug mode in production
- **Session-per-task isolation** preventing data corruption in concurrent operations
- **Comprehensive input validation** protecting against injection attacks and malformed data

## Tech Stack

- **Backend**: FastAPI + PostgreSQL + Redis + Ollama
- **AI/LLM**: Ollama (local deployment for data security)
- **Frontend**: Vue.js
- **Package Management**: uv (Python)
- **Containers**: Podman

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis
- Ollama with llama3.2:latest

### Installation

```bash
# Install dependencies
uv sync

# Start services
brew services start postgresql@14
brew services start redis
ollama serve  # In separate terminal

# Verify services
uv run python backend/scripts/check_services.py

# Run application
cd backend
uv run uvicorn app.main:app --reload
```

### Environment Configuration

Create `.env` file:

```env
DATABASE_URL=postgresql://postgres:@localhost:5432/mechanical_integrity
REDIS_URL=redis://localhost:6379/0
OLLAMA_MODEL=llama3.2:latest
OLLAMA_API_BASE=http://localhost:11434
SAFETY_FACTOR=2.0
CORROSION_RATE=0.005
MAX_ALLOWABLE_STRESS=20000
```

## Development

### Running Tests

```bash
# All tests with verbose output
uv run pytest -v

# All tests with coverage
uv run pytest --cov=app tests/

# Unit tests only
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/integration/

# Current test status: 100 passing, 19 failing (edge cases), 4 errors (database constraints)
# Core safety-critical calculations: 100% passing
# API integration tests: 100% passing
```

### Code Quality

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy .
```

### Database Operations

```bash
# Initialize database
PYTHONPATH=backend uv run python backend/scripts/init_db.py

# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

## API 579 Calculations

### Supported Assessments

- **Level 1**: Basic fitness assessment
- **Level 2**: Detailed engineering analysis
- **Level 3**: Advanced numerical analysis (requires human approval)

### Key Formulas

- **RSF**: Remaining Strength Factor = (t_actual - FCA) / t_required
- **MAWP**: Maximum Allowable Working Pressure
- **FCA**: Future Corrosion Allowance with safety factors
- **Remaining Life**: Conservative time-based projections

### Precision Requirements

- Thickness measurements: ±0.001 inches
- Pressure calculations: ±0.1 psi
- Stress calculations: ±1 psi
- Always round remaining life down for safety

## API Endpoints

### Core APIs
- **Analysis API** (`/api/v1/analysis/`): Corrosion rate trend analysis with statistical regression
- **RBI API** (`/api/v1/rbi/`): Risk-based inspection interval calculations per API 580/581
- **Equipment API** (`/api/v1/equipment/`): Comprehensive CRUD operations for equipment management
- **Inspection API** (`/api/v1/inspections/`): Safety-critical inspection record processing
- **Health API** (`/health`): System health monitoring and service status

### Frontend Features
- **Equipment Management**: Professional interface with DataTable, filtering, and export
- **Dashboard**: Real-time equipment status and inspection due dates
- **Inspection Forms**: Safety-critical data entry with validation
- **Reporting**: Comprehensive audit trails and compliance reports

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Vue Frontend  │────▶│  FastAPI     │────▶│ PostgreSQL  │
│  (Port 5173)    │     │  (Port 8000) │     │ (Port 5432) │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                               ├──────▶ Redis (Job Queue)
                               │
                               └──────▶ Ollama (LLM)
```

## Contributing

1. Ensure all tests pass: `uv run pytest -v`
2. Check code quality: `uv run ruff check .`
3. Verify calculations against API 579 examples
4. Document any new safety-critical functions
5. Human review required for all calculation changes
6. Follow session-per-task pattern for database operations
7. Use production-safe configuration defaults
8. Implement comprehensive input validation for all user inputs

## Regulatory Compliance

This system is designed for use in safety-critical petroleum industry applications. All calculations must be validated against published API 579 standards. The system provides decision support but does not replace professional engineering judgment.

### Critical Thresholds

- **RSF < 0.9**: Immediate engineering review required
- **Remaining life < 2 years**: Priority inspection needed
- **Corrosion rate > expected**: Investigation required
- **Level 3 assessments**: Advanced analysis needed

## License

This project is intended for professional mechanical integrity applications in compliance with industry safety standards.