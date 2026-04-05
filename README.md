# InStock FastAPI - 智能股票分析平台

InStock FastAPI 是一个面向股票分析场景的全栈项目，后端基于 FastAPI，前端基于 Vue 3 + Vite，配套技术分析、形态识别、策略选股、回测和资金流向等能力。

## 项目组成

- `app/`：FastAPI 后端应用，负责 API、业务服务、数据库初始化和任务调度。
- `core/`：核心分析能力，包括采集、指标、形态、策略和回测。
- `web/`：Vue 3 前端工程，同时包含后端根路径使用的静态首页模板与样式。
- `docs/`：产品、架构和接口文档。
- `scripts/`：初始化、构建和部署脚本。

## 快速开始

### 本地开发

```bash
uv sync --dev
make dev
```

前端开发服务器单独启动：

```bash
cd web
npm install
npm run dev
```

### Docker 部署

```bash
make docker-up
make docker-status
make docker-smoke
```

## 常用命令

```bash
# 依赖与环境
make install
make install-dev
make sync
make setup

# 开发
make dev
make frontend-dev

# 代码质量与测试
make lint
make style-check
make style-fix
make format
make test
make ci-backend
make ci-frontend
make ci

# Docker
make docker-up
make docker-down
make docker-status
make docker-smoke
make docker-rebuild

# 数据库
make init-db
```

## 版本管理

仓库使用根目录 [`VERSION`](./VERSION) 作为单一版本源，遵循语义化版本。

```bash
make version-show
make version-check
make version-set VERSION=0.2.0
```

发布环境可使用版本化镜像：

```bash
make docker-build-version VERSION=0.2.0
make docker-deploy-version VERSION=0.2.0
```

运行时版本会暴露在：

- `GET /health`
- `GET /api/v1/info`
- 前端顶部版本徽标

## 访问入口

- 后端首页：`http://localhost:8000/`
- 接口文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`
- 前端开发服务器：`http://localhost:3000/`
- Docker 统一入口：`http://localhost:3001/`

## 关键说明

- 后端入口位于 [`app/main.py`](./app/main.py)，会挂载 `web/static` 并渲染 `web/templates/index.html`。
- `web/` 目录下既有独立前端工程，也有后端静态首页资源，两者用途不同。
- 具体 API、架构和产品说明以 `docs/` 目录内文档为准。

## 文档导航

- [文档索引](./docs/README.md)
- [API 文档](./docs/api/api_document.md)
- [架构说明](./docs/architecture/system_architecture.md)
- [产品需求](./docs/PRD.md)
