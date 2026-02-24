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
make status
```

访问: http://localhost:3000

### 方式二：本地开发

```bash
# 1. 安装依赖
make setup

# 2. 启动后端开发服务器
make dev

# 3. 另开终端，启动前端
make frontend-dev
```

访问: http://localhost:3000 (前端) | http://localhost:8000 (后端)

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
make install          # 生产依赖
make install-dev     # 开发依赖

# 启动服务
make dev             # 后端开发服务器
make frontend-dev    # 前端开发服务器

# 代码质量
make lint            # 检查代码
make format          # 格式化代码
make test            # 运行测试

# Docker
make docker-up       # 启动 Docker
make docker-down     # 停止 Docker
make docker-rebuild  # 重构并重启

# 数据库
make init-db         # 初始化数据库
```

### 添加新依赖

```bash
# 安装新包
pip install <package-name>

# 更新 requirements.txt
pip freeze > requirements.txt
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
```

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
