# Task: WS3-05 监控仪表板（Dashboard）

**Owner**: Agent F (Quality & Observability)
**Workstream**: WS-3 质量保障
**Priority**: P2 (可视化)
**Estimated Effort**: 0.5 天
**Dependencies**: WS3-03 (监测增强)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现监控数据可视化仪表板，展示稳定性指标、质量检查结果、告警历史与数据血缘拓扑。

---

## 背景

Dashboard 提供:
- 一目了然的系统健康状态
- 历史趋势分析
- 快速定位问题（哪个表/任务失败）
- 管理层汇报视图

技术选型:
- 后端: FastAPI + SQLAlchemy（提供 JSON API）
- 前端: 简单 HTML+JS（或集成 Grafana）
- 存储: 使用现有 PostgreSQL + 稳定性日志

---

## 具体步骤

### 1. 后端 API (`app/api/v1/monitoring.py`)

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.db.session import get_session
from app.models.stability_log import StabilityLog

router = APIRouter()

@router.get("/health")
async def get_health_summary():
    """获取当前健康状态摘要"""
    async with get_session() as session:
        # 最近一次检查
        latest = await session.execute(
            select(StabilityLog).order_by(StabilityLog.timestamp.desc()).limit(1)
        )
        last_check = latest.scalar_one_or_none()

        if not last_check:
            return {"status": "unknown", "message": "无检查记录"}

        return {
            "status": last_check.overall_status,
            "timestamp": last_check.timestamp.isoformat(),
            "components": {
                "quick_suite": last_check.quick_suite,
                "db_connections": last_check.db_connections,
                "disk_space": last_check.disk_space,
                "timescale": last_check.timescale_health,
            }
        }

@router.get("/trend")
async def get_trend(days: int = 7):
    """获取历史趋势（通过率变化）"""
    async with get_session() as session:
        cutoff = datetime.now() - timedelta(days=days)
        records = await session.execute(
            select(StabilityLog)
            .where(StabilityLog.timestamp >= cutoff)
            .order_by(StabilityLog.timestamp)
        )
        logs = records.scalars().all()

        trend = []
        for log in logs:
            trend.append({
                "timestamp": log.timestamp.isoformat(),
                "pass_rate": log.pass_rate,
                "status": log.overall_status
            })

        return {"trend": trend}

@router.get("/alerts")
async def get_alerts(limit: int = 50):
    """获取最近告警列表"""
    alerts = []
    alert_log = Path("logs/alerts.log")
    if alert_log.exists():
        with open(alert_log) as f:
            lines = f.readlines()[-limit:]
            for line in lines:
                alerts.append(json.loads(line))
    return {"alerts": list(reversed(alerts))}
```

### 2. 简单前端 (`static/dashboard.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <title>InStock 监控仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>InStock 监控仪表板</h1>

    <div id="health-status">
        <h2>当前状态: <span id="status">加载中...</span></h2>
        <p>最后检查: <span id="last-check"></span></p>
    </div>

    <div>
        <h2>健康指标</h2>
        <ul>
            <li>Quick Suite: <span id="quick-suite"></span></li>
            <li>数据库连接: <span id="db-conn"></span></li>
            <li>磁盘空间: <span id="disk"></span></li>
            <li>TimescaleDB: <span id="timescale"></span></li>
        </ul>
    </div>

    <div>
        <h2>通过率趋势（近 7 天）</h2>
        <canvas id="trend-chart"></canvas>
    </div>

    <div>
        <h2>最近告警</h2>
        <ul id="alerts-list"></ul>
    </div>

    <script>
        async function loadDashboard() {
            // 获取健康状态
            const health = await fetch('/api/v1/monitoring/health').then(r => r.json());
            document.getElementById('status').textContent = health.status;
            document.getElementById('last-check').textContent = health.timestamp;

            // 获取趋势
            const trend = await fetch('/api/v1/monitoring/trend?days=7').then(r => r.json());
            renderChart(trend.trend);

            // 获取告警
            const alerts = await fetch('/api/v1/monitoring/alerts?limit=10').then(r => r.json());
            renderAlerts(alerts.alerts);
        }

        function renderChart(trendData) {
            const ctx = document.getElementById('trend-chart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: trendData.map(d => d.timestamp.slice(5, 10)), // MM-DD
                    datasets: [{
                        label: '通过率 %',
                        data: trendData.map(d => d.pass_rate),
                        borderColor: 'green',
                        fill: false
                    }]
                }
            });
        }

        loadDashboard();
    </script>
</body>
</html>
```

### 3. 集成到 FastAPI

`app/main.py`:

```python
from fastapi import FastAPI
from app.api.v1 import monitoring

app = FastAPI()
app.include_router(monitoring.router, prefix="/api/v1/monitoring")
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### 4. 稳定性日志表

创建 `StabilityLog` Model:

```python
class StabilityLog(Base):
    __tablename__ = "stability_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    quick_suite = Column(String(10))  # PASS/FAIL
    pass_rate = Column(Float)
    overall_status = Column(String(10))  # PASS/FAIL
    details = Column(JSON)  # 完整检查结果
```

修改 `scripts/monitor_stability.py` 写入数据库而非仅 JSONL。

---

## 验收标准

- [ ] `/api/v1/monitoring/health` 返回当前状态
- [ ] `/api/v1/monitoring/trend` 返回历史趋势数据
- [ ] `/api/v1/monitoring/alerts` 返回告警列表
- [ ] `static/dashboard.html` 可访问并显示图表
- [ ] `StabilityLog` 表持续记录检查结果
- [ ] 测试通过

---

## 交付物

- [ ] `app/models/stability_log.py`
- [ ] `app/api/v1/monitoring.py`
- [ ] `static/dashboard.html`
- [ ] `scripts/monitor_stability.py` 更新（写入 DB）
- [ ] Alembic 迁移（`stability_log` 表）
- [ ] `tests/test_monitoring_api.py`

---

**Trigger**: WS3-03 完成后
**Estimated Time**: 0.5 天
