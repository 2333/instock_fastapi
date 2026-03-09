.PHONY: help install dev frontend-dev test lint clean setup init-db \
        docker-up docker-down docker-rebuild docker-status docker-logs \
        docker-clean docker-build docker-smoke format lint-check style-check style-fix \
        test-cov sync ci-backend ci-frontend ci

UV ?= uv
UV_CACHE_DIR ?= .uv-cache
UV_RUN = UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run
COV_FAIL_UNDER ?= 30
ENV_FILE ?= .env
DOCKER_COMPOSE = ENV_FILE=$(ENV_FILE) docker compose
STYLE_PATHS = \
	app/config.py \
	app/core/dependencies.py \
	app/api/routers/auth_router.py \
	app/api/routers/selection_router.py \
	app/api/routers/strategy_router.py \
	app/services/auth_service.py \
	app/services/attention_service.py \
	app/services/fund_flow_service.py \
	app/services/indicator_service.py \
	app/services/market_data_service.py \
	app/services/selection_service.py \
	app/services/stock_service.py \
	app/services/strategy_service.py \
	tests

help:
	@echo "InStock FastAPI - 智能股票分析平台"
	@echo ""
	@echo "快速开始:"
	@echo "  make setup          - 初始化开发环境（推荐）"
	@echo "  make docker-up      - 启动 Docker 服务"
	@echo ""
	@echo "开发命令:"
	@echo "  make dev            - 启动后端开发服务器"
	@echo "  make frontend-dev   - 启动前端开发服务器"
	@echo ""
	@echo "Docker 命令:"
	@echo "  make docker-up      - 启动所有容器"
	@echo "  make docker-down    - 停止所有容器"
	@echo "  make docker-rebuild - 重构并重启"
	@echo ""
	@echo "代码质量:"
	@echo "  make lint-check     - 检查代码"
	@echo "  make style-check    - 检查增量严格规范"
	@echo "  make style-fix      - 修复增量严格规范"
	@echo "  make format         - 格式化代码"
	@echo "  make ci-backend     - 本地执行后端 CI 检查"
	@echo "  make ci-frontend    - 本地执行前端 CI 检查"
	@echo ""
	@echo "测试:"
	@echo "  make test           - 运行测试"
	@echo "  make test-cov       - 运行测试并生成覆盖率"

# ============ 安装依赖 ============

install:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync --frozen --no-dev

install-dev:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync --frozen --dev

sync:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync --dev

# ============ 开发环境 ============

setup: sync init-db
	@echo ""
	@echo "========================================="
	@echo "   开发环境初始化完成!"
	@echo "========================================="
	@echo ""
	@echo "启动开发服务器:"
	@echo "  make dev            # 后端"
	@echo "  make frontend-dev   # 前端"

dev:
	$(UV_RUN) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd web && npm run dev

# ============ Docker ============

docker-up:
	$(DOCKER_COMPOSE) up -d

docker-down:
	$(DOCKER_COMPOSE) down

docker-rebuild:
	@echo "Stopping..."
	$(DOCKER_COMPOSE) down -v
	@echo "Building and starting..."
	$(DOCKER_COMPOSE) up --build -d
	@echo ""
	@echo "Waiting for services..."
	@for i in 1 2 3 4 5; do sleep 2; curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "Backend: OK" && break; done
	@curl -s http://localhost:3001 > /dev/null 2>&1 && echo "Frontend: OK" || echo "Frontend: Starting..."

docker-build:
	@echo "Building images..."
	$(DOCKER_COMPOSE) build --no-cache || echo "Build failed"

docker-smoke:
	chmod +x scripts/docker_smoke.sh
	./scripts/docker_smoke.sh

docker-status:
	@echo "=== Docker Status ==="
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "=== Endpoints ==="
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:3001"
	@echo "Health:   http://localhost:8000/health"

docker-logs:
	$(DOCKER_COMPOSE) logs -f app

docker-clean:
	@echo "Cleaning up Docker resources..."
	$(DOCKER_COMPOSE) down -v --remove-orphans 2>/dev/null || true
	docker system prune -f 2>/dev/null || true
	@echo "Cleaned!"

# ============ 数据库 ============

init-db:
	$(UV_RUN) python scripts/init_timescaledb.py

# ============ 测试 ============

test:
	$(UV_RUN) pytest tests/ -v --tb=short

test-cov:
	$(UV_RUN) pytest tests/ --cov=app --cov-report=html --cov-report=xml --cov-report=term-missing --cov-fail-under=$(COV_FAIL_UNDER)

# ============ 代码质量 ============

lint-check:
	@echo "Running ruff..."
	$(UV_RUN) ruff check app/ tests/ --select E9,F63,F7,F82

style-check:
	@echo "Running incremental style checks..."
	$(UV_RUN) black --check $(STYLE_PATHS)
	$(UV_RUN) ruff check $(STYLE_PATHS)

style-fix:
	@echo "Fixing incremental style issues..."
	$(UV_RUN) black $(STYLE_PATHS)
	$(UV_RUN) ruff check --fix $(STYLE_PATHS)

format:
	@echo "Formatting code..."
	$(UV_RUN) black app/ tests/
	$(UV_RUN) isort app/ tests/
	$(UV_RUN) ruff check --fix app/ tests/
	@echo "Done!"

ci-backend:
	$(UV_RUN) ruff check app tests --select E9,F63,F7,F82
	$(UV_RUN) black --check $(STYLE_PATHS)
	$(UV_RUN) ruff check $(STYLE_PATHS)
	$(UV_RUN) pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=$(COV_FAIL_UNDER)

ci-frontend:
	cd web && npm ci
	cd web && npm run typecheck
	cd web && npm run build

ci: ci-backend ci-frontend

# ============ 清理 ============

clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned!"
