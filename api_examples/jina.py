import os
from dotenv import load_dotenv
import requests
import json
from urllib.parse import quote
from typing import Dict, List, Optional, Union

load_dotenv()

# 临时禁用代理（如果环境变量中设置了代理但代理不可用）
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)


class JinaClient:
    """Jina API 客户端，用于读取和搜索网页内容"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Jina 客户端
        
        Args:
            api_key: Jina API Key，如果为 None 则从环境变量 JINA_API_KEY 读取
        """
        self.api_key = api_key or os.getenv('JINA_API_KEY')
        self.base_url_read = "https://r.jina.ai"
        self.base_url_search = "https://s.jina.ai"
        
        # 构建请求头
        self.headers = {
            "Accept": "application/json",
            "X-With-Generated-Alt": "true",
        }
        
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def read_url(self, url: str, save_to_file: Optional[str] = None, verbose: bool = True) -> Dict:
        """
        读取单个网页内容
        
        Args:
            url: 要读取的网页 URL
            save_to_file: 可选，保存结果的文件路径
            verbose: 是否打印详细信息
            
        Returns:
            包含 title, url, content 的字典
        """
        if verbose:
            print(f"读取 URL: {url}")
        
        try:
            reader_url = f"{self.base_url_read}/{url}"
            response = requests.get(reader_url, headers=self.headers)
            response.raise_for_status()
            
            # 解析响应
            result = None
            content = None
            
            try:
                result = response.json()
                if isinstance(result, dict):
                    title = result.get('title', '')
                    url_from_result = result.get('url', '')
                    content = result.get('content', '')
                    if not content:
                        content = response.text
                elif isinstance(result, str):
                    content = result
                    result = None
                else:
                    content = response.text
                    result = None
            except (json.JSONDecodeError, ValueError):
                content = response.text
                result = None
            
            # 构建返回结果
            if result and isinstance(result, dict):
                result_data = {
                    "url": result.get('url', url),
                    "title": result.get('title', ''),
                    "content": result.get('content', '') or content or ''
                }
            else:
                result_data = {
                    "url": url,
                    "title": None,
                    "content": content or ''
                }
            
            # 显示结果
            if verbose:
                if result_data.get('title'):
                    print(f"标题: {result_data['title']}")
                else:
                    print(f"标题: N/A")
                print(f"URL: {result_data['url']}")
                if result_data.get('content'):
                    preview = result_data['content'][:500]
                    print(f"内容预览 (前500字符): {preview}..." if len(result_data['content']) > 500 else f"内容: {preview}")
                else:
                    print("内容: 无内容返回")
            
            # 保存到文件
            if save_to_file:
                with open(save_to_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                if verbose:
                    print(f"结果已保存到: {save_to_file}")
            
            return result_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求错误: {e}"
            if verbose:
                print(error_msg)
                if hasattr(e, 'response') and e.response is not None:
                    print(f"响应状态码: {e.response.status_code}")
                    print(f"响应内容: {e.response.text[:500]}")
            raise Exception(error_msg) from e
        except Exception as e:
            if verbose:
                print(f"发生错误: {e}")
                import traceback
                traceback.print_exc()
            raise
    
    def read_url_post(self, url: str, verbose: bool = True) -> Dict:
        """
        使用 POST 方法读取 URL（适用于 SPA 或带 # 的 URL）
        
        Args:
            url: 要读取的网页 URL
            verbose: 是否打印详细信息
            
        Returns:
            包含 title, url, content 的字典
        """
        if verbose:
            print(f"读取 SPA URL: {url}")
        
        try:
            response = requests.post(
                self.base_url_read,
                headers=self.headers,
                data={"url": url}
            )
            response.raise_for_status()
            
            if response.headers.get('Content-Type', '').startswith('application/json'):
                result = response.json()
                result_data = {
                    "url": result.get('url', url),
                    "title": result.get('title', ''),
                    "content": result.get('content', '')
                }
            else:
                content = response.text
                result_data = {
                    "url": url,
                    "title": None,
                    "content": content
                }
            
            if verbose:
                if result_data.get('title'):
                    print(f"标题: {result_data['title']}")
                content_preview = result_data.get('content', '')[:300]
                print(f"内容预览: {content_preview}...")
            
            return result_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求错误: {e}"
            if verbose:
                print(error_msg)
                if hasattr(e, 'response') and e.response is not None:
                    print(f"响应状态码: {e.response.status_code}")
                    print(f"响应内容: {e.response.text[:500]}")
            raise Exception(error_msg) from e
    
    def read_url_stream(self, url: str, verbose: bool = True) -> str:
        """
        使用流式模式读取网页
        
        Args:
            url: 要读取的网页 URL
            verbose: 是否打印详细信息
            
        Returns:
            网页内容的字符串
        """
        if verbose:
            print(f"流式读取 URL: {url}")
        
        try:
            stream_headers = self.headers.copy()
            stream_headers["Accept"] = "text/event-stream"
            
            reader_url = f"{self.base_url_read}/{url}"
            response = requests.get(reader_url, headers=stream_headers, stream=True)
            response.raise_for_status()
            
            if verbose:
                print("\n接收流式数据...")
            
            chunks = []
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        chunk = decoded_line[6:]
                        chunks.append(chunk)
                        if verbose:
                            print(f"收到数据块 {len(chunks)} (长度: {len(chunk)})")
            
            if chunks:
                final_content = chunks[-1]
                if verbose:
                    print(f"\n最终内容长度: {len(final_content)} 字符")
                    print(f"内容预览: {final_content[:300]}...")
                return final_content
            else:
                return ""
                
        except requests.exceptions.RequestException as e:
            error_msg = f"请求错误: {e}"
            if verbose:
                print(error_msg)
                if hasattr(e, 'response') and e.response is not None:
                    print(f"响应状态码: {e.response.status_code}")
            raise Exception(error_msg) from e
    
    def search(self, query: str, max_results: int = 3, save_to_file: Optional[str] = None, 
               verbose: bool = True) -> Dict:
        """
        搜索网页
        
        Args:
            query: 搜索查询字符串
            max_results: 最多显示的结果数量
            save_to_file: 可选，保存结果的文件路径
            verbose: 是否打印详细信息
            
        Returns:
            包含查询、结果列表、最相关结果的字典
        """
        if verbose:
            print(f"搜索查询: {query}")
        
        try:
            encoded_query = quote(query)
            search_url = f"{self.base_url_search}/{encoded_query}"
            
            response = requests.get(search_url, headers=self.headers)
            response.raise_for_status()
            
            # 解析响应
            try:
                response_data = response.json()
            except (json.JSONDecodeError, ValueError):
                content = response.text
                if verbose:
                    print(f"\n搜索结果 (前1000字符):")
                    print(content[:1000] + "..." if len(content) > 1000 else content)
                results_data = {
                    "query": query,
                    "total_count": 1,
                    "results": [{"content": content}],
                    "most_relevant": {"content": content}
                }
            else:
                # 处理不同的响应格式
                actual_results = self._parse_search_results(response_data)
                
                # 显示结果
                display_count = min(max_results, len(actual_results))
                if verbose:
                    print(f"\n找到 {len(actual_results)} 个搜索结果，显示前 {display_count} 个:\n")
                    for i, result in enumerate(actual_results[:display_count], 1):
                        if isinstance(result, dict):
                            print(f"结果 {i}:")
                            print(f"  标题: {result.get('title', 'N/A')}")
                            print(f"  URL: {result.get('url', 'N/A')}")
                            content = result.get('content', '')
                            if content:
                                preview = content[:200] + "..." if len(content) > 200 else content
                                print(f"  内容预览: {preview}")
                            else:
                                print(f"  内容: 无内容")
                            print()
                
                # 构建返回结果
                results_data = {
                    "query": query,
                    "total_count": len(actual_results),
                    "displayed_count": display_count,
                    "results": actual_results,
                    "most_relevant": actual_results[0] if actual_results else None
                }
            
            # 保存到文件
            if save_to_file:
                with open(save_to_file, 'w', encoding='utf-8') as f:
                    json.dump(results_data, f, ensure_ascii=False, indent=2)
                if verbose:
                    print(f"搜索结果已保存到: {save_to_file}")
            
            return results_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求错误: {e}"
            if verbose:
                print(error_msg)
                if hasattr(e, 'response') and e.response is not None:
                    print(f"响应状态码: {e.response.status_code}")
                    print(f"响应内容: {e.response.text[:500]}")
            raise Exception(error_msg) from e
        except Exception as e:
            if verbose:
                print(f"发生错误: {e}")
                import traceback
                traceback.print_exc()
            raise
    
    def _parse_search_results(self, response_data: Union[Dict, List]) -> List[Dict]:
        """
        解析搜索结果的响应数据，处理不同的响应格式
        
        Args:
            response_data: API 返回的原始数据
            
        Returns:
            解析后的结果列表
        """
        actual_results: List[Dict] = []
        
        # 格式1: 直接是列表
        if isinstance(response_data, list):
            actual_results = [item if isinstance(item, dict) else {"content": str(item)} 
                            for item in response_data]
        # 格式2: {"results": [{"code": 200, "status": 20000, "data": [...]}]}
        elif isinstance(response_data, dict):
            if 'results' in response_data:
                results_list = response_data.get('results', [])
                if results_list and isinstance(results_list[0], dict):
                    data = results_list[0].get('data', [])
                    if isinstance(data, list):
                        actual_results = [item if isinstance(item, dict) else {"content": str(item)} 
                                        for item in data]
                    else:
                        actual_results = [item if isinstance(item, dict) else {"content": str(item)} 
                                        for item in results_list]
                else:
                    actual_results = [item if isinstance(item, dict) else {"content": str(item)} 
                                    for item in results_list]
            # 格式3: {"data": [...]}
            elif 'data' in response_data:
                data = response_data.get('data', [])
                if isinstance(data, list):
                    actual_results = [item if isinstance(item, dict) else {"content": str(item)} 
                                    for item in data]
                else:
                    actual_results = [response_data]
            # 格式4: 单个结果对象
            else:
                actual_results = [response_data]
        else:
            actual_results = [{"content": str(response_data)}]
        
        return actual_results


# ========== 示例代码 ==========
if __name__ == "__main__":
    # 创建客户端实例
    client = JinaClient()
    
    if client.api_key:
        print("使用 API Key 进行认证")
    else:
        print("未设置 API Key，使用免费模式（速率限制较低）")
    
    print("=" * 60)
    print("Jina Reader API 示例")
    print("=" * 60)
    
    # 示例 1: 读取单个网页
    print("\n【示例 1】读取单个网页\n")
    try:
        result = client.read_url(
            url="https://github.com/CXL-edu",
            save_to_file="jina_read_result.json"
        )
    except Exception as e:
        print(f"读取失败: {e}")
    
    # 示例 2: 搜索网页
    print("\n\n【示例 2】搜索网页\n")
    try:
        search_results = client.search(
            query="Python programming tutorial",
            max_results=3,
            save_to_file="jina_search_results.json"
        )
    except Exception as e:
        print(f"搜索失败: {e}")
    
    # 示例 3: 使用 POST 方法读取 URL（适用于 SPA）
    print("\n\n【示例 3】使用 POST 方法读取 URL（适用于 SPA）\n")
    try:
        result = client.read_url_post(url="https://example.com/#/route")
    except Exception as e:
        print(f"读取失败: {e}")
    
    # 示例 4: 使用流式模式读取网页
    print("\n\n【示例 4】使用流式模式读取网页\n")
    try:
        content = client.read_url_stream(
            url="https://en.wikipedia.org/wiki/Python_(programming_language)"
        )
    except Exception as e:
        print(f"读取失败: {e}")
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
