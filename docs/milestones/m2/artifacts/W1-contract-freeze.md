# W1 Contract Freeze

> Owner: controller
> Status: frozen
> Date: 2026-04-20
> Scope: `M2 / P3-01` first-wave event contract

## 决策

- 首波只覆盖登录用户，不引入访客 / `session_id`
- 首波只覆盖 5 个受保护页面与 6 类核心事件
- 事件 payload 采用白名单结构，不接受任意 shape 的 `event_data`
- `POST /api/v1/events/track` 必须复用现有认证链路
- 写入失败不阻塞主流程，但失败不能被伪装成“已经持久化”
- 首波不引入消息队列、异步消费、分区、归档或 TTL 策略

## 事件范围

- `page_view`
- `dashboard_card_click`
- `filter_run`
- `backtest_run`
- `pattern_view`
- `attention_action`

## 禁止项

- `session_id`
- 访客埋点
- raw IP / user agent
- email / password / token / refresh token
- `notes`
- 用户输入原文
- 任意 query string / body blob
- `10+` 事件扩展
- 分区 / 归档 / 保留策略

## 已拒绝的更宽设想

- 旧草案中的“可选认证 + 未登录 session 级事件”
- 旧草案中的 IP hash / user agent 采集
- 旧草案中的按周分区和 60 天自动归档
- 在 kickoff 同一波内直接扩到 `10+` 事件类型

## 对实现的约束

- 后端 migration 必须基于当前 accepted existing-schema 起点验证，不能被 `create_all()` 掩盖
- 前端必须复用共享 axios，不允许单独再拉一个裸 `fetch` 链路
- 限流必须在服务端完成，不能靠前端节流假装成立
- reviewer 未确认 contract 与实现一致前，不允许进入 M2 最终验收
