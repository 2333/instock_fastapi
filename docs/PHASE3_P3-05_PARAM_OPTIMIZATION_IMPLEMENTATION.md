# Phase 3 实施任务：P3-05 参数优化服务 - 后端基础实现

## 任务目标
实现自动化策略参数优化后端：优化任务管理 + 算法执行 + 结果对比。

## 实施范围（本次）

### 1. 数据库模型（2 张新表）
- `ParameterOptimizationJob` - 优化任务主记录
- `ParameterOptimizationTrial` - 单次试验记录

### 2. 优化算法实现
- **随机搜索**（Random Search）：在参数空间均匀随机采样
- **贝叶斯优化**（Bayesian Optimization）：高斯过程 + 期望改进（EI）采集函数
- **评估函数**：调用回测 API 计算目标指标（夏普/收益/回撤）

### 3. 后台任务
- `run_optimization_job`：异步执行优化任务
- 支持并发控制（max_parallel_trials）
- 实时更新任务进度与状态
- 完成时发送通知（可选）

### 4. API 端点
```python
POST   /api/v1/optimization/jobs              # 创建优化任务
GET    /api/v1/optimization/jobs              # 列出我的优化任务
GET    /api/v1/optimization/jobs/{job_id}     # 任务详情与进度
DELETE /api/v1/optimization/jobs/{job_id}     # 取消任务
GET    /api/v1/optimization/jobs/{job_id}/trials   # 试验结果列表
GET    /api/v1/optimization/jobs/{job_id}/best     # 最优参数
```

### 5. 前端准备（后端只需提供接口）
- 待后续 heartbeat 实现

## 验收标准
- [ ] 2 张模型表可通过 `Base.metadata.create_all` 自动建表
- [ ] 支持至少 2 种优化算法（随机搜索 + 贝叶斯）
- [ ] 异步任务可创建、查询、取消
- [ ] 试验结果完整存储（参数 + 得分 + 回测ID）
- [ ] 最优参数自动识别并存储
- [ ] 测试无回归（131 → 131+）

## 技术决策

### 算法选择
- **随机搜索**：简单高效，适合初步探索
- **贝叶斯优化**：使用 scikit-learn GaussianProcessRegressor
  - 采集函数：Expected Improvement (EI)
  - 核函数：RBF（径向基函数）
  - 初始点：随机采样 5-10 个

### 参数空间表示
```python
param_space = {
  "short_window": {"type": "int", "low": 5, "high": 30},
  "long_window": {"type": "int", "low": 20, "high": 100},
  "rsi_period": {"type": "int", "low": 6, "high": 24},
}
```

### 目标指标
- 默认：`sharpe_ratio`（夏普比率）
- 可选：`total_return`（总收益）、`max_drawdown`（最小化最大回撤）

### 任务状态流转
```
pending → running → completed / failed / cancelled
```

### 并发控制
- 单个用户同时运行任务数限制：3
- 全局并发任务数限制：10（通过队列控制）

## 文件清单

### 新增
- `app/models/optimization_models.py` - 优化任务与试验模型
- `app/schemas/optimization_schema.py` - Pydantic schemas
- `app/services/optimization_service.py` - 优化服务（算法 + 任务管理）
- `app/jobs/tasks/optimization_tasks.py` - Celery 任务（异步执行）
- `app/api/routers/optimization_router.py` - API 路由

### 修改
- `app/models/__init__.py` - 导出新模型
- `app/api/routers/__init__.py` - 注册新路由

## 依赖项
- scikit-learn（贝叶斯优化）
- celery（异步任务，已存在）
- 回测 API（P1-04 已实现）

## 估算
- 模型 + Schema：1 小时
- 算法实现：3 小时（随机搜索 + 贝叶斯优化）
- 服务层 + 任务：2 小时
- API 端点：1.5 小时
- 测试验证：1.5 小时
- **总计：9 小时 ≈ 1.25 人日**

---

**状态**: 待实施
**优先级**: P0（Phase 3 核心功能，技术风险低）
**依赖**: 无（复用现有回测）
