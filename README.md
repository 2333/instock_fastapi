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

### 环境模型

```bash
make dev-up
make prod-status
```

- `dev`：长期保留的开发联调环境
- `prod`：长期保留的生产环境
- `staging`：默认关闭，只在高风险变更验证时临时拉起

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

# 环境管理
make dev-up
make dev-down
make dev-status
make dev-smoke
make prod-status
make prod-smoke
make staging-up
make staging-down

# 数据库
make init-db
```

## 版本管理

仓库使用根目录 [`VERSION`](./VERSION) 作为单一版本源，遵循语义化版本。

```bash
make version-show
make version-check
make version-set VERSION=0.2.0
make version-bump-patch
make version-bump-minor
```

版本文件会同步写入：

- `VERSION`
- `pyproject.toml`
- `web/package.json`
- `web/package-lock.json`

### 合并后的版本约定

- 功能分支开发过程中不要求频繁 bump 版本；以合并回主线时 bump 一次为准。
- 每次合并到主线后，默认至少执行一次 `patch` bump。
- 合并的是向后兼容的新功能、明显的用户可见能力扩展时，执行 `minor` bump。
- 合并的是破坏性 API、配置、数据结构调整时，执行 `major` bump。
- 只有纯文档、注释、CI 文案等完全不影响运行产物的合并，可以不 bump；如果拿不准，优先 bump `patch`。

对这个项目，建议把规则简化成一句话：

- `bugfix / 重构 / 小优化 / 数据抓取修复` -> `make version-bump-patch`
- `新增页面 / 新接口 / 新任务能力 / 新策略能力` -> `make version-bump-minor`
- `破坏兼容` -> `make version-bump-major`

发布环境可使用版本化镜像：

```bash
make prod-build-version VERSION=0.2.0
make prod-deploy-version VERSION=0.2.0
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
- 开发前端容器：`http://localhost:3002/`
- 生产前端入口：`http://localhost:3001/`

## 关键说明

- 后端入口位于 [`app/main.py`](./app/main.py)，会挂载 `web/static` 并渲染 `web/templates/index.html`。
- `web/` 目录下既有独立前端工程，也有后端静态首页资源，两者用途不同。
- 具体 API、架构和产品说明以 `docs/` 目录内文档为准。

## 文档导航

- [文档索引](./docs/README.md)
- [环境说明](./docs/deployment/compose_environments.md)
- [发布流程](./docs/deployment/release_workflow.md)
- [API 文档](./docs/api/api_document.md)
- [架构说明](./docs/architecture/system_architecture.md)
- [产品需求](./docs/PRD.md)
