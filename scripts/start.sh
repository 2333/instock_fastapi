#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    log_success "Docker is available"
}

check_ports() {
    log_info "Checking port availability..."
    APP_PORT=8000
    DB_PORT=5432

    if lsof -i :$APP_PORT &> /dev/null; then
        log_warn "Port $APP_PORT is in use, will attempt to free it"
    fi
}

stop_existing() {
    log_info "Stopping existing containers..."
    docker compose down --remove-orphans 2>/dev/null || true
}

clean_old_images() {
    log_info "Cleaning up dangling images..."
    docker image prune -f 2>/dev/null || true
}

build_images() {
    log_info "Building images (using cache)..."
    if docker compose build; then
        log_success "Images built successfully"
        return 0
    fi

    log_warn "Build failed, retrying with no cache..."
    if docker compose build --no-cache; then
        log_success "Images built successfully (no cache)"
        return 0
    fi

    log_error "Failed to build images"
    return 1
}

start_services() {
    log_info "Starting services..."
    if docker compose up -d; then
        log_success "Services started"
    else
        log_error "Failed to start services"
        exit 1
    fi
}

wait_for_healthy() {
    log_info "Waiting for services to be healthy..."

    MAX_WAIT=60
    WAITED=0

    while [ $WAITED -lt $MAX_WAIT ]; do
        POSTGRES_STATUS=$(docker compose ps postgres 2>/dev/null | grep -o "healthy\|unhealthy" || echo "unknown")

        if [ "$POSTGRES_STATUS" = "healthy" ]; then
            log_success "PostgreSQL is healthy"
            break
        fi

        echo -n "."
        sleep 2
        WAITED=$((WAITED + 2))
    done
    echo ""

    if [ $WAITED -ge $MAX_WAIT ]; then
        log_warn "PostgreSQL health check timed out"
    fi
}

check_status() {
    log_info "Checking service status..."
    echo ""
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
}

verify_connection() {
    log_info "Verifying database connection..."

    MAX_RETRIES=10
    RETRY=0

    while [ $RETRY -lt $MAX_RETRIES ]; do
        if docker compose exec -T postgres pg_isready -U instock &> /dev/null; then
            log_success "Database connection verified"
            return 0
        fi

        RETRY=$((RETRY + 1))
        log_info "Waiting for database... ($RETRY/$MAX_RETRIES)"
        sleep 2
    done

    log_warn "Could not verify database connection, but services are running"
    return 1
}

show_access_info() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   Services Started Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "  ${BLUE}Home:${NC}          http://localhost:8000/"
    echo -e "  ${BLUE}API Docs:${NC}      http://localhost:8000/docs"
    echo -e "  ${BLUE}ReDoc:${NC}         http://localhost:8000/redoc"
    echo -e "  ${BLUE}Health Check:${NC}  http://localhost:8000/health"
    echo -e "  ${BLUE}Frontend:${NC}      http://localhost:3001/"
    echo ""
    echo -e "  ${BLUE}PostgreSQL:${NC}     localhost:5432"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo -e "  View logs:    ${GREEN}docker compose logs -f app${NC}"
    echo -e "  Stop:         ${GREEN}docker compose down${NC}"
    echo -e "  Full restart: ${GREEN}make docker-rebuild${NC}"
    echo ""
}

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}   InStock FastAPI - Docker Startup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    check_docker
    check_ports
    stop_existing
    clean_old_images
    build_images
    start_services
    wait_for_healthy
    check_status
    verify_connection
    show_access_info
}

main "$@"
