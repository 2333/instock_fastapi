# InStock 智能股票分析平台 - API接口文档

## 概述

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: 无（可扩展JWT）
- **数据格式**: JSON
- **字符编码**: UTF-8

---

## 1. 股票接口 (Stock)

### 1.1 获取股票列表

**GET** `/stocks`

获取A股股票列表，支持分页和日期筛选。

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| date | string | 否 | 最新日期 | 交易日期(YYYYMMDD) |
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 50 | 每页数量(1-200) |

**响应示例**:

```json
[
  {
    "date": "20260213",
    "code": "300812.SZSE",
    "name": "易天股份",
    "new_price": 41.76,
    "change_rate": 21.64,
    "volume": 296994,
    "deal_amount": 1172478075.3,
    "industry": "电子",
    "open": 34.52,
    "high": 41.76,
    "low": 34.23,
    "close": 41.76,
    "pre_close": 34.33
  }
]
```

### 1.2 获取股票详情

**GET** `/stocks/{code}`

获取指定股票的详细信息，包括基本信息和K线数据。

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | string | 股票代码(如: 300812) |

**查询参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| start_date | string | 否 | 开始日期(YYYY-MM-DD) |
| end_date | string | 否 | 结束日期(YYYY-MM-DD) |

**响应示例**:

```json
{
  "code": "300812.SZSE",
  "name": "易天股份",
  "industry": "电子",
  "area": "广东",
  "bars": [
    {
      "trade_date": "20260213",
      "open": 34.52,
      "high": 41.76,
      "low": 34.23,
      "close": 41.76,
      "vol": 296994,
      "amount": 1172478075.3,
      "pct_chg": 21.64
    }
  ]
}
```

---

## 2. ETF接口

### 2.1 获取ETF列表

**GET** `/etf`

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| date | string | 否 | 最新日期 | 交易日期 |
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 50 | 每页数量 |

### 2.2 获取ETF详情

**GET** `/etf/{code}`

---

## 3. 技术指标接口 (Indicator)

### 3.1 获取技术指标

**GET** `/indicators`

获取指定股票的技术指标数据。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| code | string | 是 | 股票代码 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| limit | int | 否 | 返回条数(默认100) |

**响应示例**:

```json
[
  {
    "ts_code": "300812.SZSE",
    "trade_date": "20260213",
    "indicator_name": "MACD",
    "indicator_value": 0.5234
  },
  {
    "ts_code": "300812.SZSE",
    "trade_date": "20260213",
    "indicator_name": "RSI_14",
    "indicator_value": 65.32
  }
]
```

### 3.2 获取最新指标

**GET** `/indicators/latest`

获取指定股票的最新技术指标。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| code | string | 是 | 股票代码 |

---

## 4. K线形态接口 (Pattern)

### 4.1 获取形态识别结果

**GET** `/patterns`

获取指定股票的K线形态识别结果。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| code | string | 是 | 股票代码 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| limit | int | 否 | 返回条数 |

**响应示例**:

```json
[
  {
    "ts_code": "300812.SZSE",
    "trade_date": "20260213",
    "pattern_name": "MORNING_STAR",
    "pattern_type": "reversal",
    "confidence": 75.0,
    "stock_name": "易天股份"
  }
]
```

### 4.2 获取今日形态

**GET** `/patterns/today`

获取当日出现K线形态的所有股票。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| signal | string | 否 | 信号类型(buy/sell/hold) |
| limit | int | 否 | 返回条数 |

**形态类型说明**:

| 类型 | 名称 | 说明 |
|------|------|------|
| reversal | 反转形态 | 晨星、暮星、锤头等 |
| trend | 趋势形态 | 连续上涨、连续下跌等 |
| breakout | 突破形态 | 突破新高、突破新低等 |

---

## 5. 策略选股接口 (Strategy)

### 5.1 获取策略列表

**GET** `/strategies`

获取所有可用的选股策略。

**响应示例**:

```json
[
  {
    "name": "enter",
    "display_name": "放量上涨",
    "description": "成交量放大的上涨股票"
  },
  {
    "name": "keep_increasing",
    "display_name": "均线多头",
    "description": "均线多头排列的股票"
  }
]
```

**策略说明**:

| 策略名 | 显示名 | 描述 |
|--------|--------|------|
| enter | 放量上涨 | 成交量放大的上涨股票 |
| keep_increasing | 均线多头 | 均线多头排列的股票 |
| parking_apron | 停机坪 | 涨停后调整的股票 |
| backtrace_ma250 | 回踩年线 | 回踩250日均线的股票 |
| breakthrough_platform | 突破平台 | 突破整理平台的股票 |
| turtle_trade | 海龟交易法则 | 海龟交易策略选股 |
| high_tight_flag | 高而窄的旗形 | 高而窄的旗形形态 |
| climax_limitdown | 放量跌停 | 放量跌停的股票 |
| low_backtrace_increase | 无大幅回撤 | 60日内无大幅回撤的股票 |
| low_atr | 低ATR成长 | 低波动率高成长股票 |

### 5.2 运行策略

**POST** `/strategies/run`

运行指定的选股策略。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| strategy_name | string | 是 | 策略名称 |
| date | string | 否 | 执行日期 |

**响应示例**:

```json
{
  "status": "success",
  "strategy": "enter",
  "count": 25
}
```

### 5.3 获取策略结果

**GET** `/strategies/results`

获取策略选股结果。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| strategy_name | string | 否 | 策略名称(不指定返回全部) |
| date | string | 否 | 交易日期 |
| limit | int | 否 | 返回条数 |

**响应示例**:

```json
[
  {
    "id": 76,
    "date": "20260213",
    "strategy_name": "default",
    "code": "603090",
    "name": "宏盛股份",
    "score": 70.0,
    "signal": "buy",
    "new_price": 82.9,
    "change_rate": 12.94
  }
]
```

---

## 6. 回测接口 (Backtest)

### 6.1 运行回测

**POST** `/backtest`

运行策略回测。

**请求参数**:

```json
{
  "strategy": "turtle_trade",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "initial_capital": 100000,
  "code": "000001"
}
```

**响应示例**:

```json
{
  "backtest_id": "bt_20260215073000",
  "total_return": 0.25,
  "annual_return": 0.28,
  "max_drawdown": 0.12,
  "sharpe_ratio": 1.85,
  "win_rate": 0.65,
  "total_trades": 45
}
```

### 6.2 获取回测结果

**GET** `/backtest/{backtest_id}`

获取指定回测的详细结果。

---

## 7. 资金流向接口 (Fund Flow)

### 7.1 获取个股资金流向

**GET** `/fund-flow/{code}`

获取指定股票的资金流向数据。

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| days | int | 否 | 5 | 查询天数(1-30) |

**响应示例**:

```json
[
  {
    "ts_code": "300812.SZSE",
    "trade_date": "20260213",
    "net_amount_main": 15000000,
    "net_amount_hf": 8000000,
    "net_amount_zz": 7000000,
    "net_amount_dt": -2000000,
    "net_amount_xd": -3000000
  }
]
```

### 7.2 获取行业资金流向

**GET** `/fund-flow/sector/industry`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| date | string | 否 | 交易日期 |
| limit | int | 否 | 返回条数 |

### 7.3 获取概念资金流向

**GET** `/fund-flow/sector/concept`

---

## 8. 关注列表接口 (Attention)

### 8.1 获取关注列表

**GET** `/attention`

获取用户关注的股票列表。

### 8.2 添加关注

**POST** `/attention`

**请求体**:

```json
{
  "code": "300812"
}
```

### 8.3 取消关注

**DELETE** `/attention/{code}`

---

## 9. 综合选股接口 (Selection)

### 9.1 获取选股条件

**GET** `/selection/conditions`

获取可用的选股条件列表。

### 9.2 运行综合选股

**POST** `/selection`

根据多个条件进行综合选股。

**请求体**:

```json
{
  "price_min": 5,
  "price_max": 100,
  "pe_max": 30,
  "market_cap_min": 50,
  "change_min": -5,
  "change_max": 10
}
```

### 9.3 获取选股历史

**GET** `/selection/history`

---

## 错误响应

所有接口在出错时返回统一格式:

```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "错误描述",
  "timestamp": "2026-02-15T07:00:00"
}
```

**常见错误码**:

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| VALIDATION_ERROR | 400 | 参数验证失败 |
| NOT_FOUND | 404 | 资源不存在 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 健康检查

**GET** `/health`

检查服务状态。

**响应**:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-15T07:00:00"
}
```
