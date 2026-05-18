# Phase 3 任务设计：P3-03 参数化指标筛选与订阅提醒

> Status: revised design input
> Last updated: 2026-04-23
> Role: design asset, not plan-of-record
> Active execution entry: [docs/milestones/m3/M3_P3-03_ALERT_ENGINE_PLAN.md](../m3/M3_P3-03_ALERT_ENGINE_PLAN.md)

## 目标

面向不具备代码能力的普通用户，提供“模板化 + 可调参数”的指标筛选能力，并允许把已保存筛选器订阅为盘后提醒。

用户应当能够：

- 从模板开始，而不是从空白公式开始
- 调整 `MACD`、`RSI`、`BOLL` 等指标参数
- 在全市场运行筛选并查看命中原因
- 保存筛选器并订阅为提醒

## 核心设计原则

- **普通用户优先**：不暴露脚本语言或公式编辑器
- **参数化而非脚本化**：支持“自定义参数集”，不支持“自定义公式语言”
- **单一 authored truth**：所有已保存定义都锚定到 `Saved Screener`
- **引擎可替换**：执行引擎可以从当前 adapter 切到 `vbtpro`，但不改变用户已保存的 definition
- **注册表驱动**：字段、参数、操作符、文案和支持矩阵统一由 `Registry` 输出

## Canonical Domain Model

### 1. `Saved Screener`

唯一 canonical truth source。

保存内容包括：

- `template_key`
- `template_version`
- `schema_version`
- `scope`
- `logic`
- `blocks`
- `params`
- `definition_hash`

### 2. `Alert Subscription`

只绑定 `Saved Screener` 的不可变版本。

负责：

- 调度频率
- 冷却窗口
- dedupe
- 启停
- 通知渠道

### 3. `Registry`

唯一字段目录，定义：

- 可用模板
- 可用指标
- 参数 schema
- 默认值
- UI metadata
- 允许的操作符/触发器
- 当前 adapter 支持矩阵

### 4. `Adapter`

执行层，负责 compile / execute。

当前默认可用：

- `SQL + TA-Lib`

未来可扩展：

- `vbtpro`

约束：

- 持久化层禁止存储引擎专有语义
- 不允许把 TA-Lib 函数名、SQL 片段或 `vbtpro` 表达式写入 canonical schema

## 用户使用方式

推荐的产品路径是：

1. 选择市场范围
2. 选择模板
3. 微调参数
4. 预览结果
5. 保存为 `Saved Screener`
6. 可选地创建 `Alert Subscription`

示例：

- `MACD 金叉`
  - 参数：`fast / slow / signal / direction`
- `RSI 超卖`
  - 参数：`period / threshold / operator`
- `BOLL 突破上轨`
  - 参数：`period / stddev / trigger`

## 数据模型建议

### Near-term persistence

优先复用现有保存筛选能力，逐步收敛到 canonical envelope：

- `selection_conditions`：兼容期内可承载 `Saved Screener`
- `screening_subscriptions`：新增，存提醒绑定
- `screening_runs`：新增，存执行历史
- `selection_results` 或增强版命中表：存 `Hit`
- `notifications`：继续复用，作为投递结果

### Compatibility / legacy

以下对象不再作为 M3 长期真相源：

- `attention.alert_conditions`
- `alert_conditions(rule_type + threshold)`
- free-form `selection_conditions.params`

它们只能作为迁移输入或兼容期 wrapper。

## 执行与扩展策略

- 默认只支持 `1d` 日线
- 默认只允许有限 `ALL / ANY` 结构和受控 clause 数量
- 普通模式隐藏复杂参数，高级模式暴露参数微调
- 同一 compiled definition 允许多个订阅共享执行结果
- 通知以“新增命中摘要”为默认形式，避免噪声

## Superseded Prototypes

以下方案已明确降级，不应再被解读为 M3 目标：

1. typed row model：
   - `condition_type / operator / threshold / pattern_name / notify_channels`
   - 定性：`prototype exploration`
2. 单一 JSONB `condition`：
   - 定性：`discarded prototype`
3. `alert_conditions(rule_type + threshold)`：
   - 定性：`legacy baseline / compatibility input`

## M3 设计验收口径

设计层只有在同时满足以下条件时才算稳定：

- canonical model 明确为 `Saved Screener + Alert Subscription + Registry + Adapter`
- 文档中不存在第二套 authored rule persistence
- 明确禁止用户公式语言、脚本表达式和引擎绑定 schema
- 明确写出 future `vbtpro` 只替换 adapter，不改变 authored schema
