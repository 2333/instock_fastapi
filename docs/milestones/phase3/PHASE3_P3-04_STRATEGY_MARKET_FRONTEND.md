# Phase 3 实施任务：P3-04 策略分享社交 - 前端组件开发

## 任务目标
完成策略社交功能的前端实现：公共策略库页面 + 策略卡片 + 详情弹窗 + 排行榜。

## 实施范围（本次）

### 1. StrategyCard 组件
**文件**: `web/src/components/StrategyCard.vue`
**功能**:
- 展示策略基本信息（名称 + 描述）
- 展示社交指标（评分 stars + 评分人数 + 收藏数 + 评论数 + 回测次数）
- 展示质量标签（tags badges）
- 操作按钮：查看详情 / 复制到我的策略 / 评分 / 收藏
- 风险等级标识（颜色区分 low/medium/high）

### 2. StrategyMarket 页面
**文件**: `web/src/views/StrategyMarket.vue`
**功能**:
- 搜索框 + 分类筛选（策略类型 / 风险等级 / 标签）
- 排序选项（综合评分 / 收藏最多 / 回测最多 / 最新）
- 策略卡片网格布局（响应式）
- 分页加载（无限滚动或分页器）
- 侧边栏过滤器（类型 / 风险 / 市场条件）

### 3. StrategyDetailModal 弹窗
**文件**: `web/src/components/StrategyDetailModal.vue`
**功能**:
- 策略参数配置表单（只读 + 可编辑模式）
- 评分展示与输入（1-5 星 + 评论）
- 收藏按钮（heart 图标 + 计数）
- 评论列表（嵌套回复 + 发表框）
- "复制并回测"快捷按钮
- 质量指标展示（收益/夏普/回撤，如已计算）

### 4. StrategyLeaderboard 排行榜
**文件**: `web/src/components/StrategyLeaderboard.vue`
**功能**:
- 榜单分类：总榜 / 近期热门 / 高收益榜 / 低回撤榜
- 展示前 20 名策略（排名 + 名称 + 评分 + 收藏数）
- 点击条目查看详情
- 定期更新（每小时/每天）

### 5. Backtest 页面集成
**文件**: `web/src/views/Backtest.vue`
**改动**:
- 策略选择器增加"公共策略库"tab
- 策略卡片增加"复制"按钮（复制到我的策略模板）
- 点击卡片可打开 StrategyDetailModal

### 6. Dashboard 集成
**文件**: `web/src/views/Dashboard.vue`
**改动**:
- 添加"热门策略"卡片（本周最多人回测的策略）
- 展示策略名称 + 评分 + 回测次数

## 验收标准
- [ ] StrategyCard 组件可复用，显示完整社交指标
- [ ] StrategyMarket 页面支持筛选/排序/分页
- [ ] StrategyDetailModal 支持评分/收藏/评论完整交互
- [ ] StrategyLeaderboard 排行榜 4 种排序就绪
- [ ] Backtest 页面可访问公共策略库并复制策略
- [ ] Dashboard 显示热门策略卡片
- [ ] 类型检查通过（vue-tsc）
- [ ] 与后端 API 对接成功（Mock 数据可先演示）

## 技术决策

### 状态管理
- 使用 Pinia stores（如已存在）或本地 ref + 刷新
- 用户评分/收藏状态实时更新

### API 对接
- 复用 `api/index.ts` 添加 strategySocialApi
- 端点：`/api/v1/strategies/public` / `details` / `rate` / `favorite` / `comments`

### 样式规范
- 遵循现有 Design System（颜色/间距/圆角）
- 评分 stars 使用 SVG 或 emoji
- 标签 badges 用小号字体 + 圆角背景

## 文件清单

### 新增
- `web/src/components/StrategyCard.vue`
- `web/src/components/StrategyDetailModal.vue`
- `web/src/components/StrategyLeaderboard.vue`
- `web/src/views/StrategyMarket.vue`

### 修改
- `web/src/views/Backtest.vue` - 集成公共策略库 tab
- `web/src/views/Dashboard.vue` - 添加热门策略卡片
- `web/src/api/index.ts` - 导出 strategySocialApi

## 估算
- StrategyCard：1.5 小时
- StrategyMarket 页面：3 小时
- StrategyDetailModal：2.5 小时
- StrategyLeaderboard：1.5 小时
- Backtest 集成：1 小时
- Dashboard 集成：0.5 小时
- **总计：10 小时 ≈ 1.25 人日**

---

**状态**: 待实施
**优先级**: P0（Phase 3 社交功能闭环）
**依赖**: 后端 API 已就绪（P3-04 后端完成）
