# M1 启动前：快速修复清单（Tushare Token）

> 适用于: 熟悉终端操作的用户
> 预期耗时: 5 分钟

---

## 问题

运行 `python scripts/check_m1_readiness.py` 显示:
```
❌ Tushare: Error: 您的token不对，请确认。
```

**原因**: `.env` 中的 `TUSHARE_TOKEN` 已失效。

---

## 快速修复（3 步）

### 步骤 1: 获取新 Token

1. 打开浏览器访问 https://tushare.pro
2. 登录你的账号
3. 进入 **个人中心 → 接口申请**
4. 找到 **API Token** 字段，点击 **重置**
5. 复制新 token（一长串字母数字）

### 步骤 2: 更新项目配置

在终端执行（替换 `<你的新token>`）:

```bash
cd /Users/zhangkai/projects/instock_fastapi
# 备份旧配置
cp .env .env.backup

# 更新 token（使用 sed 或手动编辑）
sed -i '' "s/^TUSHARE_TOKEN=.*/TUSHARE_TOKEN=<你的新token>/" .env

# 验证更新
grep TUSHARE_TOKEN .env
```

或者手动编辑:
```bash
vi .env  # 找到 TUSHARE_TOKEN 行，替换为新 token，保存退出
```

### 步骤 3: 验证修复

```bash
cd /Users/zhangkai/projects/instock_fastapi
source .venv/bin/activate
python scripts/check_m1_readiness.py
```

**预期输出**:
```
✅ TimescaleDB: TimescaleDB extension found
✅ Tushare: Credits: XXXX (basic/advanced/full)
✅ Database: Database connection OK
✅ Alembic: Alembic available: x.x.x
✅ 环境就绪，可以启动 M1 WS-0 第一批任务
```

---

## 常见问题

| 问题 | 解决 |
|------|------|
| `sed` 命令报错 "no such file or directory" | 确保在项目根目录执行，或使用 `vi .env` 手动编辑 |
| 更新后仍报 token 错误 | 检查 `.env` 是否保存成功；确认无 `.env.local` 覆盖；重启终端重试 |
| 无法登录 Tushare | 使用注册邮箱/手机号找回密码，或联系 Tushare 客服 |
| 积分显示 0 或不足 | 完成 Tushare 社区任务获取积分，或购买积分包 |

---

## 修复成功后

1. **M0 合并**: 等待 PR #8 审查合入（或手动合并）
2. **启动 M1**: 按 `docs/M1_KICKOFF_CHECKLIST.md` 执行 WS-0 任务
3. **日常**: heartbeat 自动运行稳定性监测

---

**参考文档**:
- `docs/M1_TUSHARE_TOKEN_BLOCK.md` - 详细诊断与修复指南
- `docs/M1_KICKOFF_CHECKLIST.md` - M1 启动清单
- `docs/M1_TASK_BREAKDOWN.md` - 任务拆解
