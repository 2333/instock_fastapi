# Task: WS0-03 Timescale 规范落地

**Owner**: Agent A (Database Migration Specialist)
**Workstream**: WS-0 基础设施
**Priority**: P0 (阻塞 WS-1 核心改造)
**Estimated Effort**: 0.5 天
**Dependencies**: WS0-02 (时间列规范完成)
**Status**: Ready to assign (等待 M1 启动信号)

---

## 任务描述

将核心事实表转换为 TimescaleDB hypertable，配置 chunk 间隔、compression 和 retention 策略。

---

## 背景

TimescaleDB 是 PostgreSQL 的时序扩展，提供:
- 自动分区（hypertable）按时间维度
- 高效时序查询（时间窗口聚合）
- 压缩与保留策略

目标表（需转换为 hypertable）:
- `daily_bars` - 股票日线行情
- `indicators` - 技术指标
- `patterns` - K线形态
- `moneyflow` - 资金流向（新表，直接创建为 hypertable）

---

## 具体步骤

### 1. 确认 TimescaleDB 扩展已安装

```sql
-- 在 psql 中执行
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';
-- 应返回: timescaledb | x.x.x
```

如未安装，参考 `docs/DATA_LAYER_REPORT.md` 安装指南。

### 2. 创建迁移脚本

在 WS0-02 完成后，生成新迁移:

```bash
alembic revision -m "convert-core-tables-to-hypertable"
```

编辑生成的迁移脚本 `alembic/versions/<rev>_convert-core-tables-to-hypertable.py`:

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. 确保 TimescaleDB 扩展可用
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # 2. 转换 daily_bars 为 hypertable
    # 注意: 表必须已存在（WS0-02 已创建）
    op.execute("""
        SELECT create_hypertable(
            'daily_bars',
            'trade_date_dt',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """)

    # 3. 设置压缩策略（30 天前的数据自动压缩）
    op.execute("""
        ALTER TABLE daily_bars SET (
            timescaledb.compress, timescaledb.compress_orderby = 'trade_date_dt DESC'
        )
    """)
    op.execute("""
        SELECT add_compression_policy('daily_bars', INTERVAL '30 days')
    """)

    # 4. 对 indicators 表执行相同操作
    op.execute("""
        SELECT create_hypertable(
            'indicators',
            'trade_date_dt',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """)
    op.execute("ALTER TABLE indicators SET (timescaledb.compress)")
    op.execute("SELECT add_compression_policy('indicators', INTERVAL '30 days')")

    # 5. 对 patterns 表
    op.execute("""
        SELECT create_hypertable(
            'patterns',
            'trade_date_dt',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """)
    op.execute("ALTER TABLE patterns SET (timescaledb.compress)")
    op.execute("SELECT add_compression_policy('patterns', INTERVAL '30 days')")

    # 6. moneyflow 表（如果是新创建，直接在创建时指定）
    # 如已存在，同样转换
    op.execute("""
        SELECT create_hypertable(
            'moneyflow',
            'trade_date_dt',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """)
    op.execute("ALTER TABLE moneyflow SET (timescaledb.compress)")
    op.execute("SELECT add_compression_policy('moneyflow', INTERVAL '30 days')")

def downgrade():
    # 移除压缩策略
    op.execute("SELECT remove_compression_policy('daily_bars')")
    op.execute("SELECT remove_compression_policy('indicators')")
    op.execute("SELECT remove_compression_policy('patterns')")
    op.execute("SELECT remove_compression_policy('moneyflow')")

    # 删除 hypertable（注意：这不会删除底层表，仅移除 hypertable 特性）
    # TimescaleDB 没有直接"降级"命令，需手动重建普通表
    # 实际 downgrade 可能需: 导出数据 → 删除 hypertable → 重建普通表 → 导入数据
    # 为简化，downgrade 留空或记录"不可自动回滚，需手动处理"
    pass
```

### 3. 验证 hypertable 创建

```bash
# 应用迁移
alembic upgrade head

# 检查 hypertable 信息
psql -d instockdb -c "
SELECT hypertable_name, chunk_time_interval, compression_enabled
FROM timescaledb_information.hypertables
ORDER BY hypertable_name;
"

# 预期输出:
--  hypertable_name | chunk_time_interval | compression_enabled
--  daily_bars      | 7 days              | t
--  indicators      | 7 days              | t
--  patterns        | 7 days              | t
--  moneyflow       | 7 days              | t
```

### 4. 验证压缩策略

```bash
psql -d instockdb -c "
SELECT policy_name, target_table, compress_after
FROM timescaledb_information.compression_settings;
"
```

### 5. 更新 Model（可选）

SQLAlchemy Model 无需特殊修改，hypertable 对查询透明。但可在文档中标注:

```python
class DailyBar(Base):
    __tablename__ = "daily_bars"
    # ... 列定义不变
    # 注意: 此表已为 TimescaleDB hypertable，按 trade_date_dt 自动分区
```

### 6. 性能验证

运行简单查询，确认时序查询性能:

```sql
-- 查询最近 30 天数据（应只扫描最近 chunk）
SELECT COUNT(*) FROM daily_bars
WHERE trade_date_dt >= NOW() - INTERVAL '30 days';

-- 查看 chunk 统计
SELECT * FROM timescaledb_information.chunks;
```

---

## 验收标准

- [ ] `timescaledb_information.hypertables` 包含 4 张表（daily_bars/indicators/patterns/moneyflow）
- [ ] 每张表的 `chunk_time_interval` 为 7 天
- [ ] 压缩策略已配置（30 天自动压缩）
- [ ] 查询计划使用 Timescale 优化（`EXPLAIN ANALYZE` 显示 chunk 裁剪）
- [ ] 相关测试通过（screening_baseline、selection services 等）

---

## 风险与注意事项

| 风险 | 说明 | 缓解 |
|------|------|------|
| 历史数据过多 | 转换 hypertable 需重建表，大数据量耗时 | 在低峰期执行，提前备份 |
| 查询兼容性 | 某些 SQL 语法可能不兼容 hypertable | 验证核心查询路径 |
| 回滚复杂 | 降级需手动重建普通表 | 迁移前备份，downgrade 留空或记录手动步骤 |
| 存储增长 | chunk 数量增加需监控 | 设置 retention 策略（暂不启用） |

---

## 交付物

- [ ] 迁移脚本 `alembic/versions/<rev>_convert-core-tables-to-hypertable.py`
- [ ] `docs/TIMESCALE_POLICY.md`（chunk 间隔 7d、compression 30d、retention 暂不设）
- [ ] 验证 SQL 与输出截图（可选）

---

**Trigger**: WS0-02 完成后自动启动
**Estimated Time**: 0.5 天（不含数据迁移时间）
