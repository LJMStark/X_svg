#!/usr/bin/env python3
"""
测试OpenRouter API连接和基本功能
"""

import os
import sys
import json
import time
import openai
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_api_connections():
    """测试所有API连接"""
    print("🔍 测试多API连接...")
    
    # 检查API密钥
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    results = {}
    
    # 测试OpenRouter
    if openrouter_key:
        print("\n📡 测试OpenRouter API...")
        try:
            client = openai.OpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com",
                    "X-Title": "TweetProcessor"
                }
            )
            
            response = client.chat.completions.create(
                model="moonshotai/kimi-k2:free",
                messages=[
                    {"role": "system", "content": "请回复'OpenRouter正常'"},
                    {"role": "user", "content": "测试"}
                ],
                max_tokens=10
            )
            print(f"✅ OpenRouter API连接成功")
            print(f"📝 响应: {response.choices[0].message.content}")
            results["openrouter"] = True
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                print("⚠️  OpenRouter速度限制或额度用完")
            else:
                print(f"❌ OpenRouter API失败: {e}")
            results["openrouter"] = False
    else:
        print("⚠️  未配置OpenRouter API密钥")
        results["openrouter"] = False
    
    # 测试Gemini
    if gemini_key:
        print("\n📡 测试Gemini API...")
        try:
            client = openai.OpenAI(
                api_key=gemini_key,
                base_url="http://xai-studio.top:8000"
            )
            
            # 使用Gemini API格式
            url = "http://xai-studio.top:8000/gemini/v1beta/models/gemini-2.5-flash:generateContent"
            payload = {
                "contents": [{
                    "parts": [{"text": "请回复'Gemini正常'"}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 50
                }
            }
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": gemini_key
            }
            
            import requests
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        response_text = candidate['content']['parts'][0]['text'].strip()
                        print(f"✅ Gemini API连接成功")
                        print(f"📝 响应: {response_text}")
                        results["gemini"] = True
                    else:
                        print("❌ Gemini API返回空响应")
                        results["gemini"] = False
                else:
                    print("❌ Gemini API返回无效响应")
                    results["gemini"] = False
            else:
                print(f"❌ Gemini API失败: {response.status_code} - {response.text}")
                results["gemini"] = False
                        
        except Exception as e:
            print(f"❌ Gemini API失败: {e}")
            results["gemini"] = False
    else:
        print("⚠️  未配置Gemini API密钥")
        results["gemini"] = False
    
    return results

def test_rate_limiting():
    """测试速度限制处理"""
    print("\n🔍 测试速度限制处理...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ 错误：未找到OPENROUTER_API_KEY环境变量")
        return False
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com",
            "X-Title": "TweetProcessor"
        }
    )
    
    # 连续发送多个请求，测试速度限制
    print("📞 发送连续请求测试速度限制...")
    
    for i in range(3):
        try:
            start_time = time.time()
            
            response = client.chat.completions.create(
                model="moonshotai/kimi-k2:free",
                messages=[
                    {"role": "system", "content": "回复'测试OK'"},
                    {"role": "user", "content": f"测试请求 {i+1}"}
                ],
                max_tokens=5
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"✅ 请求 {i+1} 成功 (响应时间: {response_time:.2f}秒)")
            
            # 检查响应头
            if hasattr(response, 'headers') and response.headers:
                remaining = response.headers.get('x-ratelimit-remaining')
                reset_time = response.headers.get('x-ratelimit-reset')
                if remaining:
                    print(f"📊 剩余请求次数: {remaining}")
                if reset_time:
                    reset_seconds = int(reset_time) / 1000 - time.time()
                    print(f"📊 重置时间: {reset_seconds:.1f}秒后")
            
            # 短暂等待
            time.sleep(1)
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                print(f"⚠️  请求 {i+1} 遇到速度限制: {e}")
            else:
                print(f"❌ 请求 {i+1} 失败: {e}")
    
    return True

def test_configuration_files():
    """测试配置文件"""
    print("\n🔍 测试配置文件...")
    
    # 检查必需文件
    required_files = [
        "twillot-public-post-sorted.json",
        "svg提示词.txt", 
        "小红书文案提示词.txt"
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")
            all_files_exist = False
    
    # 检查配置文件
    config_files = ["config.json", "config.example.json", ".env.example"]
    for file_path in config_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} 存在")
        else:
            print(f"⚠️  {file_path} 不存在 (可选)")
    
    return all_files_exist

def test_tweet_processor():
    """测试推文处理器初始化"""
    print("\n🔍 测试推文处理器初始化...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ 错误：未找到OPENROUTER_API_KEY环境变量")
        return False
    
    try:
        from batch_process_tweets import TweetProcessor
        
        processor = TweetProcessor()
        
        print("✅ TweetProcessor初始化成功")
        print(f"📁 输出目录: {processor.output_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ TweetProcessor初始化失败: {e}")
        return False

def test_failover():
    """测试故障转移机制"""
    print("\n🔍 测试故障转移机制...")
    
    # 检查API密钥
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not openrouter_key:
        print("⚠️  未配置OpenRouter API密钥，跳过故障转移测试")
        return False
    
    if not gemini_key:
        print("⚠️  未配置Gemini API密钥，跳过故障转移测试")
        return False
    
    try:
        from api_client import APIClientManager, OpenRouterClient, GeminiClient
        
        # 创建API客户端
        openrouter_client = OpenRouterClient(openrouter_key)
        gemini_client = GeminiClient(gemini_key)
        
        # 创建API管理器
        clients = {
            "openrouter": openrouter_client,
            "gemini": gemini_client
        }
        api_manager = APIClientManager(clients, primary="openrouter")
        
        # 测试正常的OpenRouter调用
        print("📡 测试主API (OpenRouter)...")
        try:
            result = api_manager.call_with_fallback(
                "请回复'主API正常'",
                "测试主API"
            )
            if result[1]:
                print("✅ 主API调用成功")
            else:
                print("⚠️  主API调用失败，这是正常的测试场景")
        except Exception as e:
            print(f"⚠️  主API调用失败（预期行为）: {e}")
        
        # 测试故障转移到Gemini
        print("\n🔄 测试故障转移到备用API (Gemini)...")
        
        # 创建Gemini客户端直接测试
        gemini_client = GeminiClient(gemini_key)
        result = gemini_client.call_api(
            "请回复'备用API正常'",
            "测试备用API",
            max_tokens=50
        )
        
        if result:
            print("✅ 备用API (Gemini) 调用成功")
            print(f"📝 响应: {result}")
            return True
        else:
            print("❌ 备用API调用失败")
            return False
            
    except ImportError as e:
        print(f"❌ 导入API客户端失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 故障转移测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始多API系统测试...")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    api_results = test_api_connections()
    for api, result in api_results.items():
        results.append((f"{api.title()} API", result))
    
    results.append(("配置文件", test_configuration_files()))
    results.append(("推文处理器", test_tweet_processor()))
    results.append(("故障转移", test_failover()))
    
    # 输出结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 所有测试通过！系统已准备就绪。")
        print("\n📝 使用说明:")
        print("1. 设置环境变量:")
        print("   export OPENROUTER_API_KEY='your_openrouter_key'")
        print("   export GEMINI_API_KEY='your_gemini_key'")
        print("2. 运行程序: python batch_process_tweets.py --count 5")
        print("3. 或使用示例: python run_example.py")
        print("4. 查看统计: python batch_process_tweets.py --count 5 --stats")
    else:
        print("⚠️  部分测试失败，请检查配置后重试。")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())