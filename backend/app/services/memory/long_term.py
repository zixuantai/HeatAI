import json
import logging
import asyncio
import time
import math
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)

IDLE_PATTERNS = [
    "你好", "您好", "hi", "hello", "谢谢", "感谢", "再见", "拜拜", "好的", "ok", "嗯", "哦",
    "知道了", "明白了", "了解", "收到"
]
ADDRESS_PATTERNS = ["地址", "小区", "号楼", "单元", "门牌", "栋", "座", "室", "楼层", "区", "路",
                    "街", "号院", "社区"]
CONTACT_PATTERNS = ["电话", "手机", "联系", "拨打", "致电", "号码"]
HEAT_PATTERNS = ["暖气", "地暖", "散热器", "暖气管", "集中供暖", "自采暖", "燃气壁挂炉", "供暖",
                 "采暖", "供热", "锅炉", "热力", "换热站", "分户计量", "管道井", "阀门", "分水器",
                 "回水", "进水", "温控阀", "热表", "滤网", "循环泵"]
DEVICE_PATTERNS = ["型号", "品牌", "规格", "功率", "安装", "年限", "老旧", "新装", "改造"]
PROBLEM_PATTERNS = ["故障", "报修", "维修", "不热", "漏水", "问题", "坏了", "异常", "冒水",
                    "停暖", "温度低", "冰凉", "堵塞", "气堵", "排气", "放水", "噪音", "异响",
                    "忽冷忽热", "一半热一半凉", "压力", "掉压", "补压", "泄压"]

EMOTION_POSITIVE = [
    "谢谢", "感谢", "太好了", "很棒", "满意", "不错", "厉害", "专业", "赞", "好评",
    "解决了", "快多了", "暖和了", "好多了", "靠谱", "方便", "满意了", "开心"
]
EMOTION_NEGATIVE = [
    "烦", "气死", "生气", "差劲", "不满意", "投诉", "坑", "骗", "垃圾", "太慢",
    "敷衍", "不管", "没用", "还是不行", "又坏了", "又出问题", "受不了", "忍不了",
    "无语", "失望", "怎么搞的", "什么情况", "几次了", "多少次了"
]
EMOTION_URGENT = [
    "急", "紧急", "立刻", "马上", "快", "赶紧", "迅速", "尽快", "救命", "危险",
    "漏水了", "冒水了", "停暖了", "零下", "冻", "冷死了"
]

DEFAULT_PREFERENCES = {
    "profile": "",
    "device_info": "",
    "key_problems": "",
    "interaction_summary": "",
    "memory_summary": "",
    "round_counter": 0,
    "raw_history_snapshot": "",
    "emotion_timeline": [],
    "emotion_summary": "",
    "session_snapshots": [],
    "memory_last_updated": 0.0,
}

MEMORY_EXTRACTION_PROMPT = """你是一个供热服务领域的用户记忆提取专家。请根据以下对话历史，提取并更新用户的关键信息。

## 提取规则
请严格按 JSON 格式输出，包含以下字段：
- **profile**：用户的基本画像信息（称呼、住址特征、联系方式、身份角色、偏好倾向等）
- **device_info**：供暖设备相关信息（型号、品牌、安装年限、使用方式等）
- **key_problems**：用户历史上报修或咨询过的主要问题（每条一个要点）
- **interaction_summary**：重要交互事件摘要（报修、投诉、表扬、紧急事件等）
- **new_insights**：本次对话中新发现的、之前不知道的信息
- **emotion**：用户在本轮对话中的情绪状态，选项: "positive"/"negative"/"urgent"/"neutral"，及强度 intensity(0-1)
- **emotion_cause**：导致该情绪的主要原因（简短描述）

## 情感分析指南
- positive：用户表达满意、感谢、愉快
- negative：用户表达不满、抱怨、沮丧、失望
- urgent：用户有紧急诉求，语气急切
- neutral：用户情绪平稳、纯信息交换

## 注意
1. 只提取对后续服务有参考价值的实质性信息，忽略客套寒暄
2. 如果某个字段本次没有新信息，设置为空字符串 ""
3. 已有信息如下，请在此基础上增量更新，不要丢失已有信息：
{existing_context}

## 对话历史
{conversation_history}

请输出 JSON 结果（仅 JSON，不含其他文本）："""

MEMORY_COMPRESS_PROMPT = """你是一个记忆压缩专家。当前用户的长期记忆过长，需要进行无损压缩。

## 压缩规则
1. 合并重复或高度相似的条目
2. 保留所有关键事实信息（地址、设备型号、历史问题等）
3. 对冗余描述进行精简，但绝不丢失信息
4. 输出格式保持与输入一致（JSON）

## 当前记忆
{memory_json}

请输出压缩后的 JSON 结果（仅 JSON，不含其他文本）："""

SESSION_MERGE_PROMPT = """你是一个跨会话记忆合并专家。请将用户的多个历史会话摘要合并为一份精简的长期记忆。

## 合并规则
1. 合并跨会话中相同主题的信息
2. 标记出反复出现的问题（频次 > 1）
3. 识别趋势：问题是否恶化、情绪是否变化
4. 保留最新、最完整的信息，去除过时矛盾的信息

## 已有画像
{existing_context}

## 历史会话摘要
{session_snapshots}

请输出合并后的 JSON（仅 JSON），包含 profile, device_info, key_problems, interaction_summary 四个字段："""


class LongTermMemory:

    @staticmethod
    async def load(db: AsyncSession, user_id: str) -> dict:
        result = await db.execute(select(User.preferences).where(User.id == user_id))
        prefs_json = result.scalar_one_or_none()
        if prefs_json:
            stored = json.loads(prefs_json)
            combined = {**DEFAULT_PREFERENCES, **stored}
            combined.setdefault("emotion_timeline", [])
            combined.setdefault("emotion_summary", "")
            combined.setdefault("session_snapshots", [])
            combined.setdefault("memory_last_updated", 0.0)
            return combined
        return dict(DEFAULT_PREFERENCES)

    @staticmethod
    async def save(db: AsyncSession, user_id: str, prefs: dict) -> None:
        existing = dict(DEFAULT_PREFERENCES)
        existing.update(prefs)
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(preferences=json.dumps(existing, ensure_ascii=False))
        )
        await db.commit()

    @staticmethod
    async def get_context_text(db: AsyncSession, user_id: str) -> str:
        prefs = await LongTermMemory.load(db, user_id)
        summary = prefs.get("memory_summary", "")
        emotion = prefs.get("emotion_summary", "")
        parts = []
        if summary:
            parts.append(f"[用户长期记忆]\n{summary}")
        if emotion:
            parts.append(f"[情绪趋势]\n{emotion}")
        return "\n\n".join(parts)

    @staticmethod
    async def get_context_text_decayed(db: AsyncSession, user_id: str) -> str:
        prefs = await LongTermMemory.load(db, user_id)
        entries = _build_decayed_context(prefs)
        return "\n\n".join(entries) if entries else ""

    @staticmethod
    def extract_from_messages(user_messages: list[str], existing_prefs: dict) -> dict:
        prefs = dict(DEFAULT_PREFERENCES)
        prefs.update(existing_prefs)
        prefs.setdefault("emotion_timeline", [])
        prefs.setdefault("emotion_summary", "")
        prefs.setdefault("session_snapshots", [])
        prefs.setdefault("memory_last_updated", 0.0)

        profile = prefs["profile"]
        device_info = prefs["device_info"]
        key_problems = prefs["key_problems"]

        meaningful = [_filter_idle(c) for c in user_messages]
        meaningful = [c for c in meaningful if c]

        new_profile: list[str] = []
        new_device: list[str] = []
        new_problems: list[str] = []
        interaction_events: list[str] = []

        for content in meaningful:
            tag = _classify_tag(content)
            trimmed = _trim_content(content)

            if tag == "profile" and not _is_dup(trimmed, profile):
                new_profile.append(trimmed)
            elif tag == "device" and not _is_dup(trimmed, device_info):
                new_device.append(trimmed)
            elif tag == "problem" and not _is_dup(trimmed, key_problems):
                new_problems.append(trimmed)
            elif tag in ("address", "contact", "heat"):
                if not _is_dup(trimmed, profile):
                    new_profile.append(f"[{tag}] {trimmed}")

        if any(w in c for c in user_messages for w in ["保修", "报修", "投诉", "表扬", "建议"]):
            if not _is_dup("用户发起报修/投诉/建议", prefs["interaction_summary"]):
                interaction_events.append("用户发起过报修/投诉/建议类请求")

        if new_profile:
            profile = _merge(profile, "；".join(new_profile))
        if new_device:
            device_info = _merge(device_info, "；".join(new_device))
        if new_problems:
            key_problems = _merge(key_problems, "；".join(new_problems))
        if interaction_events:
            prefs["interaction_summary"] = _merge(
                prefs["interaction_summary"], "；".join(interaction_events)
            )

        profile = _truncate(profile, 2000)
        device_info = _truncate(device_info, 1500)
        key_problems = _truncate(key_problems, 2000)
        prefs["interaction_summary"] = _truncate(prefs["interaction_summary"], 1500)

        emotion, intensity = _rule_emotion_analysis(user_messages)
        if emotion != "neutral" or intensity > 0.3:
            timeline = prefs["emotion_timeline"]
            timeline.append({
                "emotion": emotion,
                "intensity": round(intensity, 2),
                "timestamp": time.time(),
                "round": prefs.get("round_counter", 0),
            })
            if len(timeline) > settings.MEMORY_EMOTION_MAX_ENTRIES:
                timeline[:] = timeline[-settings.MEMORY_EMOTION_MAX_ENTRIES:]
            prefs["emotion_timeline"] = timeline

        prefs["emotion_summary"] = _build_emotion_summary(prefs["emotion_timeline"])

        result = {
            "profile": profile,
            "device_info": device_info,
            "key_problems": key_problems,
            "interaction_summary": prefs["interaction_summary"],
            "emotion_timeline": prefs["emotion_timeline"],
            "emotion_summary": prefs["emotion_summary"],
            "round_counter": prefs.get("round_counter", 0),
            "raw_history_snapshot": prefs.get("raw_history_snapshot", ""),
            "session_snapshots": prefs.get("session_snapshots", []),
            "memory_last_updated": time.time(),
        }
        return _rebuild_summary_sync(result)

    @staticmethod
    async def extract_and_save(
        db: AsyncSession,
        user_id: str,
        user_messages: list[str],
        assistant_messages: list[str],
    ) -> bool:
        if not user_messages:
            return False

        existing = await LongTermMemory.load(db, user_id)
        round_counter = existing.get("round_counter", 0) + 1

        has_api_key = bool(settings.DASHSCOPE_API_KEY)
        is_trigger_round = (
            round_counter % settings.MEMORY_EXTRACT_TRIGGER_ROUNDS == 0
        )

        if not is_trigger_round:
            logger.info(f"[长期记忆] 第 {round_counter} 轮，非触发轮次（每 {settings.MEMORY_EXTRACT_TRIGGER_ROUNDS} 轮触发一次），仅更新计数器")
            existing["round_counter"] = round_counter
            existing["memory_last_updated"] = time.time()
            await LongTermMemory.save(db, user_id, existing)
            return False

        if has_api_key:
            logger.info(f"[长期记忆] 第 {round_counter} 轮，触发 LLM 记忆提取")
            try:
                conversation_text = _build_conversation_text(user_messages, assistant_messages)
                existing_context = _build_existing_context(existing)
                llm_result = await _call_llm_extraction(
                    conversation_text, existing_context
                )
                if llm_result:
                    merged = _merge_llm_result(existing, llm_result)
                    merged["round_counter"] = round_counter

                    emotion = llm_result.get("emotion", "neutral")
                    intensity = float(llm_result.get("intensity", 0.5))
                    emotion_cause = llm_result.get("emotion_cause", "")
                    timeline = merged.get("emotion_timeline", [])
                    timeline.append({
                        "emotion": emotion,
                        "intensity": round(intensity, 2),
                        "timestamp": time.time(),
                        "round": round_counter,
                        "cause": _truncate(emotion_cause, 200) if emotion_cause else "",
                    })
                    if len(timeline) > settings.MEMORY_EMOTION_MAX_ENTRIES:
                        timeline[:] = timeline[-settings.MEMORY_EMOTION_MAX_ENTRIES:]
                    merged["emotion_timeline"] = timeline
                    merged["emotion_summary"] = _build_emotion_summary(timeline)

                    merged["memory_last_updated"] = time.time()
                    merged = _rebuild_summary_sync(merged)
                    await LongTermMemory.save(db, user_id, merged)
                    logger.info(f"[长期记忆] ✅ LLM 提取完成，已保存")
                    return True
                else:
                    logger.warning("[长期记忆] LLM 提取返回空结果，回退到规则匹配")
            except Exception as e:
                logger.error(f"[长期记忆] LLM 提取异常，回退到规则匹配: {e}")

        logger.info(f"[长期记忆] 第 {round_counter} 轮，使用规则匹配提取")
        new_prefs = LongTermMemory.extract_from_messages(user_messages, existing)
        new_prefs["round_counter"] = round_counter
        new_prefs["memory_last_updated"] = time.time()

        total_len = len(new_prefs.get("memory_summary", ""))
        if total_len > settings.MEMORY_COMPRESS_THRESHOLD_CHARS and has_api_key:
            try:
                logger.info(f"[长期记忆] 记忆长度 {total_len} > {settings.MEMORY_COMPRESS_THRESHOLD_CHARS}，触发 LLM 压缩")
                compressed = await _call_llm_compress(new_prefs)
                if compressed:
                    compressed["round_counter"] = round_counter
                    compressed["emotion_timeline"] = new_prefs.get("emotion_timeline", [])
                    compressed["emotion_summary"] = new_prefs.get("emotion_summary", "")
                    compressed["session_snapshots"] = new_prefs.get("session_snapshots", [])
                    compressed["memory_last_updated"] = time.time()
                    await LongTermMemory.save(db, user_id, compressed)
                    logger.info(f"[长期记忆] ✅ LLM 压缩完成，已保存")
                    return True
            except Exception as e:
                logger.error(f"[长期记忆] LLM 压缩异常，保留完整记忆: {e}")

        await LongTermMemory.save(db, user_id, new_prefs)
        return True

    @staticmethod
    async def finalize_session(
        db: AsyncSession,
        user_id: str,
        session_id: str,
        user_messages: list[str],
        assistant_messages: list[str],
    ) -> None:
        prefs = await LongTermMemory.load(db, user_id)

        conversation_text = _build_conversation_text(user_messages, assistant_messages)
        if len(conversation_text) < 50:
            return

        snapshot = {
            "session_id": session_id,
            "message_count": len(user_messages) + len(assistant_messages),
            "first_message": _truncate(user_messages[0], 100) if user_messages else "",
            "summary": _truncate(conversation_text, 800),
            "created_at": time.time(),
        }

        snapshots = prefs.get("session_snapshots", [])
        replaced = False
        for i, snap in enumerate(snapshots):
            if snap.get("session_id") == session_id:
                snapshots[i] = snapshot
                replaced = True
                break
        if not replaced:
            snapshots.append(snapshot)
            if len(snapshots) > settings.MEMORY_SESSION_SNAPSHOT_MAX:
                snapshots[:] = snapshots[-settings.MEMORY_SESSION_SNAPSHOT_MAX:]

        prefs["session_snapshots"] = snapshots
        prefs["memory_last_updated"] = time.time()
        await LongTermMemory.save(db, user_id, prefs)
        logger.info(f"[长期记忆] 会话 {session_id} 快照已{'更新' if replaced else '保存'}，当前共 {len(snapshots)} 个会话快照")

    @staticmethod
    async def merge_sessions(
        db: AsyncSession,
        user_id: str,
    ) -> None:
        prefs = await LongTermMemory.load(db, user_id)
        snapshots = prefs.get("session_snapshots", [])
        if len(snapshots) < 2:
            logger.info(f"[长期记忆] 会话快照不足 {len(snapshots)} 个，跳过合并")
            return

        logger.info(f"[长期记忆] 开始跨会话合并，共 {len(snapshots)} 个会话快照")

        has_api_key = bool(settings.DASHSCOPE_API_KEY)
        if has_api_key:
            try:
                existing_context = _build_existing_context(prefs)
                snapshots_text = json.dumps(snapshots, ensure_ascii=False, indent=2)
                merged = await _call_llm_session_merge(existing_context, snapshots_text)
                if merged:
                    merged["emotion_timeline"] = prefs.get("emotion_timeline", [])
                    merged["emotion_summary"] = prefs.get("emotion_summary", "")
                    merged["session_snapshots"] = snapshots
                    merged["round_counter"] = prefs.get("round_counter", 0)
                    merged["memory_last_updated"] = time.time()
                    merged = _rebuild_summary_sync(merged)
                    await LongTermMemory.save(db, user_id, merged)
                    logger.info(f"[长期记忆] ✅ 跨会话合并完成")
                    return
            except Exception as e:
                logger.error(f"[长期记忆] LLM 跨会话合并异常，使用简单合并: {e}")

        merged_text = ""
        for snap in snapshots:
            summary = snap.get("summary", "")
            if summary:
                first_msg = snap.get("first_message", "")
                merged_text += f"[会话 {snap.get('session_id', '?')[:8]}]: {first_msg}\n"
        if merged_text:
            prefs["interaction_summary"] = _merge(
                prefs.get("interaction_summary", ""), _truncate(merged_text, 1000)
            )
            prefs["memory_last_updated"] = time.time()
            prefs = _rebuild_summary_sync(prefs)
            await LongTermMemory.save(db, user_id, prefs)
            logger.info(f"[长期记忆] ✅ 简单跨会话合并完成")


def _build_decayed_context(prefs: dict) -> list[str]:
    entries = []
    last_updated = prefs.get("memory_last_updated", 0.0)
    decay_weight = _calc_decay_weight(last_updated) if last_updated > 0 else 1.0

    if prefs.get("profile"):
        entries.append(f"[用户档案] (时效权重={decay_weight:.2f})\n{prefs['profile']}")
    if prefs.get("device_info"):
        entries.append(f"[设备信息]\n{prefs['device_info']}")
    if prefs.get("key_problems"):
        entries.append(f"[历史问题]\n{prefs['key_problems']}")
    if prefs.get("interaction_summary"):
        entries.append(f"[交互摘要]\n{prefs['interaction_summary']}")
    if prefs.get("emotion_summary"):
        entries.append(f"[情绪趋势]\n{prefs['emotion_summary']}")

    if decay_weight < 0.5:
        entries = [f"[注意] 以下长期记忆已超过 {settings.MEMORY_DECAY_HALF_LIFE_DAYS} 天未更新，仅供参考\n\n"] + entries

    return entries


def _calc_decay_weight(last_updated_ts: float) -> float:
    age_seconds = time.time() - last_updated_ts
    age_days = age_seconds / 86400.0
    half_life = max(1, settings.MEMORY_DECAY_HALF_LIFE_DAYS)
    decay = math.exp(-age_days * math.log(2) / half_life)
    return max(0.1, min(1.0, decay))


def _rule_emotion_analysis(messages: list[str]) -> tuple[str, float]:
    combined = " ".join(messages)
    pos_count = sum(1 for kw in EMOTION_POSITIVE if kw in combined)
    neg_count = sum(1 for kw in EMOTION_NEGATIVE if kw in combined)
    urgent_count = sum(1 for kw in EMOTION_URGENT if kw in combined)

    if urgent_count >= 2:
        return ("urgent", min(1.0, 0.5 + urgent_count * 0.15))
    if neg_count >= 2:
        return ("negative", min(1.0, 0.4 + neg_count * 0.15))
    if pos_count >= 2:
        return ("positive", min(1.0, 0.4 + pos_count * 0.15))
    if urgent_count >= 1:
        return ("urgent", 0.5)
    if neg_count >= 1:
        return ("negative", 0.4)
    if pos_count >= 1:
        return ("positive", 0.4)
    return ("neutral", 0.0)


def _build_emotion_summary(timeline: list[dict]) -> str:
    if not timeline:
        return ""

    recent = timeline[-10:]
    emotion_counts = {"positive": 0, "negative": 0, "urgent": 0, "neutral": 0}
    for entry in recent:
        emo = entry.get("emotion", "neutral")
        emotion_counts[emo] = emotion_counts.get(emo, 0) + 1

    total = len(recent)
    parts = []
    if total > 0 and emotion_counts.get("negative", 0) > total * 0.4:
        parts.append(f"⚠️ 近期消极情绪占比较高 ({emotion_counts['negative']}/{total})，需重点关注")
    if emotion_counts.get("urgent", 0) > 0:
        parts.append(f"🔴 近 {total} 轮对话中出现 {emotion_counts['urgent']} 次紧急诉求")
    if emotion_counts.get("positive", 0) > total * 0.5:
        parts.append(f"🟢 近期用户满意度较高 ({emotion_counts['positive']}/{total})")

    latest = recent[-1] if recent else {}
    latest_emo = latest.get("emotion", "neutral")
    cause = latest.get("cause", "")
    if latest_emo == "negative" and cause:
        parts.append(f"最新负面情绪原因: {cause}")
    elif latest_emo == "urgent" and cause:
        parts.append(f"最新紧急诉求: {cause}")
    parts.append(f"最近情绪状态: {latest_emo}")

    return "；".join(parts) if parts else ""


async def _call_llm_extraction(conversation_text: str, existing_context: str) -> Optional[dict]:
    from dashscope import Generation

    prompt = MEMORY_EXTRACTION_PROMPT.format(
        existing_context=existing_context or "（暂无已有信息）",
        conversation_history=conversation_text[:8000],
    )

    logger.info(f"[长期记忆] 调用 LLM 提取 (model={settings.MEMORY_LLM_MODEL})")

    response = await asyncio.to_thread(
        Generation.call,
        model=settings.MEMORY_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        api_key=settings.DASHSCOPE_API_KEY,
    )

    if response.status_code != 200:
        logger.error(f"[长期记忆] LLM 提取失败: {response.message}")
        return None

    content = response.output.choices[0].message.content
    return _parse_json_response(content)


async def _call_llm_compress(prefs: dict) -> Optional[dict]:
    from dashscope import Generation

    compress_target = {
        k: v for k, v in prefs.items()
        if k in ("profile", "device_info", "key_problems", "interaction_summary")
    }
    memory_json = json.dumps(compress_target, ensure_ascii=False, indent=2)
    prompt = MEMORY_COMPRESS_PROMPT.format(memory_json=memory_json[:6000])

    logger.info(f"[长期记忆] 调用 LLM 压缩 (model={settings.MEMORY_LLM_MODEL})")

    response = await asyncio.to_thread(
        Generation.call,
        model=settings.MEMORY_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        api_key=settings.DASHSCOPE_API_KEY,
    )

    if response.status_code != 200:
        logger.error(f"[长期记忆] LLM 压缩失败: {response.message}")
        return None

    content = response.output.choices[0].message.content
    parsed = _parse_json_response(content)
    if parsed:
        result = dict(DEFAULT_PREFERENCES)
        result.update(parsed)
        return _rebuild_summary_sync(result)
    return None


async def _call_llm_session_merge(existing_context: str, snapshots_text: str) -> Optional[dict]:
    from dashscope import Generation

    prompt = SESSION_MERGE_PROMPT.format(
        existing_context=existing_context or "（暂无已有画像）",
        session_snapshots=snapshots_text[:8000],
    )

    logger.info(f"[长期记忆] 调用 LLM 跨会话合并 (model={settings.MEMORY_LLM_MODEL})")

    response = await asyncio.to_thread(
        Generation.call,
        model=settings.MEMORY_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        api_key=settings.DASHSCOPE_API_KEY,
    )

    if response.status_code != 200:
        logger.error(f"[长期记忆] LLM 跨会话合并失败: {response.message}")
        return None

    content = response.output.choices[0].message.content
    return _parse_json_response(content)


def _parse_json_response(content: str) -> Optional[dict]:
    import re

    if not content:
        return None

    content = content.strip()
    if content.startswith("```"):
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            content = match.group(1).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning(f"[长期记忆] JSON 解析失败，原始内容前200字符: {content[:200]}")
    return None


def _build_conversation_text(user_messages: list[str], assistant_messages: list[str]) -> str:
    lines = []
    max_turns = min(len(user_messages), len(assistant_messages))
    for i in range(max_turns):
        u = user_messages[i]
        a = assistant_messages[i] if i < len(assistant_messages) else ""
        lines.append(f"用户: {u}")
        if a:
            lines.append(f"助手: {_truncate(a, 300)}")
    return "\n".join(lines)


def _build_existing_context(prefs: dict) -> str:
    parts = []
    if prefs.get("profile"):
        parts.append(f"- 用户档案: {prefs['profile']}")
    if prefs.get("device_info"):
        parts.append(f"- 设备信息: {prefs['device_info']}")
    if prefs.get("key_problems"):
        parts.append(f"- 历史问题: {prefs['key_problems']}")
    if prefs.get("interaction_summary"):
        parts.append(f"- 交互摘要: {prefs['interaction_summary']}")
    if prefs.get("emotion_summary"):
        parts.append(f"- 情绪趋势: {prefs['emotion_summary']}")
    return "\n".join(parts) if parts else ""


def _merge_llm_result(existing: dict, llm_result: dict) -> dict:
    result = dict(DEFAULT_PREFERENCES)
    result.update(existing)

    for field in ("profile", "device_info", "key_problems", "interaction_summary"):
        new_value = llm_result.get(field, "")
        if new_value:
            old_value = result.get(field, "")
            if old_value:
                result[field] = f"{old_value}；{new_value}"
            else:
                result[field] = new_value

    return result


def _rebuild_summary_sync(prefs: dict) -> dict:
    parts = []
    if prefs.get("profile"):
        parts.append(f"用户档案: {prefs['profile']}")
    if prefs.get("device_info"):
        parts.append(f"设备信息: {prefs['device_info']}")
    if prefs.get("key_problems"):
        parts.append(f"历史问题: {prefs['key_problems']}")
    if prefs.get("interaction_summary"):
        parts.append(f"交互摘要: {prefs['interaction_summary']}")

    prefs["memory_summary"] = "；".join(parts)
    if len(prefs["memory_summary"]) > settings.MEMORY_MAX_CONTEXT_CHARS:
        prefs["memory_summary"] = prefs["memory_summary"][:settings.MEMORY_MAX_CONTEXT_CHARS - 3] + "..."
    return prefs


async def _rebuild_summary(prefs: dict) -> dict:
    return _rebuild_summary_sync(prefs)


def _filter_idle(text: str) -> str | None:
    stripped = text.strip().rstrip("!！。.?？")
    for pattern in IDLE_PATTERNS:
        if stripped == pattern:
            return None
    if len(stripped) < 4:
        return None
    return text


def _classify_tag(text: str) -> str | None:
    for kw in PROBLEM_PATTERNS:
        if kw in text:
            return "problem"
    for kw in DEVICE_PATTERNS:
        if kw in text:
            return "device"
    for kw in HEAT_PATTERNS:
        if kw in text:
            return "heat"
    for kw in ADDRESS_PATTERNS:
        if kw in text:
            return "address"
    for kw in CONTACT_PATTERNS:
        if kw in text:
            return "contact"
    return "profile"


def _is_dup(text: str, existing: str) -> bool:
    return text[:30] in existing


def _trim_content(text: str) -> str:
    if len(text) > 200:
        return text[:197] + "..."
    return text


def _truncate(text: str, limit: int) -> str:
    if len(text) > limit:
        return text[:limit - 3] + "..."
    return text


def _merge(existing: str, new: str) -> str:
    if not existing:
        return new
    return f"{existing}；{new}"


long_term_memory = LongTermMemory()
