"""
对话服务 —— 使用 LangGraph create_agent 管理 Tool Calling 流程。

模型创建统一通过 model_factory，不直接依赖具体模型实现。
对外 API 与前版完全兼容：ask / stream_ask / quick_ask / stream_quick_ask / stream_vision_ask。
"""

import asyncio
import logging
import threading
import queue as sync_queue
from typing import Any, AsyncGenerator, List, Dict

from dashscope import MultiModalConversation
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.agents import create_agent

from app.core.config import settings
from app.services.chat.engine.model_factory import create_chat_model, _get_api_key
from app.services.chat.engine.prompts import (
    SYSTEM_PROMPT_QUICK,
    VISION_SYSTEM_PROMPT,
    build_multimodal_message,
    build_rag_system_prompt,
)
from app.services.chat.engine.personalization import build_personalization_prompt
from app.services.chat.engine.tools import LC_TOOLS, LC_QUICK_TOOLS

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3  # 等同于原来 while 循环的上限


def _ensure_api_key():
    """确保 API Key 已配置，否则抛出异常。"""
    if not _get_api_key():
        raise ValueError("LLM API Key 未配置，请在 .env 中设置 LLM_API_KEY 或 DASHSCOPE_API_KEY")


def _build_agent(tools: list, *, model_name: str | None = None):
    """构建 LangGraph ReAct agent（模型实例由工厂创建）。"""
    model = create_chat_model(tools=tools, model_name=model_name)
    return create_agent(model, tools)


def _extract_tool_calls_from_result(result: dict) -> list:
    """从 agent 结果中提取所有 tool_call 记录。"""
    all_tc = []
    for msg in result.get("messages", []):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                all_tc.append({
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": str(tc.get("args", {})),
                    },
                })
    return all_tc


def _extract_final_answer(result: dict, error_msg: str = "") -> str:
    """从 agent 结果中提取最终回答文本。"""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content or ""
            if content and not msg.tool_calls:
                return content
    if error_msg:
        return error_msg
    return "抱歉，处理您的请求时遇到了问题，请稍后再试。"


class ChatService:
    """对话服务 —— 底层由 LangGraph ReAct Agent 驱动。"""

    # ── 非流式 RAG 模式 ───────────────────────────────────────

    @staticmethod
    async def ask(
        message: str,
        history: list[dict] | None = None,
        search_results: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> dict:
        _ensure_api_key()

        if search_results:
            logger.info(f"[RAG 对话] 使用 {len(search_results)} 条搜索结果作为上下文")

        system_content = build_rag_system_prompt(search_results or [])
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            system_content += pers_prompt

        messages: list = [SystemMessage(content=system_content)]
        if history:
            messages.extend(_dict_to_lc_messages(history))
        else:
            messages.append(HumanMessage(content=message))

        agent = _build_agent(LC_TOOLS)
        try:
            result = await agent.ainvoke(
                {"messages": messages},
                config={"recursion_limit": MAX_TOOL_ROUNDS * 2 + 1},
            )
            answer = _extract_final_answer(result)
            tool_calls = _extract_tool_calls_from_result(result)
            return {
                "answer": answer,
                "model": settings.LLM_MODEL,
                "tool_calls": tool_calls,
            }
        except Exception as e:
            logger.error(f"[RAG 对话] Agent 执行失败: {e}")
            return {
                "answer": f"抱歉，处理您的请求时遇到了问题: {str(e)}",
                "model": settings.LLM_MODEL,
                "tool_calls": [],
            }

    # ── 非流式快速模式 ─────────────────────────────────────────

    @staticmethod
    async def quick_ask(
        message: str,
        history: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> dict:
        _ensure_api_key()

        logger.info("[快速模式-非流式] 直接回复，跳过RAG管线")

        sys_content = SYSTEM_PROMPT_QUICK
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            sys_content += pers_prompt

        messages: list = [SystemMessage(content=sys_content)]
        if history:
            messages.extend(_dict_to_lc_messages(history))
        else:
            messages.append(HumanMessage(content=message))

        agent = _build_agent(LC_QUICK_TOOLS)
        try:
            result = await agent.ainvoke(
                {"messages": messages},
                config={"recursion_limit": MAX_TOOL_ROUNDS * 2 + 1},
            )
            answer = _extract_final_answer(result)
            tool_calls = _extract_tool_calls_from_result(result)
            return {
                "answer": answer,
                "model": settings.LLM_MODEL,
                "tool_calls": tool_calls,
            }
        except Exception as e:
            logger.error(f"[快速模式] Agent 执行失败: {e}")
            return {
                "answer": f"抱歉，处理您的请求时遇到了问题: {str(e)}",
                "model": settings.LLM_MODEL,
                "tool_calls": [],
            }

    # ── 流式 RAG 模式 ──────────────────────────────────────────

    @staticmethod
    async def stream_ask(
        message: str,
        history: list[dict] | None = None,
        search_results: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> AsyncGenerator[dict, None]:
        _ensure_api_key()

        if search_results:
            logger.info(f"[RAG 对话] 使用 {len(search_results)} 条搜索结果作为上下文")

        system_content = build_rag_system_prompt(search_results or [])
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            system_content += pers_prompt

        messages_list: list = [SystemMessage(content=system_content)]
        if history:
            messages_list.extend(_dict_to_lc_messages(history))
        else:
            messages_list.append(HumanMessage(content=message))

        agent = _build_agent(LC_TOOLS)
        try:
            async for event in agent.astream_events(
                {"messages": messages_list},
                config={"recursion_limit": MAX_TOOL_ROUNDS * 2 + 1},
                version="v2",
            ):
                for sse in _convert_event_to_sse(event):
                    yield sse
        except Exception as e:
            logger.error(f"[RAG 流式] Agent 执行失败: {e}")
            yield {"type": "error", "content": str(e)}

    # ── 流式快速模式 ───────────────────────────────────────────

    @staticmethod
    async def stream_quick_ask(
        message: str,
        history: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> AsyncGenerator[dict, None]:
        _ensure_api_key()

        logger.info("[快速模式] 直接回复，跳过RAG管线")

        sys_content = SYSTEM_PROMPT_QUICK
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            sys_content += pers_prompt

        messages_list: list = [SystemMessage(content=sys_content)]
        if history:
            messages_list.extend(_dict_to_lc_messages(history))
        else:
            messages_list.append(HumanMessage(content=message))

        agent = _build_agent(LC_QUICK_TOOLS)
        try:
            async for event in agent.astream_events(
                {"messages": messages_list},
                config={"recursion_limit": MAX_TOOL_ROUNDS * 2 + 1},
                version="v2",
            ):
                for sse in _convert_event_to_sse(event):
                    yield sse
        except Exception as e:
            logger.error(f"[快速模式-流式] Agent 执行失败: {e}")
            yield {"type": "error", "content": str(e)}

    # ── 视觉模式（不改动，保持原逻辑）──────────────────────────

    @staticmethod
    async def stream_vision_ask(
        message: str,
        images: list[str],
        history: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> AsyncGenerator[dict, None]:
        _ensure_api_key()

        logger.info(f"[视觉模式] 图片数量: {len(images)}, 文本: {message[:50] if message else '(无)'}")

        vis_sys = VISION_SYSTEM_PROMPT
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            vis_sys += pers_prompt

        messages: list = [{"role": "system", "content": [{"text": vis_sys}]}]
        if history:
            for h in history:
                if isinstance(h.get("content"), str):
                    messages.append({"role": h["role"], "content": [{"text": h["content"]}]})
                else:
                    messages.append(h)
        user_msg = build_multimodal_message(message, images)
        messages.append(user_msg)

        result_queue: sync_queue.Queue = sync_queue.Queue()

        def _run_stream():
            try:
                for response in MultiModalConversation.call(
                    model=settings.DASHSCOPE_VL_MODEL,
                    messages=messages,
                    stream=True,
                    api_key=settings.DASHSCOPE_API_KEY,
                    temperature=settings.LLM_TEMPERATURE,
                    top_p=0.95,
                ):
                    result_queue.put_nowait(response)
            except Exception as exc:
                result_queue.put_nowait(exc)
            finally:
                result_queue.put_nowait(None)

        thread = threading.Thread(target=_run_stream, daemon=True)
        thread.start()

        previous_text = ""
        while True:
            response = await asyncio.to_thread(result_queue.get)
            if response is None:
                break
            if isinstance(response, Exception):
                yield {"type": "error", "content": str(response)}
                return

            if response.status_code != 200:
                error_msg = response.message or "视觉模型调用失败"
                yield {"type": "error", "content": error_msg}
                return

            choices = response.output.choices
            if not choices:
                continue

            msg = choices[0].message
            content = msg.get("content", "")
            if not content:
                continue

            current_text = ""
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        current_text += (item.get("text") or "")
            elif isinstance(content, str):
                current_text = content

            if current_text and current_text != previous_text:
                if current_text.startswith(previous_text):
                    delta = current_text[len(previous_text):]
                else:
                    delta = current_text
                previous_text = current_text
                if delta:
                    yield {"type": "content", "content": delta}


# ── 辅助函数 ──────────────────────────────────────────────────

def _dict_to_lc_messages(history: List[dict]) -> list:
    """将旧格式的 dict 消息列表转为 LangChain 消息对象。"""
    lc_msgs = []
    for h in history:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role == "system":
            lc_msgs.append(SystemMessage(content=content))
        elif role == "assistant":
            lc_msgs.append(AIMessage(content=content))
        else:
            lc_msgs.append(HumanMessage(content=content))
    return lc_msgs


def _convert_event_to_sse(event: dict) -> list:
    """将 LangGraph astream_events(v2) 事件转为现有的 SSE 事件格式。"""
    kind = event.get("event", "")
    data = event.get("data", {})

    if kind == "on_chat_model_stream":
        chunk = data.get("chunk")
        if chunk and chunk.content:
            return [{"type": "content", "content": chunk.content}]

    elif kind == "on_tool_start":
        tool_input = data.get("input") or {}
        # tool_input 可能是 dict 或 str
        if isinstance(tool_input, str):
            tool_args = {"input": tool_input}
        else:
            tool_args = {
                k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                for k, v in tool_input.items()
            }
        return [{
            "type": "tool_call",
            "tool_name": event.get("name", ""),
            "tool_args": tool_args,
            "tool_call_id": event.get("run_id", ""),
        }]

    elif kind == "on_tool_end":
        output = data.get("output")
        result_str = _serialize_tool_output(output)
        return [{
            "type": "tool_result",
            "tool_name": event.get("name", ""),
            "result": result_str,
            "tool_call_id": event.get("run_id", ""),
        }]

    return []


def _serialize_tool_output(output) -> str:
    """将工具输出序列化为字符串（兼容前端期望的 JSON 字符串）。"""
    import json as _json
    if isinstance(output, str):
        return output
    try:
        return _json.dumps(output, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(output)


chat_service = ChatService()