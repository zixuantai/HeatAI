PERSONALIZATION_CONFIG = {
    "gentle": {
        "label": "温柔体贴",
        "desc": {-1: "请保持专业客观，以事实和数据为重，语气更为严谨。",
                  1: "请以更友好、更亲近的语气回答，像对待朋友一样提供建议。"}
    },
    "enthusiastic": {
        "label": "热情洋溢",
        "desc": {-1: "请保持冷静中立，语气平稳，不带过多情绪色彩。",
                  1: "请更加活力充沛、热情洋溢，用饱满的语言感染用户。"}
    },
    "structure": {
        "label": "标题和列表",
        "desc": {-1: "请多用段落文本呈现信息，减少列表和标题的使用，保持自然的文章体。",
                  1: "请多用清晰的标题和列表结构组织内容，让信息一目了然。"}
    },
    "emoji": {
        "label": "表情符号",
        "desc": {-1: "请尽量减少或避免使用表情符号，保持严肃正式。",
                  1: "请在回答中适当使用表情符号，增加亲和力和趣味性。"}
    },
}


def build_personalization_prompt(personalization: dict[str, int] | None) -> str:
    if not personalization:
        return ""
    instructions = []
    for key, config in PERSONALIZATION_CONFIG.items():
        val = personalization.get(key, 0)
        if val != 0 and val in config["desc"]:
            instructions.append(config["desc"][val])
    if not instructions:
        return ""
    return "\n\n## 对话风格设定\n" + "\n".join(instructions)