.PHONY: help install install-dev sync dev frontend-dev test lint clean setup init-db \
        docker-up docker-down docker-rebuild docker-status docker-logs \
        docker-clean docker-build docker-smoke format lint-check style-check style-fix \
        test-cov sync ci-backend ci-frontend ci \
        version-show version-check version-set docker-build-version docker-deploy-version \
        dev-up dev-down dev-rebuild dev-status dev-logs dev-smoke \
        dev-local frontend-dev-local \
        staging-up staging-down staging-rebuild staging-status staging-logs staging-smoke \
        staging-local frontend-staging-local

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
	@echo "依赖与环境:"
	@echo "  make install        - 安装生产依赖"
	@echo "  make install-dev    - 安装开发依赖"
	@echo "  make sync           - 同步本地开发环境"
	@echo "  make setup          - 同步依赖并初始化数据库"
	@echo ""
	@echo "开发命令:"
	@echo "  make dev            - 启动后端开发服务器 (:8000)"
	@echo "  make frontend-dev   - 启动前端开发服务器 (:3000)"
	@echo ""
	@echo "Docker 命令:"
	@echo "  make docker-up      - 启动 Docker 全栈服务"
	@echo "  make docker-down    - 停止所有容器"
	@echo "  make docker-status  - 查看容器状态和访问入口"
	@echo "  make docker-smoke   - 执行 Docker 健康检查"
	@echo "  make docker-rebuild - 重建并重启 Docker 全栈"
	@echo "  make docker-build-version VERSION=x.y.z  - 构建带版本标签的镜像"
	@echo "  make docker-deploy-version VERSION=x.y.z - 使用版本化镜像部署"
	@echo ""
	@echo "测试环境 (不影响生产 8000/3001):"
	@echo "  make dev-up         - 构建并启动测试容器 (:8001 后端, :3002 前端)"
	@echo "  make dev-down       - 停止测试容器"
	@echo "  make dev-rebuild    - 重建测试容器（代码变动后）"
	@echo "  make dev-status     - 查看测试容器状态"
	@echo "  make dev-logs       - 查看测试容器日志"
	@echo "  make dev-smoke      - 测试容器健康检查"
	@echo "  make dev-local      - 本地启动后端 (:8001, 连测试容器 DB)"
	@echo "  make frontend-dev-local - 本地启动前端 (:3002)"
	@echo ""
	@echo "预发布环境 (复用生产 DB, 测试新代码):"
	@echo "  make staging-up       - 构建并启动预发布容器 (:$(STAGING_APP_PORT) 后端, :$(STAGING_FRONTEND_PORT) 前端)"
	@echo "  make staging-down     - 停止预发布容器"
	@echo "  make staging-rebuild  - 重建预发布容器"
	@echo "  make staging-status   - 查看预发布容器状态"
	@echo "  make staging-logs     - 查看预发布容器日志"
	@echo "  make staging-smoke    - 预发布容器健康检查"
	@echo "  make staging-local    - 本地启动后端 (:$(STAGING_APP_PORT), 连生产 DB)"
	@echo "  make frontend-staging-local - 本地启动前端 (:$(STAGING_FRONTEND_PORT))"
	@echo ""
	@echo "代码质量:"
	@echo "  make lint           - 运行基础静态检查"
	@echo "  make lint-check     - 运行后端基础错误检查"
	@echo "  make style-check    - 检查增量严格规范"
	@echo "  make style-fix      - 修复增量严格规范"
	@echo "  make format         - 格式化代码"
	@echo "  make ci-backend     - 本地执行后端 CI 检查"
	@echo "  make ci-frontend    - 本地执行前端 CI 检查"
	@echo "  make ci             - 运行完整 CI"
	@echo "  make version-show   - 显示当前仓库版本"
	@echo "  make version-check  - 检查版本文件是否同步"
	@echo "  make version-set VERSION=x.y.z - 更新仓库版本"
	@echo ""
	@echo "测试:"
	@echo "  make test           - 运行测试"
	@echo "  make test-cov       - 运行测试并生成覆盖率"
	@echo ""
	@echo "清理:"
	@echo "  make clean          - 清理缓存文件"

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

version-show:
	python3 scripts/release_version.py show

version-check:
	python3 scripts/release_version.py check

version-set:
	@test -n "$(VERSION)" || (echo "Usage: make version-set VERSION=x.y.z" && exit 1)
	python3 scripts/release_version.py set $(VERSION)

docker-build-version:
	@test -n "$(VERSION)" || (echo "Usage: make docker-build-version VERSION=x.y.z" && exit 1)
	VERSION=$(VERSION) sh scripts/build_release_images.sh

docker-deploy-version:
	@test -n "$(VERSION)" || (echo "Usage: make docker-deploy-version VERSION=x.y.z" && exit 1)
	VERSION=$(VERSION) ENV_FILE=$(ENV_FILE) sh scripts/deploy_release.sh

docker-smoke:
	chmod +x scripts/docker_smoke.sh
	./scripts/docker_smoke.sh

docker-status:
	@echo "=== Docker Status ==="
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "=== Endpoints ==="
	@echo "Home:     http://localhost:8000/"
	@echo "Docs:     http://localhost:8000/docs"
	@echo "ReDoc:    http://localhost:8000/redoc"
	@echo "Health:   http://localhost:8000/health"
	@echo "Frontend: http://localhost:3001/"

docker-logs:
	$(DOCKER_COMPOSE) logs -f app

docker-clean:
	@echo "Cleaning up Docker resources..."
	$(DOCKER_COMPOSE) down -v --remove-orphans 2>/dev/null || true
	docker system prune -f 2>/dev/null || true
	@echo "Cleaned!"

# ============ 测试环境 (Docker, 隔离端口) ============

DEV_COMPOSE = docker compose -f docker-compose.dev.yml
STAGING_APP_PORT ?= 8002
STAGING_FRONTEND_PORT ?= 3003

dev-up:
	@echo "Building and starting dev environment..."
	$(DEV_COMPOSE) up --build -d
	@echo ""
	@echo "Waiting for services..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		if curl -s http://localhost:8001/health > /dev/null 2>&1; then \
			echo "Backend:  http://localhost:8001 ✅"; \
			echo "Docs:     http://localhost:8001/docs"; \
			echo "Frontend: http://localhost:3002"; \
			echo "DB:       localhost:5433 (instock/instock_pass)"; \
			echo "Redis:    localhost:6381"; \
			break; \
		fi; \
		echo "  waiting... ($$i/10)"; \
	done

dev-down:
	$(DEV_COMPOSE) down

dev-rebuild:
	@echo "Stopping dev environment..."
	$(DEV_COMPOSE) down
	@echo "Rebuilding and starting..."
	$(DEV_COMPOSE) up --build -d
	@echo "Waiting for services..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		curl -s http://localhost:8001/health > /dev/null 2>&1 && echo "Backend: OK" && break; \
	done
	@curl -s http://localhost:3002 > /dev/null 2>&1 && echo "Frontend: OK" || echo "Frontend: Starting..."

dev-status:
	@echo "=== Dev Environment Status ==="
	@$(DEV_COMPOSE) ps
	@echo ""
	@echo "=== Endpoints ==="
	@echo "Backend:  http://localhost:8001/"
	@echo "Docs:     http://localhost:8001/docs"
	@echo "Health:   http://localhost:8001/health"
	@echo "Frontend: http://localhost:3002/"
	@echo "DB:       localhost:5433 (instock/instock_pass)"
	@echo "Redis:    localhost:6381"

dev-logs:
	$(DEV_COMPOSE) logs -f app

dev-smoke:
	@echo "=== Dev Health Check ==="
	@curl -s http://localhost:8001/health | python3 -m json.tool && echo "Backend: ✅" || echo "Backend: ❌"
	@curl -s -o /dev/null -w "Frontend: HTTP %{http_code}\n" http://localhost:3002/ && echo "Frontend: ✅" || echo "Frontend: ❌"

# ============ 本地开发 (非 Docker, 连测试容器 DB) ============
# 前提: make dev-up 已启动（提供 PG + Redis）

DEV_ENV = DATABASE_URL=postgresql+asyncpg://instock:instock_pass@localhost:5433/instock \
          SYNC_DATABASE_URL=postgresql+psycopg2://instock:instock_pass@localhost:5433/instock \
          REDIS_HOST=localhost REDIS_PORT=6381 \
          SECRET_KEY=dev-secret-key-change-in-production-12345678901234567890 \
          LOG_LEVEL=DEBUG DEBUG=true

dev-local:
	@echo "Starting backend on :8001 (connecting to dev containers)..."
	$(DEV_ENV) $(UV_RUN) uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

frontend-dev-local:
	cd web && VITE_API_URL=http://localhost:8001 npm run dev -- --port 3002

# ============ 预发布环境 (复用生产 DB, 测试新代码) ============

STAGING_COMPOSE = docker compose -p instock_staging -f docker-compose.staging.yml

staging-up:
	@echo "Building and starting staging environment (using production DB)..."
	$(STAGING_COMPOSE) up --build -d
	@echo ""
	@echo "Waiting for services..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		if curl -s http://localhost:$(STAGING_APP_PORT)/health > /dev/null 2>&1; then \
			echo "Backend:  http://localhost:$(STAGING_APP_PORT) ✅"; \
			echo "Docs:     http://localhost:$(STAGING_APP_PORT)/docs"; \
			echo "Frontend: http://localhost:$(STAGING_FRONTEND_PORT)"; \
			echo "DB:       production (localhost:5432)"; \
			break; \
		fi; \
		echo "  waiting... ($$i/10)"; \
	done

staging-down:
	$(STAGING_COMPOSE) down

staging-rebuild:
	@echo "Stopping staging environment..."
	$(STAGING_COMPOSE) down
	@echo "Rebuilding and starting..."
	$(STAGING_COMPOSE) up --build -d
	@echo "Waiting for services..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 2; \
		curl -s http://localhost:$(STAGING_APP_PORT)/health > /dev/null 2>&1 && echo "Backend: OK" && break; \
	done
	@curl -s http://localhost:$(STAGING_FRONTEND_PORT) > /dev/null 2>&1 && echo "Frontend: OK" || echo "Frontend: Starting..."

staging-status:
	@echo "=== Staging Environment Status ==="
	@$(STAGING_COMPOSE) ps
	@echo ""
	@echo "=== Endpoints ==="
	@echo "Backend:  http://localhost:$(STAGING_APP_PORT)/"
	@echo "Docs:     http://localhost:$(STAGING_APP_PORT)/docs"
	@echo "Health:   http://localhost:$(STAGING_APP_PORT)/health"
	@echo "Frontend: http://localhost:$(STAGING_FRONTEND_PORT)/"
	@echo "DB:       production (localhost:5432)"

staging-logs:
	$(STAGING_COMPOSE) logs -f app

staging-smoke:
	@echo "=== Staging Health Check ==="
	@curl -s http://localhost:$(STAGING_APP_PORT)/health | python3 -m json.tool && echo "Backend: ✅" || echo "Backend: ❌"
	@curl -s -o /dev/null -w "Frontend: HTTP %{http_code}\n" http://localhost:$(STAGING_FRONTEND_PORT)/ && echo "Frontend: ✅" || echo "Frontend: ❌"

# 本地热重载 + 生产 DB
STAGING_ENV = DATABASE_URL=postgresql+asyncpg://instock:instock_pass@localhost:5432/instock \
              SYNC_DATABASE_URL=postgresql+psycopg2://instock:instock_pass@localhost:5432/instock \
              REDIS_HOST=localhost REDIS_PORT=6380 \
              SECRET_KEY=dev-secret-key-change-in-production-12345678901234567890 \
              LOG_LEVEL=DEBUG DEBUG=true

staging-local:
	@echo "Starting backend on :$(STAGING_APP_PORT) (connecting to production DB)..."
	$(STAGING_ENV) $(UV_RUN) uvicorn app.main:app --reload --host 0.0.0.0 --port $(STAGING_APP_PORT)

frontend-staging-local:
	cd web && VITE_API_URL=http://localhost:$(STAGING_APP_PORT) npm run dev -- --port $(STAGING_FRONTEND_PORT)

# ============ 数据库 ============

init-db:
	$(UV_RUN) python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"

# ============ 测试 ============

test:
	$(UV_RUN) pytest tests/ -v --tb=short

test-cov:
	$(UV_RUN) pytest tests/ --cov=app --cov-report=html --cov-report=xml --cov-report=term-missing --cov-fail-under=$(COV_FAIL_UNDER)

# ============ 代码质量 ============

lint-check:
	@echo "Running ruff..."
	$(UV_RUN) ruff check app/ tests/ --select E9,F63,F7,F82

lint: lint-check

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
