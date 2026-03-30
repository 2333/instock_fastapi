# Phase 0 完成计划：完善扫描引擎

## 背景

当前分支 `phase-0-milestone-4-home-workbench` 已经实现了：
- ✅ 首页工作台 4 卡片（Dashboard.vue）
- ✅ 个股详情页（StockDetail.vue）
- ✅ 回测系统基础功能（Backtest.vue）
- ✅ 基础筛选功能（price/change/market）
- ✅ 命中证据结构（_build_reason）

但 Phase 0 的核心"扫描引擎"还不完整：
- ❌ 技术指标筛选（RSI、MACD、KDJ、BOLL）
- ❌ 形态筛选
- ❌ 筛选页存在大量"暂未接入"占位符
- ❌ 实际数据验证不足

## 目标

让 InStock 成为一个真正可用的最小产品：
1. 能输入筛选条件（完整的指标+形态）
2. 能看到结构化结果
3. 能打开个股详情
4. 能看懂命中证据
5. 首页能以 4 卡片形式真实摘要

## 执行计划

### Phase 0-A: 扫描引擎后端增强（1-2天）

#### 任务 1: 扩展筛选元数据 API
- 文件: `app/services/selection_service.py`
- 在 `get_screening_metadata()` 添加：
  - indicators 列表（RSI、MACD、KDJ、BOLL）
  - patterns 列表（常见形态）
  - 每个指标的可用参数范围
- 保持向后兼容

#### 任务 2: 扩展筛选执行逻辑
- 文件: `app/services/selection_service.py` → `run_selection()`
- 添加指标筛选条件处理：
  - `rsiMin` / `rsiMax`
  - `macdSignal` (看涨/看跌)
  - `kdjParameter` (J值等)
  - `bollPosition` (上下轨)
- 添加形态筛选条件处理（从 `pattern_service` 读取）
- 更新 `_build_reason()` 为指标和形态生成证据

#### 任务 3: 更新 Schema
- 文件: `app/schemas/selection_schema.py`
- 确认 `ScreeningQuery` 包含新字段
- 更新 `ScreeningRunData` 证据结构

### Phase 0-B: 前端筛选页去占位符化（2天）

#### 任务 4: 移除"暂未接入"占位符或标记为 Coming Soon
- 文件: `web/src/views/Selection.vue`
- 选项 A: 移除 unavailableFilterGroups 显示
- 选项 B: 改为"即将推出"灰色不可用状态（推荐 B，保留路线图感）
- 实际接入已支持的指标筛选控件

#### 任务 5: 实现指标筛选 UI
- 添加 RSI 范围输入
- 添加 MACD 信号选择
- 确保筛选条件正确序列化到 API

#### 任务 6: 结果页证据展示优化
- 检查 `reason_summary` 显示
- 确保证据列表可读

### Phase 0-C: 数据健康与首页真实化（0.5天）

#### 任务 7: 验证数据更新时间可见
- 检查 `marketApi` 是否返回最新交易日
- 确认首页卡片显示真实数据而非占位

#### 任务 8: 端到端 Smoke Test
- 启动后端和前端
- 运行一次完整筛选
- 验证：首页→筛选→结果→详情→证据 全链路

### Phase 0-D: 测试与文档（1天）

#### 任务 9: 补充测试
- `tests/test_selection_schema.py` 已存在，确认覆盖新字段
- 添加指标筛选的集成测试
- 测试形态筛选（如果有）

#### 任务 10: 更新 API 文档
- `docs/api/api_document.md` 补充筛选接口详情
- 更新 PRD/ROADMAP 的 Phase 0 完成状态

## 验收标准

- [ ] 开发者可以每天盘后打开产品
- [ ] 使用指标筛选（如 RSI < 30）得到合理结果
- [ ] 点击结果能看到个股详情和图表标注
- [ ] 首页 4 卡片显示真实数据（无"暂无数据"）
- [ ] 所有测试通过（99+）

## 注意事项

1. **不要过度设计**：只做 Phase 0 必需的最小增强
2. **保持向后兼容**：新增字段不影响现有功能
3. **数据质量优先**：如果指标数据缺失，要明确标识
4. **不要提前做 Phase 1**：专注扫描引擎，不回 Toward 回测

---

**开始执行**: 使用 `superpowers:execute-plan` 按顺序完成任务
