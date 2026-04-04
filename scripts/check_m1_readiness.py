#!/usr/bin/env python3
"""
M1 启动前环境就绪检查

检查项:
1. TimescaleDB 扩展是否可用
2. Tushare 积分是否满足（基础 3000+，进阶 8000+）
3. 数据库连接是否正常
4. Alembic 是否已安装

输出: 控制台报告 + JSON 摘要（stdout）
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

def check_timescaledb():
    """检查 TimescaleDB 扩展是否可用"""
    try:
        from app.database import async_engine
        from sqlalchemy import text
        import asyncio

        async def _check():
            async with async_engine.begin() as conn:
                rs = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname='timescaledb'"))
                return rs.scalar_one_or_none() is not None

        available = asyncio.run(_check())
        return {"available": available, "message": "TimescaleDB extension found" if available else "TimescaleDB not installed"}
    except Exception as e:
        return {"available": False, "message": f"Error checking TimescaleDB: {e}"}

def check_tushare_credits():
    """检查 Tushare 积分（通过 API 调用获取用户信息）"""
    try:
        import tushare as ts
        token = None
        # 从环境或配置读取 token
        from app.config import get_settings
        settings = get_settings()
        token = settings.TUSHARE_TOKEN

        if not token:
            return {"credits": None, "level": "unknown", "message": "TUSHARE_TOKEN not configured"}

        pro = ts.pro_api(token)
        info = pro.userinfo()
        # Tushare userinfo 返回包含 'credit' 字段
        credits = info.get("credit", 0)
        level = "basic" if credits < 3000 else "advanced" if credits < 8000 else "full"
        return {
            "credits": credits,
            "level": level,
            "message": f"Credits: {credits} ({level})"
        }
    except Exception as e:
        return {"credits": None, "level": "error", "message": f"Error: {e}"}

def check_database_connection():
    """检查数据库连接（通过运行 pytest 单测验证）"""
    try:
        # 使用 pytest 快速验证数据库连接是否正常
        result = subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "pytest"), "tests/test_config.py", "-q", "--tb=no"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        passed = result.returncode == 0
        return {
            "connected": passed,
            "message": "Database connection OK (config tests passed)" if passed else f"Connection test failed: {result.stdout.strip()}"
        }
    except Exception as e:
        return {"connected": False, "message": f"Connection error: {e}"}

def check_alembic_available():
    """检查 Alembic 是否可用"""
    try:
        result = subprocess.run(["alembic", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return {"available": True, "version": result.stdout.strip(), "message": f"Alembic available: {result.stdout.strip()}"}
        else:
            return {"available": False, "version": None, "message": "alembic command failed"}
    except FileNotFoundError:
        return {"available": False, "version": None, "message": "alembic command not found"}

def main():
    print("=== M1 环境就绪检查 ===\n")

    checks = {
        "TimescaleDB": check_timescaledb(),
        "Tushare": check_tushare_credits(),
        "Database": check_database_connection(),
        "Alembic": check_alembic_available(),
    }

    for name, result in checks.items():
        # 判断状态：available/connected 为 True，或 credits >= 3000
        if result.get("available") or result.get("connected"):
            status = "✅"
        else:
            credits_val = result.get("credits") or 0
            status = "✅" if credits_val >= 3000 else "❌"
        print(f"{status} {name}: {result['message']}")

    # 决策建议
    print("\n=== 启动建议 ===")
    ts_ok = checks["TimescaleDB"]["available"]
    db_ok = checks["Database"]["connected"]
    alembic_ok = checks["Alembic"]["available"]
    credits = checks["Tushare"].get("credits", 0) or 0
    credits_ok = credits >= 3000  # 基础功能门槛

    if ts_ok and db_ok and alembic_ok and credits_ok:
        print("✅ 环境就绪，可以启动 M1 WS-0 第一批任务")
        exit_code = 0
    else:
        print("⚠️  存在未满足的前置条件，请先修复：")
        if not ts_ok:
            print("   - 安装 TimescaleDB 扩展: CREATE EXTENSION timescaledb;")
        if not db_ok:
            print("   - 检查数据库连接配置（.env 中的 DATABASE_URL）")
        if not alembic_ok:
            print("   - 安装 Alembic: pip install alembic")
        if not credits_ok:
            print(f"   - Tushare 积分不足（当前 {credits}，需 ≥3000）")
        exit_code = 1

    # 输出 JSON 摘要（供脚本解析）
    summary = {
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "checks": checks,
        "ready": ts_ok and db_ok and alembic_ok and credits_ok,
    }
    print("\n--- JSON SUMMARY ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
