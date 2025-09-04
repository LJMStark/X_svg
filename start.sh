#!/bin/bash

# OpenRouter Tweet Processor - 快速开始脚本

echo "🚀 OpenRouter Tweet Processor 快速开始"
echo "========================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3，请先安装Python"
    exit 1
fi

echo "✅ Python环境检查通过"

# 检查依赖
echo "📦 检查依赖..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 未找到requirements.txt文件"
    exit 1
fi

# 安装依赖（如果需要）
read -p "是否安装/更新依赖? (y/n): " install_deps
if [ "$install_deps" = "y" ]; then
    echo "📦 安装依赖..."
    pip3 install -r requirements.txt
fi

# 检查API密钥
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️  警告: 未设置OPENROUTER_API_KEY环境变量"
    echo "请设置API密钥:"
    echo "export OPENROUTER_API_KEY='your_api_key_here'"
    echo ""
    read -p "是否现在设置API密钥? (y/n): " set_key
    if [ "$set_key" = "y" ]; then
        read -p "请输入您的OpenRouter API密钥: " api_key
        export OPENROUTER_API_KEY="$api_key"
        echo "✅ API密钥已设置为当前会话"
    fi
else
    echo "✅ API密钥已设置"
fi

# 检查必需文件
echo "📁 检查必需文件..."
required_files=("twillot-public-post-sorted.json" "svg提示词.txt" "小红书文案提示词.txt")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo "❌ 错误: 以下必需文件不存在:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    exit 1
fi

echo "✅ 所有必需文件存在"

# 运行测试
echo ""
read -p "是否运行API连接测试? (y/n): " run_test
if [ "$run_test" = "y" ]; then
    echo "🧪 运行API测试..."
    python3 test_openrouter.py
    test_result=$?
    if [ $test_result -ne 0 ]; then
        echo "❌ API测试失败，请检查配置"
        exit 1
    fi
fi

# 选择运行模式
echo ""
echo "请选择运行模式:"
echo "1) 运行示例脚本 (处理前5条记录)"
echo "2) 自定义批量处理"
echo "3) 运行完整测试"
echo "4) 退出"

read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo "🚀 运行示例脚本..."
        python3 run_example.py
        ;;
    2)
        read -p "输入处理数量 (默认全部): " count
        read -p "输入开始索引 (默认0): " start
        
        cmd="python3 batch_process_tweets.py"
        if [ ! -z "$OPENROUTER_API_KEY" ]; then
            cmd="$cmd --api-key '$OPENROUTER_API_KEY'"
        fi
        if [ ! -z "$count" ]; then
            cmd="$cmd --count $count"
        fi
        if [ ! -z "$start" ]; then
            cmd="$cmd --start $start"
        fi
        
        echo "🚀 执行命令: $cmd"
        eval $cmd
        ;;
    3)
        echo "🧪 运行完整测试..."
        python3 test_openrouter.py
        ;;
    4)
        echo "👋 退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "✨ 处理完成！"
echo "📁 查看结果: ls -la output/"
echo "📊 查看日志: cat batch_process.log"