# Task: WS0-01 Alembic 基线与迁移入口统一

**Owner**: Agent A (Database Migration Specialist)
**Workstream**: WS-0 基础设施
**Priority**: P0 (阻塞 WS-1/2/3)
**Estimated Effort**: 0.5 天
**Dependencies**: 无
**Status**: Ready to assign (等待 M1 启动信号)

---

## 任务描述

建立 Alembic 迁移框架，替代现有 `init_db()` auto-create 逻辑，为后续所有数据层迁移提供标准入口。

---

## 具体步骤

### 1. 环境准备
```bash
cd /Users/zhangkai/projects/instock_fastapi
source .venv/bin/activate
pip install alembic  # 已安装，验证: alembic --version
```

### 2. 初始化 Alembic
```bash
alembic init alembic/
```

这会创建:
- `alembic/` 目录 (env.py, script.py.mako, versions/)
- `alembic.ini` 根配置文件

### 3. 配置 `alembic.ini`
编辑 `alembic.ini`，设置:
```ini
sqlalchemy.url = postgresql+asyncpg://instock:instock@localhost:5432/instockdb
# 或使用环境变量: sqlalchemy.url = %(DATABASE_URL)s
```

### 4. 配置 `alembic/env.py`
关键修改:
```python
from app.config import get_settings
from app.database import async_engine, Base
from sqlalchemy.ext.asyncio import AsyncEngine

# 1. 设置 target_metadata
target_metadata = Base.metadata

# 2. 使用 async engine
def run_migrations_online() -> None:
    connectable = async_engine

    with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)
```

**注意**: Alembic 原生不支持 async engine，需使用 `alembic[async]` 或自定义上下文。参考方案:
- 方案 A: 使用 `alembic[async]` 扩展 (推荐)
- 方案 B: 在 `do_run_migrations` 内创建 sync engine

### 5. 生成基准迁移
```bash
alembic revision --autogenerate -m "baseline"
```
审查生成的迁移脚本，确保:
- 包含所有现有表的创建 (stocks, daily_bars, indicators, patterns, 等)
- 使用 `CREATE TABLE IF NOT EXISTS` 或检查表存在性
- 不包含数据丢失操作

### 6. 应用迁移
```bash
alembic upgrade head
```
验证:
- 数据库表结构与模型一致
- 无错误

### 7. 添加应用入口
在 `app/database.py` 或 `app/main.py` 添加:
```python
from alembic.config import Config
from alembic import command

def run_migrations():
    """应用启动时自动迁移（可选）"""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

### 8. 创建迁移规范文档
新建 `docs/MIGRATION_CONVENTIONS.md`，记录:
- 迁移命名规则: `{type}_{short_description}` (e.g., `add_column_to_daily_bars`)
- 依赖声明: `depends_on` 字段使用
- 回滚策略: 每个 `upgrade` 必须有对应的 `downgrade`
- 数据迁移注意事项: 大数据表使用批处理

---

## 输出物

| 输出 | 路径 | 说明 |
|------|------|------|
| Alembic 配置目录 | `alembic/` | env.py, script.py.mako, versions/ |
| 根配置 | `alembic.ini` | 数据库 URL 指向 |
| 基准迁移脚本 | `alembic/versions/<rev>_baseline.py` | 包含所有现有表创建 |
| 应用入口函数 | `app/database.py::run_migrations()` | 可选，用于自动迁移 |
| 迁移规范文档 | `docs/MIGRATION_CONVENTIONS.md` | 团队协作规范 |

---

## 验收标准

- [ ] `alembic current` 显示当前版本 (如 `None` -> `baseline`)
- [ ] `alembic upgrade head` 无错误完成
- [ ] 数据库表结构与 `app/models/` 中定义的 Base.metadata 一致
- [ ] 迁移脚本可通过代码审查（无数据丢失风险）
- [ ] `docs/MIGRATION_CONVENTIONS.md` 已创建并团队可查阅

---

## 验证命令

```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 应用迁移
alembic upgrade head

# 回滚（测试）
alembic downgrade -1

# 验证表是否存在
psql -d instockdb -c "\dt"
```

---

## 注意事项

- **生产环境**: 迁移前必须备份数据库
- **并发**: 多进程同时启动需加锁（alembic 自带版本锁）
- **数据迁移**: 大数据表（如 daily_bars）的列类型转换需分批进行，避免锁表
- **回滚**: 每个迁移必须提供 `downgrade` 函数，至少能回退到上一版本

---

## 后续任务依赖

- WS0-02 (时间列规范): 依赖 baseline 迁移完成
- WS0-03 (Timescale 规范): 依赖 WS0-02 完成后在基线之上添加 hypertable
- WS1 系列任务: 全部依赖 WS-0 基础设施完成

---

**任务状态**: Ready
**创建时间**: 2026-04-05 (M1 准备阶段)
**触发条件**: M1 启动信号 + Tushare token 就绪
