#!/usr/bin/env python3
"""
WebFetch 统一脚本 - 智能网页内容获取工具
集成所有功能，自动处理各种网站（包括GitHub等）
"""

import requests
from typing import Optional, Literal, Union, cast
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import html2text


# ============================================================================
# 异常类
# ============================================================================

class WebFetchError(Exception):
    """WebFetch exception class"""
    pass


# ============================================================================
# 核心WebFetch类
# ============================================================================

class WebFetch:
    """
    智能网页内容获取器
    
    支持:
    - 自动检测GitHub URL并转换为raw格式
    - HTTP/HTTPS协议
    - 三种输出格式 (markdown, text, html)
    - 智能错误处理
    - 超时控制
    """
    
    MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_TIMEOUT = 30  # 30 seconds
    MAX_TIMEOUT = 120  # 2 minutes
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    ACCEPT_HEADERS = {
        "markdown": "text/markdown;q=1.0, text/x-markdown;q=0.9, text/plain;q=0.8, text/html;q=0.7, */*;q=0.1",
        "text": "text/plain;q=1.0, text/markdown;q=0.9, text/html;q=0.8, */*;q=0.1",
        "html": "text/html;q=1.0, application/xhtml+xml;q=0.9, text/plain;q=0.8, text/markdown;q=0.7, */*;q=0.1",
    }
    
    TAGS_TO_REMOVE = ['script', 'style', 'noscript', 'iframe', 'object', 'embed', 'meta', 'link']
    
    GITHUB_PATTERNS = [
        r'https?://github\.com/([^/]+)/([^/]+)/?$',
        r'https?://github\.com/([^/]+)/([^/]+)/?#.*'
    ]
    
    def __init__(self, 
                 url: str, 
                 format: Literal["markdown", "text", "html"] = "markdown",
                 timeout: Optional[int] = None,
                 user_agent: Optional[str] = None,
                 smart: bool = True):
        """
        初始化WebFetch
        
        Args:
            url: 要获取的URL
            format: 输出格式 - "markdown" (默认), "text", 或 "html"
            timeout: 超时时间（秒），最大120秒
            user_agent: 自定义User-Agent字符串
            smart: 是否启用智能处理（自动处理GitHub等特殊网站）
        """
        self.original_url = url
        self.format = format
        self.timeout = timeout
        self.user_agent = user_agent
        self.smart = smart
        self.headers = self._build_headers()
        self.github_raw_url = None
        self.github_processed = False
        
        # 验证URL
        self._validate_url()
        
        # 初始化URL
        self.url = url
        
        # 智能处理URL
        if smart:
            self.url = self._smart_process_url(url, format)
        else:
            self.url = url
    
    def _build_headers(self) -> dict:
        """构建请求头"""
        headers = self.DEFAULT_HEADERS.copy()
        
        if self.format in self.ACCEPT_HEADERS:
            headers["Accept"] = self.ACCEPT_HEADERS[self.format]
        
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        
        return headers
    
    def _validate_url(self) -> None:
        """验证URL格式"""
        if not self.original_url.startswith("http://") and not self.original_url.startswith("https://"):
            raise WebFetchError("URL must start with http:// or https://")
        
        try:
            parsed = urlparse(self.original_url)
            if not parsed.netloc:
                raise WebFetchError("Invalid URL format")
        except Exception as e:
            raise WebFetchError(f"Invalid URL: {e}")
    
    def _smart_process_url(self, url: str, format: str) -> str:
        """
        智能处理URL（处理GitHub等特殊网站）
        
        Args:
            url: 原始URL
            format: 请求的格式
            
        Returns:
            处理后的URL
        """
        processed_url = url  # 默认返回原始URL
        
        # 检查是否是GitHub仓库URL
        for pattern in self.GITHUB_PATTERNS:
            match = re.match(pattern, url)
            if match:
                user, repo = match.groups()
                
                # 如果请求markdown或text格式，尝试获取README的raw版本
                if format in ['markdown', 'text']:
                    if self._try_github_raw_url(user, repo) and self.github_raw_url:
                        processed_url = self.github_raw_url
                
                break
        
        return processed_url
    
    def _try_github_raw_url(self, user: str, repo: str) -> bool:
        """
        尝试获取GitHub README的raw版本
        
        Args:
            user: GitHub用户名
            repo: 仓库名
            
        Returns:
            是否成功找到raw URL
        """
        raw_urls = [
            f'https://raw.githubusercontent.com/{user}/{repo}/main/README.md',
            f'https://raw.githubusercontent.com/{user}/{repo}/master/README.md',
        ]
        
        for raw_url in raw_urls:
            try:
                response = requests.head(raw_url, timeout=5, headers=self.DEFAULT_HEADERS)
                if response.status_code == 200:
                    self.github_raw_url = raw_url
                    self.url = raw_url
                    self.github_processed = True
                    print(f"  [智能处理] 检测到GitHub仓库，使用raw URL获取README")
                    print(f"  [原始URL] {self.original_url}")
                    print(f"  [转换URL] {raw_url}")
                    return True
            except:
                continue
        
        return False
    
    def _get_timeout(self) -> tuple:
        """获取超时设置"""
        timeout = self.timeout if self.timeout is not None else self.DEFAULT_TIMEOUT
        timeout = min(timeout, self.MAX_TIMEOUT)
        return (timeout, timeout)
    
    def _check_response_size(self, response: requests.Response) -> None:
        """检查响应大小"""
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_RESPONSE_SIZE:
            raise WebFetchError(f"Response too large (exceeds {self.MAX_RESPONSE_SIZE} bytes)")
        
        content_length_actual = len(response.content)
        if content_length_actual > self.MAX_RESPONSE_SIZE:
            raise WebFetchError(f"Response too large (exceeds {self.MAX_RESPONSE_SIZE} bytes)")
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """从HTML提取纯文本"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        for tag in self.TAGS_TO_REMOVE:
            for element in soup.find_all(tag):
                element.decompose()
        
        text = soup.get_text(separator=' ')
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _convert_html_to_markdown(self, html_content: str) -> str:
        """将HTML转换为Markdown"""
        h = html2text.HTML2Text()
        h.ignore_images = False
        h.ignore_links = False
        h.body_width = 0
        h.unicode_snob = True
        h.skip_internal_links = False
        
        soup = BeautifulSoup(html_content, 'lxml')
        for tag in self.TAGS_TO_REMOVE:
            for element in soup.find_all(tag):
                element.decompose()
        
        markdown = h.handle(str(soup))
        return markdown
    
    def fetch(self) -> dict:
        """
        获取处理后的内容
        
        Returns:
            包含以下键的字典:
                - content: 处理后的内容
                - url: 实际获取的URL（可能经过重定向或转换）
                - original_url: 原始URL
                - content_type: Content-Type响应头
                - format: 返回内容的格式
                - size: 内容字节数
                - smart_processed: 是否经过了智能处理
        """
        try:
            response = requests.get(
                self.url,
                headers=self.headers,
                timeout=self._get_timeout(),
                allow_redirects=True
            )
            
            response.raise_for_status()
            self._check_response_size(response)
            
            content = response.text
            content_type = response.headers.get('content-type', 'text/plain')
            
            processed_content = self._process_content(content, content_type)
            
            result = {
                'content': processed_content,
                'url': self.url,
                'original_url': self.original_url,
                'content_type': content_type,
                'format': self.format,
                'size': len(content),
                'smart_processed': self.github_processed,
            }
            
            if self.github_raw_url:
                result['github_raw_url'] = self.github_raw_url
            
            return result
            
        except requests.exceptions.Timeout:
            raise WebFetchError(f"Request timed out after {self._get_timeout()[0]} seconds")
        except requests.exceptions.RequestException as e:
            raise WebFetchError(f"Request failed: {e}")
        except Exception as e:
            raise WebFetchError(f"Unexpected error: {e}")
    
    def _process_content(self, content: str, content_type: str) -> str:
        """根据请求的格式处理内容"""
        is_html = 'text/html' in content_type.lower()
        
        if self.format == "markdown":
            if is_html:
                return self._convert_html_to_markdown(content)
            else:
                return content
        
        elif self.format == "text":
            if is_html:
                return self._extract_text_from_html(content)
            else:
                return content
        
        else:  # html
            return content


# ============================================================================
# 统一接口函数
# ============================================================================

def fetch(
    url: str,
    format: str = "markdown",
    timeout: Optional[int] = None,
    user_agent: Optional[str] = None,
    smart: bool = True,
    return_content_only: bool = True
) -> Union[str, dict]:
    """
    统一的网页内容获取接口
    
    这是推荐的通用接口，可以处理所有类型的网站
    
    Args:
        url: 要获取的URL
        format: 输出格式
            - "markdown" (默认): 转换为Markdown格式
            - "text": 提取纯文本
            - "html": 保留原始HTML
        timeout: 超时时间（秒），最大120秒
        user_agent: 自定义User-Agent
        smart: 是否启用智能处理
            - True (默认): 自动处理GitHub等特殊网站
            - False: 直接获取，不做特殊处理
        return_content_only:
            - True (默认): 只返回内容字符串
            - False: 返回完整信息字典
    
    Returns:
        如果 return_content_only=True: 内容字符串
        如果 return_content_only=False: 完整信息字典
    
    Raises:
        WebFetchError: 如果获取失败
    
    Examples:
        >>> # 基本使用（自动智能处理）
        >>> content = fetch("https://example.com")
        >>> 
        >>> # 获取GitHub README（自动转换为raw URL）
        >>> readme = fetch("https://github.com/user/repo", format="markdown")
        >>> 
        >>> # 获取完整元数据
        >>> result = fetch("https://example.com", return_content_only=False)
        >>> print(f"URL: {result['url']}, Size: {result['size']}")
        >>> 
        >>> # 禁用智能处理（强制获取原始页面）
        >>> content = fetch("https://github.com/user/repo", smart=False)
    """
    # 验证格式
    valid_formats = {"markdown", "text", "html"}
    format_str = str(format).lower()
    if format_str not in valid_formats:
        raise WebFetchError(f"Invalid format '{format}'. Must be one of: markdown, text, html")
    
    # Type cast after validation to satisfy type checker
    format_literal = cast(Literal["markdown", "text", "html"], format_str)
    
    # 创建WebFetch实例并获取内容
    fetcher = WebFetch(url=url, format=format_literal, timeout=timeout, 
                       user_agent=user_agent, smart=smart)
    result = fetcher.fetch()
    
    if return_content_only:
        return result['content']
    else:
        return result


def fetch_to_file(
    url: str,
    output_file: str,
    format: str = "markdown",
    timeout: Optional[int] = None,
    user_agent: Optional[str] = None,
    smart: bool = True,
    encoding: str = 'utf-8'
) -> dict:
    """
    获取网页内容并保存到文件
    
    Args:
        url: 要获取的URL
        output_file: 输出文件路径
        format: 输出格式（"markdown", "text", "html"）
        timeout: 超时时间（秒）
        user_agent: 自定义User-Agent
        smart: 是否启用智能处理
        encoding: 文件编码（默认utf-8）
    
    Returns:
        包含元数据的字典
    
    Example:
        >>> result = fetch_to_file(
        ...     "https://github.com/user/repo",
        ...     "readme.md",
        ...     format="markdown"
        ... )
        >>> print(f"保存了 {result['size']} 字节")
    """
    result = fetch(url, format=format, timeout=timeout, 
                   user_agent=user_agent, smart=smart, 
                   return_content_only=False)
    
    # Type cast: when return_content_only=False, fetch returns dict
    result_dict = cast(dict, result)
    
    with open(output_file, 'w', encoding=encoding) as f:
        f.write(result_dict['content'])
    
    return result_dict


def fetch_github_readme(
    repo_url: str,
    branch: str = "main",
    timeout: Optional[int] = None
) -> str:
    """
    专门获取GitHub仓库的README
    
    Args:
        repo_url: GitHub仓库URL（如 https://github.com/user/repo）
        branch: 分支名（默认"main"，会尝试"master"作为备选）
        timeout: 超时时间（秒）
    
    Returns:
        README内容（Markdown格式）
    
    Raises:
        WebFetchError: 如果无法找到README
    
    Example:
        >>> readme = fetch_github_readme("https://github.com/user/repo")
        >>> print(readme)
    """
    # 提取用户和仓库名
    for pattern in WebFetch.GITHUB_PATTERNS:
        match = re.match(pattern, repo_url)
        if match:
            user, repo = match.groups()
            
            # 尝试不同分支
            branches = [branch, "master"] if branch != "master" else ["master", "main"]
            
            for branch_name in branches:
                raw_url = f'https://raw.githubusercontent.com/{user}/{repo}/{branch_name}/README.md'
                
                try:
                    fetcher = WebFetch(url=raw_url, format="markdown", 
                                     timeout=timeout, smart=False)
                    result = fetcher.fetch()
                    
                    if result['size'] > 0:
                        print(f"✓ 成功从 {branch_name} 分支获取README")
                        return result['content']
                except WebFetchError:
                    continue
            
            raise WebFetchError(f"Could not find README.md in repository {repo_url}")
    
    raise WebFetchError(f"Invalid GitHub repository URL: {repo_url}")


def fetch_multiple(
    urls: list,
    format: str = "markdown",
    timeout: Optional[int] = None,
    max_workers: int = 5,
    smart: bool = True
) -> list:
    """
    批量获取多个URL（并发）
    
    Args:
        urls: URL列表
        format: 输出格式
        timeout: 每个请求的超时时间
        max_workers: 最大并发数
        smart: 是否启用智能处理
    
    Returns:
        结果列表，每个元素包含url、content和可能的error
    
    Example:
        >>> results = fetch_multiple([
        ...     "https://example.com",
        ...     "https://github.com/user/repo"
        ... ])
        >>> for r in results:
        ...     if 'content' in r:
        ...         print(f"✓ {r['url']}: {len(r['content'])} bytes")
        ...     else:
        ...         print(f"✗ {r['url']}: {r['error']}")
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def fetch_one(url):
        try:
            content = fetch(url, format=format, timeout=timeout, smart=smart)
            return {"url": url, "content": content, "success": True}
        except Exception as e:
            return {"url": url, "error": str(e), "success": False}
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_one, url): url for url in urls}
        
        for future in as_completed(futures):
            results.append(future.result())
    
    return results


# ============================================================================
# 命令行接口
# ============================================================================

def main():
    """命令行入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("WebFetch - 智能网页内容获取工具")
        print()
        print("用法:")
        print("  python webfetch.py <url> [format] [output_file] [options]")
        print()
        print("参数:")
        print("  url          要获取的URL")
        print("  format       输出格式: markdown (默认), text, html")
        print("  output_file  保存到文件 (可选)")
        print()
        print("选项:")
        print("  --no-smart   禁用智能处理")
        print("  --timeout N  设置超时时间（秒）")
        print()
        print("示例:")
        print("  python webfetch.py https://example.com")
        print("  python webfetch.py https://example.com markdown")
        print("  python webfetch.py https://example.com markdown output.md")
        print("  python webfetch.py https://github.com/user/repo")
        print("  python webfetch.py https://github.com/user/repo --no-smart")
        sys.exit(1)
    
    # 解析参数
    url = sys.argv[1]
    format_type = "markdown"
    output_file = None
    smart = True
    timeout = None
    
    i = 2
    args = sys.argv[2:]
    
    # 先处理选项
    while '--timeout' in args:
        idx = args.index('--timeout')
        if idx + 1 < len(args):
            timeout = int(args[idx + 1])
            args = args[:idx] + args[idx + 2:]
        else:
            args = args[:idx]
    
    if '--no-smart' in args:
        smart = False
        args.remove('--no-smart')
    
    # 处理格式和输出文件
    if args:
        if args[0] in ["markdown", "text", "html"]:
            format_type = args[0]
            args = args[1:]
    
    if args and not args[0].startswith("--"):
        output_file = args[0]
    
    try:
        if output_file:
            result = fetch_to_file(url, output_file, format=format_type, 
                                   timeout=timeout, smart=smart)
            print(f"✓ 成功获取 {result['size']} 字节")
            print(f"  格式: {result['format']}")
            print(f"  类型: {result['content_type']}")
            if result.get('smart_processed'):
                print(f"  [智能处理] 已应用GitHub优化")
            print(f"  保存到: {output_file}")
        else:
            content = fetch(url, format=format_type, timeout=timeout, smart=smart)
            print(content)
    except WebFetchError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
