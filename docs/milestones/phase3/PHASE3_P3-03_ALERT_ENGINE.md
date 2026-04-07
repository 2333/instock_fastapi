# Phase 3 任务设计：P3-03 预警规则引擎 + 推送集成

## 目标
基于用户关注列表与自定义条件，主动推送风险预警与机会提醒。

## 设计原则
- **实时性**：价格/指标变动达到阈值时及时通知
- **可配置**：用户可自定义预警条件（价格、涨跌幅、RSI、形态等）
- **多渠道**：支持应用内通知、邮件（后续扩展）
- **防骚扰**：去重与冷却机制，避免重复推送

## 数据源

### 已有数据
- **关注列表**（Attention）：用户主动关注的股票
- **用户行为**（P3-01）：筛选执行、回测、形态查看历史
- **市场数据**：实时行情、技术指标（已接入）

### 预警条件类型
| 类型 | 字段 | 示例 |
|------|------|------|
| 价格提醒 | price_above / price_below | 股价 > 30.0 或 < 25.0 |
| 涨跌幅提醒 | change_above / change_below | 日涨跌幅 > 5% 或 < -3% |
| RSI 超买超卖 | rsi_above / rsi_below | RSI > 70（超买）或 < 30（超卖） |
| 形态出现 | pattern_detected | 出现锤子线/吞没等形态 |
| 资金流向 | fund_net_inflow | 主力净流入 > X 万元 |

## 预警规则模型

### 数据库表（alert_conditions）
```python
class AlertCondition(Base):
    __tablename__ = "alert_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # 股票代码
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)  # price/change/rsi/pattern/fund
    operator: Mapped[str] = mapped_column(String(10), nullable=False)  # gt/lt/ge/le
    threshold: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    pattern_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 形态专用
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_channels: Mapped[list[str]] = mapped_column(JSONB, default=["in_app"])  # in_app/email
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### 预警检查任务（定时）
```python
# app/jobs/tasks/alert_checker.py
async def check_alerts():
    """定时检查所有活跃预警条件（每 5 分钟）"""
    # 1. 查询所有活跃预警
    # 2. 批量获取关注股票最新行情/指标
    # 3. 逐条判断是否触发
    # 4. 触发则创建通知记录 + 更新 last_triggered_at
    # 5. 推送至用户（应用内 / 邮件）
```

## 推送机制

### 应用内通知
```python
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # alert/backtest_done/pattern_detected
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {code: "000001", condition: "price_above"}
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
```

### API 端点
```python
# app/api/routers/alert_router.py
@router.get("/alerts/conditions")      # 列出我的预警条件
@router.post("/alerts/conditions")     # 创建预警条件
@router.put("/alerts/conditions/{id}") # 修改预警条件
@router.delete("/alerts/conditions/{id}")  # 删除预警条件
@router.get("/notifications")          # 获取通知列表
@router.patch("/notifications/{id}/read")  # 标记已读
```

## 前端集成

### 关注列表快速设置
在 Attention 页面，每只股票旁添加"设置预警"按钮，快速创建价格/形态预警。

### 预警管理页面
新建 `/alerts` 页面：
- 列出所有预警条件（启用/禁用开关）
- 创建/编辑表单（类型 + 条件 + 通知渠道）
- 历史触发记录

### 通知铃铛
在顶部导航栏添加通知图标，显示未读数量，下拉列表展示最近通知。

## 冷启动策略
- 默认为关注股票启用"价格突破/跌破最近 5 日高低点"预警（智能默认）
- 新用户关注股票后自动建议 3 条常用预警

## 验收标准
- [ ] 预警条件 CRUD 接口完成
- [ ] 定时检查任务每 5 分钟运行（开发环境可手动触发）
- [ ] 应用内通知可创建、可读、可标记已读
- [ ] 关注列表快速设置入口就绪
- [ ] 通知铃铛组件就绪（未读数 + 下拉列表）
- [ ] 冷启动默认预警自动创建

## 风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| 推送太频繁 | 骚扰用户 | 冷却机制（同条件 1 小时内不重复推送） |
| 性能开销 | 大量用户检查慢 | 批量查询 + 条件索引 + 异步任务 |
| 误触发 | 用户失去信任 | 价格阈值设置缓冲（如突破 5 日均线而非实时） |
| 邮件 deliverability | 进入垃圾箱 | 使用专业邮件服务（SendGrid/Mailgun） |

## 依赖项
- P3-01 用户行为数据（可选，用于推荐预警模板）
- 消息队列（可选，Celery/Redis Queue，用于异步检查）
- 邮件服务（可选，SendGrid/Mailgun）

## 估算
- 后端：6 小时（模型 + 任务 + API）
- 前端：5 小时（Alert 页面 + 快速设置 + 通知铃铛）
- 总计：**2.75 人日 ≈ 3 人日**

---

**状态**: 草案待评审
**创建时间**: 2026-04-03
**负责人**: TBD
