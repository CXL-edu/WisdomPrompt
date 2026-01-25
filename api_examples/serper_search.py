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

# Serper Search API 配置
api_key = os.getenv('SERPER_API_KEY')
base_url = "https://google.serper.dev"

# 搜索查询
query = "Python programming tutorial"

print(f"使用 Serper Search API 搜索: {query}\n")

# 构建请求头
headers = {
    "X-API-KEY": api_key,
    "Content-Type": "application/json"
}

# 构建请求体
payload = {
    "q": query,
    "num": 10,  # 返回结果数量（1-100）
    "gl": "us",  # 国家代码
    "hl": "zh-cn",  # 语言代码
    "autocorrect": True,  # 自动纠正拼写
}

# 发送搜索请求
try:
    response = requests.post(
        f"{base_url}/search",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    results = response.json()
    
    print("=" * 60)
    print("Serper Search API 返回结果")
    print("=" * 60)
    print(f"\n查询: {query}")
    
    # 显示搜索结果
    organic_results = results.get('organic', [])
    print(f"\n找到 {len(organic_results)} 个有机搜索结果:\n")
    
    for i, result in enumerate(organic_results, 1):
        print(f"结果 {i}:")
        print(f"  标题: {result.get('title', 'N/A')}")
        print(f"  链接: {result.get('link', 'N/A')}")
        print(f"  摘要: {result.get('snippet', 'N/A')[:100]}...")
        if 'position' in result:
            print(f"  排名: {result.get('position')}")
        if 'date' in result:
            print(f"  日期: {result.get('date')}")
        print()
    
    # 显示知识图谱结果（如果有）
    knowledge_graph = results.get('knowledgeGraph', {})
    if knowledge_graph:
        print("\n知识图谱信息:")
        print(f"  标题: {knowledge_graph.get('title', 'N/A')}")
        print(f"  类型: {knowledge_graph.get('type', 'N/A')}")
        print(f"  描述: {knowledge_graph.get('description', 'N/A')[:100]}...")
        if 'website' in knowledge_graph:
            print(f"  网站: {knowledge_graph.get('website')}")
        print()
    
    # 显示相关问题（如果有）
    related_questions = results.get('relatedQuestions', [])
    if related_questions:
        print(f"\n相关问题 ({len(related_questions)} 个):")
        for i, question in enumerate(related_questions[:5], 1):  # 只显示前5个
            print(f"  {i}. {question.get('question', 'N/A')}")
        print()
    
    # 显示答案框（如果有）
    answer_box = results.get('answerBox', {})
    if answer_box:
        print("答案框:")
        print(f"  答案: {answer_box.get('answer', 'N/A')}")
        if 'title' in answer_box:
            print(f"  标题: {answer_box.get('title')}")
        if 'link' in answer_box:
            print(f"  链接: {answer_box.get('link')}")
        print()
    
    # 显示图片结果（如果有）
    images = results.get('images', [])
    if images:
        print(f"\n图片结果 ({len(images)} 张):")
        for i, image in enumerate(images[:3], 1):  # 只显示前3张
            print(f"  图片 {i}: {image.get('link', 'N/A')}")
        print()
    
    # 保存完整结果到 JSON 文件
    output_file = "serper_search_results.json"
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
    import traceback
    traceback.print_exc()

print("\n完成！")
