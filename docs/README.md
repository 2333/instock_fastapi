# InStock 智能股票分析平台 - 文档中心

## 文档目录

```
docs/
├── README.md                           # 本文件（文档索引）
├── PRD.md                              # 产品需求文档
├── architecture/
│   └── system_architecture.md          # 系统架构文档
├── design/
│   └── class_diagram.md                # 类图设计文档
└── api/
    ├── api_document.md                 # API接口文档
    └── integration_report.md           # 前后端对接检查报告
```

## 快速导航

### 1. 产品需求文档 (PRD)

**文件**: [PRD.md](./PRD.md)

**内容概要**:
- 产品概述与定位
- 用户角色与使用场景
- 功能需求列表
- 非功能需求
- 数据需求
- 验收标准
- 项目规划

**适合阅读者**: 产品经理、项目经理、开发团队

---

### 2. 系统架构文档

**文件**: [architecture/system_architecture.md](./architecture/system_architecture.md)

**内容概要**:
- 系统架构图
- 数据流架构
- 定时任务流程
- 技术栈说明
- 部署架构
- 模块依赖关系

**适合阅读者**: 架构师、后端开发、运维人员

---

### 3. 类图设计文档

**文件**: [design/class_diagram.md](./design/class_diagram.md)

**内容概要**:
- 数据模型类图
- 服务层类图
- 核心引擎类图
- 策略引擎类图
- 定时任务类图
- 前端组件类图

**适合阅读者**: 开发人员、技术负责人

---

### 4. API接口文档

**文件**: [api/api_document.md](./api/api_document.md)

**内容概要**:
- 股票接口
- ETF接口
- 技术指标接口
- K线形态接口
- 策略选股接口
- 回测接口
- 资金流向接口
- 关注列表接口
- 综合选股接口

**适合阅读者**: 前端开发、接口调用方

---

## 项目概览

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | Python + FastAPI |
| 数据库 | PostgreSQL + TimescaleDB |
| 缓存 | Redis |
| 容器化 | Docker + Docker Compose |

### 核心功能

1. **数据采集**: 自动采集A股、ETF行情数据
2. **技术分析**: 32种技术指标、61种K线形态
3. **策略选股**: 10种选股策略
4. **回测验证**: 策略历史回测与绩效分析

### 项目结构

```
instock_fastapi/
├── app/                    # 后端应用
│   ├── api/               # API路由
│   ├── models/            # 数据模型
│   ├── schemas/           # Pydantic模式
│   ├── services/          # 业务服务
│   └── jobs/              # 定时任务
├── core/                   # 核心引擎
│   ├── crawling/          # 数据爬虫
│   ├── indicator/         # 指标计算
│   ├── pattern/           # 形态识别
│   ├── strategy/          # 策略引擎
│   └── kline/             # K线处理
├── web/                    # 前端应用
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   ├── api/           # API客户端
│   │   └── components/    # 公共组件
│   └── dist/              # 构建产物
├── scripts/                # 脚本文件
├── docs/                   # 文档
├── docker-compose.yml      # Docker编排
└── Dockerfile              # 容器构建
```

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ 内存
- 20GB+ 磁盘空间

### 启动命令

```bash
# 克隆项目
git clone <repository_url>
cd instock_fastapi

# 启动服务
docker-compose up -d

# 访问地址
# 前端: http://localhost:3001
# 后端: http://localhost:8000
# API文档: http://localhost:8000/docs
```

## 维护说明

### 定时任务

| 任务 | 执行时间 | 说明 |
|------|---------|------|
| 数据抓取 | 15:30 | 股票、ETF、K线数据 |
| 资金流向 | 16:00 | 个股、板块资金流 |
| 指标计算 | 17:00 | 技术指标计算 |
| 形态识别 | 17:30 | K线形态识别 |
| 策略选股 | 18:00 | 策略选股执行 |
| 数据清理 | 周日03:00 | 清理过期数据 |

### 数据保留策略

| 数据类型 | 保留期限 |
|---------|---------|
| K线数据 | 2年 |
| 技术指标 | 1年 |
| K线形态 | 6个月 |
| 资金流向 | 1年 |

## 联系方式

- 项目地址: [GitHub Repository]
- 问题反馈: [GitHub Issues]
