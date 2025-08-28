# Makefile for Mechanical Integrity AI System
# Production deployment and development commands

.PHONY: help dev prod test clean logs monitor backup

# Default target
help:
	@echo "Mechanical Integrity AI System - Make Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  dev         - Start development environment"
	@echo "  dev-build   - Build and start development environment"
	@echo "  dev-logs    - Show development logs"
	@echo "  dev-down    - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  prod        - Start production environment"
	@echo "  prod-build  - Build and start production environment"
	@echo "  prod-logs   - Show production logs"
	@echo "  prod-down   - Stop production environment"
	@echo ""
	@echo "Database:"
	@echo "  db-migrate  - Run database migrations"
	@echo "  db-backup   - Create database backup"
	@echo "  db-restore  - Restore database from backup"
	@echo ""
	@echo "Testing:"
	@echo "  test        - Run all tests"
	@echo "  test-unit   - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint        - Run code linting"
	@echo ""
	@echo "Monitoring:"
	@echo "  monitor     - Open monitoring dashboard"
	@echo "  metrics     - Show current metrics"
	@echo ""
	@echo "Utilities:"
	@echo "  clean       - Clean up containers and volumes"
	@echo "  logs        - Show all service logs"
	@echo "  health      - Check service health"

# Development environment
dev:
	docker-compose -f docker-compose.dev.yml up -d

dev-build:
	docker-compose -f docker-compose.dev.yml up -d --build

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

dev-down:
	docker-compose -f docker-compose.dev.yml down

# Production environment
prod:
	@echo "Starting production environment..."
	@echo "⚠️  Ensure .env file is configured with production values"
	docker-compose -f docker-compose.prod.yml up -d

prod-build:
	@echo "Building production environment..."
	docker-compose -f docker-compose.prod.yml up -d --build

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

prod-down:
	docker-compose -f docker-compose.prod.yml down

# Database operations
db-migrate:
	docker-compose -f docker-compose.prod.yml exec api uv run alembic upgrade head

db-backup:
	@echo "Creating database backup..."
	docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U mechanical_integrity -d mechanical_integrity > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql"

db-restore:
	@echo "⚠️  This will overwrite the existing database!"
	@read -p "Enter backup file path: " backup_file; \
	docker-compose -f docker-compose.prod.yml exec -T postgres psql -U mechanical_integrity -d mechanical_integrity < $$backup_file

# Testing
test:
	@echo "Running all tests..."
	cd backend && uv run pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

test-unit:
	@echo "Running unit tests..."
	cd backend && uv run pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	cd backend && uv run pytest tests/integration/ -v

test-safety:
	@echo "Running safety-critical tests..."
	cd backend && uv run pytest tests/safety/ tests/compliance/ -v --tb=short

lint:
	@echo "Running code linting..."
	cd backend && uv run ruff check .
	cd backend && uv run ruff format . --check

# Monitoring
monitor:
	@echo "Opening monitoring dashboard..."
	@echo "Grafana: http://localhost:3000 (admin/admin123)"
	@echo "Prometheus: http://localhost:9090"
	open http://localhost:3000 || xdg-open http://localhost:3000

metrics:
	@echo "Current system metrics:"
	curl -s http://localhost:8000/metrics | grep -E "(http_requests_total|api579_calculations_total|cache_operations_total)" | head -10

# Utilities
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose -f docker-compose.dev.yml down -v --remove-orphans
	docker-compose -f docker-compose.prod.yml down -v --remove-orphans
	docker system prune -f

clean-all: clean
	@echo "Removing all images..."
	docker system prune -af --volumes

logs:
	docker-compose -f docker-compose.prod.yml logs -f --tail=100

health:
	@echo "Checking service health..."
	@echo "API Health:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "API not responding"
	@echo ""
	@echo "Redis Health:"
	@docker-compose -f docker-compose.prod.yml exec redis redis-cli ping || echo "Redis not responding"
	@echo ""
	@echo "Database Health:"
	@docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U mechanical_integrity || echo "Database not responding"

# Security
security-scan:
	@echo "Running security scans..."
	@echo "Scanning Docker images..."
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image mechanical-integrity-api:latest
	@echo "Scanning dependencies..."
	cd backend && uv run safety check

# Deployment helpers
deploy-check:
	@echo "Pre-deployment checklist:"
	@echo "✓ Environment variables configured"
	@echo "✓ SSL certificates in place (if using HTTPS)"
	@echo "✓ Database backups recent"
	@echo "✓ Monitoring configured"
	@echo "✓ Health checks passing"
	@echo ""
	@echo "Run 'make prod' to deploy to production"

# Quick development setup
dev-setup: dev-build
	@echo "Waiting for services to start..."
	sleep 30
	@echo "Running database migrations..."
	docker-compose -f docker-compose.dev.yml exec api uv run alembic upgrade head
	@echo "Development environment ready!"
	@echo "API: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "PgAdmin: http://localhost:5050"
	@echo "Redis Commander: http://localhost:8081"

# Production deployment
prod-deploy: prod-build db-migrate
	@echo "Production deployment complete!"
	@echo "API: http://localhost:8000"
	@echo "Monitoring: http://localhost:3000"
	@echo "Remember to:"
	@echo "- Set up SSL certificates"
	@echo "- Configure backup schedules"
	@echo "- Set up alerting"