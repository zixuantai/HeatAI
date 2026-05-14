def has_tool_calls(response) -> bool:
    try:
        choices = response.output.choices
        if choices:
            msg = choices[0].message
            if msg and msg.get("tool_calls"):
                return True
        return False
    except Exception:
        return False


def extract_tool_calls(response) -> list:
    try:
        msg = response.output.choices[0].message
        return msg.get("tool_calls", [])
    except Exception:
        return []


def extract_content(response) -> str:
    try:
        msg = response.output.choices[0].message
        content = msg.get("content", "")
        return content if content else ""
    except Exception:
        return ""


def extract_finish_reason(response) -> str:
    try:
        choices = response.output.choices
        if choices:
            return choices[0].get("finish_reason", "")
        return ""
    except Exception:
        return ""