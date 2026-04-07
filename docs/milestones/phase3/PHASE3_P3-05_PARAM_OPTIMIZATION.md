# Phase 3 任务设计：P3-05 自动化参数优化服务

## 目标
为回测策略自动寻找最优参数组合，减少人工调参成本。

## 设计原则
- **自动化**：用户选择策略类型与参数空间，系统自动运行多组回测
- **结果对比**：提供参数敏感性分析与对比视图
- **防过拟合**：内置过拟合检测提醒
- **异步化**：长耗时任务后台执行，结果推送

## 现状分析

### 当前回测流程
```
用户手动配置参数 → 单次回测 → 查看结果 → 手动调整参数 → 重复
```

### 痛点
- 调参依赖经验，耗时耗力
- 难以探索参数空间全貌
- 无法量化不同参数组合的稳健性

## 优化算法选型

### 方案对比
| 算法 | 适用场景 | 复杂度 | 实现难度 | 推荐度 |
|------|----------|--------|----------|--------|
| 网格搜索 | 参数少（2-3 个） | O(n^d) | 简单 | ⭐⭐⭐ |
| 随机搜索 | 参数多，非线性 | O(n) | 简单 | ⭐⭐⭐⭐ |
| 贝叶斯优化 | 参数少，昂贵评估 | O(n log n) | 中等 | ⭐⭐⭐⭐⭐ |
| 遗传算法 | 复杂非线性空间 | O(gen * pop) | 复杂 | ⭐⭐ |

### 推荐方案：分层优化
1. **粗筛**：随机搜索 50-100 组参数（覆盖空间）
2. **精调**：对 Top 10 组进行贝叶斯优化（高斯过程）
3. **稳健性检验**：对最优参数进行滚动回测（分段验证）

## 数据模型

### OptimizationJob（优化任务）
```python
class ParameterOptimizationJob(Base):
    __tablename__ = "parameter_optimization_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameter_space: Mapped[dict] = mapped_column(JSONB, nullable=False)  # 参数边界
    optimization_method: Mapped[str] = mapped_column(String(50), default="random")  # random/bayesian/genetic
    objective_metric: Mapped[str] = mapped_column(String(50), default="sharpe_ratio")  # sharpe/returns/max_drawdown
    total_trials: Mapped[int] = mapped_column(Integer, default=100)
    completed_trials: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/completed/failed
    best_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    best_score: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    results: Mapped[list[dict]] = mapped_column(JSONB, default=list)  # 所有试验结果
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### OptimizationTrial（单次试验）
```python
class ParameterOptimizationTrial(Base):
    __tablename__ = "parameter_optimization_trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)  # 目标指标值
    backtest_result_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 关联回测结果
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/completed/failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

## 后端服务

### ParameterOptimizationService
```python
class ParameterOptimizationService:
    def __init__(self, db: AsyncSession, broker: TaskBroker):
        self.db = db
        self.broker = broker  # Celery / RQ

    async def create_job(self, user_id: int, strategy_type: str,
                         param_space: dict, method: str = "random",
                         total_trials: int = 100,
                         objective: str = "sharpe_ratio") -> int:
        """创建优化任务，异步启动"""
        job = ParameterOptimizationJob(
            user_id=user_id,
            strategy_type=strategy_type,
            parameter_space=param_space,
            optimization_method=method,
            total_trials=total_trials,
            objective_metric=objective,
        )
        self.db.add(job)
        await self.db.flush()
        # 触发异步任务
        self.broker.enqueue(run_optimization_job, job.id)
        return job.id

    async def get_job_status(self, job_id: int) -> dict:
        """查询优化任务进度"""
        # 返回：status / completed_trials / total_trials / best_score / best_params
```

### 优化算法实现
```python
# app/optimization/algorithms.py

def random_search(param_space: dict, n_trials: int) -> list[dict]:
    """随机搜索生成参数组合"""
    # 对每个参数在边界内随机采样

def bayesian_optimize(param_space: dict,
                      initial_samples: list[dict],
                      n_trials: int,
                      objective_fn) -> list[dict]:
    """高斯过程贝叶斯优化"""
    # 使用 scikit-learn GaussianProcessRegressor
    # 采集函数：Expected Improvement (EI)

def evaluate_parameters(strategy_type: str, params: dict,
                        start_date: str, end_date: str,
                        stock_code: str) -> float:
    """执行单次回测并返回目标指标"""
    # 调用 backtest_api.run_backtest
    # 提取 objective_metric（夏普/收益/回撤）
```

### 后台任务
```python
# app/jobs/tasks/optimization.py
@celery.task(bind=True)
def run_optimization_job(self, job_id: int):
    """Celery 任务：执行参数优化"""
    # 1. 加载 job 配置
    # 2. 根据方法生成初始参数组
    # 3. 并发执行回测（使用 asyncio.gather，控制并发数）
    # 4. 记录每轮结果到 trial 表
    # 5. 如果是贝叶斯，更新 GP 模型并生成下一轮
    # 6. 找到最优参数，更新 job.best_parameters / best_score
    # 7. 发送完成通知
```

## API 端点

```python
# app/api/routers/optimization_router.py
router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])

@router.post("/jobs")  # 创建优化任务
@router.get("/jobs")  # 列出我的优化任务
@router.get("/jobs/{job_id}")  # 查询任务详情与进度
@router.delete("/jobs/{job_id}")  # 取消任务
@router.get("/jobs/{job_id}/trials")  # 获取所有试验结果（用于对比图表）
@router.get("/jobs/{job_id}/best")  # 获取最优参数
```

## 前端集成

### 回测页面集成
在 Backtest 页面添加"参数优化"标签页：
```
[ 单次回测 ]  [ 参数优化 ]
┌─────────────────────────────────────┐
│ 策略类型：[MA 交叉 ▼]               │
│ 参数空间：                           │
│   ┌─────────────┬─────────────┐    │
│   │ 参数        │ 范围         │    │
│   ├─────────────┼─────────────┤    │
│   │ 短期窗口     │ 5 - 30      │    │
│   │ 长期窗口     │ 20 - 100    │    │
│   └─────────────┴─────────────┘    │
│ 优化方法：[随机搜索 ▼] 目标：[夏普比率 ▼] │
│ 试验次数：100 并发数：4               │
│                                         │
│ [开始优化]                              │
│                                         │
│ 进度：██████████░░░░ 45/100           │
│ 最优参数：short=12, long=56, 夏普=1.82 │
│                                         │
│ [查看详细对比]                          │
└─────────────────────────────────────┘
```

### 参数对比图表
使用散点图/平行坐标图展示参数-性能关系：
- X 轴：参数值（short_window / long_window）
- Y 轴：夏普比率 / 总收益
- 颜色：最大回撤（红=高回撤，绿=低回撤）
- 点击点查看该参数完整回测报告

### 优化历史记录
- 列出历史优化任务
- 状态标签（运行中/完成/失败）
- 最优参数一键应用到当前回测配置

## 防过拟合机制

### 滚动窗口验证
```python
def robustness_check(params: dict, stock_code: str, periods: int = 3):
    """将历史期分为多段，验证参数稳健性"""
    # 例如：2018-2020 / 2020-2022 / 2022-2024
    # 计算各段收益/夏普的标准差，标准差过大则警告
```

### 过拟合警告
- 训练集表现好，测试集表现差 → 高过拟合风险
- 参数过于复杂（过多自由参数）→ 警告
- 最优参数位于边界 → 警告（可能需扩大搜索空间）

## 冷启动策略
- 预置 3 种常见策略的推荐参数空间（MA 交叉 / RSI 超卖 / MACD）
- 首次使用显示示例任务（"优化 MA 交叉策略"）
- 提供"快速优化"一键配置（默认 50 次随机搜索）

## 验收标准
- [ ] 优化任务创建/查询/取消接口完成
- [ ] 支持至少 2 种优化算法（随机搜索 + 贝叶斯）
- [ ] 异步执行，可查询进度
- [ ] 最优参数自动提取并展示
- [ ] 参数-性能对比图表（散点图/平行坐标）
- [ ] 过拟合检测与警告
- [ ] 一键应用最优参数到回测配置
- [ ] 并发控制（最大 4 个同时运行）

## 风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| 计算资源耗尽 | 服务器负载高 | 并发限制 + 队列 + 优先级 |
| 回测时间过长 | 用户体验差 | 异步任务 + 进度推送 + 可取消 |
| 过拟合结果误导 | 实盘亏损 | 强制滚动验证 + 明确警告 |
| 参数空间不合理 | 无有效结果 | 提供推荐范围 + 边界检查 |

## 依赖项
- P1-04 异步回测基础架构（已具备）
- 任务队列（Celery/Redis Queue，建议复用现有）
- 前端图表库（ECharts 已接入）

## 估算
- 后端：10 小时（算法 + 任务 + API + 过拟合检测）
- 前端：6 小时（优化页面 + 对比图表 + 历史记录）
- 总计：**4 人日**

---

**状态**: 草案待评审
**创建时间**: 2026-04-03
**负责人**: TBD
