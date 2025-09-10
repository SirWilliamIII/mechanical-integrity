#!/bin/bash

# Mechanical Integrity Management System - Startup Script
# Production-ready startup script with comprehensive service checks and initialization
# Safety-critical system for petroleum industry API 579 compliance

set -euo pipefail  # Exit on any error, undefined variables, or pipe failures

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
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
LOG_DIR="${PROJECT_ROOT}/logs"
MAX_WAIT_TIME=60
HEALTH_CHECK_RETRIES=5

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

# Banner display
show_banner() {
    echo ""
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo -e "${BOLD}${BLUE}🏭 MECHANICAL INTEGRITY MANAGEMENT SYSTEM STARTUP${NC}"
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo -e "${BOLD}Safety-Critical API 579 Compliance System${NC}"
    echo -e "${BOLD}Version: Production-Ready${NC}"
    echo -e "${BOLD}Environment: $(cd ${BACKEND_DIR} && uv run python -c 'from core.config import settings; print(settings.ENVIRONMENT)')${NC}"
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required tools
check_prerequisites() {
    log "🔧 Checking prerequisites..."
    
    local missing_tools=()
    
    # Essential tools
    if ! command_exists uv; then
        missing_tools+=("uv (Python package manager)")
    fi
    
    if ! command_exists node; then
        missing_tools+=("node (JavaScript runtime)")
    fi
    
    if ! command_exists npm; then
        missing_tools+=("npm (Node package manager)")
    fi
    
    # Optional but recommended
    if ! command_exists brew && [[ "$OSTYPE" == "darwin"* ]]; then
        warn "Homebrew not found - manual service management required"
    fi
    
    if ! command_exists docker && ! command_exists podman; then
        warn "Neither Docker nor Podman found - container features disabled"
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools:"
        for tool in "${missing_tools[@]}"; do
            echo -e "  ${RED}❌${NC} $tool"
        done
        echo ""
        echo "Please install missing tools and try again."
        exit 1
    fi
    
    log "✅ All prerequisites satisfied"
}

# Wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local check_command="$2"
    local wait_time=0
    
    info "Waiting for $service_name to be ready..."
    
    while [ $wait_time -lt $MAX_WAIT_TIME ]; do
        if eval "$check_command" >/dev/null 2>&1; then
            log "✅ $service_name is ready"
            return 0
        fi
        
        echo -ne "\r${YELLOW}⏳${NC} Waiting for $service_name... ${wait_time}s"
        sleep 2
        wait_time=$((wait_time + 2))
    done
    
    echo ""
    error "$service_name failed to start within ${MAX_WAIT_TIME}s"
    return 1
}

# Start PostgreSQL service
start_postgresql() {
    log "🐘 Starting PostgreSQL..."
    
    if command_exists brew && [[ "$OSTYPE" == "darwin"* ]]; then
        if brew services list | grep -q "postgresql.*started"; then
            log "✅ PostgreSQL already running"
        else
            brew services start postgresql@14 || brew services start postgresql
            wait_for_service "PostgreSQL" "pg_isready -h localhost -p 5432"
        fi
    else
        # Check if PostgreSQL is already running
        if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
            log "✅ PostgreSQL already running"
        else
            warn "PostgreSQL not running - please start it manually"
            echo "  sudo systemctl start postgresql"
            echo "  or"
            echo "  pg_ctl start -D /usr/local/var/postgres"
            return 1
        fi
    fi
    
    # Create database if it doesn't exist
    if ! psql -h localhost -p 5432 -U "$USER" -lqt | cut -d \| -f 1 | grep -qw mechanical_integrity; then
        info "Creating mechanical_integrity database..."
        createdb -h localhost -p 5432 -U "$USER" mechanical_integrity || {
            warn "Failed to create database - it may already exist"
        }
    fi
}

# Start Redis service
start_redis() {
    log "🔴 Starting Redis..."
    
    if command_exists brew && [[ "$OSTYPE" == "darwin"* ]]; then
        if brew services list | grep -q "redis.*started"; then
            log "✅ Redis already running"
        else
            brew services start redis
            wait_for_service "Redis" "redis-cli ping"
        fi
    else
        # Check if Redis is already running
        if redis-cli ping >/dev/null 2>&1; then
            log "✅ Redis already running"
        else
            warn "Redis not running - please start it manually"
            echo "  sudo systemctl start redis"
            echo "  or"
            echo "  redis-server"
            return 1
        fi
    fi
}

# Start Ollama service
start_ollama() {
    log "🦙 Starting Ollama..."
    
    # Check if Ollama is already running
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        log "✅ Ollama already running"
        
        # Check for required model
        if ! curl -sf http://localhost:11434/api/tags | grep -q "llama3.2:latest"; then
            warn "llama3.2:latest model not found"
            info "Pulling required model (this may take a few minutes)..."
            ollama pull llama3.2:latest
        fi
    else
        warn "Ollama not running - please start it manually in a separate terminal:"
        echo "  ollama serve"
        echo ""
        echo "Then pull the required model:"
        echo "  ollama pull llama3.2:latest"
        return 1
    fi
}

# Run comprehensive service check
check_all_services() {
    log "🔍 Running comprehensive service check..."
    
    cd "$BACKEND_DIR"
    if PYTHONPATH="$(pwd)" uv run python scripts/check_services.py; then
        log "✅ All services operational"
        return 0
    else
        error "Service check failed"
        return 1
    fi
}

# Initialize database
init_database() {
    log "🗄️  Initializing database..."
    
    cd "$BACKEND_DIR"
    
    # Set proper PYTHONPATH and run database initialization
    info "Setting up database schema..."
    if PYTHONPATH="$(pwd)" uv run python scripts/init_db.py; then
        log "✅ Database schema initialized"
    else
        warn "Database initialization failed - may already exist"
    fi
    
    # Run migrations
    info "Applying database migrations..."
    if PYTHONPATH="$(pwd)" uv run alembic upgrade head; then
        log "✅ Database migrations applied"
    else
        error "Database migration failed"
        return 1
    fi
    
    log "✅ Database initialization complete"
}

# Install dependencies
install_dependencies() {
    log "📦 Installing dependencies..."
    
    # Backend dependencies
    info "Installing backend dependencies..."
    cd "$BACKEND_DIR"
    if ! uv sync; then
        error "Backend dependency installation failed"
        return 1
    fi
    
    # Frontend dependencies (if frontend exists)
    if [ -d "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ]; then
        info "Installing frontend dependencies with pnpm (Vite-optimized)..."
        cd "$FRONTEND_DIR"
        
        # Clear any corrupted npm/vite cache
        rm -rf node_modules/.vite 2>/dev/null || true
        rm -f package-lock.json 2>/dev/null || true  # Remove npm lock file
        
        # Install pnpm if not available
        if ! command -v pnpm >/dev/null 2>&1; then
            info "Installing pnpm for Vite compatibility..."
            npm install -g pnpm
        fi
        
        if ! pnpm install; then
            error "Frontend dependency installation failed"
            return 1
        fi
        
        # Verify Vite installation with pnpm
        if ! pnpm list vite >/dev/null 2>&1; then
            warn "Vite not properly installed - frontend may not start"
        fi
    fi
    
    cd "$PROJECT_ROOT"
    log "✅ Dependencies installed"
}

# Run tests
run_tests() {
    log "🧪 Running safety-critical tests..."
    
    cd "$BACKEND_DIR"
    
    # Run critical safety tests only (faster startup)
    info "Running safety-critical test suite..."
    if PYTHONPATH="$(pwd)" uv run pytest tests/safety/ tests/regression/ -v --tb=short --maxfail=3; then
        log "✅ Safety-critical tests passed"
    else
        error "Safety-critical tests failed - system may not be safe to start"
        return 1
    fi
}

# Start backend server
start_backend() {
    log "🚀 Starting FastAPI backend server..."
    
    cd "$BACKEND_DIR"
    
    # Create logs directory
    mkdir -p "$LOG_DIR"
    
    # Start server in background
    info "Starting server on http://localhost:8000"
    PYTHONPATH="$(pwd)" uv run uvicorn app.main:app \
        --reload \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        --access-log \
        > "$LOG_DIR/backend.log" 2>&1 &
    
    local backend_pid=$!
    echo $backend_pid > "$LOG_DIR/backend.pid"
    
    # Wait for backend to be ready
    wait_for_service "FastAPI Backend" "curl -sf http://localhost:8000/health"
    
    # Run health check
    info "Running backend health check..."
    local health_status
    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        if health_status=$(curl -sf http://localhost:8000/health/detailed); then
            log "✅ Backend health check passed"
            echo "$health_status" | python3 -m json.tool
            break
        else
            warn "Health check attempt $i/$HEALTH_CHECK_RETRIES failed"
            if [ $i -eq $HEALTH_CHECK_RETRIES ]; then
                # Try basic health check as fallback
                if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
                    warn "Detailed health check failed but basic health check passed - continuing"
                    log "✅ Backend basic health check passed"
                    break
                else
                    error "Backend health check failed after $HEALTH_CHECK_RETRIES attempts"
                    return 1
                fi
            fi
            sleep 3
        fi
    done
}

# Start frontend server (optional)
start_frontend() {
    if [ -d "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ]; then
        log "🖥️  Starting Vue.js frontend server..."
        
        cd "$FRONTEND_DIR"
        
        # Check Node.js version compatibility
        local node_version=$(node --version | grep -oE '[0-9]+' | head -1)
        if [ "$node_version" -lt 20 ]; then
            error "Node.js version $node_version is too old. Requires Node.js 20+ for this frontend"
            return 1
        fi
        
        # Clear Vite cache and temporary files
        info "Clearing Vite cache..."
        rm -rf node_modules/.vite .vite 2>/dev/null || true
        
        # Verify npm dependencies are properly installed
        if ! npm list >/dev/null 2>&1; then
            warn "Dependencies may be corrupted - reinstalling..."
            npm install --force
        fi
        
        # Start frontend with enhanced error handling
        info "Starting frontend on http://localhost:5173"
        
        # Try to start Vite dev server with pnpm
        if ! pnpm run dev > "$LOG_DIR/frontend.log" 2>&1 & then
            error "Failed to start frontend development server"
            cat "$LOG_DIR/frontend.log" | tail -10
            return 1
        fi
        
        local frontend_pid=$!
        echo $frontend_pid > "$LOG_DIR/frontend.pid"
        
        # Wait for frontend with extended timeout for Vite
        info "Waiting for Vite development server (this may take a minute for first startup)..."
        local frontend_wait_time=0
        local frontend_max_wait=90
        
        while [ $frontend_wait_time -lt $frontend_max_wait ]; do
            if curl -sf http://localhost:5173 >/dev/null 2>&1; then
                log "✅ Frontend server started successfully"
                break
            fi
            
            echo -ne "\r${YELLOW}⏳${NC} Waiting for Vue.js Frontend... ${frontend_wait_time}s"
            sleep 2
            frontend_wait_time=$((frontend_wait_time + 2))
        done
        
        if [ $frontend_wait_time -ge $frontend_max_wait ]; then
            echo ""
            error "Frontend failed to start within ${frontend_max_wait}s"
            info "Check frontend log: cat $LOG_DIR/frontend.log"
            warn "Continuing with backend-only mode..."
            rm -f "$LOG_DIR/frontend.pid"
            return 0  # Don't fail the entire startup for frontend issues
        else
            echo ""
        fi
        
    else
        warn "Frontend directory not found or package.json missing - skipping frontend"
    fi
}

# Display startup summary
show_summary() {
    echo ""
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo -e "${BOLD}${GREEN}🎯 MECHANICAL INTEGRITY SYSTEM STARTUP COMPLETE${NC}"
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo ""
    echo -e "${BOLD}Backend API:${NC} http://localhost:8000"
    echo -e "${BOLD}API Docs:${NC}    http://localhost:8000/docs"
    echo -e "${BOLD}Health Check:${NC} http://localhost:8000/health"
    
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        echo -e "${BOLD}Frontend:${NC}    http://localhost:5173"
    fi
    
    echo ""
    echo -e "${BOLD}Log Files:${NC}"
    echo -e "  Backend:  $LOG_DIR/backend.log"
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        echo -e "  Frontend: $LOG_DIR/frontend.log"
    fi
    
    echo ""
    echo -e "${BOLD}Process IDs:${NC}"
    if [ -f "$LOG_DIR/backend.pid" ]; then
        echo -e "  Backend:  $(cat $LOG_DIR/backend.pid)"
    fi
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        echo -e "  Frontend: $(cat $LOG_DIR/frontend.pid)"
    fi
    
    echo ""
    echo -e "${BOLD}Next Steps:${NC}"
    echo -e "  • Run integration tests: ${BLUE}cd backend && uv run pytest tests/integration/${NC}"
    echo -e "  • View logs: ${BLUE}tail -f $LOG_DIR/backend.log${NC}"
    echo -e "  • Stop system: ${BLUE}./scripts/stop.sh${NC}"
    echo ""
    echo -e "${BOLD}${GREEN}System is ready for production use! 🚀${NC}"
    echo ""
}

# Cleanup function
cleanup_on_exit() {
    if [ -f "$LOG_DIR/backend.pid" ]; then
        local backend_pid=$(cat "$LOG_DIR/backend.pid")
        if kill -0 "$backend_pid" 2>/dev/null; then
            info "Stopping backend server (PID: $backend_pid)..."
            kill "$backend_pid" 2>/dev/null || true
            rm -f "$LOG_DIR/backend.pid"
        fi
    fi
    
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        local frontend_pid=$(cat "$LOG_DIR/frontend.pid")
        if kill -0 "$frontend_pid" 2>/dev/null; then
            info "Stopping frontend server (PID: $frontend_pid)..."
            kill "$frontend_pid" 2>/dev/null || true
            rm -f "$LOG_DIR/frontend.pid"
        fi
    fi
}

# Handle script interruption
trap cleanup_on_exit EXIT INT TERM

# Parse command line arguments
SKIP_SERVICES=false
SKIP_TESTS=false
SKIP_FRONTEND=false
DEV_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-services)
            SKIP_SERVICES=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --help|-h)
            echo "Mechanical Integrity System Startup Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-services    Skip starting external services (PostgreSQL, Redis, Ollama)"
            echo "  --skip-tests       Skip running safety-critical tests"
            echo "  --skip-frontend    Skip starting frontend server"
            echo "  --dev              Development mode (more verbose output)"
            echo "  --help, -h         Show this help message"
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
    
    # Create necessary directories
    mkdir -p "$LOG_DIR"
    
    # Check prerequisites
    check_prerequisites
    
    # Install dependencies
    install_dependencies
    
    # Start external services (unless skipped)
    if [ "$SKIP_SERVICES" = false ]; then
        start_postgresql || exit 1
        start_redis || exit 1
        start_ollama || warn "Ollama not available - document analysis features disabled"
    fi
    
    # Check all services
    if [ "$SKIP_SERVICES" = false ]; then
        check_all_services || exit 1
    fi
    
    # Initialize database
    init_database
    
    # Run safety tests (unless skipped)
    if [ "$SKIP_TESTS" = false ]; then
        run_tests || exit 1
    fi
    
    # Start backend
    start_backend || exit 1
    
    # Start frontend (unless skipped)
    if [ "$SKIP_FRONTEND" = false ]; then
        start_frontend
    fi
    
    # Show summary
    show_summary
    
    # Keep script running to maintain servers
    info "Press Ctrl+C to stop all services..."
    
    # Monitor processes
    while true; do
        sleep 5
        
        # Check if backend is still running
        if [ -f "$LOG_DIR/backend.pid" ]; then
            local backend_pid=$(cat "$LOG_DIR/backend.pid")
            if ! kill -0 "$backend_pid" 2>/dev/null; then
                error "Backend process died unexpectedly"
                exit 1
            fi
        fi
        
        # Check if frontend is still running (if enabled)
        if [ -f "$LOG_DIR/frontend.pid" ]; then
            local frontend_pid=$(cat "$LOG_DIR/frontend.pid")
            if ! kill -0 "$frontend_pid" 2>/dev/null; then
                warn "Frontend process died unexpectedly"
                rm -f "$LOG_DIR/frontend.pid"
            fi
        fi
    done
}

# Run main function
main "$@"