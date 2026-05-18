# Phase 3 实施任务：P3-03 参数化指标筛选与订阅提醒 - 实施方向

> Status: revised implementation input
> Last updated: 2026-04-23
> Role: implementation reference, not plan-of-record
> Active execution entry: [docs/milestones/m3/M3_P3-03_ALERT_ENGINE_PLAN.md](../m3/M3_P3-03_ALERT_ENGINE_PLAN.md)

## 实施目标

把 `P3-03` 从“单条阈值预警 CRUD”纠正为“参数化筛选 + 订阅提醒”的统一实现路径：

- 先建立 `Saved Screener` canonical envelope
- 再建立 `Registry`
- 再实现默认 adapter
- 最后接入 `Alert Subscription`、runner 和 `Notification`

## 实施分层

### 1. Authored Layer

持久化真相只允许：

- `Saved Screener`
- `Alert Subscription`

必须包含：

- `schema_version`
- `definition_version`
- `definition_hash`
- immutable snapshot 引用

### 2. Registry Layer

每个模板/指标都应注册：

- `key`
- `version`
- `param_schema`
- `default_params`
- `ui_schema`
- `supported_triggers`
- `capability_matrix`

### 3. Adapter Layer

统一接口建议：

- `compile(definition, registry_version) -> compiled_plan`
- `evaluate(compiled_plan, trade_date) -> run_result`

默认实现：

- `SQL + TA-Lib`

未来可替换实现：

- `vbtpro`

### 4. Execution History Layer

至少保留：

- `Run`
- `Hit`
- `Notification`

要求：

- 执行记录引用 definition snapshot
- 历史命中不因后续编辑而改变语义

## 推荐实施顺序

### Phase 1. Canonical contract 与 registry

- 定义 `Saved Screener` envelope
- 定义 `Registry` 元数据输出
- 冻结首批 `MACD / RSI / BOLL`
- 明确 compatibility strategy

### Phase 2. 手动筛选运行

- 手动运行 API
- `Selection` 结果预览
- compiled hash / execution grouping
- focused tests

### Phase 3. 订阅提醒

- `Alert Subscription`
- 盘后 runner
- dedupe / cooldown
- `Notification`

### Phase 4. 兼容与迁移

- 旧 `selection_conditions.params` 包装迁移
- 旧 `alert_conditions` 映射到 compatibility template
- 明确 `attention.alert_conditions` 只读兼容，不再扩展

## 必须避免的实现方向

- 不要把 `alert_conditions(rule_type + threshold)` 继续扩成主模型
- 不要再引入第二套 authored rule persistence
- 不要把 TA-Lib / SQL / `vbtpro` 语义直接写进 persisted schema
- 不要开放用户公式字符串、脚本表达式或原生 SQL

## 兼容策略

如共享环境已经落过窄版 `alert_conditions` migration，应采用“向 canonical model 迁移”的方式处理：

- 把旧行映射到 compatibility template
- 绑定到 `Saved Screener + Alert Subscription`
- 保留通知读路径兼容
- 不再新增以 `rule_type + threshold` 为核心的新 contract

## 实施完成标准

- 文档和实现都只有一个 authored truth source
- 手动筛选与订阅提醒共用同一套 registry 和 adapter
- 当前默认 adapter 可运行，future `vbtpro` 入口已被边界设计预留
- 兼容对象被明确降级并写入迁移说明
