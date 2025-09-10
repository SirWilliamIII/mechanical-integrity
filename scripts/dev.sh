#!/bin/bash

# Mechanical Integrity Management System - Development Mode Script
# Quick development startup with hot-reload and development optimizations

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $*"
}

# Development banner
show_banner() {
    echo ""
    echo -e "${BOLD}${YELLOW}================================================================${NC}"
    echo -e "${BOLD}${YELLOW}🚀 MECHANICAL INTEGRITY SYSTEM - DEVELOPMENT MODE${NC}"
    echo -e "${BOLD}${YELLOW}================================================================${NC}"
    echo -e "${BOLD}Development Features Enabled:${NC}"
    echo -e "  • Hot reload on file changes"
    echo -e "  • Verbose logging and debugging"
    echo -e "  • Faster startup (minimal safety checks)"
    echo -e "  • Development environment variables"
    echo -e "${BOLD}${YELLOW}================================================================${NC}"
    echo ""
}

# Quick service check
quick_service_check() {
    log "🔍 Quick development service check..."
    
    # Check PostgreSQL
    if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        warn "PostgreSQL not running - starting..."
        if command -v brew >/dev/null 2>&1 && [[ "$OSTYPE" == "darwin"* ]]; then
            brew services start postgresql@14 2>/dev/null || brew services start postgresql
        else
            error "Please start PostgreSQL manually"
            exit 1
        fi
    fi
    
    # Check Redis
    if ! redis-cli ping >/dev/null 2>&1; then
        warn "Redis not running - starting..."
        if command -v brew >/dev/null 2>&1 && [[ "$OSTYPE" == "darwin"* ]]; then
            brew services start redis
        else
            error "Please start Redis manually"
            exit 1
        fi
    fi
    
    log "✅ Core services ready"
}

# Install development dependencies
install_dev_deps() {
    log "📦 Installing development dependencies..."
    
    cd "$BACKEND_DIR"
    
    # Install backend with development extras
    uv sync --dev
    
    # Install frontend dependencies with pnpm for Vite compatibility
    if [ -d "${PROJECT_ROOT}/frontend" ]; then
        cd "${PROJECT_ROOT}/frontend"
        # Install pnpm if not available
        if ! command -v pnpm >/dev/null 2>&1; then
            info "Installing pnpm for Vite development..."
            npm install -g pnpm
        fi
        pnpm install
    fi
    
    log "✅ Dependencies installed"
}

# Set development environment
setup_dev_env() {
    log "⚙️  Setting up development environment..."
    
    # Export development environment variables
    export ENVIRONMENT="development"
    export DEBUG="true"
    export LOG_LEVEL="DEBUG"
    export RELOAD="true"
    
    # Create development .env if it doesn't exist
    if [ ! -f "$BACKEND_DIR/.env.dev" ]; then
        info "Creating development environment file..."
        cat > "$BACKEND_DIR/.env.dev" << EOF
# Development Environment Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://postgres:@localhost:5432/mechanical_integrity
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mechanical_integrity
POSTGRES_USER=postgres
POSTGRES_PASSWORD=

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama (optional for development)
OLLAMA_MODEL=llama3.2:latest
OLLAMA_API_BASE=http://localhost:11434

# Development settings
RELOAD=true
WORKERS=1
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080

# Safety factors (development - more permissive)
SAFETY_FACTOR=2.0
CORROSION_RATE=0.005
MAX_ALLOWABLE_STRESS=20000

# Feature flags
ENABLE_AI_EXTRACTION=false
ENABLE_DOCUMENT_PROCESSING=false
EOF
    fi
    
    log "✅ Development environment configured"
}

# Run minimal tests
run_dev_tests() {
    log "🧪 Running minimal development test suite..."
    
    cd "$BACKEND_DIR"
    
    # Run only basic functionality tests (fast)
    info "Running core functionality tests..."
    if PYTHONPATH="$(pwd)" uv run pytest tests/unit/test_basic.py tests/unit/test_simple.py -v --tb=short; then
        log "✅ Core tests passed"
    else
        warn "Some tests failed - continuing with development server"
    fi
}

# Start development server
start_dev_server() {
    log "🚀 Starting FastAPI development server..."
    
    cd "$BACKEND_DIR"
    
    info "Starting development server with hot reload..."
    info "Backend API: http://localhost:8000"
    info "Interactive Docs: http://localhost:8000/docs"
    info "OpenAPI Schema: http://localhost:8000/openapi.json"
    
    echo ""
    echo -e "${BOLD}${GREEN}🎯 Development server starting...${NC}"
    echo -e "${BOLD}Press Ctrl+C to stop${NC}"
    echo ""
    
    # Start with development settings
    PYTHONPATH="$(pwd)" uv run uvicorn app.main:app \
        --reload \
        --reload-dir app \
        --reload-dir models \
        --reload-dir core \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level debug \
        --env-file .env.dev \
        --access-log \
        --use-colors
}

# Parse command line arguments
SKIP_TESTS=false
QUICK_START=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --quick)
            QUICK_START=true
            SKIP_TESTS=true
            shift
            ;;
        --help|-h)
            echo "Mechanical Integrity System Development Mode"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-tests       Skip running development tests"
            echo "  --quick            Quick start mode (skip tests and checks)"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Development Features:"
            echo "  • Hot reload on file changes"
            echo "  • Debug logging enabled"
            echo "  • Permissive CORS settings"
            echo "  • Development environment variables"
            echo "  • Faster startup (minimal checks)"
            echo ""
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    show_banner
    
    # Setup development environment
    setup_dev_env
    
    if [ "$QUICK_START" = false ]; then
        # Quick service check
        quick_service_check
        
        # Install dependencies
        install_dev_deps
        
        # Run minimal tests
        if [ "$SKIP_TESTS" = false ]; then
            run_dev_tests
        fi
    else
        log "🏃 Quick start mode - skipping checks and tests"
    fi
    
    # Start development server
    start_dev_server
}

# Cleanup function
cleanup() {
    echo ""
    log "🛑 Development server stopped"
    echo ""
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"