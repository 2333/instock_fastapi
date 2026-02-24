.PHONY: help install dev frontend-dev test lint clean setup init-db \
        docker-up docker-down docker-rebuild docker-status docker-logs \
        docker-clean docker-build format lint-check test-cov

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
	@echo "  make format         - 格式化代码"
	@echo ""
	@echo "测试:"
	@echo "  make test           - 运行测试"
	@echo "  make test-cov       - 运行测试并生成覆盖率"

# ============ 安装依赖 ============

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# ============ 开发环境 ============

setup: install-dev init-db
	@echo ""
	@echo "========================================="
	@echo "   开发环境初始化完成!"
	@echo "========================================="
	@echo ""
	@echo "启动开发服务器:"
	@echo "  make dev            # 后端"
	@echo "  make frontend-dev   # 前端"

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd web && npm run dev

# ============ Docker ============

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-rebuild:
	@echo "Stopping..."
	docker-compose down -v
	@echo "Building and starting..."
	docker-compose up --build -d
	@echo ""
	@echo "Waiting for services..."
	@for i in 1 2 3 4 5; do sleep 2; curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "Backend: OK" && break; done
	@curl -s http://localhost:3000 > /dev/null 2>&1 && echo "Frontend: OK" || echo "Frontend: Starting..."

docker-build:
	@echo "Building images..."
	docker-compose build --no-cache || echo "Build failed"

docker-status:
	@echo "=== Docker Status ==="
	@docker-compose ps
	@echo ""
	@echo "=== Endpoints ==="
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "Health:   http://localhost:8000/health"

docker-logs:
	docker-compose logs -f app

docker-clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans 2>/dev/null || true
	docker system prune -f 2>/dev/null || true
	@echo "Cleaned!"

# ============ 数据库 ============

init-db:
	python scripts/init_timescaledb.py

# ============ 测试 ============

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# ============ 代码质量 ============

lint-check:
	@echo "Running ruff..."
	ruff check app/ tests/ 2>/dev/null || echo "ruff not installed"
	@echo ""
	@echo "Running black..."
	black --check app/ tests/ 2>/dev/null || echo "black not installed"
	@echo ""
	@echo "Running isort..."
	isort --check-only app/ tests/ 2>/dev/null || echo "isort not installed"

format:
	@echo "Formatting code..."
	black app/ tests/ 2>/dev/null || true
	isort app/ tests/ 2>/dev/null || true
	ruff check --fix app/ tests/ 2>/dev/null || true
	@echo "Done!"

# ============ 清理 ============

clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned!"
