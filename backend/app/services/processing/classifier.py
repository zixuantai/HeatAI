import asyncio
import json
import logging

logger = logging.getLogger(__name__)

DOCUMENT_CATEGORIES = [
    "供热政策",
    "操作指南",
    "技术规范",
    "安全须知",
    "故障处理",
    "费用标准",
    "通知公告",
    "设备资料",
]

CLASSIFICATION_SYSTEM_PROMPT = """你是一个文档分类助手。你需要根据文档的标题和内容，将其归类到以下类别之一：

{categories}

分类标准：
- **供热政策**：供暖相关的法律法规、政策文件、政府通知、行业规定
- **操作指南**：设备操作手册、使用说明、操作流程、培训教程
- **技术规范**：技术标准、施工规范、设计规范、验收标准
- **安全须知**：安全操作规程、应急预案、安全管理制度
- **故障处理**：故障排查手册、维修方案、常见问题解答
- **费用标准**：收费标准、计费规则、价格公示
- **通知公告**：停暖通知、检修通知、临时公告
- **设备资料**：设备参数、产品说明书、技术参数表

请严格返回 JSON 格式，不要包含其他内容：
{{"category": "类别名称", "confidence": "high/medium/low", "reason": "简短判断依据"}}"""


class DocumentClassifier:

    def __init__(self, model: str | None = None):
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def classify(self, title: str, content: str) -> dict:
        from app.core.config import settings

        if not settings.DASHSCOPE_API_KEY:
            logger.warning("[文档分类] DashScope API Key 未配置，跳过分类")
            return {"category": None, "confidence": "low", "reason": "API Key 未配置"}

        category_list = "\n".join(f"- {c}" for c in DOCUMENT_CATEGORIES)
        system_prompt = CLASSIFICATION_SYSTEM_PROMPT.format(categories=category_list)

        content_sample = content[:2000]

        user_message = f"标题：{title}\n\n内容（前2000字）：\n{content_sample}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        try:
            from dashscope import Generation

            response = await asyncio.to_thread(
                Generation.call,
                model=self.model or settings.MEMORY_LLM_MODEL,
                messages=messages,
                result_format="message",
                api_key=settings.DASHSCOPE_API_KEY,
            )

            if response.status_code != 200:
                logger.warning(f"[文档分类] LLM 调用失败: {response.message}")
                return {"category": None, "confidence": "low", "reason": f"LLM 返回错误: {response.message}"}

            content_result = response.output.choices[0].message.content
            parsed = self._parse_response(content_result)
            return parsed

        except Exception as e:
            logger.warning(f"[文档分类] 分类异常: {e}")
            return {"category": None, "confidence": "low", "reason": str(e)}

    @staticmethod
    def _parse_response(content: str) -> dict:
        try:
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                content = "\n".join(lines).strip()

            data = json.loads(content)
            category = data.get("category")

            if category not in DOCUMENT_CATEGORIES:
                category = None

            return {
                "category": category,
                "confidence": data.get("confidence", "low"),
                "reason": data.get("reason", ""),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[文档分类] JSON 解析失败: {e}, 原始内容: {content[:200]}")
            return {"category": None, "confidence": "low", "reason": f"解析失败: {e}"}


document_classifier = DocumentClassifier()
