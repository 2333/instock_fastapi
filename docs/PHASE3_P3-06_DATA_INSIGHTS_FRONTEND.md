# Phase 3 实施任务：P3-06 数据洞察报告系统 - 前端集成

## 任务目标
完成数据洞察报告服务的前端实现：报告列表 + 详情 + 偏好设置 + Dashboard 卡片。

## 实施范围（本次）

### 1. ReportsPage 页面
**文件**: `web/src/views/Reports.vue`
**功能**:
- 报告列表展示（卡片/列表视图切换）
- 状态筛选（已生成 / 生成中 / 失败）
- 时间范围筛选（近 7 天 / 30 天 / 90 天）
- 报告类型筛选（日报 / 周报 / 月报）
- 点击查看报告详情
- 手动触发报告生成按钮
- 报告偏好设置入口

### 2. ReportDetail 页面
**文件**: `web/src/views/ReportDetail.vue`
**功能**:
- 报告元信息（标题 / 类型 / 生成时间 / 数据日期范围）
- 关键指标卡片（总览数值 + 环比）
- 图表区域：
  - 账户净值曲线（ equities 图表复用）
  - 行业分布饼图（ECharts pie）
  - 收益热力图（ECharts heatmap，股票收益矩阵）
  - 交易统计柱状图
- 报告内容 HTML 渲染（后端生成的 HTML）
- 导出 PDF 按钮（浏览器打印）

### 3. ReportPreferences 页面
**文件**: `web/src/views/ReportPreferences.vue`
**功能**:
- 报告类型开关（日报 / 周报 / 月报）
- 接收邮箱设置
- 自定义指标选择（多选框）
- 保存偏好

### 4. Dashboard 集成
**文件**: `web/src/views/Dashboard.vue`
**改动**:
- 添加"最新报告"卡片（展示最近生成的 3 份报告）
- 快速跳转到报告详情

### 5. API 扩展
**文件**: `web/src/api/index.ts`
**端点**:
- GET `/reports` - 列表
- GET `/reports/{id}` - 详情
- POST `/reports/generate` - 手动生成
- GET `/reports/preferences` - 获取偏好
- PUT `/reports/preferences` - 更新偏好

## 验收标准
- [ ] ReportsPage 可列出历史报告
- [ ] ReportDetail 正确渲染 HTML + 图表
- [ ] ReportPreferences 可保存偏好
- [ ] Dashboard 报告卡片展示最近报告
- [ ] 类型检查通过（vue-tsc）
- [ ] 与后端 API 对接成功

## 技术决策

### HTML 渲染
使用 `v-html` 渲染后端生成的报告 HTML 内容（已包含样式）。

### 图表复用
- 净值曲线：复用 Backtest 的 ECharts 初始化逻辑
- 饼图 / 热力图：新增 ECharts 组件

### 状态管理
- 本地 ref + 路由参数传递 reportId

## 文件清单

### 新增
- `web/src/views/Reports.vue`
- `web/src/views/ReportDetail.vue`
- `web/src/views/ReportPreferences.vue`

### 修改
- `web/src/views/Dashboard.vue` - 报告卡片
- `web/src/api/index.ts` - reportApi
- `web/src/router/index.ts` - 新增 `/reports` `/reports/:id` `/report-preferences`

## 估算
- ReportsPage：2 小时
- ReportDetail：3 小时（含 3 个图表）
- ReportPreferences：1 小时
- Dashboard 集成：0.5 小时
- **总计：6.5 小时 ≈ 0.8 人日**

---

**状态**: 待实施
**优先级**: P0（Phase 3 核心功能）
**依赖**: 后端 API 已就绪（P3-06 后端完成）
