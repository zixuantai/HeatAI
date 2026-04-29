import asyncio
from dashscope import Generation
from app.core.config import settings

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


class ChatService:

    @staticmethod
    async def ask(message: str) -> dict:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        response = await asyncio.to_thread(
            Generation.call,
            model=settings.DASHSCOPE_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
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
