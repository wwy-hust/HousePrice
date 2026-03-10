#!/bin/bash

# 杀掉占用 8000 端口的旧进程
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "检测到端口 8000 已被占用，正在关闭旧进程..."
    lsof -ti:8000 | xargs kill -9
    sleep 1
fi

cd "$(dirname "$0")"

echo "启动房价数据可视化服务器..."
python web_server.py --host localhost --port 8000 &

sleep 1
echo "服务已启动：http://localhost:8000"
open http://localhost:8000
