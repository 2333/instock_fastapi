# Phase 3 任务设计：P3-06 数据洞察报告生成（定时任务 + 推送）

## 目标
自动生成个性化市场与操作报告，提升用户粘性与决策效率。

## 设计原则
- **个性化**：基于用户关注列表与操作历史
- **定时推送**：每日/每周/每月固定时间发送
- **可读性强**：自然语言总结 + 可视化图表
- **多通道**：应用内通知 + 邮件（后续扩展微信/钉钉）

## 报告类型

### 1. 每日市场晨报（08:30 发送）
**内容**：
- 前一交易日市场概览（上证/深证/创业板涨跌幅）
- 涨跌分布直方图
- 北向资金净流入
- 我的关注列表表现（vs 大盘）
- 重要新闻摘要（可选，依赖外部 API）

**触发**：每日交易日 08:30

### 2. 每周操作回顾（周一 09:00 发送）
**内容**：
- 上周筛选命中股票表现 Top 5
- 回测执行次数与平均收益
- 新增关注/取消关注统计
- 形态查看偏好总结（最常看的形态类型）
- 操作建议（基于上周行为）

**触发**：每周一 09:00

### 3. 月度策略总结（每月 1 日 10:00 发送）
**内容**：
- 本月个人回测汇总（总次数/平均收益/最佳策略）
- 关注组合月度收益（等权加权）
- 与沪深 300 对比
- 行为洞察（"本月你更偏好 RSI 策略"）
- 下月建议（推荐关注板块/形态）

**触发**：每月 1 日 10:00

### 4. 自定义报告（On-Demand）
**入口**：Dashboard"生成报告"按钮
**选项**：时间范围 / 报告类型 / 包含模块

## 数据源

### 内部数据
- `user_events`：用户页面访问、筛选、回测、形态查看、关注操作
- `attention`：关注列表
- `backtest_results`：回测历史
- `selection_results`：筛选历史
- `pattern_records`：形态记录

### 外部数据（可选）
- 财经新闻摘要（如东方财富/财联社快讯）
- 机构评级变化
- 龙虎榜数据

## 报告生成架构

### 后端服务
```python
# app/services/report_generator.py
class ReportGenerator:
    async def generate_daily_market_report(self, user_id: int, date: date) -> dict:
        """生成每日市场晨报"""
        return {
            "title": f"{date} 市场晨报",
            "sections": [
                {"type": "market_summary", "data": ...},
                {"type": "attention_performance", "data": ...},
                {"type": "news_highlight", "data": ...},
            ],
            "created_at": datetime.utcnow(),
        }

    async def generate_weekly_review(self, user_id: int, week_start: date) -> dict:
        """生成每周操作回顾"""

    async def generate_monthly_summary(self, user_id: int, month: date) -> dict:
        """生成月度策略总结"""

    async def render_html(self, report: dict) -> str:
        """渲染 HTML 邮件正文"""
```

### 任务调度
```python
# app/jobs/tasks/reports.py
@celery.task
def send_daily_reports():
    """每日 08:30 触发，批量发送所有活跃用户晨报"""
    users = get_all_active_users()
    for user in users:
        generate_and_send_report.delay(user.id, "daily", date.today())

@celery.task
def send_weekly_reviews():
    """每周一 09:00 触发"""

@celery.task
def send_monthly_summaries():
    """每月 1 日 10:00 触发"""
```

### 报告存储
```python
class UserReport(Base):
    __tablename__ = "user_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # daily/weekly/monthly/custom
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_via: Mapped[list[str]] = mapped_column(JSONB, default=["in_app"])  # in_app/email
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

## 推送机制

### 应用内通知
```python
# 创建通知记录
notification = Notification(
    user_id=user_id,
    type="report_available",
    title=f"您的{report_type}报告已生成",
    message=f"点击查看 {report_date} 的{report_type}报告",
    payload={"report_id": report.id, "report_type": report_type},
)
```

### 邮件推送（可选）
使用模板引擎（Jinja2）渲染 HTML 邮件：
- 响应式布局（移动端友好）
- 内联 CSS（邮件客户端兼容）
- 关键数据高亮

### 用户偏好设置
```python
class ReportPreference(Base):
    __tablename__ = "report_preferences"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    daily_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    monthly_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_time: Mapped[time] = mapped_column(Time, default=time(8, 30))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")
```

## 前端集成

### Dashboard 报告卡片
```
┌─────────────────────────────────┐
│ 📊 我的报告                     │
│                                 │
│  最近报告：                     │
│  ✓ 04月02日 每日晨报 已读       │
│  ✓ 03月31日 每周回顾 已读       │
│  ● 04月03日 每日晨报 新         │
│                                 │
│ [生成自定义报告]                │
└─────────────────────────────────┘
```

### 报告详情页
`/reports/:id` 路由展示完整 HTML 报告，支持打印/分享。

### 偏好设置页
`/settings/reports`：
- 开关：每日/每周/月度报告
- 推送渠道：应用内 / 邮件
- 发送时间调整

## 报告模板示例（HTML）

```html
<!-- 每日晨报 -->
<div class="report-header">
  <h1>📈 2026-04-03 市场晨报</h1>
  <p>早上好，张凯。以下是今日市场简报：</p>
</div>

<div class="section market-summary">
  <h2>市场概览</h2>
  <div class="indices">
    <span class="index up">上证 +1.23%</span>
    <span class="index up">深证 +0.87%</span>
    <span class="index down">创业板 -0.32%</span>
  </div>
</div>

<div class="section attention-performance">
  <h2>我的关注表现</h2>
  <table>
    <tr><td>贵州茅台</td><td class="up">+2.1%</td></tr>
    <tr><td>平安银行</td><td class="down">-0.5%</td></tr>
  </table>
</div>

<div class="section insights">
  <h2>💡 操作建议</h2>
  <p>你近期频繁查看 RSI 超卖形态，建议关注估值较低的大盘股。</p>
</div>
```

## 冷启动策略
- 新用户注册后第 3 天开始发送每日报告（已积累行为数据）
- 首月报告增加"新手指南"板块
- 提供"暂停一周"选项

## 验收标准
- [ ] 三种定时报告生成逻辑完成
- [ ] 报告存储与历史查询
- [ ] 应用内通知推送
- [ ] Dashboard 报告卡片组件
- [ ] 报告详情页（HTML 渲染）
- [ ] 用户偏好设置（开关 + 时间 + 渠道）
- [ ] 邮件模板（可选）
- [ ] 自定义报告生成（按日期/类型选择）

## 风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| 报告无价值 | 用户关闭 | 持续迭代内容，基于行为数据个性化 |
| 推送太频繁 | 打扰用户 | 严格按偏好设置，提供暂停功能 |
| 生成性能 | 大批量用户延迟 | 分批处理 + 异步任务 + 缓存 |
| 邮件进垃圾箱 | 送达率低 | 专业邮件服务 + SPF/DKIM 配置 |

## 依赖项
- 任务队列（Celery/Redis Queue，已存在）
- 邮件服务（SendGrid/Mailgun，可选）
- 前端 Markdown/HTML 渲染器

## 估算
- 后端：8 小时（报告生成逻辑 + 任务调度 + API）
- 前端：5 小时（Dashboard 卡片 + 详情页 + 偏好设置）
- 总计：**3.25 人日 ≈ 3.5 人日**

---

**状态**: 草案待评审
**创建时间**: 2026-04-03
**负责人**: TBD
