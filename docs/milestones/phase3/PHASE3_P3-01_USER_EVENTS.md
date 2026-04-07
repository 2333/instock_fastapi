# Phase 3 任务设计：P3-01 用户行为埋点与收集

## 目标
建立用户行为数据收集基础框架，为智能推荐提供数据支撑。

## 设计原则
- **最小侵入**：不阻塞现有业务流程
- **异步记录**：行为日志异步写入，不影响响应速度
- **隐私安全**：不记录敏感信息（密码、个人身份）
- **可扩展**：事件结构支持灵活扩展

## 数据模型

### 用户行为事件表（user_events）
```python
class UserEvent(Base):
    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # page_view, click, filter_run, backtest_run, pattern_view...
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # 事件详情
    page: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 页面路径
    referrer: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 来源页面
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # IP 匿名化哈希
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_user_events_user_created", "user_id", "created_at"),
    )
```

## 事件类型定义

### 页面浏览（page_view）
```json
{
  "event_type": "page_view",
  "page": "/dashboard",
  "referrer": "/login",
  "duration_ms": 3500
}
```

### 筛选执行（filter_run）
```json
{
  "event_type": "filter_run",
  "page": "/selection",
  "criteria": {
    "priceMin": 0,
    "priceMax": 200,
    "changeMin": -10,
    "changeMax": 10,
    "macdBullish": true
  },
  "result_count": 152,
  "duration_ms": 4200
}
```

### 回测执行（backtest_run）
```json
{
  "event_type": "backtest_run",
  "page": "/backtest",
  "strategy": "ma_crossover",
  "params": {"short": 5, "long": 20},
  "stock_code": "000001.SZ",
  "period_days": 90,
  "async": true
}
```

### 形态查看（pattern_view）
```json
{
  "event_type": "pattern_view",
  "page": "/stock/000001",
  "pattern_name": "锤子线",
  "pattern_key": "hammer",
  "confidence": 85,
  "trade_date": "20260402"
}
```

### 关注操作（attention_action）
```json
{
  "event_type": "attention_action",
  "page": "/dashboard",
  "action": "add",  // add / remove
  "code": "000001",
  "source": "stock_detail"  // stock_detail / selection_result
}
```

## 实现方案

### 1. 后端：事件记录 API
- 端点：`POST /api/v1/events/track`
- 认证：可选（登录用户记录 user_id，未登录记录 session_id）
- 速率限制：100 次/分钟/用户（防刷）
- 实现：FastAPI 端点 + 异步写入 PostgreSQL

### 2. 前端：事件捕获混入（Composable）
```typescript
// composables/useAnalytics.ts
export const useAnalytics = () => {
  const track = (event: string, properties: Record<string, any>) => {
    // 发送到 /api/v1/events/track（不阻塞）
    fetch('/api/v1/events/track', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ event_type: event, ...properties })
    }).catch(() => {})
  }

  return { track }
}
```

### 3. 集成点
- Dashboard 卡片点击：`track('dashboard_card_click', { card: 'market' })`
- 筛选执行成功后：`track('filter_run', { result_count: data.total })`
- 回测发起时：`track('backtest_run', { strategy: config.strategyType })`
- 形态点击：`track('pattern_view', { pattern_name: ..., confidence: ... })`
- 关注按钮：`track('attention_action', { action: 'add', code: ... })`

## 验收标准
- [ ] 用户事件表迁移已执行
- [ ] `POST /api/v1/events/track` 端点可用（认证 + 限流）
- [ ] 前端混入已集成到 5 个核心页面（Dashboard/Selection/Backtest/StockDetail/Attention）
- [ ] 至少 10 种事件类型可收集
- [ ] 事件数据可通过 Admin 或 SQL 查询验证
- [ ] 不影响主流程性能（异步写入，P99 < 5ms）

## 风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| 事件量过大 | DB 膨胀 | 按周分区 + 60 天自动归档 |
| 写入阻塞 | 主流程延迟 | 异步写入，异常降级（失败不抛） |
| 隐私泄露 | 合规风险 | 不记录 IP 原文（hash）、不记录 password 字段 |
| 前端侵入 | 代码复杂度 | 封装为 composable，集中管理 |

## 依赖项
- 无（独立新增）

## 估算
- 后端：2 小时（模型 + 迁移 + 端点 + 限流）
- 前端：3 小时（混入 + 5 页面集成 + 测试）
- 总计：**1 人日**

---

**状态**: 草案待评审
**创建时间**: 2026-04-03
**负责人**: TBD
