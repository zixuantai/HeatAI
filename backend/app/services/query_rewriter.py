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

SIMPLE_SMALL_TALK_PATTERNS = [
    r"^(你好|您好|嗨|哈喽|hello|hi)[\s!！。.~～]*$",
    r"^(谢谢|多谢|感谢|3q|thx|thanks)[\s!！。.]*$",
    r"^(再见|拜拜|bye|再见啦)[\s!！。.]*$",
    r"^(嗯|哦|好|行|可以|OK|ok|对|是的|没错)[\s!！。.]*$",
    r"^(早上好|下午好|晚上好|早|晚安)[\s!！。.]*$",
    r"^(你是谁|你叫什么|介绍.*自己|你是.*机器人).*$",
    r"^.{1,3}$",
]

TOOL_ONLY_QUERY_PATTERNS = [
    r"^(现在|今天|明天|昨天).*(几点|时间|日期|星期|几号|啥时候)",
    r"^(几点了|什么时候了|啥时候了|现在时间)",
    r"^(天气|温度|气温).*(怎么样|如何|多少|怎样|冷|热)",
    r"^(帮我|给我|请).*(算|计算|查|查询|看).*(费|费用|天气|时间|供暖)",
    r"^(算一[下算]|计算|帮我算).*(费|费用|价格|钱|多少钱)",
    r"^(现在|今天|明天).*(天气|温度|气温|冷|热).*$",
    r"^(报修|我要报修|登记.*报修).*$",
    r"^(供暖|供热).*(建议|节能|省|省钱|降|减少).*(费|费用).*$",
    r"^(供暖季|供热季).*(安排|时间|开始|结束).*$",
]

HEATING_KEYWORDS = [
    "供暖", "供热", "暖气", "锅炉", "散热器", "管道", "阀门",
    "漏水", "不热", "压力", "温度", "循环", "补水", "排气",
    "故障", "维修", "报修", "采暖", "节能", "热力", "换热站",
    "一次网", "二次网", "分户", "计量", "温控", "调节",
    "地暖", "壁挂炉", "燃气", "煤改", "清洁能源",
]

QUERY_REWRITE_SYSTEM_PROMPT = """你是供热行业查询优化专家。将用户口语转为适合检索的关键词查询。

## 规则
1. 术语标准化：口语→专业表达（如"不热"→"供热不足"，"漏水"→"管道泄漏"）
2. 输出2-3个不同表达的扩展查询用于多路召回
3. 去噪：删除"帮我看看""怎么回事"等无意义词

仅输出JSON：
{"original_query":"原文","rewritten_query":"优化查询","expanded_queries":["扩展1","扩展2"]}"""


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

        for pattern in SIMPLE_SMALL_TALK_PATTERNS:
            if re.match(pattern, stripped):
                return True

        for pattern in TOOL_ONLY_QUERY_PATTERNS:
            if re.match(pattern, stripped):
                return True

        return False

    @staticmethod
    def needs_knowledge_base(query: str) -> bool:
        stripped = query.strip()
        if not stripped:
            return False

        for pattern in SIMPLE_SMALL_TALK_PATTERNS:
            if re.match(pattern, stripped):
                return False

        for pattern in TOOL_ONLY_QUERY_PATTERNS:
            if re.match(pattern, stripped):
                return False

        if len(stripped) <= 6 and not any(kw in stripped for kw in HEATING_KEYWORDS):
            return False

        return True

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
                model=settings.MEMORY_LLM_MODEL,
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
