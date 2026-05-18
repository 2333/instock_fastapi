# W3 Residue Cleanup

> Status: completed
> Owner: `worker-runtime`
> Depends: `W2`, `W2a`
> Last updated: 2026-04-21

> `2026-04-21` reviewer reopen 已关闭：
> 当前前端降级已完成导航/文案收口，server-backed language preference 也已通过同一条 `/auth/settings` hydrate 路径在 login/bootstrap 后真实生效；本 wave 返回 `completed`。

## 目标

在不误删真实 contract 的前提下，处理会把偏航能力伪装成主线承诺的 active residue；当前优先级高于纯样式噪音。

## 必收口范围

- `Workspace` 从 active nav / default-home 语义中降级
- `Settings` 从主线承诺中降级到“仅保留当前真实支持的偏好设置”
- `Attention` 去掉“设置提醒条件”的主线承诺，直到 `M3` 真正启动

## Owned scope

- active navigation 与默认首页入口的收口
- `Attention` 页面对提醒能力的误导性文案 / 交互收口
- 对“保留但不作为主线承诺”的 residue 进行显式记录

## Write set

- `web/src/router/index.ts`
- `web/src/composables/useUserPreferences.ts`
- `web/src/composables/useLocale.ts`
- `web/src/views/Attention.vue`
- `web/src/views/Settings.vue`
- `web/src/views/Login.vue`
- `web/src/App.vue`
- `web/src/components/layout/AppHeader.vue`
- 本 artifact

## Shared-risk note

- `attention` 的后端 `alert_conditions` contract 当前仍存在；若仅靠前端降级无法消除路线误导，再决定是否进入后端 contract 收口，并先在 tracker 记录 handoff。

## Entry criteria

- `W2` / `W2a` 已确认当前最小 runtime / API contract 基线
- 当前目标是“降级误导性 active residue”，不是提前实现 `M3` 的 alert engine

## Success criteria

- `/workspace` 不再作为 active mainline 默认入口
- `/settings` 不再被表达成超出当前真实支持范围的能力入口
- `Attention` 当前 UI 不再承诺“设置提醒条件”
- 保留的 residue 被明确记录为 intentionally kept，而不是半激活能力

## Changed files

- `web/src/router/index.ts`
  - 保留 `/workspace` 路由，但将标题标记为保留入口，不再表达主线路径语义。
- `web/src/composables/useUserPreferences.ts`
  - `defaultHome` 只允许 `/`，历史 `/workspace` 偏好会在读取与保存时被归一并覆盖。
  - 认证后通过单次 `/auth/settings` hydrate 同步 `defaultHome` 与 locale，避免重复请求与状态分叉。
- `web/src/composables/useLocale.ts`
  - 抽出 locale normalize/apply 逻辑，让语言偏好可从 `/auth/settings.language` 直接落到共享 locale 状态。
- `web/src/views/Attention.vue`
  - 去掉“设置提醒条件”的承诺性文案，改为只强调当前真实存在的分组与备注整理。
- `web/src/views/Settings.vue`
  - 重写为只展示并保存当前真实支持的偏好项：语言，以及被固定为首页工作台的默认首页语义。
  - 去掉数据刷新、通知提醒、图表默认指标等未兑现能力入口。
  - 保持单次 `/auth/settings` 响应作为页面事实来源，不再在页面内二次触发 settings hydrate。
- `web/src/views/Login.vue`
  - 登录成功后只等待一次 `/auth/settings` hydrate，再进入 redirect 路径，让跨浏览器登录能够带上 server-backed locale。
- `web/src/App.vue`
  - 恢复会话时通过 `authApi.getMe() + loadUserPreferences(true)` 同步当前用户的默认首页和语言，不再额外并行发第二个 settings 请求。
- `web/src/components/layout/AppHeader.vue`
  - 去掉 `Workspace` 主导航入口，logo 仍走当前真实默认首页。

## Commands run

- `npm run typecheck`
- `npm run build`

## Results

- `npm run typecheck`: passed
- `npm run build`: passed
- `reviewer`: reopened locale bootstrap finding closed with no additional blocking findings
- `code-review-expert`: no additional blocking findings after final W3 pass
- 构建过程中存在既有 Sass deprecation warnings：
  - legacy JS API
  - `@import` deprecation
- 这些 warning 不由本次 W3 residue cleanup 引入，本次未处理。

## Manual verification

- 当前 writable scope 内没有现成可扩写的前端测试文件。
- 本次未执行交互式浏览器手工验证，也不宣称已完成人工点击验收。
- 本次确认方式：
  - 代码检查确认 `AppHeader` 已不再渲染 `Workspace` 主导航项。
  - 代码检查确认 `useUserPreferences` 已将 `defaultHome` 归一为 `/`，不会继续保留 `/workspace`。
  - 代码检查确认 `Settings` 页面只保留真实支持的偏好项，并通过单次 `/auth/settings` contract 读写语言与 `extra.defaultHome=/`。
  - 代码检查确认 login/bootstrap 现在通过同一条 settings hydrate 路径把 server-backed language preference 应用到共享 locale。
  - 代码检查确认 `Attention` 页面文案已移除提醒条件承诺。

## Open risks

- `/workspace` 路由仍然保留为可直接访问的残留入口；这次只是把它从主导航与默认首页语义中降级，没有删除该页面。
- 顶部 header 的语言切换仍然是本地即时切换，不会在当次点击时直接写回 `/auth/settings`；当前 server-backed 语言的权威写入口仍然是 `Settings` 页。
- `router` 的 route title 仍以中文静态字符串为主，浏览器 tab title 还不是完整多语言。
- 后端 `auth/settings.extra` 与 `attention.alert_conditions` contract 仍然存在；当前只是前端降级表达，未做后端 contract 收口。
- 若后续需要彻底下线 `Workspace` 或提醒能力，需要跨前后端的进一步对齐，而不只是 W3 的前端 residue cleanup。

## Residue kept intentionally

- `/workspace` 仍可通过直接 URL 访问，作为保留入口存在。
- `buildSettingsExtra()` 仍会把 `defaultHome` 写入 `extra` / `ui_preferences`，但值已被强制规范为 `/`，用于清理历史 residue，而不是继续支持 `Workspace` 作为首页。

## Next step

1. 若 controller 需要更强收口，可评估是否在后续阶段直接移除 `/workspace` 路由入口文档与残余 discoverability。
2. 若要彻底消除提醒能力误导，需要单独决定是否收紧后端 `alert_conditions` contract。

## Recovery note

- 若后续继续接手 W3 residue，优先复查：
  - `AppHeader` 是否重新出现 `Workspace` 主导航。
  - `useUserPreferences` 是否再次允许 `/workspace` 作为 `defaultHome`。
  - `Settings` 是否重新挂回未兑现的数据 / 通知 / 图表设置入口。
  - `Attention` 是否重新出现“提醒条件”承诺性文案。
