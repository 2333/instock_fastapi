# Phase 3 实施任务：P3-04 策略分享社交 - 后端基础实现

## 任务目标
完成策略社交功能的后端基础：模型 + API + 服务层。

## 实施范围（本次）

### 1. 数据库模型（3 张新表）
- `StrategyRating` - 策略评分（1-5 星，用户去重）
- `StrategyFavorite` - 策略收藏（用户去重）
- `StrategyComment` - 策略评论（支持回复）

### 2. Strategy 模型增强
新增字段：
- `is_public` - 是否公开（默认 False）
- `is_official` - 官方认证（默认 False）
- `rating` - 平均评分（Numeric 3,2，默认 0.0）
- `rating_count` - 评分人数（Integer，默认 0）
- `favorite_count` - 收藏数（Integer，默认 0）
- `comment_count` - 评论数（Integer，默认 0）
- `backtest_count` - 被回测次数（Integer，默认 0）
- `view_count` - 查看次数（Integer，默认 0）
- `tags` - 质量标签（JSONB 数组）
- `risk_level` - 风险等级（low/medium/high）
- `suitable_market` - 适用市场（bull/bear/sideway）

### 3. API 端点
**策略社交端点**（/api/v1/strategies）：
- `GET /public` - 公共策略库列表（支持筛选/排序）
- `GET /{id}/details` - 策略详情（含社交数据）
- `POST /{id}/rate` - 评分
- `POST /{id}/favorite` - 收藏/取消
- `GET /{id}/comments` - 评论列表
- `POST /{id}/comments` - 发表评论
- `DELETE /comments/{comment_id}` - 删除评论
- `GET /my-favorites` - 我的收藏
- `GET /my-ratings` - 我的评分

### 4. 业务服务
- `StrategySocialService`：
  - `rate_strategy()` - 评分（更新平均分）
  - `toggle_favorite()` - 收藏/取消
  - `add_comment()` - 发表评论
  - `get_strategy_details()` - 详情（社交指标 + 用户状态）
  - `list_public_strategies()` - 公共策略列表（筛选/排序）

### 5. 质量指标计算框架
- 预留 `update_strategy_quality_metrics()` 任务框架
- 后续可接入：总收益、夏普比率、最大回撤、胜率计算

## 验收标准
- [ ] 3 张新表模型可通过 `Base.metadata.create_all` 自动建表
- [ ] Strategy 模型新增字段正确迁移（无数据丢失风险）
- [ ] 9 个策略社交 API 端点可用（含认证）
- [ ] 评分时自动更新 strategy.rating 和 rating_count
- [ ] 收藏/评论计数自动更新
- [ ] 公共策略列表支持按 rating/favorite_count/backtest_count 排序
- [ ] 测试无回归（131 → 131+）

## 技术决策

### 评分去重
```python
# 使用 UniqueConstraint 保证同一用户对同一策略只能评一次分
__table_args__ = (UniqueConstraint('strategy_id', 'user_id', name='uq_strategy_user_rating'),)
```

### 收藏去重
```python
__table_args__ = (UniqueConstraint('strategy_id', 'user_id', name='uq_strategy_user_favorite'),)
```

### 评论层级
支持回复：通过 `parent_id` 实现嵌套评论（前端递归渲染）。

### 公共策略标识
- `is_public=True`：用户主动公开
- `is_official=True`：官方预置策略（不显示用户信息）

## 文件清单

### 新增
- `app/models/strategy_social_models.py` - 3 张社交表模型
- `app/schemas/strategy_social_schema.py` - Pydantic schemas
- `app/services/strategy_social_service.py` - 社交业务服务
- `app/api/routers/strategy_social_router.py` - 策略社交 API

### 修改
- `app/models/strategy_model.py` - 增强 Strategy 模型（新增字段）
- `app/models/__init__.py` - 导出新模型
- `app/api/routers/__init__.py` - 注册新路由

## 估算
- 模型修改/新增：1.5 小时
- Schemas + Service：2 小时
- API 端点：2 小时
- 测试验证：1 小时
- **总计：6.5 小时**

---

**状态**: 待实施
**优先级**: P0（Phase 3 核心社交功能）
**依赖**: 无（Strategy 表已存在）
