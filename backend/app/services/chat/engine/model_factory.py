"""
模型工厂 —— 创建 BaseChatModel 实例的唯一入口。

所有大模型通过 OpenAI 兼容接口接入，更换模型只需改配置项：
  LLM_API_KEY=xxx
  LLM_BASE_URL=https://xxx/v1
  LLM_MODEL=xxx

无需编写任何适配器代码。
"""

from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from app.core.config import settings

# DashScope OpenAI 兼容端点的默认地址
_DASHSCOPE_COMPATIBLE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _get_api_key() -> str:
    """获取 API Key（LLM_API_KEY 优先，否则回退到 DASHSCOPE_API_KEY）。"""
    return settings.LLM_API_KEY or settings.DASHSCOPE_API_KEY


def _get_base_url() -> str:
    """获取 Base URL（LLM_BASE_URL 优先，否则用 DashScope 兼容端点）。"""
    return settings.LLM_BASE_URL or _DASHSCOPE_COMPATIBLE_BASE


def create_chat_model(
    tools: Sequence[BaseTool] | None = None,
    *,
    model_name: str | None = None,
) -> BaseChatModel:
    """创建文本对话模型（OpenAI 兼容接口）。

    换模型示例（改 .env 即可）：
        # 通义千问 (DashScope)
        LLM_API_KEY=sk-xxx
        LLM_MODEL=qwen-max

        # OpenAI
        LLM_API_KEY=sk-xxx
        LLM_BASE_URL=https://api.openai.com/v1
        LLM_MODEL=gpt-4o

        # 本地 vLLM / Ollama / 任何 OpenAI 兼容服务
        LLM_API_KEY=not-needed
        LLM_BASE_URL=http://localhost:8000/v1
        LLM_MODEL=Qwen2.5-72B
    """
    model = ChatOpenAI(
        model=model_name or settings.LLM_MODEL,
        api_key=_get_api_key(),
        base_url=_get_base_url(),
        temperature=settings.LLM_TEMPERATURE,
    )
    if tools:
        model = model.bind_tools(tools)
    return model