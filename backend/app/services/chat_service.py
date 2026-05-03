import asyncio
import logging
from typing import List, Dict, Any
from dashscope import Generation
from dashscope.aigc.generation import AioGeneration
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的供热服务助手，请严格遵守以下规则来组织你的回答：

## 格式要求
1. **必须使用 Markdown 格式输出**，包括但不限于：
   - 使用 `#` `##` `###` 表示标题层级
   - 使用 `**加粗**` 强调重点
   - 使用 `- ` 或 `1. ` 创建列表
   - 使用 ``` ``` 包裹代码块（并标明语言）
   - 使用 `>` 表示引用
   - 使用 `|` 创建表格（如适用）
2. 回答要结构清晰，先给出总结，再展开细节
3. 对于步骤类内容，务必使用有序列表
4. 涉及专业术语时使用加粗标注
5. 语言简洁专业，避免冗余"""


def build_rag_system_prompt(search_results: List[Dict[str, Any]]) -> str:
    if not search_results:
        return SYSTEM_PROMPT

    docs_text_parts: List[str] = []
    for i, r in enumerate(search_results):
        title = r.get("title", "未知标题")
        content = r.get("content", "")
        score = r.get("score", 0)
        docs_text_parts.append(
            f"### 参考资料 {i + 1}：{title}（相关性得分：{score:.4f}）\n{content}"
        )

    docs_context = "\n\n---\n\n".join(docs_text_parts)

    return f"""{SYSTEM_PROMPT}

## 参考资料
以下是来自知识库的相关文档内容，请优先基于这些资料回答问题。如果资料中没有相关信息，请诚实说明。

{docs_context}

---
请基于以上参考资料回答用户问题。引用资料内容时，请注明来源于哪份参考资料。"""


class ChatService:

    @staticmethod
    async def ask(
        message: str,
        history: list[dict] | None = None,
        search_results: list[dict] | None = None,
    ) -> dict:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        if search_results:
            logger.info(f"[RAG 对话] 使用 {len(search_results)} 条搜索结果作为上下文")

        system_content = build_rag_system_prompt(search_results or [])

        messages = [{"role": "system", "content": system_content}]
        if history:
            messages.extend(history)
        else:
            messages.append({"role": "user", "content": message})

        response = await asyncio.to_thread(
            Generation.call,
            model=settings.DASHSCOPE_MODEL,
            messages=messages,
            result_format="message",
            api_key=settings.DASHSCOPE_API_KEY
        )

        if response.status_code != 200:
            error_msg = response.message or "大模型调用失败"
            raise RuntimeError(f"模型调用失败: {error_msg}")

        answer = response.output.choices[0].message.content

        return {
            "answer": answer,
            "model": settings.DASHSCOPE_MODEL
        }

    @staticmethod
    async def stream_ask(
        message: str,
        history: list[dict] | None = None,
        search_results: list[dict] | None = None,
    ):
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        if search_results:
            logger.info(f"[RAG 对话] 使用 {len(search_results)} 条搜索结果作为上下文")

        system_content = build_rag_system_prompt(search_results or [])

        messages = [{"role": "system", "content": system_content}]
        if history:
            messages.extend(history)
        else:
            messages.append({"role": "user", "content": message})

        responses = await AioGeneration.call(
            model=settings.DASHSCOPE_MODEL,
            messages=messages,
            result_format="message",
            stream=True,
            incremental_output=True,
            api_key=settings.DASHSCOPE_API_KEY
        )

        async for response in responses:
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                yield content
            else:
                error_msg = response.message or "大模型调用失败"
                raise RuntimeError(f"模型调用失败: {error_msg}")


chat_service = ChatService()
