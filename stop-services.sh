#!/bin/bash

# 30周均线交易系统 - 一键停止脚本

echo "========================================="
echo "  30周均线交易系统 - 服务停止"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/trading_system"
FRONTEND_DIR="$PROJECT_ROOT/trading-dashboard"

# 检查端口占用
check_port() {
    local port=$1
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        return 0  # 端口被占用
    else
        return 1  # 端口可用
    fi
}

# 检查服务是否在运行
BACKEND_RUNNING=false
FRONTEND_RUNNING=false

if check_port 8000; then
    BACKEND_RUNNING=true
fi

if check_port 3002; then
    FRONTEND_RUNNING=true
fi

# 如果没有服务在运行
if [ "$BACKEND_RUNNING" = false ] && [ "$FRONTEND_RUNNING" = false ]; then
    echo -e "${YELLOW}⚠️  没有服务在运行${NC}"
    exit 0
fi

# 显示正在运行的服务
echo "正在运行的服务："
if [ "$BACKEND_RUNNING" = true ]; then
    echo -e "  ${GREEN}✓${NC} 后端服务 (端口 8000)"
fi
if [ "$FRONTEND_RUNNING" = true ]; then
    echo -e "  ${GREEN}✓${NC} 前端服务 (端口 3002)"
fi
echo ""

# 询问确认
read -p "确认要停止所有服务？(y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消停止。"
    exit 0
fi

echo ""
echo "正在停止服务..."

# 停止后端服务
if [ "$BACKEND_RUNNING" = true ]; then
    echo "停止后端服务..."
    pkill -f "python.*main.py.*serve" 2>/dev/null

    # 等待进程结束
    for i in {1..10}; do
        if ! check_port 8000; then
            echo -e "${GREEN}✓ 后端服务已停止${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done

    # 如果还没停止，强制杀死
    if check_port 8000; then
        echo ""
        echo -e "${YELLOW}强制停止后端服务...${NC}"
        fuser -k 8000/tcp 2>/dev/null
        sleep 1
        if ! check_port 8000; then
            echo -e "${GREEN}✓ 后端服务已强制停止${NC}"
        else
            echo -e "${RED}✗ 后端服务停止失败${NC}"
        fi
    fi
fi

# 停止前端服务
if [ "$FRONTEND_RUNNING" = true ]; then
    echo ""
    echo "停止前端服务..."
    pkill -f "vite" 2>/dev/null

    # 等待进程结束
    for i in {1..10}; do
        if ! check_port 3002; then
            echo -e "${GREEN}✓ 前端服务已停止${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done

    # 如果还没停止，强制杀死
    if check_port 3002; then
        echo ""
        echo -e "${YELLOW}强制停止前端服务...${NC}"
        fuser -k 3002/tcp 2>/dev/null
        sleep 1
        if ! check_port 3002; then
            echo -e "${GREEN}✓ 前端服务已强制停止${NC}"
        else
            echo -e "${RED}✗ 前端服务停止失败${NC}"
        fi
    fi
fi

echo ""
echo "========================================="
echo "  服务停止完成！"
echo "========================================="
echo ""

# 验证服务状态
echo "服务状态："
if check_port 8000; then
    echo -e "  ${RED}✗${NC} 后端服务仍在运行 (端口 8000)"
else
    echo -e "  ${GREEN}✓${NC} 后端服务已停止"
fi

if check_port 3002; then
    echo -e "  ${RED}✗${NC} 前端服务仍在运行 (端口 3002)"
else
    echo -e "  ${GREEN}✓${NC} 前端服务已停止"
fi
echo ""

if ! check_port 8000 && ! check_port 3002; then
    echo -e "${GREEN}✓ 所有服务已成功停止！${NC}"
else
    echo -e "${YELLOW}⚠️  部分服务未能停止，请手动检查${NC}"
fi