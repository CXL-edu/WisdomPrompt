import os
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://google.serper.dev"


def search(
    query: str,
    api_key: Optional[str] = None,
    num: int = 10,
    gl: str = "us",
    hl: str = "zh-cn",
    autocorrect: bool = True,
    timeout: int = 30,
) -> Dict[str, Any]:
    token = api_key or os.getenv("SERPER_API_KEY")
    if not token:
        raise ValueError("SERPER_API_KEY is required")

    headers = {"X-API-KEY": token, "Content-Type": "application/json"}
    payload = {
        "q": query,
        "num": num,
        "gl": gl,
        "hl": hl,
        "autocorrect": autocorrect,
    }
    response = requests.post(
        f"{BASE_URL}/search",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
