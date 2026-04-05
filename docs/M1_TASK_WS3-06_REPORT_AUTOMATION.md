# Task: WS3-06 质量报告自动化

**Owner**: Agent F (Quality & Observability)
**Workstream**: WS-3 质量保障
**Priority**: P2 (运维自动化)
**Estimated Effort**: 0.3 天
**Dependencies**: WS3-02 (告警)、WS3-05 (Dashboard)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现质量报告自动生成与分发，每日定时生成 PDF/HTML 报告，汇总稳定性、数据质量、告警统计，并邮件发送给团队。

---

## 背景

质量报告用于:
- 每日晨会汇报前一日数据质量
- 周期性回顾（周/月报）
- 问题追踪与趋势分析
- 满足合规审计需求

自动化流程:
- 每日 9:00 生成前一日报告
- 邮件发送给指定收件人
- 报告存档至 `reports/` 目录

---

## 具体步骤

### 1. 报告生成器 `app/services/report_generator.py`

```python
from datetime import datetime, timedelta
from jinja2 import Template
import weasyprint
from app.services.data_quality import quality_engine
from app.services.alerting import get_recent_alerts

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .pass { color: green; }
        .fail { color: red; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background: #f0f0f0; }
    </style>
</head>
<body>
    <h1>InStock 数据质量日报</h1>

    <div class="summary">
        <h2>报告摘要</h2>
        <p><strong>日期:</strong> {{ date }}</strong></p>
        <p><strong>总体状态:</strong> <span class="{{ overall.status }}">{{ overall.status }}</span></p>
        <p><strong>通过率:</strong> {{ overall.pass_rate }}%</p>
        <p><strong>检查项:</strong> {{ overall.total }} 项，通过 {{ overall.passed }} 项，失败 {{ overall.failed }} 项</p>
    </div>

    <h2>质量检查详情</h2>
    <table>
        <thead>
            <tr>
                <th>检查项</th>
                <th>状态</th>
                <th>详情</th>
                <th>建议</th>
            </tr>
        </thead>
        <tbody>
        {% for check in checks %}
            <tr>
                <td>{{ check.name }}</td>
                <td class="{{ 'pass' if check.passed else 'fail' }}">{{ '✅ 通过' if check.passed else '❌ 失败' }}</td>
                <td>{{ check.details | tojson }}</td>
                <td>{{ check.suggestions | join('; ') }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>

    <h2>告警统计（近 24h）</h2>
    <p>共 {{ alerts | length }} 条告警</p>
    <ul>
    {% for alert in alerts %}
        <li>[{{ alert.severity }}] {{ alert.title }} - {{ alert.timestamp }}</li>
    {% endfor %}
    </ul>

    <hr>
    <p style="color: #999; font-size: 12px;">
        报告生成时间: {{ generated_at }} |
        数据来源: Tushare API |
        系统: InStock FastAPI
    </p>
</body>
</html>
"""

async def generate_daily_report(target_date: datetime = None) -> str:
    """
    生成指定日期的质量报告

    参数:
        target_date: 报告日期（None=昨日）

    返回:
        HTML 字符串
    """
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)

    # 1. 获取当日质量检查结果（从 stability_log 读取）
    from app.models.stability_log import StabilityLog
    from app.db.session import async_session

    async with async_session() as session:
        log = await session.execute(
            select(StabilityLog)
            .where(func.date(StabilityLog.timestamp) == target_date.date())
            .order_by(StabilityLog.timestamp.desc())
            .limit(1)
        )
        daily_log = log.scalar_one_or_none()

        if not daily_log:
            return f"<h1>{target_date.date()} 无检查记录</h1>"

        # 2. 准备模板数据
        checks = daily_log.details.get("results", [])
        overall = {
            "status": daily_log.overall_status,
            "pass_rate": daily_log.pass_rate,
            "total": len(checks),
            "passed": sum(1 for c in checks if c.get("passed")),
            "failed": sum(1 for c in checks if not c.get("passed"))
        }

        alerts = get_recent_alerts(hours=24)

        template = Template(HTML_TEMPLATE)
        html = template.render(
            date=target_date.strftime("%Y-%m-%d"),
            overall=overall,
            checks=checks,
            alerts=alerts,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        return html

async def generate_and_save_report(target_date=None) -> Path:
    """生成报告并保存为 HTML + PDF"""
    html = await generate_daily_report(target_date)

    report_date = (target_date or datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)

    html_path = report_dir / f"quality_report_{report_date}.html"
    html_path.write_text(html, encoding="utf-8")

    # 生成 PDF（需要 weasyprint）
    try:
        pdf_path = report_dir / f"quality_report_{report_date}.pdf"
        weasyprint.HTML(string=html).write_pdf(pdf_path)
        print(f"报告已生成: {pdf_path}")
    except Exception as e:
        print(f"PDF 生成失败（可选）: {e}")

    return html_path
```

### 2. 邮件发送 `app/services/report_emailer.py`

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from app.config import get_settings

async def send_report_email(report_path: Path, report_date: str):
    """发送报告邮件"""
    settings = get_settings()

    msg = MIMEMultipart()
    msg['Subject'] = f"InStock 数据质量日报 {report_date}"
    msg['From'] = settings.SMTP_USER
    msg['To'] = ", ".join(settings.REPORT_RECIPIENTS)

    # HTML 正文
    html_content = report_path.read_text(encoding="utf-8")
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    # 附件（PDF）
    pdf_path = report_path.with_suffix('.pdf')
    if pdf_path.exists():
        with open(pdf_path, 'rb') as f:
            pdf = MIMEApplication(f.read(), _subtype='pdf')
            pdf.add_header('Content-Disposition', 'attachment', filename=pdf_path.name)
            msg.attach(pdf)

    # 发送
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)

    print(f"报告已发送至 {settings.REPORT_RECIPIENTS}")
```

### 3. 定时任务

**方式 A: Cron**

```bash
# crontab -e
0 9 * * 1-5 cd /path/to/instock_fastapi && .venv/bin/python scripts/generate_daily_report.py >> logs/report.log 2>&1
# 每个工作日 9:00 生成前一日报告
```

**方式 B: APScheduler**

```python
# app/jobs/scheduler.py
scheduler.add_job(
    generate_and_email_report,
    trigger='cron',
    day_of_week='mon-fri',
    hour=9,
    minute=0
)
```

### 4. 一键生成脚本 `scripts/generate_daily_report.py`

```python
#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.services.report_generator import generate_and_save_report
from app.services.report_emailer import send_report_email

async def main():
    # 昨日报告
    target_date = datetime.now() - timedelta(days=1)

    print(f"正在生成 {target_date.date()} 的质量报告...")
    report_path = await generate_and_save_report(target_date)

    print("正在发送邮件...")
    await send_report_email(report_path, target_date.strftime("%Y-%m-%d"))

    print("完成!")

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. 配置 `.env`

```bash
# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=alert@example.com
SMTP_PASSWORD=***

# 报告收件人
REPORT_RECIPIENTS=dev@example.com,ops@example.com,manager@example.com

# 报告开关
REPORT_ENABLED=true
```

---

## 验收标准

- [ ] `scripts/generate_daily_report.py` 可执行，生成 HTML 报告
- [ ] HTML 报告包含摘要、检查详情、告警统计
- [ ] PDF 生成成功（可选）
- [ ] 邮件发送成功（测试环境可打印到控制台）
- [ ] 报告存档于 `reports/quality_report_YYYYMMDD.html`
- [ ] 测试通过

---

## 交付物

- [ ] `app/services/report_generator.py`
- [ ] `app/services/report_emailer.py`
- [ ] `scripts/generate_daily_report.py`
- [ ] `static/report_template.html` (或内联模板)
- [ ] `reports/` 目录（自动创建）
- [ ] `.env` 报告配置
- [ ] `tests/test_report_generator.py`

---

**Trigger**: WS3-05 完成后
**Estimated Time**: 0.3 天
