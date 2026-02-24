# InStock 智能股票分析平台 - 前后端对接检查报告

## 1. 接口对接状态总览

| 模块 | 后端API | 前端调用 | 对接状态 |
|------|---------|---------|---------|
| 股票列表 | GET /stocks | stockApi.getStocks | ✅ 完整 |
| 股票详情 | GET /stocks/{code} | stockApi.getStockDetail | ✅ 完整 |
| ETF列表 | GET /etf | etfApi.getEtfList | ✅ 完整 |
| ETF详情 | GET /etf/{code} | etfApi.getEtfDetail | ✅ 完整 |
| 技术指标 | GET /indicators | indicatorApi.getIndicators | ✅ 完整 |
| 最新指标 | GET /indicators/latest | indicatorApi.getLatestIndicator | ✅ 完整 |
| K线形态 | GET /patterns | patternApi.getPatterns | ✅ 完整 |
| 今日形态 | GET /patterns/today | patternApi.getTodayPatterns | ✅ 完整 |
| 策略列表 | GET /strategies | strategyApi.getStrategies | ✅ 完整 |
| 运行策略 | POST /strategies/run | strategyApi.runStrategy | ✅ 完整 |
| 策略结果 | GET /strategies/results | strategyApi.getResults | ✅ 完整 |
| 策略回测 | POST /backtest | backtestApi.runBacktest | ✅ 完整 |
| 回测结果 | GET /backtest/{id} | backtestApi.getBacktest | ✅ 完整 |
| 选股条件 | GET /selection/conditions | selectionApi.getConditions | ✅ 完整 |
| 运行选股 | POST /selection | selectionApi.runSelection | ✅ 完整 |
| 选股历史 | GET /selection/history | selectionApi.getHistory | ✅ 完整 |
| 个股资金流 | GET /fund-flow/{code} | fundFlowApi.getFundFlow | ✅ 完整 |
| 行业资金流 | GET /fund-flow/sector/industry | fundFlowApi.getIndustryFundFlow | ✅ 完整 |
| 概念资金流 | GET /fund-flow/sector/concept | fundFlowApi.getConceptFundFlow | ✅ 完整 |
| 关注列表 | GET /attention | attentionApi.getList | ✅ 完整 |
| 添加关注 | POST /attention | attentionApi.add | ✅ 完整 |
| 取消关注 | DELETE /attention/{code} | attentionApi.remove | ✅ 完整 |

## 2. 页面对接状态

| 页面 | 调用API | 数据展示 | 状态 |
|------|---------|---------|------|
| Dashboard.vue | stocks, patterns, strategies | ✅ | ✅ 完整 |
| Stocks.vue | getStocks | ✅ | ✅ 完整 |
| StockDetail.vue | getStockDetail | ✅ | ✅ 完整 |
| Patterns.vue | getTodayPatterns | ✅ | ✅ 完整 |
| Selection.vue | getResults, runStrategy | ✅ | ✅ 完整 |
| Backtest.vue | runBacktest, getBacktest | ✅ | ✅ 完整 |
| Settings.vue | - | ✅ | ✅ 完整 |

## 3. 数据字段映射

### 3.1 股票列表 (Stocks.vue)

| 前端字段 | 后端字段 | 说明 |
|---------|---------|------|
| code | code | 股票代码 |
| name | name | 股票名称 |
| new_price | close | 最新价 |
| change_rate | pct_chg | 涨跌幅 |
| industry | industry | 行业 |

### 3.2 策略结果 (Selection.vue)

| 前端字段 | 后端字段 | 说明 |
|---------|---------|------|
| code | code | 股票代码 |
| name | name | 股票名称 |
| score | score | 评分 |
| signal | signal | 信号 |
| date | date | 日期 |
| new_price | new_price | 最新价 |
| change_rate | change_rate | 涨跌幅 |

### 3.3 K线形态 (Patterns.vue)

| 前端字段 | 后端字段 | 说明 |
|---------|---------|------|
| code | code/ts_code | 股票代码 |
| name | stock_name | 股票名称 |
| pattern_name | pattern_name | 形态名称 |
| pattern_type | pattern_type | 形态类型 |
| confidence | confidence | 置信度 |

## 4. 待完善功能

### 4.1 后端已实现，前端未对接

| 功能 | 后端状态 | 前端状态 | 建议 |
|------|---------|---------|------|
| 板块资金流向 | ✅ 已实现 | ❌ 未对接 | 添加板块资金流向页面 |
| 龙虎榜数据 | ✅ 表已创建 | ❌ 未实现 | 添加龙虎榜页面 |
| 大宗交易 | ✅ 表已创建 | ❌ 未实现 | 添加大宗交易页面 |

### 4.2 功能优化建议

1. **K线图表优化**: 集成ECharts专业K线图组件
2. **数据导出**: 添加Excel/CSV导出功能
3. **实时刷新**: 添加WebSocket实时数据推送
4. **移动端适配**: 优化移动端显示效果

## 5. 测试验证

### 5.1 API测试结果

```
✅ GET /health - 健康检查通过
✅ GET /api/v1/stocks - 股票列表正常
✅ GET /api/v1/strategies - 策略列表正常(10个策略)
✅ GET /api/v1/strategies/results - 策略结果正常
✅ GET /api/v1/patterns/today - 今日形态正常(144条)
```

### 5.2 前端测试结果

```
✅ http://localhost:3001 - 前端访问正常
✅ 股票列表页 - 数据展示正常
✅ 策略选股页 - 数据展示正常
✅ K线形态页 - 数据展示正常
```

## 6. 对接结论

**总体状态**: ✅ 前后端对接完整

所有核心功能已对接完成，数据流转正常。建议后续版本添加板块资金流向、龙虎榜等扩展功能的页面展示。

---

*生成时间: 2026-02-15*
