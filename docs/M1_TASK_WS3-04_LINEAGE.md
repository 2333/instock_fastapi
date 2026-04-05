# Task: WS3-04 数据血缘与影响分析

**Owner**: Agent F (Quality & Observability)
**Workstream**: WS-3 质量保障
**Priority**: P2 (可观测性)
**Estimated Effort**: 0.5 天
**Dependencies**: WS3-01 (质量检查就绪)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现数据血缘追踪，记录表与字段级别的数据来源、转换逻辑与下游影响，支持问题排查与变更影响分析。

---

## 背景

数据血缘用于:
- 追踪数据从源头到 API 的完整链路
- 变更影响分析（改字段会影响哪些报表/接口）
- 故障定位（某表数据异常，追溯上游任务）

---

## 涉及表

| 表名 | 说明 |
|------|------|
| data_lineage | 血缘关系图谱（节点与边） |

---

## 血缘模型

### 节点类型
- **Source**: Tushare API 接口（如 `pro.daily`）
- **Table**: 数据库表（`daily_bars`）
- **Column**: 字段（`daily_bars.close`）
- **Task**: 抓取/计算任务（`fetch_daily_task`）
- **API**: 对外接口（`GET /market/daily`）

### 边类型
- **PRODUCES**: Task → Table
- **READS**: Task → Source
- **MAPS**: Table.Column → Table.Column（转换关系）
- **EXPOSES**: Table → API

---

## 具体步骤

### 1. Model 定义

```python
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship

class LineageNode(Base):
    __tablename__ = "lineage_nodes"

    id = Column(Integer, primary_key=True)
    node_id = Column(String(100), unique=True, nullable=False)  # 全局唯一 ID
    node_type = Column(String(20), nullable=False)  # source/table/column/task/api
    name = Column(String(100), nullable=False)
    metadata = Column(JSON)  # 额外信息（如表注释、任务参数）
    created_at = Column(DateTime, server_default=func.now())

class LineageEdge(Base):
    __tablename__ = "lineage_edges"

    id = Column(Integer, primary_key=True)
    source_node_id = Column(String(100), ForeignKey('lineage_nodes.node_id'), nullable=False)
    target_node_id = Column(String(100), ForeignKey('lineage_nodes.node_id'), nullable=False)
    edge_type = Column(String(20), nullable=False)  # produces/reads/maps/exposes
    properties = Column(JSON)  # 边属性（如转换公式）
    created_at = Column(DateTime, server_default=func.now())
```

### 2. 自动采集实现

```python
# app/services/lineage_collector.py

class LineageCollector:
    """血缘数据自动采集器"""

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def register_source(self, api_name: str, params: dict = None):
        """注册数据源节点"""
        node_id = f"source:{api_name}"
        self.nodes[node_id] = {
            "node_id": node_id,
            "node_type": "source",
            "name": api_name,
            "metadata": {"params": params or {}}
        }
        return node_id

    def register_task(self, task_name: str, inputs: list[str], outputs: list[str]):
        """注册任务节点及其依赖"""
        task_id = f"task:{task_name}"
        self.nodes[task_id] = {
            "node_id": task_id,
            "node_type": "task",
            "name": task_name,
            "metadata": {}
        }

        # 边: Task → Source (READS)
        for src in inputs:
            self.edges.append({
                "source_node_id": src,
                "target_node_id": task_id,
                "edge_type": "reads"
            })

        # 边: Task → Table (PRODUCES)
        for out in outputs:
            self.edges.append({
                "source_node_id": task_id,
                "target_node_id": out,
                "edge_type": "produces"
            })

    def register_table(self, table_name: str, columns: list[str]):
        """注册表与字段节点"""
        table_id = f"table:{table_name}"
        self.nodes[table_id] = {
            "node_id": table_id,
            "node_type": "table",
            "name": table_name,
            "metadata": {"columns": columns}
        }

        for col in columns:
            col_id = f"column:{table_name}.{col}"
            self.nodes[col_id] = {
                "node_id": col_id,
                "node_type": "column",
                "name": col,
                "metadata": {"table": table_name}
            }
            # 边: Table → Column (CONTAINS)
            self.edges.append({
                "source_node_id": table_id,
                "target_node_id": col_id,
                "edge_type": "contains"
            })

    def register_api(self, api_path: str, depends_on: list[str]):
        """注册 API 节点"""
        api_id = f"api:{api_path}"
        self.nodes[api_id] = {
            "node_id": api_id,
            "node_type": "api",
            "name": api_path,
            "metadata": {"method": "GET"}
        }
        for tbl in depends_on:
            self.edges.append({
                "source_node_id": tbl,
                "target_node_id": api_id,
                "edge_type": "exposes"
            })

    async def persist(self):
        """持久化到数据库"""
        from app.db.session import async_session
        async with async_session() as session:
            for node_data in self.nodes.values():
                node = LineageNode(**node_data)
                session.add(node)
            for edge_data in self.edges:
                edge = LineageEdge(**edge_data)
                session.add(edge)
            await session.commit()
```

### 3. 集成到抓取任务

在 `fetch_daily_task.py` 中注册血缘:

```python
from app.services.lineage_collector import LineageCollector

collector = LineageCollector()

# 注册数据源
source_id = collector.register_source("pro.daily", {"freq": "D"})

# 注册任务
collector.register_task(
    task_name="fetch_daily_task",
    inputs=[source_id],
    outputs=["table:daily_bars"]
)

# 注册表（在 Model 定义后自动或手动）
collector.register_table("daily_bars", ["ts_code", "trade_date_dt", "open", "high", "low", "close", "vol"])

# 注册 API
collector.register_api("/market/daily", ["table:daily_bars"])

# 任务完成后持久化
await collector.persist()
```

### 4. 查询 API

```python
# app/api/v1/lineage.py

from fastapi import APIRouter
from app.services.lineage_collector import LineageCollector

router = APIRouter()

@router.get("/downstream/{table_name}")
async def get_downstream(table_name: str):
    """查询某表的下游影响（哪些 API/报表依赖它）"""
    # 从 lineage_edges 查询
    pass

@router.get("/upstream/{column}")
async def get_upstream(column: str):
    """查询字段的上游来源（从哪个 source 来）"""
    pass
```

---

## 验收标准

- [ ] `LineageNode` 与 `LineageEdge` 表创建成功
- [ ] `LineageCollector` 可注册节点/边并持久化
- [ ] 至少一个任务（如 fetch_daily）集成血缘采集
- [ ] API `/lineage/downstream/{table}` 与 `/lineage/upstream/{column}` 可查询
- [ ] 测试通过

---

## 交付物

- [ ] Model + 迁移
- [ ] `app/services/lineage_collector.py`
- [ ] 任务集成示例（fetch_daily_task）
- [ ] API 端点
- [ ] `tests/test_lineage.py`

---

**Trigger**: WS3-02 完成后
**Estimated Time**: 0.5 天
