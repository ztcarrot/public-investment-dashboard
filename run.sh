#!/bin/bash
# 投资组合仪表盘 - 快速启动脚本

cd "$(dirname "$0")"

echo "========================================"
echo "  投资组合仪表盘 - Streamlit版"
echo "========================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖包..."
pip install -q -r requirements.txt

echo ""
echo "✅ 环境准备完成！"
echo ""
echo "========================================"
echo "  启动应用..."
echo "========================================"
echo ""
echo "访问地址: http://localhost:8501"
echo "按 Ctrl+C 停止服务"
echo ""
echo "========================================"
echo ""

# 启动Streamlit
streamlit run app.py
