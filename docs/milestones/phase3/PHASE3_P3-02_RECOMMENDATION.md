# Phase 3 任务设计：P3-02 智能推荐服务

## 目标
基于用户行为历史，提供个性化推荐（筛选条件、策略模板、关注股票）。

## 设计原则
- **冷启动友好**：无历史数据时使用全局热门推荐
- **可解释性**：推荐结果附带理由（"因为你关注了 X"）
- **轻量实现**：初期采用规则引擎 + 简单协同过滤，避免复杂 ML
- **可配置**：用户可关闭或调整推荐偏好

## 数据源

### 已收集事件（P3-01）
- `page_view`：页面访问（Dashboard/Selection/Backtest/StockDetail/Attention）
- `filter_run`：筛选执行（条件 + 结果数 + 耗时）
- `backtest_run`：回测执行（策略 + 参数 + 股票）
- `pattern_view`：形态查看（名称 + 置信度 + 日期）
- `attention_action`：关注操作（add/remove + 代码 + 来源）

### 衍生特征
- 用户筛选条件偏好（price/change/macd/rsi/pattern/fund 类别使用频次）
- 用户关注股票行业分布
- 回测策略类型偏好（buy_hold/ma_crossover/rsi_oversold）
- 形态偏好（锤子线/吞没/头肩等）
- 活跃时段（小时分布）

## 推荐类型

### 1. 筛选条件推荐
**场景**：用户在 Selection 页面，右侧"推荐条件"区显示
**逻辑**：
- 基于用户历史 `filter_run` 事件，统计最常使用的条件组合
- 协同过滤："与你相似的用户还使用了..."
- 全局热门：全站最常用条件（降权展示）
**输出**：
```json
{
  "type": "filter_recommendation",
  "title": "你常用的条件",
  "items": [
    { "name": "价格 + MACD", "category": "price", "usage_count": 12, "reason": "你使用了 12 次" },
    { "name": "RSI 超卖", "category": "rsi", "usage_count": 8, "reason": "与你相似的用户常用" }
  ]
}
```

### 2. 策略模板推荐
**场景**：用户在 Backtest 页面，策略选择器顶部显示
**逻辑**：
- 基于用户 `backtest_run` 历史，推荐最常测试的策略
- 基于用户关注列表，推荐适合该股票类型的策略（如波动大的用 RSI，趋势明显的用 MA）
**输出**：
```json
{
  "type": "strategy_recommendation",
  "title": "根据你的回测历史推荐",
  "items": [
    { "name": "MA 交叉", "strategy": "ma_crossover", "reason": "你已使用 5 次" },
    { "name": "RSI 超卖", "strategy": "rsi_oversold", "reason": "适合当前关注的股票" }
  ]
}
```

### 3. 关注股票推荐
**场景**：Dashboard"我的关注"区显示"你可能还想关注"
**逻辑**：
- 基于用户已有关注列表，查找同行业、同概念股票
- 基于 `pattern_view` 历史，推荐高置信度形态出现的股票
- 基于 `filter_run` 结果，推荐频繁命中的股票
**输出**：
```json
{
  "type": "stock_recommendation",
  "title": "你可能还想关注",
  "items": [
    { "code": "000002", "name": "万科 A", "reason": "与平安银行同属金融板块" },
    { "code": "600519", "name": "贵州茅台", "reason": "近期出现锤子线形态" }
  ]
}
```

## 技术实现

### 后端服务
```
app/services/recommendation_service.py
- get_recommendations(user_id: int, limit: int = 5) -> list[Recommendation]
- 实现：
  1. 查询 user_events 表，过滤最近 30 天事件
  2. 统计用户偏好（条件类别/策略类型/形态类型）
  3. 查询相似用户（Jaccard 相似度）或全局热门
  4. 组装推荐结果（含理由）
- 缓存：Redis 缓存 1 小时（key: rec:{user_id}）
```

### 前端组件
```
web/src/components/RecommendationCard.vue
- 展示推荐列表（图标 + 标题 + 理由）
- 点击应用（加载条件 / 选择策略 / 添加关注）
-  dismiss 功能（用户可关闭不感兴趣的推荐）
```

### API 端点
```python
# app/api/routers/recommendation_router.py
@router.get("/recommendations")
async def get_recommendations(
    category: str = "all",  # filter / strategy / stock
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecommendationService(db)
    items = await service.get_recommendations(user_id=current_user.id, category=category, limit=limit)
    return {"data": items}
```

### 集成点
- Dashboard：右侧栏显示"你可能还想关注"
- Selection：条件选择器下方显示"你常用的条件"
- Backtest：策略选择器上方显示"根据你的回测历史推荐"

## 验收标准
- [ ] 推荐服务可返回至少 3 种类型推荐（筛选/策略/股票）
- [ ] 推荐结果附带可解释理由
- [ ] 冷启动用户看到全局热门推荐
- [ ] 推荐可 dismiss，且尊重用户偏好（记录 dismiss 事件）
- [ ] 前端组件集成到 3 个核心页面
- [ ] 响应时间 < 200ms（含缓存）

## 风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| 推荐不相关 | 用户体验差 | 提供 dismiss 反馈，快速迭代算法 |
| 数据不足 | 冷启动效果差 | 全局热门兜底，渐进式个性化 |
| 性能瓶颈 | 响应慢 | Redis 缓存 + 异步计算（离线生成） |
| 隐私担忧 | 用户反感 | 本地化处理，不跨用户共享明细 |

## 依赖项
- P3-01 用户行为数据就绪
- Redis（可选，用于缓存）
- 至少 2 周用户行为数据积累（冷启动期用全局热门）

## 估算
- 后端服务：4 小时（查询 + 算法 + API）
- 前端组件：3 小时（3 页面集成）
- 总计：**1.5 人日**

---

**状态**: 草案待评审
**创建时间**: 2026-04-03
**负责人**: TBD
