#!/bin/bash

# 30周均线交易系统 - 一键启动脚本

echo "========================================="
echo "  30周均线交易系统 - 服务启动"
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

# 检查服务是否已在运行
echo "检查服务状态..."

if check_port 8000; then
    echo -e "${YELLOW}⚠️  后端服务已在运行 (端口 8000)${NC}"
    BACKEND_RUNNING=true
else
    echo -e "${GREEN}✓ 后端服务未运行${NC}"
    BACKEND_RUNNING=false
fi

if check_port 3002; then
    echo -e "${YELLOW}⚠️  前端服务已在运行 (端口 3002)${NC}"
    FRONTEND_RUNNING=true
else
    echo -e "${GREEN}✓ 前端服务未运行${NC}"
    FRONTEND_RUNNING=false
fi

echo ""

# 如果两个服务都在运行，询问是否重启
if [ "$BACKEND_RUNNING" = true ] && [ "$FRONTEND_RUNNING" = true ]; then
    echo -e "${YELLOW}所有服务已在运行！${NC}"
    read -p "是否要重启服务？(y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消启动。"
        exit 0
    fi
    echo "正在停止现有服务..."
    pkill -f "python.*main.py.*serve" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    sleep 2
    echo ""
fi

# 启动后端服务
if [ "$BACKEND_RUNNING" = false ]; then
    echo "========================================="
    echo "启动后端服务..."
    echo "========================================="
    cd "$BACKEND_DIR" || exit 1

    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  未找到 .env 文件，从 .env.example 复制...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
    fi

    # 检查 Python 虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}⚠️  未找到 Python 虚拟环境，正在创建...${NC}"
        python3 -m venv venv
        echo "安装依赖..."
        source venv/bin/activate
        pip install -q -r requirements.txt
        deactivate
    fi

    # 启动后端
    echo "启动后端 API 服务 (端口 8000)..."
    nohup python3 main.py --serve --host 0.0.0.0 --port 8000 > "$BACKEND_DIR/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "后端服务 PID: $BACKEND_PID"

    # 等待后端启动
    echo "等待后端服务启动..."
    for i in {1..30}; do
        if check_port 8000; then
            echo -e "${GREEN}✓ 后端服务启动成功！${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done

    if ! check_port 8000; then
        echo -e "${RED}✗ 后端服务启动失败！${NC}"
        echo "请查看日志: $BACKEND_DIR/logs/backend.log"
        exit 1
    fi
    echo ""
fi

# 启动前端服务
if [ "$FRONTEND_RUNNING" = false ]; then
    echo "========================================="
    echo "启动前端服务..."
    echo "========================================="
    cd "$FRONTEND_DIR" || exit 1

    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}⚠️  未安装依赖，正在安装...${NC}"
        npm install
    fi

    # 启动前端
    echo "启动前端开发服务器 (端口 3002)..."
    nohup npm run dev > "$FRONTEND_DIR/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "前端服务 PID: $FRONTEND_PID"

    # 等待前端启动
    echo "等待前端服务启动..."
    for i in {1..30}; do
        if check_port 3002; then
            echo -e "${GREEN}✓ 前端服务启动成功！${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done

    if ! check_port 3002; then
        echo -e "${RED}✗ 前端服务启动失败！${NC}"
        echo "请查看日志: $FRONTEND_DIR/logs/frontend.log"
        exit 1
    fi
    echo ""
fi

# 显示服务状态
echo "========================================="
echo "  服务启动完成！"
echo "========================================="
echo ""
echo "服务访问地址："
echo -e "  前端: ${GREEN}http://$(hostname -I | awk '{print $1}'):3002${NC}"
echo -e "  后端: ${GREEN}http://$(hostname -I | awk '{print $1}'):8000${NC}"
echo ""
echo "日志文件："
echo "  后端: $BACKEND_DIR/logs/backend.log"
echo "  前端: $FRONTEND_DIR/logs/frontend.log"
echo ""
echo "使用以下命令查看日志："
echo "  后端: tail -f $BACKEND_DIR/logs/backend.log"
echo "  前端: tail -f $FRONTEND_DIR/logs/frontend.log"
echo ""
echo -e "${GREEN}✓ 所有服务已成功启动！${NC}"