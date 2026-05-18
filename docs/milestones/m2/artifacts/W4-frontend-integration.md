# W4 Frontend Integration

> Owner: controller
> Status: go
> Scope: `useAnalytics` + 5 页面接线

## 接入矩阵

| 页面 | 事件 |
|------|------|
| `Dashboard` | `page_view`、`dashboard_card_click` |
| `Selection` | `page_view`、`filter_run` |
| `Backtest` | `page_view`、`backtest_run` |
| `StockDetail` | `page_view`、`pattern_view`、`attention_action` |
| `Attention` | `page_view`、`attention_action` |

## 实现约束

- 复用 `web/src/api/index.ts` 中的共享 axios
- 前端静默失败，不阻塞主流程
- `page_view` 由路由层统一发射，不在前端做时间窗口去重
- `referrer` 只保留当前 SPA 导航上下文，使用内存态路由来源；深链打开 / 刷新时不会携带陈旧 referrer
- 页面层只保留最小接线

## 验证命令

```bash
cd web && npm run typecheck
cd web && npm run build
```

## 验证结果

- `typecheck` 通过
- `build` 通过
- 现存 Sass `@import` 弃用 warning 与 chunk warning 仍存在，但不是本轮埋点改动引入

## 收窄说明

- `dashboard_card_click` 只覆盖四张工作台卡片主入口，不扩展到卡片内列表项或“全部扫描”按钮
- 本轮不记录 session / visitor / raw query / notes / IP / UA
