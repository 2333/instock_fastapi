# InStock 文档中心

这里汇总项目的产品、架构和接口文档，便于按角色快速查阅。

## 文档清单

- [PRD.md](./PRD.md)：v2.0 产品需求文档，定义产品定位、目标用户、核心循环、功能边界和长期目标。（v1 归档：[PRD_v1_archive.md](./PRD_v1_archive.md)）
- [ROADMAP.md](./ROADMAP.md)：v2.0 产品路线图，将 Phase 0 拆分为 0a/0b，包含代码资产盘点和阶段验收标准。（v1 归档：[ROADMAP_v1_archive.md](./ROADMAP_v1_archive.md)）
- [EXECUTION_PLAN.md](./EXECUTION_PLAN.md)：Phase 0 / Phase 1 的可执行任务拆解，面向实际开发落地。
- [architecture/system_architecture.md](./architecture/system_architecture.md)：后端、任务调度、数据流和部署架构。
- [design/class_diagram.md](./design/class_diagram.md)：核心数据模型和模块关系说明。
- [api/api_document.md](./api/api_document.md)：当前 API 说明与调用示例。
- [api/integration_report.md](./api/integration_report.md)：前后端联调与检查记录。

## 代码结构对应关系

- `app/`：FastAPI 后端入口、路由、服务层和数据库层。
- `core/`：数据采集、技术指标、形态识别、策略和回测实现。
- `web/`：Vue 前端工程，以及后端根路径使用的静态首页资源。
- `scripts/`：环境初始化、数据库准备和辅助脚本。

## 阅读建议

- 产品和需求相关内容优先看 `PRD.md`。
- 想了解后端如何启动、如何挂载静态资源，优先看 `app/main.py` 和系统架构文档。
- 需要对接接口时，优先看 API 文档，再对照代码实现。
