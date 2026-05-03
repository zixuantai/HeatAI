import asyncio
import json
import logging
import re
from dashscope import Generation
from app.core.config import settings

logger = logging.getLogger(__name__)

FOLLOW_UP_PATTERNS = [
    r"^(那|那么|那这|这|它|他|她).*?(呢|吗|吧|啊|呀|？|\?)?$",
    r"^(详细|具体|仔细|深入).*(说说|讲讲|解释|介绍|展开)",
    r"^(继续|接着|往下).*",
    r"^(还有|另外|除此之外|再者|此外).*",
    r"^(比如|例如|举例|举个).*",
    r"^(什么意思|为什么|怎么会|怎么).*",
    r"^(能|可以|能否|可不可以).*(详细|具体|再|多).*",
    r"^(上面的|刚才的|之前的|前面).*",
    r"^(第二个|第2个|第三个|第3个|第一个|第1个|这个|那个|哪个).*",
    r"^(总结|概括|归纳|综上).*",
    r"^(好的|明白了|知道了|嗯嗯|哦哦|懂了).*",
    r"^(还有呢|然后呢|接下来呢|之后呢).*",
]

TRIVIAL_QUERY_PATTERNS = [
    r"^.{1,4}$",
    r"^[\u3000-\u303F\uFF00-\uFFEF\s]+$",
]

QUERY_REWRITE_SYSTEM_PROMPT = """你是一个供热行业查询优化专家。你的任务是对用户输入的问题进行改写优化，使其更适合用于知识库检索（BM25 + 向量检索）。

## 改写规则

1. **语义保持一致**
   - 不允许改变用户原始问题的意图
   - 不允许添加无关信息

2. **增强检索能力**
   - 补充必要的上下文信息（如果用户表达模糊）
   - 明确查询对象（设备、系统、故障、政策等）

3. **术语标准化（供热行业）**
   - 将口语转换为专业表达
   - 示例：
     - "不热" → "供热不足 / 供暖温度不足"
     - "没水" → "系统缺水 / 循环水不足"
     - "漏水" → "管道漏水 / 系统泄漏"
     - "暖气片凉" → "散热器不热 / 末端温度低"
     - "锅炉响" → "锅炉异响 / 设备运行噪音"
     - "费气" → "能耗过高 / 燃气消耗异常"
     - "压力低" → "系统压力不足 / 水压偏低"
     - "阀门" → "调节阀 / 截止阀 / 温控阀"

4. **关键词扩展（非常关键）**
   - 输出 2~3 个不同表达的查询版本，用于多路召回
   - 包含：
     - 原始语义表达
     - 同义表达
     - 专业表达

5. **去噪**
   - 删除无意义词（比如：帮我看看、怎么回事、这个问题、请问一下）
   - 保留核心检索信息

## 输出格式（必须严格遵守，只输出 JSON，不要输出任何其他内容）

{
  "original_query": "用户原始问题",
  "rewritten_query": "优化后的标准查询（用于主检索）",
  "expanded_queries": [
    "扩展查询1",
    "扩展查询2",
    "扩展查询3"
  ]
}"""


class QueryRewriterService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def should_skip_rewrite(query: str) -> bool:
        stripped = query.strip()
        if not stripped:
            return True

        for pattern in TRIVIAL_QUERY_PATTERNS:
            if re.match(pattern, stripped):
                return True

        for pattern in FOLLOW_UP_PATTERNS:
            if re.match(pattern, stripped):
                return True

        return False

    async def rewrite(self, query: str) -> dict:
        if not settings.DASHSCOPE_API_KEY:
            logger.warning("[Query改写] DashScope API Key 未配置，使用原始查询")
            return {
                "original_query": query,
                "rewritten_query": query,
                "expanded_queries": []
            }

        messages = [
            {"role": "system", "content": QUERY_REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]

        try:
            response = await asyncio.to_thread(
                Generation.call,
                model=settings.DASHSCOPE_MODEL,
                messages=messages,
                result_format="message",
                api_key=settings.DASHSCOPE_API_KEY
            )

            if response.status_code != 200:
                logger.warning(f"[Query改写] 模型调用失败: {response.message}，使用原始查询")
                return {
                    "original_query": query,
                    "rewritten_query": query,
                    "expanded_queries": []
                }

            content = response.output.choices[0].message.content
            result = self._parse_response(content, query)
            return result

        except Exception as e:
            logger.warning(f"[Query改写] 异常: {e}，使用原始查询")
            return {
                "original_query": query,
                "rewritten_query": query,
                "expanded_queries": []
            }

    @staticmethod
    def _parse_response(content: str, original_query: str) -> dict:
        try:
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[-1].strip() == "```":
                    content = "\n".join(lines[1:-1])
                else:
                    content = "\n".join(lines[1:])
                content = content.strip()

            result = json.loads(content)

            rewritten = result.get("rewritten_query", "").strip()
            expanded = result.get("expanded_queries", [])

            if not isinstance(expanded, list):
                expanded = []

            expanded = [q.strip() for q in expanded if isinstance(q, str) and q.strip()]

            return {
                "original_query": result.get("original_query", original_query),
                "rewritten_query": rewritten or original_query,
                "expanded_queries": expanded[:3]
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[Query改写] JSON 解析失败: {e}，原始响应前200字符: {content[:200]}")
            return {
                "original_query": original_query,
                "rewritten_query": original_query,
                "expanded_queries": []
            }


query_rewriter = QueryRewriterService()
