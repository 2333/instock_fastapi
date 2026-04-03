# Phase 3 任务设计：P3-04 策略分享功能增强（评分/评论/收藏）

## 目标
将策略模板从"个人工具"升级为"社区资产"，支持评分、评论、收藏、排行榜。

## 设计原则
- **低门槛分享**：一键发布策略到公共库
- **质量管控**：点赞/评分排序，劣质策略下沉
- **防作弊**：同一用户限投一票，异常检测
- **可发现性**：分类浏览 + 搜索 + 排行榜

## 现状分析

### 已有基础
- 策略模板 CRUD（个人层面）
- 回测结果保存与对比
- 策略类型枚举（ma_crossover / rsi_oversold / buy_hold）

### 缺失能力
- 公共策略库（独立于个人账户）
- 社交互动（评分/评论/收藏）
- 策略质量指标（收益/夏普/回撤）
- 排行榜与推荐

## 数据模型扩展

### StrategyTemplate 增强
```python
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    # 原有字段...
    id: Mapped[int] = ...
    name: Mapped[str] = ...
    strategy_type: Mapped[str] = ...
    params: Mapped[dict] = ...
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None 表示官方/公共
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)  # 官方认证

    # 新增社交字段
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)  # 平均评分 0-5
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    backtest_count: Mapped[int] = mapped_column(Integer, default=0)  # 被回测次数
    view_count: Mapped[int] = mapped_column(Integer, default=0)  # 查看次数
    last_rating_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 质量标签
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)  # ["高收益", "低回撤", "适合牛市"]
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low/medium/high
    suitable_market: Mapped[str | None] = mapped_column(String(50), nullable=True)  # bull/bear/sideway
```

### StrategyRating（策略评分）
```python
class StrategyRating(Base):
    __tablename__ = "strategy_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('strategy_id', 'user_id', name='uq_strategy_user_rating'),)
```

### StrategyFavorite（策略收藏）
```python
class StrategyFavorite(Base):
    __tablename__ = "strategy_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('strategy_id', 'user_id', name='uq_strategy_user_favorite'),)
```

### StrategyComment（策略评论）
```python
class StrategyComment(Base):
    __tablename__ = "strategy_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 回复支持
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## 后端服务

### StrategySocialService
```python
class StrategySocialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def rate_strategy(self, strategy_id: int, user_id: int, rating: int, comment: str | None = None):
        # 创建或更新评分
        # 重新计算策略平均分
        # 更新 rating_count

    async def toggle_favorite(self, strategy_id: int, user_id: int) -> bool:
        # 收藏/取消收藏，返回是否已收藏
        # 更新 favorite_count

    async def add_comment(self, strategy_id: int, user_id: int, content: str, parent_id: int | None = None):
        # 添加评论，支持回复

    async def get_strategy_details(self, strategy_id: int, current_user_id: int | None = None):
        # 返回策略详情 + 评分/评论/收藏状态
        # 包含：average_rating, rating_count, favorite_count, comment_count
        # 当前用户是否已评分/收藏

    async def list_public_strategies(self, filters: dict, sort_by: str = "rating", limit: int = 20):
        # 公共策略库列表
        # 排序：rating / favorite_count / backtest_count / latest
        # 过滤：strategy_type / tags / risk_level
```

### 质量指标计算（异步任务）
```python
# app/jobs/tasks/strategy_quality.py
async def update_strategy_quality_metrics():
    """定期更新策略质量指标（每日）"""
    # 查询该策略所有回测结果
    # 计算：总收益、夏普比率、最大回撤、胜率
    # 更新 strategy.quality_score 字段
    # 根据指标自动打标签（如"高收益"=收益>50%，"低回撤"=最大回撤<10%）
```

## API 端点设计

```python
# app/api/routers/strategy_social_router.py
router = APIRouter(prefix="/api/v1/strategies", tags=["strategies-social"])

@router.get("/public")                      # 公共策略库列表
@router.get("/{strategy_id}/details")       # 策略详情（含社交数据）
@router.post("/{strategy_id}/rate")         # 评分
@router.post("/{strategy_id}/favorite")     # 收藏/取消
@router.get("/{strategy_id}/comments")      # 评论列表
@router.post("/{strategy_id}/comments")     # 发表评论
@router.delete("/comments/{comment_id}")    # 删除评论
@router.get("/my-favorites")                # 我的收藏
@router.get("/my-ratings")                  # 我的评分
```

## 前端组件

### StrategyCard（策略卡片）
```
web/src/components/StrategyCard.vue
- 展示：策略名称 + 类型 + 评分 stars + 收藏数 + 回测次数
- 操作：查看详情 / 复制到我的策略 / 评分 / 收藏
- 质量标签：badge 显示（高收益/低回撤等）
```

### StrategyDetailModal（策略详情弹窗）
```
web/src/components/StrategyDetailModal.vue
- 策略参数配置表单（只读/可编辑）
- 评分展示与输入
- 收藏按钮
- 评论列表与输入框
- "复制并回测"快捷按钮
```

### StrategyLeaderboard（排行榜）
```
web/src/components/StrategyLeaderboard.vue
- 榜单分类：总榜 / 近期热门 / 高收益榜 / 低回撤榜
- 展示前 20 名策略
- 点击查看详情
```

### 公共策略库页面
```
web/src/views/StrategyMarket.vue
- 搜索框 + 分类筛选 + 排序选项
- 策略卡片网格布局
- 侧边栏：策略类型/风险等级/市场条件过滤
```

## 集成点

### Backtest 页面
- 策略选择器增加"公共策略库"tab
- 策略卡片显示评分/收藏数
- "复制"按钮将策略复制到个人模板后自动跳转回测

### Dashboard
- 添加"热门策略"卡片（本周最多人回测的策略）

### 新建页面 StrategyMarket
- `/strategies` 路径，独立公共策略浏览页

## 冷启动策略
1. 预置 5-10 个官方策略（高质量，覆盖常见类型）
2. 鼓励早期用户分享：分享即送"创作者徽章"
3. 首次访问显示"新手指南"策略集

## 防作弊机制
- 同一用户对同一策略只能评分一次（可更新）
- 收藏无限制但去重计数
- 评论需登录，支持举报
- 回测次数按用户去重（防止刷量）

## 验收标准
- [ ] 策略评分/收藏/评论 CRUD 接口完成
- [ ] 策略详情页显示社交指标
- [ ] 公共策略列表页支持筛选/排序
- [ ] 策略卡片组件可复用（显示评分/收藏数）
- [ ] 用户可一键复制公共策略到个人模板
- [ ] 排行榜组件完成（4 种排序）
- [ ] 质量指标自动更新（每日任务）
- [ ] 官方预置策略数据迁移脚本

## 风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| 社区冷启动 | 无内容 | 预置官方策略 + 内部账号模拟 |
| 低质量策略泛滥 | 用户体验差 | 举报机制 + 管理员下架 + 排序权重包含质量分 |
| 刷榜作弊 | 排行榜失真 | 去重计数 + 异常行为检测（短时间内大量操作） |
| 版权争议 | 法律风险 | 用户发布即同意许可协议，支持举报下架 |

## 依赖项
- P3-01 用户行为数据（可选，用于推荐策略）
- 数据库：新增 3 张表（ratings/favorites/comments）
- 后台任务系统（Celery/Redis Queue）用于质量指标计算

## 估算
- 后端：8 小时（模型 + API + 服务 + 任务）
- 前端：6 小时（StrategyCard/DetailModal/Leaderboard/StrategyMarket 页面）
- 总计：**3.5 人日**

---

**状态**: 草案待评审
**创建时间**: 2026-04-03
**负责人**: TBD
