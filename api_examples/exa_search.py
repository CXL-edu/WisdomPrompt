import os
from dotenv import load_dotenv
from exa_py import Exa
import json

load_dotenv()

# 临时禁用代理（如果环境变量中设置了代理但代理不可用）
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# Exa Search API 配置
api_key = os.getenv('EXA_API_KEY')

# 初始化 Exa 客户端
exa = Exa(api_key)

# 搜索查询
query = "Python programming tutorial"

print(f"使用 Exa Search API 搜索: {query}\n")

try:
    # 基本搜索
    print("执行基本搜索...")
    results = exa.search(
        query,
        num_results=10,  # 返回结果数量
        category="research",  # 类别：research, news, company, social
        start_published_date="2020-01-01",  # 开始日期（可选）
        # end_published_date="2024-12-31",  # 结束日期（可选）
    )
    
    print("=" * 60)
    print("Exa Search API 返回结果")
    print("=" * 60)
    print(f"\n查询: {query}")
    print(f"找到 {len(results.results)} 个结果:\n")
    
    # 显示搜索结果
    for i, result in enumerate(results.results, 1):
        print(f"结果 {i}:")
        print(f"  标题: {result.title}")
        print(f"  URL: {result.url}")
        print(f"  作者: {result.author or 'N/A'}")
        print(f"  发布日期: {result.published_date or 'N/A'}")
        print(f"  文本摘要: {result.text[:150] if result.text else 'N/A'}...")
        print()
    
    # 搜索并获取内容（包含完整文本）
    print("\n执行搜索并获取内容...")
    results_with_content = exa.search_and_contents(
        query,
        num_results=5,
        text={"max_characters": 500},  # 限制文本长度
        highlights=True,  # 启用高亮
    )
    
    print(f"\n获取到 {len(results_with_content.results)} 个带内容的结果:\n")
    for i, result in enumerate(results_with_content.results[:3], 1):  # 只显示前3条
        print(f"结果 {i} (带内容):")
        print(f"  标题: {result.title}")
        print(f"  URL: {result.url}")
        if result.text:
            print(f"  内容预览: {result.text[:200]}...")
        if result.highlights:
            print(f"  高亮片段: {result.highlights[0] if result.highlights else 'N/A'}")
        print()
    
    # 保存基本搜索结果到 JSON 文件
    output_file = "exa_search_results.json"
    results_data = {
        "query": query,
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "author": r.author,
                "published_date": str(r.published_date) if r.published_date else None,
                "text": r.text[:500] if r.text else None,
            }
            for r in results.results
        ]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)
    print(f"\n基本搜索结果已保存到: {output_file}")
    
except Exception as e:
    print(f"发生错误: {e}")
    import traceback
    traceback.print_exc()

print("\n完成！")
