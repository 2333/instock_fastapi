# M1 启动阻塞：Tushare Token 失效诊断与修复指南

> 历史说明: 本文档保留为 2026-04-05 的 token 诊断快照。当前重启口径以 `docs/milestones/m1/M1_RESTART_PLAN.md` 为准；本文中引用的 `scripts/check_m1_readiness.py` 已不再保证存在。当前阶段 M1 已接受 token-independent 收口路径，因此本文只定义 Tushare 相关 follow-up 风险，不再单独阻塞 `daily_bars` / `technical_factors(local)` 主线。
>
> 日期: 2026-04-05
> 状态: 历史诊断快照（当前只阻塞 Tushare 相关 gated follow-up）
> 检查脚本: `scripts/check_m1_readiness.py`

---

## 问题现象

执行 `scripts/check_m1_readiness.py` 输出:
```
❌ Tushare: Error: 您的token不对，请确认。
```

直接调用 Tushare `userinfo` API 返回:
```json
{
  "code": 40101,
  "msg": "您的token不对，请确认。",
  "data": null
}
```

**结论**: 当前 `.env` 中的 `TUSHARE_TOKEN` 已失效，无法通过 Tushare 认证。

---

## 可能原因

| 原因 | 说明 | 概率 |
|------|------|------|
| Token 过期 | Tushare token 永久有效，但可能被手动撤销 | 高 |
| Token 被禁用 | 账号异常或违规导致 token 被封 | 中 |
| 积分清零 | 账号长期未使用，积分被回收，token 失效 | 中 |
| 配置加载错误 | 环境变量未正确加载（但已验证配置加载正常） | 低 |

---

## 修复步骤

### 步骤 1：登录 Tushare 获取新 Token

1. 访问 https://tushare.pro
2. 使用原账号登录（如忘记密码，使用注册邮箱/手机号找回）
3. 进入 **个人中心 → 接口申请**
4. 在页面顶部或右侧找到 **API Token** 字段
5. 点击 **重置** 或 **复制** 获取新 token（格式类似：`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

**注意**:
- 新 token 与旧 token 不同，需完整替换
- 重置 token 后，旧 token 立即失效

### 步骤 2：更新项目环境配置

```bash
# 编辑 .env 文件（位于项目根目录）
cd /Users/zhangkai/projects/instock_fastapi
vi .env  # 或使用任意编辑器

# 找到 TUSHARE_TOKEN 行，替换为新 token
TUSHARE_TOKEN=你的新token粘贴到这里
```

保存并退出。

### 步骤 3：验证修复

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行环境就绪检查
python scripts/check_m1_readiness.py

# 预期输出应包含：
# ✅ Tushare: Credits: XXXX (basic/advanced/full)
```

如果仍失败，检查:
- `.env` 文件是否保存且无语法错误
- 是否有多个 `.env` 文件（如 `.env.local` 会覆盖）
- `app/config.py` 的 `env_file` 配置指向正确路径

### 步骤 4：检查 Tushare 积分等级（可选）

修复后运行检查脚本会显示积分等级：
- **basic** (< 3000 积分): 仅支持基础接口（stock_basic, daily, index_daily 等）
- **advanced** (3000-7999): 支持大部分接口
- **full** (≥8000): 支持全部接口（包括 broker_forecast, chip_* 等）

如果积分不足，需要在 Tushare 网站完成积分任务（社区活跃、资料完善等）或购买积分包。

---

## 历史 M1 启动前提（再次确认）

按 2026-04-05 的旧口径，M1 启动曾被描述为必须同时满足:

| 条件 | 状态 | 说明 |
|------|------|------|
| ✅ M0 PR #8 已合入 `main` | 待合并 | 基线冻结 |
| ✅ TimescaleDB 扩展可用 | 已确认 | `SELECT * FROM pg_extension WHERE extname='timescaledb'` |
| ✅ 数据库连接正常 | 已确认 | config tests 通过 |
| ✅ Alembic 已安装 | 1.18.4 | `alembic --version` |
| ❌ Tushare token 有效 | 历史阻塞项 | 需手动更新 `.env` |
| ✅ M1 任务拆解完成 | 已就绪 | `M1_TASK_BREAKDOWN.md` + `M1_PROGRESS_TRACKER.md` |

---

## 历史临时应对（如无法立即获取新 Token）

如果暂时无法获取新 token，可采取的临时措施:

1. **降级使用 EastMoney/BaoStock**: 修改 provider 降级策略，绕过 Tushare 直接使用免费源（功能受限）
2. **Mock 数据模式**: 在开发环境使用本地 CSV/JSON 历史数据回填，不实时抓取
3. **暂停 M1 启动**: 等待 token 修复后再启动，M0 仍可合并

---

## 相关文档

- `docs/milestones/m1/M1_INITIATION_TASKS.md` - M1 总体执行计划
- `docs/milestones/m1/DATA_LAYER_REPORT.md` - 数据层改造技术方案
- `docs/milestones/m1/M1_TASK_BREAKDOWN.md` - 任务拆解与 Agent 分配
- `docs/milestones/m1/M1_PROGRESS_TRACKER.md` - 进度跟踪模板
- `scripts/check_m1_readiness.py` - 环境就绪检查脚本

---

**下次检查**: 修复 `.env` 后重新运行 `scripts/check_m1_readiness.py`，确认所有检查项通过。
