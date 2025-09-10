#!/bin/bash

# Mechanical Integrity Management System - Stop Script
# Gracefully shut down all system components

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
LOG_DIR="${PROJECT_ROOT}/logs"

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
    echo -e "${BOLD}${RED}================================================================${NC}"
    echo -e "${BOLD}${RED}🛑 MECHANICAL INTEGRITY SYSTEM SHUTDOWN${NC}"
    echo -e "${BOLD}${RED}================================================================${NC}"
    echo ""
}

# Stop process by PID file
stop_process() {
    local service_name="$1"
    local pid_file="$2"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            info "Stopping $service_name (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown
            local wait_time=0
            while kill -0 "$pid" 2>/dev/null && [ $wait_time -lt 10 ]; do
                echo -ne "\r${YELLOW}⏳${NC} Waiting for $service_name to stop... ${wait_time}s"
                sleep 1
                wait_time=$((wait_time + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo ""
                warn "Force killing $service_name..."
                kill -KILL "$pid" 2>/dev/null || true
                sleep 1
            else
                echo ""
            fi
            
            log "✅ $service_name stopped"
        else
            warn "$service_name process (PID: $pid) not running"
        fi
        
        rm -f "$pid_file"
    else
        info "$service_name PID file not found - may not be running"
    fi
}

# Stop any processes listening on specific ports
stop_port_processes() {
    local port="$1"
    local service_name="$2"
    
    if command -v lsof >/dev/null 2>&1; then
        local pids=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            info "Stopping processes on port $port ($service_name)..."
            for pid in $pids; do
                if kill -0 "$pid" 2>/dev/null; then
                    kill -TERM "$pid" 2>/dev/null || true
                    sleep 2
                    if kill -0 "$pid" 2>/dev/null; then
                        kill -KILL "$pid" 2>/dev/null || true
                    fi
                fi
            done
            log "✅ Port $port processes stopped"
        fi
    fi
}

# Main stop function
stop_system() {
    show_banner
    
    # Stop backend server
    stop_process "Backend Server" "$LOG_DIR/backend.pid"
    
    # Stop frontend server
    stop_process "Frontend Server" "$LOG_DIR/frontend.pid"
    
    # Ensure ports are clear
    stop_port_processes 8000 "Backend"
    stop_port_processes 5173 "Frontend"
    
    # Clean up log files (optional)
    if [ "$1" = "--clean-logs" ]; then
        info "Cleaning up log files..."
        rm -f "$LOG_DIR"/*.log
        log "✅ Log files cleaned"
    fi
    
    echo ""
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo -e "${BOLD}${GREEN}✅ MECHANICAL INTEGRITY SYSTEM STOPPED${NC}"
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo ""
    echo -e "${BOLD}System Status:${NC} All services stopped"
    if [ "$1" != "--clean-logs" ]; then
        echo -e "${BOLD}Log Files:${NC} Preserved in $LOG_DIR"
        echo -e "${BOLD}Tip:${NC} Use ${BLUE}--clean-logs${NC} to remove log files"
    fi
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean-logs)
            stop_system --clean-logs
            exit 0
            ;;
        --help|-h)
            echo "Mechanical Integrity System Stop Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --clean-logs       Remove log files after stopping services"
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

# Default stop (preserve logs)
stop_system