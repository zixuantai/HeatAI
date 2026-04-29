import asyncio
from dashscope import Generation
from app.core.config import settings


class ChatService:

    @staticmethod
    async def ask(message: str) -> dict:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        response = await asyncio.to_thread(
            Generation.call,
            model=settings.DASHSCOPE_MODEL,
            messages=[{"role": "user", "content": message}],
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


chat_service = ChatService()
