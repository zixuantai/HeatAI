import json
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

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

DEFAULT_PREFERENCES = {
    "profile": "",
    "device_info": "",
    "key_problems": "",
    "interaction_summary": "",
    "memory_summary": ""
}


class LongTermMemory:

    @staticmethod
    async def load(db: AsyncSession, user_id: str) -> dict:
        result = await db.execute(select(User.preferences).where(User.id == user_id))
        prefs_json = result.scalar_one_or_none()
        if prefs_json:
            stored = json.loads(prefs_json)
            return {**DEFAULT_PREFERENCES, **stored}
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
        return prefs.get("memory_summary", "")

    @staticmethod
    def extract_from_messages(user_messages: list[str], existing_prefs: dict) -> dict:
        prefs = dict(DEFAULT_PREFERENCES)
        prefs.update(existing_prefs)

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

        parts = []
        if profile:
            parts.append(f"用户档案: {profile}")
        if device_info:
            parts.append(f"设备信息: {device_info}")
        if key_problems:
            parts.append(f"历史问题: {key_problems}")
        if prefs["interaction_summary"]:
            parts.append(f"交互摘要: {prefs['interaction_summary']}")

        memory_summary = "；".join(parts)
        if len(memory_summary) > 3000:
            memory_summary = memory_summary[:2997] + "..."

        return {
            "profile": profile,
            "device_info": device_info,
            "key_problems": key_problems,
            "interaction_summary": prefs["interaction_summary"],
            "memory_summary": memory_summary
        }


def _filter_idle(text: str) -> str | None:
    stripped = text.strip().lower().rstrip("!！。.?？")
    for pattern in IDLE_PATTERNS:
        if stripped == pattern.lower():
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
