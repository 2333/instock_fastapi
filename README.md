# InStock FastAPI - 智能股票分析平台

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-black?style=for-the-badge&logo=fastapi)
![Vue.js](https://img.shields.io/badge/Vue.js-3.4-4FC08D?style=for-the-badge&logo=vue.js)
![TA-Lib](https://img.shields.io/badge/TA--Lib-0.6.0-green?style=for-the-badge)

**智能股票分析平台** - 数据采集、技术分析、形态识别、策略回测

</div>

---

## 📋 目录

- [快速开始](#快速开始)
- [项目架构](#项目架构)
- [开发指南](#开发指南)
- [部署指南](#部署指南)
- [版本发布](#版本发布)
- [API文档](#api文档)
- [技术栈](#技术栈)

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd instock_fastapi

# 2. 启动所有服务
make docker-up

# 3. 验证服务
make docker-status
make docker-smoke
```

访问: http://localhost:3001

### 方式二：本地开发

```bash
# 1. 安装 uv 并同步后端依赖
uv sync --dev

# 2. 启动后端开发服务器
make dev

# 3. 另开终端，启动前端
make frontend-dev
```

访问: http://localhost:3000 (前端开发服务器) | http://localhost:8000 (后端)

---

## 🏗️ 项目架构

```
instock_fastapi/
├── app/                          # FastAPI 后端
│   ├── main.py                   # 应用入口
│   ├── api/                      # API 路由
│   │   └── routers/              # 路由模块
│   ├── services/                 # 业务逻辑
│   ├── models/                  # SQLAlchemy 模型
│   ├── schemas/                  # Pydantic 模式
│   ├── database.py               # 数据库连接
│   └── config.py                 # 配置管理
│
├── core/                         # 核心分析模块
│   ├── crawling/                 # 数据采集
│   │   ├── base.py              # 采集基类
│   │   └── eastmoney.py         # 东方财富数据
│   ├── storage/                  # 数据存储
│   │   ├── timescaledb.py       # TimescaleDB 操作
│   │   └── redis.py             # Redis 缓存
│   ├── kline/                    # K线处理
│   │   └── processor.py         # K线分析
│   ├── indicator/                # 技术指标
│   │   └── calculator.py        # TA-Lib 封装
│   ├── pattern/                  # 形态识别
│   │   └── recognizer.py       # TA-Lib 形态
│   └── strategy/                 # 策略回测
│       └── engine.py            # 回测引擎
│
├── web/                          # Vue 3 前端
│   ├── src/
│   │   ├── views/               # 页面视图
│   │   ├── components/          # 组件
│   │   ├── stores/              # Pinia 状态
│   │   ├── api/                 # API 调用
│   │   └── router/              # 路由配置
│   ├── package.json
│   └── Dockerfile
│
├── scripts/                       # 脚本
│   ├── start.sh                 # 启动脚本
│   └── init_timescaledb.py      # 数据库初始化
│
├── docker-compose.yml            # Docker 编排
├── Dockerfile                    # 后端镜像
├── Makefile                      # 开发命令
└── requirements.txt              # Python 依赖
```

---

## 💻 开发指南

### 可用命令

```bash
# 安装依赖
make install         # 同步生产依赖
make install-dev     # 同步开发依赖
make sync            # 更新本地 uv 环境

# 启动服务
make dev             # 后端开发服务器
make frontend-dev    # 前端开发服务器

# 代码质量
make lint            # 检查代码
make style-check     # 检查增量严格规范
make style-fix       # 修复增量严格规范
make format          # 格式化代码
make test            # 运行测试

# Docker
make docker-up       # 启动 Docker
make docker-down     # 停止 Docker
make docker-rebuild  # 重构并重启
make docker-smoke    # 验证容器服务是否可用
make docker-build-version VERSION=0.2.0
make docker-deploy-version VERSION=0.2.0

# 数据库
make init-db         # 初始化数据库
```

### 版本管理

仓库现在使用根目录 [VERSION](/Users/zhangkai/projects/instock_fastapi/VERSION) 作为单一版本源，遵循语义化版本：

```bash
# 查看当前版本
make version-show

# 检查 VERSION / pyproject.toml / web/package.json / web/package-lock.json 是否一致
make version-check

# 发布前设置新版本
make version-set VERSION=0.2.0
```

运行时版本会暴露在：

- `GET /health`
- `GET /api/v1/info`
- 前端顶部版本徽标

镜像构建会自动注入：

- `APP_VERSION`
- `APP_GIT_SHA`
- OCI image labels

### 添加新依赖

```bash
# 生产依赖
uv add <package-name>

# 开发依赖
uv add --dev <package-name>

# 更新锁文件
uv lock
```

---

## 🚢 部署指南

### 生产环境 Docker

```bash
# 构建并启动
make docker-build
make docker-up

# 检查状态
make docker-status
make docker-smoke
```

## 版本发布

### 1. 同步版本号

```bash
make version-set VERSION=0.2.0
make version-check
```

### 2. 生成版本化镜像

```bash
make docker-build-version VERSION=0.2.0
```

默认镜像标签：

- `instock/instock-app:0.2.0`
- `instock/instock-frontend:0.2.0`

可通过 `IMAGE_NAMESPACE` 覆盖命名空间：

```bash
IMAGE_NAMESPACE=ghcr.io/2333 make docker-build-version VERSION=0.2.0
```

### 3. 使用版本化镜像部署

```bash
make docker-deploy-version VERSION=0.2.0
```

部署编排文件为 [docker-compose.deploy.yml](/Users/zhangkai/projects/instock_fastapi/docker-compose.deploy.yml)，它只消费镜像，不再挂载源码目录，更适合发布环境。

### 环境变量

```bash
# 复制并编辑
cp .env.example .env

# 主要配置
POSTGRES_PASSWORD=your_password
POSTGRES_USER=instock
DATABASE_URL=postgresql://...
REDIS_HOST=redis
```

---

## 📚 API 文档

启动后访问: http://localhost:8000/docs

## CI

GitHub Actions 已提供第一版 CI，覆盖:

- 后端 `uv sync --dev`
- 后端 `pytest` 与覆盖率产物
- 后端关键级别 `ruff` 检查
- 后端增量 `black --check` + 全量 `ruff` 样式门禁
- 前端 `npm ci`
- 前端 `vue-tsc --noEmit`
- 前端生产构建
- 后端与前端 Docker 镜像构建校验
- Docker Compose 启动与容器级 smoke test
- 后端覆盖率下限校验（当前为 `30%`）

本地可用对应预检命令:

- `make ci-backend`
- `make ci-frontend`
- `make ci`
- `make style-check`

## 运行矩阵

### `dev`

- 后端: `uv sync --dev && make dev`
- 前端: `cd web && npm ci && make frontend-dev`
- 适用: 本地开发、调试、快速改动验证

### `test`

- 后端: `make ci-backend`
- 前端: `make ci-frontend`
- 容器级验活: `ENV_FILE=config/docker-ci.env docker compose up -d --build && make docker-smoke`
- 适用: 提交前预检、CI 对齐

### `prod-like`

- 配置: 复制 `.env.example` 为 `.env` 并填写真实配置
- 启动: `make docker-up`
- 验活: `make docker-status && make docker-smoke`
- 适用: 近似部署环境的本机验证

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/stocks` | GET | 股票列表 |
| `/api/v1/stocks/{code}` | GET | 股票详情 |
| `/api/v1/patterns` | GET | 形态识别 |
| `/api/v1/backtest` | POST | 策略回测 |
| `/api/v1/selection` | POST | 股票筛选 |

---

## 🛠️ 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **FastAPI** | Web 框架 |
| **SQLAlchemy** | ORM |
| **TimescaleDB** | 时序数据库 |
| **Redis** | 缓存 |
| **TA-Lib** | 技术分析 |
| **httpx** | HTTP 客户端 |
| **Loguru** | 日志 |

### 前端

| 技术 | 用途 |
|------|------|
| **Vue 3** | UI 框架 |
| **TypeScript** | 类型安全 |
| **Vite** | 构建工具 |
| **Tailwind CSS** | 样式 |
| **ECharts** | 图表 |
| **Pinia** | 状态管理 |
| **Vue Router** | 路由 |

### 基础设施

| 技术 | 用途 |
|------|------|
| **Docker** | 容器化 |
| **Docker Compose** | 编排 |
| **Nginx** | 反向代理 |

---

## 📝 许可证

MIT License

---

## 🤝 贡献

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request
