# Phase 3 实施任务：P3-06 数据洞察报告 - 后端基础实现

## 任务目标
实现自动报告生成服务：三种报告类型 + 定时推送 + 应用内通知。

## 实施范围（本次）

### 1. 数据库模型（2 张表）
- `UserReport` - 报告记录（HTML 内容 + 推送状态）
- `ReportPreference` - 用户报告偏好（开关/时间/时区/渠道）

### 2. 报告生成服务
```python
class ReportGenerator:
    async def generate_daily_market_report(user_id, date) -> dict
    async def generate_weekly_review(user_id, week_start) -> dict
    async def generate_monthly_summary(user_id, month) -> dict
    async def render_html(report) -> str
```

### 3. 定时任务
使用 APScheduler 现有调度器，新增 3 个定时任务：
- 每日 08:30：发送市场晨报（交易日）
- 每周一 09:00：发送操作回顾
- 每月 1 日 10:00：发送月度总结

### 4. 推送服务
- 应用内通知（复用 Notification 模型）
- 邮件推送（预留接口，可选 SendGrid）

### 5. API 端点
```python
GET    /api/v1/reports                      # 我的报告列表
GET    /api/v1/reports/{report_id}          # 报告详情
POST   /api/v1/reports/generate             # 手动生成报告
GET    /api/v1/reports/preferences          # 获取偏好设置
PUT    /api/v1/reports/preferences          # 更新偏好设置
```

## 验收标准
- [ ] 2 张模型表可通过 `Base.metadata.create_all` 自动建表
- [ ] 三种报告生成逻辑完成（市场数据 + 用户关注 + 行为统计）
- [ ] 定时任务接入 APScheduler（交易日检查）
- [ ] 应用内通知推送就绪
- [ ] 报告列表/详情/偏好 API 可用
- [ ] 测试无回归

## 文件清单

### 新增
- `app/models/report_models.py` - UserReport + ReportPreference
- `app/schemas/report_schema.py` - 报告 Schemas
- `app/services/report_generator.py` - 报告生成服务
- `app/jobs/tasks/report_tasks.py` - 定时任务
- `app/api/routers/report_router.py` - 报告 API

### 修改
- `app/jobs/scheduler.py` - 注册 3 个报告定时任务
- `app/models/__init__.py` - 导出新模型
- `app/api/routers/__init__.py` - 注册报告路由

## 数据源
- 用户关注列表（Attention）
- 用户行为事件（UserEvent）
- 回测历史（BacktestResult）
- 筛选历史（SelectionResult）
- 市场指数（DailyBar 中的指数）

## 估算
- 模型 + Schema：1 小时
- 报告生成服务：3 小时（3 种报告逻辑）
- 定时任务 + API：2 小时
- 测试验证：1 小时
- **总计：7 小时 ≈ 0.9 人日**

---

**状态**: 待实施
**优先级**: P0（Phase 3 收尾任务，价值明确）
**依赖**: 无
