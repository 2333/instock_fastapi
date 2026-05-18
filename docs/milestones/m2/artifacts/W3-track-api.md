# W3 Track API

> Owner: controller
> Status: go
> Endpoint: `POST /api/v1/events/track`

## 合同摘要

- 认证: 必须登录，复用现有 `get_current_user`
- 事件范围: 仅允许首波 6 类事件
- `event_data`: 白名单校验，不接受任意 shape
- 成功状态码: `202`
- 写入失败: `202` + `persisted=false`
- 非法 payload: `422`
- 限流: `100 req / minute / user`
- 限流按“请求尝试”计数，不因写库失败而绕过配额

## 验证命令

```bash
.venv/bin/pytest tests/test_events_router.py tests/test_auth_router.py tests/test_router_endpoints.py -q
```

## 验证结果

- 相关 focused tests 通过
- 已覆盖:
  - 未登录请求返回 `401`
  - 白名单 payload 成功持久化
  - 未知 `event_type` 返回 `422`
  - 非白名单字段返回 `422`
  - 写入异常被吞掉并返回 `persisted=false`
  - 写入失败后的重复请求仍会命中服务端限流 `429`
  - 首波完整事件序列可按 SQL 查询

## 残余风险

- 若后续扩展事件类型、`route_name`、Dashboard 卡片或筛选键白名单，需要同步更新 schema 校验与前端 emitter；不能只改其中一侧
