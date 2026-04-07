# Phase 3 实施任务：P3-05 参数优化服务 - 前端集成

## 任务目标
完成参数优化服务的前端实现：优化任务配置页面 + 进度监控 + 结果对比可视化。

## 实施范围（本次）

### 1. OptimizationPage 页面
**文件**: `web/src/views/Optimization.vue`
**功能**:
- 选择策略类型（下拉选择）
- 配置参数空间（每个参数的 min/max/step 输入）
- 选择优化方法（随机搜索 / 贝叶斯优化）
- 选择目标指标（夏普比率 / 总收益 / 最大回撤）
- 设置试验次数（总 trials）与并发数
- 指定回测范围（股票代码 / 开始日期 / 结束日期 / 初始资金）
- 提交创建优化任务
- 任务列表展示（状态：pending/running/completed/failed）
- 点击任务查看详情与进度

### 2. OptimizationDetail 组件
**文件**: `web/src/components/OptimizationDetail.vue`
**功能**:
- 任务基本信息展示（策略类型 / 方法 / 状态 / 进度条）
- 当前最优参数展示
- 试验结果表格（参数组合 + 得分 + 状态）
- 参数-性能散点图（X=参数值，Y=得分，颜色=回撤）
- 平行坐标图（多参数关系可视化）
- 最优参数一键应用到 Backtest 页面

### 3. Backtest 页面集成
**文件**: `web/src/views/Backtest.vue`
**改动**:
- 在配置面板添加"参数优化"标签页（与"单次回测"并列）
- 参数优化 tab 包含：参数空间配置 + 启动优化按钮 + 当前任务进度卡片
- 优化完成后显示最优参数并支持一键填入回测配置

### 4. Dashboard 集成
**文件**: `web/src/views/Dashboard.vue`
**改动**:
- 添加"优化任务"卡片，展示最近运行的优化任务与状态
- 快速跳转到 Optimization 页面

## 验收标准
- [ ] OptimizationPage 页面可创建优化任务（表单验证通过）
- [ ] 任务列表可展示，支持状态筛选
- [ ] OptimizationDetail 组件展示进度与试验结果
- [ ] 散点图/平行坐标图正确渲染（使用 ECharts）
- [ ] 最优参数一键应用到 Backtest 配置
- [ ] 类型检查通过（vue-tsc）
- [ ] 与后端 API 对接成功

## 技术决策

### 图表库
复用现有 ECharts（已在 Backtest 页面使用）：
- 散点图：`scatter` 系列
- 平行坐标图：`parallel` 系列

### 状态管理
- 优化任务状态通过轮询或 WebSocket（可选）更新
- 简化：页面轮询每 5 秒刷新任务进度

### API 对接
- 已存在的 `optimizationApi`（需补充到 api/index.ts）
- 端点：POST /jobs, GET /jobs, GET /jobs/{id}/progress, GET /jobs/{id}/trials, GET /jobs/{id}/best

## 文件清单

### 新增
- `web/src/views/Optimization.vue`
- `web/src/components/OptimizationDetail.vue`
- `web/src/api/optimization.ts`（或扩展到 index.ts）

### 修改
- `web/src/views/Backtest.vue` - 添加参数优化标签页
- `web/src/views/Dashboard.vue` - 添加优化任务卡片
- `web/src/router/index.ts` - 新增 `/optimization` 路由
- `web/src/api/index.ts` - 导出 optimizationApi

## 估算
- OptimizationPage：3 小时
- OptimizationDetail 组件：2.5 小时（含图表）
- Backtest 集成：1.5 小时
- Dashboard 集成：0.5 小时
- **总计：7.5 小时 ≈ 1 人日**

---

**状态**: 待实施
**优先级**: P0（Phase 3 核心功能）
**依赖**: 后端 API 已就绪（P3-05 后端完成）
