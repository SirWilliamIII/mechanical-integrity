# Mechanical Integrity Management System - Scripts

This directory contains production-ready startup, shutdown, and development scripts for the Mechanical Integrity Management System.

## 🚀 Quick Start

### Production Startup
```bash
./scripts/start.sh
```
Complete production-ready startup with all safety checks, service validation, and comprehensive health monitoring.

### Development Mode
```bash
./scripts/dev.sh
```
Fast development startup with hot-reload and debug features enabled.

### Stop System
```bash
./scripts/stop.sh
```
Gracefully shutdown all system components.

## 📋 Script Overview

### `start.sh` - Production Startup
**Purpose**: Complete production-ready system startup with comprehensive safety checks.

**Features**:
- ✅ Prerequisites validation (uv, node, npm)
- 🔧 Automatic service startup (PostgreSQL, Redis, Ollama)
- 📊 Comprehensive service health checks
- 🗄️ Database initialization and migration
- 🧪 Safety-critical test execution
- 🚀 Backend and frontend server startup
- 📱 Process monitoring and management
- 📝 Comprehensive logging and error handling

**Usage**:
```bash
# Full production startup
./scripts/start.sh

# Skip external services (if already running)
./scripts/start.sh --skip-services

# Skip safety tests (faster startup)
./scripts/start.sh --skip-tests

# Skip frontend server
./scripts/start.sh --skip-frontend

# Development mode with verbose output
./scripts/start.sh --dev
```

**Services Started**:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Ollama LLM service (port 11434)
- FastAPI Backend (port 8000)
- Vue.js Frontend (port 5173) *optional*

### `dev.sh` - Development Mode
**Purpose**: Fast development startup optimized for coding and testing.

**Features**:
- ⚡ Quick startup (minimal checks)
- 🔄 Hot reload on file changes
- 🐛 Debug logging enabled
- 🌐 Permissive CORS settings
- 📦 Development dependencies
- 🧪 Optional minimal test suite

**Usage**:
```bash
# Standard development mode
./scripts/dev.sh

# Skip development tests
./scripts/dev.sh --skip-tests

# Ultra-fast startup
./scripts/dev.sh --quick
```

### `stop.sh` - System Shutdown
**Purpose**: Gracefully shutdown all system components.

**Features**:
- 🛑 Graceful process termination
- 📊 Process monitoring during shutdown
- 🧹 Port cleanup
- 📝 Log file preservation
- 🗂️ Optional log cleanup

**Usage**:
```bash
# Standard shutdown (preserve logs)
./scripts/stop.sh

# Shutdown and clean logs
./scripts/stop.sh --clean-logs
```

## 🔧 System Requirements

### Required Tools
- **uv**: Python package manager (replaces pip)
- **node**: JavaScript runtime
- **npm**: Node.js package manager
- **PostgreSQL**: Primary database
- **Redis**: Caching and job queue

### Optional Tools
- **Homebrew**: Service management on macOS
- **Ollama**: LLM document processing
- **Docker/Podman**: Container support

## 📊 Process Management

### Log Files
All scripts create log files in the `logs/` directory:
- `backend.log`: FastAPI server logs
- `frontend.log`: Vue.js development server logs

### PID Files
Process IDs are stored for monitoring:
- `logs/backend.pid`: Backend server process ID
- `logs/frontend.pid`: Frontend server process ID

### Process Monitoring
The startup script continuously monitors processes and will exit if critical services fail.

## 🏥 Health Checks

### Service Validation
All scripts perform comprehensive health checks:
- Database connectivity and schema validation
- Redis connectivity and performance
- Ollama model availability
- API endpoint responsiveness

### Safety-Critical Testing
Production startup includes mandatory safety tests:
- API 579 calculation accuracy
- Decimal precision validation
- Dual-path verification consistency
- Regulatory compliance verification

## 🔐 Security & Safety

### Production Safety Features
- **Zero-tolerance precision**: All calculations use Decimal arithmetic
- **Conservative estimates**: Always round down remaining equipment life
- **Audit trails**: Complete traceability for regulatory compliance
- **Input validation**: Physical bounds checking on all measurements
- **Process isolation**: Session-per-task pattern prevents data corruption

### Development Security
- Development mode uses permissive settings for faster iteration
- Debug logging may expose sensitive information (development only)
- CORS allows local frontend development ports

## 🌐 Network Ports

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache and job queue |
| FastAPI Backend | 8000 | REST API server |
| Vue.js Frontend | 5173 | Development frontend |
| Ollama | 11434 | LLM processing service |

## 🗄️ Database Management

### Automatic Database Setup
Scripts automatically handle:
- Database creation (`mechanical_integrity`)
- Schema initialization
- Migration execution
- Connection validation

### Manual Database Commands
```bash
# Initialize database
cd backend
PYTHONPATH=/path/to/backend uv run python scripts/init_db.py

# Run migrations
PYTHONPATH=/path/to/backend uv run alembic upgrade head

# Create new migration
PYTHONPATH=/path/to/backend uv run alembic revision --autogenerate -m "description"
```

## 🧪 Testing Integration

### Test Categories
- **Unit Tests**: Core functionality validation
- **Integration Tests**: API endpoint testing
- **Safety Tests**: Edge cases and failure modes
- **Regression Tests**: API 579 compliance verification
- **Stress Tests**: Concurrent operation validation

### Manual Testing
```bash
# Run all tests
cd backend
PYTHONPATH=/path/to/backend uv run pytest

# Run safety-critical tests only
PYTHONPATH=/path/to/backend uv run pytest tests/safety/ tests/regression/

# Run with coverage
PYTHONPATH=/path/to/backend uv run pytest --cov=app tests/
```

## 🚨 Troubleshooting

### Common Issues

#### "Service check failed"
- Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
- Verify Redis is running: `redis-cli ping`
- Check service status: `brew services list` (macOS)

#### "Database connection failed"
- Create database: `createdb mechanical_integrity`
- Check PostgreSQL service: `brew services restart postgresql@14`
- Verify connection settings in `.env`

#### "Permission denied"
- Make scripts executable: `chmod +x scripts/*.sh`
- Check file ownership and permissions

#### "Port already in use"
- Stop existing processes: `./scripts/stop.sh`
- Check port usage: `lsof -i :8000`
- Kill process: `kill -9 <PID>`

### Log Analysis
```bash
# View real-time logs
tail -f logs/backend.log

# Search for errors
grep -i error logs/backend.log

# View startup sequence
grep -i startup logs/backend.log
```

## 🔄 Integration with Development Workflow

### IDE Integration
Scripts can be integrated with IDEs:
- **VS Code**: Add as terminal tasks
- **PyCharm**: Configure as external tools
- **Vim/Neovim**: Use as quickfix commands

### Git Hooks
Consider adding pre-commit hooks:
```bash
# .git/hooks/pre-commit
#!/bin/bash
cd backend
PYTHONPATH=/path/to/backend uv run pytest tests/safety/ --quiet
```

### CI/CD Integration
Scripts are designed for containerized environments:
```dockerfile
# Production Dockerfile example
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh
CMD ["/app/scripts/start.sh", "--skip-services"]
```

## 📈 Performance Monitoring

### Startup Metrics
- Service startup time tracking
- Health check duration monitoring
- Test execution timing
- Resource usage validation

### Runtime Monitoring
- Process health monitoring
- Memory usage tracking
- Database connection pooling
- API response time monitoring

---

**Safety Notice**: This is a safety-critical system for petroleum industry compliance. Always run the full safety test suite before production deployment.

**Support**: For issues or questions, refer to the main project documentation or create an issue in the project repository.