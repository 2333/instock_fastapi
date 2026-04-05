# Task: WS3-02 数据质量告警配置

**Owner**: Agent F (Quality & Observability)
**Workstream**: WS-3 质量保障
**Priority**: P0 (质量体系核心)
**Estimated Effort**: 0.5 天
**Dependencies**: WS3-01 (completeness 实现)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

配置质量检查失败时的告警通道（邮件/Webhook/钉钉），并定义不同严重等级的告警规则与通知策略。

---

## 背景

质量检查需主动通知:
- 失败时立即通知负责人
- 严重失败（如数据缺失 > 5%）触发 PagerDuty 式紧急告警
- 阈值可配置（不同环境不同阈值）

本任务实现告警基础设施，WS3-03/04/05/06 的检查失败均通过此通道上报。

---

## 具体步骤

### 1. 告警配置 `app/config/alerting.py`

```python
from pydantic import BaseSettings
from typing import Optional

class AlertConfig(BaseSettings):
    """告警配置"""
    ALERT_ENABLED: bool = True
    ALERT_LEVELS: dict = {
        "critical": {"threshold": 0, "channels": ["webhook", "email"]},
        "high": {"threshold": 2, "channels": ["webhook"]},
        "medium": {"threshold": 5, "channels": ["email"]},
        "low": {"threshold": 10, "channels": []},  # 仅记录
    }
    WEBHOOK_URL: Optional[str] = None
    EMAIL_RECIPIENTS: list[str] = []
    DINGTALK_WEBHOOK: Optional[str] = None

alert_config = AlertConfig()
```

### 2. 告警发送器 `app/services/alerting.py`

```python
import aiohttp
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from typing import Literal
from app.config.alerting import alert_config

class AlertSeverity(Literal):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

async def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = "medium",
    context: dict = None
):
    """
    发送告警到配置的通道

    参数:
        title: 告警标题
        message: 详细消息
        severity: 严重等级
        context: 附加上下文（检查结果等）
    """
    if not alert_config.ALERT_ENABLED:
        return

    # 记录告警日志
    log_alert(title, message, severity, context)

    # 根据等级发送到对应渠道
    channels = alert_config.ALERT_LEVELS.get(severity, {}).get("channels", [])

    for channel in channels:
        if channel == "webhook" and alert_config.WEBHOOK_URL:
            await send_webhook(alert_config.WEBHOOK_URL, {
                "title": title,
                "message": message,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "context": context or {}
            })

        elif channel == "email" and alert_config.EMAIL_RECIPIENTS:
            send_email(title, message, alert_config.EMAIL_RECIPIENTS)

        elif channel == "dingtalk" and alert_config.DINGTALK_WEBHOOK:
            await send_dingtalk(alert_config.DINGTALK_WEBHOOK, title, message)

def log_alert(title, message, severity, context):
    """记录告警到日志文件"""
    import json
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "message": message,
        "severity": severity,
        "context": context or {}
    }
    # 写入 alerts.log
    with open("logs/alerts.log", "a") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

async def send_webhook(url: str, payload: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                print(f"Webhook 发送失败: {resp.status}")

def send_email(title: str, body: str, recipients: list[str]):
    # 使用 SMTP 发送（配置见 .env）
    import smtplib
    from email.mime.text import MIMEText
    # ... 实现略
    pass

async def send_dingtalk(webhook: str, title: str, message: str):
    # 钉钉机器人格式
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"#### {title}\n{message}"
        }
    }
    async with aiohttp.ClientSession() as session:
        await session.post(webhook, json=payload)
```

### 3. 集成到质量引擎

修改 `QualityEngine.run_all()`:

```python
async def run_all(self, send_alerts: bool = True) -> List[CheckResult]:
    results = []
    for check in self._checks:
        try:
            result = await check.run()
            results.append(result)

            # 失败时发送告警
            if send_alerts and not result.passed:
                severity = self.determine_severity(result)
                await send_alert(
                    title=f"数据质量检查失败: {result.check_name}",
                    message=self.format_alert_message(result),
                    severity=severity,
                    context=result.to_dict()
                )

        except Exception as e:
            # 异常也告警
            result = CheckResult(...)
            results.append(result)
            await send_alert(
                title=f"质量检查异常: {check.name()}",
                message=str(e),
                severity="critical"
            )
    return results

def determine_severity(self, result: CheckResult) -> AlertSeverity:
    """根据检查类型与失败详情确定严重等级"""
    if result.check_name.startswith("completeness"):
        return "critical"  # 数据缺失是严重问题
    elif result.check_name.startswith("cross_source"):
        return "high"      # 跨源不一致需关注
    else:
        return "medium"
```

### 4. 配置管理

`.env` 告警配置示例:

```bash
# 告警总开关
ALERT_ENABLED=true

# Webhook（通用）
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...

# 邮件
ALERT_EMAIL_RECIPIENTS=dev@example.com,ops@example.com
SMTP_HOST=smtp.example.com
SMTP_USER=alert@example.com
SMTP_PASSWORD=***

# 钉钉
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=...
```

### 5. 测试 `tests/test_alerting.py`

```python
import pytest
from app.services.alerting import send_alert, AlertSeverity

@pytest.mark.asyncio
async def test_send_webhook():
    # Mock webhook 发送
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        await send_alert("Test", "Test message", "medium")
        # 验证调用
```

---

## 验收标准

- [ ] `send_alert()` 可调用，根据 severity 路由到对应渠道
- [ ] Webhook/Email/DingTalk 至少一种渠道可配置
- [ ] 质量检查失败时自动触发告警（测试环境可禁用）
- [ ] 告警日志 `logs/alerts.log` 记录完整
- [ ] 测试通过

---

## 交付物

- [ ] `app/config/alerting.py`（配置）
- [ ] `app/services/alerting.py`（发送器）
- [ ] `QualityEngine` 集成告警触发
- [ ] `.env` 告警配置示例
- [ ] `logs/alerts.log`（运行生成）
- [ ] `tests/test_alerting.py`

---

**Trigger**: WS3-01 完成后
**Estimated Time**: 0.5 天
