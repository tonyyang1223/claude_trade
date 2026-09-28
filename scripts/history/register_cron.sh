#!/usr/bin/env bash
# 注册「历史库增量入库」定时任务到**当前用户** crontab —— 幂等 / 可预览 / 可移除。
#
# 设计依据：docs/history-db/ARCHITECTURE.md §6（Q1：复用现有调度，每 15 分钟一次，不新增常驻进程）。
#
# 用法：
#   bash scripts/history/register_cron.sh            # 仅预览（默认，不写 crontab）
#   bash scripts/history/register_cron.sh --install  # 写入当前用户 crontab
#   bash scripts/history/register_cron.sh --remove   # 移除本项目该条
#   bash scripts/history/register_cron.sh --status   # 显示当前是否已注册
#
# 可用环境变量覆盖（均有合理缺省）：
#   PROJECT_DIR（默认：本仓库根）  PYTHON_BIN（默认：python3/python）
#   LOG_DIR（默认：$PROJECT_DIR/logs）  INTERVAL_MIN（默认：15）
#
# ⚠️ 安全边界：本脚本**只操作当前用户 crontab**，且以唯一 marker 精确增删自身条目，
#    **不触碰** scripts/setup_cron.sh 管理的采集任务，也不修改任何生产配置文件。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python || true)}"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
INTERVAL_MIN="${INTERVAL_MIN:-15}"

ENTRY_SCRIPT="$PROJECT_DIR/scripts/history/ingest_history.py"
LOG_FILE="$LOG_DIR/history_ingest.log"
MARKER="claude-history-ingest"

# crontab 行（末尾 marker 便于精确增删）
CRON_LINE="*/${INTERVAL_MIN} * * * * cd ${PROJECT_DIR} && ${PYTHON_BIN} ${ENTRY_SCRIPT} --incremental >> ${LOG_FILE} 2>&1  # ${MARKER}"

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

have_crontab() { command -v crontab >/dev/null 2>&1; }

is_installed() {
    have_crontab || return 1
    crontab -l 2>/dev/null | grep -qF "$MARKER"
}

do_install() {
    if ! have_crontab; then
        echo "✗ 未找到 crontab（非 cron 环境，如 Windows/macOS 开发机）。"
        echo "  请把下面这行加入你的调度器（cron / systemd timer / 任务计划）："
        echo ""
        echo "  $CRON_LINE"
        return 1
    fi
    if [ -z "$PYTHON_BIN" ]; then
        echo "✗ 未能定位 python 解释器，请显式设置 PYTHON_BIN=/path/to/python3"
        return 1
    fi
    mkdir -p "$LOG_DIR"
    # 幂等：先删同 marker 旧行，再追加新行
    ( crontab -l 2>/dev/null | grep -vF "$MARKER" || true; echo "$CRON_LINE" ) | crontab -
    echo "✓ 已写入当前用户 crontab："
    echo "  $CRON_LINE"
    echo ""
    echo "  日志：$LOG_FILE"
}

do_remove() {
    if ! have_crontab; then
        echo "✗ 未找到 crontab，无需移除。"
        return 0
    fi
    ( crontab -l 2>/dev/null | grep -vF "$MARKER" || true ) | crontab -
    echo "✓ 已从当前用户 crontab 移除本项目的增量入库任务。"
}

do_status() {
    if is_installed; then
        echo "✓ 已注册："
        crontab -l 2>/dev/null | grep -F "$MARKER"
    else
        echo "· 未注册（可执行 --install 注册）。"
    fi
}

do_preview() {
    echo "=== 预览（默认不写 crontab）==="
    echo "项目根 : $PROJECT_DIR"
    echo "解释器 : ${PYTHON_BIN:-<未找到，请设置 PYTHON_BIN>}"
    echo "日志   : $LOG_FILE"
    echo "频率   : 每 ${INTERVAL_MIN} 分钟"
    echo ""
    echo "将写入的 crontab 行："
    echo "  $CRON_LINE"
    echo ""
    if is_installed; then
        echo "当前状态：已注册。"
    else
        echo "当前状态：未注册。执行 bash scripts/history/register_cron.sh --install 以注册。"
    fi
}

case "${1:-}" in
    --install) do_install ;;
    --remove)  do_remove ;;
    --status)  do_status ;;
    -h|--help) usage ;;
    "")        do_preview ;;
    *)         echo "未知参数：$1"; usage; exit 2 ;;
esac
