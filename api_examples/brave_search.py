import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

# 临时禁用代理（如果环境变量中设置了代理但代理不可用）
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# Brave Search API 配置
api_key = os.getenv('BRAVE_API_KEY')
base_url = "https://api.search.brave.com/res/v1"

# 搜索查询
query = "Python programming tutorial"

print(f"使用 Brave Search API 搜索: {query}\n")

# 构建请求头
headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": api_key
}

# 构建请求参数
params = {
    "q": query,
    "count": 10,  # 返回结果数量
    "search_lang": "zh-hans",  # 搜索语言（可选：zh-hans, zh-hant, en 等）
    "country": "US",  # 国家代码（可选）
    "safesearch": "moderate",  # 安全搜索级别：off, moderate, strict
    "freshness": "py",  # 时间过滤：pd (过去一天), pw (过去一周), pm (过去一月), py (过去一年)
}

# 发送搜索请求
try:
    response = requests.get(
        f"{base_url}/web/search",
        headers=headers,
        params=params
    )
    response.raise_for_status()
    results = response.json()
    
    print("=" * 60)
    print("Brave Search API 返回结果")
    print("=" * 60)
    print(f"\n查询: {query}")
    print(f"总结果数: {results.get('query', {}).get('total_results', 'N/A')}")
    
    # 显示搜索结果
    web_results = results.get('web', {}).get('results', [])
    print(f"\n找到 {len(web_results)} 个结果:\n")
    
    for i, result in enumerate(web_results, 1):
        print(f"结果 {i}:")
        print(f"  标题: {result.get('title', 'N/A')}")
        print(f"  URL: {result.get('url', 'N/A')}")
        print(f"  描述: {result.get('description', 'N/A')[:100]}...")
        print(f"  年龄: {result.get('age', 'N/A')}")
        print()
    
    # 显示新闻结果（如果有）
    news_results = results.get('news', {}).get('results', [])
    if news_results:
        print(f"\n新闻结果 ({len(news_results)} 条):\n")
        for i, result in enumerate(news_results[:3], 1):  # 只显示前3条
            print(f"新闻 {i}:")
            print(f"  标题: {result.get('title', 'N/A')}")
            print(f"  URL: {result.get('url', 'N/A')}")
            print(f"  描述: {result.get('description', 'N/A')[:100]}...")
            print(f"  发布时间: {result.get('age', 'N/A')}")
            print()
    
    # 保存完整结果到 JSON 文件
    output_file = "brave_search_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n完整结果已保存到: {output_file}")
    
except requests.exceptions.RequestException as e:
    print(f"请求错误: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"响应状态码: {e.response.status_code}")
        print(f"响应内容: {e.response.text}")
except Exception as e:
    print(f"发生错误: {e}")

print("\n完成！")
