#!/bin/bash
# M1 Phase 1.5 一键启动脚本
# 用法: ./scripts/start_m1_phase.sh
# 前置: 确保 Tushare token 已修复（check_m1_readiness.py 全绿）

set -e  # 遇到错误立即退出

cd "$(dirname "$0")/.."  # 切换到项目根目录

echo "=== InStock M1 Phase 1.5 启动 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步骤 1: 检查环境就绪
echo "步骤 1/5: 检查环境就绪..."
if ! python scripts/check_m1_readiness.py > /tmp/m1_readiness.log 2>&1; then
    echo -e "${RED}❌ 环境检查未通过，请先修复以下问题：${NC}"
    cat /tmp/m1_readiness.log
    echo ""
    echo "请参考 QUICKFIX_M1_TUSHARE_TOKEN.md 修复 Tushare token"
    exit 1
fi
echo -e "${GREEN}✅ 环境检查通过${NC}"

# 步骤 2: 确保在 main 分支且最新
echo ""
echo "步骤 2/5: 检查代码库状态..."
git checkout main
git pull origin main

if ! git diff --quiet; then
    echo -e "${YELLOW}⚠️  工作区有未提交更改，正在暂存...${NC}"
    git add -A
    git commit -m "chore: pre-M1 workspace cleanup $(date '+%Y%m%d_%H%M%S')" || true
fi

if [ -n "$(git status -s)" ]; then
    echo -e "${RED}❌ 工作区仍有未提交更改，请手动清理${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 代码库状态干净${NC}"

# 步骤 3: 初始化进度跟踪
echo ""
echo "步骤 3/5: 初始化进度跟踪..."
cat > docs/M1_PROGRESS_TRACKER.md << 'EOF'
# M1 进度跟踪（实时更新）
## 启动时间
$(date '+%Y-%m-%d %H:%M:%S')

## WS-0 基础设施层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
| WS0-01 | Agent A | in_progress | $(date '+%H:%M') | - | Alembic 基线 |
| WS0-02 | Agent A | pending | - | - | 时间列规范 |
| WS0-03 | Agent A | pending | - | - | Timescale 规范 |
| WS0-04 | Agent B | pending | - | - | pro_bar 抽象 |
| WS0-05 | Agent F | pending | - | - | 质量框架骨架 |

## WS-1 核心改造层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
| WS1-01 | Agent C | pending | - | - | 股票同步 |
| WS1-02 | Agent C | pending | - | - | 日线回填 |
| WS1-03 | Agent D | pending | - | - | 指标引擎 |
| WS1-04 | Agent C | pending | - | - | 分钟线 |
| WS1-05 | Agent C | pending | - | - | 基本面数据 |

## WS-2 新接口扩展层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
| WS2-01 | Agent E | pending | - | - | moneyflow |
| WS2-02 | Agent E | pending | - | - | limit list |
| WS2-03 | Agent E | pending | - | - | limit detail |
| WS2-04 | Agent E | pending | - | - | disclosure |
| WS2-05 | Agent E | pending | - | - | bak_basic |
| WS2-06 | Agent E | pending | - | - | top_inst |

## WS-3 质量保障层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
| WS3-01 | Agent F | pending | - | - | completeness |
| WS3-02 | Agent F | pending | - | - | alerting |
| WS3-03 | Agent F | pending | - | - | monitoring |
| WS3-04 | Agent F | pending | - | - | lineage |
| WS3-05 | Agent F | pending | - | - | dashboard |
| WS3-06 | Agent F | pending | - | - | report |

## 总体状态
- M1 启动时间: $(date '+%Y-%m-%d %H:%M:%S')
- 当前阶段: WS-0 第一批任务
- 总任务数: 29
- 已完成: 0
- 进行中: 0
- 待开始: 29
EOF

echo -e "${GREEN}✅ 进度跟踪已初始化${NC}"

# 步骤 4: 创建执行日志目录
echo ""
echo "步骤 4/5: 准备执行环境..."
mkdir -p logs/m1_execution
mkdir -p reports/m1_progress
echo -e "${GREEN}✅ 执行环境准备完成${NC}"

# 步骤 5: 显示启动摘要
echo ""
echo "=========================================="
echo -e "${GREEN}✅ M1 启动准备完成！${NC}"
echo "=========================================="
echo ""
echo "下一步操作："
echo ""
echo "1. 启动 WS-0 第一批任务（以下任一方式）："
echo ""
echo "   方式 A - 并行分派给 Agents（推荐）："
echo "   $ openclaw agents spawn --task docs/M1_TASK_WS0-01_ALCHEMY.md --agentId agent-a &"
echo "   $ openclaw agents spawn --task docs/M1_TASK_WS0-02_TIME_COLUMNS.md --agentId agent-a &"
echo "   $ openclaw agents spawn --task docs/M1_TASK_WS0-03_TIMESCALE.md --agentId agent-a &"
echo "   $ openclaw agents spawn --task docs/M1_TASK_WS0-04_PRO_BAR.md --agentId agent-b &"
echo "   $ openclaw agents spawn --task docs/M1_TASK_WS0-05_QUALITY.md --agentId agent-f &"
echo ""
echo "   方式 B - 手动逐个执行（调试用）："
echo "   $ openclaw agents spawn --task docs/M1_TASK_WS0-01_ALCHEMY.md --agentId agent-a"
echo ""
echo "2. 监控进度："
echo "   $ tail -f docs/M1_PROGRESS_TRACKER.md"
echo "   $ tail -f logs/m1_execution/execution.log"
echo ""
echo "3. 每个任务完成后更新进度跟踪文档"
echo ""
echo "详细执行指南：docs/M1_LAUNCH_SEQUENCE.md"
echo "任务就绪证书：docs/M1_LAUNCH_READINESS_CERTIFICATE.md"
echo ""
echo "祝 M1 执行顺利！🚀"
echo ""
