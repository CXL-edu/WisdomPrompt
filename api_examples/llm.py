import os
from dotenv import load_dotenv
import requests

load_dotenv()

# 临时禁用代理（如果环境变量中设置了代理但代理不可用）
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {
    "accept": "application/json",
    "authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
    "content-type": "application/json"
}

model_list = [
    "deepseek-ai/deepseek-r1",
    "moonshotai/kimi-k2-thinking",
    "z-ai/glm4.7",
    "minimax/minimax-m2",
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "google/gemma-2-27b-it",
    "mistralai/mistral-large",
    "nvidia/llama-3.1-nemotron-70b-instruct"
]
data = {
    "model": "z-ai/glm4.7",
    "messages": [
        {
            "role": "user",
            "content": "你好"
        }
    ],
    "temperature": 0.6,
    "top_p": 0.7,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "max_tokens": 4096,
    "stream": False
}

# 禁用代理，直接连接
response = requests.post(url, headers=headers, json=data)
# response = requests.post(url, headers=headers, json=data, proxies={})
response.raise_for_status()
result = response.json()
print(result["choices"][0]["message"]["content"])