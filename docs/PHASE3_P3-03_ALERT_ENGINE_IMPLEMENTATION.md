# Phase 3 实施任务：P3-03 预警规则引擎 - 后端实现

## 任务目标
完成预警规则引擎的后端基础：模型 + API + 定时检查任务框架。

## 实施范围（本次）

### 1. 数据库模型
- `AlertCondition` - 预警条件定义
- `Notification` - 通知记录（已存在，复用）
- 索引设计：user_id + is_active + condition_type

### 2. API 端点（CRUD）
- `GET /api/v1/alerts/conditions` - 列出我的预警
- `POST /api/v1/alerts/conditions` - 创建预警
- `PUT /api/v1/alerts/conditions/{id}` - 更新预警
- `DELETE /api/v1/alerts/conditions/{id}` - 删除预警
- `GET /api/v1/notifications` - 通知列表
- `PATCH /api/v1/notifications/{id}/read` - 标记已读

### 3. 定时检查任务框架
- 基础任务结构（每 5 分钟触发）
- 查询活跃预警
- 批量获取行情数据（待实现）
- 条件判断逻辑框架
- 通知创建逻辑

### 4. 前端准备（后端只需提供接口）
- 待后续 heartbeat 实现

## 验收标准
- [ ] AlertCondition 模型可通过 `Base.metadata.create_all` 自动建表
- [ ] 5 个 CRUD 接口全部可用（含认证）
- [ ] 定时任务框架可运行（开发环境手动触发）
- [ ] 类型检查（vue-tsc 不涉及，后端 mypy/pyright 通过）
- [ ] 测试 128/128 无回归

## 技术决策

### 预警条件存储格式
```python
class AlertCondition(Base):
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # 示例：
    # { "type": "price", "operator": "gt", "value": 30.0 }
    # { "type": "rsi", "operator": "lt", "value": 30 }
    # { "type": "pattern", "pattern_name": "hammer" }
```
使用单一 JSONB 字段存储条件，灵活支持未来扩展。

### 定时任务执行器
使用 Celery Beat（已存在）或简单 asyncio 循环（开发环境）：
- 生产：Celery periodic task（5 分钟）
- 开发：提供 `/api/v1/alerts/check` 手动触发端点

### 通知去重与冷却
```python
# 同条件 1 小时内不重复推送
if last_triggered_at and (now - last_triggered_at) < timedelta(hours=1):
    skip
```

## 文件清单

### 新增
- `app/models/alert_condition_model.py` - 预警条件模型
- `app/models/notification_model.py` - 通知模型（如不存在）
- `app/api/routers/alert_router.py` - 预警 API
- `app/jobs/tasks/alert_checker.py` - 定时检查任务
- `app/services/alert_service.py` - 预警业务逻辑

### 修改
- `app/models/__init__.py` - 导出新模型
- `app/api/routers/__init__.py` - 注册新路由

## 估算
- 模型 + 迁移：1 小时
- API 端点：2 小时
- 定时任务框架：1 小时
- 测试验证：1 小时
- **总计：5 小时**

---

**状态**: 待实施
**优先级**: P0（Phase 3 首个实施任务）
**依赖**: 无
