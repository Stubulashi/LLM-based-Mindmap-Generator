#!/usr/bin/env bash
# =========================================================
# C: MCP Inspector 一键启动脚本
#    使用官方 @modelcontextprotocol/inspector 包装 mcp_server.py，
#    在浏览器中提供交互式 JSON-RPC 调试界面。
# E: MCP Inspector one-click launch script
#    Wraps mcp_server.py with official @modelcontextprotocol/inspector,
#    providing an interactive JSON-RPC debug UI in the browser.
# =========================================================
set -euo pipefail

# C: 定位项目根目录（脚本所在目录的上一级）
# E: Locate project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================================="
echo "C: MCP Inspector — 思维导图 MCP Server 调试工具"
echo "E: MCP Inspector — Mind Map MCP Server Debug Tool"
echo "========================================================="
echo ""

# C: 检查 Node.js 是否可用
# E: Check if Node.js is available
if ! command -v node &>/dev/null; then
    echo "C: [错误] 未检测到 Node.js。请先安装 Node.js (>=18)："
    echo "E: [Error] Node.js not found. Please install Node.js (>=18):"
    echo "    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "    sudo apt-get install -y nodejs"
    exit 1
fi

echo "C: Node.js 版本: $(node --version)"
echo "E: Node.js version: $(node --version)"
echo ""

# C: 验证 mcp_server.py 存在
# E: Verify mcp_server.py exists
if [ ! -f "$PROJECT_ROOT/mcp_server.py" ]; then
    echo "C: [错误] 未找到 mcp_server.py，请确保在项目根目录下运行此脚本。"
    echo "E: [Error] mcp_server.py not found. Ensure you're running from the project root."
    exit 1
fi

# C: 检测 Python 环境 — 优先使用 venv，其次使用系统 Python
# E: Detect Python environment — prefer venv, fallback to system Python
PYTHON_BIN=""
if [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"
    echo "C: 使用 venv Python: $PYTHON_BIN"
    echo "E: Using venv Python: $PYTHON_BIN"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
    echo "C: 使用系统 Python: $(python3 --version)"
    echo "E: Using system Python: $(python3 --version)"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
    echo "C: 使用系统 Python: $(python --version)"
    echo "E: Using system Python: $(python --version)"
else
    echo "C: [错误] 未检测到 Python，请先激活虚拟环境或安装 Python 3.10+。"
    echo "E: [Error] Python not found. Please activate venv or install Python 3.10+."
    exit 1
fi

echo ""
echo "C: 目标 Server: $PROJECT_ROOT/mcp_server.py"
echo "E: Target Server: $PROJECT_ROOT/mcp_server.py"
echo ""
echo "C: 启动后，浏览器将自动打开 http://localhost:6274"
echo "E: After launch, browser will auto-open http://localhost:6274"
echo ""
echo "C: 提示: Server 初始化需要加载 Whisper 模型，请耐心等待..."
echo "E: Hint: Server init loads Whisper model, please wait..."
echo "---------------------------------------------------------"
echo ""

# C: 启动 MCP Inspector，将 mcp_server.py 作为 stdio 子进程包装
#    设置 SKIP_HEAVY_INIT=1 跳过 Whisper 模型加载，确保 stdio 握手在秒级完成
# E: Launch MCP Inspector, wrapping mcp_server.py as stdio subprocess
#    Sets SKIP_HEAVY_INIT=1 to skip Whisper loading, ensuring stdio handshake within seconds
SKIP_HEAVY_INIT=1 npx --yes @modelcontextprotocol/inspector \
    "$PYTHON_BIN" "$PROJECT_ROOT/mcp_server.py"
