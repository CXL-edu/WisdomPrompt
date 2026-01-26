import os
from typing import Any, Dict, List, Optional

import requests

NVIDIA_CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def chat(
    messages: List[Dict[str, str]],
    model: str = "z-ai/glm4.7",
    api_key: Optional[str] = None,
    timeout: int = 30,
    **params: Any,
) -> str:
    """Call Nvidia chat completions and return the assistant content."""
    token = api_key or os.getenv("NVIDIA_API_KEY")
    if not token:
        raise ValueError("NVIDIA_API_KEY is required")

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    payload.update(params)
    response = requests.post(
        NVIDIA_CHAT_URL,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
