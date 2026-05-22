import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# 模块级知识库搜索函数，供 LangChain tool 和 ToolExecutor 共用
_kb_search_fn: Optional[Callable] = None


def set_kb_search_fn(fn: Callable):
    global _kb_search_fn
    _kb_search_fn = fn

CST = timezone(timedelta(hours=8))

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间。当用户询问当前时间、日期、星期几、或需要知道现在是什么时候时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone_offset": {
                        "type": "string",
                        "description": "时区偏移，例如 '+08:00' 表示北京时间。默认为 '+08:00'。"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气信息，包括温度、湿度、天气状况、风力等。供热行业需要根据天气温度调整供暖策略和参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如 '北京'、'哈尔滨'、'乌鲁木齐' 等。"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_heating_fee",
            "description": "计算供暖费用。根据房屋面积、供暖方式（集中供暖/自采暖）、供暖时长等参数估算供暖费用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "area_sqm": {
                        "type": "number",
                        "description": "房屋面积（平方米）"
                    },
                    "heating_type": {
                        "type": "string",
                        "enum": ["集中供暖", "燃气壁挂炉", "地暖", "电采暖"],
                        "description": "供暖方式"
                    },
                    "city": {
                        "type": "string",
                        "description": "所在城市，不同城市收费标准不同"
                    },
                    "months": {
                        "type": "integer",
                        "description": "供暖月数，默认为所在城市标准供暖季月数"
                    }
                },
                "required": ["area_sqm", "heating_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_heating_schedule",
            "description": "查询指定城市的供暖季时间安排，包括供暖开始日期、结束日期、供暖时长等信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如 '北京'、'哈尔滨'、'沈阳' 等"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "report_maintenance",
            "description": "登记供热报修工单。当用户需要报修暖气不热、漏水、异响等供热故障时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "enum": ["暖气不热", "管道漏水", "异响", "阀门故障", "温度不达标", "其他"],
                        "description": "故障类型"
                    },
                    "address": {
                        "type": "string",
                        "description": "报修地址"
                    },
                    "contact_phone": {
                        "type": "string",
                        "description": "联系电话"
                    },
                    "description": {
                        "type": "string",
                        "description": "故障详细描述"
                    }
                },
                "required": ["issue_type", "address", "contact_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_heating_tips",
            "description": "根据当前的天气温度，提供供热相关的节能建议和温度调节技巧。",
            "parameters": {
                "type": "object",
                "properties": {
                    "outdoor_temp": {
                        "type": "number",
                        "description": "室外温度（摄氏度）"
                    },
                    "heating_type": {
                        "type": "string",
                        "enum": ["集中供暖", "燃气壁挂炉", "地暖", "电采暖"],
                        "description": "供暖方式"
                    }
                },
                "required": ["outdoor_temp"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "在供热知识库中搜索相关文档和资料。当用户询问供热专业知识、技术规范、设备操作方法等需要知识库回答的问题时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询关键词或问题"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


HEATING_SCHEDULES = {
    "北京": {"start": "11月15日", "end": "次年3月15日", "months": 4, "standard_temp": "18℃以上"},
    "天津": {"start": "11月15日", "end": "次年3月15日", "months": 4, "standard_temp": "18℃以上"},
    "石家庄": {"start": "11月15日", "end": "次年3月15日", "months": 4, "standard_temp": "18℃以上"},
    "太原": {"start": "11月1日", "end": "次年3月31日", "months": 5, "standard_temp": "18℃以上"},
    "呼和浩特": {"start": "10月15日", "end": "次年4月15日", "months": 6, "standard_temp": "18℃以上"},
    "沈阳": {"start": "11月1日", "end": "次年3月31日", "months": 5, "standard_temp": "18℃以上"},
    "大连": {"start": "11月15日", "end": "次年3月31日", "months": 4.5, "standard_temp": "18℃以上"},
    "长春": {"start": "10月20日", "end": "次年4月6日", "months": 5.5, "standard_temp": "18℃以上"},
    "哈尔滨": {"start": "10月20日", "end": "次年4月20日", "months": 6, "standard_temp": "18℃以上"},
    "济南": {"start": "11月15日", "end": "次年3月15日", "months": 4, "standard_temp": "18℃以上"},
    "青岛": {"start": "11月16日", "end": "次年4月5日", "months": 4.5, "standard_temp": "18℃以上"},
    "郑州": {"start": "11月15日", "end": "次年3月15日", "months": 4, "standard_temp": "18℃以上"},
    "西安": {"start": "11月15日", "end": "次年3月15日", "months": 4, "standard_temp": "16℃以上"},
    "兰州": {"start": "11月1日", "end": "次年3月31日", "months": 5, "standard_temp": "18℃以上"},
    "西宁": {"start": "10月15日", "end": "次年4月15日", "months": 6, "standard_temp": "18℃以上"},
    "银川": {"start": "11月1日", "end": "次年3月31日", "months": 5, "standard_temp": "18℃以上"},
    "乌鲁木齐": {"start": "10月10日", "end": "次年4月10日", "months": 6, "standard_temp": "20℃以上"},
}


HEATING_FEE_STANDARDS = {
    "北京": {"集中供暖": 30, "燃气壁挂炉": 2.28, "地暖": 30, "电采暖": 0.4883},
    "哈尔滨": {"集中供暖": 38.32, "燃气壁挂炉": 2.94, "地暖": 38.32, "电采暖": 0.51},
    "沈阳": {"集中供暖": 26, "燃气壁挂炉": 2.95, "地暖": 26, "电采暖": 0.50},
    "西安": {"集中供暖": 22, "燃气壁挂炉": 2.05, "地暖": 22, "电采暖": 0.4983},
    "济南": {"集中供暖": 26.7, "燃气壁挂炉": 2.75, "地暖": 26.7, "电采暖": 0.5469},
}

DEFAULT_FEE = {"集中供暖": 25, "燃气壁挂炉": 2.5, "地暖": 25, "电采暖": 0.5}

HEATING_TIPS_DB = {
    "集中供暖": {
        "cold": [
            "室外温度较低，建议检查门窗密封性，防止热量流失",
            "定期给暖气片排气，确保水流循环畅通",
            "不要遮盖暖气片，保持散热空间",
            "建议将室内温度设置在18-22℃之间，既舒适又节能"
        ],
        "mild": [
            "当前温度适中，可适当调低供暖阀门，节约能源",
            "注意室内外温差不要过大，进出注意保暖",
            "定期检查供暖管道接口是否有渗漏"
        ],
        "warm": [
            "室外温度较高，可调低供暖温度或减少供暖时间",
            "适当开窗通风，保持室内空气新鲜",
            "检查温控阀是否正常工作"
        ]
    },
    "燃气壁挂炉": {
        "cold": [
            "室外温度低，壁挂炉水温建议设置在60-70℃",
            "检查壁挂炉水压表，确保在1-1.5bar正常范围",
            "定期清洗滤网，保持循环畅通",
            "夜间可调至防冻模式，节省燃气"
        ],
        "mild": [
            "当前温度适中，壁挂炉水温可调至50-60℃节能运行",
            "建议使用定时功能，按需供暖",
            "检查排烟管是否通畅"
        ],
        "warm": [
            "室外温度较高，可仅开启生活热水模式",
            "建议进行壁挂炉年度保养",
            "检查采暖系统是否需要补水"
        ]
    }
}


def _get_weather_simulation(city: str) -> dict:
    tz_offset = 8
    now = datetime.now(CST)
    month = now.month
    hour = now.hour
    city_hash = sum(ord(c) for c in city) % 20

    if city in ["哈尔滨", "长春", "沈阳", "乌鲁木齐", "呼和浩特", "西宁"]:
        base_temp_range = (-25, -5) if month in [12, 1, 2] else (-10, 10) if month in [3, 11] else (5, 25)
    elif city in ["北京", "天津", "石家庄", "太原", "济南", "郑州", "西安", "兰州", "银川", "青岛", "大连"]:
        base_temp_range = (-10, 5) if month in [12, 1, 2] else (0, 18) if month in [3, 11] else (10, 30)
    elif city in ["上海", "南京", "杭州", "武汉", "合肥", "长沙", "南昌"]:
        base_temp_range = (0, 10) if month in [12, 1, 2] else (8, 20) if month in [3, 11] else (15, 35)
    elif city in ["广州", "深圳", "南宁", "海口", "福州", "厦门"]:
        base_temp_range = (10, 20) if month in [12, 1, 2] else (15, 25) if month in [3, 11] else (25, 38)
    else:
        base_temp_range = (-5, 10) if month in [12, 1, 2] else (5, 20) if month in [3, 11] else (15, 32)

    temp_var = (city_hash + hour) % 10 - 3
    temp = max(base_temp_range[0], min(base_temp_range[1], (base_temp_range[0] + base_temp_range[1]) // 2 + temp_var))

    weather_types = ["晴", "多云", "阴", "小雨", "小雪", "雾霾"]
    weather_idx = (city_hash + month + hour // 6) % len(weather_types)
    weather = weather_types[weather_idx]
    if month in [6, 7, 8] and weather in ["小雪"]:
        weather = "多云"

    humidity_base = 60 if weather in ["阴", "小雨", "小雪"] else 40 if weather == "晴" else 55
    humidity = humidity_base + (city_hash % 20 - 5)

    return {
        "city": city,
        "temperature": temp,
        "feels_like": temp - abs(temp_var),
        "weather": weather,
        "humidity": humidity,
        "wind_level": (city_hash % 4) + 1,
        "wind_direction": ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"][city_hash % 8],
        "update_time": now.strftime("%Y-%m-%d %H:%M"),
        "note": "（模拟数据，实际请以气象部门发布为准）"
    }


class ToolExecutor:

    def __init__(self, search_fn=None):
        self._search_fn = search_fn

    def set_search_fn(self, fn):
        self._search_fn = fn

    async def execute(self, tool_name: str, arguments: dict) -> str:
        handler = getattr(self, f"_handle_{tool_name}", None)
        if not handler:
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
        try:
            result = handler(**arguments)
            if asyncio.iscoroutine(result):
                result = await result
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"工具执行失败 [{tool_name}]: {e}")
            return json.dumps({"error": f"工具执行异常: {str(e)}"}, ensure_ascii=False)

    @staticmethod
    def _handle_get_current_time(timezone_offset: str = "+08:00") -> dict:
        try:
            hours = int(timezone_offset.replace(":", "")[:3])
            minutes = int(timezone_offset.replace(":", "")[3:5])
            tz = timezone(timedelta(hours=hours, minutes=minutes))
        except (ValueError, IndexError):
            tz = CST

        now = datetime.now(tz)
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": weekdays[now.weekday()],
            "timezone": f"UTC{timezone_offset}",
            "timestamp": int(now.timestamp())
        }

    @staticmethod
    def _handle_get_weather(city: str) -> dict:
        return _get_weather_simulation(city)

    async def _handle_search_knowledge_base(self, query: str) -> dict:
        if not self._search_fn:
            return {"query": query, "results": [], "message": "搜索功能暂未配置"}
        try:
            results = await self._search_fn(query)
            formatted = []
            for i, r in enumerate(results[:5]):
                formatted.append({
                    "index": i + 1,
                    "title": r.get("title", "未知"),
                    "content": r.get("content", "")[:300],
                    "score": r.get("score", 0),
                    "source": r.get("document_id", "未知")
                })
            return {"query": query, "results": formatted, "total": len(formatted)}
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return {"query": query, "results": [], "message": f"搜索异常: {str(e)}"}

    @staticmethod
    def _handle_calculate_heating_fee(area_sqm: float, heating_type: str, city: str = "", months: int = None) -> dict:
        city_standard = HEATING_FEE_STANDARDS.get(city, DEFAULT_FEE)
        unit_price = city_standard.get(heating_type, DEFAULT_FEE.get(heating_type, 25))

        schedule = HEATING_SCHEDULES.get(city, {})
        default_months = schedule.get("months", 4)
        if months is None:
            months = int(default_months) if isinstance(default_months, (int, float)) else 4

        if heating_type in ["集中供暖", "地暖"]:
            total = area_sqm * unit_price
            detail = f"按面积计费：{area_sqm}㎡ × {unit_price}元/㎡ = {total:.2f}元（整个供暖季）"
        elif heating_type == "燃气壁挂炉":
            avg_gas_per_sqm = 10
            total = area_sqm * avg_gas_per_sqm * months * unit_price
            detail = f"按用气量估算：{area_sqm}㎡ × 约{avg_gas_per_sqm}m³/月 × {months}个月 × {unit_price}元/m³ ≈ {total:.2f}元"
        elif heating_type == "电采暖":
            avg_kwh_per_sqm = 8
            total = area_sqm * avg_kwh_per_sqm * months * unit_price
            detail = f"按用电量估算：{area_sqm}㎡ × 约{avg_kwh_per_sqm}度/月 × {months}个月 × {unit_price}元/度 ≈ {total:.2f}元"
        else:
            total = area_sqm * unit_price * months
            detail = f"{area_sqm}㎡ × {unit_price}元/㎡ × {months}个月 = {total:.2f}元"

        return {
            "area_sqm": area_sqm,
            "heating_type": heating_type,
            "city": city or "通用标准",
            "months": months,
            "unit_price": unit_price,
            "unit": "元/m³" if heating_type == "燃气壁挂炉" else "元/度" if heating_type == "电采暖" else "元/㎡",
            "estimated_total": round(total, 2),
            "detail": detail,
            "note": "以上费用为估算值，实际费用以当地供热公司收费标准为准"
        }

    @staticmethod
    def _handle_query_heating_schedule(city: str) -> dict:
        schedule = HEATING_SCHEDULES.get(city)
        if schedule:
            return {
                "city": city,
                "found": True,
                **schedule
            }
        return {
            "city": city,
            "found": False,
            "message": f"暂无 {city} 的供暖季安排数据。一般北方城市供暖季在11月15日至次年3月15日左右，具体请咨询当地供热公司。"
        }

    @staticmethod
    def _handle_report_maintenance(issue_type: str, address: str, contact_phone: str, description: str = "") -> dict:
        now = datetime.now(CST)
        ticket_id = f"WO{now.strftime('%Y%m%d%H%M%S')}{hash(address + contact_phone) % 10000:04d}"
        logger.info(f"[报修工单] 创建工单 {ticket_id}: 类型={issue_type}, 地址={address}, 电话={contact_phone}")
        return {
            "ticket_id": ticket_id,
            "issue_type": issue_type,
            "address": address,
            "contact_phone": contact_phone,
            "description": description,
            "status": "已受理",
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "estimated_response": "2小时内",
            "note": "维修人员将在2小时内与您联系，请保持电话畅通。如有紧急情况，请拨打供热服务热线：12319"
        }

    @staticmethod
    def _handle_get_heating_tips(outdoor_temp: float, heating_type: str = "集中供暖") -> dict:
        if outdoor_temp <= 0:
            level = "cold"
        elif outdoor_temp <= 15:
            level = "mild"
        else:
            level = "warm"

        type_tips = HEATING_TIPS_DB.get(heating_type, HEATING_TIPS_DB["集中供暖"])
        tips = type_tips.get(level, type_tips["mild"])

        level_desc = {"cold": "寒冷", "mild": "适中", "warm": "温暖"}

        return {
            "outdoor_temp": outdoor_temp,
            "heating_type": heating_type,
            "level": level_desc[level],
            "tips": tips
        }


tool_executor = ToolExecutor()


# ── LangChain Tool 包装 ──────────────────────────────────────

from typing import Optional as _Opt
from langchain_core.tools import tool as lc_tool


@lc_tool
def get_current_time(timezone_offset: str = "+08:00") -> dict:
    """获取当前日期和时间。当用户询问当前时间、日期、星期几、或需要知道现在是什么时候时调用此工具。

    Args:
        timezone_offset: 时区偏移，例如 '+08:00' 表示北京时间。默认为 '+08:00'。
    """
    return ToolExecutor._handle_get_current_time(timezone_offset)


@lc_tool
def get_weather(city: str) -> dict:
    """查询指定城市的实时天气信息，包括温度、湿度、天气状况、风力等。
    供热行业需要根据天气温度调整供暖策略和参数。

    Args:
        city: 城市名称，例如 '北京'、'哈尔滨'、'乌鲁木齐' 等。
    """
    return ToolExecutor._handle_get_weather(city)


@lc_tool
def calculate_heating_fee(
    area_sqm: float, heating_type: str, city: str = "", months: int = 0
) -> dict:
    """计算供暖费用。根据房屋面积、供暖方式（集中供暖/自采暖）、供暖时长等参数估算供暖费用。

    Args:
        area_sqm: 房屋面积（平方米）
        heating_type: 供暖方式。可选: 集中供暖, 燃气壁挂炉, 地暖, 电采暖
        city: 所在城市，不同城市收费标准不同
        months: 供暖月数，默认为所在城市标准供暖季月数
    """
    return ToolExecutor._handle_calculate_heating_fee(
        area_sqm, heating_type, city, months if months > 0 else None
    )


@lc_tool
def query_heating_schedule(city: str) -> dict:
    """查询指定城市的供暖季时间安排，包括供暖开始日期、结束日期、供暖时长等信息。

    Args:
        city: 城市名称，例如 '北京'、'哈尔滨'、'沈阳' 等
    """
    return ToolExecutor._handle_query_heating_schedule(city)


@lc_tool
def report_maintenance(
    issue_type: str, address: str, contact_phone: str, description: str = ""
) -> dict:
    """登记供热报修工单。当用户需要报修暖气不热、漏水、异响等供热故障时调用此工具。

    Args:
        issue_type: 故障类型。可选: 暖气不热, 管道漏水, 异响, 阀门故障, 温度不达标, 其他
        address: 报修地址
        contact_phone: 联系电话
        description: 故障详细描述
    """
    return ToolExecutor._handle_report_maintenance(issue_type, address, contact_phone, description)


@lc_tool
def get_heating_tips(outdoor_temp: float, heating_type: str = "集中供暖") -> dict:
    """根据当前的天气温度，提供供热相关的节能建议和温度调节技巧。

    Args:
        outdoor_temp: 室外温度（摄氏度）
        heating_type: 供暖方式。可选: 集中供暖, 燃气壁挂炉, 地暖, 电采暖
    """
    return ToolExecutor._handle_get_heating_tips(outdoor_temp, heating_type)


# search_knowledge_base 是动态绑定搜索函数的工具
@lc_tool
async def search_knowledge_base(query: str) -> dict:
    """在供热知识库中搜索相关文档和资料。
    当用户询问供热专业知识、技术规范、设备操作方法等需要知识库回答的问题时调用。

    Args:
        query: 搜索查询关键词或问题
    """
    if _kb_search_fn is None:
        return {"query": query, "results": [], "message": "搜索功能暂未配置"}
    try:
        results = await _kb_search_fn(query)
        formatted = []
        for i, r in enumerate(results[:5]):
            formatted.append({
                "index": i + 1,
                "title": r.get("title", "未知"),
                "content": r.get("content", "")[:300],
                "score": r.get("score", 0),
                "source": r.get("document_id", "未知")
            })
        return {"query": query, "results": formatted, "total": len(formatted)}
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return {"query": query, "results": [], "message": f"搜索异常: {str(e)}"}


# LangChain 工具列表（完整列表，含 search_knowledge_base）
LC_TOOLS = [
    get_current_time,
    get_weather,
    calculate_heating_fee,
    query_heating_schedule,
    report_maintenance,
    get_heating_tips,
    search_knowledge_base,
]

# 快速模式工具列表（不含 search_knowledge_base）
LC_QUICK_TOOLS = [
    get_current_time,
    get_weather,
    calculate_heating_fee,
    query_heating_schedule,
    report_maintenance,
    get_heating_tips,
]