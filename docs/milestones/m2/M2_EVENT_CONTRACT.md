# M2 Event Contract

> Status: frozen for kickoff
> Scope: first-wave authenticated user analytics only

## 设计原则

- 最小可用：只做当前 milestone 必需的 6 类事件
- 白名单约束：事件名、字段名、字段类型都必须受控
- 隐私边界优先：不记录敏感或高风险字段
- 可查询：事件结构要能支持 SQL 聚合与验收抽样
- 可回滚：不依赖消息队列、异步消费或额外基础设施

## 首波边界

- 仅记录认证用户事件，`user_id` 必填
- 不记录访客 / session / device 级事件
- 不记录 raw IP、user agent、email、password、token、refresh token
- 不记录自由文本备注、搜索原文、未受控 query blob
- 不记录任意 shape 的 `event_data`

## 持久化模型

表名: `user_events`

建议字段:

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `integer` PK | 自增主键 |
| `user_id` | `integer` | 认证用户 ID |
| `event_type` | `varchar(50)` | 事件类型白名单 |
| `event_version` | `integer` | 当前固定为 `1` |
| `page` | `varchar(120)` | 事件发生页面 |
| `referrer` | `varchar(255)` nullable | 来源页面 |
| `event_data` | `jsonb` nullable | 白名单字段组成的受控 payload |
| `created_at` | `timestamp` | 服务端写入时间 |

建议索引:

- `ix_user_events_user_created` on `(user_id, created_at)`
- `ix_user_events_event_type_created` on `(event_type, created_at)`

## API 契约

端点: `POST /api/v1/events/track`

认证:

- 首波必须登录
- 未登录请求返回 `401`

限流:

- `100 req / minute / user`
- 以服务端时间窗口计算
- 命中限流返回 `429`

成功语义:

- 持久化成功: `202 Accepted`
- 持久化失败但已被服务端吞掉: `202 Accepted`
- 非法 payload: `422`

建议响应体:

```json
{
  "accepted": true,
  "persisted": true
}
```

或

```json
{
  "accepted": true,
  "persisted": false
}
```

## 顶层请求结构

```json
{
  "event_type": "filter_run",
  "page": "/selection",
  "referrer": "/",
  "event_data": {
    "filter_keys": ["market", "priceMin", "pattern"],
    "filter_count": 3,
    "market": "main_board",
    "result_count": 12,
    "trade_date": "20240102"
  }
}
```

顶层校验规则:

- `event_type` 必须属于白名单
- `page` 必填，最大长度 `120`
- `referrer` 可空，最大长度 `255`
- `event_data` 仅允许当前事件白名单字段
- 所有字符串字段必须裁剪空白并限制长度
- 不允许嵌套自由对象或自由数组

## 事件白名单

### `page_view`

触发时机:

- 进入 5 个核心页面时发送一次

`event_data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| `route_name` | `string` | 路由名 |

### `dashboard_card_click`

触发时机:

- 点击 Dashboard 四张工作台卡片入口时发送

`event_data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| `card` | `string` | 卡片标识 |
| `target_path` | `string` | 目标路径 |

### `filter_run`

触发时机:

- Selection 页面执行筛选成功后发送

`event_data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| `filter_keys` | `string[]` | 已启用筛选键列表 |
| `filter_count` | `integer` | 启用筛选条件数 |
| `market` | `string` nullable | 当前市场范围 |
| `result_count` | `integer` | 命中数量 |
| `trade_date` | `string` nullable | 返回的交易日 |

### `backtest_run`

触发时机:

- Backtest 页面发起回测请求时发送

`event_data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| `strategy` | `string` | 回测模板 |
| `stock_code` | `string` | 股票代码 |
| `period` | `string` | 页面上的区间选项 |
| `start_date` | `string` | 实际请求开始日期 |
| `end_date` | `string` | 实际请求结束日期 |
| `param_keys` | `string[]` | 本次策略参数键 |

### `pattern_view`

触发时机:

- StockDetail 页面打开单个形态详情时发送

`event_data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| `stock_code` | `string` | 股票代码 |
| `pattern_name` | `string` | 形态名 |
| `pattern_type` | `string` | 形态方向类型 |
| `confidence` | `integer` | 置信度 |
| `trade_date` | `string` | 形态发生日期 |

### `attention_action`

触发时机:

- StockDetail / Attention 页面增删改关注时发送

`event_data`:

| 字段 | 类型 | 说明 |
|------|------|------|
| `action` | `string` | `add` / `remove` / `update` |
| `stock_code` | `string` | 股票代码 |
| `source` | `string` | `stock_detail` / `attention_page` |

## 禁止采集字段

- `password`
- `email`
- `token`
- `refresh_token`
- `raw_ip`
- `user_agent`
- `notes`
- 任意自由文本搜索词
- 任意未受控 query string / request body 原文

## 验收 SQL 样本

```sql
SELECT user_id, event_type, page, event_data, created_at
FROM user_events
ORDER BY created_at DESC
LIMIT 20;
```

```sql
SELECT event_type, COUNT(*) AS total
FROM user_events
GROUP BY event_type
ORDER BY total DESC;
```
