import asyncio
import json
import logging
from typing import List, Dict, Any, AsyncGenerator
from dashscope import Generation
from dashscope.aigc.generation import AioGeneration
from app.core.config import settings
from app.services.tools import TOOL_DEFINITIONS, tool_executor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_FULL = """你是一个专业的供热服务助手，请严格遵守以下规则来组织你的回答：

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
5. 语言简洁专业，避免冗余

## 工具使用
你可以调用以下工具来获取实时信息：
- **get_current_time**：获取当前日期时间
- **get_weather**：查询城市天气（供热与天气密切相关）
- **calculate_heating_fee**：计算供暖费用
- **query_heating_schedule**：查询城市供暖季安排
- **report_maintenance**：登记供热报修工单
- **get_heating_tips**：获取供热节能建议
- **search_knowledge_base**：搜索供热知识库

当用户询问需要实时数据的问题时，请主动调用相应工具获取信息后再回答。"""

SYSTEM_PROMPT_LITE = """你是一个专业的供热服务助手。你可以调用工具获取实时信息。
- 获取时间用 get_current_time
- 查询天气用 get_weather
- 计算费用用 calculate_heating_fee
- 查询供暖安排用 query_heating_schedule
- 登记报修用 report_maintenance
- 获取节能建议用 get_heating_tips

回答简洁清晰。当用户询问实时数据时，主动调用工具获取后再回答。"""

SYSTEM_PROMPT = SYSTEM_PROMPT_FULL


def build_rag_system_prompt(search_results: List[Dict[str, Any]], max_chunk_chars: int = 400, max_total_chars: int = 3000) -> str:
    if not search_results:
        return SYSTEM_PROMPT_LITE

    docs_text_parts: List[str] = []
    total_chars = 0
    for i, r in enumerate(search_results):
        title = r.get("title", "未知标题")
        content = r.get("content", "")
        score = r.get("score", 0)
        truncated_content = content[:max_chunk_chars]
        if len(content) > max_chunk_chars:
            truncated_content += "..."
        part = f"### 参考资料 {i + 1}：{title}（相关性得分：{score:.4f}）\n{truncated_content}"
        if total_chars + len(part) > max_total_chars:
            break
        docs_text_parts.append(part)
        total_chars += len(part)

    docs_context = "\n\n---\n\n".join(docs_text_parts)

    return f"""{SYSTEM_PROMPT}

## 参考资料
以下是来自知识库的相关文档内容，请优先基于这些资料回答问题。如果资料中没有相关信息，请诚实说明。

{docs_context}

---
请基于以上参考资料回答用户问题。引用资料内容时，请注明来源于哪份参考资料。"""


class ChatService:

    @staticmethod
    def _has_tool_calls(response) -> bool:
        try:
            choices = response.output.choices
            if choices:
                msg = choices[0].message
                if msg and msg.get("tool_calls"):
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _extract_tool_calls(response) -> list:
        try:
            msg = response.output.choices[0].message
            return msg.get("tool_calls", [])
        except Exception:
            return []

    @staticmethod
    def _extract_content(response) -> str:
        try:
            msg = response.output.choices[0].message
            content = msg.get("content", "")
            return content if content else ""
        except Exception:
            return ""

    @staticmethod
    def _extract_finish_reason(response) -> str:
        try:
            choices = response.output.choices
            if choices:
                return choices[0].get("finish_reason", "")
            return ""
        except Exception:
            return ""

    @staticmethod
    async def _call_model(messages: list, stream: bool = False, enable_tools: bool = True):
        kwargs = {
            "model": settings.DASHSCOPE_MODEL,
            "messages": messages,
            "result_format": "message",
            "api_key": settings.DASHSCOPE_API_KEY,
        }
        if enable_tools:
            kwargs["tools"] = TOOL_DEFINITIONS
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream"] = True
            kwargs["incremental_output"] = True

        if stream:
            return await AioGeneration.call(**kwargs)
        else:
            return await asyncio.to_thread(Generation.call, **kwargs)

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

        max_tool_rounds = 3
        tool_round = 0
        all_tool_calls = []

        while tool_round < max_tool_rounds:
            response = await ChatService._call_model(messages, stream=False)

            if response.status_code != 200:
                error_msg = response.message or "大模型调用失败"
                raise RuntimeError(f"模型调用失败: {error_msg}")

            if ChatService._has_tool_calls(response):
                tool_calls = ChatService._extract_tool_calls(response)
                tool_round += 1
                logger.info(f"[Tool Calling] 第 {tool_round} 轮，检测到 {len(tool_calls)} 个工具调用")

                assistant_msg = {"role": "assistant", "content": ""}
                tc_list = []
                for tc in tool_calls:
                    tc_info = {
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", "{}")
                        }
                    }
                    tc_list.append(tc_info)
                    all_tool_calls.append(tc_info)

                    fn_name = tc_info["function"]["name"]
                    try:
                        fn_args = json.loads(tc_info["function"]["arguments"]) if isinstance(tc_info["function"]["arguments"], str) else tc_info["function"]["arguments"]
                    except json.JSONDecodeError:
                        fn_args = {}
                    fn_result = await tool_executor.execute(fn_name, fn_args)
                    logger.info(f"[Tool Calling] 执行 {fn_name}({fn_args}) → 结果长度: {len(fn_result)}")

                    messages.append({
                        "role": "tool",
                        "content": fn_result,
                        "tool_call_id": tc_info["id"],
                        "name": fn_name
                    })

                assistant_msg["tool_calls"] = tc_list
                messages.append(assistant_msg)

                continue

            answer = ChatService._extract_content(response)
            return {
                "answer": answer,
                "model": settings.DASHSCOPE_MODEL,
                "tool_calls": all_tool_calls
            }

        answer = "抱歉，工具调用次数已达上限，请简化您的问题后再试。"
        return {
            "answer": answer,
            "model": settings.DASHSCOPE_MODEL,
            "tool_calls": all_tool_calls
        }

    @staticmethod
    async def stream_ask(
        message: str,
        history: list[dict] | None = None,
        search_results: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
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

        max_tool_rounds = 3
        tool_round = 0

        while tool_round < max_tool_rounds:
            responses = await ChatService._call_model(messages, stream=True)

            collected_tool_calls: Dict[int, dict] = {}
            collected_content = []
            has_tool_calls = False

            async for response in responses:
                if response.status_code != 200:
                    error_msg = response.message or "大模型调用失败"
                    yield {"type": "error", "content": error_msg}
                    return

                choices = response.output.choices
                if not choices:
                    continue

                msg = choices[0].message

                finish_reason = choices[0].get("finish_reason", "")

                tool_calls_delta = msg.get("tool_calls")
                if tool_calls_delta:
                    has_tool_calls = True
                    for tc in tool_calls_delta:
                        idx = tc.get("index", 0)
                        if idx not in collected_tool_calls:
                            collected_tool_calls[idx] = {
                                "id": tc.get("id", ""),
                                "type": tc.get("type", "function"),
                                "function": {
                                    "name": "",
                                    "arguments": ""
                                }
                            }
                        if "id" in tc and tc["id"]:
                            collected_tool_calls[idx]["id"] = tc["id"]
                        fn = tc.get("function", {})
                        if fn:
                            if "name" in fn and fn["name"]:
                                collected_tool_calls[idx]["function"]["name"] = fn["name"]
                            if "arguments" in fn:
                                collected_tool_calls[idx]["function"]["arguments"] += fn["arguments"]

                content = msg.get("content", "")
                if content:
                    collected_content.append(content)
                    yield {"type": "content", "content": content}

                if finish_reason == "tool_calls" and has_tool_calls:
                    break

            if has_tool_calls and collected_tool_calls:
                tool_round += 1
                sorted_tcs = [collected_tool_calls[i] for i in sorted(collected_tool_calls.keys())]
                logger.info(f"[Tool Calling-Stream] 第 {tool_round} 轮，检测到 {len(sorted_tcs)} 个工具调用")

                for tc in sorted_tcs:
                    fn_name = tc["function"]["name"]
                    fn_call_id = tc["id"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except json.JSONDecodeError:
                        fn_args = {}

                    yield {
                        "type": "tool_call",
                        "tool_name": fn_name,
                        "tool_args": fn_args,
                        "tool_call_id": fn_call_id
                    }

                    fn_result = await tool_executor.execute(fn_name, fn_args)
                    logger.info(f"[Tool Calling-Stream] 执行 {fn_name}({fn_args}) → 结果长度: {len(fn_result)}")

                    yield {
                        "type": "tool_result",
                        "tool_name": fn_name,
                        "result": fn_result,
                        "tool_call_id": fn_call_id
                    }

                    messages.append({
                        "role": "tool",
                        "content": fn_result,
                        "tool_call_id": fn_call_id,
                        "name": fn_name
                    })

                assistant_msg = {"role": "assistant", "content": "".join(collected_content) if collected_content else ""}
                assistant_msg["tool_calls"] = sorted_tcs
                messages.append(assistant_msg)
                collected_content = []
                continue

            return

        yield {"type": "content", "content": "\n\n抱歉，工具调用次数已达上限，请简化您的问题后再试。"}


chat_service = ChatService()
