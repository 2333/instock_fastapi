# Task: WS0-02 时间列与唯一约束规范落地

**Owner**: Agent A (Database Migration Specialist)
**Workstream**: WS-0 基础设施
**Priority**: P0 (阻塞 WS-1/2/3)
**Estimated Effort**: 0.5 天
**Dependencies**: WS0-01 (Alembic 基线)
**Status**: Ready to assign (等待 M1 启动信号)

---

## 任务描述

统一事实表时间列与主键规范，将旧 `trade_date` (字符串) 迁移到 `trade_date_dt` (DateTime)，并建立 `(ts_code, trade_date_dt)` 联合主键。

---

## 背景与动机

当前问题:
- `daily_bars.trade_date` 为 VARCHAR/STRING，不利于时间范围查询与排序
- 缺少统一时间列标准，各表时间格式不一致
- 唯一约束不明确，可能导致重复数据

目标态:
- 所有事实表使用 `trade_date_dt` (DateTime) 作为标准时间列
- 保留 `trade_date` 字符串列（用于兼容旧查询，标记为 deprecated）
- 联合主键: `(ts_code, trade_date_dt)`
- 索引命名规范: `ix_{table}_{column(s)}`

---

## 涉及表

| 表名 | 当前时间列 | 目标时间列 | 主键 |
|------|-----------|-----------|------|
| daily_bars | trade_date (str) | trade_date_dt (DateTime) | (ts_code, trade_date_dt) |
| indicators | trade_date (str) | trade_date_dt (DateTime) | (ts_code, trade_date_name, trade_date_dt) |
| patterns | trade_date (str) | trade_date_dt (DateTime) | (ts_code, pattern_name, trade_date_dt) |
| moneyflow (新表) | - | trade_date_dt (DateTime) | (ts_code, trade_date_dt) |

---

## 具体步骤

### 1. 更新 Model 定义

编辑 `app/models/stock_model.py` (或分文件):

```python
from sqlalchemy import Column, DateTime, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

class DailyBar(Base):
    __tablename__ = "daily_bars"

    id = Column(Integer, primary_key=True)  # 可选，或直接用复合主键
    ts_code = Column(String(12), nullable=False)
    trade_date_dt = Column(DateTime, nullable=False)  # 新增标准时间列
    trade_date = Column(String(8), nullable=False)   # 保留旧列（兼容）

    # 联合唯一约束
    __table_args__ = (
        UniqueConstraint('ts_code', 'trade_date_dt', name='uq_daily_bars_ts_code_date'),
    )

    # 索引
    __table_args__ = (
        Index('ix_daily_bars_ts_code', 'ts_code'),
        Index('ix_daily_bars_trade_date_dt', 'trade_date_dt'),
    )
```

**注意**:
- 先添加 `trade_date_dt` 列，保留旧 `trade_date`
- 后续数据迁移完成后，再考虑是否删除旧列（延后）

### 2. 生成迁移脚本

```bash
# 在 alembic 目录下
alembic revision --autogenerate -m "standardize-time-columns"
```

审查生成的 `alembic/versions/<rev>_standardize-time-columns.py`:

```python
def upgrade():
    # 1. 添加新列
    op.add_column('daily_bars', sa.Column('trade_date_dt', sa.DateTime(), nullable=True))
    op.add_column('indicators', sa.Column('trade_date_dt', sa.DateTime(), nullable=True))
    op.add_column('patterns', sa.Column('trade_date_dt', sa.DateTime(), nullable=True))

    # 2. 数据迁移: 将 trade_date 字符串转为 DateTime
    # 注意: 大批量数据需分批更新，避免锁表
    op.execute("""
        UPDATE daily_bars
        SET trade_date_dt = to_timestamp(trade_date, 'YYYYMMDD')
        WHERE trade_date IS NOT NULL
    """)

    # 3. 设置 NOT NULL (数据迁移后)
    op.alter_column('daily_bars', 'trade_date_dt', nullable=False)

    # 4. 创建唯一约束
    op.create_unique_constraint('uq_daily_bars_ts_code_date', 'daily_bars', ['ts_code', 'trade_date_dt'])
    op.create_unique_constraint('uq_indicators_ts_code_date_name', 'indicators', ['ts_code', 'indicator_name', 'trade_date_dt'])
    op.create_unique_constraint('uq_patterns_ts_code_date_name', 'patterns', ['ts_code', 'pattern_name', 'trade_date_dt'])

    # 5. 创建索引
    op.create_index('ix_daily_bars_ts_code', 'daily_bars', ['ts_code'])
    op.create_index('ix_daily_bars_trade_date_dt', 'daily_bars', ['trade_date_dt'])

def downgrade():
    # 反向操作: 删除约束/索引 → 复制 trade_date_dt 回 trade_date → 删除列
    op.drop_constraint('uq_daily_bars_ts_code_date', 'daily_bars', type_='unique')
    op.drop_index('ix_daily_bars_ts_code', table_name='daily_bars')
    op.drop_index('ix_daily_bars_trade_date_dt', table_name='daily_bars')

    # 回填 trade_date
    op.execute("""
        UPDATE daily_bars
        SET trade_date = to_char(trade_date_dt, 'YYYYMMDD')
        WHERE trade_date_dt IS NOT NULL
    """)

    op.drop_column('daily_bars', 'trade_date_dt')
    # ... 其他表类似
```

### 3. 数据迁移策略（大批量）

如果 `daily_bars` 超过 100 万行，一次性更新会锁表。采用分批:

```python
from alembic import op
import sqlalchemy as sa

BATCH_SIZE = 10000

def batch_update(table, batch_size):
    # 获取最大/最小 ID
    conn = op.get_bind()
    result = conn.execute(f"SELECT MIN(id), MAX(id) FROM {table}")
    min_id, max_id = result.fetchone()

    for start in range(min_id, max_id + 1, batch_size):
        end = start + batch_size - 1
        op.execute(f"""
            UPDATE {table}
            SET trade_date_dt = to_timestamp(trade_date, 'YYYYMMDD')
            WHERE id BETWEEN {start} AND {end}
              AND trade_date IS NOT NULL
              AND trade_date_dt IS NULL
        """)
```

### 4. 验证迁移

```bash
# 1. 在测试库运行
alembic upgrade head

# 2. 检查列是否存在
psql -d instockdb -c "\d daily_bars"

# 3. 检查数据完整性
psql -d instockdb -c "
SELECT COUNT(*) as total,
       COUNT(trade_date_dt) as with_datetime,
       COUNT(CASE WHEN trade_date IS NULL THEN 1 END) as old_null
FROM daily_bars;
"

# 4. 运行相关测试
pytest tests/test_screening_baseline.py -v
pytest tests/test_selection_market_services.py -v
```

### 5. 更新 Repository/Service 层

修改 `app/repositories/daily_bar_repository.py` 等，将查询中的 `trade_date` 改为 `trade_date_dt`:

```python
# 旧
query = select(DailyBar).where(DailyBar.trade_date == date_str)

# 新
query = select(DailyBar).where(DailyBar.trade_date_dt == datetime.strptime(date_str, '%Y%m%d'))
```

**注意**: 保持向后兼容，可在 service 层同时接受 str 和 datetime，内部转换。

---

## 验收标准

- [ ] 迁移脚本可执行，无数据丢失
- [ ] `daily_bars`/`indicators`/`patterns` 三张表均包含 `trade_date_dt` 列且非空
- [ ] 联合唯一约束创建成功，无重复数据报错
- [ ] 查询性能: `WHERE trade_date_dt BETWEEN ...` 使用索引
- [ ] 相关测试通过（screening_baseline、selection_market_services 等）

---

## 风险与回滚

**风险**:
- 大批量数据迁移耗时（可能数分钟），需在低峰期执行
- 迁移失败需回滚: `alembic downgrade -1`

**回滚计划**:
- 迁移前备份: `pg_dump -t daily_bars -t indicators -t patterns backup.sql`
- 回滚命令: `alembic downgrade -1` 或指定版本号

---

## 交付物清单

- [x] 任务定义文件 (本文件)
- [ ] 迁移脚本 `alembic/versions/<rev>_standardize-time-columns.py`
- [ ] Model 更新 (app/models/)
- [ ] Repository/Service 层适配
- [ ] 验证测试通过记录
- [ ] `docs/MIGRATION_CONVENTIONS.md` (WS0-01 已创建)

---

**任务状态**: Ready for assignment
**Trigger**: M1 启动命令 + Tushare token 就绪
