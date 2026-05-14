import asyncio
import json
import logging
from typing import List, Dict, Any, AsyncGenerator
from dashscope import Generation, MultiModalConversation
from dashscope.aigc.generation import AioGeneration
from app.core.config import settings
from app.services.chat.engine.tools import TOOL_DEFINITIONS, tool_executor
from app.services.chat.engine.prompts import (
    SYSTEM_PROMPT, SYSTEM_PROMPT_QUICK, SYSTEM_PROMPT_LITE,
    VISION_SYSTEM_PROMPT, build_multimodal_message, build_rag_system_prompt
)
from app.services.chat.engine.personalization import build_personalization_prompt
from app.services.chat.engine.response_parser import has_tool_calls, extract_tool_calls, extract_content, extract_finish_reason

logger = logging.getLogger(__name__)

QUICK_TOOLS = [t for t in TOOL_DEFINITIONS if t["function"]["name"] != "search_knowledge_base"]


class ChatService:

    @staticmethod
    async def _call_model(messages: list, stream: bool = False, enable_tools: bool = True, tools: list | None = None, model: str | None = None):
        kwargs = {
            "model": model or settings.DASHSCOPE_MODEL,
            "messages": messages,
            "result_format": "message",
            "api_key": settings.DASHSCOPE_API_KEY,
            "temperature": settings.LLM_TEMPERATURE,
            "top_p": 0.95,
        }
        if enable_tools:
            kwargs["tools"] = tools if tools is not None else TOOL_DEFINITIONS
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream"] = True
            kwargs["incremental_output"] = True

        if stream:
            return await AioGeneration.call(**kwargs)
        else:
            return await asyncio.to_thread(Generation.call, **kwargs)

    @staticmethod
    async def _execute_tools_and_append(tool_calls: list, messages: list, all_tool_calls: list, tool_round: int):
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

        messages.append({"role": "assistant", "content": "", "tool_calls": tc_list})

        for tc_info in tc_list:
            fn_name = tc_info["function"]["name"]
            try:
                fn_args = json.loads(tc_info["function"]["arguments"]) if isinstance(tc_info["function"]["arguments"], str) else tc_info["function"]["arguments"]
            except json.JSONDecodeError:
                fn_args = {}
            fn_result = await tool_executor.execute(fn_name, fn_args)
            logger.info(f"[Tool Calling] 第 {tool_round} 轮，执行 {fn_name}({fn_args}) → 结果长度: {len(fn_result)}")

            messages.append({
                "role": "tool",
                "content": fn_result,
                "tool_call_id": tc_info["id"],
                "name": fn_name
            })

    @staticmethod
    async def ask(
        message: str,
        history: list[dict] | None = None,
        search_results: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> dict:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        if search_results:
            logger.info(f"[RAG 对话] 使用 {len(search_results)} 条搜索结果作为上下文")

        system_content = build_rag_system_prompt(search_results or [])
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            system_content += pers_prompt

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

            if has_tool_calls(response):
                tool_calls = extract_tool_calls(response)
                tool_round += 1
                logger.info(f"[Tool Calling] 第 {tool_round} 轮，检测到 {len(tool_calls)} 个工具调用")
                await ChatService._execute_tools_and_append(tool_calls, messages, all_tool_calls, tool_round)
                continue

            answer = extract_content(response)
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
        personalization: dict[str, int] | None = None,
    ) -> AsyncGenerator[dict, None]:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        if search_results:
            logger.info(f"[RAG 对话] 使用 {len(search_results)} 条搜索结果作为上下文")

        system_content = build_rag_system_prompt(search_results or [])
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            system_content += pers_prompt

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
            has_tc = False

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
                    has_tc = True
                    for tc in tool_calls_delta:
                        idx = tc.get("index", 0)
                        if idx not in collected_tool_calls:
                            collected_tool_calls[idx] = {
                                "id": tc.get("id", ""),
                                "type": tc.get("type", "function"),
                                "function": {"name": "", "arguments": ""}
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

                if finish_reason == "tool_calls" and has_tc:
                    break

            if has_tc and collected_tool_calls:
                tool_round += 1
                sorted_tcs = [collected_tool_calls[i] for i in sorted(collected_tool_calls.keys())]
                logger.info(f"[Tool Calling-Stream] 第 {tool_round} 轮，检测到 {len(sorted_tcs)} 个工具调用")

                assistant_msg = {"role": "assistant", "content": "".join(collected_content) if collected_content else ""}
                assistant_msg["tool_calls"] = sorted_tcs
                messages.append(assistant_msg)

                for tc in sorted_tcs:
                    fn_name = tc["function"]["name"]
                    fn_call_id = tc["id"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except json.JSONDecodeError:
                        fn_args = {}

                    yield {"type": "tool_call", "tool_name": fn_name, "tool_args": fn_args, "tool_call_id": fn_call_id}

                    fn_result = await tool_executor.execute(fn_name, fn_args)
                    logger.info(f"[Tool Calling-Stream] 执行 {fn_name}({fn_args}) → 结果长度: {len(fn_result)}")

                    yield {"type": "tool_result", "tool_name": fn_name, "result": fn_result, "tool_call_id": fn_call_id}

                    messages.append({"role": "tool", "content": fn_result, "tool_call_id": fn_call_id, "name": fn_name})

                continue

            return

        yield {"type": "content", "content": "抱歉，工具调用次数已达上限，请简化您的问题后再试。"}

    @staticmethod
    async def quick_ask(
        message: str,
        history: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> dict:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        logger.info(f"[快速模式-非流式] 直接回复，跳过RAG管线")

        sys_content = SYSTEM_PROMPT_QUICK
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            sys_content += pers_prompt

        messages = [{"role": "system", "content": sys_content}]
        if history:
            messages.extend(history)
        else:
            messages.append({"role": "user", "content": message})

        max_tool_rounds = 2
        tool_round = 0
        all_tool_calls = []

        while tool_round < max_tool_rounds:
            response = await ChatService._call_model(messages, stream=False, tools=QUICK_TOOLS)

            if response.status_code != 200:
                error_msg = response.message or "大模型调用失败"
                raise RuntimeError(f"模型调用失败: {error_msg}")

            if has_tool_calls(response):
                tool_calls = extract_tool_calls(response)
                tool_round += 1
                logger.info(f"[快速模式-Tool] 第 {tool_round} 轮，检测到 {len(tool_calls)} 个工具调用")
                await ChatService._execute_tools_and_append(tool_calls, messages, all_tool_calls, tool_round)
                continue

            answer = extract_content(response)
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
    async def stream_quick_ask(
        message: str,
        history: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> AsyncGenerator[dict, None]:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        logger.info(f"[快速模式] 直接回复，跳过RAG管线")

        sys_content = SYSTEM_PROMPT_QUICK
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            sys_content += pers_prompt

        messages = [{"role": "system", "content": sys_content}]
        if history:
            messages.extend(history)
        else:
            messages.append({"role": "user", "content": message})

        max_tool_rounds = 2
        tool_round = 0

        while tool_round < max_tool_rounds:
            responses = await ChatService._call_model(messages, stream=True, tools=QUICK_TOOLS)

            collected_tool_calls: Dict[int, dict] = {}
            has_tc = False

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
                    has_tc = True
                    for tc in tool_calls_delta:
                        idx = tc.get("index", 0)
                        if idx not in collected_tool_calls:
                            collected_tool_calls[idx] = {
                                "id": tc.get("id", ""),
                                "type": tc.get("type", "function"),
                                "function": {"name": "", "arguments": ""}
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
                    yield {"type": "content", "content": content}

                if finish_reason == "tool_calls" and has_tc:
                    break

            if has_tc and collected_tool_calls:
                tool_round += 1
                sorted_tcs = [collected_tool_calls[i] for i in sorted(collected_tool_calls.keys())]
                logger.info(f"[快速模式-Tool] 第 {tool_round} 轮，检测到 {len(sorted_tcs)} 个工具调用")

                messages.append({"role": "assistant", "content": "", "tool_calls": sorted_tcs})

                for tc in sorted_tcs:
                    fn_name = tc["function"]["name"]
                    fn_call_id = tc["id"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except json.JSONDecodeError:
                        fn_args = {}

                    yield {"type": "tool_call", "tool_name": fn_name, "tool_args": fn_args, "tool_call_id": fn_call_id}

                    fn_result = await tool_executor.execute(fn_name, fn_args)
                    logger.info(f"[快速模式-Tool] 执行 {fn_name}({fn_args}) → 结果长度: {len(fn_result)}")

                    yield {"type": "tool_result", "tool_name": fn_name, "result": fn_result, "tool_call_id": fn_call_id}

                    messages.append({"role": "tool", "content": fn_result, "tool_call_id": fn_call_id, "name": fn_name})

                continue

            return

        yield {"type": "content", "content": "抱歉，工具调用次数已达上限，请简化您的问题后再试。"}

    @staticmethod
    async def stream_vision_ask(
        message: str,
        images: list[str],
        history: list[dict] | None = None,
        personalization: dict[str, int] | None = None,
    ) -> AsyncGenerator[dict, None]:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DashScope API Key 未配置，请在 .env 文件中填写 DASHSCOPE_API_KEY")

        logger.info(f"[视觉模式] 图片数量: {len(images)}, 文本: {message[:50] if message else '(无)'}")

        vis_sys = VISION_SYSTEM_PROMPT
        pers_prompt = build_personalization_prompt(personalization)
        if pers_prompt:
            vis_sys += pers_prompt

        messages = [{"role": "system", "content": [{"text": vis_sys}]}]
        if history:
            for h in history:
                if isinstance(h.get("content"), str):
                    messages.append({"role": h["role"], "content": [{"text": h["content"]}]})
                else:
                    messages.append(h)
        user_msg = build_multimodal_message(message, images)
        messages.append(user_msg)

        import threading
        import queue as sync_queue
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


chat_service = ChatService()